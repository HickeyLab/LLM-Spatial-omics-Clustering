# IEEE-style supplementary tables

These are format-only versions of the seven retained manuscript tables. The exact **414 cell strings, their order, numerical values and units are unchanged** from the verified Google Docs accepted view. Tables S6a–d also match their frozen scored CSVs exactly.

The [IEEE Editorial Style Manual](https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf) places a table's label and descriptive caption above it. These assets use centered captions, Times New Roman at 10 pt, a white background, right-aligned numerical columns, and only top, header-bottom and bottom horizontal rules. Vertical rules and interior body-row grids are omitted. **Existing supplementary identifiers are retained**; IEEE's Roman-numeral renumbering convention has not been applied.

| Table | Preview | Editable sources |
| --- | --- | --- |
| S1 | [PDF](S1.pdf) / [600 dpi PNG](S1.png) | [HTML](S1.standalone.html) / [LaTeX](S1.tex) / [TSV](S1.tsv) |
| S2A | [PDF](S2A.pdf) / [600 dpi PNG](S2A.png) | [HTML](S2A.standalone.html) / [LaTeX](S2A.tex) / [TSV](S2A.tsv) |
| S2B | [PDF](S2B.pdf) / [600 dpi PNG](S2B.png) | [HTML](S2B.standalone.html) / [LaTeX](S2B.tex) / [TSV](S2B.tsv) |
| S6a | [PDF](S6a.pdf) / [600 dpi PNG](S6a.png) | [HTML](S6a.standalone.html) / [LaTeX](S6a.tex) / [TSV](S6a.tsv) |
| S6b | [PDF](S6b.pdf) / [600 dpi PNG](S6b.png) | [HTML](S6b.standalone.html) / [LaTeX](S6b.tex) / [TSV](S6b.tsv) |
| S6c | [PDF](S6c.pdf) / [600 dpi PNG](S6c.png) | [HTML](S6c.standalone.html) / [LaTeX](S6c.tex) / [TSV](S6c.tsv) |
| S6d | [PDF](S6d.pdf) / [600 dpi PNG](S6d.png) | [HTML](S6d.standalone.html) / [LaTeX](S6d.tex) / [TSV](S6d.tsv) |

The short `.html` files contain only the table for native Google Docs replacement. The `.standalone.html`, PDF, PNG and LaTeX versions include the caption above the table. [Caption changes](caption_oldnew.json) record case, line separation and terminal punctuation. Literal filenames keep their exact case. The LaTeX fragments require `booktabs`, `tabularx` and `array`.

For native Google Docs replacement, set the insertion paragraph to **Normal text** before pasting. Body spans explicitly use normal weight and header spans use bold. Verify the saved export's cell paragraph styles as well as its borders: a heading style at the insertion point can otherwise put table cells in the document outline.

Rebuild without opening Google Docs or reading a private Word export:

```bash
python3.12 scripts/revision/render_ieee_tables.py
```

The default build reads [source_tables.json](source_tables.json), whose source export checksum and per-table cell-order checksums preserve lineage. To deliberately refresh that input, supply `--source-docx PATH`. The renderer asserts the seven expected tables and exact frozen S6 CSV equality before accepting a new source. It has no API, inference, fitting or scoring path. The [manifest](manifest.json) records each output's checksum, dimensions and formatting rules. [Verification](verification.json) checks the editable HTML/TSV cells, PDF type sizes, horizontal-only rule geometry and PNG resolution.
