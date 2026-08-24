"""Validate the clean-clone Table S2 source, notebook, and publication preview."""

from __future__ import annotations

import csv
from decimal import Decimal
from hashlib import sha256
import json
from math import prod
from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = (
    REPOSITORY_ROOT
    / "data/tables/supplementary_table_s02_marker_summary_optimization.csv"
)
NOTEBOOK_PATH = (
    REPOSITORY_ROOT
    / "notebooks/final_figures/table_s02_marker_summary_optimization.ipynb"
)
PREVIEW_PATH = REPOSITORY_ROOT / "notebooks/final_figures/previews/table_s02.png"

SOURCE_SHA256 = "e91af5dfc7ef27687aa8b07acbc74b86f9c2f119228dc1d2db20034f5ec671f4"
PREVIEW_SHA256 = "98074b1938e30fc0ed137e9b6ebe0d9c0c864a0b1abb3bde6e2ebbbcb7dde1aa"
EXPECTED_METHODS = ["FlowSOM", "Leiden", "SpatialSort", "PIXIE-style adaptation"]
EXPECTED_COMBINATIONS = [1_152, 960, 960, 960]

DECIMAL_GRID_PATTERN = re.compile(
    r"^(?P<start>\d+(?:\.\d+)?)–(?P<stop>\d+(?:\.\d+)?) "
    r"\(increment (?P<step>\d+(?:\.\d+)?)\)$"
)
INTEGER_GRID_PATTERN = re.compile(r"^(?P<start>\d+)–(?P<stop>\d+)$")


def _decimal_grid(specification: str) -> list[Decimal]:
    match = DECIMAL_GRID_PATTERN.fullmatch(specification)
    if match is None:
        raise AssertionError(f"Invalid decimal grid: {specification!r}")
    start = Decimal(match.group("start"))
    stop = Decimal(match.group("stop"))
    step = Decimal(match.group("step"))
    quotient, remainder = divmod(stop - start, step)
    if step <= 0 or remainder:
        raise AssertionError(f"Non-integral decimal grid: {specification!r}")
    return [start + index * step for index in range(int(quotient) + 1)]


def _integer_grid(specification: str) -> list[int]:
    match = INTEGER_GRID_PATTERN.fullmatch(specification)
    if match is None:
        raise AssertionError(f"Invalid integer grid: {specification!r}")
    start, stop = int(match.group("start")), int(match.group("stop"))
    return list(range(start, stop + 1))


class TableS02Tests(unittest.TestCase):
    def test_authoritative_source_and_candidate_cardinalities(self) -> None:
        self.assertEqual(sha256(SOURCE_PATH.read_bytes()).hexdigest(), SOURCE_SHA256)
        with SOURCE_PATH.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual([row["Method"] for row in rows], EXPECTED_METHODS)
        observed_combinations = []
        for row in rows:
            expression = _decimal_grid(row["Fine-grid expression threshold"])
            fraction = _decimal_grid(row["Fine-grid fraction threshold"])
            mean_expression = _decimal_grid(
                row["Fine-grid mean-expression threshold"]
            )
            maximum_markers = _integer_grid(row["Fine-grid maximum markers"])

            self.assertIn(Decimal(row["Selected expression threshold"]), expression)
            self.assertIn(Decimal(row["Selected fraction threshold"]), fraction)
            self.assertIn(
                Decimal(row["Selected mean-expression threshold"]),
                mean_expression,
            )
            self.assertIn(int(row["Selected maximum markers"]), maximum_markers)
            self.assertEqual(
                row["Selected fallback minimum markers"],
                row["Fine-grid fallback minimum markers"],
            )
            observed_combinations.append(
                prod(
                    [
                        len(expression),
                        len(fraction),
                        len(mean_expression),
                        len(maximum_markers),
                        1,
                    ]
                )
            )

        self.assertEqual(observed_combinations, EXPECTED_COMBINATIONS)

    def test_notebook_is_executed_and_clean_clone_portable(self) -> None:
        notebook_text = NOTEBOOK_PATH.read_text(encoding="utf-8")
        notebook = json.loads(notebook_text)
        code_cells = [
            cell for cell in notebook["cells"] if cell["cell_type"] == "code"
        ]

        self.assertEqual(notebook["metadata"]["table_id"], "table_s02")
        self.assertEqual(notebook["metadata"]["source_sha256"], SOURCE_SHA256)
        self.assertEqual(
            [cell["execution_count"] for cell in code_cells],
            list(range(1, len(code_cells) + 1)),
        )
        self.assertTrue(all(cell["outputs"] for cell in code_cells))
        self.assertIn(
            "outputs/source_rebuilt/table_s02/table_s02_marker_summary_optimization.png",
            notebook_text,
        )
        self.assertIn('"image/png"', notebook_text)
        self.assertNotIn("source_rebuild_scripts", notebook_text)
        self.assertNotIn("/Users/", notebook_text)

    def test_tracked_preview_is_the_canonical_source_traced_png(self) -> None:
        self.assertEqual(sha256(PREVIEW_PATH.read_bytes()).hexdigest(), PREVIEW_SHA256)


if __name__ == "__main__":
    unittest.main()
