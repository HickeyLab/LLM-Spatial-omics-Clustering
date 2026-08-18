"""Guard the current supplementary-figure numbering and notebook ownership."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FINAL_NOTEBOOKS = REPOSITORY_ROOT / "notebooks" / "final_figures"
SUPPORTING_NOTEBOOKS = REPOSITORY_ROOT / "notebooks" / "supplementary"


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

    def test_supporting_s3_contract_uses_current_numbering(self) -> None:
        current_paths = (
            REPOSITORY_ROOT / "configs" / "figure_s03.yaml",
            REPOSITORY_ROOT / "docs" / "figure_s03.md",
            REPOSITORY_ROOT / "requirements-figure-s03.txt",
            REPOSITORY_ROOT / "src" / "llm_spatial_omics_clustering" / "figure_s03.py",
            REPOSITORY_ROOT / "tests" / "test_figure_s03.py",
            SUPPORTING_NOTEBOOKS / "figure_s03_clustering_inputs_and_diagnostics.ipynb",
        )
        obsolete_paths = (
            REPOSITORY_ROOT / "configs" / "figure_s01.yaml",
            REPOSITORY_ROOT / "docs" / "figure_s01.md",
            REPOSITORY_ROOT / "requirements-figure-s01.txt",
            REPOSITORY_ROOT / "src" / "llm_spatial_omics_clustering" / "figure_s01.py",
            REPOSITORY_ROOT / "tests" / "test_figure_s01.py",
            SUPPORTING_NOTEBOOKS / "figure_s01_clustering_inputs_and_diagnostics.ipynb",
        )
        for path in current_paths:
            self.assertTrue(path.is_file(), path)
        for path in obsolete_paths:
            self.assertFalse(path.exists(), path)

        notebook_path = current_paths[-1]
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["metadata"]["figure_id"], "figure_s03")
        self.assertEqual(notebook["metadata"]["notebook_role"], "supporting_panel_runner")
        self.assertEqual(
            notebook["metadata"]["canonical_notebook"],
            "notebooks/final_figures/figure_s03_clustering_inputs_and_diagnostics.ipynb",
        )
        source = "\n".join(
            "".join(cell.get("source", [])) for cell in notebook["cells"]
        )
        for panel_letter in "ABCDE":
            self.assertIn(f"Supplementary Figure S3{panel_letter}", source)
        self.assertIn("llm_spatial_omics_clustering.figure_s03", source)
        self.assertNotIn("llm_spatial_omics_clustering.figure_s01", source)
        self.assertNotIn("Supplementary Figure 1", source)
        self.assertNotIn("/Users/", notebook_path.read_text(encoding="utf-8"))

    def test_map_documents_all_current_supplementary_figures(self) -> None:
        figure_map = (REPOSITORY_ROOT / "docs" / "figure_map.md").read_text()
        final_readme = (FINAL_NOTEBOOKS / "README.md").read_text()
        for figure_number in range(1, 5):
            label = f"S{figure_number}"
            self.assertIn(label, figure_map)
            self.assertIn(f"figure_s0{figure_number}_", final_readme)


if __name__ == "__main__":
    unittest.main()
