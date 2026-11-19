"""Offline reviewer analyses; no inference, scheduler, or networking code.

Reference labels enter scoring and supervised fitting only. Ward construction and
calibration cluster partitions have no reference-label arguments. Baselines are
admitted only from the exact authoritative 47-marker measurement source.
"""
from __future__ import annotations

import hashlib
import heapq
import json
import platform
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import adjusted_rand_score, f1_score, normalized_mutual_info_score

KEYS = ["File_ID", "ID"]
METHODS = ("leiden", "flowsom", "spatialsort", "pixie_tiff")
FAMILIES = ("openai", "anthropic", "google", "deepseek")
C_GRID = (0.001, 0.01, 0.1, 1.0, 10.0)
CLUSTER_SPLIT_VERSION = "reviewer47-calibration-cluster-split-v1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


def file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write_json(path: Path, value):
    path.write_text(json.dumps(_json_safe(value), sort_keys=True, indent=2,
                               allow_nan=False) + "\n")


def _new_output(path: Path | str) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=False)
    return out


def _environment():
    return {"python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "scipy": scipy.__version__,
            "sklearn": sklearn.__version__}


def _receipt(out, kind, inputs, details):
    outputs = {str(p.relative_to(out)): {"sha256": file_sha256(p), "bytes": p.stat().st_size}
               for p in sorted(out.rglob("*")) if p.is_file() and p.name != "verification.json"}
    receipt = {"schema": f"reviewer47.{kind}.offline.v1", "status": "completed",
               "offline_only": True, "new_annotation_calls": 0,
               "scientific_parameters_tuned_on_test": False,
               "environment": _environment(), "input_sha256": inputs,
               "outputs": outputs, **details}
    write_json(out / "verification.json", receipt)
    return receipt


@dataclass
class Bundle:
    path: Path
    protocol: dict
    memberships: pd.DataFrame
    reference: pd.DataFrame
    profiles: dict[str, pd.DataFrame]
    markers: list[str]
    inputs: dict[str, str]


def load_bundle(path: Path | str, *, include_reference_labels=True) -> Bundle:
    path = Path(path)
    protocol = json.loads((path / "protocol.json").read_text())
    markers = protocol["markers"]
    if len(markers) != 47 or len(set(markers)) != 47:
        raise ValueError("Expected exactly 47 unique markers")
    if len(protocol["ontology"]) != 28 or "Noise" not in protocol["ontology"]:
        raise ValueError("The fixed original 28-label vocabulary including Noise is required")
    files = ["protocol.json", "memberships.csv.gz", "reference_cells.csv.gz",
             "profiles_means_z.csv", "profiles_fractions.csv"]
    inputs = {n: file_sha256(path / n) for n in files}
    memberships = pd.read_csv(path / "memberships.csv.gz", dtype=str, keep_default_na=False)
    if include_reference_labels:
        reference = pd.read_csv(path / "reference_cells.csv.gz", dtype={k: str for k in KEYS})
    else:
        # Region and assignment metadata are available without opening label rows.
        reference = memberships.copy()
        reference["split"] = reference.File_ID.map(protocol["split"])
    if memberships[KEYS].duplicated().any() or reference[KEYS].duplicated().any():
        raise ValueError("Duplicate cell keys")
    if len(memberships) != protocol["n_cells"] or len(reference) != len(memberships):
        raise ValueError("Incorrect frozen cell population")
    if memberships[KEYS].eq("").any().any() or not memberships[KEYS].equals(reference[KEYS]):
        raise ValueError("Cell key join or order differs")
    if set(reference.File_ID) != set(protocol["split"]):
        raise ValueError("Region identities differ from frozen split")
    if not reference["split"].equals(reference.File_ID.map(protocol["split"])):
        raise ValueError("Incorrect training/calibration/test membership")
    if include_reference_labels:
        truth = pd.to_numeric(reference["truth_label_code"], errors="raise").to_numpy()
        if not np.all(np.isfinite(truth) & (truth == np.floor(truth)) & (truth >= 0) & (truth < 28)):
            raise ValueError("Reference codes must be integers in the fixed 28-label vocabulary")
    for method in METHODS:
        if memberships[method].eq("").any() or not memberships[method].equals(reference[method].astype(str)):
            raise ValueError(f"Frozen assignment mismatch: {method}")
    profiles = {}
    for name, filename in [("means", "profiles_means_z.csv"), ("fractions", "profiles_fractions.csv")]:
        frame = pd.read_csv(path / filename, dtype={"method": str, "cluster_id": str})
        if list(frame.columns) != ["method", "cluster_id", "n_cells", *markers]:
            raise ValueError(f"Missing or reordered markers in {filename}")
        if frame[["method", "cluster_id"]].duplicated().any():
            raise ValueError("Duplicate cluster profiles")
        if set(frame.method) != set(METHODS) or not np.isfinite(frame[markers].to_numpy()).all():
            raise ValueError("Incorrect profile method coverage or nonfinite values")
        if name == "fractions" and not frame[markers].apply(lambda x: x.between(0, 1)).all().all():
            raise ValueError("Fractions must be in [0,1]")
        for method in METHODS:
            counts = memberships[method].value_counts().sort_index()
            f = frame[frame.method == method].set_index("cluster_id").sort_index()
            if not f.index.equals(counts.index) or not np.array_equal(f.n_cells.to_numpy(), counts.to_numpy()):
                raise ValueError(f"Profile populations differ from memberships: {method}")
        profiles[name] = frame
    if not profiles["means"][["method", "cluster_id", "n_cells"]].equals(
            profiles["fractions"][["method", "cluster_id", "n_cells"]]):
        raise ValueError("Paired profile ordering differs")
    return Bundle(path, protocol, memberships, reference, profiles, markers, inputs)


def weighted_ward(cluster_ids: Iterable[str], counts, means, targets=(100, 200)):
    """One deterministic weighted Ward tree; no reference labels are accepted.

    Cost is n_A*n_B/(n_A+n_B)*||mu_A-mu_B||^2. Exact floating-point ties
    use lexicographic tuples of original IDs; snapshots use canonical leaf order.
    """
    ids = [str(x) for x in cluster_ids]
    n = np.asarray(counts, dtype=np.float64)
    x = np.asarray(means, dtype=np.float64)
    targets = tuple(sorted(set(int(k) for k in targets), reverse=True))
    if len(set(ids)) != len(ids) or len(ids) != len(n) or x.ndim != 2 or x.shape[0] != len(ids):
        raise ValueError("Incorrect Ward profile shape or duplicate cluster IDs")
    if not targets or min(targets) < 1 or max(targets) > len(ids):
        raise ValueError("Coarsening targets must lie within the occupied-cluster count")
    if not np.isfinite(x).all() or not np.isfinite(n).all() or (n <= 0).any() or (n != np.floor(n)).any():
        raise ValueError("Ward requires finite centroids and positive integer counts")
    order = sorted(range(len(ids)), key=lambda i: ids[i])
    nodes = {j: {"leaves": (ids[i],), "n": float(n[i]), "mean": x[i].copy()}
             for j, i in enumerate(order)}
    active = set(nodes)
    heap = []

    def pair(a, b):
        if nodes[a]["leaves"] > nodes[b]["leaves"]:
            a, b = b, a
        aa, bb = nodes[a], nodes[b]
        delta = aa["mean"] - bb["mean"]
        cost = aa["n"] * bb["n"] / (aa["n"] + bb["n"]) * float(np.dot(delta, delta))
        return cost, aa["leaves"], bb["leaves"], a, b

    def snapshot():
        groups = sorted(active, key=lambda a: nodes[a]["leaves"])
        return {leaf: f"c{len(groups)}_{i:03d}" for i, a in enumerate(groups) for leaf in nodes[a]["leaves"]}

    for a in active:
        for b in active:
            if a < b:
                heapq.heappush(heap, pair(a, b))
    snapshots, trace = {}, []
    if len(active) in targets:
        snapshots[len(active)] = snapshot()
    next_id = len(nodes)
    while len(active) > min(targets):
        while True:
            cost, left, right, a, b = heapq.heappop(heap)
            if a in active and b in active:
                break
        aa, bb = nodes[a], nodes[b]
        total = aa["n"] + bb["n"]
        nodes[next_id] = {"leaves": tuple(sorted(left + right)), "n": total,
                          "mean": (aa["n"] * aa["mean"] + bb["n"] * bb["mean"]) / total}
        active.remove(a)
        active.remove(b)
        trace.append({"step": len(trace) + 1, "clusters_after": len(active) + 1,
                      "left_leaves": list(left), "right_leaves": list(right),
                      "left_n": int(aa["n"]), "right_n": int(bb["n"]), "merged_n": int(total),
                      "ward_cost": cost, "ward_cost_hex": cost.hex()})
        for other in active:
            heapq.heappush(heap, pair(next_id, other))
        active.add(next_id)
        next_id += 1
        if len(active) in targets:
            snapshots[len(active)] = snapshot()
    return snapshots, trace


def partition_metrics(truth, assignments):
    truth, assignments = np.asarray(truth), np.asarray(assignments)
    if len(truth) == 0 or len(truth) != len(assignments):
        raise ValueError("Partition scoring requires a nonempty exact cell join")
    tab = pd.crosstab(pd.Series(assignments, name="cluster"), pd.Series(truth, name="label"))
    return {"n_cells": len(truth), "occupied_clusters": tab.shape[0],
            "purity": float(tab.max(axis=1).sum() / len(truth)),
            "ari": float(adjusted_rand_score(truth, assignments)),
            "nmi": float(normalized_mutual_info_score(truth, assignments, average_method="arithmetic"))}


def run_granularity(bundle_path, output, targets=(100, 200)):
    bundle = load_bundle(bundle_path, include_reference_labels=False)
    out = _new_output(output)
    cells, ref = bundle.memberships, bundle.reference
    assignments = {k: cells[KEYS].copy() for k in sorted(set(targets))}
    metric_rows, map_rows, sizes, frozen_assignments = [], [], [], {}
    for method in METHODS:
        p = bundle.profiles["means"].query("method == @method").sort_values("cluster_id")
        snapshots, trace = weighted_ward(p.cluster_id, p.n_cells, p[bundle.markers], targets)
        write_json(out / f"{method}_merge_trace.json", trace)
        all_assignments = {len(p): cells[method].to_numpy(),
                           **{k: cells[method].map(m).to_numpy() for k, m in snapshots.items()}}
        frozen_assignments[method] = all_assignments
        for k, mapping in snapshots.items():
            if len(mapping) != len(p) or len(set(mapping.values())) != k:
                raise AssertionError("Coarsening lost or duplicated a cluster")
            assignments[k][method] = cells[method].map(mapping)
            if assignments[k][method].isna().any():
                raise AssertionError("Missing coarse cell assignment")
            map_rows.extend({"method": method, "target_k": k, "original_cluster_id": original,
                             "coarse_cluster_id": coarse} for original, coarse in sorted(mapping.items()))
        for k, labels in sorted(all_assignments.items()):
            value_counts = pd.Series(labels).value_counts().sort_index()
            sizes.extend({"method": method, "k": k, "cluster_id": str(c), "n_cells": int(n)}
                         for c, n in value_counts.items())
    pd.DataFrame(map_rows).to_csv(out / "cluster_maps.csv", index=False)
    pd.DataFrame(sizes).to_csv(out / "cluster_sizes.csv", index=False)
    for k, frame in assignments.items():
        frame.to_csv(out / f"assignments_K{k}.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    sealed = {p.name: file_sha256(p) for p in sorted(out.iterdir()) if p.is_file()}
    write_json(out / "coarsening_freeze.json", {"schema": "reviewer47.coarsening_freeze.v1",
        "reference_label_values_materialized": False, "output_sha256": sealed,
        "algorithm": "cell-count-weighted Ward; exact-cost ties use sorted original ID tuples"})
    # Only after all methods' assignments/traces are persisted and sealed do we
    # materialize reference values. Checksums above read bytes, not label fields.
    scored_bundle = load_bundle(bundle_path, include_reference_labels=True)
    if scored_bundle.inputs != bundle.inputs:
        raise ValueError("Frozen input files changed between construction and scoring")
    ref = scored_bundle.reference
    for method, all_assignments in frozen_assignments.items():
        for k, labels in sorted(all_assignments.items()):
            for region in [*sorted(ref.File_ID.unique()), "pooled"]:
                mask = np.ones(len(ref), bool) if region == "pooled" else ref.File_ID.eq(region).to_numpy()
                metric_rows.append({"method": method, "k": k, "region": region,
                                    "split": "pooled" if region == "pooled" else bundle.protocol["split"][region],
                                    **partition_metrics(ref.truth_label_code.to_numpy()[mask], labels[mask])})
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(out / "regional_metrics.csv", index=False)
    metrics.query("split == 'test'").groupby(["method", "k"], sort=True)[["purity", "ari", "nmi"]].mean().reset_index().to_csv(
        out / "equal_test_region_metrics.csv", index=False)
    return _receipt(out, "granularity", bundle.inputs,
                    {"cells": len(cells), "targets": sorted(set(targets)), "methods": list(METHODS),
                     "reference_noise_preserved": True, "reference_labels_used_to_build_tree": False,
                     "reference_labels_materialized_after_assignment_freeze": True,
                     "interpretation": "Post-clustering coarsening; not native-K fits or LLM annotation-ranking evidence."})


def cluster_partition(method: str, cluster_id: str) -> str:
    digest = hashlib.sha256(canonical_bytes([CLUSTER_SPLIT_VERSION, 42, str(method), str(cluster_id)])).hexdigest()
    return "development" if int(digest, 16) % 2 == 0 else "evaluation"


def agreement_scores(predictions):
    """Own-label support / FOUR; missing other predictions never shrink denominator."""
    a = np.asarray(predictions)
    if a.ndim != 2 or a.shape[1] != 4:
        raise ValueError("Exactly four prespecified model columns are required")
    valid = np.isfinite(a) & (a == np.floor(a)) & (a >= 0) & (a < 28)
    scores = np.full(a.shape, np.nan)
    for j in range(4):
        scores[valid[:, j], j] = np.sum(valid & (a == a[:, j, None]), axis=1)[valid[:, j]] / 4.0
    return scores


def _fit_calibrator(scores, correct, regions):
    scores, correct, regions = np.asarray(scores, float), np.asarray(correct, int), np.asarray(regions)
    valid = np.isfinite(scores)
    if not valid.any():
        return None, {"kind": "unavailable", "reason": "no delivered development predictions"}, None
    x, y, r = scores[valid], correct[valid], regions[valid]
    counts = pd.Series(r).value_counts()
    w = np.array([len(r) / (len(counts) * counts[v]) for v in r], dtype=float)
    constant = float((np.dot(w, y) + 0.5) / (w.sum() + 1.0))
    if len(np.unique(y)) < 2:
        return lambda s: np.full(np.asarray(s).shape, constant), {"kind": "constant", "probability": constant,
                "reason": "single-class development outcomes", "development_delivered_cells": len(x)}, constant
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000, tol=1e-10, random_state=42)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(x[:, None], y, sample_weight=w)
    return lambda s: model.predict_proba(np.asarray(s)[:, None])[:, 1], {
        "kind": "logistic", "C": 1.0, "coefficient": float(model.coef_[0, 0]),
        "intercept": float(model.intercept_[0]), "development_delivered_cells": len(x),
        "development_regions": sorted(str(v) for v in counts.index),
        "region_weighting": "equal total region weight; weights sum to delivered development cell count"}, constant


def binary_score_metrics(probability, correct, delivered):
    probability, correct, delivered = np.asarray(probability, float), np.asarray(correct, bool), np.asarray(delivered, bool)
    if not (probability.shape == correct.shape == delivered.shape) or probability.ndim != 1:
        raise ValueError("Incorrect probability/outcome join")
    valid = delivered & np.isfinite(probability)
    n = len(correct)
    result = {"planned_cells": n, "delivered_cells": int(delivered.sum()),
              "delivery_coverage": float(delivered.mean()) if n else np.nan,
              "reference_agreement_planned": float((correct & delivered).mean()) if n else np.nan,
              "probability_metric_cells": int(valid.sum()), "brier": np.nan, "log_loss": np.nan,
              "ece": np.nan}
    if valid.any():
        p, y = probability[valid], correct[valid].astype(float)
        if ((p < 0) | (p > 1)).any():
            raise ValueError("Probabilities must lie in [0,1]")
        clipped = np.clip(p, 1e-12, 1 - 1e-12)
        result.update(brier=float(np.mean((p - y) ** 2)),
                      log_loss=float(-np.mean(y * np.log(clipped) + (1 - y) * np.log(1 - clipped))),
                      ece=float(sum(np.sum(p == v) / len(p) * abs(v - y[p == v].mean()) for v in np.unique(p))))
    return result


def risk_coverage(probability, correct, delivered, thresholds):
    p, y, delivered = np.asarray(probability, float), np.asarray(correct, bool), np.asarray(delivered, bool)
    n = len(p)
    rows = []
    for t in sorted(set(float(v) for v in thresholds)):
        retained = delivered & np.isfinite(p) & (p >= t)
        rows.append({"threshold": t, "planned_cells": n, "retained_cells": int(retained.sum()),
                     "coverage": float(retained.sum() / n) if n else np.nan,
                     "risk": float(1 - y[retained].mean()) if retained.any() else np.nan,
                     "ties_kept_together": True})
    return rows


def run_agreement_calibration(bundle_path, output):
    bundle = load_bundle(bundle_path, include_reference_labels=False)
    out = _new_output(output)
    frozen_parts = {method: {c: cluster_partition(method, c) for c in sorted(bundle.memberships[method].unique())}
                    for method in METHODS}
    splits = [{"method": method, "cluster_id": c, "partition": partition}
              for method, rows in frozen_parts.items() for c, partition in rows.items()]
    split_path = out / "calibration_cluster_split.csv"
    pd.DataFrame(splits).to_csv(split_path, index=False)
    write_json(out / "calibration_split_freeze.json", {"schema": "reviewer47.calibration_split_freeze.v1",
        "split_version": CLUSTER_SPLIT_VERSION, "split_sha256": file_sha256(split_path),
        "reference_and_prediction_values_materialized": False})
    scored_bundle = load_bundle(bundle_path, include_reference_labels=True)
    if scored_bundle.inputs != bundle.inputs:
        raise ValueError("Inputs changed after calibration split was frozen")
    bundle = scored_bundle
    prediction_file = bundle.path / "cluster_predictions.csv"
    required = ["model_family", "method", "arm", "cluster_id", "pred_label_code"]
    # Do not load the reference-derived diagnostic columns in this source table.
    preds = pd.read_csv(prediction_file, dtype={"cluster_id": str}, usecols=required)
    preds = preds[preds.arm.eq("all_means_fractions")].copy()
    if preds[["model_family", "method", "arm", "cluster_id"]].duplicated().any():
        raise ValueError("Duplicate condition/cluster prediction")
    if not set(preds.model_family).issubset(FAMILIES) or not set(preds.method).issubset(METHODS):
        raise ValueError("Unexpected method/model predictions")
    metrics, reliability, risks, calibrators = [], [], [], {}
    ref = bundle.reference
    for method in METHODS:
        cluster_ids = sorted(bundle.memberships[method].unique())
        cluster_index = {c: i for i, c in enumerate(cluster_ids)}
        rows = preds[preds.method.eq(method)]
        if not set(rows.cluster_id).issubset(cluster_ids):
            raise ValueError("Extra prediction cluster IDs")
        matrix = np.full((len(cluster_ids), 4), np.nan)
        for j, family in enumerate(FAMILIES):
            selected = rows[rows.model_family.eq(family)]
            values = pd.to_numeric(selected.pred_label_code, errors="coerce").to_numpy(dtype=float)
            for c, value in zip(selected.cluster_id, values):
                matrix[cluster_index[c], j] = value
        valid = np.isfinite(matrix) & (matrix == np.floor(matrix)) & (matrix >= 0) & (matrix < 28)
        support = agreement_scores(matrix)
        parts = frozen_parts[method]
        cell_index = bundle.memberships[method].map(cluster_index).to_numpy()
        cell_part = bundle.memberships[method].map(parts).to_numpy()
        dev = (ref.split.eq("calibration").to_numpy() & (cell_part == "development"))
        evaluation = (ref.split.eq("test").to_numpy() & (cell_part == "evaluation"))
        if set(bundle.memberships.loc[dev, method]) & set(bundle.memberships.loc[evaluation, method]):
            raise AssertionError("Development/evaluation cluster overlap")
        if set(ref.loc[dev, "File_ID"]) & set(ref.loc[evaluation, "File_ID"]):
            raise AssertionError("Development/evaluation region overlap")
        truth = ref.truth_label_code.to_numpy(dtype=int)
        for j, family in enumerate(FAMILIES):
            score = support[cell_index, j]
            delivered = valid[cell_index, j]
            correct = delivered & (matrix[cell_index, j] == truth)
            fn, record, constant = _fit_calibrator(score[dev], correct[dev], ref.File_ID.to_numpy()[dev])
            record.update(method=method, model_family=family, development_planned_cells=int(dev.sum()),
                          evaluation_planned_cells=int(evaluation.sum()))
            calibrators[f"{method}/{family}"] = record
            calibrated = np.full(len(ref), np.nan)
            if fn is not None:
                calibrated[delivered] = fn(score[delivered])
            constant_p = np.full(len(ref), np.nan if constant is None else constant)
            variants = {"raw_agreement": score, "recalibrated": calibrated, "development_constant": constant_p}
            test_regions = sorted(r for r, split in bundle.protocol["split"].items() if split == "test")
            for region in [*test_regions, "pooled"]:
                mask = evaluation if region == "pooled" else evaluation & ref.File_ID.eq(region).to_numpy()
                for variant, p in variants.items():
                    label = {"method": method, "model_family": family, "variant": variant, "region": region}
                    metrics.append({**label, **binary_score_metrics(p[mask], correct[mask], delivered[mask])})
                    valid_p = delivered[mask] & np.isfinite(p[mask])
                    for v in np.unique(p[mask][valid_p]):
                        group = valid_p & (p[mask] == v)
                        reliability.append({**label, "predicted_probability": float(v),
                                            "observed_reference_agreement": float(correct[mask][group].mean()),
                                            "cells": int(group.sum()), "planned_cells": int(mask.sum())})
                    thresholds = (0.25, 0.5, 0.75, 1.0) if variant == "raw_agreement" else (
                        fn(np.array([0.25, 0.5, 0.75, 1.0])) if variant == "recalibrated" and fn is not None else
                        ([] if constant is None else [constant]))
                    risks.extend({**label, **r} for r in risk_coverage(p[mask], correct[mask], delivered[mask], thresholds))
    metric_frame = pd.DataFrame(metrics)
    metric_frame.to_csv(out / "calibration_metrics.csv", index=False)
    equal_rows = []
    for key, frame in metric_frame[metric_frame.region.ne("pooled")].groupby(
            ["method", "model_family", "variant"], sort=True):
        entry = dict(zip(["method", "model_family", "variant"], key))
        entry["test_regions"] = len(test_regions)
        for column in ["delivery_coverage", "reference_agreement_planned", "brier", "log_loss", "ece"]:
            # Undefined regional probability metrics do not disappear from the denominator.
            values = frame[column].to_numpy(dtype=float)
            entry[column] = float(values.mean()) if len(values) == len(test_regions) and np.isfinite(values).all() else np.nan
        equal_rows.append(entry)
    pd.DataFrame(equal_rows).to_csv(out / "calibration_equal_test_region_metrics.csv", index=False)
    pd.DataFrame(reliability).to_csv(out / "calibration_reliability.csv", index=False)
    pd.DataFrame(risks).to_csv(out / "calibration_risk_coverage.csv", index=False)
    write_json(out / "calibrators.json", calibrators)
    return _receipt(out, "agreement_calibration", {**bundle.inputs, prediction_file.name: file_sha256(prediction_file)},
                    {"conditions": len(calibrators), "split_version": CLUSTER_SPLIT_VERSION,
                     "cluster_and_region_separation_verified": True, "support_denominator": 4,
                     "split_sealed_before_reference_and_prediction_values": True,
                     "probability_metrics": "Conditional on delivered predictions; planned-denominator coverage is reported separately.",
                     "evaluation_population": "Test-region cells in hash-held-out cluster IDs; not the entire primary benchmark population.",
                     "interpretation": "Retrospective within-donor cross-model agreement calibration; not run-to-run repeatability or biological confidence."})


def _h5_string(node):
    import h5py
    if isinstance(node, h5py.Group):
        categories, codes = node["categories"].asstr()[:], node["codes"][:]
        if (codes < 0).any() or (codes >= len(categories)).any():
            raise ValueError("Missing categorical source values")
        return categories[codes]
    return node.asstr()[:]


def load_authoritative_cells(bundle: Bundle, h5ad_path):
    import h5py
    h5ad_path = Path(h5ad_path)
    expected = bundle.protocol["measurement_source"]["sha256"]
    if file_sha256(h5ad_path) != expected:
        raise ValueError("Authoritative H5AD checksum mismatch; no source substitution is allowed")
    with h5py.File(h5ad_path, "r") as handle:
        if list(_h5_string(handle["var/_index"])) != bundle.markers[:45]:
            raise ValueError("Missing or reordered H5AD markers")
        if handle["X"].shape != (len(bundle.reference), 45) or handle["X"].dtype != np.float64:
            raise ValueError("Incorrect authoritative cell matrix")
        raw = np.column_stack([handle["X"][:], handle["obs/CD123"][:], handle["obs/CDX2"][:]])
        keys = pd.DataFrame({"File_ID": _h5_string(handle["obs/File_ID"]),
                             "ID": handle["obs/ID"][:].astype(str)})
    if not keys.equals(bundle.memberships[KEYS]) or keys.duplicated().any() or not np.isfinite(raw).all():
        raise ValueError("Cell join or finite-marker admission failed")
    return raw, keys, expected


def cell_feature_views(raw, train_mask):
    raw = np.asarray(raw, dtype=np.float64)
    train_mask = np.asarray(train_mask, bool)
    if raw.ndim != 2 or raw.shape[1] != 47 or not np.isfinite(raw).all() or len(train_mask) != len(raw) or not train_mask.any():
        raise ValueError("Need complete 47-marker cells and a nonempty training population")
    transformed = np.arcsinh(raw / 5.0)
    center, scale = transformed[train_mask].mean(0), transformed[train_mask].std(0, ddof=0)
    scale = np.where(scale == 0, 1.0, scale)
    z = (transformed - center) / scale
    return {"all_means": z, "all_means_fractions": np.column_stack([z, raw > 0])}, center, scale


def fit_centroids(x, labels):
    x, labels = np.asarray(x, float), np.asarray(labels, int)
    if len(x) != len(labels) or not len(x):
        raise ValueError("Incorrect training population")
    classes = np.unique(labels)
    return classes, np.stack([x[labels == c].mean(0) for c in classes])


def centroid_predict(classes, centroids, query):
    distances = ((np.asarray(query)[:, None, :] - centroids[None, :, :]) ** 2).sum(2)
    # Sorted class order supplies a deterministic lowest-label tie break.
    return np.asarray(classes)[np.argmin(distances, axis=1)]


def classifier_metrics(truth, prediction, n_labels=28):
    truth, prediction = np.asarray(truth, int), np.asarray(prediction, int)
    valid = (prediction >= 0) & (prediction < n_labels)
    return {"planned_cells": len(truth), "delivered_cells": int(valid.sum()),
            "delivery_coverage": float(valid.mean()), "reference_agreement": float((prediction == truth).mean()),
            "macro_f1": float(f1_score(truth, prediction, labels=list(range(n_labels)), average="macro", zero_division=0))}


def run_classical_baselines(bundle_path, output, h5ad_path):
    bundle = load_bundle(bundle_path)
    raw, _, h5ad_sha = load_authoritative_cells(bundle, h5ad_path)
    ref = bundle.reference
    train = ref.split.eq("train").to_numpy()
    views, center, scale = cell_feature_views(raw, train)
    # Verify the full-precision query statistics against the frozen source before fitting.
    queries = {}
    for method in METHODS:
        p = bundle.profiles["means"].query("method == @method").sort_values("cluster_id")
        f = bundle.profiles["fractions"].query("method == @method").sort_values("cluster_id")
        names = p.cluster_id.to_list()
        index = {c: i for i, c in enumerate(names)}
        codes = bundle.memberships[method].map(index).to_numpy()
        counts = np.bincount(codes, minlength=len(names))
        moments = []
        for view in [views["all_means"], (raw > 0).astype(float)]:
            sums = np.zeros((len(names), 47))
            np.add.at(sums, codes, view)
            moments.append(sums / counts[:, None])
        zmeans, fractions = moments
        if not np.allclose(zmeans, p[bundle.markers].to_numpy(), rtol=0, atol=1e-9):
            raise ValueError("Raw-source means do not reproduce frozen profiles")
        if not np.allclose(fractions, f[bundle.markers].to_numpy(), rtol=0, atol=1e-12):
            raise ValueError("Raw-source fractions do not reproduce frozen profiles")
        means_query = np.rint(p[bundle.markers].to_numpy() * 1000) / 1000
        fractions_query = np.rint(f[bundle.markers].to_numpy() * 1000) / 1000
        queries[method] = (names, codes, {"all_means": means_query,
                                         "all_means_fractions": np.column_stack([means_query, fractions_query])})
    out = _new_output(output)
    truth = ref.truth_label_code.to_numpy(dtype=int)
    metrics, selections, cluster_predictions, model_spec = [], [], [], {}
    for arm, x in views.items():
        classes, centroids = fit_centroids(x[train], truth[train])
        if len(classes) < 2:
            raise ValueError("Classifier training requires at least two reference classes")
        np.savez_compressed(out / f"{arm}_centroids.npz", classes=classes, centroids=centroids,
                            training_center=center, training_scale=scale)
        candidates = {}
        for c in C_GRID:
            model = LogisticRegression(C=c, solver="lbfgs", max_iter=2000, tol=1e-4, random_state=42)
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(x[train], truth[train])
            candidates[c] = model
        for method in METHODS:
            names, codes, q = queries[method]
            # C selection is method-specific, on the same one-label-per-cluster validation unit.
            scores = {}
            for c, model in candidates.items():
                cell_pred = model.predict(q[arm])[codes]
                regional = [float((cell_pred[mask] == truth[mask]).mean())
                            for region in sorted(ref.loc[ref.split.eq("calibration"), "File_ID"].unique())
                            for mask in [ref.File_ID.eq(region).to_numpy()]]
                scores[c] = float(np.mean(regional))
                selections.append({"method": method, "arm": arm, "C": c,
                                   "equal_calibration_region_agreement": scores[c]})
            best = min(C_GRID, key=lambda c: (-scores[c], c))
            logistic = candidates[best]
            model_spec[f"{method}/{arm}"] = {"C": best, "solver": "lbfgs", "max_iter": 2000,
                "training_cells": int(train.sum()), "training_regions": sorted(ref.loc[train, "File_ID"].unique()),
                "selection_population": "two calibration regions only", "query_unit": "one label per frozen cluster",
                "absent_training_classes": sorted(set(range(28)) - set(int(v) for v in logistic.classes_))}
            np.savez_compressed(out / f"{method}_{arm}_logistic.npz", classes=logistic.classes_,
                                coefficient=logistic.coef_, intercept=logistic.intercept_,
                                C=np.asarray(best), training_center=center, training_scale=scale)
            predictions = {"nearest_centroid": centroid_predict(classes, centroids, q[arm]),
                           "logistic_regression": logistic.predict(q[arm])}
            for classifier, pred in predictions.items():
                cluster_predictions.extend({"method": method, "arm": arm, "classifier": classifier,
                                            "cluster_id": name, "pred_label_code": int(label)}
                                           for name, label in zip(names, pred))
                cells = pred[codes]
                for region in sorted(ref.File_ID.unique()):
                    mask = ref.File_ID.eq(region).to_numpy()
                    metrics.append({"method": method, "arm": arm, "classifier": classifier,
                                    "region": region, "split": bundle.protocol["split"][region],
                                    **classifier_metrics(truth[mask], cells[mask])})
    pd.DataFrame(metrics).to_csv(out / "classifier_regional_metrics.csv", index=False)
    pd.DataFrame(metrics).query("split == 'test'").groupby(["method", "arm", "classifier"], sort=True)[
        ["reference_agreement", "macro_f1", "delivery_coverage"]].mean().reset_index().to_csv(
            out / "classifier_equal_test_region_metrics.csv", index=False)
    pd.DataFrame(selections).to_csv(out / "classifier_C_selection.csv", index=False)
    pd.DataFrame(cluster_predictions).to_csv(out / "classifier_cluster_predictions.csv", index=False)
    write_json(out / "classifier_models.json", model_spec)
    return _receipt(out, "classical_baselines", {**bundle.inputs, "authoritative_h5ad": h5ad_sha},
                    {"training_cells": int(train.sum()), "feature_dimensions": [47, 94],
                     "C_grid": list(C_GRID), "profiles_reproduced_from_authoritative_measurements": True,
                     "query_values": "exact decoded integer thousandths supplied to LLMs",
                     "reference_supervision": "Training-cell reference labels; richer supervision than supplied to LLMs.",
                     "donor_tuning": False, "test_tuning": False})


def predict_saved_baseline(directory, method, arm, classifier, query):
    """Apply frozen B004 weights to admitted donor query profiles; never fit."""
    directory, query = Path(directory), np.asarray(query, dtype=float)
    if query.ndim != 2 or not np.isfinite(query).all():
        raise ValueError("Frozen classifiers require finite query profiles")
    if classifier == "nearest_centroid":
        with np.load(directory / f"{arm}_centroids.npz", allow_pickle=False) as z:
            if query.shape[1] != z["centroids"].shape[1]:
                raise ValueError("Baseline query evidence dimension mismatch")
            return centroid_predict(z["classes"], z["centroids"], query)
    if classifier != "logistic_regression":
        raise ValueError("Unknown frozen classifier")
    with np.load(directory / f"{method}_{arm}_logistic.npz", allow_pickle=False) as z:
        coefficient, intercept, classes = z["coefficient"], z["intercept"], z["classes"]
        if query.shape[1] != coefficient.shape[1]:
            raise ValueError("Baseline query evidence dimension mismatch")
        logits = query @ coefficient.T + intercept
        return classes[(logits[:, 0] > 0).astype(int)] if len(classes) == 2 else classes[np.argmax(logits, axis=1)]
