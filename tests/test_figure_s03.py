"""Contract and local-data checks for Supplementary Figure S3, Panels A--E."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from llm_spatial_omics_clustering.figure_02 import (
    load_figure_config as load_figure_02_config,
)
from llm_spatial_omics_clustering.figure_s03 import (
    build_panel_a_summary,
    build_panel_c_composition,
    build_panel_e_metrics,
    load_figure_config,
    load_inputs,
    load_panel_d_sweep,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class FigureS03ContractTests(unittest.TestCase):
    def test_frozen_sweep_lookup_never_downloads_the_duke_h5ad(self) -> None:
        with patch(
            "llm_spatial_omics_clustering.figure_02.resolve_data_root",
            side_effect=FileNotFoundError("local data unavailable"),
        ) as resolve_data_root:
            with self.assertRaisesRegex(FileNotFoundError, "local data unavailable"):
                load_panel_d_sweep(repository_root=REPOSITORY_ROOT)

        resolve_data_root.assert_called_once()
        self.assertEqual(
            resolve_data_root.call_args.kwargs,
            {"download_if_missing": False},
        )

    def test_config_locks_panel_map_and_current_figure_02_assignments(self) -> None:
        config = load_figure_config()
        dependency = config["figure_02_dependency"]

        self.assertEqual(config["supplementary_figure"], 3)
        self.assertTrue(str(config["working_title"]).startswith("VERIFY:"))
        self.assertEqual(dependency["expected_source_cells"], 220082)
        self.assertEqual(dependency["expected_non_noise_cells"], 209587)
        self.assertEqual(dependency["excluded_label"], "Noise")
        self.assertEqual(dependency["expected_raw_label_count_including_noise"], 28)
        self.assertEqual(dependency["expected_raw_label_count_excluding_noise"], 27)
        self.assertEqual(
            dependency["expected_methods"],
            {"leiden": 55, "flowsom": 300, "spatialsort": 60, "pixie": 50},
        )
        self.assertEqual(
            [list(spec) for spec in dependency["method_order"]],
            [
                ["leiden", "Leiden"],
                ["flowsom", "FlowSOM"],
                ["spatialsort", "SpatialSort"],
                ["pixie", "PIXIE"],
            ],
        )

        self.assertEqual(len(config["panel_a"]["cell_type_order"]), 27)
        self.assertEqual(len(config["panel_a"]["marker_order"]), 45)
        self.assertEqual(config["panel_a"]["expression_threshold"], 0.0)
        self.assertEqual(len(config["panel_b"]["file_id_order"]), 8)
        self.assertEqual(len(config["panel_c"]["cell_type_order"]), 28)
        self.assertEqual(config["panel_c"]["displayed_cluster_limit"], {"flowsom": 60})
        self.assertEqual(len(config["panel_d"]["expected_rows"]), 8)
        self.assertTrue(str(config["panel_d"]["provenance_status"]).startswith("VERIFY:"))

        metric_contract = {
            str(metric["key"]): str(metric["grain"])
            for metric in config["panel_e"]["metrics"]
        }
        self.assertEqual(
            metric_contract,
            {
                "adjusted_rand_index": "region",
                "adjusted_mutual_information": "region",
                "shannon_index": "cluster",
                "f1_score": "cell_type",
                "recall": "cell_type",
                "purity_percent": "cluster",
            },
        )
        self.assertNotIn("silhouette", metric_contract)

        for panel_key in ("panel_a", "panel_b", "panel_c", "panel_d", "panel_e"):
            for output_path in config[panel_key]["outputs"].values():
                self.assertTrue(
                    str(output_path).startswith("outputs/supplementary/figure_s03/")
                )

        figure_02_config = load_figure_02_config(
            REPOSITORY_ROOT / str(dependency["config_path"])
        )
        pixie_contract = figure_02_config["panel_d"]["clustering_methods"]["pixie"]
        self.assertEqual(pixie_contract["expected_clusters"], 50)
        self.assertEqual(
            pixie_contract["assignment_filename"],
            "data/processed/figure_02/pixie_tiff_methods_50/master_pixie_clusters.csv",
        )
        self.assertEqual(
            pixie_contract["parameters"]["input"],
            "paired 48-channel OME-TIFF expression images and integer cell masks",
        )

    def test_five_cell_notebook_and_frozen_panel_d_sweep(self) -> None:
        notebook_path = (
            REPOSITORY_ROOT
            / "notebooks/supplementary/figure_s03_clustering_inputs_and_diagnostics.ipynb"
        )
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        self.assertEqual(len(notebook["cells"]), 5)
        self.assertEqual(
            [cell["cell_type"] for cell in notebook["cells"]],
            ["code"] * 5,
        )
        self.assertEqual(
            [cell["execution_count"] for cell in notebook["cells"]],
            [1, 2, 3, 4, 5],
        )
        errors = [
            output
            for cell in notebook["cells"]
            for output in cell.get("outputs", [])
            if output.get("output_type") == "error"
        ]
        self.assertEqual(errors, [])
        for panel_letter, cell in zip("abcde", notebook["cells"], strict=True):
            source = "".join(cell["source"])
            self.assertIn(f"run_panel_{panel_letter}", source)

        try:
            sweep, source_path = load_panel_d_sweep(repository_root=REPOSITORY_ROOT)
        except FileNotFoundError:
            self.skipTest(
                "The local frozen FlowSOM sweep is unavailable; "
                "set CELL_MASKS_DATA_ROOT to its containing directory."
            )
        self.assertTrue(source_path.is_file())
        self.assertEqual(sweep.shape, (8, 3))
        self.assertEqual(int(sweep.iloc[0]["k"]), 10)
        self.assertEqual(int(sweep.iloc[0]["effective_k"]), 10)
        self.assertTrue(
            np.isclose(float(sweep.iloc[0]["purity"]), 0.37564634999681934)
        )
        self.assertEqual(int(sweep.iloc[-1]["k"]), 350)
        self.assertEqual(int(sweep.iloc[-1]["effective_k"]), 324)
        self.assertTrue(np.isclose(float(sweep.iloc[-1]["purity"]), 0.4931889023182268))

    def test_panels_a_c_e_when_local_figure_02_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            inputs = load_inputs(
                repository_root=REPOSITORY_ROOT,
                download_if_missing=False,
            )
        except FileNotFoundError:
            self.skipTest(
                "Local Figure 2 H5AD or assignments are unavailable; "
                "set CELL_MASKS_DATA_ROOT to run this integration check."
            )

        self.assertEqual(inputs.source_cell_count, 220082)
        self.assertEqual(inputs.non_noise_cell_count, 209587)
        self.assertEqual(inputs.expression.shape, (220082, 45))
        self.assertEqual(len(inputs.marker_names), 45)
        self.assertEqual(inputs.cells[["File_ID", "ID"]].duplicated().sum(), 0)
        self.assertEqual(inputs.cells["File_ID"].nunique(), 8)
        self.assertEqual(inputs.cells["cell_type_update"].nunique(), 28)
        self.assertEqual(
            int(inputs.cells["cell_type_update"].eq("Noise").sum()),
            10495,
        )
        self.assertEqual(
            inputs.cluster_counts,
            {"leiden": 55, "flowsom": 300, "spatialsort": 60, "pixie": 50},
        )

        panel_a = build_panel_a_summary(inputs, config)
        self.assertEqual(panel_a.shape, (27 * 45, 8))
        self.assertEqual(panel_a["cell_type"].nunique(), 27)
        self.assertEqual(panel_a["marker"].nunique(), 45)
        self.assertEqual(
            int(panel_a.groupby("cell_type")["n_cells"].first().sum()),
            209587,
        )
        self.assertTrue(panel_a["fraction_positive"].between(0.0, 1.0).all())
        self.assertTrue(
            panel_a["marker_scaled_mean_expression"].between(0.0, 1.0).all()
        )

        panel_c = build_panel_c_composition(inputs, config)
        self.assertEqual(panel_c.shape, (6309, 9))
        self.assertEqual(
            panel_c.groupby("method_key").size().to_dict(),
            {"flowsom": 3458, "leiden": 883, "pixie": 1066, "spatialsort": 902},
        )
        self.assertEqual(
            panel_c.groupby("method_key")["cluster"].nunique().to_dict(),
            {"flowsom": 300, "leiden": 55, "pixie": 50, "spatialsort": 60},
        )
        self.assertEqual(
            panel_c.groupby("method_key")["cell_count"].sum().to_dict(),
            {
                "flowsom": 220082,
                "leiden": 220082,
                "pixie": 220082,
                "spatialsort": 220082,
            },
        )

        panel_e = build_panel_e_metrics(inputs, config)
        self.assertEqual(panel_e.shape, (1210, 10))
        self.assertEqual(
            panel_e.groupby("metric").size().to_dict(),
            {
                "adjusted_mutual_information": 32,
                "adjusted_rand_index": 32,
                "f1_score": 108,
                "purity_percent": 465,
                "recall": 108,
                "shannon_index": 465,
            },
        )
        pixie_medians = (
            panel_e.loc[panel_e["method_key"].eq("pixie")]
            .groupby("metric")["value"]
            .median()
        )
        expected_pixie_medians = {
            "adjusted_rand_index": 0.36246387565561256,
            "adjusted_mutual_information": 0.4787237976117945,
            "shannon_index": 1.6017005234958166,
            "f1_score": 0.0,
            "recall": 0.0,
            "purity_percent": 49.58060216120221,
        }
        self.assertEqual(set(pixie_medians.index), set(expected_pixie_medians))
        for metric, expected in expected_pixie_medians.items():
            with self.subTest(metric=metric):
                self.assertTrue(
                    np.isclose(
                        float(pixie_medians.loc[metric]),
                        expected,
                        rtol=0.0,
                        atol=1e-10,
                    )
                )


if __name__ == "__main__":
    unittest.main()
