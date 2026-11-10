"""Admission-independent checks for the active one-annotation study record."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PRESERVED_PREPARATIONS = {
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
        self.assertEqual(self.registry["planned_annotation_protocol"],
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
            set(PRESERVED_PREPARATIONS),
        )

    def test_no_new_result_or_launch_claim(self):
        entries = {x["id"]: x for x in self.registry["experiments"]}
        for experiment_id in (7, 14):
            entry = entries[experiment_id]
            self.assertEqual(entry["status"], "replacement_planned_not_executed")
            self.assertEqual(entry["planned_successor"], self.protocol["protocol_id"])
            self.assertFalse(entry["existing_results_remain_reported"])
            self.assertFalse(entry["new_execution"])
            self.assertNotIn(experiment_id, self.registry["active_reported_ids"])
        self.assertEqual(self.registry["planned_result_ids"], [7, 14])
        for execution in (self.active["execution"], self.protocol["execution"]):
            self.assertFalse(execution["enabled"])
            self.assertFalse(execution["automatic_launch"])
            self.assertEqual(execution["annotation_calls"], 0)
            self.assertEqual(execution["jobs_submitted"], 0)
            self.assertIsNone(execution["launch_authorization"])
        self.assertEqual(self.active["publication"]["figure_replacements"], "paused")
        self.assertIsNone(self.active["financial_planning"]["approved_spend_cap_usd"])
        self.assertFalse(
            self.active["financial_planning"]["planning_ceiling_is_spending_approval"]
        )

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
            if experiment_id not in (7, 9, 14):
                self.assertEqual(new_entries[experiment_id], old_entry)
        self.assertEqual(self.registry["active_reported_ids"],
                         [i for i in archived["active_reported_ids"] if i not in (7, 9, 14)])

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
        self.assertEqual(summary["batch_request_items"], 96)
        self.assertEqual(summary["standard_deepseek_request_items"], 32)
        self.assertEqual(summary["model_ids"],
                         [x["model_id"] for x in self.protocol["model_bindings"].values()])


if __name__ == "__main__":
    unittest.main()
