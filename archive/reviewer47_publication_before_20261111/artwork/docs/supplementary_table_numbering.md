# Current supplementary tables

The retained manuscript uses the following table identifiers without renumbering the excluded studies. The [current companion crosswalk](../configs/supplementary_table_crosswalk.json) pins their source paths and hashes. Current annotation tables come from the completed 47-marker, original-28-label single-annotation campaign.

| Display label | Content | Current source |
| --- | --- | --- |
| S1 | REDSEA matching and cell retention | [Matching audit notebook](../notebooks/final_figures/table_s1_matching_and_retention.ipynb) |
| S2A/B | Frozen clustering configurations and channel membership | [Clustering/channel notebook](../notebooks/final_figures/table_s2_clustering_and_channels.ipynb), [47-marker clustering manifest](../data/frozen/clustering47_primary_20261108/manifest.json) |
| S6a | Equal-test-region agreement for both input arms and paired change | [Table_S6a.csv](../data/frozen/annotation47_results_20261110/Table_S6a.csv) |
| S6b | Fixed-28-label macro-F1 and prediction coverage | [Table_S6b.csv](../data/frozen/annotation47_results_20261110/Table_S6b.csv) |
| S6c | Paired agreement change and delivery terms | [Table_S6c.csv](../data/frozen/annotation47_results_20261110/Table_S6c.csv) |
| S6d | Actual accepted model settings and transport | [Table_S6d.csv](../data/frozen/annotation47_results_20261110/Table_S6d.csv), [execution summary](../data/frozen/annotation47_results_20261110/actual_execution_summary.json) |
| S7 | Twelve conditional clustering comparisons | [conditional_comparisons.csv](../data/frozen/clustering47_primary_20261108/conditional_comparisons.csv), [96 regional observations](../data/frozen/clustering47_primary_20261108/paired_regional_observations.csv) |

S6 reports one accepted prediction per condition and no across-repetition SD. The original 28-label vocabulary includes Noise, and absent-class F1 is zero within each test region before equal region averaging. Complete final delivery makes the S6c delivery term zero; the valid-label term equals the observed total change and is a descriptive arithmetic decomposition. [Table notes](../data/frozen/annotation47_results_20261110/table_notes.json) record units, denominators and confirmed cost scope.

S7 contains all six method pairs for weighted F1 and cluster purity, with Holm correction across those 12 comparisons. It does not contain the excluded annotation comparison family. Its regional sign-exchangeability assumptions and within-donor limitations remain explicit.

Main Table 1 and Tables S3, S4, S5, S8 and S9 are excluded from the active manuscript. Their prior table grids, companion filenames and reconstruction entry points remain in the [checksum archive](../data/historical/publication_before_primary47_20261109/index.json) and immutable release. `scripts/render_current_tables.py`, `scripts/render_table_s01.py`, `scripts/render_table_s02.py` describe archival snapshots and earlier display labels; they must not be used as current annotation table sources.
