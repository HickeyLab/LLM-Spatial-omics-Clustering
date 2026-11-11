# Evaluation of Clustering Methods and LLMs for CODEX Cell-Type Annotation

The manuscript uses the frozen 47-marker primary clustering assignments and the completed single-annotation campaign: **220,082 B004 cells, four clustering methods, four models, two marker-representation arms, 32 annotation sets, 128 accepted logical request items and 9,024 cluster predictions**. The [active study record](configs/annotation47_active_study.json), [figure inventory](configs/manuscript_inventory.json) and [scored result manifest](data/frozen/annotation47_results_20261111/manifest.json) define the current publication inputs.

Leiden, FlowSOM, SpatialSort and PIXIE have 300, 299, 229 and 300 occupied clusters. FlowSOM used three complete shuffled passes, and the primary SpatialSort partition is seed 42 at sweep 100 with `dmh_iter=5`. Seed 43 remains a clustering sensitivity result. The annotation models are GPT-6 Astra, Claude Opus 5.5, Gemini 4 Argon and DeepSeek V4.1 Flash 1017.

## Retained figures

| Figure | Panels | Notebook |
| --- | --- | --- |
| 1 | A–F | [figure_01_spillover_compensation.ipynb](notebooks/final_figures/figure_01_spillover_compensation.ipynb) |
| 2 | A–H | [figure_02_clustering_method_benchmark.ipynb](notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb) |
| 3 | A–E | [figure_03_llm_annotation_benchmark.ipynb](notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb) |
| 4 | A–E | [figure_04_leiden_gpt_end_to_end.ipynb](notebooks/final_figures/figure_04_leiden_gpt_end_to_end.ipynb) |
| S1 | A–C | [figure_s01_clustering_metrics.ipynb](notebooks/final_figures/figure_s01_clustering_metrics.ipynb) |
| S2 | A–B | [figure_s02_spatial_celltypes.ipynb](notebooks/final_figures/figure_s02_spatial_celltypes.ipynb) |
| S3 | A–C | [figure_s03_matching_and_compensation.ipynb](notebooks/final_figures/figure_s03_matching_and_compensation.ipynb) |
| S4 | A–D | [figure_s04_reference_and_clustering_diagnostics.ipynb](notebooks/final_figures/figure_s04_reference_and_clustering_diagnostics.ipynb) |
| S5 | A | [figure_s05_reference_bounds.ipynb](notebooks/final_figures/figure_s05_reference_bounds.ipynb) |
| S6 | A–B | [figure_s06_annotation_diagnostics.ipynb](notebooks/final_figures/figure_s06_annotation_diagnostics.ipynb) |
| S7 | Unlettered | [figure_s07_agreement_decomposition.ipynb](notebooks/final_figures/figure_s07_agreement_decomposition.ipynb) |
| S8 | A–D | [figure_s08_marker_representation_controls.ipynb](notebooks/final_figures/figure_s08_marker_representation_controls.ipynb) |
| S9 | A–D | [figure_s09_prompt_controls_and_calibration.ipynb](notebooks/final_figures/figure_s09_prompt_controls_and_calibration.ipynb) |
| S10 | A–D | [figure_s10_paired_representations.ipynb](notebooks/final_figures/figure_s10_paired_representations.ipynb) |
| S11 | A | [figure_s11_cd8_profiles.ipynb](notebooks/final_figures/figure_s11_cd8_profiles.ipynb) |

There are 15 figure identifiers and 17 manuscript image files because Figure S3 has three parts. [Submission exports](figures/publication) contain the native PDF/SVG and 600 dpi PNG/TIFF versions. [Notebook previews](notebooks/final_figures/previews) and manuscript artwork use the same checked result set. The [figure map](docs/figure_map.md) describes each figure's population and source.

## Annotation results and scoring

The means-plus-fractions arm supplies the benchmark. Reference agreement is calculated separately in the two fixed test regions and averaged equally; fixed-vocabulary macro-F1 averages all 28 label-specific F1 scores, assigning zero to absent classes, within each region before equal region weighting. Noise remains a valid label. The paired study subtracts means-only outcomes from means-plus-fractions outcomes. All final annotation sets have complete cluster and cell delivery.

Across the 16 benchmark combinations, equal-test-region agreement ranges from **17.42% to 58.12%** and macro-F1 from **0.114 to 0.449**. Leiden–Astra has the highest agreement in these two regions. Adding fractions is associated with higher agreement in eight conditions and lower agreement in eight, with changes from **−10.25 to +6.50 percentage points**. These are descriptive single-run outcomes on existing B004 partitions, not estimates of repeated-call variability or generalization to new donors.

Figure 4 uses the Leiden–Astra pipeline selected for detailed presentation from the B004 benchmark results. Figure S6 retains Leiden–Opus 5.5 as a supplementary comparison. The three Figure 4 example clusters were selected by cell count before outcomes were inspected. Figure S11 uses one accepted prediction per model, fixed model-order modal ties, and no reference-label filtering to select CD8+ T groups.

The [B004 presentation amendment](docs/revision/b004_astra_presentation_amendment_20261111.md) records this selection without changing the original primary protocol. The separate [Astra–Leiden control extension](docs/revision/astra_leiden_controls_protocol_20261111.md) was launched as eight native Batch requests; its named-method and neighborhood results remain pending and are not plotted.

## Reviewer experiments

The [reviewer result export](data/frozen/reviewer47_results_20261111/manifest.json) retains **69 planned B004 annotation sets and 276 logical request items**. There are **68 complete sets and 275 accepted items**, including 109 exact reuses and 166 newly accepted items. The DeepSeek–Leiden selected-numerical condition has one pending request covering **75 clusters**. Its accuracy and macro-F1 are null; no four-arm aggregate silently drops it. The additional Astra extension has eight pending requests, so nine request items remain pending across these scopes. B005/B006 results are not included.

Figure S8 and Tables S8a–d report the four marker representations. Figure S9 and Table S9 report the completed Opus method-name and 15-neighbor controls; Astra versions await their Batch outputs. Tables S10 and S11 report the matched supervised classifiers and post-clustering K=100/200 coarsening. Figure S9 and Tables S12a–d use calibration recomputed on the current complete primary bank, with both cluster and region separation. Classifiers receive richer training-label supervision than LLM prompts; coarsening is not native-K fitting; within-donor cross-model agreement is not repeated-call consistency or biological confidence.

The [current execution summary](docs/revision/reviewer47_execution_summary_20261111.json), [per-request settings](data/frozen/reviewer47_results_20261111/model_settings.json) and [physical-attempt accounting](data/frozen/reviewer47_results_20261111/logical_physical_accounting.json) distinguish logical answers, exact reuses, Batch items, streaming continuations and authorized recoveries. Astra/Opus retain high reasoning and a 32,768-token combined ceiling; Gemini/DeepSeek retain high reasoning and 943,718 tokens. Unsupported seeds are omitted. Each physical generation and provider-reported charge is counted once; unresolved billing remains unknown. The previous $77.08/$90 financial record covers an earlier scope and is preserved in the [metadata archive](archive/reviewer47_publication_before_20261111/metadata_index.json); it is not the cost or cap of the enlarged study.

All 276 literal scientific request bodies, anonymous query maps, marker selections, fixed training scaler and [literal saved visible responses](data/frozen/reviewer47_response_evidence_20261111/manifest.json) are available for offline replay without a local H5AD or API key. Nineteen full-arm DeepSeek items follow the presealed reviewer route reconciliation; their scientific messages match exactly and were not selected by reference score. Primary figures, paired comparisons and calibration use that same admitted bank. Earlier frozen data and the disabled preparations remain unchanged. This publication update makes zero annotation calls or scheduler actions.

## Tables and offline reproduction

Active supplementary tables are **S1, S2A/B, S6a–d, S7, S8a–d, S9, S10, S11 and S12a–d**. The [table map](docs/supplementary_table_numbering.md) links their exact inputs. S7 contains only the 12 clustering-diagnostic comparisons and their 96 paired regional observations.

```bash
python3.12 -m pip install -r requirements-publication-figures.txt
python3.12 scripts/render_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S8 S9 S10 S11
python3.12 scripts/verify_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S8 S9 S10 S11
```

[Reproduction instructions](docs/manuscript_reproduction.md) explain scoring replay, immutable source hashes, retained compensation analyses and the separation of current sources from archival entry points. No API key or live inference is required. Optional offline recalibration fits are separated from label prediction; the [portable reviewer replay](docs/revision/reviewer47_publication_replay.md) verifies all saved answers and denominators.

## Archived evidence

[The checksum-indexed publication archive](data/historical/publication_before_primary47_20261109/index.json) preserves excluded figures and studies; stable experiment IDs remain in the [registry](configs/experiment_registry.json). Earlier reconstruction code and the immutable [revision release](https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/releases/tag/revision-2026-10-30-v1) remain available as archival evidence. Those inputs do not define the current annotation figures or active manuscript claims. No archival release or frozen preparation was overwritten.
