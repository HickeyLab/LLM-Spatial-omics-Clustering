"""Selection and reporting metrics for the source-locked final figures study.

The functions in this module deliberately separate label-free configuration
selection from reference-label evaluation.  A caller must explicitly provide
reference labels to invoke any supervised metric.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    adjusted_mutual_info_score,
    adjusted_rand_score,
    f1_score,
    normalized_mutual_info_score,
)


KEY_COLUMNS = ("File_ID", "ID")


class MetricsValidationError(ValueError):
    """Raised when assignment or evaluation inputs violate the final-runtime contract."""


@dataclass(frozen=True)
class LabelFreeMetrics:
    """Metrics permitted while choosing the primary clustering configuration."""

    n_cells: int
    n_clusters: int
    min_cluster_size: int
    median_cluster_size: float
    max_cluster_size: int
    viable_cluster_fraction: float
    mean_seed_ari: float
    marker_profile_coherence: float
    target_count_score: float
    selection_score: float


@dataclass(frozen=True)
class SupervisedMetrics:
    """Post-selection reference-label metrics for a keyed cluster partition."""

    n_cells: int
    n_clusters: int
    purity: float
    adjusted_rand_index: float
    adjusted_mutual_information: float
    normalized_mutual_information: float
    majority_macro_f1: float
    majority_weighted_f1: float


def _as_cluster_series(values: Sequence[object] | pd.Series) -> pd.Series:
    series = pd.Series(values, copy=False)
    if series.empty:
        raise MetricsValidationError("Cluster assignments cannot be empty")
    if series.isna().any():
        raise MetricsValidationError("Cluster assignments contain null values")
    return series.astype(str)


def validate_keyed_assignment(
    assignments: pd.DataFrame,
    *,
    expected_keys: pd.DataFrame | None = None,
    cluster_column: str = "cluster",
) -> pd.DataFrame:
    """Validate and return a canonical keyed assignment frame.

    This is intentionally stricter than legacy CSV readers: any duplicate,
    missing, or extra key is a hard failure rather than a positional fallback.
    """

    required = {*KEY_COLUMNS, cluster_column}
    missing = required.difference(assignments.columns)
    if missing:
        raise MetricsValidationError(f"Assignment missing columns: {sorted(missing)}")
    result = assignments.loc[:, [*KEY_COLUMNS, cluster_column]].copy()
    result["File_ID"] = result["File_ID"].astype(str)
    numeric_id = pd.to_numeric(result["ID"], errors="raise")
    if not np.isfinite(numeric_id).all() or not np.equal(numeric_id, np.floor(numeric_id)).all():
        raise MetricsValidationError("Assignment ID values must be finite integers")
    result["ID"] = numeric_id.astype(np.int64)
    if result.duplicated(list(KEY_COLUMNS)).any():
        duplicates = int(result.duplicated(list(KEY_COLUMNS)).sum())
        raise MetricsValidationError(f"Assignment has {duplicates} duplicate cell keys")
    if result[cluster_column].isna().any():
        raise MetricsValidationError("Assignment has null cluster labels")
    result[cluster_column] = result[cluster_column].astype(str)

    if expected_keys is not None:
        expected = expected_keys.loc[:, list(KEY_COLUMNS)].copy()
        expected["File_ID"] = expected["File_ID"].astype(str)
        expected["ID"] = pd.to_numeric(expected["ID"], errors="raise").astype(np.int64)
        if expected.duplicated(list(KEY_COLUMNS)).any():
            raise MetricsValidationError("Expected keys contain duplicates")
        merged = expected.merge(result, on=list(KEY_COLUMNS), how="outer", indicator=True)
        missing_count = int((merged["_merge"] == "left_only").sum())
        extra_count = int((merged["_merge"] == "right_only").sum())
        if missing_count or extra_count:
            raise MetricsValidationError(
                f"Assignment key coverage failed: missing={missing_count}, extra={extra_count}"
            )
        result = expected.merge(result, on=list(KEY_COLUMNS), how="left", validate="one_to_one")
    return result


def _target_count_score(n_clusters: int, *, target: int = 100) -> float:
    if n_clusters < 2:
        return 0.0
    return float(np.exp(-abs(n_clusters - target) / float(target)))


def _marker_profile_coherence(features: np.ndarray, clusters: pd.Series) -> float:
    """Mean non-negative centroid cosine similarity, negated into separation.

    Lower inter-cluster centroid similarity means stronger marker-profile
    separation.  This remains fully label-free.
    """

    if features.ndim != 2 or features.shape[0] != len(clusters):
        raise MetricsValidationError("Feature matrix shape does not match assignments")
    codes, unique = pd.factorize(clusters, sort=True)
    if len(unique) < 2:
        return 0.0
    centroids = np.zeros((len(unique), features.shape[1]), dtype=np.float64)
    np.add.at(centroids, codes, features)
    sizes = np.bincount(codes, minlength=len(unique)).astype(np.float64)
    centroids /= sizes[:, None]
    norms = np.linalg.norm(centroids, axis=1)
    valid = norms > 0
    if valid.sum() < 2:
        return 0.0
    normalized = centroids[valid] / norms[valid, None]
    similarity = normalized @ normalized.T
    upper = similarity[np.triu_indices_from(similarity, k=1)]
    if upper.size == 0:
        return 0.0
    # Map a mean cosine similarity in [-1, 1] to a separation score [0, 1].
    return float(np.clip(1.0 - np.nanmean(upper), 0.0, 1.0))


def label_free_metrics(
    features: np.ndarray,
    primary_clusters: Sequence[object] | pd.Series,
    seed_clusterings: Iterable[Sequence[object] | pd.Series],
    *,
    min_viable_cluster_size: int = 50,
    target_cluster_count: int = 100,
) -> LabelFreeMetrics:
    """Compute the frozen primary-selection objective without reference labels."""

    primary = _as_cluster_series(primary_clusters)
    if features.shape[0] != len(primary):
        raise MetricsValidationError("Features and primary clustering have different cell counts")
    sizes = primary.value_counts(sort=False)
    comparisons: list[float] = []
    for other_values in seed_clusterings:
        other = _as_cluster_series(other_values)
        if len(other) != len(primary):
            raise MetricsValidationError("Seed clustering length differs from primary clustering")
        comparisons.append(float(adjusted_rand_score(primary, other)))
    stability = float(np.mean(comparisons)) if comparisons else 1.0
    coherence = _marker_profile_coherence(np.asarray(features, dtype=np.float32), primary)
    viable_fraction = float((sizes >= min_viable_cluster_size).mean())
    count_score = _target_count_score(int(len(sizes)), target=target_cluster_count)
    # Weights are predeclared, label-free, and intentionally favor reproducibility.
    selection = 0.45 * stability + 0.25 * viable_fraction + 0.20 * coherence + 0.10 * count_score
    return LabelFreeMetrics(
        n_cells=int(len(primary)),
        n_clusters=int(len(sizes)),
        min_cluster_size=int(sizes.min()),
        median_cluster_size=float(sizes.median()),
        max_cluster_size=int(sizes.max()),
        viable_cluster_fraction=viable_fraction,
        mean_seed_ari=stability,
        marker_profile_coherence=coherence,
        target_count_score=count_score,
        selection_score=float(selection),
    )


def majority_label_predictions(
    clusters: Sequence[object] | pd.Series,
    truth: Sequence[object] | pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """Return cluster-majority prediction and deterministic mapping.

    Ties resolve lexicographically, which keeps the reference evaluation
    reproducible and makes no claim that the mapping is an LLM annotation.
    """

    cluster_series = _as_cluster_series(clusters)
    truth_series = pd.Series(truth, copy=False).astype(str)
    if len(cluster_series) != len(truth_series):
        raise MetricsValidationError("Truth labels and clusters have different lengths")
    table = pd.DataFrame({"cluster": cluster_series, "truth": truth_series})
    counts = table.groupby(["cluster", "truth"], sort=True).size().rename("n").reset_index()
    counts = counts.sort_values(["cluster", "n", "truth"], ascending=[True, False, True])
    mapping = counts.drop_duplicates("cluster", keep="first").set_index("cluster")["truth"]
    return cluster_series.map(mapping), mapping


def supervised_cluster_metrics(
    clusters: Sequence[object] | pd.Series,
    truth: Sequence[object] | pd.Series,
) -> SupervisedMetrics:
    """Score a finalized partition; never call this in the primary selector."""

    cluster_series = _as_cluster_series(clusters)
    truth_series = pd.Series(truth, copy=False).astype(str)
    predicted, _ = majority_label_predictions(cluster_series, truth_series)
    purity = float((predicted == truth_series).mean())
    return SupervisedMetrics(
        n_cells=int(len(cluster_series)),
        n_clusters=int(cluster_series.nunique()),
        purity=purity,
        adjusted_rand_index=float(adjusted_rand_score(truth_series, cluster_series)),
        adjusted_mutual_information=float(adjusted_mutual_info_score(truth_series, cluster_series)),
        normalized_mutual_information=float(normalized_mutual_info_score(truth_series, cluster_series)),
        majority_macro_f1=float(f1_score(truth_series, predicted, average="macro", zero_division=0)),
        majority_weighted_f1=float(f1_score(truth_series, predicted, average="weighted", zero_division=0)),
    )


def choose_secondary_candidate(
    diagnostics: pd.DataFrame,
    *,
    label_column: str = "majority_macro_f1",
    label_free_column: str = "label_free_selection_score",
) -> pd.Series:
    """Choose the explicitly secondary, validation-label-tuned candidate."""

    required = {label_column, label_free_column}
    missing = required.difference(diagnostics.columns)
    if missing:
        raise MetricsValidationError(f"Diagnostics missing columns: {sorted(missing)}")
    if diagnostics.empty:
        raise MetricsValidationError("Cannot select from an empty diagnostics table")
    return diagnostics.sort_values(
        [label_column, label_free_column], ascending=[False, False], kind="mergesort"
    ).iloc[0]
