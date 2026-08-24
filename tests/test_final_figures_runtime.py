import json
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

    def test_final_source_notebooks_use_frozen_assignments_without_tiff_download(self):
        notebook_root = Path(__file__).resolve().parents[1] / "notebooks" / "final_figures"
        source_rebuild_names = (
            "figure_02_clustering_method_benchmark.ipynb",
            "figure_03_llm_annotation_benchmark.ipynb",
            "figure_04_leiden_gpt_end_to_end.ipynb",
            "figure_s03_clustering_inputs_and_diagnostics.ipynb",
            "figure_s04_annotation_diagnostics.ipynb",
        )
        active = [notebook_root / name for name in source_rebuild_names]
        self.assertEqual(len(active), 5)
        for path in active:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            source = "\n".join(
                "".join(cell.get("source", [])) for cell in notebook["cells"]
            )
            self.assertNotIn("SOURCE_REBUILD_TIFF_MODE", source, path.name)
            self.assertNotIn("TIFF_MODE =", source, path.name)
            self.assertNotIn("download_b004_hubmap_tiff_pairs", source, path.name)
            self.assertNotIn("validate_hubmap_tiff_cache", source, path.name)
            self.assertIn("SOURCE_REBUILD_ASSIGNMENTS_ROOT", source, path.name)
            self.assertIn("FROZEN_ASSIGNMENT_MANIFEST", source, path.name)
            self.assertIn("_load_frozen_assignments", source, path.name)
            self.assertIn(
                'EXPECTED_H5AD_SHA256 = "5d0a59d1e7866dee5a3a06772c3c80ce7328ba6420bc140708be5ec451b8a49"',
                source,
                path.name,
            )
            self.assertIn("observed_h5ad_sha256 = _sha256(h5ad_path)", source, path.name)
            self.assertIn("final_figures_runtime.hubmap import B004_FILE_IDS", source, path.name)
            self.assertNotIn("768b7adb649959b6b7b8741c282677eef", source, path.name)
            self.assertEqual(
                notebook["metadata"]["runtime_input_boundary"],
                "H5AD + tracked frozen K=300 assignments + OpenRouter API key or cached raw response bundles",
                path.name,
            )
            for cell in notebook["cells"]:
                if "input_boundary" in cell.get("metadata", {}):
                    self.assertEqual(
                        cell["metadata"]["input_boundary"],
                        "H5AD + tracked frozen K=300 assignments + OpenRouter API key or cached raw response bundles",
                        f"{path.name}:{cell.get('id')}",
                    )


if __name__ == "__main__":
    unittest.main()
