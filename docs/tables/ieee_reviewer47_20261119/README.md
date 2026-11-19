# Current B004 and methods supplementary tables

These 15 tables match the November 19 saved manuscript. The [table index](../../supplementary_table_numbering.md) also links the file-only Table S7 and the six B005/B006 tables.

| Tables | Contents |
| --- | --- |
| [S1](S1.standalone.html), [S2A](S2A.standalone.html) | REDSEA matching and retention, and clustering configurations |
| [S6a](S6a.standalone.html), [S6d](S6d.standalone.html) | Paired reference agreement and executed model settings |
| [S8a](S8a.standalone.html), [S8b](S8b.standalone.html), [S8c](S8c.standalone.html), [S8d](S8d.standalone.html) | Four marker representations across four models, including the completed DeepSeek condition |
| [S9](S9.standalone.html) | Seven matched prompt controls, including both Astra controls |
| [S10](S10.standalone.html), [S11](S11.standalone.html) | Conventional classifiers and merging of existing clusters |
| [S12a](S12a.standalone.html), [S12b](S12b.standalone.html), [S12c](S12c.standalone.html), [S12d](S12d.standalone.html) | Cross-model support calibration |

The [combined HTML](all_tables.html) shows all tables and notes. The [manifest](manifest.json) pins the CSV, TSV, HTML, LaTeX, PDF and PNG files. [Source cells](source_tables.json) record each table’s evidence and hash. [Completed set metrics](../../../data/frozen/astra_prompt_controls_results_20261115/set_metrics.csv) retain request and cluster delivery counts for S8a–d.

Rebuild the IEEE-style exports from the checked scientific sources with Python, pandas, matplotlib, Pillow and Times New Roman installed.

```sh
SOURCE_DATE_EPOCH=0 MPLBACKEND=Agg python3 scripts/revision/render_reviewer47_tables.py
```

The [November 11 snapshot](../ieee_reviewer47_20261111/README.md) preserves the earlier release.
