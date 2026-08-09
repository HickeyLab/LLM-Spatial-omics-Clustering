"""Reproducible input validation and rendering for Figure 2 panels B through J.

Panel B reports the raw non-Noise B004 reference-label distribution. Panel D
uses one B004 embedding and colors it by either the H5AD reference label or
each method's cluster-majority reference label. It deliberately keeps
method-specific clustering assignments separate from the visual UMAP.

Panel E evaluates the same method assignments region by region.  It maps a
method's clusters to majority H5AD reference labels independently within each
region, then reports the reference-cell-count-weighted mean of class-level F1.
Panels F--H report global per-cell-type F1, per-region purity, and global
per-cell-type purity.  Panel I summarizes H5AD protein expression in
cluster-majority CD8+ T-cell groups, while Panel J shows fixed spatial examples
using the same selected method assignments.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import errno
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import tempfile
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


@dataclass(frozen=True)
class PanelBDistribution:
    """Validated raw B004 reference-label counts used by Panel B."""

    counts: pd.DataFrame
    source_cell_count: int
    excluded_counts: dict[str, int]


@dataclass(frozen=True)
class PanelCData:
    """Validated raw spatial reference labels for the selected Panel C region."""

    cells: pd.DataFrame
    source_cell_count: int
    cell_type_counts: dict[str, int]


@dataclass(frozen=True)
class PanelEData:
    """Validated per-region, per-method weighted-F1 measurements for Panel E."""

    scores: pd.DataFrame
    source_cell_count: int
    evaluation_cell_count: int
    excluded_counts: dict[str, int]
    evaluation_class_count: int
    cluster_counts: dict[str, int]


@dataclass(frozen=True)
class PanelCellTypeMetrics:
    """Validated global F1 and recall-by-reference-cell-type metrics for F/H."""

    metrics: pd.DataFrame
    source_cell_count: int
    evaluation_cell_count: int
    excluded_counts: dict[str, int]
    evaluation_class_count: int
    cluster_counts: dict[str, int]


@dataclass(frozen=True)
class PanelGData:
    """Validated region-level cluster-majority purity measurements for Panel G."""

    scores: pd.DataFrame
    source_cell_count: int
    evaluation_cell_count: int
    excluded_counts: dict[str, int]
    evaluation_class_count: int
    cluster_counts: dict[str, int]


@dataclass(frozen=True)
class PanelIData:
    """Marker summaries and selected-cell totals for Panel I's CD8+ T groups."""

    summaries: pd.DataFrame
    marker_names: tuple[str, ...]
    source_cell_count: int
    selected_cell_counts: dict[str, int]
    selected_cluster_counts: dict[str, int]
    cluster_counts: dict[str, int]


@dataclass(frozen=True)
class PanelJData:
    """Spatial labels and fixed low/high agreement example metadata for Panel J."""

    cells: pd.DataFrame
    examples: pd.DataFrame
    source_cell_count: int
    plotted_cell_count: int
    excluded_counts: dict[str, int]
    cluster_counts: dict[str, int]


def load_figure_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load the tracked Figure 2 configuration."""
    path = Path(config_path) if config_path else REPOSITORY_ROOT / "configs/figure_02.yaml"
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    required_panels = {
        "panel_b",
        "panel_c",
        "panel_d",
        "panel_e",
        "panel_f",
        "panel_g",
        "panel_h",
        "panel_i",
        "panel_j",
    }
    if not isinstance(config, dict) or not required_panels.issubset(config):
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


def _source_panel_config(
    config: Mapping[str, Any],
    panel_key: str,
    source_key_name: str,
) -> Mapping[str, Any]:
    """Resolve a panel's declared source panel without copying data contracts."""
    if panel_key not in config:
        raise Figure02ValidationError(f"Figure 2 configuration has no {panel_key!r} section")
    panel = config[panel_key]
    source_key = str(panel.get(source_key_name, panel_key))
    if source_key not in config:
        raise Figure02ValidationError(
            f"{panel_key} refers to absent {source_key_name}={source_key!r}"
        )
    source = config[source_key]
    if not isinstance(source, Mapping):
        raise Figure02ValidationError(f"Figure 2 source panel {source_key!r} is not a mapping")
    return source


def resolve_data_root(config: Mapping[str, Any], *, panel_key: str = "panel_d") -> Path:
    """Find the local source-data directory without committing an absolute path."""
    source_panel = _source_panel_config(config, panel_key, "data_source_panel")
    if "data" not in source_panel:
        raise Figure02ValidationError(f"Figure 2 configuration has no data source for {panel_key!r}")
    data_config = source_panel["data"]
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


def _validate_b004_observations(
    cells: pd.DataFrame,
    file_ids: Sequence[str],
    expected_cells: int,
    expected_cells_by_file_id: Mapping[str, int],
    truth_column: str,
) -> None:
    """Validate B004 keys, region coverage, and reference labels shared by panels."""
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
    if truth_column not in cells.columns:
        raise Figure02ValidationError(f"B004 H5AD subset is missing {truth_column!r}")
    if cells[truth_column].isna().any():
        raise Figure02ValidationError("B004 H5AD subset has missing reference labels")


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


def load_panel_b_distribution(
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> PanelBDistribution:
    """Load and validate the raw non-Noise B004 reference-label distribution."""
    config = dict(config or load_figure_config())
    panel = config["panel_b"]
    cohort = panel["cohort"]
    labels_config = panel["labels"]
    truth_column = str(labels_config["truth_column"])
    root = (
        Path(data_root).expanduser().resolve()
        if data_root
        else resolve_data_root(config, panel_key="panel_b")
    )
    h5ad_path = root / str(panel["data"]["h5ad_filename"])

    import anndata as ad

    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        required_obs = {"File_ID", "ID", truth_column}
        missing_obs = required_obs.difference(adata.obs.columns)
        if missing_obs:
            raise Figure02ValidationError(
                f"{h5ad_path.name} is missing required obs columns: {sorted(missing_obs)}"
            )
        observed = adata.obs.loc[:, ["File_ID", "ID", truth_column]].copy()
    finally:
        adata.file.close()

    file_ids = tuple(str(file_id) for file_id in cohort["file_ids"])
    cells = observed.loc[observed["File_ID"].astype(str).isin(file_ids)].copy()
    cells = _ordered_subset(cells, file_ids)
    _validate_b004_observations(
        cells,
        file_ids,
        int(cohort["expected_cells"]),
        cohort["expected_cells_by_file_id"],
        truth_column,
    )

    raw_counts = cells[truth_column].astype(str).value_counts(sort=True)
    excluded_labels = [str(label) for label in labels_config["excluded_labels"]]
    missing_excluded = sorted(set(excluded_labels).difference(raw_counts.index.astype(str)))
    if missing_excluded:
        raise Figure02ValidationError(
            f"Configured Panel B exclusions are absent from the B004 labels: {missing_excluded}"
        )
    excluded_counts = {label: int(raw_counts.loc[label]) for label in excluded_labels}
    expected_excluded = {
        str(label): int(count)
        for label, count in labels_config["expected_excluded_counts"].items()
    }
    if excluded_counts != expected_excluded:
        raise Figure02ValidationError(
            "Panel B excluded-label counts differ from the declared contract: "
            f"observed={excluded_counts}, expected={expected_excluded}"
        )

    counts = raw_counts.loc[~raw_counts.index.astype(str).isin(excluded_labels)].sort_values(
        ascending=False, kind="stable"
    )
    included_cell_count = int(counts.sum())
    if included_cell_count != int(labels_config["expected_included_cells"]):
        raise Figure02ValidationError(
            "Panel B included-cell total differs from the declared contract: "
            f"observed={included_cell_count:,}, "
            f"expected={int(labels_config['expected_included_cells']):,}"
        )
    if len(counts) != int(labels_config["expected_label_count"]):
        raise Figure02ValidationError(
            "Panel B label count differs from the declared contract: "
            f"observed={len(counts)}, expected={int(labels_config['expected_label_count'])}"
        )
    observed_counts = [(str(label), int(count)) for label, count in counts.items()]
    expected_counts = [
        (str(label), int(count)) for label, count in labels_config["expected_counts"].items()
    ]
    if observed_counts != expected_counts:
        raise Figure02ValidationError(
            "Panel B raw-label distribution differs from the declared contract: "
            f"observed={observed_counts}, expected={expected_counts}"
        )

    table = pd.DataFrame(
        {
            "Cell Type": [label for label, _ in observed_counts],
            "Cell Count": [count for _, count in observed_counts],
        }
    )
    return PanelBDistribution(
        counts=table,
        source_cell_count=len(cells),
        excluded_counts=excluded_counts,
    )


def load_panel_c_spatial_data(
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> PanelCData:
    """Load and validate the one raw-label B004 tissue region shown in Panel C.

    This intentionally reads only H5AD observation columns.  Panel C is a
    spatial rendering of the reference labels, so loading the 48-marker matrix
    used by Panel D would add unnecessary I/O and hidden dependencies.
    """
    config = dict(config or load_figure_config())
    panel = config["panel_c"]
    region = panel["region"]
    labels_config = panel["labels"]
    truth_column = str(labels_config["truth_column"])
    coordinate_columns = [str(column) for column in panel["coordinates"]["columns"]]
    if len(coordinate_columns) != 2:
        raise Figure02ValidationError("Panel C requires exactly two coordinate columns")
    root = (
        Path(data_root).expanduser().resolve()
        if data_root
        else resolve_data_root(config, panel_key="panel_c")
    )
    h5ad_path = root / str(panel["data"]["h5ad_filename"])
    file_id = str(region["file_id"])

    declared_b004_ids = {str(value) for value in config["panel_b"]["cohort"]["file_ids"]}
    if file_id not in declared_b004_ids:
        raise Figure02ValidationError(
            f"Panel C File_ID {file_id!r} is not part of the declared B004 cohort"
        )

    import anndata as ad

    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        required_obs = {"File_ID", "ID", truth_column, *coordinate_columns}
        missing_obs = required_obs.difference(adata.obs.columns)
        if missing_obs:
            raise Figure02ValidationError(
                f"{h5ad_path.name} is missing required obs columns: {sorted(missing_obs)}"
            )
        observed = adata.obs.loc[:, sorted(required_obs)].copy()
    finally:
        adata.file.close()

    cells = observed.loc[observed["File_ID"].astype(str).eq(file_id)].copy()
    if cells.empty:
        raise Figure02ValidationError(f"Panel C File_ID is absent from the H5AD: {file_id}")
    cells["File_ID"] = cells["File_ID"].astype(str)
    cells["ID"] = pd.to_numeric(cells["ID"], errors="raise").astype(np.int64)
    if cells[truth_column].isna().any():
        raise Figure02ValidationError("Panel C tissue region has missing reference labels")
    cells[truth_column] = cells[truth_column].astype(str)
    cells = cells.sort_values("ID", kind="stable").reset_index(drop=True)
    _validate_unique_keys(cells, "Panel C H5AD subset")

    expected_cell_count = int(region["expected_cells"])
    if len(cells) != expected_cell_count:
        raise Figure02ValidationError(
            f"Panel C tissue region has {len(cells):,} cells; expected {expected_cell_count:,}"
        )
    if set(cells["File_ID"]) != {file_id}:
        raise Figure02ValidationError("Panel C tissue region contains unexpected File_ID values")

    numeric_coordinates = cells.loc[:, coordinate_columns].apply(pd.to_numeric, errors="raise")
    if numeric_coordinates.isna().any().any() or not np.isfinite(
        numeric_coordinates.to_numpy(dtype=float)
    ).all():
        raise Figure02ValidationError("Panel C tissue region has missing or non-finite coordinates")
    cells.loc[:, coordinate_columns] = numeric_coordinates

    observed_counts = {
        str(label): int(count)
        for label, count in cells[truth_column].value_counts(sort=False).sort_index().items()
    }
    expected_counts = {
        str(label): int(count) for label, count in labels_config["expected_counts"].items()
    }
    if observed_counts != expected_counts:
        raise Figure02ValidationError(
            "Panel C raw-label counts differ from the declared contract: "
            f"observed={observed_counts}, expected={expected_counts}"
        )
    if len(observed_counts) != int(labels_config["expected_label_count"]):
        raise Figure02ValidationError(
            "Panel C label count differs from the declared contract: "
            f"observed={len(observed_counts)}, expected={int(labels_config['expected_label_count'])}"
        )

    expected_bounds = panel["coordinates"]["expected_bounds"]
    for column in coordinate_columns:
        observed_bounds = (float(cells[column].min()), float(cells[column].max()))
        declared_bounds = tuple(float(value) for value in expected_bounds[column])
        if not np.allclose(observed_bounds, declared_bounds, rtol=0.0, atol=1e-9):
            raise Figure02ValidationError(
                f"Panel C {column} bounds differ from the declared contract: "
                f"observed={observed_bounds}, expected={declared_bounds}"
            )

    return PanelCData(
        cells=cells,
        source_cell_count=len(cells),
        cell_type_counts=observed_counts,
    )


def _validate_panel_d_data(
    cells: pd.DataFrame,
    features: np.ndarray,
    file_ids: Sequence[str],
    expected_cells: int,
    expected_cells_by_file_id: Mapping[str, int],
    features_config: Mapping[str, Any],
) -> None:
    truth_column = str(features_config["truth_column"])
    _validate_b004_observations(
        cells,
        file_ids,
        expected_cells,
        expected_cells_by_file_id,
        truth_column,
    )
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


def _load_method_assignments_for_keys(
    keys: pd.DataFrame,
    method_configs: Mapping[str, Any],
    *,
    data_root: Path,
) -> dict[str, pd.DataFrame]:
    """Load configured method assignments for an exact, ordered B004 key set."""
    required_key_columns = {"File_ID", "ID"}
    if missing := required_key_columns.difference(keys.columns):
        raise Figure02ValidationError(
            f"Requested method-assignment keys are missing columns: {sorted(missing)}"
        )
    keys = keys.loc[:, ["File_ID", "ID"]].copy()
    keys["File_ID"] = keys["File_ID"].astype(str)
    keys["ID"] = pd.to_numeric(keys["ID"], errors="raise").astype(np.int64)
    _validate_unique_keys(keys, "requested method-assignment keys")

    assignments: dict[str, pd.DataFrame] = {}
    for method_name, method_config in method_configs.items():
        artifact_path = _resolve_assignment_path(method_name, method_config, data_root=data_root)
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
    return _load_method_assignments_for_keys(
        data.cells[["File_ID", "ID"]],
        panel["clustering_methods"],
        data_root=root,
    )


def _weighted_f1_by_reference_class(
    region: pd.DataFrame,
    *,
    truth_column: str,
    cluster_column: str,
) -> float:
    """Compute the historical Panel E regional weighted-F1 statistic.

    Cluster-to-reference mappings are deliberately made inside this region.
    ``value_counts().index[0]`` reproduces the legacy mode-selection behavior
    for tied cluster majorities using the fixed H5AD observation order.  The
    attached Methods text does not otherwise specify a tie rule.
    """
    majority_by_cluster = (
        region.groupby(cluster_column, sort=True)[truth_column]
        .agg(lambda labels: labels.value_counts(sort=True).index[0])
    )
    predicted = region[cluster_column].map(majority_by_cluster)
    if predicted.isna().any():
        raise Figure02ValidationError("A Panel E cluster could not be assigned a majority reference label")

    weighted_sum = 0.0
    weight_total = 0
    for cell_type, cell_type_rows in region.groupby(truth_column, sort=False):
        true_type = str(cell_type)
        predicted_for_type = predicted.loc[cell_type_rows.index]
        true_for_type = cell_type_rows[truth_column]
        true_positive = int(((true_for_type == true_type) & (predicted_for_type == true_type)).sum())
        false_negative = int(((true_for_type == true_type) & (predicted_for_type != true_type)).sum())
        false_positive = int(((region[truth_column] != true_type) & (predicted == true_type)).sum())
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
        weight = len(cell_type_rows)
        weighted_sum += f1 * weight
        weight_total += weight
    if weight_total == 0:
        raise Figure02ValidationError("Panel E region has no reference cells after exclusions")
    return float(weighted_sum / weight_total)


def load_panel_e_metrics(
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> PanelEData:
    """Load H5AD labels and calculate the configured per-region weighted F1 values."""
    config = dict(config or load_figure_config())
    panel = config["panel_e"]
    cohort = panel["cohort"]
    evaluation = panel["evaluation"]
    truth_column = str(evaluation["truth_column"])
    root = (
        Path(data_root).expanduser().resolve()
        if data_root
        else resolve_data_root(config, panel_key="panel_e")
    )
    h5ad_path = root / str(panel["data"]["h5ad_filename"])
    file_ids = tuple(str(file_id) for file_id in cohort["file_ids"])

    import anndata as ad

    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        required_obs = {"File_ID", "ID", truth_column}
        missing_obs = required_obs.difference(adata.obs.columns)
        if missing_obs:
            raise Figure02ValidationError(
                f"{h5ad_path.name} is missing required obs columns: {sorted(missing_obs)}"
            )
        observed = adata.obs.loc[:, ["File_ID", "ID", truth_column]].copy()
    finally:
        adata.file.close()

    # Preserve H5AD observation order.  It is part of the frozen source and
    # therefore makes the legacy tied-majority behavior reproducible.
    cells = observed.loc[observed["File_ID"].astype(str).isin(file_ids)].copy()
    cells["File_ID"] = cells["File_ID"].astype(str)
    cells["ID"] = pd.to_numeric(cells["ID"], errors="raise").astype(np.int64)
    if cells[truth_column].isna().any():
        raise Figure02ValidationError("Panel E H5AD subset has missing reference labels")
    cells[truth_column] = cells[truth_column].astype(str)
    _validate_b004_observations(
        cells,
        file_ids,
        int(cohort["expected_cells"]),
        cohort["expected_cells_by_file_id"],
        truth_column,
    )

    excluded_labels = [str(label) for label in evaluation["excluded_labels"]]
    raw_counts = cells[truth_column].value_counts(sort=True)
    missing_excluded = sorted(set(excluded_labels).difference(raw_counts.index.astype(str)))
    if missing_excluded:
        raise Figure02ValidationError(
            f"Configured Panel E exclusions are absent from the B004 labels: {missing_excluded}"
        )
    excluded_counts = {label: int(raw_counts.loc[label]) for label in excluded_labels}
    expected_excluded_counts = {
        str(label): int(count)
        for label, count in evaluation["expected_excluded_counts"].items()
    }
    if excluded_counts != expected_excluded_counts:
        raise Figure02ValidationError(
            "Panel E excluded-label counts differ from the declared contract: "
            f"observed={excluded_counts}, expected={expected_excluded_counts}"
        )

    method_source_panel = str(panel["clustering_source_panel"])
    if method_source_panel not in config:
        raise Figure02ValidationError(
            f"Panel E clustering source panel is absent from the configuration: {method_source_panel!r}"
        )
    method_configs = config[method_source_panel].get("clustering_methods")
    if not isinstance(method_configs, Mapping):
        raise Figure02ValidationError(
            f"Panel E clustering source panel has no clustering_methods mapping: {method_source_panel!r}"
        )
    method_specs = panel["methods"]
    method_keys = [str(spec["key"]) for spec in method_specs]
    if len(set(method_keys)) != len(method_keys) or set(method_keys) != set(method_configs):
        raise Figure02ValidationError(
            "Panel E method specifications differ from the source assignment configuration: "
            f"panel_e={method_keys}, source={list(method_configs)}"
        )
    assignments = _load_method_assignments_for_keys(
        cells[["File_ID", "ID"]], method_configs, data_root=root
    )

    evaluation_cells = cells.loc[
        ~cells[truth_column].isin(excluded_labels), ["File_ID", "ID", truth_column]
    ].copy()
    evaluation_cells["evaluation_label"] = evaluation_cells[truth_column].replace(
        {str(source): str(target) for source, target in evaluation["harmonization_map"].items()}
    )
    if evaluation_cells["evaluation_label"].isna().any():
        raise Figure02ValidationError("Panel E harmonization produced missing evaluation labels")
    if len(evaluation_cells) != int(evaluation["expected_evaluation_cells"]):
        raise Figure02ValidationError(
            "Panel E evaluation-cell total differs from the declared contract: "
            f"observed={len(evaluation_cells):,}, "
            f"expected={int(evaluation['expected_evaluation_cells']):,}"
        )
    evaluation_class_count = int(evaluation_cells["evaluation_label"].nunique())
    if evaluation_class_count != int(evaluation["expected_evaluation_class_count"]):
        raise Figure02ValidationError(
            "Panel E evaluation-class count differs from the declared contract: "
            f"observed={evaluation_class_count}, "
            f"expected={int(evaluation['expected_evaluation_class_count'])}"
        )

    scored_cells = evaluation_cells[["File_ID", "ID", "evaluation_label"]].copy()
    for method_key in method_keys:
        scored_cells = scored_cells.merge(
            assignments[method_key][["File_ID", "ID", "cluster"]].rename(
                columns={"cluster": method_key}
            ),
            on=["File_ID", "ID"],
            how="left",
            validate="one_to_one",
            sort=False,
        )
        if scored_cells[method_key].isna().any():
            missing = int(scored_cells[method_key].isna().sum())
            raise Figure02ValidationError(
                f"Panel E {method_key} assignments are missing {missing:,} non-Noise cells"
            )

    cluster_counts = {method_key: int(scored_cells[method_key].nunique()) for method_key in method_keys}
    expected_cluster_counts = {
        str(method_key): int(method_config["expected_clusters"])
        for method_key, method_config in method_configs.items()
    }
    if cluster_counts != expected_cluster_counts:
        raise Figure02ValidationError(
            "Panel E cluster counts differ from the selected method assignments: "
            f"observed={cluster_counts}, expected={expected_cluster_counts}"
        )

    rows: list[dict[str, Any]] = []
    expected_scores = panel["expected_scores"]
    for file_id in file_ids:
        region = scored_cells.loc[scored_cells["File_ID"].eq(file_id)].copy()
        if region.empty:
            raise Figure02ValidationError(f"Panel E File_ID is empty after filtering: {file_id}")
        expected_region = expected_scores.get(file_id)
        if not isinstance(expected_region, Mapping):
            raise Figure02ValidationError(f"Panel E has no expected score contract for {file_id}")
        expected_cell_count = int(expected_region["n_cells"])
        if len(region) != expected_cell_count:
            raise Figure02ValidationError(
                f"Panel E {file_id} has {len(region):,} evaluation cells; expected {expected_cell_count:,}"
            )
        for method_spec in method_specs:
            method_key = str(method_spec["key"])
            method_label = str(method_spec["label"])
            weighted_f1 = _weighted_f1_by_reference_class(
                region,
                truth_column="evaluation_label",
                cluster_column=method_key,
            )
            expected_score = float(expected_region[method_label])
            if not np.isclose(weighted_f1, expected_score, rtol=0.0, atol=1e-12):
                raise Figure02ValidationError(
                    f"Panel E {file_id} {method_label} weighted F1 differs from the declared contract: "
                    f"observed={weighted_f1:.16f}, expected={expected_score:.16f}"
                )
            rows.append(
                {
                    "region": file_id,
                    "method": method_label,
                    "weighted_f1": weighted_f1,
                    "n_cells": len(region),
                }
            )

    scores = pd.DataFrame(rows)
    if len(scores) != len(file_ids) * len(method_specs):
        raise Figure02ValidationError("Panel E score table has an unexpected number of regional observations")
    return PanelEData(
        scores=scores,
        source_cell_count=len(cells),
        evaluation_cell_count=len(evaluation_cells),
        excluded_counts=excluded_counts,
        evaluation_class_count=evaluation_class_count,
        cluster_counts=cluster_counts,
    )


def _load_b004_observation_subset(
    config: Mapping[str, Any],
    *,
    panel_key: str,
    required_columns: Sequence[str],
    data_root: str | Path | None = None,
) -> pd.DataFrame:
    """Read an ordered B004 H5AD-observation subset without loading ``X``.

    The H5AD observation order is intentionally retained.  The legacy figure
    scripts used ``value_counts().idxmax()`` to resolve cluster-majority ties,
    so changing this order could silently change a tied label assignment.
    """
    source_panel = _source_panel_config(config, panel_key, "data_source_panel")
    cohort_panel = _source_panel_config(config, panel_key, "cohort_source_panel")
    if "data" not in source_panel or "cohort" not in cohort_panel:
        raise Figure02ValidationError(f"{panel_key} has no resolvable data/cohort contract")
    data_config = source_panel["data"]
    cohort = cohort_panel["cohort"]
    root = (
        Path(data_root).expanduser().resolve()
        if data_root
        else resolve_data_root(config, panel_key=panel_key)
    )
    h5ad_path = root / str(data_config["h5ad_filename"])
    file_ids = tuple(str(file_id) for file_id in cohort["file_ids"])
    columns = list(dict.fromkeys(str(column) for column in required_columns))
    required = {"File_ID", "ID", *columns}

    import anndata as ad

    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        missing = required.difference(adata.obs.columns)
        if missing:
            raise Figure02ValidationError(
                f"{h5ad_path.name} is missing required obs columns: {sorted(missing)}"
            )
        observed = adata.obs.loc[:, ["File_ID", "ID", *columns]].copy()
    finally:
        adata.file.close()

    cells = observed.loc[observed["File_ID"].astype(str).isin(file_ids)].copy()
    cells["File_ID"] = cells["File_ID"].astype(str)
    cells["ID"] = pd.to_numeric(cells["ID"], errors="raise").astype(np.int64)
    for column in columns:
        if cells[column].isna().any():
            raise Figure02ValidationError(f"{panel_key} H5AD subset has missing {column!r} values")
    truth_column = next(
        (column for column in columns if column.endswith("cell_type_update")), None
    )
    # The common Figure 2 truth label has a fixed name; retain a clear error if
    # a future panel passes different required columns by mistake.
    if truth_column is None and "cell_type_update" in columns:
        truth_column = "cell_type_update"
    if truth_column is not None:
        cells[truth_column] = cells[truth_column].astype(str)
        _validate_b004_observations(
            cells,
            file_ids,
            int(cohort["expected_cells"]),
            cohort["expected_cells_by_file_id"],
            truth_column,
        )
    else:
        _validate_unique_keys(cells, f"{panel_key} B004 H5AD subset")
    return cells


def _panel_method_specs(
    config: Mapping[str, Any],
    panel_key: str,
) -> tuple[list[tuple[str, str]], Mapping[str, Any]]:
    """Return a panel's display-order method specs and selected assignments."""
    panel = config[panel_key]
    source_key = str(panel.get("clustering_source_panel", "panel_d"))
    if source_key not in config:
        raise Figure02ValidationError(
            f"{panel_key} refers to absent clustering_source_panel={source_key!r}"
        )
    method_configs = config[source_key].get("clustering_methods")
    if not isinstance(method_configs, Mapping):
        raise Figure02ValidationError(f"{source_key} has no clustering_methods mapping")
    method_specs = [
        (str(spec["key"]), str(spec["label"]))
        for spec in panel.get("methods", [])
    ]
    if not method_specs:
        raise Figure02ValidationError(f"{panel_key} has no method display specifications")
    method_keys = [key for key, _ in method_specs]
    if len(set(method_keys)) != len(method_keys) or set(method_keys) != set(method_configs):
        raise Figure02ValidationError(
            f"{panel_key} method specifications do not match {source_key} assignments"
        )
    return method_specs, method_configs


def _load_panel_method_assignments(
    config: Mapping[str, Any],
    *,
    panel_key: str,
    keys: pd.DataFrame,
    data_root: str | Path | None = None,
) -> tuple[list[tuple[str, str]], dict[str, pd.DataFrame]]:
    """Load one panel's selected method assignments for exact H5AD keys."""
    method_specs, method_configs = _panel_method_specs(config, panel_key)
    root = (
        Path(data_root).expanduser().resolve()
        if data_root
        else resolve_data_root(config, panel_key=panel_key)
    )
    assignments = _load_method_assignments_for_keys(keys, method_configs, data_root=root)
    return method_specs, assignments


def _evaluation_config_for_panel(
    config: Mapping[str, Any], panel_key: str
) -> Mapping[str, Any]:
    """Resolve a panel's shared 20-class non-Noise evaluation contract."""
    source = _source_panel_config(config, panel_key, "evaluation_source_panel")
    evaluation = source.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise Figure02ValidationError(f"{panel_key} has no resolvable evaluation contract")
    return evaluation


def _prepare_harmonized_evaluation_cells(
    cells: pd.DataFrame,
    evaluation: Mapping[str, Any],
    *,
    panel_key: str,
) -> tuple[pd.DataFrame, dict[str, int], int]:
    """Exclude Noise and harmonize raw reference labels to the 20-class set."""
    truth_column = str(evaluation["truth_column"])
    if truth_column not in cells:
        raise Figure02ValidationError(f"{panel_key} cells are missing {truth_column!r}")
    excluded_labels = [str(label) for label in evaluation["excluded_labels"]]
    raw_counts = cells[truth_column].astype(str).value_counts(sort=True)
    missing_excluded = sorted(set(excluded_labels).difference(raw_counts.index.astype(str)))
    if missing_excluded:
        raise Figure02ValidationError(
            f"{panel_key} exclusions are absent from the B004 labels: {missing_excluded}"
        )
    excluded_counts = {label: int(raw_counts.loc[label]) for label in excluded_labels}
    expected_excluded_counts = {
        str(label): int(count)
        for label, count in evaluation["expected_excluded_counts"].items()
    }
    if excluded_counts != expected_excluded_counts:
        raise Figure02ValidationError(
            f"{panel_key} excluded counts differ from the declared contract: "
            f"observed={excluded_counts}, expected={expected_excluded_counts}"
        )
    evaluation_cells = cells.loc[
        ~cells[truth_column].astype(str).isin(excluded_labels), ["File_ID", "ID", truth_column]
    ].copy()
    evaluation_cells["evaluation_label"] = evaluation_cells[truth_column].astype(str).replace(
        {
            str(source): str(target)
            for source, target in evaluation["harmonization_map"].items()
        }
    )
    if evaluation_cells["evaluation_label"].isna().any():
        raise Figure02ValidationError(f"{panel_key} harmonization produced missing labels")
    expected_cells = int(evaluation["expected_evaluation_cells"])
    if len(evaluation_cells) != expected_cells:
        raise Figure02ValidationError(
            f"{panel_key} has {len(evaluation_cells):,} evaluation cells; expected {expected_cells:,}"
        )
    class_count = int(evaluation_cells["evaluation_label"].nunique())
    expected_class_count = int(evaluation["expected_evaluation_class_count"])
    if class_count != expected_class_count:
        raise Figure02ValidationError(
            f"{panel_key} has {class_count} evaluation classes; expected {expected_class_count}"
        )
    return evaluation_cells, excluded_counts, class_count


def _load_scored_evaluation_cells(
    config: Mapping[str, Any],
    *,
    panel_key: str,
    data_root: str | Path | None = None,
) -> tuple[pd.DataFrame, int, dict[str, int], int, dict[str, int], list[tuple[str, str]]]:
    """Load H5AD truth and selected clusters for a non-Noise 20-class panel."""
    evaluation = _evaluation_config_for_panel(config, panel_key)
    truth_column = str(evaluation["truth_column"])
    cells = _load_b004_observation_subset(
        config,
        panel_key=panel_key,
        required_columns=[truth_column],
        data_root=data_root,
    )
    evaluation_cells, excluded_counts, class_count = _prepare_harmonized_evaluation_cells(
        cells, evaluation, panel_key=panel_key
    )
    method_specs, assignments = _load_panel_method_assignments(
        config,
        panel_key=panel_key,
        keys=cells[["File_ID", "ID"]],
        data_root=data_root,
    )
    scored = evaluation_cells[["File_ID", "ID", "evaluation_label"]].copy()
    for method_key, _ in method_specs:
        scored = scored.merge(
            assignments[method_key][["File_ID", "ID", "cluster"]].rename(
                columns={"cluster": method_key}
            ),
            on=["File_ID", "ID"],
            how="left",
            validate="one_to_one",
            sort=False,
        )
        if scored[method_key].isna().any():
            raise Figure02ValidationError(f"{panel_key} has missing {method_key} assignments")
    cluster_counts = {method_key: int(scored[method_key].nunique()) for method_key, _ in method_specs}
    expected_cluster_counts = {
        method_key: int(config[str(config[panel_key].get("clustering_source_panel", "panel_d"))]
                        ["clustering_methods"][method_key]["expected_clusters"])
        for method_key, _ in method_specs
    }
    if cluster_counts != expected_cluster_counts:
        raise Figure02ValidationError(
            f"{panel_key} cluster counts differ from selected assignments: "
            f"observed={cluster_counts}, expected={expected_cluster_counts}"
        )
    return (
        scored,
        len(cells),
        excluded_counts,
        class_count,
        cluster_counts,
        method_specs,
    )


def _majority_predictions(
    cells: pd.DataFrame,
    *,
    truth_column: str,
    method_key: str,
) -> pd.Series:
    """Return cluster-majority reference predictions in the preserved input order."""
    majority_by_cluster = (
        cells.groupby(method_key, sort=True)[truth_column]
        .agg(lambda labels: labels.value_counts(sort=True).index[0])
    )
    predicted = cells[method_key].map(majority_by_cluster)
    if predicted.isna().any():
        raise Figure02ValidationError(f"No majority reference label for a {method_key} cluster")
    return predicted.astype(str)


def load_panel_fh_metrics(
    config: Mapping[str, Any] | None = None,
    *,
    panel_key: str,
    data_root: str | Path | None = None,
) -> PanelCellTypeMetrics:
    """Compute Panel F/H global F1 and per-reference-class purity values.

    The screenshot's legacy "purity" is classwise recall: the fraction of
    cells of a reference type recovered by a globally majority-mapped cluster.
    It is intentionally not cluster purity.
    """
    config = dict(config or load_figure_config())
    if panel_key not in {"panel_f", "panel_h"}:
        raise Figure02ValidationError(f"Panel F/H metrics do not support {panel_key!r}")
    panel = config[panel_key]
    scored, source_count, excluded_counts, class_count, cluster_counts, method_specs = (
        _load_scored_evaluation_cells(config, panel_key=panel_key, data_root=data_root)
    )
    row_order = [str(label) for label in panel["row_order"]]
    observed_labels = set(scored["evaluation_label"].astype(str))
    if set(row_order) != observed_labels or len(row_order) != len(observed_labels):
        raise Figure02ValidationError(
            f"{panel_key} row_order differs from the observed evaluation labels"
        )
    predictions = {
        method_key: _majority_predictions(
            scored, truth_column="evaluation_label", method_key=method_key
        )
        for method_key, _ in method_specs
    }
    rows: list[dict[str, Any]] = []
    truth = scored["evaluation_label"].astype(str)
    for cell_type in row_order:
        truth_mask = truth.eq(cell_type)
        n_cells = int(truth_mask.sum())
        record: dict[str, Any] = {"cell_type": cell_type, "n_cells": n_cells}
        for method_key, method_label in method_specs:
            predicted = predictions[method_key]
            true_positive = int((truth_mask & predicted.eq(cell_type)).sum())
            false_negative = int((truth_mask & ~predicted.eq(cell_type)).sum())
            false_positive = int((~truth_mask & predicted.eq(cell_type)).sum())
            precision = (
                true_positive / (true_positive + false_positive)
                if true_positive + false_positive
                else 0.0
            )
            recall = (
                true_positive / (true_positive + false_negative)
                if true_positive + false_negative
                else 0.0
            )
            record[f"{method_label}_f1"] = (
                2.0 * precision * recall / (precision + recall)
                if precision + recall
                else 0.0
            )
            record[f"{method_label}_purity"] = recall
        rows.append(record)
    metrics = pd.DataFrame(rows)
    for suffix in ("f1", "purity"):
        columns = [f"{label}_{suffix}" for _, label in method_specs]
        metrics[f"mean_{suffix}"] = metrics.loc[:, columns].mean(axis=1)
    return PanelCellTypeMetrics(
        metrics=metrics,
        source_cell_count=source_count,
        evaluation_cell_count=len(scored),
        excluded_counts=excluded_counts,
        evaluation_class_count=class_count,
        cluster_counts=cluster_counts,
    )


def load_panel_g_metrics(
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> PanelGData:
    """Compute the eight regional cluster-majority purity observations for G."""
    config = dict(config or load_figure_config())
    panel = config["panel_g"]
    scored, source_count, excluded_counts, class_count, cluster_counts, method_specs = (
        _load_scored_evaluation_cells(config, panel_key="panel_g", data_root=data_root)
    )
    cohort_source = _source_panel_config(config, "panel_g", "cohort_source_panel")
    file_ids = [str(file_id) for file_id in cohort_source["cohort"]["file_ids"]]
    rows: list[dict[str, Any]] = []
    for file_id in file_ids:
        region = scored.loc[scored["File_ID"].eq(file_id)].copy()
        if region.empty:
            raise Figure02ValidationError(f"Panel G has no evaluation cells for {file_id}")
        for method_key, method_label in method_specs:
            predicted = _majority_predictions(
                region, truth_column="evaluation_label", method_key=method_key
            )
            rows.append(
                {
                    "region": file_id,
                    "method": method_label,
                    "cell_purity": float(
                        predicted.eq(region["evaluation_label"].astype(str)).mean()
                    ),
                    "n_cells": len(region),
                }
            )
    scores = pd.DataFrame(rows)
    if len(scores) != len(file_ids) * len(method_specs):
        raise Figure02ValidationError("Panel G score table has an unexpected number of rows")
    return PanelGData(
        scores=scores,
        source_cell_count=source_count,
        evaluation_cell_count=len(scored),
        excluded_counts=excluded_counts,
        evaluation_class_count=class_count,
        cluster_counts=cluster_counts,
    )


def load_panel_i_data(
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> PanelIData:
    """Summarize H5AD X markers in globally CD8+ T-majority clusters for I."""
    config = dict(config or load_figure_config())
    panel = config["panel_i"]
    truth_column = str(panel["truth_column"])
    raw_cells = _load_b004_observation_subset(
        config,
        panel_key="panel_i",
        required_columns=[truth_column],
        data_root=data_root,
    )
    method_specs, assignments = _load_panel_method_assignments(
        config,
        panel_key="panel_i",
        keys=raw_cells[["File_ID", "ID"]],
        data_root=data_root,
    )
    labeled = raw_cells[["File_ID", "ID", truth_column]].copy()
    selected_keys: dict[str, pd.DataFrame] = {}
    selected_cluster_counts: dict[str, int] = {}
    target_cell_type = str(panel["target_cell_type"])
    for method_key, method_label in method_specs:
        joined = labeled.merge(
            assignments[method_key][["File_ID", "ID", "cluster"]],
            on=["File_ID", "ID"],
            how="left",
            validate="one_to_one",
            sort=False,
        )
        if joined["cluster"].isna().any():
            raise Figure02ValidationError(f"Panel I has missing {method_key} assignments")
        predicted = _majority_predictions(
            joined.rename(columns={"cluster": method_key}),
            truth_column=truth_column,
            method_key=method_key,
        )
        selected = joined.loc[predicted.eq(target_cell_type), ["File_ID", "ID", "cluster"]].copy()
        if selected.empty:
            raise Figure02ValidationError(
                f"Panel I found no {target_cell_type!r} cells for {method_label}"
            )
        selected_keys[method_label] = selected[["File_ID", "ID"]]
        selected_cluster_counts[method_label] = int(selected["cluster"].nunique())

    # Panel D's validated loader gives aligned 48-feature vectors. Panel I is
    # intentionally limited to the 45 native H5AD X markers shown in the
    # supplied dot plot, not the three auxiliary H5AD obs markers used by D.
    panel_d_data = load_b004_h5ad(config, data_root=data_root)
    auxiliary_marker_count = len(config["panel_d"]["features"]["h5ad_obs_markers"])
    marker_names = tuple(panel_d_data.marker_names[auxiliary_marker_count:])
    expected_marker_count = int(panel["expected_marker_count"])
    if len(marker_names) != expected_marker_count:
        raise Figure02ValidationError(
            f"Panel I has {len(marker_names)} H5AD X markers; expected {expected_marker_count}"
        )
    expected_markers = tuple(str(marker) for marker in panel["marker_order"])
    if marker_names != expected_markers:
        raise Figure02ValidationError("Panel I H5AD marker order differs from the declared contract")
    feature_matrix = panel_d_data.features[:, auxiliary_marker_count:]
    feature_key_index = pd.MultiIndex.from_frame(panel_d_data.cells[["File_ID", "ID"]])
    rows: list[dict[str, Any]] = []
    selected_cell_counts: dict[str, int] = {}
    for _, method_label in method_specs:
        keys = selected_keys[method_label]
        indexer = feature_key_index.get_indexer(pd.MultiIndex.from_frame(keys))
        if (indexer < 0).any():
            raise Figure02ValidationError(f"Panel I selected keys are absent from H5AD features: {method_label}")
        values = feature_matrix[indexer]
        selected_cell_counts[method_label] = int(values.shape[0])
        means = values.mean(axis=0)
        fractions = 100.0 * (values > float(panel["expression_threshold"])).mean(axis=0)
        rows.extend(
            {
                "method": method_label,
                "marker": marker,
                "mean_expression": float(mean),
                "fraction_cells_pct": float(fraction),
                "n_selected_cells": int(values.shape[0]),
            }
            for marker, mean, fraction in zip(marker_names, means, fractions, strict=True)
        )
    summaries = pd.DataFrame(rows)
    summaries["scaled_mean_expression"] = 0.0
    for marker in marker_names:
        marker_mask = summaries["marker"].eq(marker)
        values = summaries.loc[marker_mask, "mean_expression"]
        low, high = float(values.min()), float(values.max())
        if high > low:
            summaries.loc[marker_mask, "scaled_mean_expression"] = (values - low) / (high - low)
    cluster_counts = {method_key: int(assignments[method_key]["cluster"].nunique()) for method_key, _ in method_specs}
    return PanelIData(
        summaries=summaries,
        marker_names=marker_names,
        source_cell_count=len(raw_cells),
        selected_cell_counts=selected_cell_counts,
        selected_cluster_counts=selected_cluster_counts,
        cluster_counts=cluster_counts,
    )


def load_panel_j_data(
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> PanelJData:
    """Load fixed TIFF-PIXIE low/high spatial agreement examples for Panel J."""
    config = dict(config or load_figure_config())
    panel = config["panel_j"]
    truth_column = str(panel["truth_column"])
    coordinate_columns = [str(column) for column in panel["coordinate_columns"]]
    if len(coordinate_columns) != 2:
        raise Figure02ValidationError("Panel J requires exactly two coordinate columns")
    raw_cells = _load_b004_observation_subset(
        config,
        panel_key="panel_j",
        required_columns=[truth_column, *coordinate_columns],
        data_root=data_root,
    )
    method_specs, assignments = _load_panel_method_assignments(
        config,
        panel_key="panel_j",
        keys=raw_cells[["File_ID", "ID"]],
        data_root=data_root,
    )
    labels = raw_cells[["File_ID", "ID", *coordinate_columns, truth_column]].copy()
    for method_key, method_label in method_specs:
        joined = raw_cells[["File_ID", "ID", truth_column]].merge(
            assignments[method_key][["File_ID", "ID", "cluster"]],
            on=["File_ID", "ID"],
            how="left",
            validate="one_to_one",
            sort=False,
        ).rename(columns={"cluster": method_key})
        labels[method_label] = _majority_predictions(
            joined, truth_column=truth_column, method_key=method_key
        ).to_numpy()
    labels = labels.rename(columns={truth_column: "Ground Truth"})
    excluded_labels = [str(label) for label in panel["excluded_labels"]]
    raw_counts = labels["Ground Truth"].astype(str).value_counts(sort=True)
    excluded_counts = {label: int(raw_counts.loc[label]) for label in excluded_labels}
    expected_excluded_counts = {
        str(label): int(count)
        for label, count in panel["expected_excluded_counts"].items()
    }
    if excluded_counts != expected_excluded_counts:
        raise Figure02ValidationError(
            f"Panel J excluded counts differ from the contract: {excluded_counts}"
        )
    plotted = labels.loc[~labels["Ground Truth"].astype(str).isin(excluded_labels)].copy()
    example_rows: list[dict[str, Any]] = []
    for example in panel["examples"]:
        example_name = str(example["name"])
        file_id = str(example["file_id"])
        x0, x1, y0, y1 = (float(example[key]) for key in ("x0", "x1", "y0", "y1"))
        region = plotted.loc[
            plotted["File_ID"].eq(file_id)
            & plotted[coordinate_columns[0]].between(x0, x1)
            & plotted[coordinate_columns[1]].between(y0, y1)
        ]
        if len(region) != int(example["expected_cells"]):
            raise Figure02ValidationError(
                f"Panel J {example_name} has {len(region)} cells; expected {example['expected_cells']}"
            )
        agreement_columns = [method_label for _, method_label in method_specs]
        agreement_counts = sum(
            region[method_label].astype(str).eq(region["Ground Truth"].astype(str)).astype(int)
            for method_label in agreement_columns
        )
        example_rows.append(
            {
                "example": example_name,
                "file_id": file_id,
                "x0": x0,
                "x1": x1,
                "y0": y0,
                "y1": y1,
                "n_cells": len(region),
                "mean_method_agreement": float((agreement_counts / len(agreement_columns)).mean()),
                "any_disagreement_rate": float((agreement_counts < len(agreement_columns)).mean()),
            }
        )
    examples = pd.DataFrame(example_rows)
    if {"Low Agreement", "High Agreement"}.issubset(set(examples["example"])):
        low_rate = float(examples.loc[examples["example"].eq("Low Agreement"), "any_disagreement_rate"].iloc[0])
        high_rate = float(examples.loc[examples["example"].eq("High Agreement"), "any_disagreement_rate"].iloc[0])
        if high_rate >= low_rate:
            raise Figure02ValidationError("Panel J high-agreement window is not more concordant than low-agreement")
    cluster_counts = {method_key: int(assignments[method_key]["cluster"].nunique()) for method_key, _ in method_specs}
    return PanelJData(
        cells=plotted,
        examples=examples,
        source_cell_count=len(raw_cells),
        plotted_cell_count=len(plotted),
        excluded_counts=excluded_counts,
        cluster_counts=cluster_counts,
    )


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


def _file_sha256(path: Path) -> str:
    """Return a SHA-256 digest without loading an entire file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_color_map(
    labels: Sequence[str],
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
    panel_key: str = "panel_d",
) -> dict[str, str]:
    """Load the cell-type color key, with a deterministic fallback."""
    config = dict(config or load_figure_config())
    root = (
        Path(data_root).expanduser().resolve()
        if data_root
        else resolve_data_root(config, panel_key=panel_key)
    )
    filename = str(config[panel_key]["style"]["color_map_filename"])
    # The tracked snapshot is the canonical visual key. A local same-named
    # file is only a fallback for a clone made before the snapshot is present.
    path = REPOSITORY_ROOT / "configs" / filename
    if not path.is_file():
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


def _save_figure_via_local_tempfile(
    figure: Any,
    output_path: str | Path,
    **savefig_kwargs: Any,
) -> Path:
    """Save an artifact locally before atomically publishing it to the output path.

    Large rasterized PDFs can make many small writes while Matplotlib embeds
    fonts. Rendering first under the local temporary directory avoids exposing
    a partial manuscript artifact when the output directory is file-provider
    backed. ``os.replace`` publishes the complete result atomically whenever
    both paths share a filesystem; the cross-device fallback is still scoped to
    the declared generated-artifact path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{output_path.stem}.", suffix=output_path.suffix, dir=tempfile.gettempdir()
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        figure.savefig(temporary_path, **savefig_kwargs)
        try:
            os.replace(temporary_path, output_path)
        except OSError as error:
            if error.errno != errno.EXDEV:
                raise
            shutil.copy2(temporary_path, output_path)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise Figure02ValidationError(f"Figure export was not written: {output_path}")
    finally:
        temporary_path.unlink(missing_ok=True)
    return output_path


def render_panel_b(
    counts: pd.DataFrame,
    output_path: str | Path,
    *,
    color_map: Mapping[str, str] | None = None,
    style: Mapping[str, Any] | None = None,
    dpi: int = 300,
) -> Path:
    """Render Panel B as the supplied raw-label count distribution."""
    import matplotlib.pyplot as plt
    import numpy as np

    required_columns = {"Cell Type", "Cell Count"}
    if missing := required_columns.difference(counts.columns):
        raise Figure02ValidationError(f"Panel B count table is missing columns: {sorted(missing)}")
    if counts.empty:
        raise Figure02ValidationError("Panel B count table is empty")
    if not counts["Cell Count"].is_monotonic_decreasing:
        raise Figure02ValidationError("Panel B count table must be sorted by descending cell count")

    style = dict(style or {})
    figure_size = tuple(float(value) for value in style.get("figure_size_inches", (12.0, 6.0)))
    if len(figure_size) != 2:
        raise Figure02ValidationError("Panel B figure_size_inches must have two values")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels = counts["Cell Type"].astype(str)
    colors = dict(color_map or default_color_map(labels))
    bar_colors = labels.map(colors).fillna("#808080").to_numpy()
    x_positions = np.arange(len(counts))

    fig, axis = plt.subplots(figsize=figure_size)
    fig.subplots_adjust(
        left=float(style.get("left", 0.18)),
        right=float(style.get("right", 0.99)),
        bottom=float(style.get("bottom", 0.58)),
        top=float(style.get("top", 0.96)),
    )
    axis.bar(
        x_positions,
        counts["Cell Count"].to_numpy(),
        color=bar_colors,
        edgecolor=str(style.get("bar_edgecolor", "#ffffff")),
        linewidth=float(style.get("bar_linewidth", 0.3)),
        width=float(style.get("bar_width", 0.8)),
    )
    axis.set_xticks(x_positions)
    axis.set_xticklabels(
        labels,
        rotation=float(style.get("x_tick_label_rotation", 90)),
        fontsize=float(style.get("x_tick_label_fontsize", 14)),
    )
    axis.set_xlabel(
        str(style.get("x_axis_label", "Cell Type")),
        fontsize=float(style.get("axis_label_fontsize", 18)),
    )
    axis.set_ylabel(
        str(style.get("y_axis_label", "Cell Count")),
        fontsize=float(style.get("axis_label_fontsize", 18)),
    )
    axis.tick_params(axis="x", length=0)
    axis.tick_params(axis="y", labelsize=float(style.get("y_tick_label_fontsize", 14)))
    if "y_limit" in style:
        axis.set_ylim(0, float(style["y_limit"]))
    if "y_ticks" in style:
        axis.set_yticks([float(value) for value in style["y_ticks"]])
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    for spine_name in ("left", "bottom"):
        axis.spines[spine_name].set_color("#808080")
        axis.spines[spine_name].set_linewidth(0.8)
    fig.text(
        float(style.get("panel_label_x", 0.015)),
        float(style.get("panel_label_y", 0.95)),
        str(style.get("panel_label", "B")),
        fontsize=float(style.get("panel_label_fontsize", 36)),
        ha="left",
        va="top",
    )
    _save_figure_via_local_tempfile(fig, output_path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return output_path


def render_panel_c(
    cells: pd.DataFrame,
    output_path: str | Path,
    *,
    label_column: str,
    coordinate_columns: Sequence[str],
    color_map: Mapping[str, str] | None = None,
    style: Mapping[str, Any] | None = None,
    dpi: int = 300,
) -> Path:
    """Render the raw-label spatial tissue region shown in Panel C.

    The point styling matches the verified legacy tissue renderer: one group
    per raw ``cell_type_update`` label, 2-point markers, 0.8 alpha, equal
    spatial aspect, and no coordinate inversion or visible axes.
    """
    import matplotlib.pyplot as plt

    if len(coordinate_columns) != 2:
        raise Figure02ValidationError("Panel C rendering requires exactly two coordinate columns")
    x_column, y_column = (str(column) for column in coordinate_columns)
    required_columns = {x_column, y_column, label_column}
    if missing := required_columns.difference(cells.columns):
        raise Figure02ValidationError(f"Panel C data are missing columns: {sorted(missing)}")
    if cells.empty:
        raise Figure02ValidationError("Panel C data are empty")

    style = dict(style or {})
    figure_size = tuple(float(value) for value in style.get("figure_size_inches", (6.0, 6.7)))
    if len(figure_size) != 2:
        raise Figure02ValidationError("Panel C figure_size_inches must have two values")
    axes_position = tuple(float(value) for value in style.get("axes_position", (0.15, 0.10, 0.75, 0.75)))
    if len(axes_position) != 4:
        raise Figure02ValidationError("Panel C axes_position must have four values")

    labels = cells[label_column].astype(str)
    colors = dict(color_map or default_color_map(labels))
    fig = plt.figure(figsize=figure_size)
    axis = fig.add_axes(axes_position)
    # The explicit string conversion above intentionally gives the same
    # lexicographically ordered category layering as the verified legacy plot.
    for cell_type, group in cells.groupby(label_column, sort=True):
        axis.scatter(
            group[x_column],
            group[y_column],
            s=float(style.get("point_size", 2.0)),
            c=colors.get(str(cell_type), "#808080"),
            alpha=float(style.get("point_alpha", 0.8)),
            linewidths=0,
            rasterized=True,
        )
    axis.set_aspect("equal", adjustable="box")
    axis.axis("off")
    fig.text(
        float(style.get("panel_label_x", 0.03)),
        float(style.get("panel_label_y", 0.95)),
        str(style.get("panel_label", "C")),
        fontsize=float(style.get("panel_label_fontsize", 42)),
        ha="left",
        va="top",
    )
    fig.text(
        float(style.get("title_x", 0.55)),
        float(style.get("title_y", 0.93)),
        str(style.get("title", "A Ground Truth Tissue Region")),
        fontsize=float(style.get("title_fontsize", 20)),
        ha="center",
        va="top",
    )
    _save_figure_via_local_tempfile(fig, output_path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return Path(output_path)


def render_panel_e(
    scores: pd.DataFrame,
    output_path: str | Path,
    *,
    method_order: Sequence[str],
    region_order: Sequence[str],
    style: Mapping[str, Any] | None = None,
    dpi: int = 300,
) -> Path:
    """Render Panel E's regional weighted-F1 box-and-strip plot.

    Each point is one imaged B004 tissue region.  Boxplot whiskers therefore
    use Matplotlib's default 1.5-IQR definition, while every regional
    observation remains visible as a deterministic jittered point.
    """
    import matplotlib.pyplot as plt

    required_columns = {"region", "method", "weighted_f1", "n_cells"}
    if missing := required_columns.difference(scores.columns):
        raise Figure02ValidationError(f"Panel E score table is missing columns: {sorted(missing)}")
    if scores.empty:
        raise Figure02ValidationError("Panel E score table is empty")
    methods = [str(method) for method in method_order]
    regions = [str(region) for region in region_order]
    if set(scores["method"].astype(str)) != set(methods):
        raise Figure02ValidationError("Panel E score table methods differ from the configured display order")
    if set(scores["region"].astype(str)) != set(regions):
        raise Figure02ValidationError("Panel E score table regions differ from the configured display order")
    expected_rows = len(methods) * len(regions)
    if len(scores) != expected_rows:
        raise Figure02ValidationError(
            f"Panel E score table has {len(scores)} rows; expected {expected_rows}"
        )

    style = dict(style or {})
    figure_size = tuple(float(value) for value in style.get("figure_size_inches", (3.2, 3.4)))
    if len(figure_size) != 2:
        raise Figure02ValidationError("Panel E figure_size_inches must have two values")
    region_colors = {str(key): str(value) for key, value in style.get("region_colors", {}).items()}
    if set(region_colors) != set(regions):
        raise Figure02ValidationError("Panel E needs one configured point color for every region")

    plt.rcParams.update({"font.family": str(style.get("font_family", "Arial"))})
    fig, axis = plt.subplots(figsize=figure_size)
    fig.subplots_adjust(
        left=float(style.get("left", 0.22)),
        right=float(style.get("right", 0.98)),
        bottom=float(style.get("bottom", 0.18)),
        top=float(style.get("top", 0.96)),
    )
    positions = (
        np.arange(len(methods), dtype=float) * float(style.get("method_spacing", 0.85))
        + float(style.get("method_position_start", 1.0))
    )
    data_by_method = []
    points_by_method: list[pd.DataFrame] = []
    for method in methods:
        points = (
            scores.loc[scores["method"].astype(str).eq(method), ["region", "weighted_f1"]]
            .assign(region=lambda frame: frame["region"].astype(str))
            .set_index("region")
            .loc[regions]
            .reset_index()
        )
        data_by_method.append(points["weighted_f1"].to_numpy(dtype=float))
        points_by_method.append(points)

    box = axis.boxplot(
        data_by_method,
        positions=positions,
        patch_artist=True,
        widths=float(style.get("box_width", 0.48)),
        showfliers=False,
        medianprops={
            "color": str(style.get("box_edgecolor", "#111827")),
            "linewidth": float(style.get("median_linewidth", 1.2)),
        },
        boxprops={"linewidth": float(style.get("box_linewidth", 1.2))},
        whiskerprops={"linewidth": float(style.get("whisker_linewidth", 1.1))},
        capprops={"linewidth": float(style.get("cap_linewidth", 1.1))},
    )
    for patch in box["boxes"]:
        patch.set_facecolor(str(style.get("box_facecolor", "#E5E7EB")))
        patch.set_edgecolor(str(style.get("box_edgecolor", "#111827")))

    rng = np.random.default_rng(int(style.get("jitter_seed", 7)))
    for position, points in zip(positions, points_by_method, strict=True):
        jitter = rng.uniform(
            -float(style.get("jitter_half_width", 0.18)),
            float(style.get("jitter_half_width", 0.18)),
            size=len(points),
        )
        axis.scatter(
            np.full(len(points), position, dtype=float) + jitter,
            points["weighted_f1"].to_numpy(dtype=float),
            s=float(style.get("point_size", 24)),
            color=[region_colors[region] for region in points["region"]],
            alpha=float(style.get("point_alpha", 0.95)),
            edgecolors="none",
            linewidths=0.0,
            zorder=3,
        )

    axis.set_xlabel(
        str(style.get("x_axis_label", "Clustering Method")),
        fontsize=float(style.get("axis_label_fontsize", 12)),
    )
    axis.set_ylabel(
        str(style.get("y_axis_label", "Cell-Type Classification Weighted F1")),
        fontsize=float(style.get("axis_label_fontsize", 12)),
    )
    axis.set_ylim(*(float(value) for value in style.get("y_limits", (0.4, 0.8))))
    axis.set_yticks([float(value) for value in style.get("y_ticks", (0.4, 0.5, 0.6, 0.7, 0.8))])
    axis.set_xticks(positions)
    axis.set_xticklabels(methods, fontsize=float(style.get("x_tick_label_fontsize", 10)))
    axis.tick_params(axis="x", labelsize=float(style.get("x_tick_label_fontsize", 10)))
    axis.tick_params(axis="y", labelsize=float(style.get("y_tick_label_fontsize", 9)))
    axis.set_xlim(
        positions[0] - float(style.get("x_margin", 0.42)),
        positions[-1] + float(style.get("x_margin", 0.42)),
    )
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(
        axis="y",
        linestyle="--",
        linewidth=float(style.get("grid_linewidth", 0.6)),
        alpha=float(style.get("grid_alpha", 0.4)),
    )
    axis.set_axisbelow(True)
    fig.text(
        float(style.get("panel_label_x", 0.03)),
        float(style.get("panel_label_y", 0.98)),
        str(style.get("panel_label", "E")),
        fontsize=float(style.get("panel_label_fontsize", 30)),
        ha="left",
        va="top",
    )
    _save_figure_via_local_tempfile(fig, output_path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return Path(output_path)


def render_panel_cell_type_heatmap(
    metrics: pd.DataFrame,
    output_path: str | Path,
    *,
    method_order: Sequence[str],
    metric_suffix: str,
    style: Mapping[str, Any] | None = None,
    dpi: int = 300,
) -> Path:
    """Render the Panel F or H heatmap with its matched cell-count bars."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    style = dict(style or {})
    methods = [str(method) for method in method_order]
    metric_columns = [f"{method}_{metric_suffix}" for method in methods]
    required_columns = {"cell_type", "n_cells", *metric_columns}
    if missing := required_columns.difference(metrics.columns):
        raise Figure02ValidationError(
            f"Panel cell-type heatmap is missing columns: {sorted(missing)}"
        )
    if metrics.empty:
        raise Figure02ValidationError("Panel cell-type heatmap data are empty")
    if metrics["cell_type"].duplicated().any():
        raise Figure02ValidationError("Panel cell-type heatmap has duplicate row labels")
    figure_size = tuple(float(value) for value in style.get("figure_size_inches", (7.4, 6.6)))
    if len(figure_size) != 2:
        raise Figure02ValidationError("Panel heatmap figure_size_inches must have two values")

    plt.rcParams.update({"font.family": str(style.get("font_family", "Arial"))})
    fig = plt.figure(figsize=figure_size)
    fig.subplots_adjust(
        left=float(style.get("left", 0.28)),
        right=float(style.get("right", 0.98)),
        bottom=float(style.get("bottom", 0.11)),
        top=float(style.get("top", 0.92)),
    )
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[float(value) for value in style.get("width_ratios", (4.0, 1.55))],
        height_ratios=[float(value) for value in style.get("height_ratios", (0.055, 1.0))],
        wspace=float(style.get("wspace", 0.08)),
        hspace=float(style.get("hspace", 0.08)),
    )
    color_axis = fig.add_subplot(grid[0, 0])
    fig.add_subplot(grid[0, 1]).axis("off")
    axis = fig.add_subplot(grid[1, 0])
    count_axis = fig.add_subplot(grid[1, 1], sharey=axis)

    value_multiplier = float(style.get("value_multiplier", 1.0))
    matrix = metrics.loc[:, metric_columns].to_numpy(dtype=float) * value_multiplier
    vmin, vmax = (float(value) for value in style.get("color_limits", (0.0, 1.0)))
    image = axis.imshow(
        matrix,
        aspect="auto",
        cmap=str(style.get("cmap", "RdYlGn")),
        vmin=vmin,
        vmax=vmax,
    )
    row_labels = metrics["cell_type"].astype(str).tolist()
    axis.set_xticks(np.arange(len(methods)))
    axis.set_xticklabels(
        methods, fontsize=float(style.get("x_tick_label_fontsize", 10))
    )
    axis.set_yticks(np.arange(len(row_labels)))
    axis.set_yticklabels(
        row_labels, fontsize=float(style.get("y_tick_label_fontsize", 9))
    )
    axis.set_xlabel(
        str(style.get("x_axis_label", "Clustering Method")),
        fontsize=float(style.get("axis_label_fontsize", 11)),
    )
    axis.set_ylabel(
        str(style.get("y_axis_label", "Cell Type")),
        fontsize=float(style.get("axis_label_fontsize", 11)),
    )

    colorbar = fig.colorbar(image, cax=color_axis, orientation="horizontal")
    colorbar.set_label(
        str(style.get("colorbar_label", "F1 Score")),
        fontsize=float(style.get("colorbar_label_fontsize", 10)),
    )
    ticks = [float(value) for value in style.get("colorbar_ticks", np.linspace(vmin, vmax, 6))]
    colorbar.set_ticks(ticks)
    if bool(style.get("colorbar_percent", False)):
        colorbar.ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}%"))
    color_axis.xaxis.set_ticks_position("top")
    color_axis.xaxis.set_label_position("top")
    color_axis.tick_params(labelsize=float(style.get("colorbar_tick_fontsize", 9)))

    y_positions = np.arange(len(row_labels))
    count_axis.barh(
        y_positions,
        metrics["n_cells"].to_numpy(dtype=float),
        height=float(style.get("count_bar_height", 0.76)),
        color=str(style.get("count_bar_color", "#64748B")),
    )
    count_axis.set_xlabel(
        str(style.get("count_axis_label", "Cell Count")),
        fontsize=float(style.get("axis_label_fontsize", 11)),
    )
    count_axis.tick_params(axis="y", left=False, labelleft=False)
    count_axis.tick_params(axis="x", labelsize=float(style.get("count_tick_label_fontsize", 9)))
    count_axis.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: "0" if value == 0 else f"{value / 1000:.0f}k")
    )
    count_axis.grid(
        axis="x",
        linestyle="--",
        linewidth=float(style.get("grid_linewidth", 0.6)),
        alpha=float(style.get("grid_alpha", 0.4)),
    )
    count_axis.set_axisbelow(True)
    count_axis.spines["top"].set_visible(False)
    count_axis.spines["right"].set_visible(False)
    count_axis.set_ylim(axis.get_ylim())
    count_limit = style.get("count_x_limit")
    if count_limit is not None:
        count_axis.set_xlim(0.0, float(count_limit))

    fig.text(
        float(style.get("panel_label_x", 0.02)),
        float(style.get("panel_label_y", 0.98)),
        str(style.get("panel_label", "F")),
        fontsize=float(style.get("panel_label_fontsize", 32)),
        ha="left",
        va="top",
    )
    _save_figure_via_local_tempfile(fig, output_path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return Path(output_path)


def render_panel_g(
    scores: pd.DataFrame,
    output_path: str | Path,
    *,
    method_order: Sequence[str],
    region_order: Sequence[str],
    style: Mapping[str, Any] | None = None,
    dpi: int = 300,
) -> Path:
    """Render G's percent-purity box-and-strip plot using E's shared geometry."""
    required_columns = {"region", "method", "cell_purity", "n_cells"}
    if missing := required_columns.difference(scores.columns):
        raise Figure02ValidationError(f"Panel G score table is missing columns: {sorted(missing)}")
    # Render with the deliberately shared box/strip implementation after
    # changing only the plotting unit from fraction to percentage. This keeps
    # the eight deterministic File_ID points spatially comparable to Panel E.
    plot_scores = scores.loc[:, ["region", "method", "n_cells"]].copy()
    plot_scores["weighted_f1"] = scores["cell_purity"].to_numpy(dtype=float) * 100.0
    return render_panel_e(
        plot_scores,
        output_path,
        method_order=method_order,
        region_order=region_order,
        style=style,
        dpi=dpi,
    )


def render_panel_i(
    summaries: pd.DataFrame,
    output_path: str | Path,
    *,
    marker_order: Sequence[str],
    method_order: Sequence[str],
    style: Mapping[str, Any] | None = None,
    dpi: int = 300,
) -> Path:
    """Render the Panel I CD8+ T-cell marker-expression bubble plot."""
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    style = dict(style or {})
    markers = [str(marker) for marker in marker_order]
    methods = [str(method) for method in method_order]
    required_columns = {
        "method",
        "marker",
        "scaled_mean_expression",
        "fraction_cells_pct",
    }
    if missing := required_columns.difference(summaries.columns):
        raise Figure02ValidationError(f"Panel I table is missing columns: {sorted(missing)}")
    expected_rows = len(markers) * len(methods)
    if len(summaries) != expected_rows:
        raise Figure02ValidationError(
            f"Panel I has {len(summaries)} marker-method rows; expected {expected_rows}"
        )
    if set(summaries["marker"].astype(str)) != set(markers):
        raise Figure02ValidationError("Panel I marker table differs from the declared marker order")
    if set(summaries["method"].astype(str)) != set(methods):
        raise Figure02ValidationError("Panel I method table differs from the declared method order")

    figure_size = tuple(float(value) for value in style.get("figure_size_inches", (12.5, 3.8)))
    if len(figure_size) != 2:
        raise Figure02ValidationError("Panel I figure_size_inches must have two values")
    plt.rcParams.update({"font.family": str(style.get("font_family", "Arial"))})
    fig = plt.figure(figsize=figure_size)
    axis = fig.add_axes([float(value) for value in style.get("axes_position", (0.14, 0.40, 0.73, 0.39))])
    cmap = plt.get_cmap(str(style.get("cmap", "Reds")))
    norm = Normalize(vmin=0.0, vmax=1.0)
    x_positions = {marker: index for index, marker in enumerate(markers)}
    y_positions = {method: len(methods) - 1 - index for index, method in enumerate(methods)}
    size_scale = float(style.get("size_scale", 250.0))
    minimum_size = float(style.get("minimum_point_size", 1.0))

    ordered = summaries.copy()
    ordered["_marker_order"] = ordered["marker"].astype(str).map(x_positions)
    ordered["_method_order"] = ordered["method"].astype(str).map(y_positions)
    ordered = ordered.sort_values(["_method_order", "_marker_order"], kind="stable")
    sizes = np.maximum(
        minimum_size,
        ordered["fraction_cells_pct"].to_numpy(dtype=float) / 100.0 * size_scale,
    )
    axis.scatter(
        ordered["_marker_order"].to_numpy(dtype=float),
        ordered["_method_order"].to_numpy(dtype=float),
        s=sizes,
        c=ordered["scaled_mean_expression"].to_numpy(dtype=float),
        cmap=cmap,
        norm=norm,
        edgecolors=str(style.get("point_edgecolor", "#777777")),
        linewidths=float(style.get("point_edgewidth", 0.35)),
    )
    axis.set_xlim(-0.7, len(markers) - 0.3)
    axis.set_ylim(-0.7, len(methods) - 0.3)
    axis.set_xticks(np.arange(len(markers)))
    axis.set_xticklabels(
        markers,
        rotation=90,
        fontsize=float(style.get("x_tick_label_fontsize", 8)),
        ha="center",
    )
    axis.set_yticks([y_positions[method] for method in methods])
    axis.set_yticklabels(methods, fontsize=float(style.get("y_tick_label_fontsize", 10)))
    axis.set_xlabel(
        str(style.get("x_axis_label", "Protein Marker")),
        fontsize=float(style.get("axis_label_fontsize", 11)),
        labelpad=float(style.get("x_label_pad", 15)),
    )
    axis.set_ylabel(
        str(style.get("y_axis_label", "Clustering Method")),
        fontsize=float(style.get("axis_label_fontsize", 11)),
    )
    for spine in axis.spines.values():
        spine.set_color(str(style.get("spine_color", "#333333")))
        spine.set_linewidth(float(style.get("spine_linewidth", 0.7)))

    # The two compact legend axes preserve the source panel's independent
    # encodings: dot area is expression-positive cell fraction; red intensity
    # is the marker-wise standardized mean expression.
    size_axis = fig.add_axes([float(value) for value in style.get("size_legend_position", (0.14, 0.09, 0.22, 0.16))])
    size_axis.axis("off")
    legend_values = [float(value) for value in style.get("size_legend_values", (20, 40, 60, 80, 100))]
    legend_x = np.arange(len(legend_values), dtype=float)
    size_axis.scatter(
        legend_x,
        np.zeros_like(legend_x),
        s=np.maximum(minimum_size, np.asarray(legend_values) / 100.0 * size_scale),
        color=str(style.get("size_legend_color", "#8a8a8a")),
        edgecolors=str(style.get("point_edgecolor", "#777777")),
        linewidths=float(style.get("point_edgewidth", 0.35)),
    )
    for x_value, value in zip(legend_x, legend_values, strict=True):
        size_axis.text(x_value, -0.58, f"{value:.0f}", ha="center", va="top", fontsize=float(style.get("legend_tick_fontsize", 8)))
    size_axis.text(
        -0.45,
        0.76,
        str(style.get("size_legend_label", "Fraction of\\nCells in\\nGroup (%)")),
        ha="right",
        va="center",
        fontsize=float(style.get("legend_label_fontsize", 10)),
    )
    size_axis.set_xlim(-1.6, len(legend_values) - 0.2)
    size_axis.set_ylim(-1.0, 1.0)

    color_axis = fig.add_axes([float(value) for value in style.get("colorbar_position", (0.75, 0.09, 0.12, 0.04))])
    colorbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=color_axis, orientation="horizontal")
    colorbar.set_ticks([0.0, 0.5, 1.0])
    colorbar.ax.tick_params(labelsize=float(style.get("legend_tick_fontsize", 8)))
    fig.text(
        float(style.get("colorbar_label_x", 0.90)),
        float(style.get("colorbar_label_y", 0.14)),
        str(style.get("colorbar_label", "Mean\\nExpression\\nin Group")),
        ha="left",
        va="center",
        fontsize=float(style.get("legend_label_fontsize", 10)),
    )
    fig.text(
        float(style.get("panel_label_x", 0.02)),
        float(style.get("panel_label_y", 0.96)),
        str(style.get("panel_label", "I")),
        fontsize=float(style.get("panel_label_fontsize", 30)),
        ha="left",
        va="top",
    )
    _save_figure_via_local_tempfile(fig, output_path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return Path(output_path)


def render_panel_j(
    data: PanelJData,
    output_path: str | Path,
    *,
    color_map: Mapping[str, str],
    method_order: Sequence[str],
    coordinate_columns: Sequence[str],
    style: Mapping[str, Any] | None = None,
    dpi: int = 300,
) -> Path:
    """Render two fixed spatial agreement examples with whole-tissue callouts."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import ConnectionPatch, Rectangle

    style = dict(style or {})
    methods = [str(method) for method in method_order]
    x_column, y_column = (str(column) for column in coordinate_columns)
    required_columns = {"File_ID", x_column, y_column, "Ground Truth", *methods}
    if missing := required_columns.difference(data.cells.columns):
        raise Figure02ValidationError(f"Panel J cells are missing columns: {sorted(missing)}")
    if data.examples.empty:
        raise Figure02ValidationError("Panel J has no configured agreement examples")
    examples = data.examples.copy()
    example_order = [str(value) for value in style.get("example_order", examples["example"].astype(str).tolist())]
    examples = examples.set_index("example").loc[example_order].reset_index()
    figure_size = tuple(float(value) for value in style.get("figure_size_inches", (12.0, 5.1)))
    if len(figure_size) != 2:
        raise Figure02ValidationError("Panel J figure_size_inches must have two values")

    plt.rcParams.update({"font.family": str(style.get("font_family", "Arial"))})
    fig = plt.figure(figsize=figure_size)
    grid = fig.add_gridspec(
        len(examples),
        # One whole-tissue callout plus Ground Truth and four method zooms.
        len(methods) + 2,
        left=float(style.get("left", 0.18)),
        right=float(style.get("right", 0.99)),
        bottom=float(style.get("bottom", 0.08)),
        top=float(style.get("top", 0.83)),
        width_ratios=[float(value) for value in style.get("width_ratios", (1.0, 1.12, 1.12, 1.12, 1.12, 1.12))],
        wspace=float(style.get("wspace", 0.12)),
        hspace=float(style.get("hspace", 0.12)),
    )

    def scatter_labels(axis: Any, frame: pd.DataFrame, label_column: str, point_size: float) -> None:
        for label, group in frame.groupby(label_column, sort=True):
            axis.scatter(
                group[x_column],
                group[y_column],
                s=point_size,
                c=color_map.get(str(label), "#808080"),
                alpha=float(style.get("point_alpha", 0.82)),
                linewidths=0,
                rasterized=True,
            )

    for row_index, example in examples.iterrows():
        file_id = str(example["file_id"])
        x0, x1, y0, y1 = (float(example[key]) for key in ("x0", "x1", "y0", "y1"))
        whole = data.cells.loc[data.cells["File_ID"].eq(file_id)]
        zoom = whole.loc[
            whole[x_column].between(x0, x1) & whole[y_column].between(y0, y1)
        ]
        whole_axis = fig.add_subplot(grid[row_index, 0])
        scatter_labels(whole_axis, whole, "Ground Truth", float(style.get("whole_point_size", 0.45)))
        whole_axis.add_patch(
            Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                linewidth=float(style.get("callout_linewidth", 0.7)),
                edgecolor=str(style.get("callout_color", "#222222")),
                facecolor="none",
                zorder=4,
            )
        )
        whole_axis.set_aspect("equal", adjustable="box")
        whole_axis.invert_yaxis()
        whole_axis.set_xticks([])
        whole_axis.set_yticks([])
        for spine in whole_axis.spines.values():
            spine.set_color(str(style.get("frame_color", "#d9d9d9")))
            spine.set_linewidth(float(style.get("frame_linewidth", 0.5)))

        zoom_axes: list[Any] = []
        for column_index, label_column in enumerate(["Ground Truth", *methods], start=1):
            axis = fig.add_subplot(grid[row_index, column_index])
            scatter_labels(axis, zoom, label_column, float(style.get("zoom_point_size", 5.5)))
            axis.set_xlim(x0, x1)
            axis.set_ylim(y1, y0)
            axis.set_aspect("equal", adjustable="box")
            axis.set_xticks([])
            axis.set_yticks([])
            for spine in axis.spines.values():
                spine.set_color(str(style.get("frame_color", "#d9d9d9")))
                spine.set_linewidth(float(style.get("frame_linewidth", 0.5)))
            if row_index == 0:
                axis.set_title(
                    label_column,
                    fontsize=float(style.get("column_title_fontsize", 10)),
                    pad=float(style.get("column_title_pad", 7)),
                )
            zoom_axes.append(axis)
        # Connect the callout rectangle's right corners to the ground-truth
        # zoom. The connection is in figure space, so it remains correct if a
        # reader later resizes the notebook output.
        for whole_corner, zoom_corner in [((x1, y0), (0.0, 1.0)), ((x1, y1), (0.0, 0.0))]:
            connection = ConnectionPatch(
                xyA=whole_corner,
                xyB=zoom_corner,
                coordsA="data",
                coordsB="axes fraction",
                axesA=whole_axis,
                axesB=zoom_axes[0],
                color=str(style.get("callout_color", "#222222")),
                linewidth=float(style.get("callout_linewidth", 0.7)),
            )
            fig.add_artist(connection)
        fig.text(
            float(style.get("row_label_x", 0.13)),
            (whole_axis.get_position().y0 + whole_axis.get_position().y1) / 2.0,
            str(example["example"]),
            ha="right",
            va="center",
            fontsize=float(style.get("row_label_fontsize", 11)),
        )

    fig.text(
        float(style.get("panel_label_x", 0.02)),
        float(style.get("panel_label_y", 0.96)),
        str(style.get("panel_label", "J")),
        fontsize=float(style.get("panel_label_fontsize", 28)),
        ha="left",
        va="top",
    )
    fig.text(
        float(style.get("title_x", 0.61)),
        float(style.get("title_y", 0.96)),
        str(style.get("title", "Spatial Agreement Across Clustering Methods")),
        fontsize=float(style.get("title_fontsize", 13)),
        ha="center",
        va="top",
    )
    _save_figure_via_local_tempfile(fig, output_path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return Path(output_path)


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
    _save_figure_via_local_tempfile(
        fig, output_path, dpi=dpi, bbox_inches="tight", facecolor="white"
    )
    plt.close(fig)
    return output_path


def save_panel_b_provenance(
    distribution: PanelBDistribution,
    output_path: str | Path,
    config: Mapping[str, Any] | None = None,
) -> Path:
    """Write concise local provenance facts beside the Panel B artifacts."""
    config = dict(config or load_figure_config())
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel = config["panel_b"]
    color_key_path = REPOSITORY_ROOT / "configs" / panel["style"]["color_map_filename"]
    if not color_key_path.is_file():
        raise Figure02ValidationError(f"Tracked Panel B color key is missing: {color_key_path}")
    payload = {
        "figure": 2,
        "panel": "B",
        "cohort": panel["cohort"],
        "truth_column": panel["labels"]["truth_column"],
        "source_h5ad": {
            "filename": panel["data"]["h5ad_filename"],
            "declared_sha256": panel["data"]["h5ad_sha256"],
        },
        "color_key": {
            "filename": color_key_path.name,
            "sha256": _file_sha256(color_key_path),
        },
        "source_cell_count": distribution.source_cell_count,
        "plotted_cell_count": int(distribution.counts["Cell Count"].sum()),
        "excluded_counts": distribution.excluded_counts,
        "cell_type_counts": dict(
            zip(
                distribution.counts["Cell Type"].astype(str),
                distribution.counts["Cell Count"].astype(int),
                strict=True,
            )
        ),
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def save_panel_c_provenance(
    data: PanelCData,
    output_path: str | Path,
    config: Mapping[str, Any] | None = None,
) -> Path:
    """Write concise local provenance facts beside the Panel C artifacts."""
    config = dict(config or load_figure_config())
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel = config["panel_c"]
    color_key_path = REPOSITORY_ROOT / "configs" / panel["style"]["color_map_filename"]
    if not color_key_path.is_file():
        raise Figure02ValidationError(f"Tracked Panel C color key is missing: {color_key_path}")
    coordinate_columns = [str(column) for column in panel["coordinates"]["columns"]]
    payload = {
        "figure": 2,
        "panel": "C",
        "region": panel["region"],
        "truth_column": panel["labels"]["truth_column"],
        "coordinate_columns": coordinate_columns,
        "coordinate_orientation": "H5AD x/y; no axis inversion",
        "source_h5ad": {
            "filename": panel["data"]["h5ad_filename"],
            "declared_sha256": panel["data"]["h5ad_sha256"],
        },
        "color_key": {
            "filename": color_key_path.name,
            "sha256": _file_sha256(color_key_path),
        },
        "source_cell_count": data.source_cell_count,
        "plotted_cell_count": len(data.cells),
        "coordinate_bounds": {
            column: [float(data.cells[column].min()), float(data.cells[column].max())]
            for column in coordinate_columns
        },
        "cell_type_counts": data.cell_type_counts,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def save_panel_e_provenance(
    data: PanelEData,
    output_path: str | Path,
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> Path:
    """Write local input and metric provenance beside the Panel E artifacts."""
    config = dict(config or load_figure_config())
    panel = config["panel_e"]
    root = (
        Path(data_root).expanduser().resolve()
        if data_root
        else resolve_data_root(config, panel_key="panel_e")
    )
    source_panel_key = str(panel["clustering_source_panel"])
    source_methods = config[source_panel_key]["clustering_methods"]
    assignment_artifacts: dict[str, dict[str, str]] = {}
    for method_name, method_config in source_methods.items():
        artifact_path = _resolve_assignment_path(method_name, method_config, data_root=root)
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Panel E {method_name} assignments are missing: {artifact_path}")
        artifact = {
            "filename": str(method_config["assignment_filename"]),
            "sha256": _file_sha256(artifact_path),
        }
        if method_name == "pixie":
            manifest_path = artifact_path.parent / "manifest.json"
            if not manifest_path.is_file():
                raise Figure02ValidationError(f"Panel E PIXIE manifest is missing: {manifest_path}")
            artifact["manifest_filename"] = manifest_path.name
            artifact["manifest_sha256"] = _file_sha256(manifest_path)
        assignment_artifacts[method_name] = artifact

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "figure": 2,
        "panel": "E",
        "cohort": panel["cohort"],
        "source_h5ad": {
            "filename": panel["data"]["h5ad_filename"],
            "declared_sha256": panel["data"]["h5ad_sha256"],
        },
        "clustering_source_panel": source_panel_key,
        "method_assignments": assignment_artifacts,
        "evaluation": panel["evaluation"],
        "source_cell_count": data.source_cell_count,
        "evaluation_cell_count": data.evaluation_cell_count,
        "excluded_counts": data.excluded_counts,
        "evaluation_class_count": data.evaluation_class_count,
        "cluster_counts": data.cluster_counts,
        "regional_scores": data.scores.to_dict(orient="records"),
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def _method_assignment_artifacts_for_panel(
    config: Mapping[str, Any],
    *,
    panel_key: str,
    data_root: str | Path | None = None,
) -> dict[str, dict[str, str]]:
    """Hash the exact method inputs consumed by one local Figure 2 panel."""
    panel = config[panel_key]
    source_key = str(panel.get("clustering_source_panel", "panel_d"))
    source_methods = config[source_key]["clustering_methods"]
    root = (
        Path(data_root).expanduser().resolve()
        if data_root
        else resolve_data_root(config, panel_key=panel_key)
    )
    artifacts: dict[str, dict[str, str]] = {}
    for method_name, method_config in source_methods.items():
        path = _resolve_assignment_path(method_name, method_config, data_root=root)
        if not path.is_file():
            raise FileNotFoundError(f"{panel_key} {method_name} assignments are missing: {path}")
        artifact = {
            "filename": str(method_config["assignment_filename"]),
            "sha256": _file_sha256(path),
        }
        if method_name == "pixie":
            manifest_path = path.parent / "manifest.json"
            if not manifest_path.is_file():
                raise Figure02ValidationError(f"{panel_key} PIXIE manifest is missing: {manifest_path}")
            artifact["manifest_filename"] = manifest_path.name
            artifact["manifest_sha256"] = _file_sha256(manifest_path)
        artifacts[method_name] = artifact
    return artifacts


def _write_panel_provenance(output_path: str | Path, payload: Mapping[str, Any]) -> Path:
    """Write a small JSON provenance record next to locally generated outputs."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def _panel_h5ad_source(config: Mapping[str, Any], panel_key: str) -> dict[str, str]:
    """Return the H5AD identity inherited by an aliased Figure 2 panel."""
    source_panel = _source_panel_config(config, panel_key, "data_source_panel")
    data = source_panel["data"]
    return {
        "filename": str(data["h5ad_filename"]),
        "declared_sha256": str(data["h5ad_sha256"]),
    }


def save_panel_cell_type_metrics_provenance(
    data: PanelCellTypeMetrics,
    output_path: str | Path,
    *,
    panel_key: str,
    config: Mapping[str, Any] | None = None,
    data_root: str | Path | None = None,
) -> Path:
    """Write shared Panel F/H metric and selected-assignment provenance."""
    config = dict(config or load_figure_config())
    panel = config[panel_key]
    evaluation = _evaluation_config_for_panel(config, panel_key)
    payload = {
        "figure": 2,
        "panel": str(panel_key).replace("panel_", "").upper(),
        "source_h5ad": _panel_h5ad_source(config, panel_key),
        "clustering_source_panel": panel["clustering_source_panel"],
        "method_assignments": _method_assignment_artifacts_for_panel(
            config, panel_key=panel_key, data_root=data_root
        ),
        "evaluation": evaluation,
        "row_order": panel["row_order"],
        "source_cell_count": data.source_cell_count,
        "evaluation_cell_count": data.evaluation_cell_count,
        "excluded_counts": data.excluded_counts,
        "evaluation_class_count": data.evaluation_class_count,
        "cluster_counts": data.cluster_counts,
        "cell_type_metrics": data.metrics.to_dict(orient="records"),
    }
    return _write_panel_provenance(output_path, payload)


def save_panel_g_provenance(
    data: PanelGData,
    output_path: str | Path,
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> Path:
    """Write Panel G's eight-region purity inputs and scores."""
    config = dict(config or load_figure_config())
    panel = config["panel_g"]
    payload = {
        "figure": 2,
        "panel": "G",
        "source_h5ad": _panel_h5ad_source(config, "panel_g"),
        "clustering_source_panel": panel["clustering_source_panel"],
        "method_assignments": _method_assignment_artifacts_for_panel(
            config, panel_key="panel_g", data_root=data_root
        ),
        "evaluation": _evaluation_config_for_panel(config, "panel_g"),
        "source_cell_count": data.source_cell_count,
        "evaluation_cell_count": data.evaluation_cell_count,
        "excluded_counts": data.excluded_counts,
        "evaluation_class_count": data.evaluation_class_count,
        "cluster_counts": data.cluster_counts,
        "regional_scores": data.scores.to_dict(orient="records"),
    }
    return _write_panel_provenance(output_path, payload)


def save_panel_i_provenance(
    data: PanelIData,
    output_path: str | Path,
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> Path:
    """Write Panel I's H5AD-X marker and global CD8-group provenance."""
    config = dict(config or load_figure_config())
    panel = config["panel_i"]
    payload = {
        "figure": 2,
        "panel": "I",
        "source_h5ad": _panel_h5ad_source(config, "panel_i"),
        "clustering_source_panel": panel["clustering_source_panel"],
        "method_assignments": _method_assignment_artifacts_for_panel(
            config, panel_key="panel_i", data_root=data_root
        ),
        "target_cell_type": panel["target_cell_type"],
        "expression_threshold": panel["expression_threshold"],
        "marker_order": list(data.marker_names),
        "source_cell_count": data.source_cell_count,
        "selected_cell_counts": data.selected_cell_counts,
        "selected_cluster_counts": data.selected_cluster_counts,
        "cluster_counts": data.cluster_counts,
    }
    return _write_panel_provenance(output_path, payload)


def save_panel_j_provenance(
    data: PanelJData,
    output_path: str | Path,
    config: Mapping[str, Any] | None = None,
    *,
    data_root: str | Path | None = None,
) -> Path:
    """Write Panel J's fixed TIFF example windows and agreement summaries."""
    config = dict(config or load_figure_config())
    panel = config["panel_j"]
    color_key_path = REPOSITORY_ROOT / "configs" / panel["style"]["color_map_filename"]
    if not color_key_path.is_file():
        raise Figure02ValidationError(f"Tracked Panel J color key is missing: {color_key_path}")
    payload = {
        "figure": 2,
        "panel": "J",
        "source_h5ad": _panel_h5ad_source(config, "panel_j"),
        "clustering_source_panel": panel["clustering_source_panel"],
        "method_assignments": _method_assignment_artifacts_for_panel(
            config, panel_key="panel_j", data_root=data_root
        ),
        "truth_column": panel["truth_column"],
        "coordinate_columns": panel["coordinate_columns"],
        "excluded_counts": data.excluded_counts,
        "source_cell_count": data.source_cell_count,
        "plotted_cell_count": data.plotted_cell_count,
        "cluster_counts": data.cluster_counts,
        "configured_examples": panel["examples"],
        "computed_examples": data.examples.to_dict(orient="records"),
        "color_key": {
            "filename": color_key_path.name,
            "sha256": _file_sha256(color_key_path),
        },
    }
    return _write_panel_provenance(output_path, payload)


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
    panel = config["panel_d"]
    color_key_path = REPOSITORY_ROOT / "configs" / panel["style"]["color_map_filename"]
    if not color_key_path.is_file():
        raise Figure02ValidationError(f"Tracked Panel D color key is missing: {color_key_path}")
    payload = {
        "figure": 2,
        "panel": "D",
        "cohort": panel["cohort"],
        "source_h5ad": {
            "filename": panel["data"]["h5ad_filename"],
            "declared_sha256": panel["data"]["h5ad_sha256"],
        },
        "color_key": {
            "filename": color_key_path.name,
            "sha256": _file_sha256(color_key_path),
        },
        "marker_count": len(data.marker_names),
        "row_count": len(panel_table),
        "cluster_counts": {
            method: int(panel_table[method].nunique())
            for method in ("leiden", "flowsom", "spatialsort", "pixie")
        },
        "shared_umap": panel["shared_umap"],
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
