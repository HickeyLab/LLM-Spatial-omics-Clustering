"""Admission-independent checks for the active one-annotation study record."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PRESERVED_PREPARATIONS = {
    "configs/primary_annotation47_1repeat_opus55_v1.json":
        "c8de5b481ee48253015f54d6e30f47ba9cefc3ab00ec2ba465df0395b5580052",
    "configs/primary_annotation47_3repeat_v1.json":
        "d22155c550654327d72f3c3014c7847d8ace7ee020d7889a374a3da3d4258da6",
    "configs/combined_annotation47_7_9_14_v1.json":
        "480d9fd4191346ba8cd3b2a4a541698a6e8c7806bc5eaedf427e7e9ce9d3e99a",
}


def load(relative_path):
    return json.loads((ROOT / relative_path).read_text())


def sha(relative_path):
    return hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()


class ActiveStudyTests(unittest.TestCase):
    def setUp(self):
        self.registry = load("configs/experiment_registry.json")
        self.active = load("configs/annotation47_active_study.json")
        self.protocol = load(self.active["active_preparation"])

    def test_one_authoritative_active_selection(self):
        self.assertEqual(self.registry["active_study_record"],
                         "configs/annotation47_active_study.json")
        self.assertEqual(self.registry["annotation_protocol"],
                         self.active["active_preparation"])
        self.assertEqual(self.active["active_preparation"],
                         "configs/primary_annotation47_1repeat_opus55_v1.json")
        self.assertEqual(self.registry["active_annotation_experiment_ids"], [7, 14])
        self.assertEqual(self.active["active_experiment_ids"], [7, 14])
        self.assertEqual(self.protocol["experiment_ids"], [7, 14])
        self.assertEqual(self.active["active_preparation_protocol_id"],
                         self.protocol["protocol_id"])
        self.assertNotIn("planned_combined_protocol", self.registry)
        self.assertEqual(
            {x["path"] for x in self.registry["archival_preparations"]},
            set(PRESERVED_PREPARATIONS) - {"configs/primary_annotation47_1repeat_opus55_v1.json"},
        )

    def test_completed_results_are_recorded_without_an_inference_launch(self):
        entries = {x["id"]: x for x in self.registry["experiments"]}
        self.assertEqual(self.active["status"], "completed_scored_verified")
        self.assertEqual(self.registry["active_reported_ids"],
                         [1, 2, 3, 5, 7, 8, 10, 11, 12, 13, 14])
        for experiment_id in (7, 14):
            entry = entries[experiment_id]
            self.assertEqual(entry["status"], "reported_completed")
            self.assertEqual(entry["reported_protocol_id"], self.protocol["protocol_id"])
            self.assertFalse(entry["prior_results_remain_reported"])
            self.assertFalse(entry["new_execution"])
            self.assertIn(experiment_id, self.registry["active_reported_ids"])
        self.assertEqual(self.registry["completed_result_ids"], [7, 12, 14])
        self.assertFalse(self.active["execution"]["enabled"])
        self.assertFalse(self.active["execution"]["automatic_launch"])
        self.assertEqual(self.active["execution"]["new_annotation_calls_by_publication_update"], 0)
        self.assertEqual(self.active["execution"]["accepted_request_items"], 128)
        self.assertEqual(self.active["execution"]["accepted_cluster_predictions"], 9024)
        self.assertFalse(self.protocol["execution"]["enabled"])
        self.assertFalse(self.protocol["execution"]["automatic_launch"])
        self.assertEqual(self.protocol["execution"]["annotation_calls"], 0)
        self.assertIsNone(self.protocol["execution"]["launch_authorization"])
        result = self.active["results"]
        self.assertEqual(sha(result["manifest"]), result["manifest_sha256"])
        manifest = load(result["manifest"])
        for name, entry in manifest["files"].items():
            path = str(Path(result["manifest"]).parent / name)
            self.assertEqual(sha(path), entry["sha256"])
            self.assertEqual((ROOT / path).stat().st_size, entry["bytes"])
        summary = load(result["summary"])
        self.assertEqual(summary["accepted_requests"], 128)
        self.assertEqual(summary["accepted_predictions"], 9024)
        actual = load(self.active["execution"]["actual_execution_summary"])
        self.assertEqual(actual["new_calls_from_scoring"], 0)
        self.assertEqual(actual["new_scheduler_actions_from_publication"], 0)
        self.assertIsNone(actual["settled_total_campaign_cost_usd"])
        self.assertTrue(actual["unknown_billing_preserved"])
        self.assertNotIn("recorded_campaign_charge_usd", actual)
        self.assertNotIn("approved_cap_usd", actual)
        settings = {r["model_family"]: r for r in actual["models"]}
        for model in ("openai", "anthropic"):
            self.assertEqual(settings[model]["accepted_wire_max_tokens"], 32768)
        for model in ("google", "deepseek"):
            self.assertEqual(settings[model]["accepted_wire_max_tokens"], 943718)
        self.assertEqual({row["reasoning"] for row in actual["models"]}, {"high"})
        self.assertEqual(settings["openai"]["seed_where_supported"], 42)
        self.assertEqual(settings["google"]["seed_where_supported"], 42)
        self.assertIsNone(settings["anthropic"]["seed_where_supported"])
        self.assertIsNone(settings["deepseek"]["seed_where_supported"])
        self.assertEqual(settings["google"]["native_continuation_segment_output_bound"], 65536)
        self.assertEqual(self.active["publication"]["google_doc_mode"], "Suggesting")
        self.assertFalse(self.active["publication"]["result_placeholders_only_until_valid_outputs"])

    def test_repeatability_id_is_archived_not_succeeded(self):
        entry = next(x for x in self.registry["experiments"] if x["id"] == 9)
        self.assertNotIn(9, self.registry["active_reported_ids"])
        self.assertEqual(entry["status"], "archived")
        self.assertFalse(entry["existing_results_remain_reported"])
        self.assertFalse(entry["new_execution"])
        self.assertNotIn("planned_successor", entry)
        self.assertEqual(entry["archive"],
                         self.active["experiment_9"]["registry_archive_manifest"])
        self.assertEqual(entry["evidence_archive"],
                         self.active["experiment_9"]["archive_index"])
        self.assertEqual(self.active["experiment_9"]["status"], "archived")
        self.assertFalse(self.active["experiment_9"]["active_manuscript_result"])
        self.assertTrue(all(v is False for v in self.active["repetition_claims"].values()))

    def test_registry_archive_is_exact_and_unrelated_ids_unchanged(self):
        manifest_path = self.active["experiment_9"]["registry_archive_manifest"]
        self.assertEqual(sha(manifest_path),
                         self.active["experiment_9"]["registry_archive_manifest_sha256"])
        manifest = load(manifest_path)
        entry = manifest["files"][0]
        self.assertEqual(entry["original_path"], "configs/experiment_registry.json")
        self.assertEqual(entry["sha256"],
                         "ad31a568209f0444d7050601b226de799b03737fd739a70d6ca07c7f13e17d21")
        self.assertEqual(sha(entry["archive_path"]), entry["sha256"])
        self.assertEqual((ROOT / entry["archive_path"]).stat().st_size, entry["bytes"])
        archived = load(entry["archive_path"])
        old_entries = {x["id"]: x for x in archived["experiments"]}
        new_entries = {x["id"]: x for x in self.registry["experiments"]}
        self.assertEqual(set(old_entries), set(new_entries))
        for experiment_id, old_entry in old_entries.items():
            self.assertEqual(new_entries[experiment_id]["experiment"], old_entry["experiment"])
            if experiment_id in (1, 2, 3, 4):
                self.assertEqual(new_entries[experiment_id], old_entry)
        self.assertEqual(self.registry["active_reported_ids"],
                         [1, 2, 3, 5, 7, 8, 10, 11, 12, 13, 14])
        for experiment_id in (4, 6, 9):
            self.assertEqual(new_entries[experiment_id]["status"], "archived")
            self.assertNotIn(experiment_id, self.registry["active_reported_ids"])
        self.assertEqual(new_entries[5]["components"]["native_requested_K_study"]["status"], "archived")
        self.assertEqual(new_entries[8]["components"]["reference_assisted_annotation"]["status"], "archived")
        self.assertEqual(new_entries[8]["components"]["B005_B006_transfer"]["status"], "pending")
        for experiment_id in (8, 10, 11, 13):
            self.assertEqual(new_entries[experiment_id]["status"], "reported_partial")

    def test_followup_pending_results_are_not_called_completed(self):
        followup = self.active["followup_components"]
        self.assertEqual(followup["planned_base_annotation_sets"], 69)
        self.assertEqual(followup["complete_base_annotation_sets"], 68)
        self.assertEqual(followup["planned_base_request_items"], 276)
        self.assertEqual(followup["accepted_base_request_items"], 275)
        self.assertEqual(followup["total_pending_request_items"], 9)
        self.assertEqual(followup["exact_reused_request_items"], 109)
        self.assertEqual(followup["newly_accepted_request_items"], 166)
        self.assertFalse(followup["donor_results_included"])
        self.assertFalse(followup["private_high_xhigh_pilot_included"])
        self.assertEqual(sha(followup["result_manifest"]), followup["result_manifest_sha256"])
        entries = {row["id"]: row for row in self.registry["experiments"]}
        compact = entries[10]["components"]["matched47marker_representations"]
        self.assertEqual(compact["complete_annotation_sets"], 63)
        self.assertEqual(compact["pending_clusters"], 75)
        self.assertIsNone(compact["incomplete_condition_accuracy"])
        self.assertIsNone(compact["overall_four_arm_aggregate"])
        for experiment_id in (11, 13):
            self.assertEqual(entries[experiment_id]["components"]["Astra_Leiden"]["status"], "pending")
            self.assertFalse(entries[experiment_id]["components"]["Astra_Leiden"]["results_included"])

    def test_original_publication_metadata_is_hash_preserved(self):
        index = load("archive/reviewer47_publication_before_20261111/metadata_index.json")
        self.assertEqual(len(index["files"]), 6)
        for row in index["files"]:
            self.assertEqual(sha(row["archive_path"]), row["sha256"])
            self.assertEqual((ROOT / row["archive_path"]).stat().st_size, row["bytes"])
        archived = load("archive/reviewer47_publication_before_20261111/configs/annotation47_active_study.json")
        self.assertEqual(archived["financial_execution"]["confirmed_campaign_charge_usd"], "77.078729829")
        self.assertIsNone(self.active["financial_execution"]["settled_total_campaign_cost_usd"])

    def test_live_document_verification_is_not_inferred_from_preparation(self):
        publication = self.active["publication"]
        if publication["live_google_doc_saved_verified"]:
            self.assertEqual(publication["state"], "google_doc_suggestions_saved_and_verified")
            self.assertTrue((ROOT / publication["integration_receipt"]).exists())
        else:
            self.assertEqual(publication["state"], "prepared_awaiting_google_doc_verification")
            self.assertIsNone(publication["integration_receipt"])

    def test_preparations_and_repeatability_evidence_preserved(self):
        for path, expected in PRESERVED_PREPARATIONS.items():
            self.assertEqual(sha(path), expected)
        archive = self.active["experiment_9"]
        self.assertEqual(sha(archive["archive_index"]), archive["archive_index_sha256"])
        index = load(archive["archive_index"])
        self.assertEqual(len(index["files"]), 175)
        indexed = {x["archive_path"]: x for x in index["files"]}
        for entry in archive["archived_members"]:
            self.assertEqual(indexed[entry["archive_path"]], entry)
            self.assertEqual(sha(entry["archive_path"]), entry["sha256"])
        replay_entry = next(
            x for x in archive["archived_members"]
            if x["original_path"] == "data/frozen/manuscript_replay/manifest.json"
        )
        replay = load(replay_entry["archive_path"])
        replay_files = {x["path"]: x for x in replay["files"]}
        for entry in archive["preserved_manifest_pinned_evidence"]:
            self.assertEqual(replay_files[entry["path"]], entry)
            self.assertEqual(sha(entry["path"]), entry["sha256"])

    def test_design_record_matches_new_protocol(self):
        summary = self.active["study_summary"]
        self.assertEqual(summary["repetitions"], 1)
        self.assertEqual(self.protocol["repeats"], 1)
        self.assertEqual(self.protocol["repeat_seeds_where_supported"], [42])
        for key, expected in (("logical_annotation_sets", 32),
                              ("initial_request_items", 128),
                              ("planned_cluster_predictions", 9024)):
            self.assertEqual(self.protocol[key], expected)
        self.assertEqual(summary["annotation_sets"], 32)
        self.assertEqual(summary["initial_request_items"], 128)
        self.assertEqual(summary["planned_cluster_predictions"], 9024)
        self.assertEqual(summary["initial_batch_request_items"], 96)
        self.assertEqual(summary["accepted_batch_request_items"], 64)
        self.assertEqual(summary["accepted_standard_streaming_request_items"], 64)
        self.assertEqual(summary["initial_standard_request_items"], 32)
        self.assertEqual(summary["model_ids"],
                         [x["model_id"] for x in self.protocol["model_bindings"].values()])


if __name__ == "__main__":
    unittest.main()
