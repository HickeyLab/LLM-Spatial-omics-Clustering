"""Contract and safety checks for the Figure 3 A--L notebook."""

from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest import mock
from urllib import error as urllib_error

import nbformat
import numpy as np
import pandas as pd

from llm_spatial_omics_clustering.figure_03 import (
    AnnotationResult,
    Figure03APIError,
    Figure03CredentialError,
    Figure03Inputs,
    Figure03ValidationError,
    _consensus_annotations,
    _consensus_tie_sensitivity_table,
    _post_json,
    _provider_request_contract,
    _require_provider_generation_available,
    _returned_model_id,
    _search_spatial_examples,
    _spatial_agreement_cells,
    _strip_reasoning_fields,
    load_figure03_inputs,
    load_figure_config,
    run_panel_b,
    run_panel_c,
    run_panel_d,
    run_panel_e,
    run_panel_f,
    run_panel_g,
    run_panel_h,
    run_panel_i,
    run_panel_j,
    run_panel_k,
    run_panel_l,
    summarize_cluster_markers,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class Figure03ContractTests(unittest.TestCase):
    def test_config_inherits_exact_figure_02_cluster_contract(self) -> None:
        config = load_figure_config()
        expected = config["figure_02_dependency"]["expected_methods"]
        self.assertEqual(
            {method: int(contract["expected_clusters"]) for method, contract in expected.items()},
            {"flowsom": 300, "leiden": 55, "spatialsort": 60, "pixie": 50},
        )
        self.assertEqual(config["figure_02_dependency"]["source_panel"], "panel_d")
        self.assertEqual(config["evaluation"]["excluded_labels"], ["Noise"])
        self.assertEqual(config["evaluation"]["expected_source_cells"], 220082)
        self.assertEqual(config["evaluation"]["expected_evaluation_cells"], 209587)
        self.assertEqual(len(config["evaluation"]["allowed_labels"]), 20)
        self.assertEqual(
            config["consensus"]["tie_priority"]["leiden"],
            ["anthropic", "gemini", "openai", "deepseek"],
        )
        self.assertTrue(
            config["consensus"]["tie_break_selected_on_evaluation_labels"]
        )
        self.assertEqual(
            config["providers"]["openai"]["conditions"]["reasoning"]["model_id"],
            "gpt-5.2-2025-12-11",
        )
        self.assertEqual(
            config["providers"]["deepseek"]["generation_status"],
            "retired",
        )
        self.assertFalse(
            config["providers"]["gemini"]["conditions"]["non_reasoning"][
                "no_reasoning_guaranteed"
            ]
        )
        self.assertEqual(
            config["marker_summaries"]["optimized"]["pixie"],
            {
                "expression_threshold": 0.10,
                "fraction_threshold": 0.56,
                "mean_expression_threshold": 0.02,
                "maximum_markers": 4,
                "fallback_minimum_markers": 4,
            },
        )
        color_table = pd.read_csv(
            REPOSITORY_ROOT / config["style"]["cell_type_color_map_path"]
        )
        self.assertEqual(
            set(color_table["cell_type"].astype(str)),
            set(config["evaluation"]["allowed_labels"]),
        )
        self.assertFalse(color_table["cell_type"].duplicated().any())

    def test_notebook_has_exactly_one_code_cell_per_panel(self) -> None:
        notebook_path = (
            REPOSITORY_ROOT
            / "notebooks"
            / "main"
            / "figure_03_llm_annotation_benchmark.ipynb"
        )
        notebook = nbformat.read(notebook_path, as_version=4)
        nbformat.validate(notebook)
        self.assertEqual(len(notebook.cells), 12)
        self.assertTrue(all(cell.cell_type == "code" for cell in notebook.cells))
        self.assertEqual(
            [cell.metadata["panel"] for cell in notebook.cells],
            list("ABCDEFGHIJKL"),
        )
        for letter, cell in zip("ABCDEFGHIJKL", notebook.cells):
            self.assertIsNone(cell.execution_count)
            self.assertEqual(cell.outputs, [])
            self.assertIn(f"run_panel_{letter.lower()}(", cell.source)
            if letter == "A":
                self.assertNotIn("PASTE_", cell.source)
            else:
                self.assertIn("PASTE_", cell.source)
                self.assertIn("os.getenv(", cell.source)

    def test_placeholder_keys_stop_every_llm_panel_before_data_loading(self) -> None:
        placeholders = {
            "gemini": "PASTE_GEMINI_API_KEY_HERE",
            "openai": "PASTE_OPENAI_API_KEY_HERE",
            "anthropic": "PASTE_ANTHROPIC_API_KEY_HERE",
            "deepseek": "PASTE_DEEPSEEK_API_KEY_HERE",
        }
        runners = (
            run_panel_b,
            run_panel_c,
            run_panel_d,
            run_panel_e,
            run_panel_f,
            run_panel_g,
            run_panel_h,
            run_panel_i,
            run_panel_j,
            run_panel_k,
            run_panel_l,
        )
        with mock.patch(
            "llm_spatial_omics_clustering.figure_03.load_figure03_inputs"
        ) as loader:
            for runner in runners:
                with self.subTest(panel=runner.__name__):
                    with self.assertRaises(Figure03CredentialError):
                        runner(placeholders, REPOSITORY_ROOT)
            loader.assert_not_called()

    def test_marker_thresholds_are_strict_and_short_lists_are_not_padded(self) -> None:
        cells = pd.DataFrame(
            {
                "File_ID": ["f"] * 4,
                "ID": [1, 2, 3, 4],
                "truth": ["A", "A", "B", "B"],
                "cluster_toy": [0, 0, 1, 1],
            }
        )
        expression = np.asarray(
            [
                [0.5, 0.4, 0.1],
                [0.5, 0.0, 0.1],
                [0.1, 0.2, 0.3],
                [0.1, 0.2, 0.3],
            ],
            dtype=np.float32,
        )
        inputs = Figure03Inputs(
            marker_cells=cells,
            cells=cells,
            expression=expression,
            expression_sha256="test",
            marker_names=("A", "B", "C"),
            cluster_counts={"toy": 2},
            source_cell_count=4,
            evaluation_cell_count=4,
            figure_02_config_path=Path("figure_02.yaml"),
            data_root=Path("."),
        )
        summaries = summarize_cluster_markers(
            inputs,
            "toy",
            {
                "expression_threshold": 0.3,
                "fraction_threshold": 0.5,
                "mean_expression_threshold": 0.2,
                "maximum_markers": 3,
                "fallback_minimum_markers": 2,
            },
        )
        # Marker B is positive in exactly 50% of cluster 0 and therefore fails
        # the strict > 0.5 test. The surviving one-marker list is not padded.
        self.assertEqual(summaries["0"], ["A"])
        # Cluster 1 has no passing marker and falls back to its top two means.
        self.assertEqual(summaries["1"], ["C", "B"])
        # Evaluation truth is never consulted when marker summaries are built.
        changed_evaluation = cells.assign(truth=["Noise", "B", "A", "Noise"])
        changed_inputs = replace(inputs, cells=changed_evaluation)
        self.assertEqual(
            summarize_cluster_markers(
                changed_inputs,
                "toy",
                {
                    "expression_threshold": 0.3,
                    "fraction_threshold": 0.5,
                    "mean_expression_threshold": 0.2,
                    "maximum_markers": 3,
                    "fallback_minimum_markers": 2,
                },
            ),
            summaries,
        )

    def test_consensus_uses_method_specific_llm_priority_not_truth(self) -> None:
        config = load_figure_config()
        labels = {
            "gemini": {"0": "B", "1": "B"},
            "openai": {"0": "DC", "1": "B"},
            "anthropic": {"0": "Plasma", "1": "DC"},
            "deepseek": {"0": "Stroma", "1": "DC"},
        }
        results = {}
        for provider, annotations in labels.items():
            key = (provider, "reasoning", "leiden", "optimized")
            results[key] = AnnotationResult(
                provider=provider,
                condition="reasoning",
                method="leiden",
                marker_state="optimized",
                requested_model_id="test-requested",
                returned_model_id="test-returned",
                annotations=annotations,
                cache_path=Path(f"{provider}.json"),
                cache_hit=True,
                cache_contract_sha256="contract",
                annotation_sha256="annotations",
                prompt_sha256="prompt",
                marker_summary_sha256="markers",
            )
        consensus = _consensus_annotations(results, config, method="leiden")
        # Four-way tie: Leiden's first-priority provider is Anthropic.
        self.assertEqual(consensus["0"], "Plasma")
        # Two-way label tie: Anthropic's DC vote wins over Gemini's B vote.
        self.assertEqual(consensus["1"], "DC")

    def test_spatial_example_selection_is_invariant_to_ground_truth(self) -> None:
        coordinates = [(x, y) for x in range(15) for y in range(15)]
        cells = pd.DataFrame(
            [
                {
                    "File_ID": file_id,
                    "ID": index,
                    "x": x,
                    "y": y,
                    "truth": "A",
                    "cluster_leiden": index % 4,
                    "agreement_fraction": agreement,
                }
                for file_id, agreement in (("low", 0.25), ("high", 1.0))
                for index, (x, y) in enumerate(coordinates)
            ]
        )
        panel = {
            "method": "leiden",
            "target_cells": 50,
            "cell_tolerance": 20,
            "random_seed": 123,
            "candidate_centers_per_file": 40,
            "radius_scale_factors": [1.0],
        }
        _, metadata_a = _search_spatial_examples(cells, panel)
        changed_truth = cells.copy()
        changed_truth["truth"] = np.where(
            np.arange(len(changed_truth)) % 3 == 0,
            "B",
            "C",
        )
        _, metadata_b = _search_spatial_examples(changed_truth, panel)
        pd.testing.assert_frame_equal(metadata_a, metadata_b)

    def test_spatial_agreement_uses_all_source_cells_and_emits_24_orders(self) -> None:
        config = load_figure_config()
        marker_cells = pd.DataFrame(
            {
                "File_ID": ["f"] * 6,
                "ID": list(range(6)),
                "x": list(range(6)),
                "y": list(range(6)),
                "truth_raw": ["B", "Noise", "DC", "B", "Noise", "DC"],
                "truth": ["B", "Noise", "DC", "B", "Noise", "DC"],
                "cluster_leiden": [0, 0, 1, 0, 1, 1],
            }
        )
        evaluation_cells = marker_cells.loc[
            ~marker_cells["truth_raw"].eq("Noise")
        ].reset_index(drop=True)
        inputs = Figure03Inputs(
            marker_cells=marker_cells,
            cells=evaluation_cells,
            expression=np.zeros((6, 1), dtype=np.float32),
            expression_sha256="expression",
            marker_names=("marker",),
            cluster_counts={"leiden": 2},
            source_cell_count=6,
            evaluation_cell_count=4,
            figure_02_config_path=Path("figure_02.yaml"),
            data_root=Path("."),
        )
        labels = {
            "gemini": {"0": "B", "1": "DC"},
            "openai": {"0": "B", "1": "B"},
            "anthropic": {"0": "DC", "1": "DC"},
            "deepseek": {"0": "DC", "1": "B"},
        }
        results = {
            (provider, "reasoning", "leiden", "optimized"): AnnotationResult(
                provider=provider,
                condition="reasoning",
                method="leiden",
                marker_state="optimized",
                requested_model_id="requested",
                returned_model_id="returned",
                annotations=annotations,
                cache_path=Path(f"{provider}.json"),
                cache_hit=True,
                cache_contract_sha256="contract",
                annotation_sha256="annotations",
                prompt_sha256="prompt",
                marker_summary_sha256="markers",
            )
            for provider, annotations in labels.items()
        }
        spatial = _spatial_agreement_cells(
            inputs,
            results,
            config,
            method="leiden",
            condition="reasoning",
        )
        self.assertEqual(len(spatial), 6)
        self.assertEqual(int(spatial["truth_raw"].eq("Noise").sum()), 2)
        sensitivity = _consensus_tie_sensitivity_table(
            inputs,
            results,
            config,
            level="cell",
            condition="reasoning",
            methods=["leiden"],
        )
        self.assertEqual(len(sensitivity), 24)
        self.assertEqual(int(sensitivity["selected_historical_order"].sum()), 1)

    def test_reasoning_payloads_and_signatures_are_removed(self) -> None:
        response = {
            "model": "served-model",
            "output": [
                {"type": "reasoning", "encrypted_content": "secret"},
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "{}"},
                        {
                            "text": "hidden thought",
                            "thought": True,
                            "thoughtSignature": "signature",
                        },
                    ],
                },
            ],
            "thinking": {"tokens": 100},
            "reasoning_content": "hidden",
        }
        cleaned = _strip_reasoning_fields(response)
        serialized = json.dumps(cleaned).lower()
        self.assertIn("served-model", serialized)
        self.assertIn("output_text", serialized)
        for forbidden in (
            "hidden thought",
            "reasoning_content",
            "encrypted_content",
            "thoughtsignature",
            "\"thinking\"",
            "\"type\": \"reasoning\"",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_provider_response_model_is_not_inferred_from_request(self) -> None:
        self.assertEqual(
            _returned_model_id("openai", {"model": "gpt-snapshot-served"}),
            "gpt-snapshot-served",
        )
        self.assertEqual(
            _returned_model_id("gemini", {"modelVersion": "gemini-version-served"}),
            "gemini-version-served",
        )
        with self.assertRaises(Figure03APIError):
            _returned_model_id("anthropic", {})

    def test_request_contract_changes_with_reasoning_settings(self) -> None:
        config = load_figure_config()
        original = _provider_request_contract("gemini", "non_reasoning", config)
        modified = json.loads(json.dumps(config))
        modified["providers"]["gemini"]["conditions"]["non_reasoning"][
            "thinking_level"
        ] = "high"
        changed = _provider_request_contract("gemini", "non_reasoning", modified)
        self.assertNotEqual(original, changed)
        self.assertEqual(original["max_output_tokens"], 16000)
        self.assertIn("endpoint_template", original)

    def test_retired_deepseek_fresh_generation_is_blocked(self) -> None:
        config = load_figure_config()
        with self.assertRaisesRegex(
            Figure03ValidationError,
            "will not silently substitute",
        ):
            _require_provider_generation_available("deepseek", config)
        _require_provider_generation_available("openai", config)

    def test_transient_transport_error_is_retried(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"model": "served"}'

        with (
            mock.patch(
                "llm_spatial_omics_clustering.figure_03.urllib_request.urlopen",
                side_effect=[urllib_error.URLError("temporary"), Response()],
            ) as urlopen,
            mock.patch(
                "llm_spatial_omics_clustering.figure_03.time.sleep"
            ) as sleep,
        ):
            result = _post_json(
                "https://example.invalid",
                {"prompt": "test"},
                {"Authorization": "Bearer test"},
                1.0,
            )
        self.assertEqual(result, {"model": "served"})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_figure_02_inputs_when_local_data_are_available(self) -> None:
        try:
            inputs = load_figure03_inputs(REPOSITORY_ROOT)
        except FileNotFoundError:
            self.skipTest("Local Figure 2 inputs are unavailable.")
        self.assertEqual(inputs.source_cell_count, 220082)
        self.assertEqual(inputs.evaluation_cell_count, 209587)
        self.assertEqual(inputs.expression.shape, (220082, 45))
        self.assertEqual(len(inputs.marker_cells), 220082)
        self.assertEqual(
            inputs.marker_cells[["File_ID", "ID"]].duplicated().sum(),
            0,
        )
        self.assertEqual(inputs.cells["File_ID"].nunique(), 8)
        self.assertEqual(inputs.cells[["File_ID", "ID"]].duplicated().sum(), 0)
        self.assertEqual(inputs.cells["truth"].nunique(), 20)
        self.assertEqual(
            inputs.cluster_counts,
            {"flowsom": 300, "leiden": 55, "spatialsort": 60, "pixie": 50},
        )


if __name__ == "__main__":
    unittest.main()
