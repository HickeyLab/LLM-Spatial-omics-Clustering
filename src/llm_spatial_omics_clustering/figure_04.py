"""Reproducible Figure 4 Leiden-GPT end-to-end evaluation.

Figure 4 deliberately does not rerun Leiden or choose a new LLM annotation.
Panels B--F reuse the single optimized, reasoning-enabled OpenAI/Leiden result
defined by Figure 3. They evaluate that result on all 220,082 B004 source
cells, including cells whose reference label is ``Noise``.

Every LLM-dependent runner validates the API key before loading the H5AD,
reading an annotation cache, or writing an output. The checked-in notebook can
therefore contain a placeholder key without accidentally creating biological
results or making a paid request.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from llm_spatial_omics_clustering.figure_03 import (
    AnnotationResult,
    Figure03Inputs,
    ensure_annotation,
    load_figure03_inputs,
    load_figure_config as load_figure03_config,
    require_api_keys,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PANEL_KEYS = tuple(f"panel_{letter}" for letter in "abcdef")


class Figure04ValidationError(ValueError):
    """Raised when a Figure 4 dependency or derived result violates its contract."""


@dataclass(frozen=True)
class Figure04Analysis:
    """One validated full-cohort prediction table and all shared metrics."""

    cells: pd.DataFrame
    annotation_result: AnnotationResult
    figure_03_inputs: Figure03Inputs
    confusion_counts: pd.DataFrame
    confusion_row_normalized: pd.DataFrame
    pooled_f1: pd.DataFrame
    regional_f1: pd.DataFrame
    cluster_stats: pd.DataFrame
    aggregate: pd.DataFrame
    prediction_sha256: str
    selection_lock_path: Path | None = None
    selection_lock_sha256: str | None = None


def load_figure_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and minimally validate the tracked Figure 4 configuration."""
    path = Path(config_path) if config_path else REPOSITORY_ROOT / "configs/figure_04.yaml"
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or int(config.get("figure", -1)) != 4:
        raise Figure04ValidationError(f"Invalid Figure 4 configuration: {path}")
    panels = config.get("panels")
    if not isinstance(panels, dict) or set(panels) != set(PANEL_KEYS):
        raise Figure04ValidationError(
            f"Figure 4 configuration must define exactly Panels A--F: {path}"
        )
    evaluation = config.get("evaluation", {})
    class_order = [str(label) for label in evaluation.get("class_order", [])]
    if len(class_order) != int(evaluation.get("expected_truth_classes", -1)):
        raise Figure04ValidationError(
            "Figure 4 class_order length differs from expected_truth_classes"
        )
    if len(class_order) != len(set(class_order)) or "Noise" not in class_order:
        raise Figure04ValidationError(
            "Figure 4 class_order must contain unique labels including Noise"
        )
    return config


def _resolve_repository_root(repository_root: str | Path | None) -> Path:
    return Path(repository_root).expanduser().resolve() if repository_root else REPOSITORY_ROOT


def _resolve_config_path(
    repository_root: Path,
    config_path: str | Path | None,
) -> Path:
    if config_path is None:
        return repository_root / "configs/figure_04.yaml"
    path = Path(config_path).expanduser()
    return (repository_root / path).resolve() if not path.is_absolute() else path.resolve()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataframe_fingerprint(frame: pd.DataFrame) -> str:
    hashes = pd.util.hash_pandas_object(frame, index=False).to_numpy(dtype=np.uint64)
    return _sha256_bytes(hashes.tobytes())


def _json_dump(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _json_sha256(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(serialized.encode("utf-8"))


def _relative_path(path: Path, repository_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repository_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _validate_annotation_cache_integrity(result: AnnotationResult) -> None:
    """Detect accidental edits to the selected Figure 3 cache annotations."""
    try:
        cached = json.loads(result.cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Figure04ValidationError(
            f"Cannot validate Figure 3 annotation cache: {result.cache_path}"
        ) from exc
    expected = {
        "cache_contract_sha256": result.cache_contract_sha256,
        "annotation_sha256": result.annotation_sha256,
        "requested_model_id": result.requested_model_id,
        "returned_model_id": result.returned_model_id,
    }
    observed = {key: cached.get(key) for key in expected}
    if observed != expected:
        raise Figure04ValidationError(
            "Figure 3 annotation cache integrity fields do not match the "
            "validated AnnotationResult. Regenerate or restore the cache before "
            "running Figure 4."
        )


def _validate_or_create_selection_lock(
    result: AnnotationResult,
    repository_root: Path,
) -> tuple[Path, str]:
    """Freeze the first selected mapping so later Figure 4 cells cannot drift."""
    contract = {
        "provider": result.provider,
        "condition": result.condition,
        "method": result.method,
        "marker_state": result.marker_state,
        "requested_model_id": result.requested_model_id,
        "returned_model_id": result.returned_model_id,
        "cache_contract_sha256": result.cache_contract_sha256,
        "annotation_sha256": result.annotation_sha256,
        "prompt_sha256": result.prompt_sha256,
        "marker_summary_sha256": result.marker_summary_sha256,
    }
    contract_sha256 = _json_sha256(contract)
    lock_path = (
        repository_root
        / "outputs/figure_04/cache"
        / (
            f"selected_{result.provider}_{result.condition}_"
            f"{result.method}_{result.marker_state}.json"
        )
    )
    if lock_path.is_file():
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise Figure04ValidationError(
                f"Cannot validate the Figure 4 selection lock: {lock_path}"
            ) from exc
        if (
            existing.get("selection_contract_sha256") != contract_sha256
            or existing.get("selection_contract") != contract
        ):
            raise Figure04ValidationError(
                "Figure 3's selected Leiden-GPT annotation differs from the "
                "mapping already locked for Figure 4. Restore the selected cache "
                "or perform an explicit, author-approved selection-lock reset; "
                "panels will not silently mix mappings."
            )
    else:
        _json_dump(
            lock_path,
            {
                "selection_contract_sha256": contract_sha256,
                "selection_contract": contract,
                "purpose": (
                    "Freeze one Figure 3 Leiden-GPT annotation mapping across "
                    "all Figure 4 biological panels."
                ),
            },
        )
    return lock_path, _sha256_file(lock_path)


def _validate_dependency_contract(
    config: Mapping[str, Any],
    figure_03_config: Mapping[str, Any],
) -> None:
    dependency = config["figure_03_dependency"]
    method = str(dependency["method"])
    expected_clusters = int(dependency["expected_clusters"])
    observed_contract = figure_03_config["figure_02_dependency"]["expected_methods"][method]
    if int(observed_contract["expected_clusters"]) != expected_clusters:
        raise Figure04ValidationError(
            "Figure 3 Leiden cluster count differs from Figure 4's frozen contract"
        )
    provider = str(dependency["provider"])
    condition = str(dependency["condition"])
    if provider not in figure_03_config["providers"]:
        raise Figure04ValidationError(f"Unknown Figure 3 provider: {provider!r}")
    if condition not in figure_03_config["providers"][provider]["conditions"]:
        raise Figure04ValidationError(
            f"Unknown Figure 3 provider condition: {provider}/{condition}"
        )
    figure_03_evaluation = figure_03_config["evaluation"]
    expected_source = int(dependency["expected_source_cells"])
    if int(figure_03_evaluation["expected_source_cells"]) != expected_source:
        raise Figure04ValidationError(
            "Figure 3 source-cell count differs from Figure 4's frozen contract"
        )
    figure_04_labels = set(str(label) for label in config["evaluation"]["class_order"])
    figure_03_labels = set(str(label) for label in figure_03_evaluation["allowed_labels"])
    if figure_04_labels - {"Noise"} != figure_03_labels:
        raise Figure04ValidationError(
            "Figure 4 biological label vocabulary differs from Figure 3"
        )


def classification_metrics(
    truth: Sequence[str] | pd.Series,
    predicted: Sequence[str] | pd.Series,
    labels: Sequence[str],
    *,
    omit_zero_support: bool = False,
) -> pd.DataFrame:
    """Compute one-vs-rest precision, recall, and F1 for an explicit label set."""
    truth_series = pd.Series(truth, dtype="string").reset_index(drop=True)
    predicted_series = pd.Series(predicted, dtype="string").reset_index(drop=True)
    if len(truth_series) != len(predicted_series):
        raise Figure04ValidationError("Truth and prediction vectors differ in length")

    rows: list[dict[str, Any]] = []
    for label in labels:
        label = str(label)
        truth_positive = truth_series.eq(label)
        predicted_positive = predicted_series.eq(label)
        support = int(truth_positive.sum())
        if omit_zero_support and support == 0:
            continue
        tp = int((truth_positive & predicted_positive).sum())
        fp = int((~truth_positive & predicted_positive).sum())
        fn = int((truth_positive & ~predicted_positive).sum())
        precision = float(tp / (tp + fp)) if tp + fp else 0.0
        recall = float(tp / (tp + fn)) if tp + fn else 0.0
        f1 = (
            float(2.0 * precision * recall / (precision + recall))
            if precision + recall
            else 0.0
        )
        rows.append(
            {
                "cell_type": label,
                "support": support,
                "predicted_count": int(predicted_positive.sum()),
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return pd.DataFrame(rows)


def confusion_tables(
    cells: pd.DataFrame,
    labels: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return count and row-normalized confusion matrices with zero rows retained."""
    categories = [str(label) for label in labels]
    truth = pd.Categorical(cells["truth"].astype(str), categories=categories, ordered=True)
    predicted = pd.Categorical(
        cells["predicted"].astype(str),
        categories=categories,
        ordered=True,
    )
    counts = pd.crosstab(truth, predicted, dropna=False)
    counts.index = pd.Index(categories, name="ground_truth")
    counts.columns = pd.Index(categories, name="predicted")
    row_totals = counts.sum(axis=1)
    if (row_totals <= 0).any():
        missing = row_totals.loc[row_totals.le(0)].index.tolist()
        raise Figure04ValidationError(
            f"Figure 4 truth classes have zero support: {missing}"
        )
    normalized = counts.div(row_totals, axis=0)
    return counts.astype(np.int64), normalized.astype(float)


def cluster_error_decomposition(cells: pd.DataFrame) -> pd.DataFrame:
    """Compute the documented correctness/annotation/clustering arithmetic."""
    required = {"cluster_leiden", "truth", "predicted"}
    if missing := required.difference(cells.columns):
        raise Figure04ValidationError(
            f"Cluster decomposition is missing columns: {sorted(missing)}"
        )

    rows: list[dict[str, Any]] = []
    for cluster, group in cells.groupby("cluster_leiden", sort=True):
        counts = (
            group["truth"]
            .astype(str)
            .value_counts(sort=False)
            .rename_axis("cell_type")
            .reset_index(name="count")
            .sort_values(["count", "cell_type"], ascending=[False, True], kind="mergesort")
        )
        majority_truth = str(counts.iloc[0]["cell_type"])
        predicted_values = group["predicted"].astype(str).unique()
        if len(predicted_values) != 1:
            raise Figure04ValidationError(
                f"Leiden cluster {cluster} has multiple predicted annotations"
            )
        predicted_label = str(predicted_values[0])
        n_cells = int(len(group))
        purity = float(group["truth"].astype(str).eq(majority_truth).mean())
        final_correct = float(group["truth"].astype(str).eq(predicted_label).mean())
        annotation_loss = float(max(purity - final_correct, 0.0))
        clustering_loss = float(1.0 - purity)
        component_sum = final_correct + annotation_loss + clustering_loss
        if not np.isclose(component_sum, 1.0, atol=1e-12):
            raise Figure04ValidationError(
                f"Leiden cluster {cluster} decomposition sums to {component_sum}"
            )
        rows.append(
            {
                "cluster": int(cluster),
                "n_cells": n_cells,
                "majority_truth": majority_truth,
                "predicted_label": predicted_label,
                "purity": purity,
                "final_correct": final_correct,
                "annotation_loss": annotation_loss,
                "clustering_loss": clustering_loss,
                "predicted_matches_majority": predicted_label == majority_truth,
            }
        )
    return pd.DataFrame(rows).sort_values("cluster", kind="mergesort").reset_index(drop=True)


def aggregate_error_decomposition(cluster_stats: pd.DataFrame) -> pd.DataFrame:
    """Weight per-cluster components by the number of cells."""
    total = int(cluster_stats["n_cells"].sum())
    if total <= 0:
        raise Figure04ValidationError("Cannot aggregate an empty cluster table")
    components = ("final_correct", "annotation_loss", "clustering_loss")
    values = {
        component: float(
            np.average(
                cluster_stats[component].to_numpy(dtype=float),
                weights=cluster_stats["n_cells"].to_numpy(dtype=float),
            )
        )
        for component in components
    }
    if not np.isclose(sum(values.values()), 1.0, atol=1e-12):
        raise Figure04ValidationError("Aggregate error-decomposition fractions do not sum to one")
    return pd.DataFrame(
        [
            {
                "pipeline": "Leiden and GPT",
                "n_cells": total,
                **values,
                "clustering_upper_bound": 1.0 - values["clustering_loss"],
            }
        ]
    )


def select_failure_examples(
    cluster_stats: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Select one deterministic cluster for each displayed failure mode."""
    contract = config["error_decomposition"]
    minimum_cells = int(contract["minimum_example_cells"])
    minimum_mixed = float(contract["minimum_mixed_loss"])
    eligible = cluster_stats.loc[cluster_stats["n_cells"].ge(minimum_cells)].copy()
    if eligible.empty:
        raise Figure04ValidationError("No Leiden cluster satisfies the example-size threshold")

    selected: list[pd.Series] = []
    used: set[int] = set()

    annotation = eligible.loc[
        eligible["annotation_loss"].gt(0.0)
        & eligible["annotation_loss"].gt(eligible["clustering_loss"])
    ].assign(
        score=lambda table: table["annotation_loss"] - table["clustering_loss"]
    ).sort_values(
        ["score", "annotation_loss", "n_cells", "cluster"],
        ascending=[False, False, False, True],
        kind="mergesort",
    )
    if annotation.empty:
        raise Figure04ValidationError(
            "No cluster has positive annotation loss greater than clustering loss"
        )
    selected.append(annotation.iloc[0])
    used.add(int(annotation.iloc[0]["cluster"]))

    clustering = eligible.loc[
        eligible["predicted_matches_majority"]
        & eligible["clustering_loss"].gt(0.0)
        & eligible["clustering_loss"].gt(eligible["annotation_loss"])
        & ~eligible["cluster"].isin(used)
    ].assign(
        score=lambda table: table["clustering_loss"] - table["annotation_loss"]
    ).sort_values(
        ["score", "clustering_loss", "n_cells", "cluster"],
        ascending=[False, False, False, True],
        kind="mergesort",
    )
    if clustering.empty:
        raise Figure04ValidationError("No distinct clustering-limited example is available")
    selected.append(clustering.iloc[0])
    used.add(int(clustering.iloc[0]["cluster"]))

    mixed = eligible.loc[
        eligible["annotation_loss"].gt(minimum_mixed)
        & eligible["clustering_loss"].gt(minimum_mixed)
        & ~eligible["cluster"].isin(used)
    ].assign(
        score=lambda table: np.minimum(
            table["annotation_loss"],
            table["clustering_loss"],
        )
    ).sort_values(
        ["score", "n_cells", "cluster"],
        ascending=[False, False, True],
        kind="mergesort",
    )
    if mixed.empty:
        raise Figure04ValidationError("No distinct mixed-loss example is available")
    selected.append(mixed.iloc[0])

    names = ["Annotation Limited", "Clustering Limited", "Mixed Loss"]
    table = pd.DataFrame(selected).drop(columns=["score"], errors="ignore").reset_index(drop=True)
    table.insert(0, "failure_mode", names)
    table["display_label"] = table.apply(
        lambda row: (
            f"{row['failure_mode']}\n"
            f"Cluster: {row['majority_truth']}\n"
            f"Annotation: {row['predicted_label']}"
        ),
        axis=1,
    )
    return table


def _regional_f1(
    cells: pd.DataFrame,
    labels: Sequence[str],
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for file_id, region in cells.groupby("File_ID", sort=True):
        table = classification_metrics(
            region["truth"],
            region["predicted"],
            labels,
            omit_zero_support=True,
        )
        table.insert(0, "File_ID", str(file_id))
        table.insert(1, "region_n_cells", int(len(region)))
        rows.append(table)
    if not rows:
        raise Figure04ValidationError("No File_ID groups were available for regional F1")
    return pd.concat(rows, ignore_index=True)


def build_analysis(
    figure_03_inputs: Figure03Inputs,
    annotation_result: AnnotationResult,
    config: Mapping[str, Any],
) -> Figure04Analysis:
    """Build every Figure 4 metric from one in-memory annotation result."""
    dependency = config["figure_03_dependency"]
    evaluation = config["evaluation"]
    method = str(dependency["method"])
    cluster_column = f"cluster_{method}"

    cells = figure_03_inputs.marker_cells.loc[
        :,
        ["File_ID", "ID", "truth_raw", "truth", "x", "y", cluster_column],
    ].copy()
    cells = cells.rename(columns={cluster_column: "cluster_leiden"})
    if cells[["File_ID", "ID"]].duplicated().any():
        raise Figure04ValidationError("Figure 4 has duplicate (File_ID, ID) keys")
    if len(cells) != int(evaluation["expected_cells"]):
        raise Figure04ValidationError(
            f"Figure 4 received {len(cells):,} cells; "
            f"expected {int(evaluation['expected_cells']):,}"
        )
    if cells["File_ID"].astype(str).nunique() != int(dependency["expected_regions"]):
        raise Figure04ValidationError("Figure 4 region count differs from its contract")
    expected_regions = set(str(key) for key in config["style"]["region_colors"])
    observed_regions = set(cells["File_ID"].astype(str).unique())
    if observed_regions != expected_regions:
        raise Figure04ValidationError(
            "Figure 4 File_ID values differ from the fixed regional-color contract: "
            f"missing={sorted(expected_regions - observed_regions)}, "
            f"unexpected={sorted(observed_regions - expected_regions)}"
        )
    if cells["cluster_leiden"].nunique() != int(dependency["expected_clusters"]):
        raise Figure04ValidationError("Figure 4 Leiden cluster count differs from its contract")

    observed_cluster_ids = set(cells["cluster_leiden"].astype(int).tolist())
    annotation_keys: set[int] = set()
    for key in annotation_result.annotations:
        try:
            annotation_keys.add(int(key))
        except (TypeError, ValueError) as exc:
            raise Figure04ValidationError(f"Non-integer annotation key: {key!r}") from exc
    if annotation_keys != observed_cluster_ids:
        raise Figure04ValidationError(
            "Figure 3 annotation mapping does not exactly cover Leiden clusters: "
            f"missing={sorted(observed_cluster_ids - annotation_keys)}, "
            f"unexpected={sorted(annotation_keys - observed_cluster_ids)}"
        )
    mapping = {
        int(cluster): str(label)
        for cluster, label in annotation_result.annotations.items()
    }
    class_order = [str(label) for label in evaluation["class_order"]]
    permitted_predictions = set(class_order) - {"Noise"}
    unknown_predictions = set(mapping.values()) - permitted_predictions
    if unknown_predictions:
        raise Figure04ValidationError(
            f"Figure 3 mapping contains labels outside the Figure 4 vocabulary: "
            f"{sorted(unknown_predictions)}"
        )
    cells["predicted"] = cells["cluster_leiden"].astype(int).map(mapping)
    if cells["predicted"].isna().any():
        raise Figure04ValidationError("Figure 4 has unmapped Leiden cells")
    cells["predicted"] = cells["predicted"].astype(str)

    observed_truth = set(cells["truth"].astype(str).unique())
    if observed_truth != set(class_order):
        raise Figure04ValidationError(
            "Figure 4 truth vocabulary drifted: "
            f"missing={sorted(set(class_order) - observed_truth)}, "
            f"unexpected={sorted(observed_truth - set(class_order))}"
        )
    observed_noise = int(cells["truth"].astype(str).eq("Noise").sum())
    if observed_noise != int(evaluation["expected_noise_cells"]):
        raise Figure04ValidationError(
            f"Figure 4 has {observed_noise:,} Noise cells; "
            f"expected {int(evaluation['expected_noise_cells']):,}"
        )

    counts, normalized = confusion_tables(cells, class_order)
    pooled = classification_metrics(cells["truth"], cells["predicted"], class_order)
    regional = _regional_f1(cells, class_order)
    cluster_stats = cluster_error_decomposition(cells)
    aggregate = aggregate_error_decomposition(cluster_stats)
    prediction_sha256 = _dataframe_fingerprint(
        cells[["File_ID", "ID", "cluster_leiden", "truth", "predicted"]]
    )
    return Figure04Analysis(
        cells=cells,
        annotation_result=annotation_result,
        figure_03_inputs=figure_03_inputs,
        confusion_counts=counts,
        confusion_row_normalized=normalized,
        pooled_f1=pooled,
        regional_f1=regional,
        cluster_stats=cluster_stats,
        aggregate=aggregate,
        prediction_sha256=prediction_sha256,
    )


def _analysis_from_dependency(
    api_keys: Mapping[str, str],
    repository_root: Path,
    config: Mapping[str, Any],
    *,
    force_refresh: bool,
) -> tuple[Figure04Analysis, dict[str, Any], Path]:
    """Resolve the one Figure 3 mapping after an up-front credential check."""
    dependency = config["figure_03_dependency"]
    figure_03_config_path = (repository_root / dependency["config_path"]).resolve()
    figure_03_config = load_figure03_config(figure_03_config_path)
    _validate_dependency_contract(config, figure_03_config)

    provider = str(dependency["provider"])
    # This preflight intentionally occurs before H5AD/cache access or output.
    require_api_keys(api_keys, [provider], figure_03_config)
    figure_03_inputs = load_figure03_inputs(repository_root, figure_03_config_path)
    annotation = ensure_annotation(
        figure_03_inputs,
        figure_03_config,
        repository_root,
        api_keys,
        provider=provider,
        condition=str(dependency["condition"]),
        method=str(dependency["method"]),
        marker_state=str(dependency["marker_state"]),
        force_refresh=force_refresh,
    )
    _validate_annotation_cache_integrity(annotation)
    analysis = build_analysis(figure_03_inputs, annotation, config)
    selection_lock_path, selection_lock_sha256 = _validate_or_create_selection_lock(
        annotation,
        repository_root,
    )
    return (
        replace(
            analysis,
            selection_lock_path=selection_lock_path,
            selection_lock_sha256=selection_lock_sha256,
        ),
        figure_03_config,
        figure_03_config_path,
    )


def _panel_output_paths(
    repository_root: Path,
    panel: Mapping[str, Any],
) -> dict[str, Path]:
    directory = repository_root / "outputs/figure_04"
    stem = str(panel["output_stem"])
    return {
        "png": directory / f"{stem}.png",
        "pdf": directory / f"{stem}.pdf",
        "csv": directory / f"{stem}.csv",
        "provenance": directory / f"{stem}_provenance.json",
    }


def _save_figure(fig: Any, paths: Mapping[str, Path]) -> None:
    paths["png"].parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(paths["png"], dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(paths["pdf"], bbox_inches="tight", facecolor="white")


def _annotation_provenance(
    result: AnnotationResult,
    repository_root: Path,
) -> dict[str, Any]:
    return {
        "provider": result.provider,
        "condition": result.condition,
        "method": result.method,
        "marker_state": result.marker_state,
        "requested_model_id": result.requested_model_id,
        "returned_model_id": result.returned_model_id,
        "cache_path": _relative_path(result.cache_path, repository_root),
        "cache_sha256": _sha256_file(result.cache_path),
        "cache_hit": bool(result.cache_hit),
        "cache_contract_sha256": result.cache_contract_sha256,
        "annotation_sha256": result.annotation_sha256,
        "prompt_sha256": result.prompt_sha256,
        "marker_summary_sha256": result.marker_summary_sha256,
    }


def _write_panel_provenance(
    path: Path,
    *,
    panel_key: str,
    config_path: Path,
    repository_root: Path,
    analysis: Figure04Analysis | None,
    figure_03_config_path: Path | None,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    payload: dict[str, Any] = {
        "figure": 4,
        "panel": panel_key.removeprefix("panel_").upper(),
        "config_path": _relative_path(config_path, repository_root),
        "config_sha256": _sha256_file(config_path),
    }
    if analysis is not None:
        payload.update(
            {
                "evaluation_universe": "all 220,082 B004 source cells including Noise",
                "figure_03_metric_universe_difference": (
                    "Figure 3 benchmark metrics exclude Noise; Figure 4 includes it."
                ),
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
                "figure_02_config_path": _relative_path(
                    analysis.figure_03_inputs.figure_02_config_path,
                    repository_root,
                ),
                "figure_02_config_sha256": _sha256_file(
                    analysis.figure_03_inputs.figure_02_config_path
                ),
                "marker_expression_sha256": (
                    analysis.figure_03_inputs.expression_sha256
                ),
                "figure_03_config_path": (
                    _relative_path(figure_03_config_path, repository_root)
                    if figure_03_config_path is not None
                    else None
                ),
                "figure_03_config_sha256": (
                    _sha256_file(figure_03_config_path)
                    if figure_03_config_path is not None
                    else None
                ),
                "llm_annotation": _annotation_provenance(
                    analysis.annotation_result,
                    repository_root,
                ),
            }
        )
    if extra:
        payload.update(dict(extra))
    return _json_dump(path, payload)


def render_panel_a(
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
    *,
    model_display_name: str,
) -> None:
    """Render the frozen Figure 2 -> Figure 3 -> Figure 4 workflow."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(13.2, 4.1))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 4.1)
    ax.axis("off")

    boxes = [
        (0.35, 1.35, 2.1, 1.45, "B004 H5AD", "220,082 cells\n8 tissue regions"),
        (2.95, 1.35, 2.1, 1.45, "Figure 2 Leiden", "55 fixed clusters\nno reclustering"),
        (5.55, 1.35, 2.1, 1.45, "Figure 3 markers", "Optimized summaries\nfrom 45 markers"),
        (
            8.15,
            1.35,
            2.1,
            1.45,
            "GPT annotation",
            f"{model_display_name}\none label / cluster",
        ),
        (10.75, 1.35, 2.1, 1.45, "Figure 4 evaluation", "Confusion · F1\nerror decomposition"),
    ]
    fills = ["#E8EEF7", "#E8EEF7", "#FFF1D6", "#FCE7D7", "#E8F3E7"]
    for (x, y, width, height, title, detail), fill in zip(boxes, fills):
        patch = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            linewidth=1.2,
            edgecolor="#243042",
            facecolor=fill,
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, y + height * 0.68, title, ha="center", va="center", fontsize=12)
        ax.text(x + width / 2, y + height * 0.31, detail, ha="center", va="center", fontsize=9)
    for left, right in zip(boxes[:-1], boxes[1:]):
        arrow = FancyArrowPatch(
            (left[0] + left[2] + 0.08, left[1] + left[3] / 2),
            (right[0] - 0.08, right[1] + right[3] / 2),
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.2,
            color="#243042",
        )
        ax.add_patch(arrow)

    ax.text(
        6.6,
        0.70,
        "One shared OpenAI reasoning + optimized-Leiden annotation cache feeds Panels B-F",
        ha="center",
        va="center",
        fontsize=9,
        color="#374151",
    )
    ax.text(
        6.6,
        0.34,
        "End-to-end evaluation includes the 10,495 reference-label Noise cells; "
        "the GPT label vocabulary remains the 20 biological cell types.",
        ha="center",
        va="center",
        fontsize=8,
        color="#4B5563",
    )
    fig.suptitle(str(config["panels"]["panel_a"]["title"]), fontsize=14, y=0.98)
    fig.text(0.008, 0.98, "A", fontsize=30, ha="left", va="top")
    fig.subplots_adjust(left=0.02, right=0.995, top=0.88, bottom=0.04)
    _save_figure(fig, paths)
    plt.close(fig)


def render_panel_b(
    normalized: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
) -> None:
    """Render the row-normalized all-cell confusion matrix."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10.4, 8.8))
    image = ax.imshow(
        normalized.to_numpy(dtype=float),
        cmap=str(config["style"]["confusion_cmap"]),
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
        aspect="equal",
    )
    labels = normalized.index.astype(str).tolist()
    ax.set_xticks(np.arange(len(labels)), labels=labels, rotation=90, fontsize=7.5)
    ax.set_yticks(np.arange(len(labels)), labels=labels, fontsize=8)
    ax.set_xlabel("Predicted Cell Type Labels", labelpad=12)
    ax.set_ylabel("Ground Truth Cell Type Label")
    ax.set_title(str(config["panels"]["panel_b"]["title"]), pad=14)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("Fraction of Cells", rotation=270, labelpad=18)
    fig.text(0.015, 0.98, "B", fontsize=29, ha="left", va="top")
    fig.subplots_adjust(left=0.22, bottom=0.30, right=0.90, top=0.91)
    _save_figure(fig, paths)
    plt.close(fig)


def render_panel_c(
    pooled: pd.DataFrame,
    regional: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
) -> None:
    """Render pooled class F1 bars with one point per supporting region."""
    import matplotlib.pyplot as plt

    ordered = pooled.sort_values(
        ["f1", "support", "cell_type"],
        ascending=[False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    y = np.arange(len(ordered))
    fig, ax = plt.subplots(figsize=(9.2, 8.5))
    ax.barh(
        y,
        ordered["f1"],
        color=str(config["style"]["pooled_f1_color"]),
        edgecolor=str(config["style"]["pooled_f1_edge_color"]),
        linewidth=0.6,
        height=0.74,
        zorder=1,
    )

    color_map = {
        str(key): str(value)
        for key, value in config["style"]["region_colors"].items()
    }
    offsets = np.linspace(-0.24, 0.24, len(color_map))
    offset_by_region = {
        file_id: offset
        for file_id, offset in zip(sorted(color_map), offsets)
    }
    for index, row in ordered.iterrows():
        points = regional.loc[regional["cell_type"].eq(row["cell_type"])]
        for point in points.itertuples(index=False):
            file_id = str(point.File_ID)
            ax.scatter(
                float(point.f1),
                float(index) + float(offset_by_region[file_id]),
                s=18,
                color=color_map[file_id],
                edgecolors="white",
                linewidths=0.25,
                zorder=3,
            )
    ax.set_yticks(y, ordered["cell_type"], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0.0, 1.05)
    ax.set_xlabel("F1 Score")
    ax.set_ylabel("Cell Type")
    ax.set_title(str(config["panels"]["panel_c"]["title"]))
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.7, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.015, 0.98, "C", fontsize=29, ha="left", va="top")
    fig.subplots_adjust(left=0.27, right=0.98, top=0.92, bottom=0.09)
    _save_figure(fig, paths)
    plt.close(fig)


def render_panel_d(
    examples: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
) -> None:
    """Render three representative cluster-level error decompositions."""
    import matplotlib.pyplot as plt

    components = [
        ("final_correct", "Final correct annotation", config["style"]["correct_color"]),
        ("annotation_loss", "Annotation-stage error", config["style"]["annotation_loss_color"]),
        ("clustering_loss", "Clustering-stage error", config["style"]["clustering_loss_color"]),
    ]
    y = np.arange(len(examples))
    fig, ax = plt.subplots(figsize=(10.2, 4.9))
    left = np.zeros(len(examples), dtype=float)
    for column, label, color in components:
        values = examples[column].to_numpy(dtype=float)
        ax.barh(
            y,
            values,
            left=left,
            color=str(color),
            edgecolor="white",
            linewidth=0.7,
            height=0.80,
            label=label,
        )
        for index, (start, value) in enumerate(zip(left, values)):
            if value >= 0.08:
                text_color = "white" if column != "clustering_loss" else "#111827"
                ax.text(
                    start + value / 2,
                    index,
                    f"{100 * value:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=11,
                    color=text_color,
                    fontweight="bold",
                )
        left += values
    ax.set_yticks(y, examples["display_label"], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0.0, 1.0)
    ax.set_xticks(np.linspace(0, 1, 6), labels=[f"{int(x * 100)}%" for x in np.linspace(0, 1, 6)])
    ax.set_xlabel("Fraction of Cells in Each Cluster")
    ax.set_title(str(config["panels"]["panel_d"]["title"]))
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.6, zorder=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.22),
        ncol=3,
        frameon=False,
        fontsize=8,
    )
    fig.text(0.015, 0.98, "D", fontsize=29, ha="left", va="top")
    fig.subplots_adjust(left=0.33, right=0.98, top=0.88, bottom=0.26)
    _save_figure(fig, paths)
    plt.close(fig)


def render_panel_e(
    aggregate: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
) -> None:
    """Render the cohort-wide weighted error decomposition."""
    import matplotlib.pyplot as plt

    row = aggregate.iloc[0]
    components = [
        ("final_correct", "Final correct annotation", config["style"]["correct_color"]),
        ("annotation_loss", "Annotation-stage error", config["style"]["annotation_loss_color"]),
        ("clustering_loss", "Clustering-stage error", config["style"]["clustering_loss_color"]),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    left = 0.0
    for column, label, color in components:
        value = float(row[column])
        ax.barh(
            [0],
            [value],
            left=[left],
            height=0.52,
            color=str(color),
            edgecolor="white",
            linewidth=0.7,
            label=label,
        )
        if value >= 0.06:
            text_color = "white" if column != "clustering_loss" else "#111827"
            ax.text(
                left + value / 2,
                0,
                f"{100 * value:.2f}%",
                ha="center",
                va="center",
                fontsize=12,
                color=text_color,
                fontweight="bold",
            )
        left += value
    ax.set_yticks([0], [str(row["pipeline"])])
    ax.set_xlim(0.0, 1.0)
    ax.set_xticks(np.linspace(0, 1, 6), labels=[f"{int(x * 100)}%" for x in np.linspace(0, 1, 6)])
    ax.set_xlabel("Fraction of Cells")
    ax.set_title(str(config["panels"]["panel_e"]["title"]))
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.30),
        ncol=3,
        frameon=False,
        fontsize=8,
    )
    fig.text(0.015, 0.97, "E", fontsize=29, ha="left", va="top")
    fig.subplots_adjust(left=0.18, right=0.98, top=0.78, bottom=0.34)
    _save_figure(fig, paths)
    plt.close(fig)


def render_panel_f(
    cluster_stats: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
) -> None:
    """Render the three arithmetic outcome fractions for every Leiden cluster."""
    import matplotlib.pyplot as plt

    table = cluster_stats.sort_values("cluster", kind="mergesort").reset_index(drop=True)
    y = np.arange(len(table))
    components = [
        ("final_correct", "Final correct annotation", config["style"]["correct_color"]),
        ("annotation_loss", "Annotation-stage error", config["style"]["annotation_loss_color"]),
        ("clustering_loss", "Clustering-stage error", config["style"]["clustering_loss_color"]),
    ]
    fig, ax = plt.subplots(figsize=(10.0, 14.2))
    left = np.zeros(len(table), dtype=float)
    for column, label, color in components:
        values = table[column].to_numpy(dtype=float)
        ax.barh(
            y,
            values,
            left=left,
            color=str(color),
            edgecolor="white",
            linewidth=0.25,
            height=0.76,
            label=label,
        )
        left += values
    ax.set_yticks(
        y,
        labels=[
            f"Leiden {int(row.cluster)}  ({row.majority_truth})"
            for row in table.itertuples(index=False)
        ],
        fontsize=7,
    )
    ax.invert_yaxis()
    ax.set_xlim(0.0, 1.0)
    ax.set_xticks(np.linspace(0, 1, 6), labels=[f"{int(x * 100)}%" for x in np.linspace(0, 1, 6)])
    ax.set_xlabel("Fraction of Cells in Leiden Cluster")
    ax.set_ylabel("Leiden cluster (majority reference label)")
    ax.set_title(str(config["panels"]["panel_f"]["title"]))
    ax.grid(axis="x", color="#E5E7EB", linewidth=0.5, zorder=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.035),
        ncol=3,
        frameon=False,
        fontsize=8,
    )
    fig.text(0.015, 0.995, "F", fontsize=29, ha="left", va="top")
    fig.subplots_adjust(left=0.28, right=0.98, top=0.965, bottom=0.07)
    _save_figure(fig, paths)
    plt.close(fig)


def _run_context(
    repository_root: str | Path | None,
    config_path: str | Path | None,
) -> tuple[Path, Path, dict[str, Any]]:
    root = _resolve_repository_root(repository_root)
    path = _resolve_config_path(root, config_path)
    return root, path, load_figure_config(path)


def load_analysis(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> Figure04Analysis:
    """Load the one provenance-locked Figure 4 Leiden--GPT analysis.

    This public read interface lets dependent supplementary figures reuse the
    exact same in-memory prediction table and annotation-selection lock without
    first writing a main-figure panel. The existing credential preflight still
    occurs before H5AD/cache access or any output mutation.
    """
    root, _, config = _run_context(repository_root, config_path)
    analysis, _, _ = _analysis_from_dependency(
        api_keys,
        root,
        config,
        force_refresh=force_refresh,
    )
    return analysis


def run_panel_a(
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Render Panel A, the only panel that does not require an API key."""
    root, path, config = _run_context(repository_root, config_path)
    dependency = config["figure_03_dependency"]
    figure_03_config_path = (root / dependency["config_path"]).resolve()
    figure_03_config = load_figure03_config(figure_03_config_path)
    _validate_dependency_contract(config, figure_03_config)
    provider = str(dependency["provider"])
    condition = str(dependency["condition"])
    condition_config = figure_03_config["providers"][provider]["conditions"][condition]
    model_display_name = str(condition_config["display_name"])
    paths = _panel_output_paths(root, config["panels"]["panel_a"])
    render_panel_a(
        paths,
        config,
        model_display_name=model_display_name,
    )
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_a",
        config_path=path,
        repository_root=root,
        analysis=None,
        figure_03_config_path=None,
        extra={
            "description": "Workflow schematic only; no biological result is computed.",
            "figure_03_dependency": config["figure_03_dependency"],
            "figure_03_config_path": _relative_path(figure_03_config_path, root),
            "figure_03_config_sha256": _sha256_file(figure_03_config_path),
            "displayed_annotation_model": {
                "provider": provider,
                "condition": condition,
                "display_name": model_display_name,
                "requested_model_id": str(condition_config["model_id"]),
            },
        },
    )
    return {key: paths[key] for key in ("png", "pdf", "provenance")}


def run_panel_b(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate the row-normalized all-cell confusion matrix."""
    root, path, config = _run_context(repository_root, config_path)
    analysis, _, figure_03_path = _analysis_from_dependency(
        api_keys,
        root,
        config,
        force_refresh=force_refresh,
    )
    paths = _panel_output_paths(root, config["panels"]["panel_b"])
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    analysis.confusion_row_normalized.to_csv(paths["csv"])
    counts_path = paths["csv"].with_name(f"{paths['csv'].stem}_counts.csv")
    analysis.confusion_counts.to_csv(counts_path)
    render_panel_b(analysis.confusion_row_normalized, paths, config)
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_b",
        config_path=path,
        repository_root=root,
        analysis=analysis,
        figure_03_config_path=figure_03_path,
        extra={
            "normalization": "within each ground-truth row",
            "counts_csv": _relative_path(counts_path, root),
            "row_normalized_csv": _relative_path(paths["csv"], root),
        },
    )
    return {**paths, "counts_csv": counts_path}


def run_panel_c(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate pooled F1 bars and the eight region-level point estimates."""
    root, path, config = _run_context(repository_root, config_path)
    analysis, _, figure_03_path = _analysis_from_dependency(
        api_keys,
        root,
        config,
        force_refresh=force_refresh,
    )
    paths = _panel_output_paths(root, config["panels"]["panel_c"])
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    analysis.pooled_f1.to_csv(paths["csv"], index=False)
    regional_path = paths["csv"].with_name(f"{paths['csv'].stem}_by_region.csv")
    analysis.regional_f1.to_csv(regional_path, index=False)
    region_key_path = paths["csv"].with_name(f"{paths['csv'].stem}_region_key.csv")
    pd.DataFrame(
        [
            {"File_ID": file_id, "color": color}
            for file_id, color in sorted(config["style"]["region_colors"].items())
        ]
    ).to_csv(region_key_path, index=False)
    render_panel_c(analysis.pooled_f1, analysis.regional_f1, paths, config)
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_c",
        config_path=path,
        repository_root=root,
        analysis=analysis,
        figure_03_config_path=figure_03_path,
        extra={
            "pooled_metric": "one-vs-rest F1 over all source cells",
            "regional_points": (
                "one-vs-rest F1 within each File_ID; omitted only when the "
                "ground-truth class has zero support in that region"
            ),
            "regional_csv": _relative_path(regional_path, root),
            "region_key_csv": _relative_path(region_key_path, root),
        },
    )
    return {
        **paths,
        "regional_csv": regional_path,
        "region_key_csv": region_key_path,
    }


def run_panel_d(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate deterministic examples of the three displayed failure modes."""
    root, path, config = _run_context(repository_root, config_path)
    analysis, _, figure_03_path = _analysis_from_dependency(
        api_keys,
        root,
        config,
        force_refresh=force_refresh,
    )
    examples = select_failure_examples(analysis.cluster_stats, config)
    paths = _panel_output_paths(root, config["panels"]["panel_d"])
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    examples.drop(columns=["display_label"]).to_csv(paths["csv"], index=False)
    all_clusters_path = paths["csv"].with_name(f"{paths['csv'].stem}_all_clusters.csv")
    analysis.cluster_stats.to_csv(all_clusters_path, index=False)
    render_panel_d(examples, paths, config)
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_d",
        config_path=path,
        repository_root=root,
        analysis=analysis,
        figure_03_config_path=figure_03_path,
        extra={
            "selection_contract": config["error_decomposition"],
            "all_cluster_stats_csv": _relative_path(all_clusters_path, root),
            "decomposition_caveat": (
                "The plotted fractions are arithmetic upper-bound components, "
                "not mutually exclusive causal cell assignments."
            ),
        },
    )
    return {**paths, "all_clusters_csv": all_clusters_path}


def run_panel_e(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate the cohort-wide weighted error decomposition."""
    root, path, config = _run_context(repository_root, config_path)
    analysis, _, figure_03_path = _analysis_from_dependency(
        api_keys,
        root,
        config,
        force_refresh=force_refresh,
    )
    paths = _panel_output_paths(root, config["panels"]["panel_e"])
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    analysis.aggregate.to_csv(paths["csv"], index=False)
    render_panel_e(analysis.aggregate, paths, config)
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_e",
        config_path=path,
        repository_root=root,
        analysis=analysis,
        figure_03_config_path=figure_03_path,
        extra={
            "aggregation": "Leiden-cluster components weighted by cluster cell count",
            "formula": {
                "final_correct": "fraction(truth == GPT cluster label)",
                "annotation_loss": "max(cluster purity - final_correct, 0)",
                "clustering_loss": "1 - cluster purity",
            },
            "legacy_value_policy": (
                "Screenshot percentages are not hard-coded; this panel recomputes "
                "all values from the single Figure 3 annotation mapping."
            ),
        },
    )
    return paths


def run_panel_f(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate per-Leiden-cluster outcome fractions."""
    root, path, config = _run_context(repository_root, config_path)
    analysis, _, figure_03_path = _analysis_from_dependency(
        api_keys,
        root,
        config,
        force_refresh=force_refresh,
    )
    paths = _panel_output_paths(root, config["panels"]["panel_f"])
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    analysis.cluster_stats.to_csv(paths["csv"], index=False)
    render_panel_f(analysis.cluster_stats, paths, config)
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_f",
        config_path=path,
        repository_root=root,
        analysis=analysis,
        figure_03_config_path=figure_03_path,
        extra={
            "cluster_order": "ascending integer Leiden cluster ID",
            "decomposition_caveat": (
                "The three fractions sum to one within each cluster but are "
                "arithmetic upper-bound components, not causal cell labels."
            ),
        },
    )
    return paths
