"""Supplementary Figure 2 views of the shared Figure 4 Leiden--GPT analysis.

Panel A renders the unnormalized cell-count confusion matrix. Panel B renders
the per-Leiden-cluster arithmetic decomposition into observed correctness,
annotation loss, and clustering loss, ordered as in the supplied reference.

Both runners call :func:`figure_04.load_analysis`. Consequently they use one
provenance-locked OpenAI/reasoning/optimized-Leiden annotation result and keep
Figure 4's fail-closed credential policy. A placeholder API key is rejected
before H5AD/cache access or any Supplementary Figure 2 output is written.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from llm_spatial_omics_clustering.figure_04 import (
    Figure04Analysis,
    load_analysis as load_figure04_analysis,
    load_figure_config as load_figure04_config,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class FigureS02ValidationError(ValueError):
    """Raised when an S2 dependency or derived table violates its contract."""


def load_figure_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and minimally validate the Supplementary Figure 2 contract."""
    path = Path(config_path) if config_path else REPOSITORY_ROOT / "configs/figure_s02.yaml"
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or int(config.get("supplementary_figure", -1)) != 2:
        raise FigureS02ValidationError(f"Invalid Supplementary Figure 2 config: {path}")
    if not {"panel_a", "panel_b"}.issubset(config):
        raise FigureS02ValidationError(f"Config does not define Panels A and B: {path}")
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
        return repository_root / "configs/figure_s02.yaml"
    path = Path(config_path).expanduser()
    return (repository_root / path).resolve() if not path.is_absolute() else path.resolve()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataframe_fingerprint(frame: pd.DataFrame) -> str:
    hashes = pd.util.hash_pandas_object(frame, index=True).to_numpy(dtype=np.uint64)
    return hashlib.sha256(hashes.tobytes()).hexdigest()


def _relative_path(path: Path, repository_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repository_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _json_dump(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _output_path(repository_root: Path, configured_path: str) -> Path:
    path = Path(configured_path)
    path = path if path.is_absolute() else repository_root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _validate_figure04_dependency(
    config: Mapping[str, Any],
    figure_04_config: Mapping[str, Any],
) -> None:
    """Ensure S2 has not drifted from Figure 4's single selected analysis."""
    expected = config["figure_04_dependency"]
    dependency = figure_04_config["figure_03_dependency"]
    observed_dependency = {
        "expected_provider": str(dependency["provider"]),
        "expected_condition": str(dependency["condition"]),
        "expected_method": str(dependency["method"]),
        "expected_marker_state": str(dependency["marker_state"]),
        "expected_source_cells": int(dependency["expected_source_cells"]),
        "expected_leiden_clusters": int(dependency["expected_clusters"]),
        "expected_regions": int(dependency["expected_regions"]),
    }
    expected_dependency = {
        key: (int(value) if key.startswith("expected_") and isinstance(value, int) else str(value))
        for key, value in expected.items()
        if key in observed_dependency
    }
    if observed_dependency != expected_dependency:
        raise FigureS02ValidationError(
            "Figure 4 annotation dependency differs from S2: "
            f"observed={observed_dependency}, expected={expected_dependency}"
        )
    evaluation = figure_04_config["evaluation"]
    observed_evaluation = {
        "expected_source_cells": int(evaluation["expected_cells"]),
        "expected_noise_cells": int(evaluation["expected_noise_cells"]),
        "expected_truth_classes": int(evaluation["expected_truth_classes"]),
    }
    expected_evaluation = {
        key: int(expected[key])
        for key in observed_evaluation
    }
    if observed_evaluation != expected_evaluation:
        raise FigureS02ValidationError(
            "Figure 4 evaluation universe differs from S2: "
            f"observed={observed_evaluation}, expected={expected_evaluation}"
        )


def load_analysis(
    api_keys: Mapping[str, str],
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    force_refresh: bool = False,
) -> tuple[Figure04Analysis, dict[str, Any], Path]:
    """Load S2's one shared Figure 4 analysis after dependency validation."""
    root = _resolve_repository_root(repository_root)
    resolved_config = _resolve_config_path(root, config_path)
    config = load_figure_config(resolved_config)
    figure_04_path = (root / str(config["figure_04_dependency"]["config_path"])).resolve()
    figure_04_config = load_figure04_config(figure_04_path)
    _validate_figure04_dependency(config, figure_04_config)
    analysis = load_figure04_analysis(
        api_keys,
        repository_root=root,
        config_path=figure_04_path,
        force_refresh=force_refresh,
    )
    return analysis, config, figure_04_path


def prepare_panel_a_matrix(
    analysis: Figure04Analysis,
    config: Mapping[str, Any],
    figure_04_config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate and return the 21-by-21 unnormalized count matrix."""
    matrix = analysis.confusion_counts.copy()
    class_order = [str(value) for value in figure_04_config["evaluation"]["class_order"]]
    if matrix.index.astype(str).tolist() != class_order:
        raise FigureS02ValidationError("Panel A truth-row order differs from Figure 4")
    if matrix.columns.astype(str).tolist() != class_order:
        raise FigureS02ValidationError("Panel A prediction-column order differs from Figure 4")
    expected_classes = int(config["figure_04_dependency"]["expected_truth_classes"])
    if matrix.shape != (expected_classes, expected_classes):
        raise FigureS02ValidationError(
            f"Panel A matrix has shape {matrix.shape}; expected {(expected_classes,) * 2}"
        )
    if not np.issubdtype(matrix.to_numpy().dtype, np.integer):
        numeric = matrix.to_numpy(dtype=float)
        if not np.allclose(numeric, np.rint(numeric), rtol=0.0, atol=0.0):
            raise FigureS02ValidationError("Panel A contains non-integer cell counts")
        matrix = matrix.astype(np.int64)
    expected_cells = int(config["figure_04_dependency"]["expected_source_cells"])
    if int(matrix.to_numpy(dtype=np.int64).sum()) != expected_cells:
        raise FigureS02ValidationError("Panel A count matrix does not cover all source cells")
    return matrix


def prepare_panel_b_table(
    cluster_stats: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Validate and display-order the 55 cluster outcome decompositions."""
    required = {
        "cluster",
        "n_cells",
        "majority_truth",
        "predicted_label",
        "purity",
        "final_correct",
        "annotation_loss",
        "clustering_loss",
    }
    if missing := required.difference(cluster_stats.columns):
        raise FigureS02ValidationError(f"Panel B cluster table is missing: {sorted(missing)}")
    table = cluster_stats.loc[:, sorted(required)].copy()
    expected_clusters = int(config["figure_04_dependency"]["expected_leiden_clusters"])
    if len(table) != expected_clusters or table["cluster"].nunique() != expected_clusters:
        raise FigureS02ValidationError(
            f"Panel B requires {expected_clusters} distinct Leiden clusters"
        )
    if table["cluster"].isna().any() or table["n_cells"].isna().any():
        raise FigureS02ValidationError("Panel B has null cluster IDs or cell counts")
    components = table[["final_correct", "annotation_loss", "clustering_loss"]]
    if not np.allclose(
        components.sum(axis=1).to_numpy(dtype=float),
        1.0,
        rtol=0.0,
        atol=1e-10,
    ):
        raise FigureS02ValidationError("Panel B arithmetic components do not sum to one")
    if (components.to_numpy(dtype=float) < -1e-12).any():
        raise FigureS02ValidationError("Panel B has a negative arithmetic component")
    if int(table["n_cells"].sum()) != int(
        config["figure_04_dependency"]["expected_source_cells"]
    ):
        raise FigureS02ValidationError("Panel B cluster sizes do not cover all source cells")

    sort_config = config["panel_b"]["sort"]
    columns = [str(value) for value in sort_config["columns"]]
    ascending = [bool(value) for value in sort_config["ascending"]]
    table = table.sort_values(columns, ascending=ascending, kind="mergesort").reset_index(drop=True)
    table.insert(0, "display_rank", np.arange(1, len(table) + 1))
    template = str(config["panel_b"]["row_label_template"])
    table.insert(
        1,
        "display_label",
        [
            template.format(
                cluster=int(row.cluster),
                majority_truth=str(row.majority_truth),
                predicted=str(row.predicted_label),
            )
            for row in table.itertuples(index=False)
        ],
    )
    return table


def render_panel_a(
    matrix: pd.DataFrame,
    config: Mapping[str, Any],
) -> Any:
    """Render the S2A count heatmap."""
    style = config["panel_a"]["style"]
    shared = config["shared_style"]
    plt.rcParams.update({"font.family": str(shared["font_family"])})
    figure, axis = plt.subplots(figsize=tuple(style["figure_size_inches"]))
    image = axis.imshow(
        matrix.to_numpy(dtype=float),
        cmap=str(shared["confusion_cmap"]),
        vmin=0.0,
        vmax=float(matrix.to_numpy(dtype=float).max()),
        interpolation="nearest",
        aspect="equal",
    )
    labels = matrix.index.astype(str).tolist()
    axis.set_xticks(
        np.arange(len(labels)),
        labels=labels,
        rotation=90,
        fontsize=float(style["tick_label_fontsize"]),
    )
    axis.set_yticks(
        np.arange(len(labels)),
        labels=labels,
        fontsize=float(style["tick_label_fontsize"]),
    )
    axis.set_xlabel(
        "Predicted Cell Type Labels",
        fontsize=float(style["axis_label_fontsize"]),
        labelpad=12,
    )
    axis.set_ylabel(
        "Ground Truth Cell Type Label",
        fontsize=float(style["axis_label_fontsize"]),
    )
    axis.set_title(str(config["panel_a"]["title"]), fontsize=11, pad=14)
    colorbar = figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    colorbar.set_label(
        str(style["colorbar_label"]),
        rotation=270,
        labelpad=18,
        fontsize=float(style["axis_label_fontsize"]),
    )
    colorbar.ax.tick_params(labelsize=float(style["tick_label_fontsize"]))
    figure.text(
        0.015,
        0.98,
        "A",
        fontsize=float(shared["panel_label_fontsize"]),
        ha="left",
        va="top",
    )
    figure.subplots_adjust(left=0.23, bottom=0.30, right=0.90, top=0.91)
    return figure


def render_panel_b(
    table: pd.DataFrame,
    config: Mapping[str, Any],
) -> Any:
    """Render the sorted per-cluster arithmetic decomposition."""
    style = config["panel_b"]["style"]
    shared = config["shared_style"]
    plt.rcParams.update({"font.family": str(shared["font_family"])})
    figure, axis = plt.subplots(figsize=tuple(style["figure_size_inches"]))
    y = np.arange(len(table))
    components = [
        ("final_correct", str(shared["correct_color"])),
        ("annotation_loss", str(shared["annotation_loss_color"])),
        ("clustering_loss", str(shared["clustering_loss_color"])),
    ]
    left = np.zeros(len(table), dtype=float)
    for column, color in components:
        values = table[column].to_numpy(dtype=float)
        axis.barh(
            y,
            values,
            left=left,
            color=color,
            edgecolor="white",
            linewidth=0.25,
            height=float(style["bar_height"]),
            zorder=2,
        )
        left += values
    axis.set_yticks(
        y,
        labels=table["display_label"].astype(str),
        fontsize=float(style["tick_label_fontsize"]),
    )
    axis.invert_yaxis()
    axis.set_xlim(0.0, 1.0)
    ticks = np.linspace(0.0, 1.0, 6)
    axis.set_xticks(ticks, labels=[f"{int(value * 100)}%" for value in ticks], fontsize=8)
    axis.set_xlabel(str(style["x_axis_label"]), fontsize=9)
    axis.set_ylabel(str(style["y_axis_label"]), fontsize=9, labelpad=10)
    axis.set_title(str(config["panel_b"]["title"]), fontsize=10, pad=12)
    axis.set_axisbelow(True)
    axis.grid(axis="x", color="#E5E7EB", linewidth=0.55)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    figure.text(
        0.015,
        0.99,
        "B",
        fontsize=float(shared["panel_label_fontsize"]),
        ha="left",
        va="top",
    )
    figure.subplots_adjust(left=0.43, right=0.98, top=0.965, bottom=0.065)
    return figure


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


def _analysis_provenance(
    analysis: Figure04Analysis,
    repository_root: Path,
) -> dict[str, Any]:
    annotation = analysis.annotation_result
    return {
        "evaluation_universe": "all 220,082 B004 source cells including Noise",
        "source_cell_count": int(len(analysis.cells)),
        "noise_cell_count": int(analysis.cells["truth"].eq("Noise").sum()),
        "region_count": int(analysis.cells["File_ID"].nunique()),
        "leiden_cluster_count": int(analysis.cells["cluster_leiden"].nunique()),
        "truth_class_count": int(analysis.cells["truth"].nunique()),
        "prediction_sha256": analysis.prediction_sha256,
        "selection_lock_path": (
            _relative_path(analysis.selection_lock_path, repository_root)
            if analysis.selection_lock_path is not None
            else None
        ),
        "selection_lock_sha256": analysis.selection_lock_sha256,
        "llm_annotation": {
            "provider": annotation.provider,
            "condition": annotation.condition,
            "method": annotation.method,
            "marker_state": annotation.marker_state,
            "requested_model_id": annotation.requested_model_id,
            "returned_model_id": annotation.returned_model_id,
            "cache_path": _relative_path(annotation.cache_path, repository_root),
            "cache_contract_sha256": annotation.cache_contract_sha256,
            "annotation_sha256": annotation.annotation_sha256,
            "prompt_sha256": annotation.prompt_sha256,
            "marker_summary_sha256": annotation.marker_summary_sha256,
        },
    }


def run_panel_a(
    api_keys: Mapping[str, str],
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate S2A only after Figure 4 resolves its selected annotation."""
    root = _resolve_repository_root(repository_root)
    analysis, config, figure_04_path = load_analysis(
        api_keys,
        repository_root=root,
        config_path=config_path,
        force_refresh=force_refresh,
    )
    figure_04_config = load_figure04_config(figure_04_path)
    matrix = prepare_panel_a_matrix(analysis, config, figure_04_config)
    outputs = config["panel_a"]["outputs"]
    matrix_path = _output_path(root, str(outputs["matrix_csv"]))
    matrix.to_csv(matrix_path)
    figure_paths = _save_figure(render_panel_a(matrix, config), root, outputs)
    provenance_path = _output_path(root, str(outputs["provenance_json"]))
    _json_dump(
        provenance_path,
        {
            "supplementary_figure": 2,
            "panel": "A",
            "status": "executed",
            "figure_04_config_path": _relative_path(figure_04_path, root),
            "figure_04_config_sha256": _sha256_file(figure_04_path),
            "matrix_semantics": config["panel_a"]["matrix_semantics"],
            "matrix_sha256": _dataframe_fingerprint(matrix),
            "reference_composite_status": config["reference_composite"]["provenance_status"],
            "legacy_panel_a_warning": (
                "The reference count matrix used a file labelled Leiden that is "
                "byte-identical to the legacy Gemini map; it is not reused here."
            ),
            **_analysis_provenance(analysis, root),
        },
    )
    return {
        "matrix_csv": matrix_path,
        **figure_paths,
        "provenance_json": provenance_path,
    }


def run_panel_b(
    api_keys: Mapping[str, str],
    *,
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate S2B only after Figure 4 resolves its selected annotation."""
    root = _resolve_repository_root(repository_root)
    analysis, config, figure_04_path = load_analysis(
        api_keys,
        repository_root=root,
        config_path=config_path,
        force_refresh=force_refresh,
    )
    table = prepare_panel_b_table(analysis.cluster_stats, config)
    outputs = config["panel_b"]["outputs"]
    table_path = _output_path(root, str(outputs["cluster_stats_csv"]))
    table.to_csv(table_path, index=False)
    figure_paths = _save_figure(render_panel_b(table, config), root, outputs)
    provenance_path = _output_path(root, str(outputs["provenance_json"]))
    _json_dump(
        provenance_path,
        {
            "supplementary_figure": 2,
            "panel": "B",
            "status": "executed",
            "figure_04_config_path": _relative_path(figure_04_path, root),
            "figure_04_config_sha256": _sha256_file(figure_04_path),
            "cluster_order": config["panel_b"]["sort"],
            "row_label_semantics": config["panel_b"]["row_label_semantics"],
            "decomposition": config["panel_b"]["decomposition"],
            "cluster_table_sha256": _dataframe_fingerprint(table),
            "reference_composite_status": config["reference_composite"]["provenance_status"],
            "legacy_panel_b_warning": (
                "The reference gpt52 mapping was generated by deterministic "
                "marker-driven expert logic without an external API call; it "
                "is not reused here."
            ),
            **_analysis_provenance(analysis, root),
        },
    )
    return {
        "cluster_stats_csv": table_path,
        **figure_paths,
        "provenance_json": provenance_path,
    }


__all__ = [
    "FigureS02ValidationError",
    "load_analysis",
    "load_figure_config",
    "prepare_panel_a_matrix",
    "prepare_panel_b_table",
    "render_panel_a",
    "render_panel_b",
    "run_panel_a",
    "run_panel_b",
]
