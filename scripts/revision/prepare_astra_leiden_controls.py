#!/usr/bin/env python3
"""Prepare/check the disabled eight-item B004 Astra control extension, offline.

No credential lookup, networking, job submission or automatic activation exists
in this module. Existing blinded answers and Opus control evidence are frozen as
provenance; none is submitted as a new blinded-baseline generation.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
from pathlib import Path

ARMS = ("method_named", "neighborhood")
MARKERS = ["CD45RO", "CD56", "CD15", "CD163", "MUC2", "CD34", "CD36", "aDefensin5", "CD49a", "HLA-DR", "CD38", "CollagenIV", "CD4", "CD138", "CD44", "Vimentin", "CD66", "Podoplanin", "CHGA", "CD3", "SOX9", "CD161", "Synaptophysin", "CD57", "ITLN1", "CD127", "CD45", "CD49f", "aSMA", "Cytokeratin", "CD8", "CD19", "BCL2", "CD90", "CD21", "CD7", "CD11c", "Ki67", "CD68", "MUC1", "CD206", "CD16", "CD117", "CD69", "CD31", "CD123", "CDX2"]
LABELS = ["B", "CD36 high Endothelial", "CD36 low Endothelial", "CD4+ T", "CD49a+ Smooth muscle", "CD57+ Epithelial", "CD66+ Epithelial", "CD8+ T", "Cycling TA", "DC", "Epithelial", "Goblet", "ICC", "ITLN+ Epithelial", "M1 Macrophage", "M2 Macrophage", "MUC1+ Epithelial", "NK", "Nerve", "Neuroendocrine", "Neutrophil", "Noise", "PDPN+ Stromal", "Paneth", "Plasma", "Smooth muscle", "Stromal", "TA"]
BASE_FIELDS = {"expression_definition", "fraction_above_processed_zero", "fraction_definition", "label_dictionary", "marker_order", "mean_asinh_expression_z_thousandths", "query_case_ids", "response_contract", "task"}
EXTRA_FIELDS = {"method_named": {"clustering_method"}, "neighborhood": {"neighborhood_mean_asinh_expression_z_thousandths", "neighborhood_definition"}}
NATIVE_FIELDS = {"model", "messages", "max_completion_tokens", "reasoning_effort", "response_format", "seed"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(text):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("Duplicate JSON key")
            out[key] = value
        return out
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def read(path):
    return strict_json(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")


def validate_matrix(value, *, fraction=False):
    if not isinstance(value, list) or len(value) != 75:
        raise ValueError("Exactly 75 evidence rows are required")
    for row in value:
        if not isinstance(row, list) or len(row) != 47 or any(type(v) is not int for v in row):
            raise ValueError("Evidence must have 47 integer values per query")
        if fraction and any(v < 0 or v > 1000 for v in row):
            raise ValueError("Fractions must lie in integer thousandths 0..1000")


def validate_base(evidence):
    if set(evidence) != BASE_FIELDS or evidence["marker_order"] != MARKERS:
        raise ValueError("Missing/reordered markers or unexpected baseline fields")
    if evidence["label_dictionary"] != {str(i): label for i, label in enumerate(LABELS)}:
        raise ValueError("Original fixed 28-label vocabulary including Noise is required")
    if evidence["query_case_ids"] != list(range(75)) or any(type(i) is not int for i in evidence["query_case_ids"]):
        raise ValueError("Anonymous query IDs must remain 0..74")
    validate_matrix(evidence["mean_asinh_expression_z_thousandths"])
    validate_matrix(evidence["fraction_above_processed_zero"], fraction=True)


def native_body(base_body, control_body, arm):
    if arm not in ARMS:
        raise ValueError("Only the two B004 Leiden controls are admitted")
    if base_body["model"] != "openai/gpt-6-astra" or base_body["reasoning"] != {"effort": "high"} or base_body["max_tokens"] != 32768 or base_body["seed"] != 42:
        raise ValueError("Frozen Astra settings changed")
    if control_body["model"] != "anthropic/claude-opus-5.5":
        raise ValueError("Expected the preserved Opus control template")
    base = strict_json(base_body["messages"][1]["content"])
    evidence = strict_json(control_body["messages"][1]["content"])
    validate_base(base)
    if set(evidence) != BASE_FIELDS | EXTRA_FIELDS[arm]:
        raise ValueError("Reference/method metadata leakage or missing control fields")
    if {k: v for k, v in evidence.items() if k not in EXTRA_FIELDS[arm]} != base:
        raise ValueError("Paired means, fractions, vocabulary or instructions changed")
    if arm == "method_named" and evidence["clustering_method"] != "Leiden":
        raise ValueError("Incorrect named method")
    if arm == "neighborhood":
        validate_matrix(evidence["neighborhood_mean_asinh_expression_z_thousandths"])
        if not isinstance(evidence["neighborhood_definition"], str) or not evidence["neighborhood_definition"]:
            raise ValueError("Missing frozen measured-neighborhood definition")
    if base_body["messages"][0] != control_body["messages"][0] or base_body["response_format"] != {"type": "json_object"}:
        raise ValueError("Task instructions or response format changed")
    return {"model": "gpt-6-astra", "messages": deepcopy(control_body["messages"]), "max_completion_tokens": 32768, "reasoning_effort": "high", "seed": 42, "response_format": {"type": "json_object"}}


def accept_response(text, *, finish_reason="stop", refusal=None):
    if finish_reason != "stop" or refusal:
        raise ValueError("Refused or truncated output remains missing")
    value = strict_json(text)
    if not isinstance(value, dict) or set(value) != {"a"} or not isinstance(value["a"], list) or len(value["a"]) != 75:
        raise ValueError("Exactly one response object per planned query is required")
    labels = {}
    for item in value["a"]:
        if not isinstance(item, dict) or set(item) != {"i", "l"} or type(item["i"]) is not int or type(item["l"]) is not int:
            raise ValueError("Response IDs and label codes must be integers without extra fields")
        if item["i"] not in range(75) or item["i"] in labels or item["l"] not in range(28):
            raise ValueError("Invalid/duplicate query ID or label code")
        labels[item["i"]] = item["l"]
    return [labels[i] for i in range(75)]


def check(bundle):
    bundle = Path(bundle)
    manifest = read(bundle / "manifest.json")
    for name, expected in manifest["files"].items():
        if sha(bundle / name) != expected:
            raise ValueError("Frozen file changed: " + name)
    protocol = read(bundle / "protocol.json")
    if protocol["execution"] != {"inference_enabled": False, "automatic_launch": False, "separate_launch_instruction_required": True, "spending_cap_usd": None, "paid_calls": 0, "jobs_submitted": 0}:
        raise ValueError("The prepared extension must remain disabled")
    records = read(bundle / "requests.json")
    lines = [strict_json(line) for line in (bundle / "requests.DRAFT.jsonl").read_text().splitlines()]
    if len(records) != 8 or len(lines) != 8 or {(r["arm"], r["batch"]) for r in records} != {(a, g) for a in ARMS for g in range(4)}:
        raise ValueError("Incomplete or duplicate eight-item Cartesian coverage")
    if len({r["request_id"] for r in records}) != 8:
        raise ValueError("Duplicate request ID")
    joins = {}
    for record, wire in zip(records, lines, strict=True):
        base = read(bundle / record["baseline_template_path"])
        control = read(bundle / record["control_template_path"])
        expected_body = native_body(base, control, record["arm"])
        if set(wire) != {"custom_id", "method", "url", "body"} or wire != {"custom_id": record["request_id"], "method": "POST", "url": "/v1/chat/completions", "body": expected_body}:
            raise ValueError("Native wire body or request join differs")
        condition = {key: record[key] for key in ("cohort", "family", "method", "arm", "repeat", "batch", "cluster_ids")}
        if condition["cohort"] != "B004" or condition["family"] != "openai" or condition["method"] != "leiden" or condition["repeat"] != 0 or len(record["cluster_ids"]) != 75:
            raise ValueError("Incorrect cohort, method, repeat or cell/cluster join")
        expected_id = "r47_" + digest({"protocol_id": protocol["protocol_id"], "condition": condition, "native_body": expected_body})
        if record["request_id"] != expected_id or record["native_body_sha256"] != digest(expected_body):
            raise ValueError("Request ID/body hash mismatch")
        base_record = read(bundle / record["baseline_record_path"])
        if base_record["cluster_ids"] != record["cluster_ids"] or base_record["batch"] != record["batch"] or base_record["source_request_id"] != record["reused_baseline_request_id"]:
            raise ValueError("Incorrect cluster join to reused blinded baseline")
        accepted = read(bundle / record["accepted_baseline_path"])
        if accepted["request_id"] != record["reused_baseline_request_id"] or accepted["body_sha256"] != digest(base) or accepted["method"] != "leiden" or accepted["arm"] != "all_means_fractions" or accepted["model_family"] != "openai" or accepted["canonical_slug_expected"] != "openai/gpt-6-astra-20260903" or accepted["provider"].lower() != "openai" or accepted["accepted_wire_max_tokens"] != 32768 or len(accepted["labels"]) != 75 or any(type(i) is not int or i not in range(28) for i in accepted["labels"]):
            raise ValueError("Accepted blinded baseline provenance differs")
        joins.setdefault(record["arm"], []).extend(record["cluster_ids"])
    if any(len(ids) != 300 or len(set(ids)) != 300 for ids in joins.values()) or joins[ARMS[0]] != joins[ARMS[1]]:
        raise ValueError("Each arm must preserve the same 300 unique Leiden clusters")
    cost = read(bundle / "cost_reservation.json")
    actual_bounds = [len(canonical(item["body"])) + 4096 for item in lines]
    reservation = sum((Decimal(n) * Decimal("6.25") + Decimal(32768) * Decimal("25")) / Decimal(1000000) for n in actual_bounds)
    if cost["input_token_upper_bounds"] != actual_bounds or Decimal(cost["full_output_reservation_usd_exact"]) != reservation or Decimal(cost["rounded_up_reservation_usd"]) != reservation.quantize(Decimal("0.01"), rounding=ROUND_CEILING):
        raise ValueError("Under-reservation or incorrect input-token bound")
    return {"schema": "b004.astra_leiden_controls.offline_check.v1", "passed": True, "request_items": 8, "new_annotation_sets": 2, "cluster_predictions": 600, "reused_blinded_baseline_items": 4, "paid_calls": 0, "execution_enabled": False, "manifest_sha256": sha(bundle / "manifest.json"), "reservation_ceiling_usd": cost["rounded_up_reservation_usd"], "launch_ready": False}


def build(preparation, native_admission, accepted_results, config, output):
    preparation, native_admission, output = map(Path, (preparation, native_admission, output))
    if output.exists():
        raise ValueError("Refusing to overwrite any prepared bundle")
    protocol = read(config)
    source_manifest = read(preparation / "manifest.json")
    if source_manifest["markers"] != MARKERS or source_manifest["cluster_counts"]["leiden"] != 300:
        raise ValueError("Unmatched frozen B004 markers/membership")
    if sha(preparation / "requests.json") != source_manifest["files"]["requests.json"]:
        raise ValueError("Source request/cluster map checksum differs")
    result_manifest = read(Path(accepted_results).parent / "manifest.json")
    if sha(accepted_results) != result_manifest["files"][Path(accepted_results).name]["sha256"]:
        raise ValueError("Frozen accepted-result checksum differs")
    rows = read(preparation / "requests.json")
    accepted_rows = read(accepted_results)["records"]
    accepted = {r["request_id"]: r for r in accepted_rows}
    if len(accepted) != len(accepted_rows):
        raise ValueError("Duplicate accepted baseline IDs")
    index = {(r["family"], r["method"], r["arm"], r["batch"]): r for r in rows}
    if len(index) != len(rows):
        raise ValueError("Duplicate source condition")
    records, lines = [], []
    for arm in ARMS:
        for group in range(4):
            base_record = index["openai", "leiden", "all_means_fractions", group]
            control_record = index["anthropic", "leiden", arm, group]
            for source_record in (base_record, control_record):
                path = preparation / source_record["body_path"]
                if source_manifest["files"][source_record["body_path"]] != sha(path) or digest(read(path)) != source_record["body_sha256"]:
                    raise ValueError("Source evidence checksum differs")
            if base_record["cluster_ids"] != control_record["cluster_ids"] or base_record["expected_n"] != 75 or control_record["expected_n"] != 75:
                raise ValueError("Source control and baseline joins differ")
            base_body = read(preparation / base_record["body_path"])
            control_body = read(preparation / control_record["body_path"])
            body = native_body(base_body, control_body, arm)
            condition = {"cohort": "B004", "family": "openai", "method": "leiden", "arm": arm, "repeat": 0, "batch": group, "cluster_ids": base_record["cluster_ids"]}
            rid = "r47_" + digest({"protocol_id": protocol["protocol_id"], "condition": condition, "native_body": body})
            base_path = f"source/baseline_{group}.json"
            control_path = f"source/control_{arm}_{group}.json"
            base_record_path = f"source/baseline_record_{group}.json"
            accepted_path = f"source/accepted_baseline_{group}.json"
            write(output / base_path, base_body)
            write(output / control_path, control_body)
            write(output / base_record_path, base_record)
            write(output / accepted_path, accepted[base_record["source_request_id"]])
            record = {**condition, "request_id": rid, "expected_n": 75, "native_body_sha256": digest(body), "evidence_sha256": digest(strict_json(body["messages"][1]["content"])), "baseline_template_path": base_path, "control_template_path": control_path, "baseline_record_path": base_record_path, "accepted_baseline_path": accepted_path, "reused_baseline_request_id": base_record["source_request_id"], "source_control_request_id": control_record["request_id"], "submission_allowed": False}
            records.append(record)
            lines.append({"custom_id": rid, "method": "POST", "url": "/v1/chat/completions", "body": body})
    binding = read(native_admission / "model_binding.json")
    pricing = read(native_admission / "pricing.json")
    if binding["admitted"] is not True or binding["native_model"] != "gpt-6-astra" or pricing["input_usd_per_million"] != "5.00" or pricing["output_usd_per_million"] != "25.00" or pricing["default_30m_cache_write_usd_per_million"] != "6.25":
        raise ValueError("Prior admitted model/pricing snapshot differs")
    write(output / "protocol.json", protocol)
    write(output / "requests.json", records)
    (output / "requests.DRAFT.jsonl").write_bytes(b"\n".join(canonical(item) for item in lines) + b"\n")
    write(output / "source/model_binding.json", binding)
    write(output / "source/pricing.json", pricing)
    bounds = [len(canonical(line["body"])) + 4096 for line in lines]
    reservation = sum((Decimal(n) * Decimal("6.25") + Decimal(32768) * Decimal("25")) / Decimal(1000000) for n in bounds)
    write(output / "cost_reservation.json", {"schema": "b004.astra_leiden_controls.reservation.v1", "currency": "USD", "payment_source": "existing_openai_api_balance", "rates_source": "source/pricing.json", "pricing_observed_utc": pricing["verified_at"], "pricing_freshness_at_launch_required": True, "batch_input_usd_per_million": "5.00", "conservative_default_cache_write_input_usd_per_million": "6.25", "batch_output_usd_per_million": "25.00", "input_bound_method": "full_native_body_utf8_bytes_plus_4096_per_item", "input_token_upper_bounds": bounds, "total_input_token_upper_bound": sum(bounds), "combined_reasoning_and_visible_output_token_ceiling_per_item": 32768, "total_output_token_reservation": 8 * 32768, "full_output_reservation_usd_exact": str(reservation), "rounded_up_reservation_usd": str(reservation.quantize(Decimal("0.01"), rounding=ROUND_CEILING)), "spending_cap_approved": False, "live_balance_checked": False, "additional_paid_calls": 0})
    files = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    write(output / "manifest.json", {"schema": "b004.astra_leiden_controls.bundle.v1", "protocol_id": protocol["protocol_id"], "status": "planned_not_executed", "request_items": 8, "new_annotation_sets": 2, "cluster_predictions": 600, "source_preparation_manifest_sha256": sha(preparation / "manifest.json"), "source_preparation_requests_sha256": sha(preparation / "requests.json"), "accepted_results_sha256": sha(accepted_results), "source_receipt_sha256": sha(preparation / "source_receipt.json"), "source_training_scaler_sha256": sha(preparation / "training_scaler.npz"), "files": files, "paid_calls": 0, "jobs_submitted": 0, "execution_enabled": False, "launch_ready": False})
    return check(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    make = sub.add_parser("build")
    for name in ("preparation", "native-admission", "accepted-results", "config", "output"):
        make.add_argument("--" + name, required=True, type=Path)
    inspect = sub.add_parser("check")
    inspect.add_argument("--bundle", required=True, type=Path)
    args = vars(parser.parse_args())
    action = args.pop("action")
    print(json.dumps(build(**args) if action == "build" else check(**args), indent=2))


if __name__ == "__main__":
    main()
