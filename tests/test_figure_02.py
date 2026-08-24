"""Contract checks for the Figure 2 Panel B through J implementations."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from llm_spatial_omics_clustering.figure_02 import (
    Figure02ValidationError,
    _load_four_llm_consensus_for_keys,
    _load_method_assignments_for_keys,
    _source_csv_sha256,
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
    def test_assignment_loader_validates_observed_not_configured_count(self) -> None:
        keys = pd.DataFrame({"File_ID": ["region", "region"], "ID": [1, 2]})
        method_config = {
            "assignment_filename": "leiden.csv",
            "assignment_column": "cluster",
            "configured_clusters": 300,
            "observed_clusters": 2,
            "selected_artifact_parameters": {},
        }
        with TemporaryDirectory() as temporary:
            data_root = Path(temporary)
            pd.DataFrame(
                {
                    "File_ID": ["region", "region"],
                    "ID": [1, 2],
                    "cluster": ["cluster_a", "cluster_b"],
                }
            ).to_csv(data_root / "leiden.csv", index=False)

            assignments = _load_method_assignments_for_keys(
                keys,
                {"leiden": method_config},
                data_root=data_root,
            )
            self.assertEqual(assignments["leiden"]["cluster"].nunique(), 2)

            method_config["observed_clusters"] = 3
            with self.assertRaisesRegex(
                Figure02ValidationError, "declared observed_clusters=3"
            ):
                _load_method_assignments_for_keys(
                    keys,
                    {"leiden": method_config},
                    data_root=data_root,
                )

    def test_figure_02_config_declares_b004_panel_b_and_cluster_contracts(self) -> None:
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
            "5d0a59d1e7866dee5a3a06772c3c80ce7328ba6420bc140708be5ec451b8a49",
        )
        self.assertEqual(panel_b["data"]["h5ad_filename"], "20260130_HuBMAP_experted_annotated.h5ad")
        self.assertTrue(panel_b["data"]["download"])
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
        self.assertEqual(panel_c["coordinates"]["expected_bounds"]["x"], [13.0, 9985.0])
        self.assertEqual(panel_c["coordinates"]["expected_bounds"]["y"], [301.0, 9509.0])
        self.assertEqual(panel_c["data"]["h5ad_sha256"], panel_b["data"]["h5ad_sha256"])
        self.assertEqual(panel_d["features"]["expected_total_markers"], 48)
        clustering_methods = panel_d["clustering_methods"]
        self.assertEqual(
            {
                name: spec["configured_clusters"]
                for name, spec in clustering_methods.items()
            },
            {"leiden": 300, "flowsom": 300, "spatialsort": 300, "pixie": 300},
        )
        self.assertEqual(
            {
                name: spec["observed_clusters"]
                for name, spec in clustering_methods.items()
            },
            {"leiden": 300, "flowsom": 300, "spatialsort": 246, "pixie": 300},
        )
        for method_config in clustering_methods.values():
            self.assertNotIn("expected_clusters", method_config)
            self.assertNotIn("parameters", method_config)
            self.assertIn("selected_artifact_parameters", method_config)
        self.assertEqual(
            {
                name: spec["assignment_filename"]
                for name, spec in clustering_methods.items()
            },
            {
                "leiden": "data/frozen/v3_k300_assignments/leiden/assignments.csv.gz",
                "flowsom": "data/frozen/v3_k300_assignments/flowsom/assignments.csv.gz",
                "spatialsort": (
                    "data/frozen/v3_k300_assignments/spatialsort/"
                    "master_spatialsort_clusters.csv.gz"
                ),
                "pixie": (
                    "data/frozen/v3_k300_assignments/pixie/"
                    "master_pixie_clusters.csv.gz"
                ),
            },
        )
        for method_config in clustering_methods.values():
            self.assertTrue(method_config["repository_artifact"])
            self.assertEqual(method_config["expected_rows"], 220082)
        pixie = clustering_methods["pixie"]
        self.assertEqual(pixie["observed_clusters"], 300)
        self.assertEqual(
            pixie["selected_artifact_parameters"]["cell_som_shape"], [24, 24]
        )
        self.assertEqual(
            pixie["selected_artifact_parameters"]["cell_metaclusters"], 300
        )
        self.assertEqual(
            pixie["selected_artifact_parameters"]["pixel_metaclusters"], 20
        )
        self.assertEqual(
            pixie["selected_artifact_parameters"]["pixel_som_sigma"], 5.0
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
            0.6755626737130034,
        )

    def test_data_root_rejects_a_same_named_h5ad_with_the_wrong_hash(self) -> None:
        environment_name = "FIGURE_02_TEST_DATA_ROOT"
        filename = "hash_contract_test.h5ad"
        with TemporaryDirectory() as temporary:
            data_root = Path(temporary)
            source_path = data_root / filename
            source_path.write_bytes(b"declared Figure 2 test source")
            declared_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
            config = {
                "panel_d": {
                    "data": {
                        "root_env": environment_name,
                        "h5ad_filename": filename,
                        "h5ad_sha256": declared_sha256,
                        "download": False,
                    }
                }
            }
            with patch.dict("os.environ", {environment_name: str(data_root)}):
                self.assertEqual(
                    resolve_data_root(config, download_if_missing=False), data_root.resolve()
                )
                config["panel_d"]["data"]["h5ad_sha256"] = "0" * 64
                with self.assertRaisesRegex(Figure02ValidationError, "declared h5ad_sha256"):
                    resolve_data_root(config, download_if_missing=False)

    def test_frozen_k300_assignments_and_four_llm_consensus_are_hash_locked(self) -> None:
        config = load_figure_config()
        frozen_root = Path(__file__).resolve().parents[1] / "data/frozen/v3_k300_assignments"
        manifest = json.loads((frozen_root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["schema_version"],
            "llm_spatial_omics_clustering.frozen_v3_k300_assignments.v1",
        )
        self.assertEqual(manifest["cohort"]["cells"], 220082)

        method_configs = config["panel_d"]["clustering_methods"]
        observed_counts = {
            "leiden": 300,
            "flowsom": 300,
            "spatialsort": 246,
            "pixie": 300,
        }
        keys = pd.read_csv(
            frozen_root / manifest["methods"]["leiden"]["path"],
            usecols=["File_ID", "ID"],
        )
        self.assertEqual(len(keys), 220082)
        self.assertEqual(int(keys.duplicated(["File_ID", "ID"]).sum()), 0)
        assignments = _load_method_assignments_for_keys(
            keys,
            method_configs,
            data_root=frozen_root,
        )
        self.assertEqual(
            {
                method: int(frame["cluster"].nunique())
                for method, frame in assignments.items()
            },
            observed_counts,
        )
        for method, method_manifest in manifest["methods"].items():
            artifact = frozen_root / method_manifest["path"]
            config_contract = method_configs[method]
            self.assertEqual(config_contract["configured_clusters"], 300)
            self.assertEqual(config_contract["observed_clusters"], observed_counts[method])
            self.assertEqual(
                config_contract["source_csv_sha256"],
                method_manifest["source_csv_sha256"],
            )
            self.assertEqual(
                _source_csv_sha256(artifact),
                method_manifest["source_csv_sha256"],
            )
            self.assertEqual(
                hashlib.sha256(artifact.read_bytes()).hexdigest(),
                method_manifest["gzip_sha256"],
            )

        consensus_config = config["four_llm_consensus"]
        consensus_manifest = manifest["four_llm_consensus"]
        consensus_path = frozen_root / consensus_manifest["path"]
        self.assertEqual(
            consensus_config["assignment_filename"],
            "data/frozen/v3_k300_assignments/panel_i_j_four_llm_consensus.csv.gz",
        )
        self.assertEqual(consensus_config["expected_rows"], 220082)
        self.assertEqual(
            consensus_config["models_in_tie_order"],
            ["GPT", "Claude", "Gemini", "DeepSeek"],
        )
        self.assertEqual(
            consensus_config["source_annotations_sha256"],
            consensus_manifest["source_annotations_sha256"],
        )
        self.assertEqual(
            consensus_config["source_csv_sha256"],
            consensus_manifest["derived_source_csv_sha256"],
        )
        self.assertEqual(
            _source_csv_sha256(consensus_path),
            consensus_manifest["derived_source_csv_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(consensus_path.read_bytes()).hexdigest(),
            consensus_manifest["gzip_sha256"],
        )
        consensus = _load_four_llm_consensus_for_keys(keys, config)
        self.assertEqual(consensus.shape, (220082, 6))
        self.assertFalse(consensus.isna().any().any())

    def test_panel_b_distribution_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config, panel_key="panel_b", download_if_missing=False)
        except FileNotFoundError:
            self.skipTest(
                "Duke H5AD cache is not available; run the downloader to run this integration check."
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
            data_root = resolve_data_root(config, panel_key="panel_c", download_if_missing=False)
        except FileNotFoundError:
            self.skipTest(
                "Duke H5AD cache is not available; run the downloader to run this integration check."
            )
        data = load_panel_c_spatial_data(config, data_root=data_root)
        self.assertEqual(data.source_cell_count, 36464)
        self.assertEqual(len(data.cells), 36464)
        self.assertEqual(data.cells["File_ID"].nunique(), 1)
        self.assertEqual(data.cells["File_ID"].iloc[0], "8da8f27977d946b8c912d42c8827b55c")
        self.assertEqual(data.cells[["File_ID", "ID"]].duplicated().sum(), 0)
        self.assertEqual(data.cell_type_counts["Noise"], 3202)
        self.assertEqual(len(data.cell_type_counts), 27)
        self.assertEqual((float(data.cells["x"].min()), float(data.cells["x"].max())), (13.0, 9985.0))
        self.assertEqual((float(data.cells["y"].min()), float(data.cells["y"].max())), (301.0, 9509.0))

    def test_b004_h5ad_contract_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config, download_if_missing=False)
        except FileNotFoundError:
            self.skipTest(
                "Duke H5AD cache is not available; run the downloader to run this integration check."
            )
        data = load_b004_h5ad(config, data_root=data_root)
        self.assertEqual(len(data.cells), 220082)
        self.assertEqual(data.features.shape, (220082, 48))
        self.assertEqual(data.cells[["File_ID", "ID"]].duplicated().sum(), 0)

    def test_panel_e_metrics_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config, panel_key="panel_e", download_if_missing=False)
        except FileNotFoundError:
            self.skipTest(
                "Duke H5AD cache is not available; run the downloader to run this integration check."
            )
        data = load_panel_e_metrics(config, data_root=data_root)
        self.assertEqual(data.source_cell_count, 220082)
        self.assertEqual(data.evaluation_cell_count, 209587)
        self.assertEqual(data.excluded_counts, {"Noise": 10495})
        self.assertEqual(data.evaluation_class_count, 20)
        self.assertEqual(
            data.cluster_counts,
            {"flowsom": 300, "leiden": 300, "spatialsort": 246, "pixie": 300},
        )
        self.assertEqual(data.scores.shape, (32, 4))
        pixie_region = data.scores.loc[
            (data.scores["region"] == "2e65eeef2dd18bee2a0baf1cec6d35a1")
            & (data.scores["method"] == "PIXIE"),
            "weighted_f1",
        ].iloc[0]
        self.assertAlmostEqual(pixie_region, 0.6755626737130034, places=12)

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
        self.assertEqual(config["panel_j"]["examples"][0]["expected_cells"], 1086)
        self.assertEqual(config["panel_j"]["examples"][1]["expected_cells"], 915)

    def test_panels_fgh_metrics_when_source_data_are_available(self) -> None:
        config = load_figure_config()
        try:
            data_root = resolve_data_root(config, panel_key="panel_f", download_if_missing=False)
        except FileNotFoundError:
            self.skipTest(
                "Duke H5AD cache is not available; run the downloader to run this integration check."
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
        self.assertAlmostEqual(pixie_f1, 0.841393192430167, places=12)
        pixie_purity = panel_h.metrics.loc[
            panel_h.metrics["cell_type"].eq("Smooth muscle"), "PIXIE_purity"
        ].iloc[0]
        self.assertAlmostEqual(pixie_purity, 0.8758888392703789, places=12)
        pixie_g = panel_g.scores.loc[
            (panel_g.scores["region"] == "76d3efd17b6fc83aaac13e961824c5ae")
            & (panel_g.scores["method"] == "PIXIE"),
            "cell_purity",
        ].iloc[0]
        self.assertAlmostEqual(pixie_g, 0.6411685241472476, places=12)
