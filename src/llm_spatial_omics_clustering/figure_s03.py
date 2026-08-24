"""Reproducible implementation of Supplementary Figure S3, Panels A--E.

Panels A--C and E import the exact B004 cohort and selected clustering
assignments from the Figure 2 contract.  That choice intentionally makes the
new PIXIE results differ from the supplied legacy composite: the composite
used an older table-level MiniSom partition, whereas Figure 2 now fixes the
image-native TIFF-derived PIXIE result.

Panel D is a separate recovered historical input.  Its eight-row CSV came
from an exploratory FlowSOM pipeline, not the final 45-marker, robust-scaled
K=300 configuration. The loader validates that CSV byte-for-byte and records
the gap in provenance; it does not misrepresent the curve as a rerun of Figure 2.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PANEL_KEYS = tuple(f"panel_{letter}" for letter in "abcde")


class FigureS03ValidationError(ValueError):
    """Raised when a Supplementary Figure S3 input violates its contract."""


@dataclass(frozen=True)
class FigureS03Inputs:
    """Validated Figure 2 cohort, raw expression, and selected assignments."""

    cells: pd.DataFrame
    expression: np.ndarray
    marker_names: tuple[str, ...]
    cluster_counts: dict[str, int]
    source_cell_count: int
    non_noise_cell_count: int
    data_root: Path
    figure_02_config_path: Path
    figure_02_h5ad_sha256: str


def load_figure_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and minimally validate the Supplementary Figure S3 configuration."""
    path = Path(config_path) if config_path else REPOSITORY_ROOT / "configs/figure_s03.yaml"
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or int(config.get("supplementary_figure", -1)) != 3:
        raise FigureS03ValidationError(f"Invalid Supplementary Figure S3 config: {path}")
    if not set(PANEL_KEYS).issubset(config):
        raise FigureS03ValidationError(f"Config does not define Panels A--E: {path}")
    return config


def _resolve_repository_root(repository_root: str | Path | None) -> Path:
    return (
        Path(repository_root).expanduser().resolve()
        if repository_root
        else REPOSITORY_ROOT
    )


def _resolve_config_path(
    repository_root: Path,
    config_path: str | Path | None,
) -> Path:
    if config_path is None:
        return repository_root / "configs/figure_s03.yaml"
    path = Path(config_path).expanduser()
    return (repository_root / path).resolve() if not path.is_absolute() else path.resolve()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataframe_fingerprint(frame: pd.DataFrame) -> str:
    hashed = pd.util.hash_pandas_object(frame, index=False).to_numpy(dtype=np.uint64)
    return hashlib.sha256(hashed.tobytes()).hexdigest()


def _json_dump(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _output_path(repository_root: Path, configured_path: str) -> Path:
    path = Path(configured_path)
    path = path if path.is_absolute() else repository_root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _save_figure(
    figure: Any,
    repository_root: Path,
    output_config: Mapping[str, Any],
) -> dict[str, Path]:
    paths = {
        "panel_png": _output_path(repository_root, str(output_config["panel_png"])),
        "panel_pdf": _output_path(repository_root, str(output_config["panel_pdf"])),
    }
    figure.savefig(paths["panel_png"], dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(paths["panel_pdf"], bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return paths


def _method_cluster_contracts(
    config: Mapping[str, Any],
) -> tuple[dict[str, int], dict[str, int]]:
    dependency = config["figure_02_dependency"]
    configured = {
        str(key): int(value)
        for key, value in dependency["configured_methods"].items()
    }
    observed = {
        str(key): int(value)
        for key, value in dependency["observed_methods"].items()
    }
    if set(configured) != set(observed):
        raise FigureS03ValidationError(
            "Configured and observed method contracts have different keys"
        )
    return configured, observed


def _method_specs(config: Mapping[str, Any]) -> list[tuple[str, str]]:
    specs = [
        (str(method_key), str(method_label))
        for method_key, method_label in config["figure_02_dependency"]["method_order"]
    ]
    configured, observed = _method_cluster_contracts(config)
    method_keys = {key for key, _ in specs}
    if method_keys != set(configured) or method_keys != set(observed):
        raise FigureS03ValidationError(
            "Method order and configured/observed method keys differ"
        )
    return specs


def _load_color_map(
    repository_root: Path,
    config: Mapping[str, Any],
    observed_labels: Sequence[str],
) -> dict[str, str]:
    path = repository_root / str(config["shared"]["color_map_path"])
    frame = pd.read_csv(path)
    required = {"cell_type_update", "color_hex"}
    if missing := required.difference(frame.columns):
        raise FigureS03ValidationError(f"Color map is missing columns: {sorted(missing)}")
    if frame["cell_type_update"].duplicated().any():
        raise FigureS03ValidationError("Color map has duplicate cell-type labels")
    colors = dict(
        zip(
            frame["cell_type_update"].astype(str),
            frame["color_hex"].astype(str),
            strict=True,
        )
    )
    if missing := set(map(str, observed_labels)).difference(colors):
        raise FigureS03ValidationError(f"Color map has no entries for: {sorted(missing)}")
    return colors


@lru_cache(maxsize=4)
def _load_inputs_cached(
    repository_root_string: str,
    config_path_string: str,
    download_if_missing: bool,
) -> FigureS03Inputs:
    repository_root = Path(repository_root_string)
    config_path = Path(config_path_string)
    config = load_figure_config(config_path)
    dependency = config["figure_02_dependency"]
    figure_02_config_path = (repository_root / str(dependency["config_path"])).resolve()

    from llm_spatial_omics_clustering.figure_02 import (
        load_b004_h5ad,
        load_figure_config as load_figure_02_config,
        load_method_assignments,
        resolve_data_root,
    )

    figure_02_config = load_figure_02_config(figure_02_config_path)
    configured_methods, observed_methods = _method_cluster_contracts(config)
    figure_02_configured_methods = {
        str(method_key): int(method_config["configured_clusters"])
        for method_key, method_config in figure_02_config["panel_d"][
            "clustering_methods"
        ].items()
    }
    if figure_02_configured_methods != configured_methods:
        raise FigureS03ValidationError(
            "S3 configured method counts differ from Figure 2: "
            f"s3={configured_methods}, figure_02={figure_02_configured_methods}"
        )
    data_root = resolve_data_root(
        figure_02_config,
        download_if_missing=download_if_missing,
    )
    figure_02_data = load_b004_h5ad(figure_02_config, data_root=data_root)
    assignments = load_method_assignments(
        figure_02_data,
        figure_02_config,
        data_root=data_root,
    )

    cells = figure_02_data.cells.copy()
    cells["File_ID"] = cells["File_ID"].astype(str)
    cells["ID"] = pd.to_numeric(cells["ID"], errors="raise").astype(np.int64)
    if cells[["File_ID", "ID"]].duplicated().any():
        raise FigureS03ValidationError("Figure 2 cells have duplicate (File_ID, ID) keys")

    if set(assignments) != set(observed_methods):
        raise FigureS03ValidationError(
            "Figure 2 method keys differ from the S3 contract: "
            f"loaded={sorted(assignments)}, declared={sorted(observed_methods)}"
        )
    for method_key, _ in _method_specs(config):
        frame = assignments[method_key][["File_ID", "ID", "cluster"]].copy()
        frame["File_ID"] = frame["File_ID"].astype(str)
        frame["ID"] = pd.to_numeric(frame["ID"], errors="raise").astype(np.int64)
        cells = cells.merge(
            frame.rename(columns={"cluster": method_key}),
            on=["File_ID", "ID"],
            how="left",
            validate="one_to_one",
            sort=False,
        )
        if cells[method_key].isna().any():
            raise FigureS03ValidationError(f"{method_key} has missing S3 assignments")

    cluster_counts = {
        method_key: int(cells[method_key].nunique())
        for method_key, _ in _method_specs(config)
    }
    if cluster_counts != observed_methods:
        raise FigureS03ValidationError(
            "Selected artifact occupied-cluster counts changed: "
            f"loaded={cluster_counts}, declared_observed={observed_methods}"
        )

    source_count = int(len(cells))
    if source_count != int(dependency["expected_source_cells"]):
        raise FigureS03ValidationError(
            f"Expected {dependency['expected_source_cells']:,} B004 cells; found {source_count:,}"
        )
    truth_column = str(dependency["truth_column"])
    if cells[truth_column].isna().any():
        raise FigureS03ValidationError("B004 raw truth labels contain missing values")
    cells[truth_column] = cells[truth_column].astype(str)
    raw_label_count = int(cells[truth_column].nunique())
    if raw_label_count != int(dependency["expected_raw_label_count_including_noise"]):
        raise FigureS03ValidationError(
            f"Expected 28 raw labels including Noise; found {raw_label_count}"
        )
    non_noise_count = int(cells[truth_column].ne(str(dependency["excluded_label"])).sum())
    if non_noise_count != int(dependency["expected_non_noise_cells"]):
        raise FigureS03ValidationError(
            f"Expected {dependency['expected_non_noise_cells']:,} non-Noise cells; "
            f"found {non_noise_count:,}"
        )

    # Figure 2 places three observation-derived markers before the 45 H5AD X
    # variables. Supplementary Figure S3A deliberately uses only H5AD X.
    obs_marker_count = len(figure_02_config["panel_d"]["features"]["h5ad_obs_markers"])
    marker_names = tuple(map(str, figure_02_data.marker_names[obs_marker_count:]))
    expression = np.asarray(figure_02_data.features[:, obs_marker_count:], dtype=np.float64)
    if expression.shape != (source_count, 45) or len(marker_names) != 45:
        raise FigureS03ValidationError(
            f"Expected a 220,082 x 45 H5AD-X matrix; found {expression.shape}"
        )

    return FigureS03Inputs(
        cells=cells,
        expression=expression,
        marker_names=marker_names,
        cluster_counts=cluster_counts,
        source_cell_count=source_count,
        non_noise_cell_count=non_noise_count,
        data_root=data_root,
        figure_02_config_path=figure_02_config_path,
        figure_02_h5ad_sha256=str(figure_02_config["panel_d"]["data"]["h5ad_sha256"]),
    )


def load_inputs(
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    download_if_missing: bool = True,
) -> FigureS03Inputs:
    """Load the shared S3 inputs through Figure 2's public, validated API."""
    root = _resolve_repository_root(repository_root)
    resolved_config = _resolve_config_path(root, config_path)
    return _load_inputs_cached(str(root), str(resolved_config), download_if_missing)


def build_panel_a_summary(
    inputs: FigureS03Inputs,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Compute mean expression, positive fraction, and marker-scaled means."""
    from scipy.cluster.hierarchy import leaves_list, linkage

    truth_column = str(config["figure_02_dependency"]["truth_column"])
    excluded_label = str(config["figure_02_dependency"]["excluded_label"])
    keep = inputs.cells[truth_column].ne(excluded_label).to_numpy()
    labels = inputs.cells.loc[keep, truth_column].astype(str).to_numpy()
    expression = inputs.expression[keep]
    cell_types = sorted(np.unique(labels).tolist())
    if len(cell_types) != int(
        config["figure_02_dependency"]["expected_raw_label_count_excluding_noise"]
    ):
        raise FigureS03ValidationError("Panel A raw non-Noise label count changed")

    mean_matrix = np.vstack(
        [expression[labels == cell_type].mean(axis=0) for cell_type in cell_types]
    )
    fraction_matrix = np.vstack(
        [(expression[labels == cell_type] > float(config["panel_a"]["expression_threshold"])).mean(axis=0)
         for cell_type in cell_types]
    )

    row_order = [
        cell_types[index]
        for index in leaves_list(
            linkage(mean_matrix, method="average", metric="correlation")
        )
    ]
    marker_list = list(inputs.marker_names)
    marker_order = [
        marker_list[index]
        for index in leaves_list(
            linkage(mean_matrix.T, method="average", metric="correlation")
        )
    ]
    expected_rows = [str(value) for value in config["panel_a"]["cell_type_order"]]
    expected_markers = [str(value) for value in config["panel_a"]["marker_order"]]
    if row_order != expected_rows:
        raise FigureS03ValidationError(
            f"Panel A cell-type clustering order changed: {row_order}"
        )
    if marker_order != expected_markers:
        raise FigureS03ValidationError(
            f"Panel A marker clustering order changed: {marker_order}"
        )

    row_lookup = {label: index for index, label in enumerate(cell_types)}
    marker_lookup = {label: index for index, label in enumerate(marker_list)}
    minima = mean_matrix.min(axis=0)
    ranges = mean_matrix.max(axis=0) - minima
    scaled = np.divide(
        mean_matrix - minima,
        ranges,
        out=np.zeros_like(mean_matrix),
        where=ranges != 0,
    )
    records: list[dict[str, Any]] = []
    for cell_rank, cell_type in enumerate(expected_rows, start=1):
        row_index = row_lookup[cell_type]
        n_cells = int(np.sum(labels == cell_type))
        for marker_rank, marker in enumerate(expected_markers, start=1):
            marker_index = marker_lookup[marker]
            records.append(
                {
                    "cell_type": cell_type,
                    "cell_type_display_rank": cell_rank,
                    "marker": marker,
                    "marker_display_rank": marker_rank,
                    "n_cells": n_cells,
                    "mean_expression": float(mean_matrix[row_index, marker_index]),
                    "fraction_positive": float(fraction_matrix[row_index, marker_index]),
                    "marker_scaled_mean_expression": float(scaled[row_index, marker_index]),
                }
            )
    return pd.DataFrame.from_records(records)


def _render_panel_a(
    summary: pd.DataFrame,
    config: Mapping[str, Any],
) -> Any:
    style = config["panel_a"]["style"]
    shared = config["shared"]
    plt.rcParams.update({"font.family": str(shared["font_family"])})
    figure, axis = plt.subplots(figsize=tuple(style["figure_size_inches"]))
    figure.subplots_adjust(left=0.15, right=0.86, bottom=0.29, top=0.96)

    x = summary["marker_display_rank"].to_numpy(dtype=float) - 1
    y = summary["cell_type_display_rank"].to_numpy(dtype=float) - 1
    low, high = map(float, style["dot_size_range"])
    sizes = low + summary["fraction_positive"].to_numpy(dtype=float) * (high - low)
    points = axis.scatter(
        x,
        y,
        s=sizes,
        c=summary["marker_scaled_mean_expression"],
        cmap=str(style["color_map"]),
        norm=Normalize(0.0, 1.0),
        edgecolors=str(style["dot_edge_color"]),
        linewidths=float(style["dot_edge_width"]),
    )
    cell_types = (
        summary[["cell_type", "cell_type_display_rank"]]
        .drop_duplicates()
        .sort_values("cell_type_display_rank")
    )
    markers = (
        summary[["marker", "marker_display_rank"]]
        .drop_duplicates()
        .sort_values("marker_display_rank")
    )
    axis.set_xticks(np.arange(len(markers)))
    axis.set_xticklabels(markers["marker"], rotation=90, fontsize=8)
    axis.set_yticks(np.arange(len(cell_types)))
    axis.set_yticklabels(cell_types["cell_type"], fontsize=9)
    axis.set_xlim(-0.7, len(markers) - 0.3)
    axis.set_ylim(len(cell_types) - 0.3, -0.7)
    axis.set_xlabel("Protein Markers", fontsize=10)
    axis.set_ylabel("Cell Type", fontsize=10)
    axis.grid(False)

    size_handles = [
        Line2D(
            [],
            [],
            linestyle="",
            marker="o",
            markerfacecolor="#8c8c8c",
            markeredgecolor="#8c8c8c",
            markersize=np.sqrt(low + fraction * (high - low)),
            label=f"{int(fraction * 100)}",
        )
        for fraction in (0.2, 0.4, 0.6, 0.8, 1.0)
    ]
    axis.legend(
        handles=size_handles,
        title="Fraction of Cells\nin Group (%)",
        loc="upper left",
        bbox_to_anchor=(1.01, 0.48),
        ncol=5,
        frameon=False,
        fontsize=7,
        title_fontsize=9,
        handletextpad=0.1,
        columnspacing=0.4,
    )
    color_axis = figure.add_axes([0.875, 0.10, 0.105, 0.018])
    colorbar = figure.colorbar(points, cax=color_axis, orientation="horizontal")
    colorbar.set_ticks([0.0, 0.5, 1.0])
    colorbar.ax.tick_params(labelsize=7)
    color_axis.set_title("Mean Expression\nin Group", fontsize=9, pad=7)
    figure.text(
        0.012,
        0.97,
        "A",
        ha="left",
        va="top",
        fontsize=float(shared["panel_label_fontsize"]),
    )
    return figure


def run_panel_a(
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Compute, render, and provenance-lock Supplementary Figure S3A."""
    root = _resolve_repository_root(repository_root)
    resolved_config = _resolve_config_path(root, config_path)
    config = load_figure_config(resolved_config)
    inputs = load_inputs(repository_root=root, config_path=resolved_config)
    summary = build_panel_a_summary(inputs, config)
    outputs = config["panel_a"]["outputs"]
    summary_path = _output_path(root, str(outputs["summary_csv"]))
    summary.to_csv(summary_path, index=False)
    figure_paths = _save_figure(_render_panel_a(summary, config), root, outputs)
    provenance_path = _output_path(root, str(outputs["provenance_json"]))
    _json_dump(
        provenance_path,
        {
            "panel": "S3A",
            "status": "executed",
            "source": "Figure 2 validated B004 H5AD cohort",
            "source_h5ad_sha256": inputs.figure_02_h5ad_sha256,
            "source_cells": inputs.source_cell_count,
            "evaluation_cells": inputs.non_noise_cell_count,
            "raw_cell_types": 27,
            "markers": 45,
            "expression_transform": "none",
            "row_and_column_order": "average linkage; correlation distance",
            "dot_size": "fraction of cells with raw expression > 0",
            "dot_color": "raw group mean, min-max scaled within each marker",
            "summary_sha256": _dataframe_fingerprint(summary),
        },
    )
    return {
        "summary_csv": summary_path,
        **figure_paths,
        "provenance_json": provenance_path,
    }


def _build_panel_b_region_summary(
    inputs: FigureS03Inputs,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    truth_column = str(config["figure_02_dependency"]["truth_column"])
    order = [str(value) for value in config["panel_b"]["file_id_order"]]
    if set(order) != set(inputs.cells["File_ID"]) or len(order) != 8:
        raise FigureS03ValidationError("Panel B File_ID order differs from B004")
    rows: list[dict[str, Any]] = []
    for rank, file_id in enumerate(order, start=1):
        region = inputs.cells.loc[inputs.cells["File_ID"].eq(file_id)]
        rows.append(
            {
                "display_rank": rank,
                "File_ID": file_id,
                "n_cells": int(len(region)),
                "n_cell_types": int(region[truth_column].nunique()),
                "x_min": float(region["x"].min()),
                "x_max": float(region["x"].max()),
                "y_min": float(region["y"].min()),
                "y_max": float(region["y"].max()),
            }
        )
    return pd.DataFrame(rows)


def _render_panel_b(
    inputs: FigureS03Inputs,
    config: Mapping[str, Any],
    color_map: Mapping[str, str],
) -> Any:
    style = config["panel_b"]["style"]
    shared = config["shared"]
    truth_column = str(config["figure_02_dependency"]["truth_column"])
    plt.rcParams.update({"font.family": str(shared["font_family"])})
    figure, axes = plt.subplots(2, 4, figsize=tuple(style["figure_size_inches"]))
    for axis, file_id in zip(axes.flat, config["panel_b"]["file_id_order"], strict=True):
        region = inputs.cells.loc[inputs.cells["File_ID"].eq(str(file_id))]
        for cell_type in sorted(region[truth_column].unique()):
            group = region.loc[region[truth_column].eq(cell_type)]
            axis.scatter(
                group["x"],
                group["y"],
                s=float(style["point_size"]),
                color=color_map[str(cell_type)],
                alpha=float(style["point_alpha"]),
                linewidths=0,
                rasterized=True,
            )
        axis.set_aspect("equal")
        axis.axis("off")
    figure.subplots_adjust(
        left=0.02,
        right=0.99,
        bottom=0.02,
        top=0.91,
        wspace=float(style["horizontal_space"]),
        hspace=float(style["vertical_space"]),
    )
    figure.suptitle(str(config["panel_b"]["title"]), y=0.94, fontsize=15)
    figure.text(
        0.012,
        0.97,
        "B",
        ha="left",
        va="top",
        fontsize=float(shared["panel_label_fontsize"]),
    )
    return figure


def run_panel_b(
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Render all eight raw-label B004 tissue regions in a 2x4 montage."""
    root = _resolve_repository_root(repository_root)
    resolved_config = _resolve_config_path(root, config_path)
    config = load_figure_config(resolved_config)
    inputs = load_inputs(repository_root=root, config_path=resolved_config)
    truth_column = str(config["figure_02_dependency"]["truth_column"])
    colors = _load_color_map(root, config, inputs.cells[truth_column].unique())
    summary = _build_panel_b_region_summary(inputs, config)
    outputs = config["panel_b"]["outputs"]
    summary_path = _output_path(root, str(outputs["region_summary_csv"]))
    summary.to_csv(summary_path, index=False)
    figure_paths = _save_figure(_render_panel_b(inputs, config, colors), root, outputs)
    provenance_path = _output_path(root, str(outputs["provenance_json"]))
    _json_dump(
        provenance_path,
        {
            "panel": "S3B",
            "status": "executed",
            "source": "Figure 2 validated B004 H5AD cohort",
            "source_h5ad_sha256": inputs.figure_02_h5ad_sha256,
            "source_cells": inputs.source_cell_count,
            "raw_cell_types_including_noise": int(inputs.cells[truth_column].nunique()),
            "regions": 8,
            "coordinate_orientation": "native H5AD x/y; y is not inverted",
            "region_summary_sha256": _dataframe_fingerprint(summary),
        },
    )
    return {
        "region_summary_csv": summary_path,
        **figure_paths,
        "provenance_json": provenance_path,
    }


def build_panel_c_composition(
    inputs: FigureS03Inputs,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Return a complete long cluster-by-raw-truth composition table."""
    truth_column = str(config["figure_02_dependency"]["truth_column"])
    expected_types = [str(value) for value in config["panel_c"]["cell_type_order"]]
    observed_types = set(inputs.cells[truth_column].astype(str))
    if set(expected_types) != observed_types:
        raise FigureS03ValidationError("Panel C raw cell-type vocabulary changed")
    limits = {
        str(key): int(value)
        for key, value in config["panel_c"].get("displayed_cluster_limit", {}).items()
    }
    records: list[dict[str, Any]] = []
    for method_key, method_label in _method_specs(config):
        grouped = (
            inputs.cells.groupby([method_key, truth_column], sort=False)
            .size()
            .rename("cell_count")
            .reset_index()
        )
        totals = (
            grouped.groupby(method_key, sort=False)["cell_count"]
            .sum()
            .rename("cluster_total")
            .reset_index()
        )
        # Secondary string sorting makes equal-size clusters deterministic
        # without assuming that every assignment label is numeric.
        totals["_cluster_string"] = totals[method_key].astype(str)
        totals = totals.sort_values(
            ["cluster_total", "_cluster_string"],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True)
        totals["size_rank"] = np.arange(1, len(totals) + 1)
        limit = limits.get(method_key, len(totals))
        totals["displayed"] = totals["size_rank"].le(limit)
        grouped = grouped.merge(
            totals.drop(columns="_cluster_string"),
            on=method_key,
            how="left",
            validate="many_to_one",
        )
        type_rank = {cell_type: index + 1 for index, cell_type in enumerate(expected_types)}
        for row in grouped.itertuples(index=False):
            cell_type = str(getattr(row, truth_column))
            records.append(
                {
                    "method_key": method_key,
                    "method": method_label,
                    "cluster": str(getattr(row, method_key)),
                    "size_rank": int(row.size_rank),
                    "cell_type": cell_type,
                    "cell_type_stack_rank": type_rank[cell_type],
                    "cell_count": int(row.cell_count),
                    "cluster_total": int(row.cluster_total),
                    "displayed": bool(row.displayed),
                }
            )
    composition = pd.DataFrame.from_records(records)
    if int(composition.groupby(["method_key", "cluster"])["cluster_total"].first().sum()) != (
        inputs.source_cell_count * len(_method_specs(config))
    ):
        raise FigureS03ValidationError("Panel C composition totals do not cover every cell")
    return composition


def _render_panel_c(
    composition: pd.DataFrame,
    config: Mapping[str, Any],
    color_map: Mapping[str, str],
) -> Any:
    style = config["panel_c"]["style"]
    shared = config["shared"]
    plt.rcParams.update({"font.family": str(shared["font_family"])})
    figure, axes = plt.subplots(4, 1, figsize=tuple(style["figure_size_inches"]))
    for axis, (method_key, method_label) in zip(
        axes,
        _method_specs(config),
        strict=True,
    ):
        method = composition.loc[
            composition["method_key"].eq(method_key) & composition["displayed"]
        ].copy()
        cluster_order = (
            method[["cluster", "size_rank"]]
            .drop_duplicates()
            .sort_values("size_rank")
        )
        clusters = cluster_order["cluster"].tolist()
        lookup = {
            (str(row.cluster), str(row.cell_type)): int(row.cell_count)
            for row in method.itertuples(index=False)
        }
        x = np.arange(len(clusters))
        bottom = np.zeros(len(clusters), dtype=float)
        for cell_type in config["panel_c"]["cell_type_order"]:
            values = np.array(
                [lookup.get((cluster, str(cell_type)), 0) for cluster in clusters],
                dtype=float,
            )
            axis.bar(
                x,
                values,
                bottom=bottom,
                width=float(style["bar_width"]),
                color=color_map[str(cell_type)],
                edgecolor=str(style["bar_edge_color"]),
                linewidth=float(style["bar_edge_width"]),
                rasterized=True,
            )
            bottom += values
        axis.set_title(method_label, fontsize=11, pad=2)
        axis.set_ylabel("Cell Count", fontsize=8)
        axis.set_xlabel("Cluster", fontsize=8)
        axis.set_xticks([])
        axis.tick_params(axis="y", labelsize=7)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        total_clusters = int(
            composition.loc[composition["method_key"].eq(method_key), "cluster"].nunique()
        )
        if len(clusters) < total_clusters:
            axis.text(
                1.005,
                0.02,
                f"…\n{len(clusters)} largest\nof {total_clusters}",
                transform=axis.transAxes,
                ha="left",
                va="bottom",
                fontsize=7,
                color="#666666",
            )
    figure.subplots_adjust(left=0.085, right=0.94, bottom=0.06, top=0.95, hspace=0.42)
    figure.text(
        0.012,
        0.985,
        "C",
        ha="left",
        va="top",
        fontsize=float(shared["panel_label_fontsize"]),
    )
    return figure


def run_panel_c(
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Render selected-method cluster composition using raw B004 labels."""
    root = _resolve_repository_root(repository_root)
    resolved_config = _resolve_config_path(root, config_path)
    config = load_figure_config(resolved_config)
    inputs = load_inputs(repository_root=root, config_path=resolved_config)
    truth_column = str(config["figure_02_dependency"]["truth_column"])
    colors = _load_color_map(root, config, inputs.cells[truth_column].unique())
    composition = build_panel_c_composition(inputs, config)
    outputs = config["panel_c"]["outputs"]
    composition_path = _output_path(root, str(outputs["composition_csv"]))
    composition.to_csv(composition_path, index=False)
    figure_paths = _save_figure(
        _render_panel_c(composition, config, colors),
        root,
        outputs,
    )
    provenance_path = _output_path(root, str(outputs["provenance_json"]))
    _json_dump(
        provenance_path,
        {
            "panel": "S3C",
            "status": "executed",
            "source": "Figure 2 selected assignments and raw B004 H5AD labels",
            "source_cells": inputs.source_cell_count,
            "raw_cell_types_including_noise": 28,
            "cluster_counts": inputs.cluster_counts,
            "display_rule": "all clusters except FlowSOM, which displays the 60 largest of 300",
            "legacy_difference": (
                "The supplied composite used the older table-level PIXIE partition; "
                "this implementation uses Figure 2's canonical TIFF-derived PIXIE."
            ),
            "composition_sha256": _dataframe_fingerprint(composition),
        },
    )
    return {
        "composition_csv": composition_path,
        **figure_paths,
        "provenance_json": provenance_path,
    }


def load_panel_d_sweep(
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    """Load and exact-value validate the recovered historical FlowSOM sweep."""
    root = _resolve_repository_root(repository_root)
    resolved_config = _resolve_config_path(root, config_path)
    config = load_figure_config(resolved_config)

    source_path = root / str(config["panel_d"]["source_filename"])
    if not source_path.is_file():
        raise FileNotFoundError(f"Recovered Panel D sweep is missing: {source_path}")
    observed_hash = _sha256_file(source_path)
    expected_hash = str(config["panel_d"]["source_sha256"])
    if observed_hash != expected_hash:
        raise FigureS03ValidationError(
            f"Panel D sweep SHA-256 changed: {observed_hash} != {expected_hash}"
        )
    sweep = pd.read_csv(source_path)
    if list(sweep.columns) != ["k", "effective_k", "purity"]:
        raise FigureS03ValidationError(f"Unexpected Panel D columns: {list(sweep.columns)}")
    expected = pd.DataFrame(
        config["panel_d"]["expected_rows"],
        columns=["k", "effective_k", "purity"],
    )
    if sweep.shape != expected.shape or not np.allclose(
        sweep.to_numpy(dtype=float),
        expected.to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-15,
    ):
        raise FigureS03ValidationError("Panel D sweep values differ from the frozen contract")
    return sweep, source_path


def _render_panel_d(sweep: pd.DataFrame, config: Mapping[str, Any]) -> Any:
    style = config["panel_d"]["style"]
    shared = config["shared"]
    plt.rcParams.update({"font.family": str(shared["font_family"])})
    figure, axis = plt.subplots(figsize=tuple(style["figure_size_inches"]))
    axis.plot(
        sweep["k"],
        sweep["purity"] * 100.0,
        color=str(style["line_color"]),
        marker="o",
        markersize=float(style["marker_size"]),
        linewidth=1.2,
    )
    axis.set_xlabel(str(style["x_label"]), fontsize=9)
    axis.set_ylabel(str(style["y_label"]), fontsize=9)
    axis.tick_params(labelsize=8)
    axis.grid(True, color="#d9d9d9", linewidth=0.5, alpha=0.65)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    figure.subplots_adjust(left=0.18, right=0.97, bottom=0.18, top=0.96)
    figure.text(
        0.012,
        0.985,
        "D",
        ha="left",
        va="top",
        fontsize=float(shared["panel_label_fontsize"]),
    )
    return figure


def run_panel_d(
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Render the frozen exploratory FlowSOM cluster-count sweep."""
    root = _resolve_repository_root(repository_root)
    resolved_config = _resolve_config_path(root, config_path)
    config = load_figure_config(resolved_config)
    sweep, source_path = load_panel_d_sweep(
        repository_root=root,
        config_path=resolved_config,
    )
    outputs = config["panel_d"]["outputs"]
    sweep_path = _output_path(root, str(outputs["sweep_csv"]))
    sweep.to_csv(sweep_path, index=False)
    figure_paths = _save_figure(_render_panel_d(sweep, config), root, outputs)
    provenance_path = _output_path(root, str(outputs["provenance_json"]))
    _json_dump(
        provenance_path,
        {
            "panel": "S3D",
            "status": "executed_from_frozen_historical_table",
            "source_path": str(source_path),
            "source_sha256": _sha256_file(source_path),
            "purity_definition": "sum over clusters of the largest raw truth count, divided by N",
            "x_axis": "requested k; the k=350 request has effective_k=324",
            "provenance_status": str(config["panel_d"]["provenance_status"]),
            "generator_available": bool(config["panel_d"]["generator_available"]),
            "final_method_equivalent": bool(config["panel_d"]["final_method_equivalent"]),
            "scientific_gap": (
                "This exploratory sweep used variance selection and PCA. It is an "
                "archived illustration, not tuning or validation of the final Figure 2 "
                "45-marker, robust-scaled K=300 FlowSOM method."
            ),
            "sweep_sha256": _dataframe_fingerprint(sweep),
        },
    )
    return {
        "sweep_csv": sweep_path,
        **figure_paths,
        "provenance_json": provenance_path,
    }


def _majority_label(labels: pd.Series) -> str:
    counts = labels.astype(str).value_counts(sort=False).rename_axis("label").reset_index(name="n")
    counts = counts.sort_values(["n", "label"], ascending=[False, True], kind="stable")
    return str(counts.iloc[0]["label"])


def build_panel_e_metrics(
    inputs: FigureS03Inputs,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Compute all six Panel E metric distributions from canonical assignments."""
    from scipy.stats import entropy
    from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score

    truth_column = str(config["figure_02_dependency"]["truth_column"])
    excluded_label = str(config["figure_02_dependency"]["excluded_label"])
    cells = inputs.cells.loc[inputs.cells[truth_column].ne(excluded_label)].copy()
    if len(cells) != inputs.non_noise_cell_count:
        raise FigureS03ValidationError("Panel E non-Noise universe changed")
    cell_types = sorted(cells[truth_column].astype(str).unique())
    if len(cell_types) != 27:
        raise FigureS03ValidationError("Panel E must use 27 raw non-Noise labels")

    records: list[dict[str, Any]] = []
    for method_key, method_label in _method_specs(config):
        # Region-grain partition agreement. No cluster-majority mapping is used.
        for file_id, region in cells.groupby("File_ID", sort=True):
            truth = region[truth_column].astype(str).to_numpy()
            clusters = region[method_key].astype(str).to_numpy()
            records.extend(
                [
                    {
                        "metric": "adjusted_rand_index",
                        "metric_label": "Adjusted Rand Index",
                        "method_key": method_key,
                        "method": method_label,
                        "grain": "region",
                        "observation_id": str(file_id),
                        "value": float(adjusted_rand_score(truth, clusters)),
                        "raw_value": float(adjusted_rand_score(truth, clusters)),
                        "n_cells": int(len(region)),
                        "color_group": "",
                    },
                    {
                        "metric": "adjusted_mutual_information",
                        "metric_label": "Adjusted Mutual Information",
                        "method_key": method_key,
                        "method": method_label,
                        "grain": "region",
                        "observation_id": str(file_id),
                        "value": float(adjusted_mutual_info_score(truth, clusters)),
                        "raw_value": float(adjusted_mutual_info_score(truth, clusters)),
                        "n_cells": int(len(region)),
                        "color_group": "",
                    },
                ]
            )

        # Cluster-grain composition metrics and the global retrospective
        # cluster-majority map used for per-cell-type F1/recall.
        majority_by_cluster: dict[Any, str] = {}
        for cluster, group in cells.groupby(method_key, sort=True):
            counts = group[truth_column].astype(str).value_counts(sort=False)
            probabilities = counts.to_numpy(dtype=float) / float(counts.sum())
            majority = _majority_label(group[truth_column])
            majority_by_cluster[cluster] = majority
            cluster_id = str(cluster)
            records.extend(
                [
                    {
                        "metric": "shannon_index",
                        "metric_label": "Shannon Index",
                        "method_key": method_key,
                        "method": method_label,
                        "grain": "cluster",
                        "observation_id": cluster_id,
                        "value": float(entropy(probabilities)),
                        "raw_value": float(entropy(probabilities)),
                        "n_cells": int(len(group)),
                        "color_group": majority,
                    },
                    {
                        "metric": "purity_percent",
                        "metric_label": "Purity (%)",
                        "method_key": method_key,
                        "method": method_label,
                        "grain": "cluster",
                        "observation_id": cluster_id,
                        "value": float(100.0 * counts.max() / counts.sum()),
                        "raw_value": float(counts.max() / counts.sum()),
                        "n_cells": int(len(group)),
                        "color_group": majority,
                    },
                ]
            )
        predicted = cells[method_key].map(majority_by_cluster).astype(str)
        truth = cells[truth_column].astype(str)
        for cell_type in cell_types:
            truth_positive = truth.eq(cell_type)
            predicted_positive = predicted.eq(cell_type)
            true_positive = int((truth_positive & predicted_positive).sum())
            false_negative = int((truth_positive & ~predicted_positive).sum())
            false_positive = int((~truth_positive & predicted_positive).sum())
            recall = (
                true_positive / (true_positive + false_negative)
                if true_positive + false_negative
                else 0.0
            )
            precision = (
                true_positive / (true_positive + false_positive)
                if true_positive + false_positive
                else 0.0
            )
            f1 = (
                2.0 * precision * recall / (precision + recall)
                if precision + recall
                else 0.0
            )
            records.extend(
                [
                    {
                        "metric": "f1_score",
                        "metric_label": "F1 Score",
                        "method_key": method_key,
                        "method": method_label,
                        "grain": "cell_type",
                        "observation_id": cell_type,
                        "value": float(f1),
                        "raw_value": float(f1),
                        "n_cells": int(truth_positive.sum()),
                        "color_group": cell_type,
                    },
                    {
                        "metric": "recall",
                        "metric_label": "Recall",
                        "method_key": method_key,
                        "method": method_label,
                        "grain": "cell_type",
                        "observation_id": cell_type,
                        "value": float(recall),
                        "raw_value": float(recall),
                        "n_cells": int(truth_positive.sum()),
                        "color_group": cell_type,
                    },
                ]
            )

    metrics = pd.DataFrame.from_records(records)
    expected_observations = {
        "adjusted_rand_index": 8 * 4,
        "adjusted_mutual_information": 8 * 4,
        "shannon_index": sum(inputs.cluster_counts.values()),
        "f1_score": 27 * 4,
        "recall": 27 * 4,
        "purity_percent": sum(inputs.cluster_counts.values()),
    }
    observed = metrics.groupby("metric").size().to_dict()
    if observed != expected_observations:
        raise FigureS03ValidationError(
            f"Panel E observation counts changed: {observed} != {expected_observations}"
        )
    return metrics


def _render_panel_e(
    metrics: pd.DataFrame,
    config: Mapping[str, Any],
    color_map: Mapping[str, str],
) -> Any:
    style = config["panel_e"]["style"]
    shared = config["shared"]
    methods = [label for _, label in _method_specs(config)]
    plt.rcParams.update({"font.family": str(shared["font_family"])})
    figure, axes = plt.subplots(1, 6, figsize=tuple(style["figure_size_inches"]))
    rng = np.random.default_rng(int(shared["random_seed"]))
    for axis, metric_spec in zip(axes, config["panel_e"]["metrics"], strict=True):
        metric_key = str(metric_spec["key"])
        metric = metrics.loc[metrics["metric"].eq(metric_key)]
        data = [
            metric.loc[metric["method"].eq(method), "value"].to_numpy(dtype=float)
            for method in methods
        ]
        boxplot = axis.boxplot(
            data,
            tick_labels=methods,
            patch_artist=True,
            widths=float(style["box_width"]),
            medianprops={"color": "black", "linewidth": 1.1},
            whiskerprops={"color": "black", "linewidth": 0.8},
            capprops={"color": "black", "linewidth": 0.8},
            flierprops={"marker": "", "markersize": 0},
        )
        for patch in boxplot["boxes"]:
            patch.set_facecolor("none")
            patch.set_edgecolor("black")
            patch.set_linewidth(0.8)
        for method_index, method in enumerate(methods, start=1):
            observations = metric.loc[metric["method"].eq(method)].copy()
            jitter = rng.uniform(
                -float(style["jitter_width"]),
                float(style["jitter_width"]),
                size=len(observations),
            )
            if metric_key in {"adjusted_rand_index", "adjusted_mutual_information"}:
                colors = ["#222222"] * len(observations)
            else:
                colors = [
                    color_map[str(group)]
                    for group in observations["color_group"].astype(str)
                ]
            axis.scatter(
                np.full(len(observations), method_index, dtype=float) + jitter,
                observations["value"],
                c=colors,
                s=float(style["point_size"]),
                alpha=0.95,
                linewidths=0,
                zorder=3,
            )
        axis.set_ylabel(str(metric_spec["label"]), fontsize=8)
        axis.tick_params(axis="x", labelrotation=0, labelsize=7)
        axis.tick_params(axis="y", labelsize=7)
        axis.grid(axis="y", color="#d9d9d9", linewidth=0.5, alpha=0.55)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        if metric_key in {"f1_score", "recall"}:
            axis.set_ylim(-0.05, 1.05)
        elif metric_key == "purity_percent":
            axis.set_ylim(0.0, 105.0)
            axis.set_yticks([0, 25, 50, 75, 100])
        axis.set_xlabel("Clustering Method", fontsize=7)
    figure.subplots_adjust(left=0.035, right=0.995, bottom=0.22, top=0.95, wspace=0.55)
    figure.text(
        0.005,
        0.99,
        "E",
        ha="left",
        va="top",
        fontsize=float(shared["panel_label_fontsize"]),
    )
    return figure


def run_panel_e(
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Compute and render the six clustering-metric distributions in Panel E."""
    root = _resolve_repository_root(repository_root)
    resolved_config = _resolve_config_path(root, config_path)
    config = load_figure_config(resolved_config)
    inputs = load_inputs(repository_root=root, config_path=resolved_config)
    truth_column = str(config["figure_02_dependency"]["truth_column"])
    colors = _load_color_map(root, config, inputs.cells[truth_column].unique())
    metrics = build_panel_e_metrics(inputs, config)
    outputs = config["panel_e"]["outputs"]
    metrics_path = _output_path(root, str(outputs["metrics_csv"]))
    metrics.to_csv(metrics_path, index=False)
    figure_paths = _save_figure(_render_panel_e(metrics, config, colors), root, outputs)
    provenance_path = _output_path(root, str(outputs["provenance_json"]))
    medians = (
        metrics.groupby(["metric", "method"], sort=False)["value"]
        .median()
        .unstack("method")
        .to_dict(orient="index")
    )
    _json_dump(
        provenance_path,
        {
            "panel": "S3E",
            "status": "executed",
            "source": "Figure 2 selected assignments and raw B004 H5AD labels",
            "source_cells": inputs.source_cell_count,
            "evaluation_cells": inputs.non_noise_cell_count,
            "raw_cell_types": 27,
            "cluster_counts": inputs.cluster_counts,
            "metrics": {
                "ARI_AMI": "one value per File_ID, comparing raw truth with cluster IDs",
                "Shannon": "natural-log entropy of raw truth composition per cluster",
                "F1_recall": "one-vs-rest after global cluster-majority raw-truth mapping",
                "purity": "unweighted per-cluster largest raw-truth fraction, displayed as percent",
            },
            "legacy_difference": (
                "The supplied composite's PIXIE points used an older table-level "
                "partition; these values use Figure 2's TIFF-derived PIXIE."
            ),
            "medians": medians,
            "metrics_sha256": _dataframe_fingerprint(metrics),
        },
    )
    return {
        "metrics_csv": metrics_path,
        **figure_paths,
        "provenance_json": provenance_path,
    }


__all__ = [
    "FigureS03Inputs",
    "FigureS03ValidationError",
    "build_panel_a_summary",
    "build_panel_c_composition",
    "build_panel_e_metrics",
    "load_figure_config",
    "load_inputs",
    "load_panel_d_sweep",
    "run_panel_a",
    "run_panel_b",
    "run_panel_c",
    "run_panel_d",
    "run_panel_e",
]
