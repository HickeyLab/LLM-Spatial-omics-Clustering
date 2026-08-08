"""Contract, metric, and safety checks for the Figure 4 A--F notebook."""

from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

import nbformat
import numpy as np
import pandas as pd

from llm_spatial_omics_clustering.figure_03 import (
    AnnotationResult,
    Figure03CredentialError,
)
from llm_spatial_omics_clustering.figure_04 import (
    Figure04ValidationError,
    _validate_annotation_cache_integrity,
    _validate_or_create_selection_lock,
    aggregate_error_decomposition,
    classification_metrics,
    cluster_error_decomposition,
    confusion_tables,
    load_figure_config,
    run_panel_b,
    run_panel_c,
    run_panel_d,
    run_panel_e,
    run_panel_f,
    select_failure_examples,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class Figure04ContractTests(unittest.TestCase):
    def test_config_freezes_one_figure_03_annotation_contract(self) -> None:
        config = load_figure_config()
        dependency = config["figure_03_dependency"]
        self.assertEqual(
            {
                "provider": dependency["provider"],
                "condition": dependency["condition"],
                "method": dependency["method"],
                "marker_state": dependency["marker_state"],
                "expected_clusters": dependency["expected_clusters"],
            },
            {
                "provider": "openai",
                "condition": "reasoning",
                "method": "leiden",
                "marker_state": "optimized",
                "expected_clusters": 55,
            },
        )
        self.assertEqual(config["evaluation"]["expected_cells"], 220082)
        self.assertEqual(config["evaluation"]["expected_noise_cells"], 10495)
        self.assertEqual(config["evaluation"]["expected_truth_classes"], 21)
        self.assertEqual(len(config["evaluation"]["class_order"]), 21)
        self.assertIn("Noise", config["evaluation"]["class_order"])
        self.assertEqual(len(config["style"]["region_colors"]), 8)

    def test_notebook_has_exactly_one_cleared_code_cell_per_panel(self) -> None:
        notebook_path = (
            REPOSITORY_ROOT
            / "notebooks"
            / "main"
            / "figure_04_leiden_gpt_end_to_end.ipynb"
        )
        notebook = nbformat.read(notebook_path, as_version=4)
        nbformat.validate(notebook)
        self.assertEqual(len(notebook.cells), 6)
        self.assertTrue(all(cell.cell_type == "code" for cell in notebook.cells))
        self.assertEqual(
            [cell.metadata["panel"] for cell in notebook.cells],
            list("ABCDEF"),
        )
        for letter, cell in zip("ABCDEF", notebook.cells):
            self.assertIsNone(cell.execution_count)
            self.assertEqual(cell.outputs, [])
            self.assertIn(f"run_panel_{letter.lower()}(", cell.source)
            if letter == "A":
                self.assertNotIn("PASTE_OPENAI_API_KEY_HERE", cell.source)
                self.assertNotIn("os.getenv(", cell.source)
            else:
                self.assertIn("PASTE_OPENAI_API_KEY_HERE", cell.source)
                self.assertIn("os.getenv(", cell.source)
                self.assertIn("force_refresh=False", cell.source)

    def test_placeholder_stops_every_llm_panel_before_data_loading(self) -> None:
        placeholder = {"openai": "PASTE_OPENAI_API_KEY_HERE"}
        runners = (run_panel_b, run_panel_c, run_panel_d, run_panel_e, run_panel_f)
        with mock.patch(
            "llm_spatial_omics_clustering.figure_04.load_figure03_inputs"
        ) as loader:
            for runner in runners:
                with self.subTest(panel=runner.__name__):
                    with self.assertRaises(Figure03CredentialError):
                        runner(placeholder, REPOSITORY_ROOT)
            loader.assert_not_called()

    def test_no_legacy_annotation_map_is_referenced(self) -> None:
        paths = [
            REPOSITORY_ROOT / "configs/figure_04.yaml",
            REPOSITORY_ROOT / "src/llm_spatial_omics_clustering/figure_04.py",
            REPOSITORY_ROOT
            / "notebooks/main/figure_04_leiden_gpt_end_to_end.ipynb",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        forbidden = (
            "cluster_celltype_leiden.json",
            "cluster_celltype_gpt52_leiden.json",
            "leiden_llm_annotations.json",
            "0.5315",
            "0.1387",
            "0.3298",
        )
        for fragment in forbidden:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, combined)

    def test_cache_integrity_and_selection_lock_reject_mapping_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache_path = root / "annotation.json"
            result = AnnotationResult(
                provider="openai",
                condition="reasoning",
                method="leiden",
                marker_state="optimized",
                requested_model_id="requested",
                returned_model_id="returned",
                annotations={"0": "B"},
                cache_path=cache_path,
                cache_hit=True,
                cache_contract_sha256="contract",
                annotation_sha256="annotation-one",
                prompt_sha256="prompt",
                marker_summary_sha256="markers",
            )
            cache_path.write_text(
                json.dumps(
                    {
                        "cache_contract_sha256": "contract",
                        "annotation_sha256": "annotation-one",
                        "requested_model_id": "requested",
                        "returned_model_id": "returned",
                    }
                ),
                encoding="utf-8",
            )
            _validate_annotation_cache_integrity(result)
            lock_path, lock_sha = _validate_or_create_selection_lock(result, root)
            self.assertTrue(lock_path.is_file())
            self.assertEqual(len(lock_sha), 64)

            drifted = AnnotationResult(
                **{
                    **result.__dict__,
                    "annotations": {"0": "DC"},
                    "annotation_sha256": "annotation-two",
                }
            )
            with self.assertRaisesRegex(
                Figure04ValidationError,
                "will not silently mix mappings",
            ):
                _validate_or_create_selection_lock(drifted, root)

            cache_path.write_text(
                json.dumps(
                    {
                        "cache_contract_sha256": "contract",
                        "annotation_sha256": "tampered",
                        "requested_model_id": "requested",
                        "returned_model_id": "returned",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                Figure04ValidationError,
                "integrity fields",
            ):
                _validate_annotation_cache_integrity(result)


class Figure04MetricTests(unittest.TestCase):
    def test_confusion_rows_normalize_and_f1_is_one_vs_rest(self) -> None:
        cells = pd.DataFrame(
            {
                "truth": ["A", "A", "A", "B", "B", "Noise"],
                "predicted": ["A", "A", "B", "B", "A", "A"],
            }
        )
        labels = ["A", "B", "Noise"]
        counts, normalized = confusion_tables(cells, labels)
        self.assertEqual(int(counts.loc["A", "A"]), 2)
        self.assertEqual(int(counts.loc["Noise", "A"]), 1)
        np.testing.assert_allclose(normalized.sum(axis=1), np.ones(3))

        metrics = classification_metrics(cells["truth"], cells["predicted"], labels)
        by_label = metrics.set_index("cell_type")
        self.assertAlmostEqual(float(by_label.loc["A", "precision"]), 0.5)
        self.assertAlmostEqual(float(by_label.loc["A", "recall"]), 2.0 / 3.0)
        self.assertAlmostEqual(float(by_label.loc["A", "f1"]), 4.0 / 7.0)
        self.assertEqual(float(by_label.loc["Noise", "f1"]), 0.0)

    def test_cluster_and_aggregate_decomposition_sum_to_one(self) -> None:
        cells = pd.DataFrame(
            {
                "cluster_leiden": [0, 0, 0, 0, 1, 1, 1, 1],
                "truth": ["A", "A", "A", "B", "A", "A", "B", "B"],
                "predicted": ["B", "B", "B", "B", "B", "B", "B", "B"],
            }
        )
        stats = cluster_error_decomposition(cells).set_index("cluster")
        self.assertAlmostEqual(float(stats.loc[0, "purity"]), 0.75)
        self.assertAlmostEqual(float(stats.loc[0, "final_correct"]), 0.25)
        self.assertAlmostEqual(float(stats.loc[0, "annotation_loss"]), 0.50)
        self.assertAlmostEqual(float(stats.loc[0, "clustering_loss"]), 0.25)
        # Cluster 1 is a deterministic A/B tie. Prediction B reaches the same
        # fraction as the lexicographically selected majority A.
        self.assertAlmostEqual(float(stats.loc[1, "final_correct"]), 0.50)
        self.assertAlmostEqual(float(stats.loc[1, "annotation_loss"]), 0.0)
        self.assertAlmostEqual(float(stats.loc[1, "clustering_loss"]), 0.50)
        np.testing.assert_allclose(
            stats[["final_correct", "annotation_loss", "clustering_loss"]].sum(axis=1),
            np.ones(2),
        )

        aggregate = aggregate_error_decomposition(stats.reset_index()).iloc[0]
        self.assertAlmostEqual(float(aggregate["final_correct"]), 0.375)
        self.assertAlmostEqual(float(aggregate["annotation_loss"]), 0.25)
        self.assertAlmostEqual(float(aggregate["clustering_loss"]), 0.375)
        self.assertAlmostEqual(
            float(
                aggregate["final_correct"]
                + aggregate["annotation_loss"]
                + aggregate["clustering_loss"]
            ),
            1.0,
        )

    def test_failure_examples_are_distinct_and_deterministic(self) -> None:
        config = load_figure_config()
        table = pd.DataFrame(
            [
                {
                    "cluster": 0,
                    "n_cells": 1000,
                    "majority_truth": "A",
                    "predicted_label": "B",
                    "purity": 0.90,
                    "final_correct": 0.05,
                    "annotation_loss": 0.85,
                    "clustering_loss": 0.10,
                    "predicted_matches_majority": False,
                },
                {
                    "cluster": 1,
                    "n_cells": 1000,
                    "majority_truth": "B",
                    "predicted_label": "B",
                    "purity": 0.30,
                    "final_correct": 0.30,
                    "annotation_loss": 0.00,
                    "clustering_loss": 0.70,
                    "predicted_matches_majority": True,
                },
                {
                    "cluster": 2,
                    "n_cells": 1000,
                    "majority_truth": "C",
                    "predicted_label": "A",
                    "purity": 0.55,
                    "final_correct": 0.20,
                    "annotation_loss": 0.35,
                    "clustering_loss": 0.45,
                    "predicted_matches_majority": False,
                },
            ]
        )
        examples = select_failure_examples(table, config)
        self.assertEqual(examples["cluster"].astype(int).tolist(), [0, 1, 2])
        self.assertEqual(
            examples["failure_mode"].tolist(),
            ["Annotation Limited", "Clustering Limited", "Mixed Loss"],
        )

    def test_failure_mode_name_requires_dominant_positive_named_loss(self) -> None:
        config = load_figure_config()
        no_annotation_limited = pd.DataFrame(
            [
                {
                    "cluster": 0,
                    "n_cells": 1000,
                    "majority_truth": "A",
                    "predicted_label": "A",
                    "purity": 0.70,
                    "final_correct": 0.70,
                    "annotation_loss": 0.00,
                    "clustering_loss": 0.30,
                    "predicted_matches_majority": True,
                },
                {
                    "cluster": 1,
                    "n_cells": 1000,
                    "majority_truth": "B",
                    "predicted_label": "B",
                    "purity": 0.60,
                    "final_correct": 0.60,
                    "annotation_loss": 0.00,
                    "clustering_loss": 0.40,
                    "predicted_matches_majority": True,
                },
            ]
        )
        with self.assertRaisesRegex(
            Figure04ValidationError,
            "positive annotation loss",
        ):
            select_failure_examples(no_annotation_limited, config)


if __name__ == "__main__":
    unittest.main()
