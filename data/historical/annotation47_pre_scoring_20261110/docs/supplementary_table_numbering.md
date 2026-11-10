# Current supplementary table numbering

Display labels follow the manuscript checked on November 6, 2026. Original companion filenames and bytes are preserved, including names with earlier table numbers. The pinned [companion crosswalk](../configs/supplementary_table_crosswalk.json) records the retained released files. The current display map below also identifies the relocated Table S9.

| Earlier identifier | Current manuscript label | Content |
| --- | --- | --- |
| S8 matching | S1 | REDSEA shared-object matching and retention |
| S1 | S2A/B | Clustering settings and channel membership |
| S2 | S3 archival entry | Retrospective marker-name export records, with the earlier numerical grids archived |
| S3a–f | S4a–f | Controlled annotation and donor transfer |
| S4a–j | S5a–j | Repeats, prompt controls, calibration, neighborhood and historical settings |
| S6a–d | S6a–d | Paired marker representations |
| S5 conditional comparisons | S7 | Conditional paired regional comparisons |
| S7a–b | S8a–b | Label-mapping sensitivity |
| Main Table 2 | S9 | Paired absolute B005/B006 agreement without and with labeled reference profiles, plus the equal-donor average |

The current numerical supplementary tables are S1, S2A, S2B, S5i, S5j, S6a, S6c, S6d, S8a and S9. Other entries point to complete companion records or archived data. S6a and S6c remain in the manuscript, and their full CSVs are preserved.

The retained [native-cell snapshot](../data/frozen/manuscript_replay/tables/current_tables.json) uses earlier display labels and includes grids no longer printed in the current manuscript. Its entry with label `2` contains the unchanged values now displayed as Table S9. Those values are also supported by [donor metrics](../data/frozen/manuscript_replay/tables/companions/S3b_donor_metrics.csv) and [equal-donor metrics](../data/frozen/manuscript_replay/tables/companions/S3c_equal_donor_metrics.csv), using `external_common5px`, `marker_only` and `retrieval` records. Main Table 1 retains the conventional classifier comparison.

Table S7 retains all 60 conditional regional comparisons and their assumptions. Eight regional pairs cannot establish equivalence or general method superiority. These descriptive and conditional records remain available alongside the matching audit, label-mapping sensitivity and inference settings.

```bash
python scripts/render_current_tables.py
python scripts/render_table_s01.py  # legacy filename, current Table S2A
python scripts/render_table_s02.py  # legacy filename, current Table S3
```

The latter two commands create separate editable DOCX/HTML outputs under `outputs/manuscript_replay/`. They do not modify the manuscript. Their configuration and frozen data paths retain legacy identifiers for compatibility. Historical presentation audits under `docs/archive/` describe earlier numbering and are not current table inventories.
