"""Publication evidence, pending-denominator and table-format safeguards."""
from pathlib import Path
import csv
import hashlib
import json
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_reviewer47_figures as figures


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ReviewerPublicationArtworkTests(unittest.TestCase):
    def test_representation_matrix_contains_the_completed_planned_condition(self):
        rows = figures.complete_sets()
        self.assertEqual(len(rows), 71)
        self.assertTrue(rows.status.eq("complete").all())
        selected = rows[rows.family.eq("deepseek") & rows.method.eq("leiden") & rows.arm.eq("selected_means")].iloc[0]
        self.assertEqual(int(selected.delivered_clusters), 300)
        self.assertAlmostEqual(float(selected.agreement), 0.41421655633688514, places=14)
        matrix = figures.representation_matrix(rows, "deepseek")
        self.assertEqual(int(np.isfinite(matrix).sum()), 16)
        # Historical pending evidence is preserved, rather than rewritten.
        original = pd.read_csv(ROOT / "data/frozen/reviewer47_results_20261111/set_metrics.csv")
        pending = original[original.status.eq("pending")]
        self.assertEqual(len(pending), 1)
        self.assertTrue(pending[["agreement", "fixed28_macro_f1"]].isna().all().all())

    def test_partial_accuracy_is_rejected_before_plotting(self):
        rows = figures.complete_sets()
        rows.loc[0, "status"] = "pending"
        rows.loc[0, "agreement"] = .99
        with patch.object(figures, "table", return_value=rows):
            with self.assertRaisesRegex(ValueError, "partial accuracy"):
                figures.complete_sets()

    def test_complete_opus_and_astra_controls_are_plotted(self):
        rows = figures.complete_sets()
        controls = rows[rows.arm.isin(["method_named", "neighborhood"])]
        self.assertTrue(controls.status.eq("complete").all())
        self.assertEqual(set(controls.family), {"anthropic", "openai"})
        self.assertEqual(len(controls), 7)
        pending = read("data/frozen/reviewer47_results_20261111/pending_dependencies.json")
        self.assertEqual(pending["astra_extension"]["planned_request_items"], 8)
        self.assertEqual(pending["astra_extension"]["status"], "pending")
        latest = read("data/frozen/astra_prompt_controls_results_20261115/verification.json")
        self.assertEqual(latest["extension_requests"], 8)
        self.assertEqual(latest["extension_predictions"], 600)

    def test_native_table_rows_and_covariates_are_preserved(self):
        original = read("docs/tables/ieee/source_tables.json")["tables"]
        current = read("docs/tables/ieee_reviewer47_20261111/source_tables.json")["tables"]
        for key in ["S6a", "S6b", "S6c"]:
            self.assertEqual([r[:2] for r in current[key]["rows"][1:]],
                             [r[:2] for r in original[key]["rows"][1:]])
        self.assertIn("Means + fractions macro-F1", current["S6b"]["rows"][0])
        deep = current["S8d"]["rows"]
        selected = next(r for r in deep[1:] if r[:2] == ["Leiden", "Selected means"])
        self.assertEqual(selected[2:4], ["41.42", "0.3576"])
        self.assertEqual(selected[4], "300/300")

    def test_export_hashes_and_ieee_style(self):
        folder = ROOT / "docs/tables/ieee_reviewer47_20261111"
        manifest = read("docs/tables/ieee_reviewer47_20261111/manifest.json")
        self.assertEqual(len(manifest["tables"]), 15)
        for key, record in manifest["tables"].items():
            for suffix, entry in record["files"].items():
                self.assertEqual(sha(folder / (key + suffix)), entry["sha256"])
            html = (folder / (key + ".html")).read_text()
            self.assertIn("font-size:10pt", html)
            self.assertIn("Times New Roman", html)
            self.assertNotIn("border-left:", html)
            self.assertNotIn("border-right:", html)
            self.assertEqual(record["render"]["horizontal_rules"], 3)
            self.assertEqual(record["render"]["vertical_rules"], 0)
            self.assertEqual(record["render"]["font_points"], 10)

    def test_new_figures_and_archived_predecessors_have_distinct_bindings(self):
        inventory = read("configs/manuscript_inventory.json")
        for key in ["S8", "S9"]:
            record = inventory["figures"][key]
            self.assertEqual(record["panels"], list("ABCD"))
            self.assertEqual(record["scored_inputs"], "data/frozen/astra_prompt_controls_results_20261115/manifest.json")
            self.assertNotIn(key, inventory["archived_figure_ids"])
        archive = read("archive/reviewer47_publication_before_20261111/artwork_index.json")
        for entry in archive["entries"]:
            self.assertEqual(sha(ROOT / entry["archive_path"]), entry["sha256"])
        # The current native export must match its publication inventory.
        self.assertEqual(sha(ROOT / "figures/manuscript/Figure_4.png"), inventory["figures"]["4"]["images"][0]["sha256"])
        self.assertEqual(sha(ROOT / "figures/manuscript/Figure_S6.png"), inventory["figures"]["S6"]["images"][0]["sha256"])


if __name__ == "__main__":
    unittest.main()
