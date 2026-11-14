#!/usr/bin/env python3
"""Format the seven retained tables without changing a cell or its order.

The stable supplementary IDs are retained. This is an IEEE-style visual
adaptation, not IEEE's Roman-numeral renumbering convention. Reproduction uses
the checked source_tables.json; --source-docx refreshes that input explicitly.
There is no inference, fitting, scoring, or network code in this renderer.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import textwrap
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/tables/ieee"
IDS = ("S1", "S2A", "S2B", "S6a", "S6b", "S6c", "S6d")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
STYLE_SOURCE = "https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf"
WEIGHTS = {
    "S1": [19, 19, 19, 17, 13, 13],
    "S2A": [17, 20.75, 20.75, 20.75, 20.75],
    "S2B": [30, 17.5, 17.5, 17.5, 17.5],
    "S6a": [15, 25, 20, 20, 20],
    "S6b": [15, 25, 15, 15, 15, 15],
    "S6c": [15, 25, 20, 20, 20],
    "S6d": [17, 24, 18, 12, 29],
}
NUMERIC = {"S1": [1, 2, 3, 4, 5], "S2A": [], "S2B": [],
           "S6a": [2, 3, 4], "S6b": [2, 3, 4, 5],
           "S6c": [2, 3, 4], "S6d": []}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_rows(rows):
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode()


def extract_source(docx):
    with zipfile.ZipFile(docx) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    parents = {c: p for p in root.iter() for c in p}

    def removed(element):
        while element is not None:
            if element.tag in (W + "del", W + "moveFrom"):
                return True
            if element.tag == W + "tr" and element.find(W + "trPr/" + W + "del") is not None:
                return True
            element = parents.get(element)
        return False

    def text(element):
        return "".join(t.text or "" for t in element.iter(W + "t") if not removed(t))

    body = root.find(W + "body")
    captions = {}
    tables = []
    for item in body:
        if item.tag == W + "p":
            value = text(item)
            match = re.match(r"^Table (S1|S2A|S2B|S6[a-d])\. (.+)$", value)
            if match:
                assert match[1] not in captions, match[1]
                captions[match[1]] = value
        elif item.tag == W + "tbl":
            rows = [[text(cell) for cell in row.findall(W + "tc")]
                    for row in item.findall(W + "tr") if not removed(row)]
            if rows:
                tables.append(rows)
    assert len(tables) == 7 and set(captions) == set(IDS)
    result = {"schema": "manuscript.table_format_source.v1",
              "source_docx_sha256": sha(docx),
              "accepted_view": "Skip deleted/move-from text and deleted table rows",
              "tables": {}}
    for table_id, rows in zip(IDS, tables):
        assert all(len(r) == len(rows[0]) for r in rows)
        if table_id.startswith("S6"):
            csv_path = ROOT / "data/frozen/annotation47_results_20261110" / ("Table_" + table_id + ".csv")
            with csv_path.open(newline="") as f:
                assert rows == list(csv.reader(f)), table_id
        result["tables"][table_id] = {
            "caption_old": captions[table_id], "rows": rows,
            "cell_order_sha256": hashlib.sha256(canonical_rows(rows)).hexdigest(),
        }
    return result


def caption(table_id, original):
    title = original.split(". ", 1)[1].removesuffix(".")
    # A data filename is an identifier, not prose: preserve its exact case.
    literals = re.findall(r"Table_S\d+[a-z]?\.csv", title)
    title = title.upper()
    for value in literals:
        title = title.replace(value.upper(), value)
    return "TABLE " + table_id, title


def table_html(table_id, rows):
    chunks = ['<table aria-label="Table ' + table_id + '" style="border-collapse:collapse;'
              'table-layout:fixed;width:624px;max-width:100%;font-family:Times New Roman,Times,serif;'
              'font-size:10pt;font-weight:normal;line-height:1.2;background-color:#ffffff;color:#000000;">']
    for i, row in enumerate(rows):
        chunks.append("<tr>")
        for j, value in enumerate(row):
            alignment = "right" if j in NUMERIC[table_id] else "left"
            style = ("border:0px solid #ffffff;padding:3pt 4pt;vertical-align:top;"
                     "font-family:Times New Roman,Times,serif;font-size:10pt;font-weight:normal;"
                     "background-color:#ffffff;color:#000000;overflow-wrap:anywhere;"
                     f"width:{WEIGHTS[table_id][j]}%;text-align:{alignment};")
            if i == 0:
                style += "border-top:1pt solid #000000;border-bottom:0.6pt solid #000000;font-weight:bold;"
            elif i == len(rows) - 1:
                style += "border-bottom:1pt solid #000000;"
            # td rather than th gives Google Docs a predictable native cell map.
            weight = "bold" if i == 0 else "normal"
            # Explicit inline weight prevents a bold insertion-point style in
            # Google Docs from being inherited by pasted body text.
            chunks.append('<td style="' + style + '"><span style="font-family:Times New Roman,Times,serif;'
                          'font-size:10pt;font-weight:' + weight + ';">' + html.escape(value) + "</span></td>")
        chunks.append("</tr>")
    chunks.append("</table>")
    return "\n".join(chunks)


def tex_escape(value):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(c, c) for c in value)


def table_tex(table_id, rows, label, title):
    n = len(rows[0])
    spec = []
    for j, weight in enumerate(WEIGHTS[table_id]):
        align = r"\raggedleft" if j in NUMERIC[table_id] else r"\raggedright"
        spec.append(r">{\hsize=" + f"{n * weight / 100:.6g}" + r"\hsize" + align + r"\arraybackslash}X")
    lines = ["% Requires booktabs, tabularx, array; preserve supplementary IDs.",
             "% IEEE-style layout adaptation; no scientific values changed.",
             r"\begin{table*}[t]", r"\centering", r"\begingroup",
             r"\fontsize{10}{12}\selectfont", tex_escape(label) + r"\\",
             tex_escape(title) + r"\par\smallskip", r"\setlength{\tabcolsep}{4pt}",
             r"\renewcommand{\arraystretch}{1.15}",
             r"\begin{tabularx}{\linewidth}{@{}" + "".join(spec) + "@{}}", r"\toprule"]
    lines.append(" & ".join(r"\textbf{" + tex_escape(x) + "}" for x in rows[0]) + r" \\")
    lines.append(r"\midrule")
    lines.extend(" & ".join(tex_escape(x) for x in row) + r" \\" for row in rows[1:])
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\endgroup", r"\end{table*}", ""])
    return "\n".join(lines)


def render_preview(path, table_id, rows, label, title, note=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties, findfont
    from matplotlib import rc_context
    from PIL import ImageFont
    font = findfont(FontProperties(family="Times New Roman"), fallback_to_default=False)
    bold_font = findfont(FontProperties(family="Times New Roman", weight="bold"), fallback_to_default=False)
    body_fp = FontProperties(fname=font, size=10)
    bold_fp = FontProperties(fname=bold_font, size=10)
    body_measure = ImageFont.truetype(font, size=100)
    bold_measure = ImageFont.truetype(bold_font, size=100)
    width_pt = 6.5 * 72
    pad = 4
    col_widths = [width_pt * w / 100 for w in WEIGHTS[table_id]]

    def measure(value, fp):
        if not value:
            return 0
        measuring_font = bold_measure if fp is bold_fp else body_measure
        return measuring_font.getlength(value) / 10

    def wrap(value, available, fp):
        if not value:
            return [""]
        lines, current = [], ""
        for token in re.findall(r"\S+\s*", value):
            candidate = current + token
            if measure(candidate.rstrip(), fp) <= available:
                current = candidate
                continue
            if current:
                lines.append(current.rstrip())
                current = ""
            # Identifiers may have no whitespace. Break visually, not in data.
            while measure(token.rstrip(), fp) > available:
                count = 1
                while count < len(token) and measure(token[:count + 1], fp) <= available:
                    count += 1
                delimiters = [m.end() for m in re.finditer(r"[/_-]", token[:count])]
                if delimiters and delimiters[-1] >= 5:
                    count = delimiters[-1]
                lines.append(token[:count])
                token = token[count:]
            current = token
        if current:
            lines.append(current.rstrip())
        return lines

    wrapped = [[wrap(v, col_widths[j] - 2 * pad, bold_fp if i == 0 else body_fp)
                for j, v in enumerate(row)] for i, row in enumerate(rows)]
    line_height = 12
    row_heights = [max(len(c) for c in row) * line_height + 2 * pad for row in wrapped]
    title_lines = wrap(title, width_pt - 8, body_fp)
    caption_height = 16 + 12 * len(title_lines) + 12
    note_lines = wrap(note, width_pt - 8, body_fp) if note else []
    height_pt = caption_height + sum(row_heights) + 8
    if note_lines:
        height_pt += 10 + line_height * len(note_lines)
    with rc_context({"font.family": "Times New Roman", "font.size": 10,
                     "pdf.fonttype": 42, "ps.fonttype": 42}):
        fig = plt.figure(figsize=(6.5, height_pt / 72), facecolor="white")
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, width_pt)
        ax.set_ylim(height_pt, 0)
        ax.axis("off")
        ax.text(width_pt / 2, 3, label, ha="center", va="top", fontproperties=body_fp)
        ax.text(width_pt / 2, 19, "\n".join(title_lines), ha="center", va="top", fontproperties=body_fp, linespacing=1.2)
        y = caption_height
        ax.plot([0, width_pt], [y, y], color="black", lw=0.8)
        for i, row in enumerate(wrapped):
            x = 0
            for j, lines in enumerate(row):
                numeric = j in NUMERIC[table_id]
                ax.text(x + col_widths[j] - pad if numeric else x + pad, y + pad,
                        "\n".join(lines), ha="right" if numeric else "left", va="top",
                        fontproperties=bold_fp if i == 0 else body_fp, linespacing=1.2)
                x += col_widths[j]
            y += row_heights[i]
            if i == 0:
                ax.plot([0, width_pt], [y, y], color="black", lw=0.6)
        ax.plot([0, width_pt], [y, y], color="black", lw=0.8)
        if note_lines:
            ax.text(4, y + 10, "\n".join(note_lines), ha="left", va="top",
                    fontproperties=body_fp, linespacing=1.2)
        fig.savefig(path.with_suffix(".pdf"), metadata={"Creator": "render_ieee_tables.py", "CreationDate": None, "ModDate": None})
        fig.savefig(path.with_suffix(".png"), dpi=600)
        plt.close(fig)
    return {"width_inches": 6.5, "height_inches": height_pt / 72,
            "font_points": 10, "font_file_basename": Path(font).name,
            "horizontal_rules": 3, "vertical_rules": 0, "interior_body_rules": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-docx", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--artifact-output", type=Path)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    source_path = out / "source_tables.json"
    if args.source_docx:
        source = extract_source(args.source_docx)
        source_path.write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n")
    else:
        source = json.loads(source_path.read_text())
    manifest = {"schema": "manuscript.ieee_style_table_format.v1", "format_only": True,
                "style_source": STYLE_SOURCE,
                "stable_supplementary_ids_preserved": True,
                "roman_numeral_renumbering_applied": False,
                "new_scientific_calls_or_fits": 0,
                "source_tables_sha256": sha(source_path), "tables": {}}
    captions = []
    for table_id in IDS:
        entry = source["tables"][table_id]
        rows = entry["rows"]
        assert hashlib.sha256(canonical_rows(rows)).hexdigest() == entry["cell_order_sha256"]
        label, title = caption(table_id, entry["caption_old"])
        fragment = '<html><body>\n' + table_html(table_id, rows) + '\n</body></html>\n'
        (out / (table_id + ".html")).write_text(fragment)
        title_html = '<div style="font-family:Times New Roman,Times,serif;font-size:10pt;text-align:center;color:#000;background:#fff;margin-bottom:8pt;">' + html.escape(label) + '<br>' + html.escape(title) + '</div>'
        standalone = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>' + html.escape(label) + '</title></head><body style="margin:24px;background:white;">' + title_html + table_html(table_id, rows) + '</body></html>\n'
        (out / (table_id + ".standalone.html")).write_text(standalone)
        (out / (table_id + ".tsv")).write_text("\n".join("\t".join(row) for row in rows) + "\n")
        (out / (table_id + ".tex")).write_text(table_tex(table_id, rows, label, title))
        preview = render_preview(out / table_id, table_id, rows, label, title)
        files = {suffix: {"sha256": sha(out / (table_id + suffix)), "bytes": (out / (table_id + suffix)).stat().st_size}
                 for suffix in (".html", ".standalone.html", ".tsv", ".tex", ".pdf", ".png")}
        manifest["tables"][table_id] = {"row_count_including_header": len(rows), "column_count": len(rows[0]),
                                        "cell_order_sha256": entry["cell_order_sha256"],
                                        "numeric_columns_zero_based": NUMERIC[table_id],
                                        "caption_label": label, "caption_title": title,
                                        "render": preview, "files": files}
        captions.append({"id": table_id, "old": entry["caption_old"], "new": label + "\n" + title,
                         "label": label, "title": title, "caption_font_points": 10,
                         "alignment": "center", "terminal_period": False})
    (out / "caption_oldnew.json").write_text(json.dumps(captions, indent=2, ensure_ascii=False) + "\n")
    (out / "expected_cells.json").write_text(json.dumps({table_id: source["tables"][table_id]["rows"] for table_id in IDS}, indent=2, ensure_ascii=False) + "\n")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if args.artifact_output:
        import shutil
        args.artifact_output.mkdir(parents=True, exist_ok=True)
        for file in out.iterdir():
            if file.is_file():
                shutil.copy2(file, args.artifact_output / file.name)
    print("Formatted seven tables; 414 cells unchanged; 600 dpi previews; no scientific calls")


if __name__ == "__main__":
    main()
