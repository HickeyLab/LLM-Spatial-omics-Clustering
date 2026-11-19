"""Build blinded 75-query follow-up evidence. No credentials or HTTP calls."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import h5py
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import rankdata

from .common import canonical, digest, file_sha, new_output, read_json, write_json, verify_index, strict_json
from .native_astra import adapt_astra_request

METHOD_NAMES = {"leiden": "Leiden", "flowsom": "FlowSOM",
                "spatialsort": "SpatialSort", "pixie_tiff": "PIXIE"}
ARMS = ("selected_names", "selected_means", "all_means", "all_means_fractions")
FORBIDDEN = {"truth", "truth_label", "truth_label_code", "reference_labels",
             "reference_profiles", "File_ID", "ID", "cluster_id", "donor", "split"}
SELECTED_DEFINITION = (
    "Up to six markers per query, selected without reference labels by positive "
    "one-versus-rest tie-corrected Wilcoxon rank, then transformed mean and marker name. "
    "If no marker qualifies, the highest transformed-mean marker is supplied.")
NEIGHBOR_DEFINITION = ("Per target cell, average measured arcsinh(X/5) over up to 15 "
    "nearest other cells in the same region; break distance ties by cell ID. Average these vectors "
    "within the target cluster, standardize with the frozen B004 training center/SD, and divide "
    "the supplied integer thousandths by 1000. No neighboring labels are supplied.")


def assert_blinded(evidence, *, named=False):
    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in FORBIDDEN or (key == "clustering_method" and not named):
                    raise ValueError(f"Forbidden annotation field: {key}")
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
    walk(evidence)
    text = canonical(evidence).decode()
    if not named and any(name in text for name in METHOD_NAMES.values()):
        raise ValueError("Clustering-method identity leaked into blinded evidence")
    ids = evidence.get("query_case_ids")
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 75
            or any(type(i) is not int for i in ids) or ids != list(range(len(ids)))):
        raise ValueError("Anonymous IDs must be consecutive inside each original group")


def select_markers(transformed, labels, means, markers, maximum=6):
    """Tie-corrected one-versus-rest Wilcoxon; no reference-label argument."""
    x = np.asarray(transformed, dtype=np.float64)
    names, codes = np.unique(np.asarray(labels, dtype=str), return_inverse=True)
    if (x.ndim != 2 or x.shape[1] != len(markers) or len(labels) != len(x)
            or not len(x) or len(set(markers)) != len(markers) or maximum < 1):
        raise ValueError("Expression, markers and membership differ")
    if not np.isfinite(x).all() or np.asarray(means).shape != (len(names), len(markers)):
        raise ValueError("Invalid selection measurements")
    n = len(x)
    counts = np.bincount(codes, minlength=len(names))
    z = np.zeros((len(names), len(markers)))
    for j in range(x.shape[1]):
        ranks = rankdata(x[:, j], method="average")
        ties = np.unique(x[:, j], return_counts=True)[1].astype(np.float64)
        correction = 1 - np.sum(ties**3 - ties) / (n**3 - n) if n > 1 else 0.
        variance = counts * (n - counts) * (n + 1) * correction / 12
        sums = np.bincount(codes, weights=ranks, minlength=len(names))
        z[:, j] = np.divide(sums - counts * (n + 1) / 2, np.sqrt(variance),
                            out=np.zeros(len(names)), where=variance > 0)
    selections, fallbacks = [], []
    for row in range(len(names)):
        order = sorted(range(len(markers)), key=lambda j: (-z[row, j], -means[row, j], markers[j]))
        chosen = [j for j in order if z[row, j] > 0][:maximum]
        fallback = not chosen
        if fallback:
            chosen = [min(range(len(markers)), key=lambda j: (-means[row, j], markers[j]))]
        selections.append(chosen)
        fallbacks.append(fallback)
    return names, selections, fallbacks, z


def neighborhood_profiles(transformed, keys, coords, labels, center, scale, k=15):
    """Within-region measured neighbors, with deterministic distance/ID ties."""
    x, xy = np.asarray(transformed), np.asarray(coords, dtype=np.float64)
    center, scale = np.asarray(center), np.asarray(scale)
    if (x.ndim != 2 or not np.isfinite(x).all() or len(labels) != len(x)
            or center.shape != (x.shape[1],) or scale.shape != center.shape
            or not np.isfinite(center).all() or not np.isfinite(scale).all()
            or np.any(scale <= 0) or k < 1):
        raise ValueError("Invalid neighborhood expression, labels or scaler")
    keys = keys.reset_index(drop=True)
    if xy.shape != (len(x), 2) or not np.isfinite(xy).all():
        raise ValueError("Missing/nonfinite spatial coordinates")
    if len(keys) != len(x) or keys.duplicated(["File_ID", "ID"]).any():
        raise ValueError("Invalid neighborhood cell joins")
    neighbor_mean = np.empty_like(x, dtype=np.float64)
    ids = keys.ID.astype(np.int64).to_numpy()
    for _, indices in keys.groupby("File_ID", sort=True).groups.items():
        rows = np.asarray(indices, dtype=np.int64)
        if len(rows) < 2:
            raise ValueError("A neighborhood needs at least two cells per region")
        points = xy[rows]
        tree = cKDTree(points)
        take = min(k, len(rows) - 1)
        distances, initial = tree.query(points, k=take + 1, workers=1)
        for i, row in enumerate(rows):
            candidates = np.asarray(initial[i]).reshape(-1)
            ds = np.asarray(distances[i]).reshape(-1)
            ds = ds[candidates != i]
            radius = np.partition(ds, take - 1)[take - 1]
            local = np.asarray(tree.query_ball_point(points[i], np.nextafter(radius, np.inf)))
            local = local[local != i]
            d2 = np.sum((points[local] - points[i])**2, axis=1)
            order = np.lexsort((ids[rows[local]], d2))
            chosen = rows[local[order[:take]]]
            if len(chosen) != take:
                raise ValueError("Neighborhood boundary/tie construction failed")
            neighbor_mean[row] = x[chosen].mean(axis=0)
    names, codes = np.unique(np.asarray(labels, dtype=str), return_inverse=True)
    means = np.asarray([neighbor_mean[codes == i].mean(axis=0) for i in range(len(names))])
    z = (means - center) / scale
    return names, np.rint(z * 1000).astype(np.int64)


def compact_evidence(base, selections, markers, *, numerical):
    out = deepcopy(base)
    means = out.pop("mean_asinh_expression_z_thousandths")
    out.pop("fraction_above_processed_zero", None)
    if len(means) != len(selections):
        raise ValueError("Selection rows differ from original query rows")
    out["selected_marker_names"] = [[markers[j] for j in selected] for selected in selections]
    out["selected_marker_definition"] = SELECTED_DEFINITION
    if numerical:
        out["selected_mean_asinh_expression_z_thousandths"] = [
            [row[j] for j in selected] for row, selected in zip(means, selections, strict=True)]
    assert_blinded(out)
    return out


def _body_from_evidence(source, evidence, family, config):
    out = deepcopy(source)
    # Unchanged arms retain the exact model-visible string, including encoding.
    if strict_json(out["messages"][1]["content"]) != evidence:
        out["messages"][1]["content"] = canonical(evidence).decode()
    out["reasoning"] = {"effort": "high"}
    out["max_tokens"] = config["models"][family]["max_completion_tokens"]
    out.pop("provider", None)
    if config["models"][family]["seed"] is None:
        out.pop("seed", None)
    else:
        out["seed"] = config["models"][family]["seed"]
    return out


def prepare_b004(repo, source_bundle, h5ad, output, config_path):
    from llm_spatial_omics_clustering.revision import annotation47_prepare as frozen
    repo, source_bundle = Path(repo), Path(source_bundle)
    config = read_json(config_path)
    bundle = repo / config["b004_bundle"]
    if config["clusters_per_request"] != 75 or config["repetitions"] != 1:
        raise ValueError("Do not change original query grouping/repetition")
    if any(v["effort"] != "high" for v in config["models"].values()):
        raise ValueError("All models must retain high reasoning")
    protocol = read_json(bundle / "protocol.json")
    source_manifest = read_json(source_bundle / "manifest.json")
    if source_manifest["source_h5ad_sha256"] != frozen.H5AD_SHA256:
        raise ValueError("Unfrozen source bundle")
    verify_index(source_bundle, source_manifest["files"])
    result_manifest = read_json(bundle / "manifest.json")
    verify_index(bundle, result_manifest["files"], ["protocol.json", "accepted_requests.json"])
    raw, keys, memberships, source_receipt = frozen.load_inputs(protocol, repo, Path(h5ad))
    scaler, profiles = frozen.compute_profiles(raw, keys.split.eq("train").to_numpy(), memberships)
    transformed = np.arcsinh(raw / 5)
    selections, selection_rows = {}, []
    for method, profile in profiles.items():
        names, chosen, fallback, z = select_markers(transformed, memberships[method],
                                                   profile["means_asinh"], frozen.MARKERS)
        if not np.array_equal(names, profile["cluster_names"]):
            raise ValueError("Selection cluster order differs")
        selections[method] = chosen
        for i, cluster in enumerate(names):
            selection_rows.append({"method": method, "cluster_id": str(cluster),
                "marker_indices": chosen[i], "marker_names": [frozen.MARKERS[j] for j in chosen[i]],
                "fallback": fallback[i], "selected_z": [float(z[i, j]) for j in chosen[i]]})
    with h5py.File(h5ad, "r") as handle:
        coords = np.column_stack([handle["obs/x"][:], handle["obs/y"][:]])
    neighbor_names, neighbor_values = neighborhood_profiles(
        transformed, keys.reset_index(drop=True), coords, memberships["leiden"],
        scaler["center"], scaler["scale"])
    if not np.array_equal(neighbor_names, profiles["leiden"]["cluster_names"]):
        raise ValueError("Neighborhood cluster order differs")
    accepted_rows = read_json(bundle / "accepted_requests.json")["records"]
    accepted = {r["request_id"]: r for r in accepted_rows}
    if len(accepted) != len(accepted_rows):
        raise ValueError("Duplicate accepted request IDs")
    original = [strict_json(line) for line in (source_bundle / "requests.jsonl").read_text().splitlines()]
    templates = {(r["model_family"], r["method"], r["arm"], r["batch"]): r for r in original}
    if len(templates) != 128 or len(original) != 128:
        raise ValueError("Incomplete or duplicate source Cartesian coverage")
    for sr in original:
        old = accepted.get(sr["request_id"])
        if old is None or any(old.get(k) != sr.get(k) for k in
                              ("body_sha256", "method", "arm", "batch", "model_family", "expected_n")):
            raise ValueError("Accepted result does not match its frozen request")
        if old["canonical_slug_expected"] != config["models"][sr["model_family"]]["source_canonical_model"]:
            raise ValueError("Accepted model binding differs from the follow-up contract")
        if old["accepted_wire_max_tokens"] != config["models"][sr["model_family"]]["max_completion_tokens"]:
            raise ValueError("Accepted output ceiling differs from the follow-up contract")
    out = new_output(output)
    records, bodies, sources = [], {}, {}

    def add(family, method, arm, group, source_record, source, evidence, reuse=None):
        assert_blinded(evidence, named=arm == "method_named")
        body = _body_from_evidence(source, evidence, family, config)
        n = len(evidence["query_case_ids"])
        start = group * 75
        names = profiles[method]["cluster_names"][start:start + n].tolist()
        condition = {"cohort": "B004", "family": family, "method": method,
                     "arm": arm, "repeat": 0, "batch": group, "cluster_ids": names}
        rid = "r47_" + digest({"condition": condition, "body": body})
        if rid in bodies:
            raise ValueError("Duplicate request ID")
        body_path = "logical_bodies/" + rid + ".json"
        record = {**condition, "request_id": rid, "expected_n": n,
                  "model_id": body["model"], "effort": "high", "transport": config["models"][family]["transport"],
                  "body_path": body_path, "body_sha256": digest(body),
                  "evidence_sha256": digest(evidence), "model_visible_messages_sha256": digest(body["messages"]),
                  "source_request_id": source_record["request_id"], "reuse": reuse,
                  "submission_allowed": False}
        records.append(record)
        bodies[rid] = body
        write_json(out / body_path, body)
        if family == "openai":
            native = adapt_astra_request(body, native_model=config["models"][family]["native_model_candidate"])
            write_json(out / "native_astra" / (rid + ".json"), native)
            record["native_body_sha256"] = digest(native)
    for family in config["models"]:
        for method in config["methods"]:
            profile = profiles[method]
            for group, start in enumerate(range(0, len(profile["cluster_names"]), 75)):
                stop = min(start + 75, len(profile["cluster_names"]))
                r = templates[family, method, "all_means", group]
                p = source_bundle / r["body_path"]
                if file_sha(p) != r["body_sha256"]:
                    raise ValueError("Original body hash changed")
                source = read_json(p)
                base = strict_json(source["messages"][1]["content"])
                expected = profile["means_z_thousandths"][start:stop].tolist()
                if base["mean_asinh_expression_z_thousandths"] != expected:
                    raise ValueError("Recomputed paired means differ from original literal values")
                for arm in ARMS:
                    sr = templates[family, method, "all_means_fractions" if arm == "all_means_fractions" else "all_means", group]
                    sp = source_bundle / sr["body_path"]
                    if file_sha(sp) != sr["body_sha256"]:
                        raise ValueError("Original paired body hash changed")
                    sb = read_json(sp)
                    evidence = strict_json(sb["messages"][1]["content"])
                    reuse = None
                    if arm.startswith("selected_"):
                        evidence = compact_evidence(base, selections[method][start:stop], frozen.MARKERS,
                                                    numerical=arm == "selected_means")
                    else:
                        old = accepted[sr["request_id"]]
                        possible = family != "deepseek" or old.get("provider") == "Morph"
                        reuse = {"candidate": possible, "admitted": False,
                            "source_request_id": old["request_id"], "source_response_sha256": old["source_sha256"],
                            "source_provider": old.get("provider"), "source_quantization": old.get("quantization"),
                            "labels": old["labels"] if possible else None,
                            "reason": "exact condition; native binding/route and full wire contract still require admission" if possible else "different inference variant"}
                        sources[sr["request_id"]] = {"body_sha256": sr["body_sha256"],
                            "source_response_sha256": old["source_sha256"]}
                        if arm == "all_means_fractions" and evidence["fraction_above_processed_zero"] != profile["fractions_thousandths"][start:stop].tolist():
                            raise ValueError("Paired fractions changed")
                    add(family, method, arm, group, sr, sb, evidence, reuse)
    for method in config["methods"]:
        for group in range((len(profiles[method]["cluster_names"]) + 74) // 75):
            sr = templates["anthropic", method, "all_means_fractions", group]
            sb = read_json(source_bundle / sr["body_path"])
            evidence = strict_json(sb["messages"][1]["content"])
            evidence["clustering_method"] = METHOD_NAMES[method]
            add("anthropic", method, "method_named", group, sr, sb, evidence)
    for group, start in enumerate(range(0, len(neighbor_names), 75)):
        sr = templates["anthropic", "leiden", "all_means_fractions", group]
        sb = read_json(source_bundle / sr["body_path"])
        evidence = strict_json(sb["messages"][1]["content"])
        evidence["neighborhood_mean_asinh_expression_z_thousandths"] = neighbor_values[start:start + 75].tolist()
        evidence["neighborhood_definition"] = NEIGHBOR_DEFINITION
        add("anthropic", "leiden", "neighborhood", group, sr, sb, evidence)
    if len(records) != 276 or len({r["request_id"] for r in records}) != 276:
        raise ValueError("Incomplete B004 Cartesian/control coverage")
    write_json(out / "requests.json", records)
    write_json(out / "marker_selection.json", selection_rows)
    write_json(out / "source_receipt.json", source_receipt)
    np.savez_compressed(out / "training_scaler.npz", **scaler)
    for family in config["models"]:
        planned = [r for r in records if r["family"] == family]
        if family == "openai":
            lines = [{"custom_id": r["request_id"], "method": "POST", "url": "/v1/chat/completions",
                      "body": adapt_astra_request(bodies[r["request_id"]],
                              native_model=config["models"][family]["native_model_candidate"])} for r in planned]
            (out / "native_astra_all_conditions.DRAFT.jsonl").write_bytes(b"".join(canonical(x) + b"\n" for x in lines))
        else:
            write_json(out / (family + "_logical_requests.DRAFT.json"),
                {"execution_enabled": False, "route_admitted": False,
                 "requests": [{"custom_id": r["request_id"], "body": bodies[r["request_id"]]} for r in planned]})
    files = {str(p.relative_to(out)): file_sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    candidates = sum(bool(r["reuse"] and r["reuse"]["candidate"]) for r in records)
    summary = {"schema": "reviewer47.b004.prepared.v1", "protocol_id": config["protocol_id"],
        "protocol_sha256": file_sha(config_path), "request_items": len(records),
        "cluster_counts": {m: len(p["cluster_names"]) for m, p in profiles.items()},
        "markers": frozen.MARKERS, "ontology": protocol["ontology"],
        "source_bundle_manifest_sha256": file_sha(source_bundle / "manifest.json"),
        "accepted_result_manifest_sha256": file_sha(bundle / "manifest.json"),
        "logical_annotation_sets": 69, "primary_representation_sets": 64,
        "reuse_candidates": candidates, "new_initial_items_if_all_candidates_admitted": len(records) - candidates,
        "native_astra_requires_model_credit_and_launch_admission": True,
        "reference_labels_read_for_inputs": False, "scientific_condition_repetitions": 1,
        "paid_calls": 0, "launch_ready": False, "bodies": "DRAFT: exact admission and reuse reconciliation required",
        "source_proofs": sources, "files": files}
    write_json(out / "manifest.json", summary)
    return summary
