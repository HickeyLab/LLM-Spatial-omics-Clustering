import unittest
from pathlib import Path

from llm_spatial_omics_clustering.final_figures_runtime import clustering, metrics


class FinalFiguresRuntimeTests(unittest.TestCase):
    def test_clustering_runner_contract_is_available(self):
        required = {
            "run_leiden",
            "run_flowsom",
            "run_spatialsort",
            "run_tiff_pixie",
            "validate_tiff_mask_correspondence",
        }
        self.assertTrue(required.issubset(vars(clustering)))

    def test_settings_defaults_are_deterministic(self):
        self.assertEqual(clustering.LeidenSettings().seed, 42)
        self.assertEqual(clustering.FlowSOMSettings().seed, 42)
        self.assertEqual(clustering.SpatialSortSettings().seed, 42)
        self.assertEqual(clustering.PixieSettings().seed, 42)

    def test_key_contract_is_unchanged(self):
        self.assertEqual(metrics.KEY_COLUMNS, ("File_ID", "ID"))

    def test_runtime_namespace_is_neutral_and_uses_fresh_cache_names(self):
        runtime_root = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "llm_spatial_omics_clustering"
            / "final_figures_runtime"
        )
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(runtime_root.glob("*.py"))
        ).casefold()
        self.assertNotIn("v2", source)
        self.assertNotIn("reproduction_v2", source)
        self.assertIn("final_figures.pixie_prefix_cache.v1", source)
        self.assertIn("final_figures_pixie_prefix_cache", source)
        self.assertIn("prefix_manifest.json", source)
        self.assertNotIn("v2_prefix_manifest.json", source)
        cache_root = clustering._default_pixie_prefix_cache_root(
            Path("/tmp/final_figures_output/runs/pixie_candidate")
        )
        self.assertEqual(
            cache_root,
            Path("/tmp/final_figures_output/final_figures_pixie_prefix_cache").resolve(),
        )

    def test_final_source_notebooks_acquire_hubmap_tiffs_without_a_mode_switch(self):
        notebook_root = Path(__file__).resolve().parents[1] / "notebooks" / "final_figures"
        notebooks = sorted(notebook_root.glob("figure_*.ipynb"))
        active = [path for path in notebooks if path.name != "figure_01_redsea_spillover_correction.ipynb"]
        self.assertEqual(len(active), 5)
        for path in active:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("SOURCE_REBUILD_TIFF_MODE", source, path.name)
            self.assertNotIn("TIFF_MODE =", source, path.name)
            self.assertIn("download_b004_hubmap_tiff_pairs", source, path.name)
            self.assertIn("HUBMAP_TIFF_DOWNLOAD = download_b004_hubmap_tiff_pairs", source, path.name)
            self.assertIn("validate_hubmap_tiff_cache", source, path.name)
            self.assertIn("final_figures_runtime.hubmap import B004_FILE_IDS", source, path.name)
            self.assertNotIn("768b7adb649959b6b7b8741c282677eef", source, path.name)


if __name__ == "__main__":
    unittest.main()
