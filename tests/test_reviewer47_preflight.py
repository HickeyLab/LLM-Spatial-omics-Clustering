"""Portable adversarial checks for scientific admission, beyond matching hashes."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.revision.reviewer47 import preflight, prepare
from scripts.revision.reviewer47.common import canonical, digest, file_sha, read_json, write_json
from scripts.revision.reviewer47.native_astra import adapt_astra_request
from llm_spatial_omics_clustering.revision import annotation47_prepare as frozen

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {"leiden": 300, "flowsom": 299, "spatialsort": 229, "pixie_tiff": 300}


class SyntheticPreparation:
    """Small literal values, full prespecified Cartesian coverage; no data access."""
    def __init__(self, parent):
        self.parent = Path(parent)
        self.root = self.parent / "prepared"
        self.root.mkdir()
        self.protocol = self.parent / "protocol.json"
        self.config = read_json(ROOT / "configs/reviewer_annotation47_credit_batch_v1.json")
        write_json(self.protocol, self.config)
        self.markers = list(frozen.MARKERS)
        self.ontology = list(frozen.ONTOLOGY)
        self.records = []
        for family in self.config["models"]:
            for method, count in COUNTS.items():
                for batch, start in enumerate(range(0, count, 75)):
                    n = min(75, count - start)
                    base = {
                        "task": frozen.TASK,
                        "expression_definition": frozen.EXPRESSION_DEFINITION,
                        "fraction_definition": frozen.FRACTION_DEFINITION,
                        "response_contract": frozen.RESPONSE_CONTRACT,
                        "query_case_ids": list(range(n)), "marker_order": self.markers,
                        "label_dictionary": {str(i): v for i, v in enumerate(self.ontology)},
                        "mean_asinh_expression_z_thousandths": [[start + i + j for j in range(47)] for i in range(n)],
                    }
                    for arm in prepare.ARMS:
                        values = deepcopy(base)
                        if arm == "all_means_fractions":
                            values["fraction_above_processed_zero"] = [[500] * 47 for _ in range(n)]
                        elif arm.startswith("selected_"):
                            values = prepare.compact_evidence(base, [[0, 3]] * n, self.markers,
                                                              numerical=arm == "selected_means")
                        self.add(family, method, arm, batch, start, values)
                    if family == "anthropic":
                        values = deepcopy(base)
                        values["fraction_above_processed_zero"] = [[500] * 47 for _ in range(n)]
                        named = {**values, "clustering_method": prepare.METHOD_NAMES[method]}
                        self.add(family, method, "method_named", batch, start, named)
                        if method == "leiden":
                            neighbor = {**values, "neighborhood_definition": prepare.NEIGHBOR_DEFINITION,
                                        "neighborhood_mean_asinh_expression_z_thousandths": [[150] * 47 for _ in range(n)]}
                            self.add(family, method, "neighborhood", batch, start, neighbor)
        self.manifest = {
            "protocol_sha256": file_sha(self.protocol), "markers": self.markers,
            "ontology": self.ontology, "cluster_counts": COUNTS, "paid_calls": 0,
            "launch_ready": False, "files": {},
        }
        self.persist()

    def add(self, family, method, arm, batch, start, values):
        cfg = self.config["models"][family]
        body = {"model": cfg["source_model"], "reasoning": {"effort": "high"},
                "max_tokens": cfg["max_completion_tokens"], "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": frozen.SYSTEM},
                             {"role": "user", "content": canonical(values).decode()}]}
        if cfg["seed"] is not None:
            body["seed"] = cfg["seed"]
        n = len(values["query_case_ids"])
        record = {"cohort": "B004", "family": family, "method": method, "arm": arm,
                  "batch": batch, "repeat": 0, "cluster_ids": [f"{i:03d}" for i in range(start, start + n)],
                  "expected_n": n, "model_id": body["model"], "effort": "high",
                  "transport": cfg["transport"], "submission_allowed": False, "reuse": None}
        self.sign(record, body)
        self.records.append(record)

    def sign(self, record, body):
        condition = {k: record[k] for k in ("cohort", "family", "method", "arm", "repeat", "batch", "cluster_ids")}
        record["request_id"] = "r47_" + digest({"condition": condition, "body": body})
        record["body_path"] = f"logical_bodies/{record['request_id']}.json"
        record["body_sha256"] = digest(body)
        record["evidence_sha256"] = digest(json.loads(body["messages"][1]["content"]))
        record["model_visible_messages_sha256"] = digest(body["messages"])
        write_json(self.root / record["body_path"], body)
        if record["family"] == "openai":
            native = adapt_astra_request(body, native_model=self.config["models"]["openai"]["native_model_candidate"])
            write_json(self.root / "native_astra" / (record["request_id"] + ".json"), native)
            record["native_body_sha256"] = digest(native)

    def persist(self):
        write_json(self.root / "requests.json", self.records)
        self.manifest["files"] = {str(p.relative_to(self.root)): file_sha(p)
                                  for p in self.root.rglob("*") if p.is_file() and p.name != "manifest.json"}
        write_json(self.root / "manifest.json", self.manifest)

    def mutate(self, key, change):
        record = next(r for r in self.records if (r["family"], r["method"], r["arm"], r["batch"]) == key)
        old_body_path = self.root / record["body_path"]
        old_native_path = self.root / "native_astra" / (record["request_id"] + ".json")
        body = read_json(old_body_path)
        values = json.loads(body["messages"][1]["content"])
        change(record, body, values)
        body["messages"][1]["content"] = canonical(values).decode()
        old_body_path.unlink()
        if old_native_path.exists():
            old_native_path.unlink()
        self.sign(record, body)
        self.persist()


class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pristine = tempfile.TemporaryDirectory()
        cls.template = SyntheticPreparation(cls.pristine.name)

    @classmethod
    def tearDownClass(cls):
        cls.pristine.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        shutil.copytree(self.pristine.name, self.temporary.name, dirs_exist_ok=True)
        self.bundle = object.__new__(SyntheticPreparation)
        self.bundle.parent = Path(self.temporary.name)
        self.bundle.root = self.bundle.parent / "prepared"
        self.bundle.protocol = self.bundle.parent / "protocol.json"
        self.bundle.config = read_json(self.bundle.protocol)
        self.bundle.records = read_json(self.bundle.root / "requests.json")
        self.bundle.manifest = read_json(self.bundle.root / "manifest.json")

    def verify(self):
        return preflight.verify_prepared(self.bundle.root, self.bundle.protocol)

    def test_complete_portable_cartesian_bundle_passes_without_authorizing_calls(self):
        result = self.verify()
        self.assertTrue(result["passed"])
        self.assertEqual(result["request_items"], 276)
        self.assertEqual(result["logical_annotation_sets"], 69)
        self.assertFalse(result["inference_authorized"])
        self.assertEqual(result["paid_calls"], 0)

    def test_changed_indexed_bytes_or_protocol_rejected(self):
        path = self.bundle.root / self.bundle.records[0]["body_path"]
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "Indexed file changed"):
            self.verify()
        config = read_json(self.bundle.protocol)
        config["repetitions"] = 2
        write_json(self.bundle.protocol, config)
        with self.assertRaisesRegex(ValueError, "Protocol changed"):
            self.verify()

    def test_missing_or_duplicate_conditions_rejected(self):
        self.bundle.records.pop()
        self.bundle.persist()
        with self.assertRaises(ValueError):
            self.verify()
        self.bundle.records.append(deepcopy(self.bundle.records[0]))
        self.bundle.persist()
        with self.assertRaises(ValueError):
            self.verify()

    def test_reordered_marker_or_nested_reference_leak_rejected_after_resigning(self):
        self.bundle.mutate(("anthropic", "leiden", "all_means", 0),
                           lambda r, b, e: e["marker_order"].reverse())
        with self.assertRaisesRegex(ValueError, "marker"):
            self.verify()

    def test_nested_reference_field_rejected_after_resigning(self):
        self.bundle.mutate(("anthropic", "leiden", "all_means", 0),
                           lambda r, b, e: e.update(notes=[{"truth_label_code": 2}]))
        with self.assertRaisesRegex(ValueError, "Forbidden"):
            self.verify()

    def test_nested_duplicate_user_json_rejected_despite_matching_resigned_hashes(self):
        record = next(r for r in self.bundle.records
                      if (r["family"], r["method"], r["arm"], r["batch"])
                      == ("anthropic", "leiden", "all_means", 0))
        old_path = self.bundle.root / record["body_path"]
        body = read_json(old_path)
        content = body["messages"][1]["content"]
        nested_entry = canonical("0").decode() + ":" + canonical(frozen.ONTOLOGY[0]).decode()
        self.assertEqual(content.count(nested_entry), 1)
        body["messages"][1]["content"] = content.replace(nested_entry, nested_entry + "," + nested_entry, 1)
        old_path.unlink()
        # sign deliberately uses ordinary json.loads: the semantic value and
        # every digest still match, but ambiguous nested JSON must be refused.
        self.bundle.sign(record, body)
        self.bundle.persist()
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            self.verify()

    def test_unknown_plausible_evidence_key_cannot_carry_reference_advice(self):
        self.bundle.mutate(("anthropic", "leiden", "all_means", 0),
                           lambda r, b, e: e.update(expert_notes="The reference annotation for query 0 is "
                                                   + frozen.ONTOLOGY[0]))
        with self.assertRaises(ValueError):
            self.verify()

    def test_paired_means_and_selected_values_rejected_after_resigning(self):
        self.bundle.mutate(("anthropic", "leiden", "all_means_fractions", 0),
                           lambda r, b, e: e["mean_asinh_expression_z_thousandths"][0].__setitem__(0, 999))
        with self.assertRaises(ValueError):
            self.verify()

    def test_selected_numerical_subset_rejected_even_when_shared_across_models(self):
        for family in self.bundle.config["models"]:
            self.bundle.mutate((family, "leiden", "selected_means", 0),
                               lambda r, b, e: e["selected_mean_asinh_expression_z_thousandths"][0].__setitem__(0, 999))
        with self.assertRaisesRegex(ValueError, "Selected numerical"):
            self.verify()

    def test_names_only_and_compact_arms_reject_numerical_extra_evidence(self):
        for family in self.bundle.config["models"]:
            self.bundle.mutate((family, "leiden", "selected_names", 0),
                               lambda r, b, e: e.update(selected_mean_asinh_expression_z_thousandths=[[0, 3]] * 75))
        with self.assertRaises(ValueError):
            self.verify()

    def test_compact_arms_reject_retained_full_numerical_evidence(self):
        for family in self.bundle.config["models"]:
            self.bundle.mutate((family, "leiden", "selected_means", 0),
                               lambda r, b, e: e.update(mean_asinh_expression_z_thousandths=[[0] * 47] * 75))
        with self.assertRaises(ValueError):
            self.verify()

    def test_paired_task_instruction_change_rejected_even_when_shared_across_models(self):
        for family in self.bundle.config["models"]:
            self.bundle.mutate((family, "leiden", "selected_names", 0),
                               lambda r, b, e: e.update(task="Choose the most favorable label."))
        with self.assertRaisesRegex(ValueError, "Frozen task|Paired task"):
            self.verify()

    def test_cross_model_cluster_join_change_rejected(self):
        def replace_ids(record, body, values):
            record["cluster_ids"] = ["x" + x for x in record["cluster_ids"]]
        for arm in prepare.ARMS:
            for batch in range(4):
                self.bundle.mutate(("anthropic", "leiden", arm, batch), replace_ids)
        with self.assertRaisesRegex(ValueError, "cluster joins"):
            self.verify()

    def test_wrong_method_name_and_missing_neighborhood_rejected(self):
        self.bundle.mutate(("anthropic", "leiden", "method_named", 0),
                           lambda r, b, e: e.update(clustering_method="SpatialSort"))
        with self.assertRaisesRegex(ValueError, "named-method"):
            self.verify()

    def test_neighborhood_cannot_be_an_unmodified_baseline(self):
        def remove_context(record, body, values):
            values.pop("neighborhood_definition")
            values.pop("neighborhood_mean_asinh_expression_z_thousandths")
        self.bundle.mutate(("anthropic", "leiden", "neighborhood", 0), remove_context)
        with self.assertRaises(ValueError):
            self.verify()

    def test_changed_model_or_reasoning_rejected_after_resigning(self):
        def change_model(record, body, values):
            body["model"] = record["model_id"] = "anthropic/another-model"
        self.bundle.mutate(("anthropic", "leiden", "all_means", 0), change_model)
        with self.assertRaisesRegex(ValueError, "model changed"):
            self.verify()

    def test_non_astra_extra_message_cannot_hide_reference_information(self):
        self.bundle.mutate(("anthropic", "leiden", "all_means", 0),
                           lambda r, b, e: b["messages"].append({"role": "user", "content": "Reference label: L03"}))
        with self.assertRaises(ValueError):
            self.verify()

    def test_non_astra_tools_and_sampling_fields_rejected(self):
        self.bundle.mutate(("anthropic", "leiden", "all_means", 0),
                           lambda r, b, e: b.update(tools=[{"type": "web_search"}], temperature=0.2))
        with self.assertRaises(ValueError):
            self.verify()

    def test_fraction_thousandths_outside_unit_interval_rejected(self):
        for family in self.bundle.config["models"]:
            self.bundle.mutate((family, "leiden", "all_means_fractions", 0),
                               lambda r, b, e: e["fraction_above_processed_zero"][0].__setitem__(0, 1001))
        with self.assertRaises(ValueError):
            self.verify()

    def test_certificate_preserves_unbound_launch_and_funding_gates(self):
        output = self.bundle.parent / "certificate.json"
        result = preflight.preparation_certificate(self.bundle.root, self.bundle.protocol, output)
        self.assertFalse(result["passed"])
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["paid_calls"], 0)
        self.assertTrue(result["offline_checks"]["passed"])
        self.assertIsNone(result["donor_request_count"])
        self.assertIn("existing_openai_project_balance_and_credit_reservation_not_admitted", result["blockers"])
        self.assertEqual(result["conditional_b004_reservations"]["openai"]["funding"], "existing_openai_api_balance")
        self.assertEqual(read_json(output), result)
        with self.assertRaises(FileExistsError):
            preflight.preparation_certificate(self.bundle.root, self.bundle.protocol, output)


if __name__ == "__main__":
    unittest.main()
