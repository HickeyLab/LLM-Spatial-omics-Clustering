"""Protect pending denominators, strict output identity and region weighting."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "publication_replay", ROOT / "scripts/replay_reviewer47_publication.py")
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


class PublicationReplayTests(unittest.TestCase):
    def test_duplicate_json_keys_are_not_silently_last_wins(self):
        with self.assertRaises(ValueError):
            REPLAY.strict_json('{"a": [], "a": []}')

    def test_duplicate_anonymous_query_id_is_rejected(self):
        with self.assertRaises(ValueError):
            REPLAY.parse_labels('{"a":[{"i":0,"l":1},{"i":0,"l":2}]}', 2)

    def test_missing_is_distinct_from_valid_noise(self):
        pending = {"request_id": REPLAY.PENDING_ID, "expected_n": 2,
                   "status": "pending", "labels": [None, None]}
        REPLAY.validate_outcome(pending)
        pending["labels"] = [21, 21]
        with self.assertRaises(ValueError):
            REPLAY.validate_outcome(pending)
        REPLAY.validate_outcome({**pending, "status": "accepted"})

    def test_region_weighting_does_not_weight_larger_region_more(self):
        rows = REPLAY.region_metrics([0, 0, 0, 0, 0, 0],
                                     [0, 0, 1, 1, 1, 1],
                                     ["A", "A", "B", "B", "B", "B"], ["A", "B"])
        self.assertEqual(sum(row["agreement"] for row in rows) / 2, 0.5)
        self.assertEqual(rows[0]["fixed28_macro_f1"], 1 / 28)

    def test_cluster_join_cannot_duplicate_a_query_across_batches(self):
        records = [{"request_id": f"r{i}", "expected_n": 1, "status": "accepted",
                    "batch": i, "cluster_ids": ["same"], "labels": [0]}
                   for i in range(4)]
        with self.assertRaises(ValueError):
            REPLAY.condition_map(records)

    def test_labels_must_be_integer_codes_not_boolean_or_string(self):
        for label in (True, "1", 28, -1):
            with self.assertRaises(ValueError):
                REPLAY.validate_outcome({"request_id": "r", "expected_n": 1,
                                         "status": "accepted", "labels": [label]})


if __name__ == "__main__":
    unittest.main()
