import unittest

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


if __name__ == "__main__":
    unittest.main()
