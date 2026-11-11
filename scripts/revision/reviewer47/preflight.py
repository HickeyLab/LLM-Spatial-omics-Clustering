"""Offline bundle audit. A preparation certificate never authorizes inference."""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import Path
import json

from .common import digest, file_sha, read_json, verify_index, write_json, strict_json
from .native_astra import adaptation_receipt
from .prepare import ARMS, METHOD_NAMES, SELECTED_DEFINITION, NEIGHBOR_DEFINITION, assert_blinded


def verify_prepared(root, protocol_path):
    from llm_spatial_omics_clustering.revision import annotation47_prepare as frozen
    root = Path(root)
    manifest, config = read_json(root / "manifest.json"), read_json(protocol_path)
    if manifest["protocol_sha256"] != file_sha(protocol_path):
        raise ValueError("Protocol changed after preparation")
    verify_index(root, manifest["files"])
    markers, ontology = manifest["markers"], manifest["ontology"]
    if markers != frozen.MARKERS or ontology != frozen.ONTOLOGY:
        raise ValueError("The exact 47-marker/28-label contract is required")
    if manifest["paid_calls"] != 0 or manifest["launch_ready"] is not False:
        raise ValueError("This is a disabled preparation artifact")
    records = read_json(root / "requests.json")
    if len(records) != 276 or len({r["request_id"] for r in records}) != len(records):
        raise ValueError("Duplicate IDs or incomplete Cartesian coverage")
    indexed = {}
    for r in records:
        key = (r["family"], r["method"], r["arm"], r["batch"])
        if key in indexed or r["repeat"] != 0 or r["submission_allowed"] is not False:
            raise ValueError("Duplicate condition, repeated generation or enabled request")
        if r["family"] not in config["models"] or r["method"] not in config["methods"]:
            raise ValueError("Unexpected condition")
        body = read_json(root / r["body_path"])
        cfg = config["models"][r["family"]]
        required = {"model", "messages", "reasoning", "max_tokens", "response_format"}
        if cfg["seed"] is not None:
            required.add("seed")
        if set(body) != required or body["response_format"] != {"type": "json_object"}:
            raise ValueError("Unexpected tools, retrieval, routing, sampling or response settings")
        messages = body["messages"]
        if (not isinstance(messages, list) or len(messages) != 2
                or any(set(m) != {"role", "content"} or m["role"] != role
                       or not isinstance(m["content"], str) for m, role in zip(messages, ("system", "user")))
                or messages[0]["content"] != frozen.SYSTEM):
            raise ValueError("The exact frozen system/user pair is required")
        evidence = strict_json(body["messages"][1]["content"])
        assert_blinded(evidence, named=r["arm"] == "method_named")
        allowed = {"task", "response_contract", "expression_definition", "fraction_definition",
                   "label_dictionary", "marker_order", "query_case_ids"}
        if r["arm"].startswith("selected_"):
            allowed |= {"selected_marker_names", "selected_marker_definition"}
            if evidence.get("selected_marker_definition") != SELECTED_DEFINITION:
                raise ValueError("Selection interpretation changed")
            if r["arm"] == "selected_means":
                allowed.add("selected_mean_asinh_expression_z_thousandths")
        else:
            allowed.add("mean_asinh_expression_z_thousandths")
            if r["arm"] != "all_means":
                allowed.add("fraction_above_processed_zero")
            if r["arm"] == "method_named":
                allowed.add("clustering_method")
            if r["arm"] == "neighborhood":
                allowed |= {"neighborhood_definition", "neighborhood_mean_asinh_expression_z_thousandths"}
                if evidence.get("neighborhood_definition") != NEIGHBOR_DEFINITION:
                    raise ValueError("Neighborhood interpretation changed")
        if set(evidence) != allowed:
            raise ValueError("Unexpected or missing model-visible evidence fields")
        if (digest(body) != r["body_sha256"] or digest(evidence) != r["evidence_sha256"]
                or digest(body["messages"]) != r["model_visible_messages_sha256"]):
            raise ValueError("Request content hash mismatch")
        if evidence["marker_order"] != markers:
            raise ValueError("Missing or reordered marker")
        if evidence["label_dictionary"] != {str(i): x for i, x in enumerate(ontology)}:
            raise ValueError("Label vocabulary changed")
        for field_name, expected in (("task", frozen.TASK), ("response_contract", frozen.RESPONSE_CONTRACT),
                              ("expression_definition", frozen.EXPRESSION_DEFINITION),
                              ("fraction_definition", frozen.FRACTION_DEFINITION)):
            if evidence.get(field_name) != expected:
                raise ValueError("Frozen task/interpretation instructions changed")
        n = r["expected_n"]
        if len(evidence["query_case_ids"]) != n or len(r["cluster_ids"]) != n:
            raise ValueError("Query map differs from the planned denominator")
        for field in ("mean_asinh_expression_z_thousandths", "fraction_above_processed_zero",
                      "neighborhood_mean_asinh_expression_z_thousandths"):
            if field in evidence:
                matrix = evidence[field]
                if len(matrix) != n or any(len(row) != 47 or any(type(v) is not int for v in row) for row in matrix):
                    raise ValueError("Evidence must be complete 47-marker integer thousandths")
                if field == "fraction_above_processed_zero" and any(not 0 <= v <= 1000 for row in matrix for v in row):
                    raise ValueError("Fractions must lie between zero and one")
        if body["model"] != cfg["source_model"] or r["model_id"] != body["model"]:
            raise ValueError("Configured model changed")
        if body["reasoning"] != {"effort": "high"} or body["max_tokens"] != cfg["max_completion_tokens"]:
            raise ValueError("Reasoning/output settings changed")
        if cfg["seed"] is None and "seed" in body or cfg["seed"] is not None and body.get("seed") != cfg["seed"]:
            raise ValueError("Unsupported or changed seed")
        condition = {k: r[k] for k in ("cohort", "family", "method", "arm", "repeat", "batch", "cluster_ids")}
        if r["request_id"] != "r47_" + digest({"condition": condition, "body": body}):
            raise ValueError("Request ID does not bind the exact condition/body")
        if r["family"] == "openai":
            native = read_json(root / "native_astra" / (r["request_id"] + ".json"))
            if not adaptation_receipt(body, native)["model_visible_contract_exact"]:
                raise ValueError("Native translation changed model-visible content/settings")
        indexed[key] = (r, body, evidence)
    expected = set()
    for family in config["models"]:
        for method in config["methods"]:
            count = manifest["cluster_counts"][method]
            for arm in ARMS:
                rows = []
                for group, start in enumerate(range(0, count, 75)):
                    key = (family, method, arm, group)
                    expected.add(key)
                    r, body, evidence = indexed[key]
                    if r["expected_n"] != min(75, count - start):
                        raise ValueError("Original 75-query boundaries changed")
                    rows.extend(r["cluster_ids"])
                    base_r, base_body, base = indexed[family, method, "all_means", group]
                    canonical_r, _, canonical_evidence = indexed["openai", method, arm, group]
                    if r["cluster_ids"] != canonical_r["cluster_ids"] or evidence != canonical_evidence:
                        raise ValueError("Model families do not share identical evidence/cluster joins")
                    if body["messages"][0] != base_body["messages"][0] or r["cluster_ids"] != base_r["cluster_ids"]:
                        raise ValueError("Paired instructions or query ordering differs")
                    if arm == "all_means_fractions" and base["mean_asinh_expression_z_thousandths"] != evidence["mean_asinh_expression_z_thousandths"]:
                        raise ValueError("Mismatched paired means")
                    added = {"fraction_above_processed_zero"} if arm == "all_means_fractions" else set()
                    removed = set()
                    if arm.startswith("selected_"):
                        if "mean_asinh_expression_z_thousandths" in evidence or "fraction_above_processed_zero" in evidence:
                            raise ValueError("Compact arms must not retain the full numerical evidence")
                        if arm == "selected_names" and "selected_mean_asinh_expression_z_thousandths" in evidence:
                            raise ValueError("Names-only arm must not expose numerical values")
                        added = {"selected_marker_names", "selected_marker_definition"}
                        if arm == "selected_means":
                            added.add("selected_mean_asinh_expression_z_thousandths")
                        removed = {"mean_asinh_expression_z_thousandths"}
                        selected = evidence["selected_marker_names"]
                        mate = indexed[family, method, "selected_names", group][2]
                        if selected != mate["selected_marker_names"] or len(selected) != r["expected_n"]:
                            raise ValueError("Selected arms use different marker names")
                        for i, names in enumerate(selected):
                            if not 1 <= len(names) <= 6 or len(set(names)) != len(names) or any(x not in markers for x in names):
                                raise ValueError("Invalid selected markers")
                            if arm == "selected_means":
                                wanted = [base["mean_asinh_expression_z_thousandths"][i][markers.index(x)] for x in names]
                                if evidence["selected_mean_asinh_expression_z_thousandths"][i] != wanted:
                                    raise ValueError("Selected numerical values differ from the full arm")
                    if ({k: v for k, v in evidence.items() if k not in added}
                            != {k: v for k, v in base.items() if k not in removed}):
                        raise ValueError("Paired task, definitions, vocabulary or response instructions changed")
                if len(set(rows)) != count or rows != sorted(rows):
                    raise ValueError("Duplicate, omitted or reordered cluster join")
    for method in config["methods"]:
        for group in range((manifest["cluster_counts"][method] + 74) // 75):
            expected.add(("anthropic", method, "method_named", group))
    for group in range((manifest["cluster_counts"]["leiden"] + 74) // 75):
        expected.add(("anthropic", "leiden", "neighborhood", group))
    if set(indexed) != expected:
        raise ValueError("Unexpected or missing control condition")
    for (family, method, arm, group), (r, body, evidence) in indexed.items():
        if arm in ("method_named", "neighborhood"):
            base_r, base_body, base = indexed[family, method, "all_means_fractions", group]
            extra = {"clustering_method"} if arm == "method_named" else {
                "neighborhood_mean_asinh_expression_z_thousandths", "neighborhood_definition"}
            if not extra <= set(evidence):
                raise ValueError("Missing prespecified control evidence")
            if arm == "method_named" and evidence["clustering_method"] != METHOD_NAMES[method]:
                raise ValueError("Incorrect named-method identity")
            if arm == "neighborhood" and not evidence["neighborhood_definition"]:
                raise ValueError("Missing neighborhood interpretation")
            if {k: v for k, v in evidence.items() if k not in extra} != base:
                raise ValueError("Control changed more than its prespecified evidence")
            if body["messages"][0] != base_body["messages"][0] or r["cluster_ids"] != base_r["cluster_ids"]:
                raise ValueError("Control instructions/order changed")
    return {"passed": True, "request_items": len(records), "logical_annotation_sets": 69,
            "reference_labels_used_for_inputs": False, "paid_calls": 0,
            "manifest_sha256": file_sha(root / "manifest.json"),
            "protocol_sha256": file_sha(protocol_path), "inference_authorized": False}


def preparation_certificate(root, protocol_path, output, *, donor_observation=None):
    """Record passing offline checks and all unresolved live gates explicitly."""
    audit = verify_prepared(root, protocol_path)
    config = read_json(protocol_path)
    records = read_json(Path(root) / "requests.json")
    counts = Counter(r["family"] for r in records)
    candidates = Counter(r["family"] for r in records if r["reuse"] and r["reuse"]["candidate"])
    # UTF-8 bytes + framing is a deliberately conservative input proxy, not a
    # provider tokenizer count. Output reservations use the entire ceiling.
    estimates = {}
    for family, cfg in config["models"].items():
        new = [r for r in records if r["family"] == family and not (r["reuse"] and r["reuse"]["candidate"])]
        ibytes = sum(len(json.dumps(read_json(Path(root) / r["body_path"])["messages"], ensure_ascii=False).encode()) + 128 for r in new)
        irate = Decimal(cfg.get("input_usd_per_million", cfg.get("input_usd_per_million_proxy", "0")))
        orate = Decimal(cfg.get("output_usd_per_million", cfg.get("output_usd_per_million_proxy", "0")))
        upper = (Decimal(ibytes) * irate + Decimal(len(new) * cfg["max_completion_tokens"]) * orate) / Decimal(1000000)
        estimates[family] = {"planned_items": counts[family], "conditional_reuse_candidates": candidates[family],
            "new_items_if_reuse_admitted": len(new), "funding": cfg["funding"],
            "full_output_plus_byte_input_proxy_usd": str(upper), "pricing_and_tokenization_admitted": False}
    blockers = ["no_separate_launch_instruction_for_this_preflight",
        "native_astra_exact_model_and_seed_support_not_admitted",
        "existing_openai_project_balance_and_credit_reservation_not_admitted",
        "reused_outputs_require_exact_wire_model_route_reconciliation",
        "native_google_batch_long_output_checkpoint_and_pricing_not_admitted",
        "deepseek_morph_fp8_batch_long_output_contract_not_admitted",
        "new_campaign_cash_and_credit_caps_not_bound",
        "donor_both_chains_50_sweeps_not_admitted",
        "current_donor_labels_other_memberships_and_pixie_correspondence_not_admitted"]
    result = {"schema": "reviewer47.preparation_certificate.v1", "status": "blocked_before_launch",
        "passed": False, "offline_checks": audit, "execution_enabled": False,
        "paid_calls": 0, "batch_only": True, "scientific_repetitions": 1,
        "conditional_b004_reservations": estimates,
        "donor_request_count": None, "donor_count_reason": "Occupied clusters and admitted memberships pending",
        "blockers": blockers, "donor_observation": ({
            k: donor_observation.get(k) for k in ("producer_thread_id", "producer_root", "observed_utc",
                "status", "admitted_for_annotation", "approved_external_contract", "expected_total_cells")
            } | {"full_observation_sha256": digest(donor_observation)} if donor_observation else None),
        "note": "This is not a transport launch certificate. No account credit source is restricted to Pro promotions."}
    if Path(output).exists():
        raise FileExistsError("Preserve existing certificate; choose a new path")
    write_json(output, result)
    return result
