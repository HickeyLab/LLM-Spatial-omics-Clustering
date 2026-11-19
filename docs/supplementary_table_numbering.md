# Current supplementary tables

The saved manuscript contains 21 displayed supplementary tables. Table S7 is supplied as two companion files. The [table crosswalk](../configs/supplementary_table_crosswalk.json) pins the current sources and their hashes.

| Display label | Content | Current source |
| --- | --- | --- |
| S1 | REDSEA matching and cell retention | [Table_S1.csv](tables/ieee_reviewer47_20261119/Table_S1.csv) |
| S2A | Frozen clustering configurations and hyperparameters | [Table_S2A.csv](tables/ieee_reviewer47_20261119/Table_S2A.csv), [47-marker clustering manifest](../data/frozen/clustering47_primary_20261108/manifest.json) |
| S6a | Equal-test-region agreement for both input arms and paired change | [Table_S6a.csv](tables/ieee_reviewer47_20261119/Table_S6a.csv) |
| S6d | Requested model identities, transport and inference settings | [Table_S6d.csv](tables/ieee_reviewer47_20261119/Table_S6d.csv), [completed execution records](revision/reviewer47_completed_publication_20261115.md) |
| S7 | Twelve conditional clustering comparisons | [conditional_comparisons.csv](../data/frozen/clustering47_primary_20261108/conditional_comparisons.csv), [96 regional observations](../data/frozen/clustering47_primary_20261108/paired_regional_observations.csv) |
| S8a–d | Four marker representations, one table per model | [IEEE tables](tables/ieee_reviewer47_20261119/manifest.json), [complete condition metrics and coverage](../data/frozen/astra_prompt_controls_results_20261115/set_metrics.csv) |
| S9 | Five Opus 5.5 controls and two Astra–Leiden controls | [Table_S9.csv](tables/ieee_reviewer47_20261119/Table_S9.csv), [full contrasts](../data/frozen/astra_prompt_controls_results_20261115/control_contrasts.csv) |
| S10 | Conventional B004 annotation classifiers | [Table_S10.csv](tables/ieee_reviewer47_20261119/Table_S10.csv) |
| S11 | K100/K200 post-clustering coarsening | [Table_S11.csv](tables/ieee_reviewer47_20261119/Table_S11.csv) |
| S12a–d | Cross-model support calibration by model | [IEEE tables](tables/ieee_reviewer47_20261119/manifest.json), [complete selective-risk observations](../data/frozen/reviewer47_results_20261111/calibration/calibration_risk_coverage.csv) |
| S13a–b | Native-28-label cross-donor annotation and complete prediction delivery | [Donor source bank](../data/frozen/donor47_deepseek_completion_20261116/manifest.json) |
| S14a–b | Frozen cross-donor clustering and SpatialSort seed sensitivity; ready | [Table_S14a.csv](tables/ieee_donor47_20261116/Table_S14a.csv), [Table_S14b.csv](tables/ieee_donor47_20261116/Table_S14b.csv) |
| S15a–b | Same-cell native-28-label versus projected-23-label sensitivity | [Donor source bank](../data/frozen/donor47_deepseek_completion_20261116/manifest.json) |

Tables S6a and S8a–d report single-run outcomes with equal weighting of the two B004 test regions. The original 28-label vocabulary includes Noise, and absent-class F1 is zero within each test region before equal region averaging. The [saved table notes](tables/ieee_reviewer47_20261119/source_tables.json) specify the units and denominators.

S7 contains all six method pairs for weighted F1 and cluster purity, with Holm correction across those 12 comparisons. The supplementary methods describe the regional sign-exchangeability assumptions and within-donor scope. [GitHub manuscript](manuscript_primary47.md)

Earlier versions of S2B, S6b and S6c are available in the [IEEE archive](tables/ieee/manifest.json) and [November 11 reviewer table snapshot](tables/ieee_reviewer47_20261111/manifest.json). Earlier studies and their reconstruction entry points are available in the [checksum archive](../data/historical/publication_before_primary47_20261109/index.json).

The [B004 and methods table package](tables/ieee_reviewer47_20261119/README.md) contains the editable tables and previews. The [B005/B006 table package](tables/ieee_donor47_20261116/manifest.json) contains S13a–b, S14a–b and S15a–b. Figure 5C–D presents the equal-donor classifier comparison. S15 includes coverage under the projected vocabulary.
