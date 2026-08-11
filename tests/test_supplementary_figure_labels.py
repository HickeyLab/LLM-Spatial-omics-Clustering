"""Guard the current supplementary-figure numbering and notebook ownership."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FINAL_NOTEBOOKS = REPOSITORY_ROOT / "notebooks" / "final_figures"


class SupplementaryFigureLabelTests(unittest.TestCase):
    def test_current_notebooks_have_unique_numbered_paths(self) -> None:
        expected = {
            "figure_s01_clustering_metrics.ipynb": ("Figure S1", "Figure S01"),
            "figure_s02_spatial_celltypes.ipynb": ("Figure S2", "Figure S02"),
            "figure_s03_clustering_inputs_and_diagnostics.ipynb": ("Figure S3",),
            "figure_s04_annotation_diagnostics.ipynb": ("Figure S4",),
        }

        for filename, labels in expected.items():
            path = FINAL_NOTEBOOKS / filename
            self.assertTrue(path.is_file(), path)
            notebook = json.loads(path.read_text())
            source = "\n".join(
                "".join(cell.get("source", []))
                for cell in notebook.get("cells", [])
            )
            self.assertTrue(any(label in source for label in labels), path)

        self.assertFalse(
            (FINAL_NOTEBOOKS / "figure_s01_clustering_inputs_and_diagnostics.ipynb").exists()
        )
        self.assertFalse(
            (FINAL_NOTEBOOKS / "figure_s02_annotation_diagnostics.ipynb").exists()
        )

    def test_source_rebuild_metadata_matches_s3_and_s4(self) -> None:
        for figure_number in (3, 4):
            candidates = sorted(FINAL_NOTEBOOKS.glob(f"figure_s0{figure_number}_*.ipynb"))
            self.assertEqual(len(candidates), 1)
            notebook = json.loads(candidates[0].read_text())
            self.assertEqual(notebook["metadata"]["figure_id"], f"figure_s0{figure_number}")

    def test_map_documents_all_current_supplementary_figures(self) -> None:
        figure_map = (REPOSITORY_ROOT / "docs" / "figure_map.md").read_text()
        final_readme = (FINAL_NOTEBOOKS / "README.md").read_text()
        for figure_number in range(1, 5):
            label = f"S{figure_number}"
            self.assertIn(label, figure_map)
            self.assertIn(f"figure_s0{figure_number}_", final_readme)


if __name__ == "__main__":
    unittest.main()
