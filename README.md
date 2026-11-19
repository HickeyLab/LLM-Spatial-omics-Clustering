# Evaluation of Clustering Methods and Large Language Models for Spatial Proteomic Cell Type Annotation

## Current manuscript figures

Read the [manuscript](docs/manuscript_primary47.md) or browse [Figures 1–5 and S1–S14](figures/current_manuscript/PNG) and their [captions](figures/current_manuscript/Figure_captions.txt).

The study comprises **809,550 cells across 24 tissue regions from three donors**. B004 supplies within-donor benchmarking and classifier development. B005/B006 supply cross-donor evaluation. All annotation evidence uses 47 protein markers and the native 28-label vocabulary including Noise.

The B004 primary campaign comprises **220,082 cells, four clustering methods, four models, two marker-representation arms, 32 annotation sets, 128 accepted logical request items and 9,024 cluster predictions**. The [B004 study record](configs/annotation47_active_study.json) and [primary results](data/frozen/annotation47_results_20261111/manifest.json) define those publication inputs.

In B004, Leiden, FlowSOM, SpatialSort and PIXIE have 300, 299, 229 and 300 occupied clusters. FlowSOM used three complete shuffled passes, and the primary SpatialSort partition is seed 42 at sweep 100 with `dmh_iter=5`. Seed 43 remains a clustering sensitivity result. The annotation models are GPT-6 Astra, Claude Opus 5.5, Gemini 4 Argon and DeepSeek V4.1 Flash 1017.

## Figure reproduction

The [manuscript figure map](docs/figure_map.md) and [notebook index](notebooks/final_figures/README.md) map all 19 figures to their sources. The saved manuscript artwork contains 21 PNGs because Figure S5 has three parts. The [display crosswalk](configs/manuscript_display_crosswalk.json) binds the current figure numbers and artwork hashes to the stable identifiers used in [native figure exports](figures/publication). Figure S14 is available as saved manuscript artwork.

## Annotation results and scoring

The means-plus-fractions arm supplies the benchmark. Reference agreement is calculated separately in the two fixed test regions and averaged equally; fixed-vocabulary macro-F1 averages all 28 label-specific F1 scores, assigning zero to absent classes, within each region before equal region weighting. Noise remains a valid label. The paired study subtracts means-only outcomes from means-plus-fractions outcomes. All final B004 primary annotation sets have complete cluster and cell delivery.

Across the 16 benchmark combinations, equal-test-region agreement ranges from **17.42% to 58.12%** and macro-F1 from **0.114 to 0.449**. Leiden–Astra has the highest agreement in these two regions. Adding fractions is associated with higher agreement in eight conditions and lower agreement in eight, with changes from **−10.25 to +6.50 percentage points**. These are descriptive single-run outcomes on existing B004 partitions, not estimates of repeated-call variability or generalization to new donors.

Figure 4 uses the Leiden–Astra pipeline selected for detailed presentation from the B004 benchmark results. Figure S1 retains Leiden–Opus 5.5 as a supplementary comparison. The three Figure 4 example clusters were selected by cell count before outcomes were inspected. Figure S11 uses one accepted prediction per model, fixed model-order modal ties, and no reference-label filtering to select CD8+ T groups.

The [B004 presentation amendment](docs/revision/b004_astra_presentation_amendment_20261111.md) records this selection.

## Cross-donor evaluation

B005 and B006 contain **288,188 and 301,280 cells**, respectively, with eight regions each. Frozen Leiden, FlowSOM, SpatialSort and PIXIE partitions retain every donor cell. FlowSOM used three all-cell passes; primary SpatialSort used seed 42 at 50 actual sweeps with `dmh_iter=5`. Native Leiden-parent and PIXIE image inputs retain Hoechst1 as well as 47 proteins; all annotation profiles use 47 proteins only. The [donor score bank](data/frozen/donor47_deepseek_completion_20261116/manifest.json) provides the terminal response bank and offline results. Figure S12 and Tables S14a/b use equal-region clustering metrics and global common-cell seed ARI as specified.

The all-marker means plus fractions arm contains **32 donor–method–model sets, 128 accepted logical items and 9,468 of 9,468 delivered cluster predictions**. Five DeepSeek recoveries supplied the 375 labels absent from the November 14 bank. All 123 previously accepted responses, frozen assignments and B004 classifier baselines were preserved. Equal-donor agreement ranges from **21.14% to 38.57%** across the 16 LLM–method combinations. The B004-selected Leiden–Astra pipeline reaches **35.87%**. The 23-label sensitivity uses the same reference-eligible cells for both vocabularies. [Offline scoring replay](docs/manuscript_reproduction.md#completed-cross-donor-scoring) and [six donor tables](docs/tables/ieee_donor47_20261116/manifest.json) are available.

## Reviewer experiments

The [completed B004 reviewer package](configs/reviewer47_completed_publication_20261115.json) contains **71 completed sets, 284 accepted items and 20,076 cluster predictions**, including the primary benchmark. The completion adds a recovered 75-cluster DeepSeek–Leiden selected-means item and eight Astra control requests to the [November 11 snapshot](data/frozen/reviewer47_results_20261111/manifest.json).

Figure S10 and Tables S8a–d report the four marker representations. DeepSeek–Leiden selected means reaches **41.42% agreement and 0.3576 macro-F1** with all 300 cluster predictions delivered. Figure S2A–B and Table S9 report seven matched prompt contrasts. For Leiden–Astra, agreement was **58.12%** at baseline, **53.53%** with the method name and **51.43%** with measured neighborhood expression. Figure S2C–D and Tables S12a–d summarize within-donor calibration. Tables S10 and S11 report the matched supervised classifiers and post-clustering K=100/200 coarsening.

The [completed execution record](docs/revision/reviewer47_completed_publication_20261115.md) documents the actual settings, routes, recoveries and known charges. The original [execution summary](docs/revision/reviewer47_execution_summary_20261111.json), [per-request settings](data/frozen/reviewer47_results_20261111/model_settings.json) and [physical-attempt accounting](data/frozen/reviewer47_results_20261111/logical_physical_accounting.json) describe the November 11 snapshot. Unresolved billing remains unknown.

The [offline B004 replay](docs/manuscript_reproduction.md#reviewer-controls-and-recalibration-replay) validates the pinned requests and saved visible responses and recomputes the scores without credentials or an H5AD file.

## Tables and offline reproduction

The [table index](docs/supplementary_table_numbering.md) links the 21 displayed supplementary tables and their source files. Table S7 is supplied as files containing the 12 clustering comparisons and 96 paired regional observations.

```bash
python3.12 -m pip install -r requirements-reviewer47.txt
python3.12 -B scripts/replay_completed_reviewer47.py --output outputs/reviewer47_completed_replay
```

Use a fresh output path for each run. The [reproduction guide](docs/manuscript_reproduction.md) also covers donor replay, optional offline recalibration and figure generation.

## Archived evidence

[The checksum-indexed publication archive](data/historical/publication_before_primary47_20261109/index.json) preserves excluded figures and studies; stable experiment IDs remain in the [registry](configs/experiment_registry.json). Earlier reconstruction code and the immutable [revision release](https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/releases/tag/revision-2026-10-30-v1) remain available as archival evidence. Those inputs do not define the current annotation figures or active manuscript claims. No archival release or frozen preparation was overwritten.
