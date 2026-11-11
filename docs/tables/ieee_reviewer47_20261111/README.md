# Current B004 annotation and reviewer tables

S6a–d are the current full-arm benchmark display tables. S8a–d report the
four marker representations, S9 the completed Opus controls, S10 supervised
classifiers, S11 partition coarsening, and S12a–d cross-model agreement
calibration. The one incomplete DeepSeek selected-means condition remains
Pending, with its planned-cluster delivery shown and no partial accuracy.

`source_tables.json` preserves exact display cells and evidence hashes.
`manifest.json` pins editable HTML, CSV/TSV, LaTeX and PDF/PNG previews.
All tables use Times New Roman, 10-point type, centered uppercase captions,
three horizontal rules and no vertical grid or body rules. HTML notes and
PDF previews retain the population, supervision and interpretation limits.

Use individual `.html` files for native Google Docs insertion.
`all_new_tables.html` combines the eleven new reviewer tables; it omits S6,
whose existing native tables can receive narrow cell updates. The source
and numerically complete raw companions remain in the two frozen 20261111
result banks. S1 and S2A/B retain their existing IEEE exports one directory up.

Rebuild presentation exports without inference, fitting or network access:

```sh
python3 scripts/revision/render_reviewer47_tables.py
```
