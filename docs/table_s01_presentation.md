# Table S1 presentation revision

The current native Table S1 remains an editable comparison of Leiden, FlowSOM,
SpatialSort and PIXIE. The presentation uses a pale blue-gray header, a subtle
field column, bold method names, consistent Arial typography, light gray rules
and generous cell padding. Short numerical entries are centered, while longer
settings are left aligned. Text is vertically centered, rows expand to fit
content and the header repeats if the table spans pages.

The five columns deliberately total 6.5 inches, fitting the portrait manuscript
text width. Body type is 9.5 pt and headers are 10 pt. The table and unchanged
caption fit on one page. There are no fixed row heights that could clip text.

All **45 cell texts** and the **caption** match the current manuscript export.
The rendered PDF table was independently extracted and checked cell by cell,
ignoring only line-wrap whitespace. The full page was visually inspected.
No hyperparameter, biological label or numerical result changed.

The manuscript table is the content authority for this formatting task. The
older notebook's three-column table has a different historical presentation
and is not substituted for it. Frozen content and provenance are in
`data/frozen/table_s01/manuscript_table.json` and
`table_s01_presentation_audit.json`.

```bash
python scripts/render_table_s01.py --output-dir /tmp/table_s01
python scripts/render_table_s01.py --check /tmp/table_s01/Table_S1_professional.docx
```

The script produces an editable DOCX and a styled HTML table for the existing
native document. Apply the document workflow's title sanitizer, render the
DOCX, and inspect its page before native insertion. The PNG in
`notebooks/final_figures/previews/table_s01.png` is a review snapshot from that
verified rendering. It is not used as a substitute for the editable table.

Native editable formatting is applied. The exported DOCX preserves all 45 cells
and the caption, and the native PDF confirms Arial typography and one-page
table/caption placement. Unrelated suggestions remain pending review.
