"""Contract checks for the Figure 2 Panel B through J implementations."""

import unittest

from llm_spatial_omics_clustering.figure_02 import (
    load_b004_h5ad,
    load_figure_config,
    load_panel_b_distribution,
    load_panel_c_spatial_data,
    load_panel_e_metrics,
    load_panel_fh_metrics,
    load_panel_g_metrics,
    resolve_data_root,
)


class Figure02ContractTests(unittest.TestCase):
    def test_figure_02_config_declares_b004_panel_b_and_exact_cluster_counts(self) -> None:
        config = load_figure_config()
        panel_b = config["panel_b"]
        panel_c = config["panel_c"]
        panel_d = config["panel_d"]
        panel_e = config["panel_e"]
        self.assertEqual(panel_b["cohort"], panel_d["cohort"])
        self.assertEqual(panel_b["cohort"]["donor_label"], "B004")
        self.assertEqual(panel_b["status"], "executed")
        self.assertEqual(len(panel_b["cohort"]["file_ids"]), 8)
        self.assertEqual(panel_b["cohort"]["expected_cells"], 220082)
        self.assertEqual(sum(panel_b["cohort"]["expected_cells_by_file_id"].values()), 220082)
        self.assertEqual(panel_b["labels"]["excluded_labels"], ["Noise"])
        self.assertEqual(panel_b["labels"]["expected_label_count"], 27)
        self.assertEqual(panel_b["labels"]["expected_included_cells"], 209587)
        self.assertEqual(panel_b["labels"]["expected_excluded_counts"], {"Noise": 10495})
        self.assertEqual(len(panel_b["labels"]["expected_counts"]), 27)
        self.assertEqual(
            panel_b["data"]["h5ad_sha256"],
            "a159bbeca2a4dd84dc265929d3b1d409c16be5e00a2f9819c012b8a5879c37e0",
        )
        self.assertEqual(panel_b["data"]["h5ad_sha256"], panel_d["data"]["h5ad_sha256"])
        self.assertEqual(panel_c["status"], "executed")
        self.assertEqual(panel_c["region"]["donor_label"], "B004")
        self.assertEqual(
            panel_c["region"]["file_id"], "8da8f27977d946b8c912d42c8827b55c"
        )
        self.assertEqual(panel_c["region"]["source_slide_name"], "B004-A-404")
        self.assertEqual(panel_c["region"]["expected_cells"], 36464)
        self.assertEqual(panel_c["labels"]["truth_column"], "cell_type_update")
        self.assertEqual(panel_c["labels"]["expected_label_count"], 27)
        self.assertEqual(panel_c["labels"]["expected_counts"]["Noise"], 3202)
        self.assertEqual(panel_c["coordinates"]["columns"], ["x", "y"])
        self.assertEqual(panel_c["coordinates"]["expected_bounds"]["x"], [301.0, 9509.0])
        self.assertEqual(panel_c["coordinates"]["expected_bounds"]["y"], [13.0, 9985.0])
        self.assertEqual(panel_c["data"]["h5ad_sha256"], panel_b["data"]["h5ad_sha256"])
        self.assertEqual(panel_d["features"]["expected_total_markers"], 48)
        self.assertEqual(
            {
                name: spec["expected_clusters"]
                for name, spec in panel_d["clustering_methods"].items()
            },
            {"leiden": 55, "flowsom": 300, "spatialsort": 60, "pixie": 50},
        )
        self.assertEqual(panel_e["status"], "executed")
        self.assertEqual(panel_e["cohort"], panel_d["cohort"])
        self.assertEqual(panel_e["clustering_source_panel"], "panel_d")
        self.assertEqual(
            [method["label"] for method in panel_e["methods"]],
            ["FlowSOM", "Leiden", "SpatialSort", "PIXIE"],
        )
        self.assertEqual(panel_e["evaluation"]["excluded_labels"], ["Noise"])
        self.assertEqual(panel_e["evaluation"]["expected_evaluation_cells"], 209587)
        self.assertEqual(panel_e["evaluation"]["expected_evaluation_class_count"], 20)
        self.assertEqual(len(panel_e["expected_scores"]), 8)
        self.assertEqual(
            panel_e["expected_scores"]["2e65eeef2dd18bee2a0baf1cec6d35a1"]["PIXIE"],
            0.6501438844622639,
        )

    def test_panel_b_distribution_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config, panel_key="panel_b")
        except FileNotFoundError:
            self.skipTest(
                "Local H5AD is not available; set CELL_MASKS_DATA_ROOT to run this integration check."
            )
        distribution = load_panel_b_distribution(config, data_root=data_root)
        self.assertEqual(distribution.source_cell_count, 220082)
        self.assertEqual(int(distribution.counts["Cell Count"].sum()), 209587)
        self.assertEqual(distribution.excluded_counts, {"Noise": 10495})
        self.assertEqual(len(distribution.counts), 27)
        self.assertTrue(distribution.counts["Cell Count"].is_monotonic_decreasing)
        self.assertEqual(
            distribution.counts.iloc[0].to_dict(),
            {"Cell Type": "Epithelial", "Cell Count": 30833},
        )
        self.assertEqual(
            distribution.counts.iloc[-1].to_dict(),
            {"Cell Type": "NK", "Cell Count": 174},
        )

    def test_panel_c_spatial_data_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config, panel_key="panel_c")
        except FileNotFoundError:
            self.skipTest(
                "Local H5AD is not available; set CELL_MASKS_DATA_ROOT to run this integration check."
            )
        data = load_panel_c_spatial_data(config, data_root=data_root)
        self.assertEqual(data.source_cell_count, 36464)
        self.assertEqual(len(data.cells), 36464)
        self.assertEqual(data.cells["File_ID"].nunique(), 1)
        self.assertEqual(data.cells["File_ID"].iloc[0], "8da8f27977d946b8c912d42c8827b55c")
        self.assertEqual(data.cells[["File_ID", "ID"]].duplicated().sum(), 0)
        self.assertEqual(data.cell_type_counts["Noise"], 3202)
        self.assertEqual(len(data.cell_type_counts), 27)
        self.assertEqual((float(data.cells["x"].min()), float(data.cells["x"].max())), (301.0, 9509.0))
        self.assertEqual((float(data.cells["y"].min()), float(data.cells["y"].max())), (13.0, 9985.0))

    def test_b004_h5ad_contract_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config)
        except FileNotFoundError:
            self.skipTest(
                "Local H5AD is not available; set CELL_MASKS_DATA_ROOT to run this integration check."
            )
        data = load_b004_h5ad(config, data_root=data_root)
        self.assertEqual(len(data.cells), 220082)
        self.assertEqual(data.features.shape, (220082, 48))
        self.assertEqual(data.cells[["File_ID", "ID"]].duplicated().sum(), 0)

    def test_panel_e_metrics_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config, panel_key="panel_e")
        except FileNotFoundError:
            self.skipTest(
                "Local H5AD is not available; set CELL_MASKS_DATA_ROOT to run this integration check."
            )
        data = load_panel_e_metrics(config, data_root=data_root)
        self.assertEqual(data.source_cell_count, 220082)
        self.assertEqual(data.evaluation_cell_count, 209587)
        self.assertEqual(data.excluded_counts, {"Noise": 10495})
        self.assertEqual(data.evaluation_class_count, 20)
        self.assertEqual(
            data.cluster_counts,
            {"flowsom": 300, "leiden": 55, "spatialsort": 60, "pixie": 50},
        )
        self.assertEqual(data.scores.shape, (32, 4))
        pixie_region = data.scores.loc[
            (data.scores["region"] == "2e65eeef2dd18bee2a0baf1cec6d35a1")
            & (data.scores["method"] == "PIXIE"),
            "weighted_f1",
        ].iloc[0]
        self.assertAlmostEqual(pixie_region, 0.6501438844622639, places=12)

    def test_panel_f_to_j_config_contract(self) -> None:
        config = load_figure_config()
        expected_method_order = ["FlowSOM", "Leiden", "SpatialSort", "PIXIE"]
        for panel_key in ("panel_f", "panel_g", "panel_h"):
            panel = config[panel_key]
            self.assertEqual(panel["data_source_panel"], "panel_e")
            self.assertEqual(panel["cohort_source_panel"], "panel_d")
            self.assertEqual(panel["clustering_source_panel"], "panel_d")
            self.assertEqual(panel["evaluation_source_panel"], "panel_e")
            self.assertEqual(
                [method["label"] for method in panel["methods"]], expected_method_order
            )
        self.assertEqual(len(config["panel_f"]["row_order"]), 20)
        self.assertEqual(len(config["panel_h"]["row_order"]), 20)
        self.assertEqual(config["panel_i"]["expected_marker_count"], 45)
        self.assertEqual(
            [method["label"] for method in config["panel_i"]["methods"]],
            ["Leiden", "FlowSOM", "SpatialSort", "PIXIE"],
        )
        self.assertEqual(config["panel_j"]["excluded_labels"], ["Noise"])
        self.assertEqual(
            [example["name"] for example in config["panel_j"]["examples"]],
            ["Low Agreement", "High Agreement"],
        )
        self.assertEqual(config["panel_j"]["examples"][0]["expected_cells"], 1091)
        self.assertEqual(config["panel_j"]["examples"][1]["expected_cells"], 1041)

    def test_panels_fgh_metrics_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config, panel_key="panel_f")
        except FileNotFoundError:
            self.skipTest(
                "Local H5AD is not available; set CELL_MASKS_DATA_ROOT to run this integration check."
            )
        panel_f = load_panel_fh_metrics(config, panel_key="panel_f", data_root=data_root)
        panel_h = load_panel_fh_metrics(config, panel_key="panel_h", data_root=data_root)
        panel_g = load_panel_g_metrics(config, data_root=data_root)
        self.assertEqual(panel_f.metrics.shape[0], 20)
        self.assertEqual(panel_h.metrics.shape[0], 20)
        self.assertEqual(panel_f.evaluation_cell_count, 209587)
        self.assertEqual(panel_h.evaluation_cell_count, 209587)
        self.assertEqual(panel_g.scores.shape, (32, 4))
        pixie_f1 = panel_f.metrics.loc[
            panel_f.metrics["cell_type"].eq("Smooth muscle"), "PIXIE_f1"
        ].iloc[0]
        self.assertAlmostEqual(pixie_f1, 0.824893918, places=8)
        pixie_purity = panel_h.metrics.loc[
            panel_h.metrics["cell_type"].eq("Smooth muscle"), "PIXIE_purity"
        ].iloc[0]
        self.assertAlmostEqual(pixie_purity, 0.901514891, places=8)
        pixie_g = panel_g.scores.loc[
            (panel_g.scores["region"] == "76d3efd17b6fc83aaac13e961824c5ae")
            & (panel_g.scores["method"] == "PIXIE"),
            "cell_purity",
        ].iloc[0]
        self.assertAlmostEqual(pixie_g, 0.60998537, places=8)
