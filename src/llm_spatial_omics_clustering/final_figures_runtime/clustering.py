"""Leakage-safe clustering runners for the final figures runtime.

This module never loads reference labels.  It accepts an H5AD-derived cell
table and feature matrix, returns explicitly keyed assignments, and leaves any
truth-based scoring to :mod:`final_figures_runtime.metrics`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import RobustScaler

from .metrics import KEY_COLUMNS, MetricsValidationError, label_free_metrics, validate_keyed_assignment


class ClusteringError(RuntimeError):
    """Raised when a final-figures clustering backend cannot meet its contract."""


# Match the image-native runner's channel equivalences.  This is a schema
# validation aid only; pixel values continue to come directly from OME-TIFF.
_TIFF_CHANNEL_ALIASES = {
    "aDefensin5": "aDef5",
    "HLA-DR": "HLADR",
    "CollagenIV": "CollIV",
    "Synaptophysin": "Synapto",
}


@dataclass(frozen=True)
class LeidenSettings:
    n_neighbors: int = 30
    resolution: float = 1.0
    n_pcs: int = 30
    seed: int = 42


@dataclass(frozen=True)
class FlowSOMSettings:
    xdim: int = 15
    ydim: int = 15
    n_clusters: int = 80
    seed: int = 42


@dataclass(frozen=True)
class SpatialSortSettings:
    n_neighbors: int = 15
    n_clusters: int = 80
    precision_scale: float = 0.5
    num_iterations: int = 500
    dmh_iterations: int = 5
    point_estimate: str = "last_iteration"
    save_diagnostics: bool = False
    seed: int = 42


@dataclass(frozen=True)
class PixieSettings:
    pixel_som_side: int = 10
    pixel_meta_clusters: int = 20
    cell_som_side: int = 20
    cell_meta_clusters: int = 80
    cell_som_sigma: float = 2.0
    cell_som_learning_rate: float = 0.3
    cell_som_iterations: int = 5000
    seed: int = 42
    # The locked Yang H5AD has 45 X markers and no Hoechst1 variable.  TIFF
    # PIXIE therefore excludes Hoechst by default so the image-native marker
    # set cannot silently diverge from the H5AD-controlled schema.
    include_hoechst: bool = False
    # Preserve every valid H5AD key even when all selected TIFF phenotype
    # pixels are zero. The streaming runner assigns those cells cluster 0 and
    # records its explicit no_phenotype_signal QC status; they never enter the
    # cell SOM or masquerade as a biological PIXIE cluster.
    zero_signal_policy: str = "qc_unclustered"


@dataclass(frozen=True)
class ClusterRun:
    method: str
    settings: Mapping[str, Any]
    assignments: pd.DataFrame
    diagnostics: Mapping[str, Any]


@dataclass(frozen=True)
class SpatialSortScreenSubset:
    """A fixed-key, FOV-balanced, label-free SpatialSort screen input.

    The screen subset is deliberately only a computational triage input.  It
    retains source-row indices and a hash of its keys so a later full SpatialSort
    fit cannot be confused with this reduced-cell MCMC screen.
    """

    cells: pd.DataFrame
    features: np.ndarray
    source_row_indices: tuple[int, ...]
    cells_per_fov: int
    sampling_salt: str
    sampling_sha256: str


# The legacy streaming runner checkpoint filenames that are read, but never
# modified, by ``--stage cell --resume``.  The final-runtime wrapper may hardlink or copy
# only this closed set into a candidate-specific cell-SOM directory.  It never
# links cell-SOM artifacts, labels, or a legacy master table.
_PIXIE_PREFIX_CACHE_SCHEMA = "final_figures.pixie_prefix_cache.v1"
_PIXIE_PREFIX_CHECKPOINTS = (
    "checkpoints/mask_areas.npz",
    "checkpoints/pixel_normalization.npz",
    "checkpoints/pixel_som_weights.npy",
    "checkpoints/pixel_som_to_meta.npy",
    "checkpoints/all_cell_compositions.npz",
)
_PIXIE_PREFIX_FIXED_OPTIONS: Mapping[str, Any] = {
    "tile_size": 512,
    "blur_sigma": 2.0,
    "sample_tiles": 64,
    "sample_per_fov": 50000,
    "som_passes": 1,
}


def stable_config_hash(method: str, settings: Mapping[str, Any]) -> str:
    """Produce a stable namespace for outputs and PIXIE checkpoints."""

    payload = json.dumps({"method": method, "settings": dict(settings)}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def validate_tiff_mask_correspondence(
    cells: pd.DataFrame,
    marker_names: Sequence[str],
    tiffs_dir: str | Path,
) -> pd.DataFrame:
    """Validate paired OME-TIFF availability and H5AD/TIFF schema alignment.

    It deliberately reads only OME metadata, not whole pixel planes: the
    streaming PIXIE runner performs the expensive per-cell mask-label scan
    later in its checkpointed ``sample`` stage.  This check catches missing
    pairs, FOV drift, spatial-shape mismatches, channel-schema mismatches, and
    inconsistent channel ordering before any tile computation begins.
    """

    try:
        import tifffile
    except ImportError as exc:  # pragma: no cover - dependency environment guard
        raise ClusteringError("TIFF correspondence validation requires tifffile") from exc
    canonical = _canonical_cells(cells)
    root = Path(tiffs_dir).expanduser().resolve()
    if not root.is_dir():
        raise ClusteringError(f"TIFF directory does not exist: {root}")
    names = tuple(str(marker) for marker in marker_names)
    if not names or len(set(names)) != len(names):
        raise ClusteringError("H5AD marker names must be non-empty and unique for TIFF validation")
    rows: list[dict[str, Any]] = []
    reference_channels: tuple[str, ...] | None = None
    expected_fovs = set(canonical["File_ID"])
    paired_fovs = {
        child.name
        for child in root.iterdir()
        if child.is_dir()
        and (child / "reg001_expr.ome.tif").is_file()
        and (child / "reg001_mask.ome.tif").is_file()
    }
    if paired_fovs != expected_fovs:
        raise ClusteringError(
            "Paired TIFF FOVs do not exactly match H5AD cells: "
            f"missing={sorted(expected_fovs - paired_fovs)}, extra={sorted(paired_fovs - expected_fovs)}"
        )
    for file_id in sorted(expected_fovs):
        expression_path = root / file_id / "reg001_expr.ome.tif"
        mask_path = root / file_id / "reg001_mask.ome.tif"
        try:
            with tifffile.TiffFile(expression_path) as expression_tiff, tifffile.TiffFile(mask_path) as mask_tiff:
                expression_series = expression_tiff.series[0]
                mask_series = mask_tiff.series[0]
                expression_shape = tuple(int(value) for value in expression_series.shape)
                mask_shape = tuple(int(value) for value in mask_series.shape)
                expression_axes = str(expression_series.axes)
                mask_axes = str(mask_series.axes)
                if expression_axes != "CYX" or mask_axes != "CYX":
                    raise ClusteringError(
                        f"{file_id} requires CYX OME arrays; got expression={expression_axes}, mask={mask_axes}"
                    )
                if expression_shape[1:] != mask_shape[1:] or mask_shape[0] < 1:
                    raise ClusteringError(f"{file_id} expression/mask spatial correspondence failed")
                ome = expression_tiff.ome_metadata
                if not ome:
                    raise ClusteringError(f"{file_id} expression TIFF lacks OME channel metadata")
                channel_names = tuple(
                    str(element.attrib["Name"])
                    for element in ET.fromstring(ome).iter()
                    if element.tag.endswith("Channel") and element.attrib.get("Name")
                )
                if len(channel_names) != expression_shape[0]:
                    raise ClusteringError(
                        f"{file_id} OME channel metadata has {len(channel_names)} channels, "
                        f"but expression has {expression_shape[0]} planes"
                    )
        except (ET.ParseError, OSError, IndexError) as exc:
            raise ClusteringError(f"Cannot inspect paired TIFF metadata for {file_id}") from exc
        unresolved = [
            marker
            for marker in names
            if marker not in channel_names and _TIFF_CHANNEL_ALIASES.get(marker) not in channel_names
        ]
        if unresolved:
            raise ClusteringError(
                f"{file_id} lacks H5AD marker channels after alias resolution: {unresolved}"
            )
        if reference_channels is None:
            reference_channels = channel_names
        elif channel_names != reference_channels:
            raise ClusteringError(f"{file_id} OME channel ordering differs from the first paired TIFF")
        rows.append(
            {
                "File_ID": file_id,
                "h5ad_cells": int(canonical["File_ID"].eq(file_id).sum()),
                "expression_path": str(expression_path),
                "mask_path": str(mask_path),
                "expression_shape": "x".join(map(str, expression_shape)),
                "mask_shape": "x".join(map(str, mask_shape)),
                "ome_channel_count": int(len(channel_names)),
                "h5ad_marker_count": int(len(names)),
                "status": "metadata_correspondent",
            }
        )
    return pd.DataFrame(rows).sort_values("File_ID", kind="mergesort").reset_index(drop=True)


def transform_h5ad_features(features: np.ndarray) -> np.ndarray:
    """Apply the predeclared arcsinh and robust-scaling representation."""

    values = np.asarray(features, dtype=np.float32)
    if values.ndim != 2 or values.shape[0] < 2 or values.shape[1] < 2:
        raise ClusteringError("Features must be a two-dimensional nontrivial matrix")
    if not np.isfinite(values).all():
        raise ClusteringError("H5AD-derived features contain non-finite values")
    transformed = np.arcsinh(values / 5.0)
    return RobustScaler().fit_transform(transformed).astype(np.float32, copy=False)


def deterministic_spatialsort_screen_subset(
    cells: pd.DataFrame,
    features: np.ndarray,
    *,
    cells_per_fov: int,
    sampling_salt: str = "final_figures.spatialsort_screen.v1",
) -> SpatialSortScreenSubset:
    """Create a reproducible equal-FOV H5AD-only screen subset.

    Each FOV contributes exactly ``cells_per_fov`` cells, selected using a
    SHA-256 rank of the already available ``(File_ID, ID)`` keys.  No labels,
    CSV comparison tables, or spatial coordinates enter the sampling rank.  A
    later full fit must rebuild its graph from all development cells; this
    helper intentionally never presents the subsample as a full fit.
    """

    if not isinstance(cells_per_fov, int) or cells_per_fov < 2:
        raise ClusteringError("SpatialSort screen cells_per_fov must be an integer of at least two")
    salt = str(sampling_salt)
    if not salt.strip():
        raise ClusteringError("SpatialSort screen sampling_salt must be non-empty")
    forbidden = {
        "cell_type_update",
        "truth",
        "truth_raw",
        "ground_truth",
        "reference_label",
        "cell_type",
    }
    observed_columns = {
        str(column).strip().casefold(): str(column) for column in cells.columns
    }
    observed_forbidden = sorted(
        observed_columns[name] for name in forbidden.intersection(observed_columns)
    )
    if observed_forbidden:
        raise ClusteringError(
            "SpatialSort screen cells must be label-free; prohibited columns: "
            f"{observed_forbidden}"
        )
    # ``split`` is provenance rather than a label: preserve it verbatim so the
    # screen remains a valid subset for the common assignment contract.  The
    # low-level clustering canonicalizer intentionally selects only geometry
    # and keys, so dropping it here would make the otherwise valid screen
    # impossible to hash or validate downstream.
    if "split" not in cells.columns:
        raise ClusteringError("SpatialSort screen cells are missing the frozen split column")
    raw_split_values = cells["split"].reset_index(drop=True)
    if raw_split_values.isna().any():
        raise ClusteringError("SpatialSort screen cells have missing frozen split values")
    split_values = raw_split_values.astype(str)
    if split_values.str.strip().eq("").any():
        raise ClusteringError("SpatialSort screen cells have missing frozen split values")
    canonical = _canonical_cells(cells).reset_index(drop=True)
    canonical["split"] = split_values
    values = np.asarray(features)
    if values.ndim != 2 or values.shape[0] != len(canonical):
        raise ClusteringError("SpatialSort screen cells/features mismatch")
    if not np.isfinite(values).all():
        raise ClusteringError("SpatialSort screen features contain non-finite values")

    ranked_parts: list[pd.DataFrame] = []
    for file_id, group in canonical.groupby("File_ID", sort=True):
        if len(group) < cells_per_fov:
            raise ClusteringError(
                f"SpatialSort screen FOV {file_id} has {len(group)} cells, fewer than "
                f"the required balanced screen size {cells_per_fov}"
            )
        ranked = group.loc[:, list(KEY_COLUMNS)].copy()
        ranked["source_row_index"] = group.index.to_numpy(dtype=np.int64)
        ranked["screen_rank"] = [
            hashlib.sha256(
                f"{salt}\x00{file_id}\x00{int(cell_id)}".encode("utf-8")
            ).hexdigest()
            for cell_id in ranked["ID"]
        ]
        ranked_parts.append(
            ranked.sort_values(["screen_rank", "ID"], kind="mergesort").head(cells_per_fov)
        )
    selected = pd.concat(ranked_parts, ignore_index=True).sort_values(
        ["File_ID", "screen_rank", "ID"], kind="mergesort"
    ).reset_index(drop=True)
    source_indices = tuple(int(value) for value in selected["source_row_index"])
    subset_cells = canonical.iloc[list(source_indices)].reset_index(drop=True)
    subset_features = np.asarray(values[list(source_indices)]).copy()
    per_fov = subset_cells.groupby("File_ID", sort=True).size()
    if not per_fov.eq(cells_per_fov).all():  # defensive against a malformed group operation
        raise ClusteringError("SpatialSort screen sample is not FOV-balanced")
    sample_records = [
        {"File_ID": str(row.File_ID), "ID": int(row.ID)}
        for row in subset_cells.loc[:, list(KEY_COLUMNS)].itertuples(index=False)
    ]
    digest_payload = json.dumps(
        {
            "schema": "final_figures.spatialsort_screen_subset.v1",
            "cells_per_fov": cells_per_fov,
            "sampling_salt": salt,
            "selected_keys": sample_records,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return SpatialSortScreenSubset(
        cells=subset_cells,
        features=subset_features,
        source_row_indices=source_indices,
        cells_per_fov=cells_per_fov,
        sampling_salt=salt,
        sampling_sha256=hashlib.sha256(digest_payload.encode("utf-8")).hexdigest(),
    )


def estimate_spatialsort_legacy_work(
    *,
    n_cells: int,
    n_clusters: int,
    n_markers: int,
    num_iterations: int,
    dmh_iterations: int,
) -> Mapping[str, int]:
    """Return a transparent conservative work proxy for the vendored sampler.

    The legacy collapsed-Gibbs update recomputes a marker-wise likelihood for
    every proposed cell/cluster state, so its dominant work scales with
    ``cells * clusters**2 * markers * sweeps``.  This is a planning estimate,
    not a timing benchmark, and makes a short screen visibly different from a
    full-resolution MCMC request before any computation starts.  It also
    includes the vendored ``Trace.beta_iter_multiplier=5``: every outer MCMC
    iteration invokes five beta-DMH updates, not one.
    """

    values = {
        "n_cells": n_cells,
        "n_clusters": n_clusters,
        "n_markers": n_markers,
        "num_iterations": num_iterations,
        "dmh_iterations": dmh_iterations,
    }
    if any(not isinstance(value, int) or value < 1 for value in values.values()):
        raise ClusteringError("SpatialSort work estimate requires positive integer dimensions")
    # The vendored chain starts cell updates at t=2.  Keep at least one sweep
    # in the report for a two-iteration smoke configuration.
    x_sweeps = max(num_iterations - 2, 1)
    collapsed_gibbs_terms = n_cells * n_clusters * n_clusters * n_markers * x_sweeps
    # ``dmh_iterations`` controls auxiliary sweeps within one beta update.
    # The vendored Trace independently runs five beta updates per outer MCMC
    # iteration, so retain that source-locked multiplier explicitly.
    beta_update_multiplier = 5
    dmh_terms = (
        n_cells
        * n_clusters
        * n_clusters
        * dmh_iterations
        * beta_update_multiplier
        * x_sweeps
    )
    return {
        **values,
        "x_update_sweeps": x_sweeps,
        "beta_update_multiplier": beta_update_multiplier,
        "beta_update_sweeps": int(beta_update_multiplier * x_sweeps),
        "collapsed_gibbs_marker_terms": int(collapsed_gibbs_terms),
        "dmh_spatial_terms": int(dmh_terms),
        "total_proxy_terms": int(collapsed_gibbs_terms + dmh_terms),
    }


def estimate_spatialsort_fast_work(
    *,
    n_cells: int,
    n_clusters: int,
    n_markers: int,
    num_iterations: int,
    dmh_iterations: int,
) -> Mapping[str, int]:
    """Estimate work after the opt-in local-delta 2K x-update substitution.

    The finite-data accelerator replaces only the marker-wise collapsed-Gibbs
    likelihood calculation.  Vendor beta DMH remains unchanged, so this
    function reports both terms rather than claiming a full end-to-end
    ``K``-fold speedup.
    """

    values = {
        "n_cells": n_cells,
        "n_clusters": n_clusters,
        "n_markers": n_markers,
        "num_iterations": num_iterations,
        "dmh_iterations": dmh_iterations,
    }
    if any(not isinstance(value, int) or value < 1 for value in values.values()):
        raise ClusteringError("SpatialSort work estimate requires positive integer dimensions")
    x_sweeps = max(num_iterations - 2, 1)
    # One source/candidate pair is evaluated per proposed label.  Its marker
    # contribution is O(M), rather than a full O(K*M) likelihood rebuild.
    collapsed_gibbs_terms = n_cells * n_clusters * n_markers * x_sweeps
    # The fast path intentionally leaves beta-DMH unchanged.  Account for all
    # five vendor beta updates per outer MCMC iteration rather than claiming a
    # speedup that applies only to the x-update.
    beta_update_multiplier = 5
    dmh_terms = (
        n_cells
        * n_clusters
        * n_clusters
        * dmh_iterations
        * beta_update_multiplier
        * x_sweeps
    )
    return {
        **values,
        "x_update_sweeps": x_sweeps,
        "beta_update_multiplier": beta_update_multiplier,
        "beta_update_sweeps": int(beta_update_multiplier * x_sweeps),
        "collapsed_gibbs_marker_terms": int(collapsed_gibbs_terms),
        "dmh_spatial_terms": int(dmh_terms),
        "total_proxy_terms": int(collapsed_gibbs_terms + dmh_terms),
    }


def estimate_spatialsort_fast_beta_dmh_work(
    *,
    n_cells: int,
    n_clusters: int,
    n_markers: int,
    n_neighbors: int,
    num_iterations: int,
    dmh_iterations: int,
    use_fast_x_kernel: bool = False,
) -> Mapping[str, int | bool]:
    """Estimate the separately gated 2K auxiliary beta-DMH optimization.

    The historical work proxy deliberately treated each auxiliary Gibbs energy
    as a ``clusters``-sized neighbourhood calculation.  The beta accelerator
    instead makes one neighbour-label histogram plus one ``clusters``-sized
    energy vector per auxiliary node.  The x-update gate remains independent:
    this reporting helper never changes a registered SpatialSort setting or
    the completed bounded-screen calculation.
    """

    values = {
        "n_cells": n_cells,
        "n_clusters": n_clusters,
        "n_markers": n_markers,
        "n_neighbors": n_neighbors,
        "num_iterations": num_iterations,
        "dmh_iterations": dmh_iterations,
    }
    if any(not isinstance(value, int) or value < 1 for value in values.values()):
        raise ClusteringError("SpatialSort work estimate requires positive integer dimensions")
    if not isinstance(use_fast_x_kernel, bool):
        raise ClusteringError("use_fast_x_kernel must be an explicit boolean")
    x_sweeps = max(num_iterations - 2, 1)
    beta_update_multiplier = 5
    beta_update_sweeps = beta_update_multiplier * x_sweeps
    if use_fast_x_kernel:
        x_terms = n_cells * n_clusters * n_markers * x_sweeps
    else:
        x_terms = n_cells * n_clusters * n_clusters * n_markers * x_sweeps
    # For each proposed beta row, every auxiliary node first counts its
    # neighbours (O(degree)) then materializes all K candidate energies.
    beta_auxiliary_terms = (
        n_cells
        * n_clusters
        * dmh_iterations
        * beta_update_sweeps
        * (n_neighbors + n_clusters)
    )
    return {
        **values,
        "x_update_sweeps": x_sweeps,
        "beta_update_multiplier": beta_update_multiplier,
        "beta_update_sweeps": beta_update_sweeps,
        "fast_x_kernel": use_fast_x_kernel,
        "x_update_marker_terms": int(x_terms),
        "beta_auxiliary_energy_terms": int(beta_auxiliary_terms),
        "total_proxy_terms": int(x_terms + beta_auxiliary_terms),
    }


def _canonical_cells(cells: pd.DataFrame) -> pd.DataFrame:
    required = {*KEY_COLUMNS, "x", "y"}
    missing = required.difference(cells.columns)
    if missing:
        raise ClusteringError(f"Cells missing required columns: {sorted(missing)}")
    result = cells.loc[:, [*KEY_COLUMNS, "x", "y"]].copy()
    result["File_ID"] = result["File_ID"].astype(str)
    result["ID"] = pd.to_numeric(result["ID"], errors="raise").astype(np.int64)
    if result.duplicated(list(KEY_COLUMNS)).any():
        raise ClusteringError("Cells contain duplicate (File_ID, ID) keys")
    for column in ("x", "y"):
        result[column] = pd.to_numeric(result[column], errors="raise").astype(float)
    return result


def _assignment(cells: pd.DataFrame, labels: Sequence[object], method: str) -> pd.DataFrame:
    canonical = _canonical_cells(cells)
    if len(canonical) != len(labels):
        raise ClusteringError(f"{method} returned {len(labels)} labels for {len(canonical)} cells")
    assignments = canonical.loc[:, list(KEY_COLUMNS)].copy()
    assignments["cluster"] = pd.Series(labels, index=assignments.index).astype(str)
    assignments["method"] = method
    return validate_keyed_assignment(assignments, expected_keys=canonical, cluster_column="cluster").assign(method=method)


def run_leiden(cells: pd.DataFrame, features: np.ndarray, settings: LeidenSettings) -> ClusterRun:
    """Run deterministic Leiden clustering on the H5AD-derived representation."""

    try:
        import anndata as ad
        import scanpy as sc
    except ImportError as exc:  # pragma: no cover - dependency environment guard
        raise ClusteringError("Leiden backend requires anndata and scanpy") from exc
    canonical = _canonical_cells(cells)
    values = transform_h5ad_features(features)
    if len(canonical) != values.shape[0]:
        raise ClusteringError("Leiden cells/features mismatch")
    n_pcs = min(int(settings.n_pcs), values.shape[1], values.shape[0] - 1)
    if n_pcs < 2:
        raise ClusteringError("Leiden requires at least two usable principal components")
    representation = PCA(n_components=n_pcs, random_state=settings.seed, svd_solver="randomized").fit_transform(values)
    adata = ad.AnnData(X=np.zeros((len(canonical), 1), dtype=np.float32))
    adata.obsm["X_final"] = representation.astype(np.float32, copy=False)
    sc.pp.neighbors(
        adata,
        n_neighbors=min(int(settings.n_neighbors), len(canonical) - 1),
        use_rep="X_final",
        n_pcs=None,
        metric="euclidean",
        random_state=settings.seed,
    )
    sc.tl.leiden(
        adata,
        resolution=float(settings.resolution),
        random_state=int(settings.seed),
        key_added="final_cluster",
        n_iterations=2,
        flavor="igraph",
        directed=False,
    )
    labels = adata.obs["final_cluster"].astype(str).to_numpy(copy=True)
    assignments = _assignment(canonical, labels, "leiden")
    return ClusterRun(
        method="leiden",
        settings=asdict(settings),
        assignments=assignments,
        diagnostics={"n_clusters": int(assignments["cluster"].nunique()), "backend": "scanpy"},
    )


def run_flowsom(cells: pd.DataFrame, features: np.ndarray, settings: FlowSOMSettings) -> ClusterRun:
    """Run unsupervised FlowSOM without legacy label-derived weights."""

    try:
        from flowsom import FlowSOM
    except ImportError as exc:  # pragma: no cover - dependency environment guard
        raise ClusteringError("FlowSOM backend requires the flowsom package") from exc
    canonical = _canonical_cells(cells)
    values = transform_h5ad_features(features)
    if len(canonical) != values.shape[0]:
        raise ClusteringError("FlowSOM cells/features mismatch")
    frame = pd.DataFrame(values, columns=[f"marker_{index}" for index in range(values.shape[1])])
    model = FlowSOM(
        frame,
        cols_to_use=list(frame.columns),
        xdim=int(settings.xdim),
        ydim=int(settings.ydim),
        n_clusters=int(settings.n_clusters),
        seed=int(settings.seed),
    )
    labels = np.asarray(model.metacluster_labels, dtype=np.int64) + 1
    assignments = _assignment(canonical, labels, "flowsom")
    return ClusterRun(
        method="flowsom",
        settings=asdict(settings),
        assignments=assignments,
        diagnostics={"n_clusters": int(assignments["cluster"].nunique()), "backend": "flowsom"},
    )


def spatial_knn_relations(cells: pd.DataFrame, n_neighbors: int) -> pd.DataFrame:
    """Create SpatialSort relations without quadratic pairwise distances."""

    canonical = _canonical_cells(cells)
    if n_neighbors < 1:
        raise ClusteringError("SpatialSort requires at least one neighbor")
    parts: list[pd.DataFrame] = []
    for file_id, group in canonical.groupby("File_ID", sort=True):
        coordinates = group.loc[:, ["x", "y"]].to_numpy(dtype=float)
        if len(group) < 2:
            raise ClusteringError(f"FOV {file_id} has fewer than two cells")
        # ``kneighbors(X=None)`` already excludes the queried training point,
        # so asking for n+1 then dropping the first result silently produced
        # only n-1 actual neighbours.  Keep exactly the declared graph degree.
        query_neighbors = min(n_neighbors, len(group) - 1)
        indices = (
            NearestNeighbors(n_neighbors=query_neighbors, metric="euclidean")
            .fit(coordinates)
            .kneighbors(return_distance=False)
        )
        source = np.repeat(np.arange(len(group), dtype=np.int64), query_neighbors)
        target = indices.reshape(-1).astype(np.int64)
        # Canonical undirected edge set; exact node indexing is documented by cell_order.csv.
        lo = np.minimum(source, target)
        hi = np.maximum(source, target)
        edges = pd.DataFrame({"file_id": str(file_id), "firstobjectnumber": lo, "secondobjectnumber": hi})
        parts.append(edges.drop_duplicates())
    return pd.concat(parts, ignore_index=True)


def write_spatialsort_inputs(
    cells: pd.DataFrame,
    features: np.ndarray,
    output_dir: str | Path,
    *,
    n_neighbors: int,
) -> Mapping[str, Path]:
    """Write keyed, reproducible SpatialSort inputs and an explicit cell order map."""

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    canonical = _canonical_cells(cells).sort_values(list(KEY_COLUMNS), kind="mergesort").reset_index(drop=True)
    values = transform_h5ad_features(features)
    if values.shape[0] != len(canonical):
        raise ClusteringError("SpatialSort cells/features mismatch")
    # Feature rows must be reordered with cells by the caller; reject uncertain row order.
    if not cells.loc[:, list(KEY_COLUMNS)].reset_index(drop=True).equals(canonical.loc[:, list(KEY_COLUMNS)]):
        order = pd.MultiIndex.from_frame(canonical.loc[:, list(KEY_COLUMNS)])
        original = pd.MultiIndex.from_frame(_canonical_cells(cells).loc[:, list(KEY_COLUMNS)])
        positions = original.get_indexer(order)
        if (positions < 0).any():
            raise ClusteringError("Cannot align SpatialSort features to canonical key order")
        values = values[positions]
    feature_columns = [f"marker_{index}" for index in range(values.shape[1])]
    expression = pd.DataFrame(values, columns=feature_columns)
    expression.insert(0, "file_id", canonical["File_ID"].to_numpy())
    locations = canonical.loc[:, ["File_ID", "x", "y"]].rename(columns={"File_ID": "file_id"})
    cell_order = canonical.loc[:, list(KEY_COLUMNS)].copy()
    cell_order.insert(0, "row_index", np.arange(len(cell_order), dtype=np.int64))
    relations = spatial_knn_relations(canonical, n_neighbors=n_neighbors)
    paths = {
        "expression": destination / "expression.csv",
        "locations": destination / "locations.csv",
        "relations": destination / "relations.csv",
        "cell_order": destination / "cell_order.csv",
    }
    expression.to_csv(paths["expression"], index=False)
    locations.to_csv(paths["locations"], index=False)
    relations.to_csv(paths["relations"], index=False)
    cell_order.to_csv(paths["cell_order"], index=False)
    return paths


def _import_spatialsort_inference(source_root: Path):
    """Import the untouched vendored MCMC kernel for the isolated final-runtime adapter."""

    source_root = source_root.resolve()
    if not (source_root / "src" / "inference" / "mcmc.py").is_file():
        raise ClusteringError(f"SpatialSort source tree not found at {source_root}")
    previous = list(sys.path)
    try:
        sys.path.insert(0, str(source_root))
        module = importlib.import_module("src.inference.mcmc")
        beta_model = getattr(module, "TWO_K", None)
        if beta_model is None:
            raise ClusteringError("Vendored SpatialSort inference does not expose TWO_K")
        return module.inference_dmh, beta_model
    finally:
        sys.path[:] = previous


def run_spatialsort(
    cells: pd.DataFrame,
    features: np.ndarray,
    settings: SpatialSortSettings,
    *,
    output_dir: str | Path,
    source_root: str | Path,
    use_fast_kernel: bool = False,
    use_fast_beta_dmh_2k: bool = False,
) -> ClusterRun:
    """Run SpatialSort with explicit, default-off final-runtime acceleration gates.

    ``use_fast_kernel`` is intentionally not part of :class:`SpatialSortSettings`.
    Keeping it out of the registered settings payload ensures this optional
    full-resolution research path cannot rewrite or invalidate the completed
    bounded-screen selection.  ``use_fast_beta_dmh_2k`` is a separate gate for
    only the 2K auxiliary HotPotts energies inside beta DMH; it can run with
    either the vendored or the separately gated local-delta x update.  A future
    full-fit protocol must opt in explicitly and receives standalone
    source-hashed parity/provenance artifacts.
    """

    if not isinstance(settings.num_iterations, int) or settings.num_iterations < 2:
        raise ClusteringError("SpatialSort num_iterations must be an integer of at least two")
    if not isinstance(settings.dmh_iterations, int) or settings.dmh_iterations < 1:
        raise ClusteringError("SpatialSort dmh_iterations must be a positive integer")
    if settings.point_estimate != "last_iteration":
        raise ClusteringError(
            "Final SpatialSort supports only point_estimate='last_iteration'; "
            "legacy MPEAR is quadratic in cell count and remains isolated in the vendored runner"
        )
    if not isinstance(use_fast_kernel, bool):
        raise ClusteringError("use_fast_kernel must be an explicit boolean")
    if not isinstance(use_fast_beta_dmh_2k, bool):
        raise ClusteringError("use_fast_beta_dmh_2k must be an explicit boolean")
    fast_kernel_metadata: Mapping[str, Any] | None = None
    fast_parity: Mapping[str, Any] | None = None
    fast_beta_metadata: Mapping[str, Any] | None = None
    fast_beta_parity: Mapping[str, Any] | None = None
    if use_fast_kernel:
        # Fail closed before writing inputs or starting any full-resolution
        # MCMC: the opt-in substitution is admitted only after its deterministic
        # candidate-likelihood and seeded-sweep checks match the vendor.
        try:
            from .spatialsort_fast import FastSpatialSortError, validate_fast_kernel_against_vendor

            fast_parity = validate_fast_kernel_against_vendor(source_root)
        except FastSpatialSortError as exc:
            raise ClusteringError("Fast SpatialSort parity preflight failed") from exc
    if use_fast_beta_dmh_2k:
        # Keep beta-DMH admission separate from the x-update certificate.  It
        # checks the vendor HotPotts, proposal, and beta-DMH sources before any
        # study inputs are written or an MCMC chain begins.
        try:
            from .spatialsort_fast_beta import (
                FastBetaDMHError,
                validate_fast_beta_dmh_2k_against_vendor,
            )

            fast_beta_parity = validate_fast_beta_dmh_2k_against_vendor(source_root)
        except FastBetaDMHError as exc:
            raise ClusteringError("Fast SpatialSort beta-DMH parity preflight failed") from exc
    destination = Path(output_dir)
    paths = write_spatialsort_inputs(cells, features, destination / "inputs", n_neighbors=settings.n_neighbors)
    vendor_root = destination / "vendor"
    vendor_root.mkdir(parents=True, exist_ok=True)
    # Call the untouched vendored kernel directly.  Avoiding its legacy
    # MPEAR post-processing is an explicit final-runtime adapter decision: MPEAR builds
    # an O(cells^2) matrix, whereas the final MCMC state is already a valid
    # source-model output and can be reconstructed in the explicit cell order.
    if use_fast_beta_dmh_2k:
        try:
            from .spatialsort_fast_beta import (
                FastBetaDMHError,
                fast_inference_dmh_2k_with_fast_beta,
            )

            trace, fast_beta_metadata = fast_inference_dmh_2k_with_fast_beta(
                source_root=source_root,
                k_clusters=int(settings.n_clusters),
                t_iter=int(settings.num_iterations),
                dmh_iter=int(settings.dmh_iterations),
                output_dir=vendor_root,
                expression_csv=paths["expression"],
                location_csv=paths["locations"],
                relation_csv=paths["relations"],
                prec_scale=float(settings.precision_scale),
                seed=int(settings.seed),
                save_trace=bool(settings.save_diagnostics),
                parity_certificate=fast_beta_parity,
                use_fast_x_kernel=use_fast_kernel,
                x_parity_certificate=fast_parity,
            )
        except FastBetaDMHError as exc:
            raise ClusteringError("Fast SpatialSort beta-DMH run failed closed") from exc
        beta_provenance_path = destination / "fast_beta_dmh_2k_provenance.json"
        beta_provenance_path.write_text(
            json.dumps(dict(fast_beta_metadata), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if use_fast_kernel and fast_parity is not None:
            # The beta provenance already embeds this certificate, but retain
            # the existing x-gate artifact name as a standalone audit record
            # when a future protocol explicitly combines both substitutions.
            fast_kernel_metadata = {
                "schema_version": "final_figures.spatialsort_fast_2k.v1",
                "backend": "local-delta-spatialsort-2k+fast-beta-dmh-2k",
                "substituted_operation": "finite_2k_collapsed_gibbs_x_update_only",
                "beta_updates": "fast-beta-dmh-2k",
                "parity_validation": dict(fast_parity),
            }
            provenance_path = destination / "fast_kernel_provenance.json"
            provenance_path.write_text(
                json.dumps(dict(fast_kernel_metadata), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    elif use_fast_kernel:
        try:
            from .spatialsort_fast import FastSpatialSortError, fast_inference_dmh_2k

            trace, fast_kernel_metadata = fast_inference_dmh_2k(
                source_root=source_root,
                k_clusters=int(settings.n_clusters),
                t_iter=int(settings.num_iterations),
                dmh_iter=int(settings.dmh_iterations),
                output_dir=vendor_root,
                expression_csv=paths["expression"],
                location_csv=paths["locations"],
                relation_csv=paths["relations"],
                prec_scale=float(settings.precision_scale),
                seed=int(settings.seed),
                save_trace=bool(settings.save_diagnostics),
                parity_certificate=fast_parity,
            )
        except FastSpatialSortError as exc:
            raise ClusteringError("Fast SpatialSort run failed closed") from exc
        provenance_path = destination / "fast_kernel_provenance.json"
        provenance_path.write_text(
            json.dumps(dict(fast_kernel_metadata), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        inference_dmh, beta_model = _import_spatialsort_inference(Path(source_root))
        np.random.seed(int(settings.seed))
        trace = inference_dmh(
            k_clusters=int(settings.n_clusters),
            t_iter=int(settings.num_iterations),
            dmh_iter=int(settings.dmh_iterations),
            beta_model=beta_model,
            output_dir=str(vendor_root) + "/",
            expression_csv=str(paths["expression"]),
            location_csv=str(paths["locations"]),
            relation_csv=str(paths["relations"]),
            prec_scale=float(settings.precision_scale),
            save_trace=bool(settings.save_diagnostics),
        )
    labels = np.concatenate(
        [
            trace.get_x_curr()[patient, :trace.list_of_n_cells[patient]]
            for patient in range(len(trace.list_of_n_cells))
        ]
    )
    ordered = pd.read_csv(paths["cell_order"])
    if len(labels) != len(ordered):
        raise ClusteringError(
            f"SpatialSort output length {len(labels)} does not match explicit cell order {len(ordered)}"
        )
    assignments = ordered.loc[:, list(KEY_COLUMNS)].copy()
    assignments["cluster"] = np.asarray(labels, dtype=np.int64).astype(str)
    assignments = validate_keyed_assignment(assignments, expected_keys=ordered, cluster_column="cluster")
    assignments["method"] = "spatialsort"
    if use_fast_beta_dmh_2k:
        backend = (
            "fast-beta-dmh-2k+local-delta-x"
            if use_fast_kernel
            else "fast-beta-dmh-2k+vendored-x"
        )
    elif use_fast_kernel:
        backend = "local-delta-spatialsort-2k"
    else:
        backend = "vendored-spatialsort"
    diagnostics: dict[str, Any] = {
        "n_clusters": int(assignments["cluster"].nunique()),
        "backend": backend,
        "point_estimate": str(settings.point_estimate),
        "dmh_iterations": int(settings.dmh_iterations),
        "fast_kernel_requested": bool(use_fast_kernel),
        "fast_beta_dmh_2k_requested": bool(use_fast_beta_dmh_2k),
    }
    if fast_kernel_metadata is not None:
        diagnostics["fast_kernel"] = dict(fast_kernel_metadata)
        diagnostics["fast_kernel_provenance_path"] = str(destination / "fast_kernel_provenance.json")
    if fast_beta_metadata is not None:
        diagnostics["fast_beta_dmh_2k"] = dict(fast_beta_metadata)
        diagnostics["fast_beta_dmh_2k_provenance_path"] = str(
            destination / "fast_beta_dmh_2k_provenance.json"
        )
    return ClusterRun(
        method="spatialsort",
        settings=asdict(settings),
        assignments=assignments,
        diagnostics=diagnostics,
    )


def write_pixie_registry(
    cells: pd.DataFrame,
    marker_names: Sequence[str],
    marker_values: np.ndarray,
    registry_path: str | Path,
    *,
    include_hoechst: np.ndarray | None = None,
) -> Path:
    """Create the TIFF runner registry directly from H5AD-derived data."""

    frame = _pixie_registry_frame(
        cells,
        marker_names,
        marker_values,
        include_hoechst=include_hoechst,
    )
    destination = Path(registry_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    return destination


def _pixie_registry_frame(
    cells: pd.DataFrame,
    marker_names: Sequence[str],
    marker_values: np.ndarray,
    *,
    include_hoechst: np.ndarray | None = None,
) -> pd.DataFrame:
    """Return the deterministic H5AD-derived registry used by TIFF PIXIE."""

    original = _canonical_cells(cells)
    canonical = original.sort_values(list(KEY_COLUMNS), kind="mergesort").reset_index(drop=True)
    values = np.asarray(marker_values)
    if values.shape != (len(original), len(marker_names)):
        raise ClusteringError("PIXIE registry marker matrix does not match H5AD cells/markers")
    # H5AD rows are aligned to the caller's cells.  The registry itself is
    # canonicalized by exact key, so carry both expression and optional
    # Hoechst values through the same deterministic permutation.
    canonical_keys = pd.MultiIndex.from_frame(canonical.loc[:, list(KEY_COLUMNS)])
    original_keys = pd.MultiIndex.from_frame(original.loc[:, list(KEY_COLUMNS)])
    positions = original_keys.get_indexer(canonical_keys)
    if (positions < 0).any():  # defensive: canonical keys came from original
        raise ClusteringError("Cannot align H5AD values to canonical PIXIE registry keys")
    values = values[positions]
    frame = canonical.loc[:, list(KEY_COLUMNS)].copy()
    for index, marker in enumerate(marker_names):
        frame[str(marker)] = values[:, index]
    if include_hoechst is not None:
        values_hoechst = np.asarray(include_hoechst)
        if values_hoechst.shape[0] != len(original):
            raise ClusteringError("Hoechst vector does not match H5AD cells")
        frame["Hoechst1"] = values_hoechst[positions]
    return frame


def _json_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _registry_csv_sha256(frame: pd.DataFrame) -> str:
    """Fingerprint exactly the registry CSV bytes the legacy runner receives."""

    return hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()


def _pixie_split_key(cells: pd.DataFrame) -> list[dict[str, str]]:
    """Capture the frozen split membership without exposing any labels."""

    canonical = _canonical_cells(cells)
    if "split" not in cells.columns:
        return []
    split_frame = cells.loc[:, [*KEY_COLUMNS, "split"]].copy()
    split_frame["File_ID"] = split_frame["File_ID"].astype(str)
    split_frame["ID"] = pd.to_numeric(split_frame["ID"], errors="raise").astype(np.int64)
    ordered = canonical.loc[:, list(KEY_COLUMNS)].merge(
        split_frame,
        on=list(KEY_COLUMNS),
        how="left",
        validate="one_to_one",
    )
    if ordered["split"].isna().any():
        raise ClusteringError("PIXIE cells have missing frozen split values")
    return [
        {"File_ID": str(row.File_ID), "ID": str(int(row.ID)), "split": str(row.split)}
        for row in ordered.itertuples(index=False)
    ]


def _tiff_filesystem_identity(cells: pd.DataFrame, tiffs_dir: str | Path) -> Mapping[str, Any]:
    """Fingerprint paired TIFF identities without an expensive full pixel read.

    The cache is deliberately scoped to an immutable HuBMAP TIFF directory. A
    path, device/inode, size, ctime, and mtime change invalidates reuse before
    the legacy runner is called.  OME schema validation remains a separate
    explicit final-runtime contract check.
    """

    root = Path(tiffs_dir).expanduser().resolve()
    if not root.is_dir():
        raise ClusteringError(f"TIFF directory does not exist: {root}")
    canonical = _canonical_cells(cells)
    records: list[dict[str, Any]] = []
    for file_id in sorted(canonical["File_ID"].unique()):
        for kind, filename in (
            ("expression", "reg001_expr.ome.tif"),
            ("mask", "reg001_mask.ome.tif"),
        ):
            path = root / str(file_id) / filename
            if not path.is_file():
                raise ClusteringError(f"Missing paired TIFF required for PIXIE cache: {path}")
            stat = path.stat()
            records.append(
                {
                    "File_ID": str(file_id),
                    "kind": kind,
                    "path": str(path),
                    "device": int(stat.st_dev),
                    "inode": int(stat.st_ino),
                    "size": int(stat.st_size),
                    "mtime_ns": int(stat.st_mtime_ns),
                    "ctime_ns": int(stat.st_ctime_ns),
                }
            )
    return {"records": records, "sha256": _json_sha256({"records": records})}


def _default_pixie_prefix_cache_root(output_root: Path) -> Path:
    """Place the fresh final-figures cache under the enclosing output root when known."""

    resolved = output_root.resolve()
    for ancestor in (resolved, *resolved.parents):
        if ancestor.name == "runs":
            return ancestor.parent / "final_figures_pixie_prefix_cache"
    return resolved.parent / "final_figures_pixie_prefix_cache"


def _prefix_payload(
    *,
    cells: pd.DataFrame,
    registry_sha256: str,
    marker_names: Sequence[str],
    tiff_identity: Mapping[str, Any],
    runner_path: Path,
    settings: PixieSettings,
    source_h5ad_sha256: str | None,
) -> dict[str, Any]:
    """Describe every image-native input relevant to reusable prefix outputs."""

    pixel_settings = {
        "pixel_som_side": int(settings.pixel_som_side),
        "pixel_meta_clusters": int(settings.pixel_meta_clusters),
        "seed": int(settings.seed),
        "include_hoechst": bool(settings.include_hoechst),
        "zero_signal_policy": str(settings.zero_signal_policy),
        **dict(_PIXIE_PREFIX_FIXED_OPTIONS),
    }
    payload: dict[str, Any] = {
        "schema": _PIXIE_PREFIX_CACHE_SCHEMA,
        "registry_csv_sha256": registry_sha256,
        "marker_names": [str(marker) for marker in marker_names],
        "split_keys": _pixie_split_key(cells),
        "tiff_filesystem_identity": dict(tiff_identity),
        "runner_sha256": _file_sha256(runner_path),
        "pixel_compose_settings": pixel_settings,
    }
    if source_h5ad_sha256 is not None:
        payload["source_h5ad_sha256"] = str(source_h5ad_sha256)
    return payload


def _read_json_mapping(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClusteringError(f"Cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ClusteringError(f"{label} must be a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _required_prefix_checkpoint_identities(prefix_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in _PIXIE_PREFIX_CHECKPOINTS:
        path = prefix_dir / relative
        if not path.is_file():
            raise ClusteringError(
                f"PIXIE prefix cache lacks required checkpoint {relative}; do not reuse it"
            )
        stat = path.stat()
        records.append(
            {
                "relative_path": relative,
                "size": int(stat.st_size),
                "mtime_ns": int(stat.st_mtime_ns),
            }
        )
    return records


def _prefix_manifest_matches(prefix_dir: Path, expected_payload: Mapping[str, Any]) -> bool:
    manifest_path = prefix_dir / "prefix_manifest.json"
    if not manifest_path.is_file():
        return False
    manifest = _read_json_mapping(manifest_path, label="PIXIE prefix manifest")
    if manifest.get("status") != "complete" or manifest.get("payload") != dict(expected_payload):
        return False
    try:
        identities = _required_prefix_checkpoint_identities(prefix_dir)
    except ClusteringError:
        return False
    return manifest.get("checkpoint_identities") == identities


def _legacy_prefix_command(
    *,
    runner: Path,
    registry: Path,
    tiffs_dir: Path,
    prefix_dir: Path,
    settings: PixieSettings,
    stage: str,
) -> list[str]:
    command = [
        sys.executable,
        str(runner),
        "--master",
        str(registry),
        "--tiffs-dir",
        str(tiffs_dir),
        "--output-dir",
        str(prefix_dir),
        "--stage",
        stage,
        "--resume",
        "--tile-size",
        str(_PIXIE_PREFIX_FIXED_OPTIONS["tile_size"]),
        "--blur-sigma",
        str(_PIXIE_PREFIX_FIXED_OPTIONS["blur_sigma"]),
        "--sample-tiles",
        str(_PIXIE_PREFIX_FIXED_OPTIONS["sample_tiles"]),
        "--sample-per-fov",
        str(_PIXIE_PREFIX_FIXED_OPTIONS["sample_per_fov"]),
        "--som-passes",
        str(_PIXIE_PREFIX_FIXED_OPTIONS["som_passes"]),
        "--zero-signal-policy",
        str(settings.zero_signal_policy),
        "--pixel-som-side",
        str(settings.pixel_som_side),
        "--pixel-meta-clusters",
        str(settings.pixel_meta_clusters),
        "--seed",
        str(settings.seed),
    ]
    if settings.include_hoechst:
        command.append("--include-hoechst")
    return command


def _prepare_pixie_tiff_view(
    *,
    prefix_dir: Path,
    source_tiffs: Path,
    cells: pd.DataFrame,
    tiff_identity: Mapping[str, Any],
) -> Path:
    """Create an exact-FOV symlink view required by the legacy runner.

    ``run_streaming_tiff_pixie.py`` intentionally rejects any TIFF FOV not in
    its master registry.  A final-runtime development, selection, or sealed subset thus
    cannot safely point the runner at the complete B004 TIFF directory.  This
    view contains directory symlinks only: pixel bytes remain in the original
    paired OME-TIFF files and no image data are copied into final-runtime outputs.
    """

    source = source_tiffs.resolve()
    file_ids = sorted(_canonical_cells(cells)["File_ID"].unique())
    payload = {
        "schema": _PIXIE_PREFIX_CACHE_SCHEMA,
        "source_tiffs": str(source),
        "file_ids": [str(file_id) for file_id in file_ids],
        "tiff_filesystem_identity_sha256": str(tiff_identity["sha256"]),
    }
    manifest_path = prefix_dir / "tiff_view.json"
    view = prefix_dir / "tiff_fov_view"
    if view.exists() or view.is_symlink():
        if not manifest_path.is_file() or _read_json_mapping(
            manifest_path, label="PIXIE TIFF view manifest"
        ) != payload:
            raise ClusteringError("PIXIE TIFF FOV view does not match the registered prefix inputs")
        observed = sorted(child.name for child in view.iterdir()) if view.is_dir() else []
        if observed != [str(file_id) for file_id in file_ids]:
            raise ClusteringError("PIXIE TIFF FOV view has unexpected FOV entries")
        for file_id in file_ids:
            link = view / str(file_id)
            target = source / str(file_id)
            if not link.is_symlink() or link.resolve() != target:
                raise ClusteringError("PIXIE TIFF FOV view symlink target changed")
        return view

    view.mkdir(parents=True, exist_ok=False)
    try:
        for file_id in file_ids:
            target = source / str(file_id)
            if not target.is_dir():
                raise ClusteringError(f"Missing TIFF FOV directory required for PIXIE view: {target}")
            os.symlink(target, view / str(file_id), target_is_directory=True)
    except OSError as exc:
        raise ClusteringError(
            "Cannot create a final-runtime TIFF FOV symlink view; refusing to copy image data or use extra FOVs"
        ) from exc
    _write_json(manifest_path, payload)
    return view


def _normalise_zero_signal_payload(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Return a copy whose zero-signal policy is separated for safe recovery."""

    copied = json.loads(json.dumps(dict(payload), sort_keys=True))
    settings = copied.get("pixel_compose_settings")
    if not isinstance(settings, dict):
        raise ClusteringError("PIXIE prefix payload lacks pixel_compose_settings")
    policy = settings.pop("zero_signal_policy", None)
    return copied, None if policy is None else str(policy)


def _zero_signal_recovery_checkpoint_paths(
    source_prefix: Path,
    *,
    file_ids: Sequence[str],
) -> list[Path]:
    """Validate raw stage checkpoints reusable after a fail-to-QC policy upgrade."""

    checkpoint_dir = source_prefix / "checkpoints"
    relatives = [
        "mask_areas.npz",
        "pixel_normalization.npz",
        "pixel_som_weights.npy",
        "pixel_som_to_meta.npy",
    ]
    for file_id in file_ids:
        relatives.extend(
            [
                f"pixel_sample_{file_id}.npz",
                f"pixel_node_aggregate_{file_id}.npz",
                f"cell_composition_{file_id}.npz",
            ]
        )
    paths = [checkpoint_dir / relative for relative in relatives]
    missing = [str(path.name) for path in paths if not path.is_file() or path.stat().st_size <= 0]
    if missing:
        raise ClusteringError(
            "Interrupted fail-policy PIXIE prefix lacks a complete reusable raw checkpoint set: "
            f"{missing}"
        )
    if (checkpoint_dir / "all_cell_compositions.npz").is_file():
        raise ClusteringError(
            "Fail-policy PIXIE prefix unexpectedly has a completed cell-composition checkpoint; "
            "do not recover it under a different zero-signal policy"
        )
    return paths


def _recover_zero_signal_prefix(
    *,
    prefix_root: Path,
    destination: Path,
    payload: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Reuse raw checkpoints after the only-safe fail-to-QC PIXIE transition.

    The legacy runner writes each FOV's raw composition before its final
    zero-signal policy check.  If it stopped solely because a few valid H5AD
    cells had no selected-marker pixels, those raw image-derived checkpoints
    are unaffected by switching to the runner's explicit ``qc_unclustered``
    policy.  We materialize a new, policy-hashed prefix instead of mutating the
    failed one, and reject every other incomplete-prefix recovery.
    """

    target_core, target_policy = _normalise_zero_signal_payload(payload)
    if target_policy != "qc_unclustered":
        return None
    split_keys = payload.get("split_keys")
    if not isinstance(split_keys, list):
        raise ClusteringError("PIXIE prefix payload split_keys are malformed")
    file_ids = sorted(
        {
            str(record.get("File_ID"))
            for record in split_keys
            if isinstance(record, Mapping) and record.get("File_ID") is not None
        }
    )
    if not file_ids:
        raise ClusteringError("PIXIE prefix payload contains no registered TIFF FOVs")

    candidates: list[tuple[Path, dict[str, Any], list[Path]]] = []
    for source_prefix in sorted(prefix_root.glob("prefix_*")):
        if source_prefix.resolve() == destination.resolve():
            continue
        request = source_prefix / "prefix_request.json"
        if not request.is_file() or (source_prefix / "prefix_manifest.json").is_file():
            continue
        try:
            source_payload = _read_json_mapping(request, label="PIXIE recovery source request")
            source_core, source_policy = _normalise_zero_signal_payload(source_payload)
        except ClusteringError:
            continue
        if source_policy != "fail" or source_core != target_core:
            continue
        registry = source_prefix / "h5ad_pixie_registry.csv"
        if not registry.is_file() or _file_sha256(registry) != str(payload["registry_csv_sha256"]):
            continue
        try:
            checkpoints = _zero_signal_recovery_checkpoint_paths(source_prefix, file_ids=file_ids)
        except ClusteringError:
            continue
        candidates.append((source_prefix, source_payload, checkpoints))
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ClusteringError(
            "Multiple incomplete fail-policy PIXIE prefixes match this QC policy upgrade; "
            "do not choose a recovery source implicitly"
        )

    source_prefix, source_payload, checkpoints = candidates[0]
    materialized: dict[str, dict[str, Any]] = {}
    for source in checkpoints:
        relative = str(source.relative_to(source_prefix))
        mode = _materialize_prefix_checkpoint(source, destination / relative)
        materialized[relative] = {
            "mode": mode,
            "sha256": _file_sha256(source),
            "size": int(source.stat().st_size),
        }
    recovery = {
        "schema": _PIXIE_PREFIX_CACHE_SCHEMA,
        "status": "recovered_fail_to_qc_unclustered",
        "source_prefix": str(source_prefix),
        "source_request_sha256": _json_sha256(source_payload),
        "source_zero_signal_policy": "fail",
        "target_zero_signal_policy": "qc_unclustered",
        "target_payload_sha256": _json_sha256(dict(payload)),
        "raw_checkpoint_materialization": materialized,
    }
    _write_json(destination / "zero_signal_recovery.json", recovery)
    return recovery


def _prepare_pixie_prefix_cache(
    *,
    prefix_root: Path,
    registry_frame: pd.DataFrame,
    payload: Mapping[str, Any],
    runner: Path,
    tiffs_dir: Path,
    cells: pd.DataFrame,
    tiff_identity: Mapping[str, Any],
    settings: PixieSettings,
    resume: bool,
) -> tuple[Path, bool, Path]:
    """Build or validate an immutable sample/pixel/compose cache namespace."""

    cache_key = _json_sha256(dict(payload))[:24]
    prefix_dir = prefix_root / f"prefix_{cache_key}"
    if _prefix_manifest_matches(prefix_dir, payload):
        return (
            prefix_dir,
            True,
            _prepare_pixie_tiff_view(
                prefix_dir=prefix_dir,
                source_tiffs=tiffs_dir,
                cells=cells,
                tiff_identity=tiff_identity,
            ),
        )
    request_path = prefix_dir / "prefix_request.json"
    if prefix_dir.exists() and any(prefix_dir.iterdir()):
        if not resume or not request_path.is_file():
            raise ClusteringError(
                f"Refusing to reuse incomplete PIXIE prefix cache {prefix_dir}; "
                "choose a fresh final-figures output root or resume the exact registered prefix"
            )
        if _read_json_mapping(request_path, label="PIXIE prefix request") != dict(payload):
            raise ClusteringError("Incomplete PIXIE prefix request does not match the current inputs")
    else:
        prefix_dir.mkdir(parents=True, exist_ok=True)
        _write_json(request_path, payload)
        _recover_zero_signal_prefix(
            prefix_root=prefix_root,
            destination=prefix_dir,
            payload=payload,
        )

    registry = prefix_dir / "h5ad_pixie_registry.csv"
    if registry.is_file():
        expected = _registry_csv_sha256(registry_frame)
        if _file_sha256(registry) != expected:
            raise ClusteringError("PIXIE prefix registry differs from the H5AD-derived registry")
    else:
        registry_frame.to_csv(registry, index=False)
    tiff_view = _prepare_pixie_tiff_view(
        prefix_dir=prefix_dir,
        source_tiffs=tiffs_dir,
        cells=cells,
        tiff_identity=tiff_identity,
    )
    for stage in ("sample", "pixel", "compose"):
        subprocess.run(
            _legacy_prefix_command(
                runner=runner,
                registry=registry,
                tiffs_dir=tiff_view,
                prefix_dir=prefix_dir,
                settings=settings,
                stage=stage,
            ),
            check=True,
        )
    identities = _required_prefix_checkpoint_identities(prefix_dir)
    _write_json(
        prefix_dir / "prefix_manifest.json",
        {
            "schema": _PIXIE_PREFIX_CACHE_SCHEMA,
            "status": "complete",
            "payload": dict(payload),
            "checkpoint_identities": identities,
        },
    )
    return prefix_dir, False, tiff_view


def _materialize_prefix_checkpoint(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
        return "copy"
    return "hardlink"


def _prepare_pixie_cell_stage(
    *,
    destination: Path,
    registry_frame: pd.DataFrame,
    prefix_dir: Path,
    prefix_payload: Mapping[str, Any],
    resume: bool,
) -> tuple[Path, Mapping[str, Any]]:
    """Create a candidate-local cell stage that can read an immutable prefix."""

    materialization_path = destination / "prefix_materialization.json"
    registry_path = destination / "h5ad_pixie_registry.csv"
    registry_sha256 = _registry_csv_sha256(registry_frame)
    expected = {
        "schema": _PIXIE_PREFIX_CACHE_SCHEMA,
        "prefix_dir": str(prefix_dir),
        "prefix_payload_sha256": _json_sha256(dict(prefix_payload)),
        "registry_csv_sha256": registry_sha256,
        "checkpoint_identities": _required_prefix_checkpoint_identities(prefix_dir),
    }
    if destination.exists() and any(destination.iterdir()):
        if not resume or not materialization_path.is_file():
            raise ClusteringError(
                f"PIXIE candidate output already exists without a resumable final-runtime materialization: {destination}"
            )
        materialization = _read_json_mapping(materialization_path, label="PIXIE materialization")
        if {key: materialization.get(key) for key in expected} != expected:
            raise ClusteringError("PIXIE candidate materialization does not match the requested prefix cache")
        if not registry_path.is_file() or _file_sha256(registry_path) != registry_sha256:
            raise ClusteringError("PIXIE candidate registry does not match the H5AD-derived registry")
        for identity in expected["checkpoint_identities"]:
            candidate = destination / str(identity["relative_path"])
            if not candidate.is_file() or candidate.stat().st_size != int(identity["size"]):
                raise ClusteringError("PIXIE candidate is missing a valid materialized prefix checkpoint")
        return registry_path, materialization

    destination.mkdir(parents=True, exist_ok=True)
    registry_frame.to_csv(registry_path, index=False)
    materialized: dict[str, str] = {}
    for identity in expected["checkpoint_identities"]:
        relative = str(identity["relative_path"])
        materialized[relative] = _materialize_prefix_checkpoint(
            prefix_dir / relative, destination / relative
        )
    materialization = {**expected, "materialized_as": materialized}
    _write_json(materialization_path, materialization)
    return registry_path, materialization


def run_tiff_pixie(
    cells: pd.DataFrame,
    marker_names: Sequence[str],
    marker_values: np.ndarray,
    *,
    output_root: str | Path,
    tiffs_dir: str | Path,
    runner_path: str | Path,
    settings: PixieSettings,
    hoechst_values: np.ndarray | None = None,
    resume: bool = False,
    prefix_cache_root: str | Path | None = None,
    source_h5ad_sha256: str | None = None,
) -> ClusterRun:
    """Execute a candidate-local cell SOM over a verified image-native prefix.

    Pixel sampling, pixel SOM, and per-cell pixel composition are independent
    of the cell-SOM side and metacluster count.  The final runtime therefore creates one
    immutable prefix for an exact H5AD registry/TIFF/pixel-settings signature,
    then materializes only the legacy runner's read-only prefix checkpoints in
    each configuration-hashed candidate directory.  This preserves tile-based
    image processing while avoiding repeated pixel passes for cell-SOM grids.
    """

    settings_dict = asdict(settings)
    marker_schema = tuple(str(marker) for marker in marker_names)
    if settings.include_hoechst and "Hoechst1" not in marker_schema:
        raise ClusteringError(
            "PIXIE include_hoechst=True conflicts with the H5AD marker schema: "
            "Hoechst1 is not an H5AD X marker"
        )
    if settings.zero_signal_policy != "qc_unclustered":
        raise ClusteringError(
            "Final TIFF PIXIE requires zero_signal_policy='qc_unclustered' to preserve "
            "the complete H5AD cell registry without assigning zero-signal cells to a biological cluster"
        )
    run_hash = stable_config_hash("pixie", settings_dict)
    destination = Path(output_root) / f"pixie_{run_hash}"
    runner = Path(runner_path).expanduser().resolve()
    if not runner.is_file():
        raise ClusteringError(f"Streaming PIXIE runner not found: {runner}")
    resolved_tiffs = Path(tiffs_dir).expanduser().resolve()
    registry_frame = _pixie_registry_frame(
        cells,
        marker_names,
        marker_values,
        include_hoechst=hoechst_values if settings.include_hoechst else None,
    )
    registry_sha256 = _registry_csv_sha256(registry_frame)
    tiff_identity = _tiff_filesystem_identity(cells, resolved_tiffs)
    prefix_payload = _prefix_payload(
        cells=cells,
        registry_sha256=registry_sha256,
        marker_names=marker_names,
        tiff_identity=tiff_identity,
        runner_path=runner,
        settings=settings,
        source_h5ad_sha256=source_h5ad_sha256,
    )
    cache_root = (
        Path(prefix_cache_root).expanduser().resolve()
        if prefix_cache_root is not None
        else _default_pixie_prefix_cache_root(destination)
    )
    prefix_dir, prefix_reused, tiff_view = _prepare_pixie_prefix_cache(
        prefix_root=cache_root,
        registry_frame=registry_frame,
        payload=prefix_payload,
        runner=runner,
        tiffs_dir=resolved_tiffs,
        cells=cells,
        tiff_identity=tiff_identity,
        settings=settings,
        resume=resume,
    )
    registry, materialization = _prepare_pixie_cell_stage(
        destination=destination,
        registry_frame=registry_frame,
        prefix_dir=prefix_dir,
        prefix_payload=prefix_payload,
        resume=resume,
    )
    command = _legacy_prefix_command(
        runner=runner,
        registry=registry,
        tiffs_dir=tiff_view,
        prefix_dir=destination,
        settings=settings,
        stage="cell",
    )
    command.extend(
        [
            "--cell-som-side",
            str(settings.cell_som_side),
            "--cell-meta-clusters",
            str(settings.cell_meta_clusters),
            "--cell-som-sigma",
            str(settings.cell_som_sigma),
            "--cell-som-learning-rate",
            str(settings.cell_som_learning_rate),
            "--cell-som-iterations",
            str(settings.cell_som_iterations),
        ]
    )
    subprocess.run(command, check=True)
    result_path = destination / "master_pixie_clusters.csv"
    if not result_path.is_file():
        raise ClusteringError("Streaming PIXIE did not produce master_pixie_clusters.csv")
    result = pd.read_csv(result_path)
    cluster_column = "pixie_cell_cluster"
    if cluster_column not in result.columns:
        raise ClusteringError(f"Streaming PIXIE output lacks {cluster_column}")
    assignments = result.loc[:, [*KEY_COLUMNS, cluster_column]].rename(columns={cluster_column: "cluster"})
    assignments = validate_keyed_assignment(assignments, expected_keys=_canonical_cells(cells), cluster_column="cluster")
    assignments["method"] = "pixie"
    return ClusterRun(
        method="pixie",
        settings=settings_dict,
        assignments=assignments,
        diagnostics={
            "n_clusters": int(assignments["cluster"].nunique()),
            "backend": "streaming-tiff-pixie",
            "output_dir": str(destination),
            "registry": str(registry),
            "prefix_cache_dir": str(prefix_dir),
            "prefix_cache_reused": bool(prefix_reused),
            "prefix_cache_payload_sha256": _json_sha256(prefix_payload),
            "tiff_fov_view": str(tiff_view),
            "prefix_materialization": dict(materialization),
        },
    )


def evaluate_label_free_run(
    features: np.ndarray,
    primary: ClusterRun,
    seed_runs: Iterable[ClusterRun],
    *,
    min_viable_cluster_size: int = 50,
    target_cluster_count: int = 100,
) -> Mapping[str, Any]:
    """Return a serializable, label-free diagnostics record for candidate ranking."""

    metric_features, primary_labels, seed_labels, _ = label_free_metric_inputs(
        features,
        primary,
        seed_runs,
    )
    metrics = label_free_metrics(
        metric_features,
        primary_labels,
        seed_labels,
        min_viable_cluster_size=min_viable_cluster_size,
        target_cluster_count=target_cluster_count,
    )
    return {**asdict(metrics), "method": primary.method, "settings": dict(primary.settings)}


def label_free_metric_inputs(
    features: np.ndarray,
    primary: ClusterRun,
    seed_runs: Iterable[ClusterRun],
) -> tuple[np.ndarray, pd.Series, list[pd.Series], np.ndarray]:
    """Return biological rows/labels eligible for label-free selection metrics.

    TIFF PIXIE preserves every H5AD cell, including its registered cluster-0
    zero-signal QC state.  That state is intentionally not a biological
    cluster, so it must not change candidate viability, target-cluster count,
    marker coherence, or seed stability.  It is filtered only for PIXIE and
    only when the frozen runner setting confirms the explicit QC policy.
    Every seed must place exactly the same keyed rows in that QC state; a
    mismatch signals an invalid TIFF contract rather than an opportunity to
    hide a stability failure.
    """

    matrix = np.asarray(features)
    if matrix.ndim != 2 or matrix.shape[0] != len(primary.assignments):
        raise ClusteringError("Label-free metric features do not match primary assignments")
    runs = list(seed_runs)
    if not runs:
        raise ClusteringError("Label-free metrics require at least one seed run")
    primary_labels = primary.assignments["cluster"].astype(str).reset_index(drop=True)
    primary_keys = primary.assignments.loc[:, list(KEY_COLUMNS)].reset_index(drop=True)
    for run in runs:
        if str(run.method) != str(primary.method):
            raise ClusteringError("Label-free seed runs must use the same clustering method")
        if len(run.assignments) != len(primary.assignments):
            raise ClusteringError("Label-free seed assignments have different cell coverage")
        run_keys = run.assignments.loc[:, list(KEY_COLUMNS)].reset_index(drop=True)
        if not run_keys.equals(primary_keys):
            raise ClusteringError("Label-free seed assignments are not key-aligned")
    if str(primary.method) != "pixie":
        return (
            matrix,
            primary_labels,
            [run.assignments["cluster"].astype(str).reset_index(drop=True) for run in runs],
            np.ones(len(primary_labels), dtype=bool),
        )

    policy = primary.settings.get("zero_signal_policy") if isinstance(primary.settings, Mapping) else None
    if not isinstance(policy, str) or policy.strip() != "qc_unclustered":
        raise ClusteringError(
            "PIXIE label-free metrics require frozen zero_signal_policy='qc_unclustered'"
        )
    biological_mask = primary_labels.ne("0").to_numpy()
    if not biological_mask.any():
        raise ClusteringError("PIXIE has no biological cells eligible for label-free metrics")
    labels_by_seed: list[pd.Series] = []
    for run in runs:
        run_policy = run.settings.get("zero_signal_policy") if isinstance(run.settings, Mapping) else None
        if not isinstance(run_policy, str) or run_policy.strip() != "qc_unclustered":
            raise ClusteringError(
                "PIXIE seed metrics require frozen zero_signal_policy='qc_unclustered'"
            )
        labels = run.assignments["cluster"].astype(str).reset_index(drop=True)
        if not np.array_equal(labels.eq("0").to_numpy(), ~biological_mask):
            raise ClusteringError("PIXIE QC-unclustered key coverage differs across seeds")
        labels_by_seed.append(labels.loc[biological_mask].reset_index(drop=True))
    return (
        matrix[biological_mask],
        primary_labels.loc[biological_mask].reset_index(drop=True),
        labels_by_seed,
        biological_mask,
    )
