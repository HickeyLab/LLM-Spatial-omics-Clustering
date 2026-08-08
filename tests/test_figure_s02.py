"""Contract, safety, table, and rendering checks for Supplementary Figure 2."""

from pathlib import Path
from types import SimpleNamespace
import shutil
import tempfile
import unittest
from unittest import mock

import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd

from llm_spatial_omics_clustering.figure_03 import Figure03CredentialError
from llm_spatial_omics_clustering.figure_04 import (
    load_figure_config as load_figure_04_config,
)
from llm_spatial_omics_clustering.figure_s02 import (
    _validate_figure04_dependency,
    load_figure_config,
    prepare_panel_a_matrix,
    prepare_panel_b_table,
    render_panel_a,
    render_panel_b,
    run_panel_a,
    run_panel_b,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = (
    REPOSITORY_ROOT
    / "notebooks"
    / "supplementary"
    / "figure_s02_leiden_gpt_diagnostics.ipynb"
)


def _synthetic_cluster_stats() -> pd.DataFrame:
    """Return 55 valid cluster rows covering the full 220,082-cell universe."""
    cluster_count = 55
    cell_counts = np.full(cluster_count, 4001, dtype=np.int64)
    cell_counts[:27] += 1
    purity = np.linspace(0.45, 0.99, cluster_count)
    final_correct = purity - 0.10
    return pd.DataFrame(
        {
            "cluster": np.arange(cluster_count, dtype=np.int64),
            "n_cells": cell_counts,
            "majority_truth": [f"Truth {value}" for value in range(cluster_count)],
            "predicted_label": [
                f"Prediction {value}" for value in range(cluster_count)
            ],
            "purity": purity,
            "final_correct": final_correct,
            "annotation_loss": np.full(cluster_count, 0.10),
            "clustering_loss": 1.0 - purity,
        }
    )


class FigureS02ContractTests(unittest.TestCase):
    def test_config_locks_the_current_figure_04_analysis(self) -> None:
        config = load_figure_config()
        dependency = config["figure_04_dependency"]

        self.assertEqual(config["supplementary_figure"], 2)
        self.assertTrue(str(config["working_title"]).startswith("VERIFY:"))
        self.assertEqual(
            {
                "provider": dependency["expected_provider"],
                "condition": dependency["expected_condition"],
                "method": dependency["expected_method"],
                "marker_state": dependency["expected_marker_state"],
                "cells": dependency["expected_source_cells"],
                "noise_cells": dependency["expected_noise_cells"],
                "truth_classes": dependency["expected_truth_classes"],
                "clusters": dependency["expected_leiden_clusters"],
                "regions": dependency["expected_regions"],
            },
            {
                "provider": "openai",
                "condition": "reasoning",
                "method": "leiden",
                "marker_state": "optimized",
                "cells": 220082,
                "noise_cells": 10495,
                "truth_classes": 21,
                "clusters": 55,
                "regions": 8,
            },
        )
        self.assertEqual(
            config["panel_a"]["source_table"],
            "figure_04.confusion_counts",
        )
        self.assertEqual(
            config["panel_b"]["source_table"],
            "figure_04.cluster_stats",
        )
        self.assertIn("majority reference label", config["panel_b"]["row_label_semantics"])
        self.assertTrue(
            str(config["reference_composite"]["provenance_status"]).startswith(
                "VERIFY:"
            )
        )

        figure_04_config = load_figure_04_config(
            REPOSITORY_ROOT / str(dependency["config_path"])
        )
        # The module-level check is the runtime guard against configuration drift.
        _validate_figure04_dependency(config, figure_04_config)
        self.assertEqual(
            figure_04_config["evaluation"]["class_order"],
            [
                "B",
                "CD4+ T cell",
                "CD66+ Enterocyte",
                "CD7+ Immune",
                "CD8+ T",
                "Cycling TA",
                "DC",
                "Endothelial",
                "Enterocyte",
                "Goblet",
                "ICC",
                "Lymphatic",
                "M2 Macrophage",
                "MUC1+ Enterocyte",
                "Nerve",
                "Neuroendocrine",
                "Neutrophil",
                "Noise",
                "Plasma",
                "Smooth muscle",
                "Stroma",
            ],
        )

        for panel_key in ("panel_a", "panel_b"):
            for output_path in config[panel_key]["outputs"].values():
                self.assertTrue(
                    str(output_path).startswith(
                        "outputs/supplementary/figure_s02/"
                    )
                )

    def test_notebook_has_two_cleared_placeholder_code_cells(self) -> None:
        notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)
        nbformat.validate(notebook)
        self.assertEqual(len(notebook.cells), 2)
        self.assertTrue(all(cell.cell_type == "code" for cell in notebook.cells))

        for panel_letter, cell in zip("AB", notebook.cells, strict=True):
            self.assertIsNone(cell.execution_count)
            self.assertEqual(cell.outputs, [])
            self.assertIn(
                f"run_panel_{panel_letter.lower()}(",
                cell.source,
            )
            self.assertIn("PASTE_OPENAI_API_KEY_HERE", cell.source)
            self.assertIn("OPENAI_API_KEY", cell.source)
            self.assertIn("force_refresh=False", cell.source)

    def test_placeholder_stops_both_panels_before_data_or_outputs(self) -> None:
        placeholder = {"openai": "PASTE_OPENAI_API_KEY_HERE"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_dir = root / "configs"
            config_dir.mkdir()
            for filename in ("figure_s02.yaml", "figure_04.yaml", "figure_03.yaml"):
                shutil.copy2(
                    REPOSITORY_ROOT / "configs" / filename,
                    config_dir / filename,
                )

            with mock.patch(
                "llm_spatial_omics_clustering.figure_04.load_figure03_inputs"
            ) as data_loader:
                for runner in (run_panel_a, run_panel_b):
                    with self.subTest(panel=runner.__name__):
                        with self.assertRaises(Figure03CredentialError):
                            runner(placeholder, repository_root=root)

            data_loader.assert_not_called()
            self.assertFalse((root / "outputs").exists())


class FigureS02TableAndRenderTests(unittest.TestCase):
    def test_panel_a_matrix_is_integer_21_by_21_and_covers_all_cells(self) -> None:
        config = load_figure_config()
        figure_04_config = load_figure_04_config(
            REPOSITORY_ROOT / str(config["figure_04_dependency"]["config_path"])
        )
        class_order = figure_04_config["evaluation"]["class_order"]
        values = np.zeros((21, 21), dtype=np.int64)
        values[0, 0] = 220082
        matrix = pd.DataFrame(values, index=class_order, columns=class_order)

        prepared = prepare_panel_a_matrix(
            SimpleNamespace(confusion_counts=matrix),
            config,
            figure_04_config,
        )
        self.assertEqual(prepared.shape, (21, 21))
        self.assertTrue(np.issubdtype(prepared.to_numpy().dtype, np.integer))
        self.assertEqual(int(prepared.to_numpy().sum()), 220082)
        self.assertEqual(prepared.index.tolist(), class_order)
        self.assertEqual(prepared.columns.tolist(), class_order)

    def test_panel_b_has_55_sorted_clusters_valid_components_and_labels(self) -> None:
        config = load_figure_config()
        prepared = prepare_panel_b_table(_synthetic_cluster_stats(), config)

        self.assertEqual(len(prepared), 55)
        self.assertEqual(prepared["cluster"].nunique(), 55)
        self.assertEqual(int(prepared["n_cells"].sum()), 220082)
        np.testing.assert_allclose(
            prepared[
                ["final_correct", "annotation_loss", "clustering_loss"]
            ].sum(axis=1),
            np.ones(55),
            rtol=0.0,
            atol=1e-10,
        )
        self.assertTrue(
            (
                prepared[
                    ["final_correct", "annotation_loss", "clustering_loss"]
                ]
                >= 0.0
            )
            .all()
            .all()
        )
        self.assertEqual(prepared["display_rank"].tolist(), list(range(1, 56)))
        self.assertEqual(prepared.iloc[0]["cluster"], 54)
        self.assertEqual(prepared.iloc[-1]["cluster"], 0)
        self.assertEqual(prepared.iloc[0]["display_label"], "Cluster 54 - Truth 54")
        self.assertNotIn("Prediction", prepared.iloc[0]["display_label"])

    def test_renderers_write_nonempty_png_and_pdf_files(self) -> None:
        config = load_figure_config()
        figure_04_config = load_figure_04_config(
            REPOSITORY_ROOT / str(config["figure_04_dependency"]["config_path"])
        )
        class_order = figure_04_config["evaluation"]["class_order"]
        values = np.zeros((21, 21), dtype=np.int64)
        np.fill_diagonal(values, 10000)
        values[0, 1] = 10082
        matrix = pd.DataFrame(values, index=class_order, columns=class_order)
        table = prepare_panel_b_table(_synthetic_cluster_stats(), config)

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            for stem, figure in (
                ("panel_a", render_panel_a(matrix, config)),
                ("panel_b", render_panel_b(table, config)),
            ):
                try:
                    for suffix in ("png", "pdf"):
                        path = output_dir / f"{stem}.{suffix}"
                        figure.savefig(path, dpi=72, bbox_inches="tight")
                        self.assertTrue(path.is_file())
                        self.assertGreater(path.stat().st_size, 0)
                finally:
                    plt.close(figure)


if __name__ == "__main__":
    unittest.main()
