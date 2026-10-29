# IEEE-style Table S1

Table S1 follows the user's supplied IEEE-style example: Times New Roman,
white cells, no vertical borders or body-row grid, and black horizontal rules
at the top, below the header and at the bottom. The centered TABLE S1 label
and uppercase descriptive title sit above the table. Original explanatory
caption notes sit below it. Supplementary numbering is retained for manuscript
cross-references. This is the requested visual style, not a claim of
venue-template certification.

The five columns total 6.5 inches. Body and header type are 10 pt. Short values
are centered, while longer settings are left aligned and vertically centered.
Automatic row heights and consistent padding let text wrap naturally.
The table, title and notes fit on one portrait page.

All **45 cell texts** remain identical to the current manuscript source.
Every caption word is retained, with capitalization and placement changed for
the requested style. The native DOCX was checked cell by cell. Independent
native PDF extraction matches all word/value counts, confirms Times New Roman
for visible text and confirms there are no vertical rules. Local and native
pages were visually inspected. No hyperparameter, label or result changed.

The manuscript table is the content authority for this formatting task. The
older notebook's three-column table has a different historical presentation
and is not substituted for it. Frozen content and provenance are in
`data/frozen/table_s01/manuscript_table.json` and
`table_s01_presentation_audit.json`.

```bash
python scripts/render_table_s01.py --output-dir /tmp/table_s01
python scripts/render_table_s01.py --check /tmp/table_s01/Table_S1_IEEE.docx
```

The script produces an editable DOCX and native HTML with the caption, table
and notes. Apply the document workflow's title sanitizer, render the
DOCX, and inspect its page before native insertion. The PNG in
`notebooks/final_figures/previews/table_s01.png` is a review snapshot from that
verified rendering. It is not used as a substitute for the editable table.

IEEE-style formatting is applied in Google Docs. Only this formatting
replacement was accepted. Unrelated suggestions remain pending review.
