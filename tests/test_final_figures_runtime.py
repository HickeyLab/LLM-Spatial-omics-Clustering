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


if __name__ == "__main__":
    unittest.main()
