#!/usr/bin/env python3
"""Render editable IEEE-style Table S3 without searches or analytical reruns."""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from render_table_s01 import element

ROOT = Path(__file__).resolve().parents[1]


def load_inputs():
    config = json.loads((ROOT / "configs/table_s02.json").read_text())
    source = ROOT / config["data"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != config["data_sha256"]:
        raise ValueError("Table S3 presentation content checksum differs")
    data = json.loads(source.read_text())
    if hashlib.sha256((ROOT / data["source_csv"]).read_bytes()).hexdigest() != data["source_csv_sha256"]:
        raise ValueError("The analytical source CSV changed")
    style = json.loads((ROOT / config["style_reference"]).read_text())
    if style["font"] != "Times New Roman" or style["vertical_rules"] or style["body_row_rules"]:
        raise ValueError("S2 must use the current S1 IEEE-style convention")
    if [p["letter"] for p in data["panels"]] != list("ABCD"):
        raise ValueError("Expected all four S2 parts")
    if sum((len(p["rows"]) + 1) * len(p["headers"]) for p in data["panels"]) != 135:
        raise ValueError("Expected all 135 S2 cells")
    for panel in data["panels"]:
        widths = config["column_widths"][panel["letter"]]
        if abs(sum(widths) - 6.5) > 1e-8 or len(widths) != len(panel["headers"]):
            raise ValueError("Invalid S2 column widths")
    return config, style, data


def notes_text(data):
    prefix = "Table S3. Retrospective marker-name-list parameter selection. "
    if not data["caption"].startswith(prefix):
        raise ValueError("Unexpected current Table S3 caption")
    return data["caption"][len(prefix):]


def add_page_caption(document, continued=False):
    for size, text in [(11, "TABLE S3" + (" (CONTINUED)" if continued else "")),
                       (10, "RETROSPECTIVE MARKER-NAME-LIST PARAMETER SELECTION")]:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.keep_with_next = True
        paragraph.paragraph_format.space_after = Pt(4)
        paragraph.add_run(text).font.size = Pt(size)


def add_panel(document, panel, widths, style):
    paragraph = document.add_paragraph(f"{panel['letter']}. {panel['title']}")
    paragraph.paragraph_format.space_before = Pt(12)
    paragraph.paragraph_format.space_after = Pt(5)
    paragraph.paragraph_format.keep_with_next = True
    table = document.add_table(rows=len(panel["rows"]) + 1, cols=len(widths))
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for column, width in zip(table.columns, widths):
        column.width = Inches(width)
    borders = element(table._tbl.tblPr, "tblBorders")
    for side in ("top", "bottom"):
        element(borders, side, val="single", sz=round(style["top_bottom_rule_pt"] * 8), color="000000")
    for side in ("left", "right", "insideH", "insideV"):
        element(borders, side, val="nil")
    for r, (row, values) in enumerate(zip(table.rows, [panel["headers"], *panel["rows"]])):
        properties = row._tr.get_or_add_trPr()
        element(properties, "cantSplit")
        if r == 0:
            element(properties, "tblHeader")
        for c, (cell, value, width) in enumerate(zip(row.cells, values, widths)):
            cell.width = Inches(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            props = cell._tc.get_or_add_tcPr()
            padding = element(props, "tcMar")
            for side, amount in style["cell_padding_twips"].items():
                element(padding, side, w=amount, type="dxa")
            if r == 0:
                edge = element(props, "tcBorders")
                element(edge, "bottom", val="single", sz=round(style["header_rule_pt"] * 8), color="000000")
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if c == 0 else WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.keep_together = True
            paragraph.add_run(value)


def build_document(config, style, data):
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(1)
    section.left_margin = section.right_margin = Inches(1)
    normal = document.styles["Normal"]
    normal.font.name = style["font"]
    normal.font.size = Pt(style["font_size_pt"])
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.space_before = normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = style["line_spacing"]
    by_letter = {p["letter"]: p for p in data["panels"]}
    for index, page in enumerate(config["page_panels"]):
        if index:
            document.add_page_break()
        add_page_caption(document, continued=bool(index))
        for letter in page:
            add_panel(document, by_letter[letter], config["column_widths"][letter], style)
    paragraph = document.add_paragraph(notes_text(data))
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.line_spacing = 1.1
    paragraph.paragraph_format.keep_together = True
    for run in paragraph.runs:
        run.font.size = Pt(9.5)
    document.core_properties.title = "Table S3 retrospective marker name list parameter selection"
    return document


def html_page(config, style, data, page_index):
    label = "TABLE S3" + (" (CONTINUED)" if page_index else "")
    base = "font-family:'Times New Roman';font-weight:normal;color:#000000;line-height:105%;"
    output = [f'<p style="{base}font-size:11pt;text-align:center;margin:0 0 4pt;">{label}</p>',
              f'<p style="{base}font-size:10pt;text-align:center;margin:0 0 4pt;">RETROSPECTIVE MARKER-NAME-LIST PARAMETER SELECTION</p>']
    by_letter = {p["letter"]: p for p in data["panels"]}
    for letter in config["page_panels"][page_index]:
        panel = by_letter[letter]
        output.append(f'<p style="{base}font-size:10pt;margin:12pt 0 5pt;">{letter}. {escape(panel["title"])}</p>')
        output.append('<table style="border-collapse:collapse;table-layout:fixed;border:none;width:6.5in;">')
        for r, values in enumerate([panel["headers"], *panel["rows"]]):
            output.append('<tr>')
            for c, (value, width) in enumerate(zip(values, config["column_widths"][letter])):
                rules = "border:none;"
                if r == 0:
                    rules += f"border-top:{style['top_bottom_rule_pt']}pt solid #000000;border-bottom:{style['header_rule_pt']}pt solid #000000;"
                if r == len(panel["rows"]):
                    rules += f"border-bottom:{style['top_bottom_rule_pt']}pt solid #000000;"
                align = "left" if c == 0 else "center"
                text = escape(value)
                if r == 0:
                    text = text.replace("Mean-expression", "Mean-<br>expression").replace("Maximum-marker", "Maximum-<br>marker")
                output.append(f'<td style="{base}font-size:10pt;width:{width}in;padding:4pt 4.5pt;background-color:#ffffff;{rules}text-align:{align};vertical-align:middle;"><span style="{base}font-size:10pt;">{text}</span></td>')
            output.append('</tr>')
        output.append('</table>')
    if page_index == len(config["page_panels"]) - 1:
        output.append(f'<p style="{base}font-size:9.5pt;line-height:110%;margin:8pt 0 0;">{escape(notes_text(data))}</p>')
    return "".join(output)


def verify_document(path, data):
    document = Document(path)
    matrices = [[[cell.text for cell in row.cells] for row in table.rows] for table in document.tables]
    if matrices != [[panel["headers"], *panel["rows"]] for panel in data["panels"]]:
        raise ValueError("Table S3 cell content changed")
    if document.paragraphs[-1].text != notes_text(data):
        raise ValueError("Table S3 provenance notes changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/manuscript_replay/table_s03_ieee")
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    config, style, data = load_inputs()
    if args.check:
        verify_document(args.check, data)
        print("Verified 135 Table S3 cells and all provenance notes")
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / "Table_S3_IEEE.docx"
    build_document(config, style, data).save(target)
    for index in range(len(config["page_panels"])):
        (args.output_dir / f"Table_S3_IEEE_page_{index+1}.html").write_text(html_page(config, style, data, index))
    verify_document(target, data)
    print(target)


if __name__ == "__main__":
    main()
