"""Contracts for the published Figure 1, S1, and S2 Duke inputs."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "configs" / "duke_record_565_manifest.json"
NOTEBOOK_ROOT = REPOSITORY_ROOT / "notebooks" / "final_figures"
NOTEBOOKS = (
    NOTEBOOK_ROOT / "figure_01_spillover_compensation.ipynb",
    NOTEBOOK_ROOT / "figure_s01_clustering_metrics.ipynb",
    NOTEBOOK_ROOT / "figure_s02_spatial_celltypes.ipynb",
)


class DukeRecord565ManifestTests(unittest.TestCase):
    def test_manifest_pins_the_exact_published_input_set(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "duke_research_repository_record_manifest.v1")
        self.assertEqual(manifest["record_url"], "https://research.repository.duke.edu/record/565")
        self.assertEqual(manifest["doi"], "10.7924/r4r565")
        self.assertEqual(manifest["version"], 1)
        self.assertEqual(manifest["checksum_algorithm"], "md5")

        files = manifest["files"]
        self.assertEqual(len(files), 13)
        filenames = {entry["filename"] for entry in files}
        self.assertEqual(len(filenames), 13)
        self.assertEqual(sum(entry["size_bytes"] for entry in files), 3_005_498_915)
        self.assertIn("20260130_HuBMAP_Yang_annotate_with_area.h5ad", filenames)
        self.assertEqual(
            len([name for name in filenames if name.endswith("beforeREDSEA_leiden.h5ad")]),
            6,
        )
        self.assertEqual(
            len([name for name in filenames if name.endswith("afterREDSEA_leiden.h5ad")]),
            6,
        )
        for entry in files:
            self.assertGreater(entry["size_bytes"], 0)
            self.assertRegex(entry["md5"], re.compile(r"^[0-9a-f]{32}$"))

    def test_manifest_covers_every_h5ad_named_by_the_three_notebooks(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        manifest_filenames = {entry["filename"] for entry in manifest["files"]}
        notebook_filenames: set[str] = set()
        for notebook_path in NOTEBOOKS:
            notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
            code_source = "\n".join(
                "".join(cell.get("source", []))
                for cell in notebook["cells"]
                if cell["cell_type"] == "code"
            )
            notebook_filenames.update(
                re.findall(
                    r"[A-Za-z0-9_]+\.h5ad",
                    code_source,
                )
            )
        self.assertEqual(notebook_filenames, manifest_filenames)

    def test_notebooks_use_the_repository_relative_published_layout(self) -> None:
        for notebook_path in NOTEBOOKS:
            notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
            serialized = json.dumps(notebook)
            opening_markdown = "".join(notebook["cells"][0]["source"])
            source_cell = notebook["cells"][3]
            source_code = "".join(source_cell["source"])

            with self.subTest(notebook=notebook_path.name):
                self.assertIn("https://research.repository.duke.edu/record/565", opening_markdown)
                self.assertIn('REPO_ROOT / "data" / "processed"', source_code)
                self.assertNotIn('"/data/processed', serialized)
                self.assertNotIn("/mnt/jwh83-data", serialized)
                self.assertIsNone(source_cell["execution_count"])
                self.assertIn("intentionally left unexecuted", opening_markdown)


if __name__ == "__main__":
    unittest.main()
