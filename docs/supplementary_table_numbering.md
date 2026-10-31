# Current supplementary table numbering

Display labels follow the October 31 manuscript snapshot. Original companion filenames and bytes are preserved, including names that contain an earlier table number. The machine-readable mapping is [supplementary_table_crosswalk.json](../configs/supplementary_table_crosswalk.json).

| Earlier identifier | Current manuscript label | Content |
| --- | --- | --- |
| S8 matching | S1 | REDSEA shared-object matching and retention |
| S1 | S2A/B | Clustering settings and channel membership |
| S2 | S3A–D | Retrospective marker-name-list parameter selection |
| S3a–f | S4a–f | Controlled annotation and donor transfer |
| S4a–j | S5a–j | Repeats, prompt controls, calibration, neighborhood and historical settings |
| S6a–d | S6a–d | Paired marker representations |
| S5 conditional comparisons | S7 | Conditional paired regional comparisons |
| S7a–b | S8a–b | Label-mapping sensitivity |

Native manuscript table cells and notes are frozen in `data/frozen/manuscript_replay/tables/current_tables.json`. The display notebooks show those cells before the complete companion records where both exist. Missing native tables are supplied as their released companions. Main Tables I and II are also retained in the native-cell snapshot, with no changes to their values.

```bash
python scripts/render_current_tables.py
python scripts/render_table_s01.py  # legacy filename, current Table S2A
python scripts/render_table_s02.py  # legacy filename, current Table S3
```

The latter two commands create separate editable DOCX/HTML outputs under `outputs/manuscript_replay/`. They do not modify the manuscript. Their configuration and frozen data paths retain legacy identifiers for compatibility. Historical presentation audits under `docs/archive/` describe earlier numbering and are not current table inventories.
