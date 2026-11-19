# November 11 B004 annotation and reviewer table snapshot

The [current manuscript table package](../ieee_reviewer47_20261119/README.md) includes the completed DeepSeek and Astra controls.

In this snapshot, S6a–d report the full-arm benchmark, S8a–d report the four
marker representations, S9 reports the completed Opus controls, S10 reports
supervised classifiers, S11 reports partition coarsening, and S12a–d report
cross-model agreement calibration. The DeepSeek selected-means condition was
pending at the time, with planned-cluster delivery shown in the table.

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

The [archived renderer](https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/blob/914de55d2cd739390721c9ec333af7af47389e59/scripts/revision/render_reviewer47_tables.py) reproduces this snapshot from its release checkout.
