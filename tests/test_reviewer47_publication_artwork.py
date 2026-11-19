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
    def test_representation_matrix_retains_the_pending_planned_condition(self):
        rows = figures.complete_sets()
        self.assertEqual(len(rows), 69)
        pending = rows[rows.status.eq("pending")]
        self.assertEqual(pending[["family", "method", "arm"]].values.tolist(),
                         [["deepseek", "leiden", "selected_means"]])
        self.assertTrue(pending[["agreement", "fixed28_macro_f1"]].isna().all().all())
        matrix = figures.representation_matrix(rows, "deepseek")
        self.assertTrue(np.isnan(matrix[0, 1]))
        self.assertEqual(int(np.isfinite(matrix).sum()), 15)

    def test_partial_accuracy_is_rejected_before_plotting(self):
        rows = figures.complete_sets()
        rows.loc[rows.status.eq("pending"), "agreement"] = .99
        with patch.object(figures, "table", return_value=rows):
            with self.assertRaisesRegex(ValueError, "partial accuracy"):
                figures.complete_sets()

    def test_only_complete_opus_controls_are_plotted(self):
        rows = figures.control_rows()
        self.assertTrue(rows[rows.arm.isin(["method_named", "neighborhood"])].status.eq("complete").all())
        self.assertEqual(set(rows.family), {"anthropic"})
        pending = read("data/frozen/reviewer47_results_20261111/pending_dependencies.json")
        self.assertEqual(pending["astra_extension"]["planned_request_items"], 8)
        self.assertEqual(pending["astra_extension"]["status"], "pending")

    def test_native_table_rows_and_covariates_are_preserved(self):
        original = read("docs/tables/ieee/source_tables.json")["tables"]
        snapshot = read("docs/tables/ieee_reviewer47_20261111/source_tables.json")["tables"]
        for key in ["S6a", "S6b", "S6c"]:
            self.assertEqual([r[:2] for r in snapshot[key]["rows"][1:]],
                             [r[:2] for r in original[key]["rows"][1:]])
        self.assertIn("Means + fractions macro-F1", snapshot["S6b"]["rows"][0])
        deep = snapshot["S8d"]["rows"]
        selected = next(r for r in deep[1:] if r[:2] == ["Leiden", "Selected means"])
        self.assertEqual(selected[2:4], ["Pending", "Pending"])
        self.assertEqual(selected[4], "225/300")

        current = read("docs/tables/ieee_reviewer47_20261119/source_tables.json")["tables"]
        self.assertNotIn("S6b", current)
        self.assertNotIn("S6c", current)
        deep = current["S8d"]["rows"]
        selected = next(r for r in deep[1:] if r[:2] == ["Leiden", "Selected marker means"])
        self.assertEqual(selected[2:], ["41.42", "0.3576"])
        self.assertIn("Standard streaming and Batch", current["S6d"]["rows"][-1])
        self.assertEqual(current["S9"]["rows"][-2:], [
            ["Leiden–Astra", "Method name", "58.12", "53.53", "-4.59", "40"],
            ["Leiden–Astra", "Neighborhood", "58.12", "51.43", "-6.69", "39"],
        ])

    def test_export_hashes_and_ieee_style(self):
        for date in ("20261111", "20261119"):
            folder = ROOT / f"docs/tables/ieee_reviewer47_{date}"
            manifest = read(folder / "manifest.json")
            self.assertEqual(len(manifest["tables"]), 15)
            for key, record in manifest["tables"].items():
                for suffix, entry in record["files"].items():
                    self.assertEqual(sha(folder / (key + suffix)), entry["sha256"])
                self.assertEqual(sha(folder / record["csv_companion"]["path"]), record["csv_companion"]["sha256"])
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
            self.assertEqual(record["scored_inputs"], "data/frozen/reviewer47_results_20261111/manifest.json")
            self.assertNotIn(key, inventory["archived_figure_ids"])
        archive = read("archive/reviewer47_publication_before_20261111/artwork_index.json")
        for entry in archive["entries"]:
            self.assertEqual(sha(ROOT / entry["archive_path"]), entry["sha256"])
        for key in ["4", "S6"]:
            image = inventory["figures"][key]["images"][0]
            receipt = read(f"figures/publication/Figure_{key}_verification.json")
            self.assertEqual(sha(ROOT / image["path"]), image["sha256"])
            self.assertEqual(image["sha256"], receipt["files"][f"Figure_{key}.png"]["sha256"])


if __name__ == "__main__":
    unittest.main()
