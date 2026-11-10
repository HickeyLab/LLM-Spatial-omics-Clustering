"""Formatting cannot change table data or reintroduce vertical/grid rules."""
from __future__ import annotations

import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "docs/tables/ieee"


class CellParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.styles, self.cell = [], [], None
        self.span_styles = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.current = []
        elif tag == "td":
            self.cell = ""
            self.styles.append(dict(attrs)["style"])
        elif tag == "span" and self.cell is not None:
            self.span_styles.append(dict(attrs)["style"])

    def handle_data(self, value):
        if self.cell is not None:
            self.cell += value

    def handle_endtag(self, tag):
        if tag == "td":
            self.current.append(self.cell)
            self.cell = None
        elif tag == "tr":
            self.rows.append(self.current)
            self.current = None


class IEEEFormattingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads((TABLES / "expected_cells.json").read_text())
        cls.manifest = json.loads((TABLES / "manifest.json").read_text())

    def test_exact_cells_in_both_editable_html_and_tsv(self):
        self.assertEqual(sum(len(row) for rows in self.expected.values() for row in rows), 414)
        for table_id, rows in self.expected.items():
            parser = CellParser()
            parser.feed((TABLES / (table_id + ".html")).read_text())
            self.assertEqual(parser.rows, rows, table_id)
            with (TABLES / (table_id + ".tsv")).open(newline="") as f:
                self.assertEqual(list(csv.reader(f, delimiter="\t")), rows, table_id)
            if table_id.startswith("S6"):
                with (ROOT / "data/frozen/annotation47_results_20261110" / ("Table_" + table_id + ".csv")).open(newline="") as f:
                    self.assertEqual(rows, list(csv.reader(f)), table_id)

    def test_native_fragment_minimal_rules_and_numeric_alignment(self):
        for table_id, rows in self.expected.items():
            parser = CellParser()
            parser.feed((TABLES / (table_id + ".html")).read_text())
            columns = len(rows[0])
            numeric = self.manifest["tables"][table_id]["numeric_columns_zero_based"]
            for index, style in enumerate(parser.styles):
                row, col = divmod(index, columns)
                self.assertNotIn("border-left:1", style)
                self.assertNotIn("border-right:1", style)
                self.assertIn("border:0px solid #ffffff", style)
                self.assertIn("font-size:10pt", style)
                self.assertIn("font-weight:normal", style)
                self.assertIn("background-color:#ffffff", style)
                self.assertIn("text-align:" + ("right" if col in numeric else "left"), style)
                if row == 0:
                    self.assertIn("font-weight:bold", parser.span_styles[index])
                    self.assertIn("border-top:1pt", style)
                    self.assertIn("border-bottom:0.6pt", style)
                elif row == len(rows) - 1:
                    self.assertIn("font-weight:normal", parser.span_styles[index])
                    self.assertIn("border-bottom:1pt", style)
                else:
                    self.assertIn("font-weight:normal", parser.span_styles[index])
                    self.assertNotIn("border-bottom:", style)
                    self.assertNotIn("border-top:", style)

    def test_output_hashes_and_caption_conventions(self):
        captions = json.loads((TABLES / "caption_oldnew.json").read_text())
        self.assertEqual(set(x["id"] for x in captions), set(self.expected))
        self.assertFalse(self.manifest["roman_numeral_renumbering_applied"])
        for entry in captions:
            self.assertEqual(entry["label"], "TABLE " + entry["id"])
            self.assertFalse(entry["title"].endswith("."))
            self.assertEqual(entry["new"].split("\n"), [entry["label"], entry["title"]])
        for table_id, entry in self.manifest["tables"].items():
            for suffix, proof in entry["files"].items():
                path = TABLES / (table_id + suffix)
                self.assertEqual(path.stat().st_size, proof["bytes"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), proof["sha256"])


if __name__ == "__main__":
    unittest.main()
