# Evaluation of Clustering Methods and LLMs for CODEX Cell-Type Annotation

The study comprises **809,550 cells across 24 tissue regions from three donors**. B004 supplies within-donor benchmarking and classifier development; B005/B006 supply cross-donor evaluation. All annotation evidence uses 47 protein markers and the native 28-label vocabulary including Noise.

The B004 primary campaign comprises **220,082 cells, four clustering methods, four models, two marker-representation arms, 32 annotation sets, 128 accepted logical request items and 9,024 cluster predictions**. The [B004 active study record](configs/annotation47_active_study.json), [figure inventory](configs/manuscript_inventory.json) and [B004 scored result manifest](data/frozen/annotation47_results_20261111/manifest.json) define those publication inputs.

In B004, Leiden, FlowSOM, SpatialSort and PIXIE have 300, 299, 229 and 300 occupied clusters. FlowSOM used three complete shuffled passes, and the primary SpatialSort partition is seed 42 at sweep 100 with `dmh_iter=5`. Seed 43 remains a clustering sensitivity result. The annotation models are GPT-6 Astra, Claude Opus 5.5, Gemini 4 Argon and DeepSeek V4.1 Flash 1017.

## Retained figures

[Download or view the current manuscript figures](figures/current_manuscript/PNG).

| Manuscript figure | Native source | Panels | Notebook |
| --- | --- | --- | --- |
| 1 | 1 | A–F | [figure_01_spillover_compensation.ipynb](notebooks/final_figures/figure_01_spillover_compensation.ipynb) |
| 2 | 2 | A–H | [figure_02_clustering_method_benchmark.ipynb](notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb) |
| 3 | 3 | A–E | [figure_03_llm_annotation_benchmark.ipynb](notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb) |
| 4 | 4 | A–E | [figure_04_leiden_gpt_end_to_end.ipynb](notebooks/final_figures/figure_04_leiden_gpt_end_to_end.ipynb) |
| 5 | 5 | A–D | [figure_05_cross_donor_annotation.ipynb](notebooks/final_figures/figure_05_cross_donor_annotation.ipynb) |
| S1 | S6 | A–B | [figure_s01_annotation_diagnostics.ipynb](notebooks/final_figures/figure_s01_annotation_diagnostics.ipynb) |
| S2 | S9 | A–D | [figure_s02_prompt_controls_and_calibration.ipynb](notebooks/final_figures/figure_s02_prompt_controls_and_calibration.ipynb) |
| S3 | S1 | A–C | [figure_s03_compensation_metrics.ipynb](notebooks/final_figures/figure_s03_compensation_metrics.ipynb) |
| S4 | S2 | A–B | [figure_s04_compensation_spatial_maps.ipynb](notebooks/final_figures/figure_s04_compensation_spatial_maps.ipynb) |
| S5 | S3 | A–C | [figure_s05_matching_and_compensation.ipynb](notebooks/final_figures/figure_s05_matching_and_compensation.ipynb) |
| S6 | S4 | A–D | [figure_s06_reference_and_clustering_diagnostics.ipynb](notebooks/final_figures/figure_s06_reference_and_clustering_diagnostics.ipynb) |
| S7 | S5 | A | [figure_s07_reference_bounds.ipynb](notebooks/final_figures/figure_s07_reference_bounds.ipynb) |
| S8 | S7 | Unlettered | [figure_s08_agreement_decomposition.ipynb](notebooks/final_figures/figure_s08_agreement_decomposition.ipynb) |
| S9 | S10 | A–D | [figure_s09_paired_representations.ipynb](notebooks/final_figures/figure_s09_paired_representations.ipynb) |
| S10 | S8 | A–D | [figure_s10_marker_representation_controls.ipynb](notebooks/final_figures/figure_s10_marker_representation_controls.ipynb) |
| S11 | S11 | A | [figure_s11_cd8_profiles.ipynb](notebooks/final_figures/figure_s11_cd8_profiles.ipynb) |
| S12 | S12 | A–C | [figure_s12_donor_clustering.ipynb](notebooks/final_figures/figure_s12_donor_clustering.ipynb) |
| S13 | S13 | A–D | [figure_s13_donor_label_projection.ipynb](notebooks/final_figures/figure_s13_donor_label_projection.ipynb) |

There are 18 manuscript figure identifiers and 20 image files because manuscript Figure S5 has three parts. The [display crosswalk](configs/manuscript_display_crosswalk.json) keeps manuscript labels separate from stable native renderer IDs and source filenames. [Current figure notebooks](notebooks/final_figures/README.md) use the current manuscript numbering.

## Annotation results and scoring

The means-plus-fractions arm supplies the benchmark. Reference agreement is calculated separately in the two fixed test regions and averaged equally; fixed-vocabulary macro-F1 averages all 28 label-specific F1 scores, assigning zero to absent classes, within each region before equal region weighting. Noise remains a valid label. The paired study subtracts means-only outcomes from means-plus-fractions outcomes. All final B004 primary annotation sets have complete cluster and cell delivery.

Across the 16 benchmark combinations, equal-test-region agreement ranges from **17.42% to 58.12%** and macro-F1 from **0.114 to 0.449**. Leiden–Astra has the highest agreement in these two regions. Adding fractions is associated with higher agreement in eight conditions and lower agreement in eight, with changes from **−10.25 to +6.50 percentage points**. These are descriptive single-run outcomes on existing B004 partitions, not estimates of repeated-call variability or generalization to new donors.

Figure 4 uses the Leiden–Astra pipeline selected for detailed presentation from the B004 benchmark results. Figure S1 retains Leiden–Opus 5.5 as a supplementary comparison. The three Figure 4 example clusters were selected by cell count before outcomes were inspected. Figure S11 uses one accepted prediction per model, fixed model-order modal ties, and no reference-label filtering to select CD8+ T groups.

The [B004 presentation amendment](docs/revision/b004_astra_presentation_amendment_20261111.md) records this selection without changing the original primary protocol. The [Astra–Leiden control extension](docs/revision/astra_leiden_controls_protocol_20261111.md) is complete: all eight saved requests were strictly accepted, delivering 600 predictions. The [completion bundle](data/frozen/astra_prompt_controls_results_20261115/manifest.json) preserves the literal requests, visible terminal responses and offline scores. The native OpenAI Batch controls reuse an OpenRouter Batch baseline, so the contrasts do not isolate prompt content from provider route.

## Cross-donor evaluation

B005 and B006 contain **288,188 and 301,280 cells**, respectively, with eight regions each. Frozen Leiden, FlowSOM, SpatialSort and PIXIE partitions retain every donor cell. FlowSOM used three all-cell passes; primary SpatialSort used seed 42 at 50 actual sweeps with `dmh_iter=5`. The [frozen donor protocol](data/frozen/donor47_results_20261114/scientific_inputs/protocol.json) records 47 proteins plus Hoechst1 for native donor Leiden-parent generation, followed by a 47-protein local hierarchy and frozen label-blind Ward coarsening. Donor PIXIE uses 47 protein image channels plus Hoechst1. These donor-parent settings differ from the B004 cell-feature benchmark, which uses 47 proteins without Hoechst1. All annotation profiles use only the same 47 proteins. The [donor score bank](data/frozen/donor47_results_20261114/manifest.json) provides the terminal response bank and offline results. Figure S12 and Tables S14a/b use equal-region clustering metrics and global common-cell seed ARI as specified.

The frozen November 14 donor release has **32 donor–method–model sets, 128 planned logical items and 9,468 planned cluster predictions**. Strict acceptance delivered **9,093 of 9,468 planned cluster predictions from 123 of 128 logical items**. Astra, Opus and Gemini had complete delivery; five DeepSeek items were invalid and their 375 predictions remain errors in the planned denominator. The 23-label sensitivity uses the same reference-eligible cells for both vocabularies and no separate generation protocol. The B004-selected Astra–Leiden pipeline supplies the illustrative cross-donor analysis; frozen B004 conventional classifiers are applied without donor refitting. Equal-donor native-28-label agreement ranges from 16.33% to 38.57%; the illustrative Astra–Leiden pipeline reaches 35.87%.

Current Figures 5 and S13 include later DeepSeek recovery results from the saved manuscript. The frozen donor manifest and coverage above refer to the original November 14 replay.

## Reviewer experiments

The [completed publication record](configs/reviewer47_completed_publication_20261115.json) combines the immutable original reviewer bank with two append-only completion bundles. All **69 base B004 sets, 276 logical request items and 19,476 planned cluster predictions** are complete. The [DeepSeek completion](data/frozen/reviewer47_deepseek_completion_20261115/manifest.json) admits the one previously pending 75-cluster item without changing the earlier 275 accepted items. DeepSeek–Leiden selected numerical means reached **41.42% agreement and 0.3576 fixed-28-label macro-F1**, with all 300 cluster predictions delivered.

The [Astra controls](data/frozen/astra_prompt_controls_results_20261115/manifest.json) add two completed Leiden sets, eight items and 600 predictions. The full current B004 scope therefore contains **71 completed sets, 284 accepted items and 20,076 predictions**. Astra agreement was **58.12%** for the reused blinded baseline, **53.53%** with the method name and **51.43%** with neighborhood evidence. The controls used native OpenAI Batch, while the reused baseline used OpenRouter Batch. These descriptive single-generation contrasts do not isolate prompt content from execution route or establish repeatability.

Manuscript Figure S10 reports the four marker representations. Figure S2 and Table S9 report Opus and Astra prompt controls, and Figure S2 also reports retrospective cross-model reference-agreement calibration. Tables S10 and S11 report supervised classifiers and post-clustering coarsening. Tables S12a–d report calibration. Classifiers received richer reference-label supervision than the LLMs, coarsening is not native-K fitting, and within-donor cross-model agreement is not biological confidence or repeated-call stability.

All literal scientific requests, query maps and saved visible terminal answers needed for the completed scope are available in the linked frozen bundles. Credentials, private paths and hidden reasoning content are excluded. Earlier frozen snapshots and their pending metadata remain byte-preserved as historical evidence. The [offline replay](docs/revision/reviewer47_completed_publication_20261115.md) verifies the original bank, the newly admitted DeepSeek item and the eight Astra answers without network access, model calls or fitting.

## Tables and offline reproduction

Active supplementary tables are **S1, S2A/B, S6a–d, S7, S8a–d, S9, S10, S11, S12a–d, S13a–c, S14a–b and S15a–b**. The [table map](docs/supplementary_table_numbering.md) links their exact inputs. S7 contains only the 12 clustering-diagnostic comparisons and their 96 paired regional observations.

```bash
python3.12 -m pip install -r requirements-publication-figures.txt
python3.12 scripts/render_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S8 S9 S10 S11
python3.12 scripts/verify_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S8 S9 S10 S11
```

[Reproduction instructions](docs/manuscript_reproduction.md) explain scoring replay, immutable source hashes, retained compensation analyses and the separation of current sources from archival entry points. No API key or live inference is required. Optional offline recalibration fits are separated from label prediction; the [portable reviewer replay](docs/revision/reviewer47_publication_replay.md) verifies all saved answers and denominators.

## Archived evidence

[The checksum-indexed publication archive](data/historical/publication_before_primary47_20261109/index.json) preserves excluded figures and studies; stable experiment IDs remain in the [registry](configs/experiment_registry.json). Earlier reconstruction code and the immutable [revision release](https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/releases/tag/revision-2026-10-30-v1) remain available as archival evidence. Those inputs do not define the current annotation figures or active manuscript claims. No archival release or frozen preparation was overwritten.

The [current figure PNGs](figures/current_manuscript/PNG) match the saved November 17 manuscript. The [figure manifest](figures/current_manuscript/Figure_manifest.json) records checksums and source limits. The figure notebooks display these PNGs. The native renderer and vector exports correspond to their source snapshots.
