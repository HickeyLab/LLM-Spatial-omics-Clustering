"""Reproducible input validation and rendering for Figure 2, Panel D.

Panel D uses a single B004 embedding and colors it by either the H5AD reference
label or each method's cluster-majority reference label.  It deliberately
keeps method-specific clustering assignments separate from the visual UMAP.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
from typing import Any
import warnings

import numpy as np
import pandas as pd
import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parent


class Figure02ValidationError(ValueError):
    """Raised when a Figure 2 input violates its declared data contract."""


@dataclass(frozen=True)
class PanelDData:
    """B004 H5AD data after exact-key validation."""

    cells: pd.DataFrame
    features: np.ndarray
    marker_names: tuple[str, ...]


def load_figure_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load the tracked Figure 2 configuration."""
    path = Path(config_path) if config_path else REPOSITORY_ROOT / "configs/figure_02.yaml"
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or "panel_d" not in config:
        raise Figure02ValidationError(f"Invalid Figure 2 configuration: {path}")
    return config


def _candidate_data_roots(h5ad_filename: str, root_env: str) -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get(root_env)
    if configured:
        candidates.append(Path(configured).expanduser())
    for base in (Path.cwd(), REPOSITORY_ROOT):
        candidates.extend((base, *base.parents))
    seen: set[Path] = set()
    roots: list[Path] = []
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate not in seen:
            seen.add(candidate)
            roots.append(candidate)
    return roots


def resolve_data_root(config: Mapping[str, Any]) -> Path:
    """Find the local source-data directory without committing an absolute path."""
    data_config = config["panel_d"]["data"]
    filename = str(data_config["h5ad_filename"])
    env_name = str(data_config["root_env"])
    for root in _candidate_data_roots(filename, env_name):
        if (root / filename).is_file():
            return root
    raise FileNotFoundError(
        f"Cannot find {filename}. Set {env_name} to the containing directory."
    )


def _as_dense_array(matrix: Any) -> np.ndarray:
    """Convert an AnnData slice to a numeric dense feature matrix."""
    if hasattr(matrix, "toarray"):
        matrix = matrix.toarray()
    return np.asarray(matrix, dtype=np.float64)


def _validate_unique_keys(frame: pd.DataFrame, label: str) -> None:
    missing = {"File_ID", "ID"}.difference(frame.columns)
    if missing:
        raise Figure02ValidationError(f"{label} is missing key columns: {sorted(missing)}")
    if frame[["File_ID", "ID"]].isna().any().any():
        raise Figure02ValidationError(f"{label} has null (File_ID, ID) keys")
    duplicate_count = int(frame.duplicated(["File_ID", "ID"]).sum())
    if duplicate_count:
        raise Figure02ValidationError(f"{label} has {duplicate_count:,} duplicate (File_ID, ID) keys")


def _ordered_subset(frame: pd.DataFrame, file_ids: Sequence[str]) -> pd.DataFrame:
    """Apply the declared FOV order and a deterministic ascending cell-ID order."""
    ordered = frame.copy()
    ordered["File_ID"] = ordered["File_ID"].astype(str)
    ordered["ID"] = pd.to_numeric(ordered["ID"], errors="raise").astype(np.int64)
    ordered["_fov_order"] = pd.Categorical(
        ordered["File_ID"], categories=list(file_ids), ordered=True
    )
    ordered = ordered.sort_values(["_fov_order", "ID"], kind="stable")
    return ordered.drop(columns="_fov_order").reset_index(drop=True)


def load_b004_h5ad(
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> PanelDData:
    """Load the declared B004 cohort directly from the source H5AD.

    The returned 48 features are H5AD ``X`` (45 protein markers) plus the
    three specified H5AD ``obs`` marker columns.  No ``master.csv`` or
    ``truth.csv`` is needed to create this panel input.
    """
    config = dict(config or load_figure_config())
    panel = config["panel_d"]
    cohort = panel["cohort"]
    features_config = panel["features"]
    root = Path(data_root).expanduser().resolve() if data_root else resolve_data_root(config)
    h5ad_path = root / panel["data"]["h5ad_filename"]

    import anndata as ad

    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        required_obs = {
            "File_ID",
            "ID",
            features_config["truth_column"],
            *features_config["coordinate_columns"],
            *features_config["h5ad_obs_markers"],
        }
        missing_obs = required_obs.difference(adata.obs.columns)
        if missing_obs:
            raise Figure02ValidationError(
                f"{h5ad_path.name} is missing required obs columns: {sorted(missing_obs)}"
            )
        file_ids = tuple(str(file_id) for file_id in cohort["file_ids"])
        obs = adata.obs.loc[:, sorted(required_obs)].copy()
        mask = obs["File_ID"].astype(str).isin(file_ids).to_numpy()
        if not mask.any():
            raise Figure02ValidationError("No declared B004 File_IDs were found in the H5AD")
        subset = adata[mask].to_memory()
    finally:
        adata.file.close()

    cells = subset.obs.loc[:, sorted(required_obs)].copy().reset_index(drop=True)
    cells = _ordered_subset(cells, file_ids)
    # ``subset`` retains the original row order, so use exact-key reindexing
    # after the declared order is applied to ``cells``.
    subset_keys = subset.obs.loc[:, ["File_ID", "ID"]].copy()
    subset_keys["File_ID"] = subset_keys["File_ID"].astype(str)
    subset_keys["ID"] = pd.to_numeric(subset_keys["ID"], errors="raise").astype(np.int64)
    feature_frame = pd.DataFrame(
        _as_dense_array(subset.X), columns=[str(name) for name in subset.var_names]
    )
    feature_frame.insert(0, "ID", subset_keys["ID"].to_numpy())
    feature_frame.insert(0, "File_ID", subset_keys["File_ID"].to_numpy())
    feature_frame = cells[["File_ID", "ID"]].merge(
        feature_frame, on=["File_ID", "ID"], how="left", validate="one_to_one", sort=False
    )

    obs_markers = [str(marker) for marker in features_config["h5ad_obs_markers"]]
    cells = cells.merge(
        feature_frame[["File_ID", "ID"]],
        on=["File_ID", "ID"],
        how="left",
        validate="one_to_one",
        sort=False,
    )
    x_markers = [str(name) for name in subset.var_names]
    marker_names = tuple(obs_markers + x_markers)
    if len(marker_names) != int(features_config["expected_total_markers"]):
        raise Figure02ValidationError(
            f"Expected {features_config['expected_total_markers']} features; found {len(marker_names)}"
        )
    obs_marker_values = cells.loc[:, obs_markers].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    x_values = feature_frame.loc[:, x_markers].to_numpy(dtype=float)
    matrix = np.column_stack((obs_marker_values, x_values))

    _validate_panel_d_data(
        cells,
        matrix,
        file_ids,
        int(cohort["expected_cells"]),
        cohort["expected_cells_by_file_id"],
        features_config,
    )
    return PanelDData(cells=cells, features=matrix, marker_names=marker_names)


def _validate_panel_d_data(
    cells: pd.DataFrame,
    features: np.ndarray,
    file_ids: Sequence[str],
    expected_cells: int,
    expected_cells_by_file_id: Mapping[str, int],
    features_config: Mapping[str, Any],
) -> None:
    _validate_unique_keys(cells, "B004 H5AD subset")
    if len(cells) != expected_cells:
        raise Figure02ValidationError(
            f"B004 H5AD subset has {len(cells):,} cells; expected {expected_cells:,}"
        )
    observed_file_ids = set(cells["File_ID"].astype(str))
    if observed_file_ids != set(file_ids):
        raise Figure02ValidationError(
            "B004 H5AD subset File_IDs differ from the declared cohort: "
            f"missing={sorted(set(file_ids) - observed_file_ids)}, "
            f"unexpected={sorted(observed_file_ids - set(file_ids))}"
        )
    observed_counts = cells.groupby("File_ID", sort=False).size().to_dict()
    normalized_expected_counts = {
        str(file_id): int(count) for file_id, count in expected_cells_by_file_id.items()
    }
    if observed_counts != normalized_expected_counts:
        raise Figure02ValidationError(
            "B004 H5AD per-region cell counts differ from the declared cohort: "
            f"observed={observed_counts}, expected={normalized_expected_counts}"
        )
    truth_column = str(features_config["truth_column"])
    if cells[truth_column].isna().any():
        raise Figure02ValidationError("B004 H5AD subset has missing reference labels")
    if features.shape != (len(cells), int(features_config["expected_total_markers"])):
        raise Figure02ValidationError(
            f"Unexpected feature shape {features.shape}; expected "
            f"({len(cells)}, {features_config['expected_total_markers']})"
        )
    if not np.isfinite(features).all():
        raise Figure02ValidationError("B004 H5AD feature matrix contains non-finite values")


def build_shared_umap(
    data: PanelDData,
    config: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Create the one shared UMAP embedding used by all five Panel D views."""
    config = dict(config or load_figure_config())
    params = config["panel_d"]["shared_umap"]

    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    import harmonypy as hm
    import umap

    logging.getLogger("harmonypy").setLevel(logging.WARNING)
    warnings.filterwarnings(
        "ignore",
        message="n_jobs value 1 overridden to 1 by setting random_state.*",
        category=UserWarning,
    )
    transformed = np.arcsinh(data.features / float(params["arcsinh_cofactor"]))
    if bool(params["standardize"]):
        transformed = StandardScaler().fit_transform(transformed)
    components = PCA(
        n_components=float(params["pca_variance_explained"]),
        random_state=int(params["random_seed"]),
    ).fit_transform(transformed)
    batch_key = str(params["harmony_batch_key"])
    harmony_input = pd.DataFrame({batch_key: data.cells[batch_key].astype(str).to_numpy()})
    harmony = hm.run_harmony(
        components,
        harmony_input,
        [batch_key],
        max_iter_harmony=int(params["harmony_max_iterations"]),
    )
    corrected = np.asarray(harmony.Z_corr)
    if corrected.shape[0] != components.shape[0]:
        corrected = corrected.T
    if corrected.shape != components.shape:
        raise Figure02ValidationError(
            f"Harmony returned unexpected shape {corrected.shape}; expected {components.shape}"
        )
    embedding = umap.UMAP(
        n_neighbors=int(params["n_neighbors"]),
        min_dist=float(params["min_dist"]),
        metric=str(params["metric"]),
        random_state=int(params["random_seed"]),
    ).fit_transform(corrected)
    coordinates = data.cells[["File_ID", "ID"]].copy()
    coordinates["UMAP1"] = embedding[:, 0]
    coordinates["UMAP2"] = embedding[:, 1]
    _validate_unique_keys(coordinates, "shared UMAP coordinates")
    return coordinates


def _resolve_assignment_path(
    method_name: str,
    method_config: Mapping[str, Any],
    *,
    data_root: Path,
) -> Path:
    filename = Path(str(method_config["assignment_filename"]))
    if method_name == "pixie":
        return REPOSITORY_ROOT / filename
    return data_root / filename


def _validate_tiff_pixie_manifest(artifact_path: Path, method_config: Mapping[str, Any]) -> None:
    manifest_path = artifact_path.parent / "manifest.json"
    if not manifest_path.is_file():
        raise Figure02ValidationError(f"PIXIE manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise Figure02ValidationError(
            f"PIXIE run is not complete (status={manifest.get('status')!r}): {manifest_path}"
        )
    expected = method_config["parameters"]
    observed = manifest.get("parameters", {})
    for key, expected_value in {
        "include_hoechst": expected["include_hoechst"],
        "blur_sigma": expected["gaussian_sigma_pixels"],
        "pixel_som_side": expected["pixel_som_shape"][0],
        "pixel_meta_clusters": expected["pixel_metaclusters"],
        "cell_som_side": expected["cell_som_shape"][0],
        "cell_meta_clusters": expected["cell_metaclusters"],
        "seed": expected["random_seed"],
    }.items():
        if observed.get(key) != expected_value:
            raise Figure02ValidationError(
                f"PIXIE manifest parameter {key}={observed.get(key)!r}; expected {expected_value!r}"
            )
    training = observed.get("cell_som_training", {})
    for key, expected_value in {
        "sigma": expected["cell_som_sigma"],
        "learning_rate": expected["cell_som_learning_rate"],
        "iterations": expected["cell_som_iterations"],
        "decay": expected["cell_som_decay"],
        "initialization": expected["cell_som_initialization"],
    }.items():
        if training.get(key) != expected_value:
            raise Figure02ValidationError(
                f"PIXIE cell-SOM parameter {key}={training.get(key)!r}; expected {expected_value!r}"
            )


def load_method_assignments(
    data: PanelDData,
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Load and exact-key validate selected clustering assignments for Panel D."""
    config = dict(config or load_figure_config())
    panel = config["panel_d"]
    root = Path(data_root).expanduser().resolve() if data_root else resolve_data_root(config)
    keys = data.cells[["File_ID", "ID"]].copy()
    assignments: dict[str, pd.DataFrame] = {}
    for method_name, method_config in panel["clustering_methods"].items():
        artifact_path = _resolve_assignment_path(method_name, method_config, data_root=root)
        if not artifact_path.is_file():
            raise FileNotFoundError(f"{method_name} assignments are missing: {artifact_path}")
        if method_name == "pixie":
            _validate_tiff_pixie_manifest(artifact_path, method_config)
        label_column = str(method_config["assignment_column"])
        frame = pd.read_csv(artifact_path, usecols=["File_ID", "ID", label_column])
        frame["File_ID"] = frame["File_ID"].astype(str)
        frame["ID"] = pd.to_numeric(frame["ID"], errors="raise").astype(np.int64)
        _validate_unique_keys(frame, f"{method_name} assignments")
        joined = keys.merge(frame, on=["File_ID", "ID"], how="left", validate="one_to_one")
        if joined[label_column].isna().any():
            missing = int(joined[label_column].isna().sum())
            raise Figure02ValidationError(f"{method_name} is missing {missing:,} B004 assignments")
        cluster_count = int(joined[label_column].nunique())
        expected_count = int(method_config["expected_clusters"])
        if cluster_count != expected_count:
            raise Figure02ValidationError(
                f"{method_name} has {cluster_count} clusters; expected {expected_count}"
            )
        assignments[method_name] = joined.rename(columns={label_column: "cluster"})
    return assignments


def majority_reference_labels(
    cells: pd.DataFrame,
    assignments: pd.DataFrame,
    config: Mapping[str, Any] | None = None,
) -> pd.Series:
    """Map each cluster to its globally most frequent H5AD reference label."""
    config = dict(config or load_figure_config())
    truth_column = str(config["panel_d"]["features"]["truth_column"])
    joined = cells[["File_ID", "ID", truth_column]].merge(
        assignments, on=["File_ID", "ID"], how="inner", validate="one_to_one"
    )
    if len(joined) != len(cells):
        raise Figure02ValidationError("Cluster assignments do not cover all B004 cells")
    majority = (
        joined.groupby("cluster", sort=True)[truth_column]
        .agg(lambda values: values.value_counts(sort=True).index[0])
    )
    return assignments["cluster"].map(majority)


def build_panel_d_table(
    data: PanelDData,
    coordinates: pd.DataFrame,
    assignments: Mapping[str, pd.DataFrame],
    config: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Create one rendering table with truth and four majority-mapped methods."""
    config = dict(config or load_figure_config())
    truth_column = str(config["panel_d"]["features"]["truth_column"])
    result = data.cells[["File_ID", "ID", truth_column]].merge(
        coordinates, on=["File_ID", "ID"], how="inner", validate="one_to_one"
    )
    if len(result) != len(data.cells):
        raise Figure02ValidationError("Shared UMAP coordinates do not cover all B004 cells")
    for method_name, method_assignments in assignments.items():
        labeled = majority_reference_labels(data.cells, method_assignments, config)
        label_frame = method_assignments[["File_ID", "ID"]].copy()
        label_frame[method_name] = labeled.to_numpy()
        result = result.merge(label_frame, on=["File_ID", "ID"], how="inner", validate="one_to_one")
    return result.rename(columns={truth_column: "Ground Truth"})


def default_color_map(labels: Sequence[str]) -> dict[str, str]:
    """Use a deterministic, readable palette when the local color map is absent."""
    from matplotlib.colors import to_hex
    from matplotlib import colormaps

    categories = sorted(pd.Series(labels, dtype="string").dropna().unique())
    cmap = colormaps.get_cmap("tab20")
    return {category: to_hex(cmap(index % cmap.N)) for index, category in enumerate(categories)}


def load_color_map(
    labels: Sequence[str],
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> dict[str, str]:
    """Load the existing local cell-type color key, with a deterministic fallback."""
    config = dict(config or load_figure_config())
    root = Path(data_root).expanduser().resolve() if data_root else resolve_data_root(config)
    filename = str(config["panel_d"]["style"]["color_map_filename"])
    path = root / filename
    if not path.is_file():
        return default_color_map(labels)
    color_table = pd.read_csv(path, usecols=["cell_type_update", "color_hex"])
    color_map = dict(
        zip(color_table["cell_type_update"].astype(str), color_table["color_hex"].astype(str), strict=True)
    )
    color_map.setdefault("Unassigned", "#808080")
    for label in pd.Series(labels, dtype="string").dropna().astype(str).unique():
        color_map.setdefault(label, "#808080")
    return color_map


def render_panel_d(
    panel_table: pd.DataFrame,
    output_path: str | Path,
    *,
    color_map: Mapping[str, str] | None = None,
    zoom: Mapping[str, float] | None = None,
    dpi: int = 300,
    point_size: float = 0.18,
    alpha: float = 0.6,
) -> Path:
    """Render the five shared-geometry Panel D UMAPs as one manuscript panel."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from mpl_toolkits.axes_grid1.inset_locator import mark_inset

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel_order = ["Ground Truth", "leiden", "flowsom", "spatialsort", "pixie"]
    panel_titles = ["Ground Truth", "Leiden", "FlowSOM", "SpatialSort", "PIXIE"]
    colors = dict(color_map or default_color_map(panel_table["Ground Truth"].astype(str)))
    colors.setdefault("Unassigned", "#808080")
    fig, axes = plt.subplots(1, len(panel_order), figsize=(16.4, 6.7))
    fig.subplots_adjust(left=0.035, right=0.995, bottom=0.10, top=0.52, wspace=0.28)
    zoom = dict(zoom or {})
    use_zoom = {"x0", "y0", "size"}.issubset(zoom)
    for axis, column, title in zip(axes, panel_order, panel_titles, strict=True):
        point_colors = panel_table[column].astype(str).map(colors).fillna("#808080")
        axis.scatter(
            panel_table["UMAP1"],
            panel_table["UMAP2"],
            s=point_size,
            c=point_colors.to_numpy(),
            alpha=alpha,
            linewidths=0,
            rasterized=True,
        )
        axis.set_title(title)
        axis.set_xlabel("UMAP 1")
        axis.set_ylabel("UMAP 2")
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_aspect("equal", adjustable="box")
        if use_zoom:
            x0, y0, size = (float(zoom[key]) for key in ("x0", "y0", "size"))
            axis.add_patch(
                Rectangle((x0, y0), size, size, linewidth=0.8, edgecolor="black", facecolor="none")
            )
            bounds = axis.get_position()
            inset_height = bounds.width * fig.get_figwidth() / fig.get_figheight()
            inset = fig.add_axes([bounds.x0, 0.58, bounds.width, inset_height])
            inset.scatter(
                panel_table["UMAP1"],
                panel_table["UMAP2"],
                s=max(point_size * 5, 0.7),
                c=point_colors.to_numpy(),
                alpha=alpha,
                linewidths=0,
                rasterized=True,
            )
            inset.set_xlim(x0, x0 + size)
            inset.set_ylim(y0, y0 + size)
            inset.set_xticks([])
            inset.set_yticks([])
            for spine in inset.spines.values():
                spine.set_linewidth(0.8)
            mark_inset(axis, inset, loc1=3, loc2=4, fc="none", ec="black", lw=0.8)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def save_panel_d_provenance(
    data: PanelDData,
    panel_table: pd.DataFrame,
    output_path: str | Path,
    config: Mapping[str, Any] | None = None,
) -> Path:
    """Write small, local provenance facts next to the rendered artifact."""
    config = dict(config or load_figure_config())
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "figure": 2,
        "panel": "D",
        "cohort": config["panel_d"]["cohort"],
        "marker_count": len(data.marker_names),
        "row_count": len(panel_table),
        "cluster_counts": {
            method: int(panel_table[method].nunique())
            for method in ("leiden", "flowsom", "spatialsort", "pixie")
        },
        "shared_umap": config["panel_d"]["shared_umap"],
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
