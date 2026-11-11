"""Scientific pairing, provenance, budget and strict-response failure cases."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/revision/prepare_astra_leiden_controls.py"
SPEC = importlib.util.spec_from_file_location("astra_leiden_controls", PATH)
controls = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controls)
BUNDLE = ROOT / "data/frozen/astra_leiden_controls_prepared_20261111"


class TestAstraLeidenControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = controls.read(BUNDLE / "source/baseline_0.json")
        cls.named = controls.read(BUNDLE / "source/control_method_named_0.json")
        cls.neighbor = controls.read(BUNDLE / "source/control_neighborhood_0.json")

    def test_frozen_bundle_passes_and_remains_disabled(self):
        result = controls.check(BUNDLE)
        self.assertEqual((result["request_items"], result["cluster_predictions"], result["paid_calls"]), (8, 600, 0))
        self.assertFalse(result["launch_ready"])
        self.assertFalse(result["execution_enabled"])

    def test_missing_and_reordered_marker_columns_rejected(self):
        for markers in (controls.MARKERS[:-1], list(reversed(controls.MARKERS))):
            evidence = controls.strict_json(self.base["messages"][1]["content"])
            evidence["marker_order"] = markers
            with self.assertRaises(ValueError):
                controls.validate_base(evidence)

    def test_reference_metadata_and_method_leakage_rejected(self):
        for key, value in (("truth_label", 7), ("donor", "B004"), ("clustering_method", "Leiden")):
            modified = deepcopy(self.neighbor)
            evidence = controls.strict_json(modified["messages"][1]["content"])
            evidence[key] = value
            modified["messages"][1]["content"] = controls.canonical(evidence).decode()
            with self.assertRaises(ValueError):
                controls.native_body(self.base, modified, "neighborhood")

    def test_mismatched_paired_means_fractions_or_query_ids_rejected(self):
        for field in ("mean_asinh_expression_z_thousandths", "fraction_above_processed_zero", "query_case_ids"):
            modified = deepcopy(self.named)
            evidence = controls.strict_json(modified["messages"][1]["content"])
            if field == "query_case_ids":
                evidence[field][0] = 74
            else:
                evidence[field][0][0] += 1
            modified["messages"][1]["content"] = controls.canonical(evidence).decode()
            with self.assertRaises(ValueError):
                controls.native_body(self.base, modified, "method_named")

    def test_wrong_named_method_and_noninteger_neighbor_rejected(self):
        for original, arm, field, value in ((self.named, "method_named", "clustering_method", "FlowSOM"), (self.neighbor, "neighborhood", "neighborhood_mean_asinh_expression_z_thousandths", [[0.5] * 47] * 75)):
            modified = deepcopy(original)
            evidence = controls.strict_json(modified["messages"][1]["content"])
            evidence[field] = value
            modified["messages"][1]["content"] = controls.canonical(evidence).decode()
            with self.assertRaises(ValueError):
                controls.native_body(self.base, modified, arm)

    def _mutated_bundle(self, mutate):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / "bundle"
        shutil.copytree(BUNDLE, out)
        mutate(out)
        # Recompute the index so these tests reach semantic guards, not just
        # file-integrity checks. The external sealed manifest hash also changes.
        manifest = controls.read(out / "manifest.json")
        manifest["files"] = {name: controls.sha(out / name) for name in manifest["files"]}
        controls.write(out / "manifest.json", manifest)
        return out

    def test_duplicate_request_and_incomplete_coverage_rejected(self):
        for duplicate in (True, False):
            def mutate(out):
                records = controls.read(out / "requests.json")
                if duplicate:
                    records[1] = records[0]
                else:
                    records.pop()
                controls.write(out / "requests.json", records)
            with self.assertRaises(ValueError):
                controls.check(self._mutated_bundle(mutate))

    def test_wrong_cluster_join_rejected(self):
        def mutate(out):
            records = controls.read(out / "requests.json")
            records[0]["cluster_ids"][0] = "999::999"
            controls.write(out / "requests.json", records)
        with self.assertRaises(ValueError):
            controls.check(self._mutated_bundle(mutate))

    def test_under_reservation_rejected(self):
        def mutate(out):
            cost = controls.read(out / "cost_reservation.json")
            cost["full_output_reservation_usd_exact"] = "0.01"
            controls.write(out / "cost_reservation.json", cost)
        with self.assertRaises(ValueError):
            controls.check(self._mutated_bundle(mutate))

    def test_accidental_activation_rejected(self):
        def mutate(out):
            protocol = controls.read(out / "protocol.json")
            protocol["execution"]["inference_enabled"] = True
            controls.write(out / "protocol.json", protocol)
        with self.assertRaises(ValueError):
            controls.check(self._mutated_bundle(mutate))

    def test_noise_is_valid_and_shuffled_response_order_is_joined(self):
        answer = {"a": [{"i": i, "l": 21} for i in reversed(range(75))]}
        self.assertEqual(controls.accept_response(json.dumps(answer)), [21] * 75)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            controls.accept_response('{"a":[],"a":[]}')

    def test_missing_extra_duplicate_ids_fields_and_bad_types_rejected(self):
        good = {"a": [{"i": i, "l": 7} for i in range(75)]}
        changes = []
        wrong = deepcopy(good); wrong["a"].pop(); changes.append(wrong)
        wrong = deepcopy(good); wrong["a"].append({"i": 75, "l": 7}); changes.append(wrong)
        wrong = deepcopy(good); wrong["a"][0]["i"] = 1; changes.append(wrong)
        wrong = deepcopy(good); wrong["a"][0]["confidence"] = 1; changes.append(wrong)
        for field, value in (("i", "0"), ("l", True), ("l", 28), ("l", -1)):
            wrong = deepcopy(good); wrong["a"][0][field] = value; changes.append(wrong)
        for wrong in changes:
            with self.assertRaises(ValueError):
                controls.accept_response(json.dumps(wrong))

    def test_truncation_and_refusal_rejected(self):
        good = json.dumps({"a": [{"i": i, "l": 7} for i in range(75)]})
        with self.assertRaises(ValueError):
            controls.accept_response(good, finish_reason="length")
        with self.assertRaises(ValueError):
            controls.accept_response(good, refusal="refusal")


if __name__ == "__main__":
    unittest.main()
