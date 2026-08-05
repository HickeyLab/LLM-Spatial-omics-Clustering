"""Contract checks for the Figure 2 Panel D implementation."""

import unittest

from llm_spatial_omics_clustering.figure_02 import (
    load_b004_h5ad,
    load_figure_config,
    resolve_data_root,
)


class Figure02PanelDContractTests(unittest.TestCase):
    def test_figure_02_config_declares_b004_and_exact_cluster_counts(self) -> None:
        config = load_figure_config()
        panel = config["panel_d"]
        self.assertEqual(panel["cohort"]["donor_label"], "B004")
        self.assertEqual(len(panel["cohort"]["file_ids"]), 8)
        self.assertEqual(panel["cohort"]["expected_cells"], 220082)
        self.assertEqual(sum(panel["cohort"]["expected_cells_by_file_id"].values()), 220082)
        self.assertEqual(panel["features"]["expected_total_markers"], 48)
        self.assertEqual(
            {
                name: spec["expected_clusters"]
                for name, spec in panel["clustering_methods"].items()
            },
            {"leiden": 55, "flowsom": 300, "spatialsort": 60, "pixie": 50},
        )

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
