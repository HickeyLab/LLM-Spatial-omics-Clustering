#!/usr/bin/env python3
"""Verify and replay the frozen B004 reviewer publication export, entirely offline.

There is no credential, network, scheduler, submission, repair or generation path.
The pending DeepSeek condition remains in the planned inventory with null scores.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from llm_spatial_omics_clustering.revision.annotation47_results import parse_labels

FAMILIES = ("openai", "anthropic", "google", "deepseek")
METHODS = ("leiden", "flowsom", "spatialsort", "pixie_tiff")
ARMS = ("selected_names", "selected_means", "all_means", "all_means_fractions")
PENDING_ID = "r47_94568343fcddc146209aad2e4095fe5e52446a51a1161a0a27d1c81175be0cb1"


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"Non-finite JSON number: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def read_json(path):
    return strict_json(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_manifest(directory):
    directory = Path(directory).resolve()
    manifest = read_json(directory / "manifest.json")
    for relative, spec in manifest["files"].items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise ValueError(f"Missing or escaping manifest path: {relative}")
        expected = spec["sha256"] if isinstance(spec, dict) else spec
        if sha(path) != expected:
            raise ValueError(f"Frozen artifact hash differs: {relative}")
    verification_path = directory / "verification.json"
    if verification_path.exists():
        for relative, spec in read_json(verification_path).get("outputs", {}).items():
            path = (directory / relative).resolve()
            if not path.is_relative_to(directory) or sha(path) != spec["sha256"]:
                raise ValueError(f"Scoring verification output hash differs: {relative}")
    return sha(directory / "manifest.json"), len(manifest["files"])


def read_csv(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def write_csv(path, rows):
    with Path(path).open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def validate_outcome(record):
    n = record["expected_n"]
    if type(n) is not int or not 1 <= n <= 75:
        raise ValueError("Invalid planned request size")
    labels = record["labels"]
    if not isinstance(labels, list) or len(labels) != n:
        raise ValueError("Changed planned prediction denominator")
    if record["status"] == "accepted":
        if any(type(value) is not int or not 0 <= value < 28 for value in labels):
            raise ValueError("Accepted codes must be integers in the fixed 28-label vocabulary")
    elif record["status"] == "pending":
        if record["request_id"] != PENDING_ID or any(value is not None for value in labels):
            raise ValueError("Pending predictions must remain missing, never Noise or zero")
    else:
        raise ValueError("Unadmitted output status")


def condition_map(records):
    result = {}
    batches = set()
    for record in records:
        validate_outcome(record)
        if record["batch"] in batches:
            raise ValueError("Duplicate condition batch")
        batches.add(record["batch"])
        clusters = record["cluster_ids"]
        if len(clusters) != record["expected_n"]:
            raise ValueError("Changed query-cluster join")
        for cluster, label in zip(clusters, record["labels"], strict=True):
            if cluster in result:
                raise ValueError("Duplicate cluster within an annotation set")
            result[cluster] = label
    if batches != {0, 1, 2, 3}:
        raise ValueError("Incomplete planned request coverage")
    return result


def region_metrics(truth, prediction, regions, test_regions):
    """Counter-based recomputation, independent of the publication metric helper."""
    if len(truth) != len(prediction) or len(truth) != len(regions):
        raise ValueError("Cell array lengths differ")
    if len(test_regions) != 2 or len(set(test_regions)) != 2:
        raise ValueError("Exactly two fixed test regions are required")
    output = []
    for region in test_regions:
        pairs = Counter((a, b) for a, b, r in zip(truth, prediction, regions, strict=True)
                        if r == region)
        count = sum(pairs.values())
        if not count:
            raise ValueError("A planned test region is missing")
        correct = sum(n for (a, b), n in pairs.items() if a == b)
        f1 = []
        for label in range(28):
            tp = pairs[label, label]
            fn = sum(n for (a, b), n in pairs.items() if a == label and b != label)
            fp = sum(n for (a, b), n in pairs.items() if b == label and a != label)
            denominator = 2 * tp + fn + fp
            f1.append(2 * tp / denominator if denominator else 0.0)
        output.append({"region": region, "planned_cells": count,
                       "correct_cells": correct, "agreement": correct / count,
                       "fixed28_macro_f1": sum(f1) / 28})
    return output


def compare_rows(actual, expected_path, keys, columns):
    expected = {tuple(row[key] for key in keys): row for row in read_csv(expected_path)}
    observed = {tuple(str(row[key]) for key in keys): row for row in actual}
    if set(expected) != set(observed):
        raise ValueError(f"Condition coverage differs: {expected_path.name}")
    maximum = 0.0
    for key, row in observed.items():
        saved = expected[key]
        for column in columns:
            value = row[column]
            if value is None:
                if saved[column] not in ("", "null", "None"):
                    raise ValueError(f"An incomplete score was finalized: {key}/{column}")
            elif isinstance(value, (float, int)):
                difference = abs(float(value) - float(saved[column]))
                maximum = max(maximum, difference)
                if difference > 1e-12:
                    raise ValueError(f"Scored value differs: {key}/{column}")
            elif str(value) != saved[column]:
                raise ValueError(f"Scored status differs: {key}/{column}")
    return maximum


def replay(reviewer, primary, response_evidence, output, recompute_calibration=False):
    reviewer, primary, response_evidence, output = map(Path, (reviewer, primary, response_evidence, output))
    if output.exists():
        raise FileExistsError("Preserve previous replay evidence; choose a new output directory")
    manifest_proofs = {name: verify_manifest(path) for name, path in
                       [("reviewer", reviewer), ("primary", primary), ("responses", response_evidence)]}
    freeze_path = reviewer / "prediction_freeze.json"
    freeze = read_json(freeze_path)
    if sha(freeze_path) != read_json(reviewer / "prediction_freeze.seal.json")["sha256"]:
        raise ValueError("Prediction freeze seal differs")
    records = freeze["records"]
    if len(records) != 276 or len({row["request_id"] for row in records}) != 276:
        raise ValueError("Duplicate or missing planned request IDs")
    accepted = [row for row in records if row["status"] == "accepted"]
    pending = [row for row in records if row["status"] == "pending"]
    if len(accepted) != 275 or len(pending) != 1 or pending[0]["request_id"] != PENDING_ID:
        raise ValueError("Frozen accepted/pending inventory differs")
    receipts = {}
    for filename in ("reused_response_receipts.json", "new_response_receipts.json"):
        for row in read_json(response_evidence / filename)["records"]:
            if row["request_id"] in receipts:
                raise ValueError("Duplicate visible response ID")
            receipts[row["request_id"]] = row
    if set(receipts) != {row["request_id"] for row in accepted}:
        raise ValueError("Visible response evidence does not cover exactly the accepted requests")
    observed_generations = set()
    for record in records:
        validate_outcome(record)
        body = read_json(reviewer / "request_bodies" / (record["request_id"] + ".json"))
        if canonical_sha(body) != record["body_sha256"]:
            raise ValueError("Literal sealed logical request changed")
        if canonical_sha(body["messages"]) != record["model_visible_messages_sha256"]:
            raise ValueError("Scientific task/evidence messages changed")
        effort = body.get("reasoning", {}).get("effort", body.get("reasoning_effort"))
        if effort != "high":
            raise ValueError("The primary study must retain high reasoning")
        if record["status"] == "pending":
            continue
        evidence = receipts[record["request_id"]]
        if parse_labels(evidence["visible_content"], record["expected_n"]) != record["labels"]:
            raise ValueError("Saved visible response and frozen labels differ")
        response_rows = evidence["response_receipts"]
        if not response_rows or response_rows[-1]["finish_reason"] != "stop":
            raise ValueError("No normal-stop final response")
        if any(row.get("refusal") for row in response_rows):
            raise ValueError("A refused response cannot be admitted")
        generation = evidence["source_generation_id"]
        if generation != record["generation_id"] or generation != response_rows[-1]["id"]:
            raise ValueError("Physical generation identity differs")
        if generation in observed_generations:
            raise ValueError("Duplicate physical final generation")
        observed_generations.add(generation)
    output.mkdir(parents=True)
    write_json(output / "response_validation.json", {
        "accepted_requests_reparsed": 275, "pending_requests": 1,
        "literal_request_hashes_verified": 276, "unique_final_generations": 275,
        "prediction_freeze_sha256": sha(freeze_path), "reference_values_read_by_replayer": False,
        "input_manifest_sha256_and_file_counts": manifest_proofs,
    })
    # Only now load the fixed reference values, after strict output/identity validation.
    protocol = read_json(primary / "protocol.json")
    if len(protocol["markers"]) != 47 or len(set(protocol["markers"])) != 47:
        raise ValueError("Missing or reordered marker definition")
    if len(protocol["ontology"]) != 28 or protocol["ontology"][21] != "Noise":
        raise ValueError("The original 28-label vocabulary including Noise is required")
    cells = read_csv(primary / "reference_cells.csv.gz")
    memberships = read_csv(primary / "memberships.csv.gz")
    keys = [(row["File_ID"], row["ID"]) for row in cells]
    if len(keys) != 220082 or len(set(keys)) != 220082:
        raise ValueError("Incorrect or duplicated cell-key population")
    if keys != [(row["File_ID"], row["ID"]) for row in memberships]:
        raise ValueError("Cell join/order differs")
    if any(a[method] != b[method] for a, b in zip(cells, memberships, strict=True)
           for method in METHODS):
        raise ValueError("Frozen clustering membership differs")
    if any(row["split"] != protocol["split"][row["File_ID"]] for row in cells):
        raise ValueError("Frozen train/calibration/test split differs")
    test_regions = sorted(region for region, split in protocol["split"].items() if split == "test")
    test_cells = [row for row in cells if row["File_ID"] in test_regions]
    if len(test_cells) != 69576:
        raise ValueError("Test population differs")
    truth = [int(row["truth_label_code"]) for row in cells]
    if any(not 0 <= label < 28 for label in truth):
        raise ValueError("Invalid reference label")
    regions = [row["File_ID"] for row in cells]
    grouped = defaultdict(list)
    for row in records:
        grouped[row["family"], row["method"], row["arm"]].append(row)
    if len(grouped) != 69:
        raise ValueError("Planned scientific condition coverage differs")
    maps, metric_rows, per_region_rows = {}, [], []
    for key, request_rows in grouped.items():
        family, method, arm = key
        mapping = condition_map(request_rows)
        if set(mapping) != {row[method] for row in memberships}:
            raise ValueError("Incorrect condition-to-cluster join")
        maps[key] = mapping
        complete = all(row["status"] == "accepted" for row in request_rows)
        delivered_test = sum(mapping[row[method]] is not None for row in test_cells)
        delivered_clusters = sum(value is not None for value in mapping.values())
        metric = {"family": family, "method": method, "arm": arm,
                  "status": "complete" if complete else "pending",
                  "planned_requests": 4, "accepted_requests": sum(row["status"] == "accepted" for row in request_rows),
                  "planned_clusters": len(mapping), "delivered_clusters": delivered_clusters,
                  "cluster_delivery_coverage": delivered_clusters / len(mapping),
                  "planned_test_cells": 69576, "delivered_test_cells": delivered_test,
                  "cell_delivery_coverage": delivered_test / 69576,
                  "agreement": None, "fixed28_macro_f1": None}
        if complete:
            scores = region_metrics(truth, [mapping[row[method]] for row in cells], regions, test_regions)
            metric["agreement"] = sum(row["agreement"] for row in scores) / 2
            metric["fixed28_macro_f1"] = sum(row["fixed28_macro_f1"] for row in scores) / 2
            per_region_rows.extend({"family": family, "method": method, "arm": arm, **row} for row in scores)
        elif key != ("deepseek", "leiden", "selected_means"):
            raise ValueError("Unexpected incomplete condition")
        metric_rows.append(metric)
    numeric = ["status", "planned_requests", "accepted_requests", "planned_clusters", "delivered_clusters",
               "cluster_delivery_coverage", "planned_test_cells", "delivered_test_cells", "cell_delivery_coverage",
               "agreement", "fixed28_macro_f1"]
    differences = [compare_rows(metric_rows, reviewer / "set_metrics.csv", ["family", "method", "arm"], numeric)]
    index = {(row["family"], row["method"], row["arm"]): row for row in metric_rows}
    controls = []
    for key in grouped:
        family, method, arm = key
        if arm not in ("method_named", "neighborhood"):
            continue
        baseline, control = index[family, method, "all_means_fractions"], index[key]
        left, right = maps[family, method, "all_means_fractions"], maps[key]
        controls.append({"family": family, "method": method, "control_arm": arm, "status": "complete",
                         "baseline_agreement": baseline["agreement"], "control_agreement": control["agreement"],
                         "agreement_difference": control["agreement"] - baseline["agreement"],
                         "baseline_macro_f1": baseline["fixed28_macro_f1"], "control_macro_f1": control["fixed28_macro_f1"],
                         "macro_f1_difference": control["fixed28_macro_f1"] - baseline["fixed28_macro_f1"],
                         "planned_clusters": len(left), "cluster_label_changes": sum(left[c] != right[c] for c in left),
                         "planned_test_cells": 69576,
                         "test_cell_label_changes": sum(left[row[method]] != right[row[method]] for row in test_cells)})
    columns = [key for key in controls[0] if key not in ("family", "method", "control_arm")]
    differences.append(compare_rows(controls, reviewer / "control_contrasts.csv", ["family", "method", "control_arm"], columns))
    # The updated primary bank must use exactly these full-arm outcomes.
    primary_rows = {(row["model_family"], row["method"], row["arm"]): row for row in
                    read_csv(primary / "metrics.csv") if row["scope"] == "equal_test_regions" and row["population"] == "all_labels"}
    if len(primary_rows) != 32:
        raise ValueError("Primary benchmark condition coverage differs")
    for key, saved in primary_rows.items():
        for column in ("agreement", "fixed28_macro_f1"):
            if abs(index[key][column] - float(saved[column])) > 1e-12:
                raise ValueError("Reviewer/primary full-arm bank differs")
    write_csv(output / "set_metrics.csv", metric_rows)
    write_csv(output / "completed_region_metrics.csv", per_region_rows)
    write_csv(output / "control_contrasts.csv", controls)
    calibration_recomputed = False
    if recompute_calibration:
        from scripts.revision.reviewer47.offline import run_agreement_calibration
        run_agreement_calibration(primary, output / "calibration")
        for name in ("calibration_cluster_split.csv", "calibration_equal_test_region_metrics.csv",
                     "calibration_metrics.csv", "calibration_risk_coverage.csv", "calibration_reliability.csv"):
            if sha(output / "calibration" / name) != sha(reviewer / "calibration" / name):
                raise ValueError(f"Recalibration replay differs: {name}")
        calibration_recomputed = True
    report = {"passed": True, "accepted_request_items": 275, "pending_request_items": 1,
              "complete_annotation_sets": 68, "pending_annotation_sets": 1,
              "incomplete_condition_scores_null": True, "overall_four_arm_aggregate": None,
              "unique_cell_keys": 220082, "test_cells": 69576, "test_regions": test_regions,
              "fixed_vocabulary_size": 28, "noise_code": 21, "replications": 1,
              "primary_complete_sets_verified": 32, "maximum_score_difference": max(differences),
              "calibration_recomputed_and_hash_equal": calibration_recomputed,
              "annotation_calls": 0, "scheduler_actions": 0}
    write_json(output / "verification.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer", type=Path, default=ROOT / "data/frozen/reviewer47_results_20261111")
    parser.add_argument("--primary", type=Path, default=ROOT / "data/frozen/annotation47_results_20261111")
    parser.add_argument("--response-evidence", type=Path, default=ROOT / "data/frozen/reviewer47_response_evidence_20261111")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recompute-calibration", action="store_true")
    args = parser.parse_args()
    print(json.dumps(replay(args.reviewer, args.primary, args.response_evidence, args.output,
                            args.recompute_calibration), indent=2))


if __name__ == "__main__":
    main()
