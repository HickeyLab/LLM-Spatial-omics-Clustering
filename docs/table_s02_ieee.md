# IEEE-style Table S2

Table S2 matches the supplied S1 style: Times New Roman, a centered uppercase
caption above, black rules at the top/header/bottom, no shading and no vertical
borders. All four original parts remain: A candidate ranges, B cardinalities,
C fine-grid search spaces and D recorded export settings.

The four editable tables use 10 pt text and span two portrait pages, A/B then
C/D. The second page repeats TABLE S2 (CONTINUED), and the unchanged provenance
notes follow D. Semantic header line breaks prevent words from splitting
inside narrow columns. This layout avoids shrinking the table to fit one page.

All 135 native cells exactly match the frozen presentation input. All 20 selected
parameters, ranges and cardinalities are preserved. The native DOCX was checked
cell by cell. Independent native PDF text matches every expected word and value
on both pages, uses Times New Roman for visible text and has no vertical rules.
Both local and native pages were visually inspected. Table S1 cells are unchanged.

```bash
python scripts/render_table_s02.py --output-dir /tmp/table_s02_ieee
python scripts/render_table_s02.py --check /tmp/table_s02_ieee/Table_S2_IEEE.docx
```

The renderer checks the frozen JSON and analytical CSV checksums, inherits S1's
style configuration, and produces editable DOCX and per-page native HTML.
Use the document workflow's sanitizer and render/inspection steps before native
insertion. Current publication previews are `table_s02_ieee_page_1.png` and
`table_s02_ieee_page_2.png`. The earlier `table_s02.png` remains a historical,
reproducible label-overlay snapshot rather than the current table style.

The canonical notebook also renders its compact four-part overview with serif
text, white cells and horizontal rules. All three display-only cells were
executed and the existing three source/notebook/preview tests passed. No
parameter search, model call, fit or rescoring was performed.

The native image was replaced with editable tables and the existing, authorized
Table S2 caption edits were accepted to move their wording into the new layout.
Unrelated manuscript suggestions were left intact. The legacy 50-cluster export
qualification and distinction from original numerical LLM prompt profiles remain.
