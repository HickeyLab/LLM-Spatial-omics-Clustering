"""Protect frozen Claude provenance and the minority-match correction."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("figure04_replay", ROOT / "scripts/replay_figure_04_historical_claude.py")
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class HistoricalClaudeReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads((ROOT / "docs/leiden_claude_diagnostic_identity_audit.json").read_text())
        with (ROOT / cls.audit["cluster_count_table"]).open() as handle:
            cls.rows = list(csv.DictReader(handle))

    def test_frozen_counts_retain_minority_matches(self):
        summary = replay.verify_clusters(self.rows, self.audit["summary"])[0]
        self.assertEqual(summary["direct_matches"], 123099)
        self.assertEqual(summary["minority_matches"], 7486)
        self.assertEqual(summary["net_annotation_gap_cells"], 41402 - 7486)

    def test_majority_mismatch_is_not_net_annotation_gap(self):
        rows = copy.deepcopy(self.rows)
        row = next(r for r in rows if int(r["historical_21_minority_matches"]) > 0)
        row["historical_21_minority_matches"] = "0"
        with self.assertRaisesRegex(ValueError, "Invalid identity"):
            replay.verify_clusters(rows, self.audit["summary"])

    def test_tampered_claude_label_rejected_before_loading_reference(self):
        config = json.loads((ROOT / replay.CONFIG).read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "configs").mkdir()
            (root / replay.CONFIG).write_text(json.dumps(config))
            for frozen in config["frozen_inputs"].values():
                target = root / frozen["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / frozen["path"]).read_bytes())
            target = root / config["frozen_inputs"]["cluster_counts"]["path"]
            target.write_text(target.read_text().replace("MUC1+ Enterocyte", "Noise", 1))
            with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
                replay.load_replay(root)


if __name__ == "__main__":
    unittest.main()
