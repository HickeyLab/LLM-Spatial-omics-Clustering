# Evaluation of Clustering Methods and LLMs for CODEX Cell-Type Annotation

The manuscript uses the frozen 47-marker primary clustering assignments and the completed single-annotation campaign: **220,082 B004 cells, four clustering methods, four models, two marker-representation arms, 32 annotation sets, 128 accepted logical request items and 9,024 cluster predictions**. The [active study record](configs/annotation47_active_study.json), [figure inventory](configs/manuscript_inventory.json) and [scored result manifest](data/frozen/annotation47_results_20261110/manifest.json) define the current publication inputs.

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
| S10 | A–D | [figure_s10_paired_representations.ipynb](notebooks/final_figures/figure_s10_paired_representations.ipynb) |
| S11 | A | [figure_s11_cd8_profiles.ipynb](notebooks/final_figures/figure_s11_cd8_profiles.ipynb) |

There are 13 figure identifiers and 15 manuscript image files because Figure S3 has three parts. [Submission exports](figures/publication) contain the native PDF/SVG and 600 dpi PNG/TIFF versions. [Notebook previews](notebooks/final_figures/previews) and manuscript artwork use the same checked result set. The [figure map](docs/figure_map.md) describes each figure's population and source.

## Annotation results and scoring

The means-plus-fractions arm supplies the benchmark. Reference agreement is calculated separately in the two fixed test regions and averaged equally; fixed-vocabulary macro-F1 averages all 28 label-specific F1 scores, assigning zero to absent classes, within each region before equal region weighting. Noise remains a valid label. The paired study subtracts means-only outcomes from means-plus-fractions outcomes. All final annotation sets have complete cluster and cell delivery.

Across the 16 benchmark combinations, equal-test-region agreement ranges from **23.06% to 58.12%** and macro-F1 from **0.151 to 0.449**. Leiden–Astra has the highest agreement in these two regions. Adding fractions is associated with higher agreement in nine conditions and lower agreement in seven, with changes from **−8.75 to +6.50 percentage points**. These are descriptive single-run outcomes on existing B004 partitions, not estimates of repeated-call variability or generalization to new donors.

Figure 4 uses the Leiden–Astra pipeline selected for detailed presentation from the B004 benchmark results. Figure S6 retains Leiden–Opus 5.5 as a supplementary comparison. The three Figure 4 example clusters were selected by cell count before outcomes were inspected. Figure S11 uses one accepted prediction per model, fixed model-order modal ties, and no reference-label filtering to select CD8+ T groups.

The [B004 presentation amendment](docs/revision/b004_astra_presentation_amendment_20261111.md) records this selection without changing the original protocol. A separate [Astra–Leiden control extension](docs/revision/astra_leiden_controls_protocol_20261111.md) prepares eight native Batch items with a conservative $8.71 reservation. It remains disabled pending fresh preflight and separate launch approval; B005/B006 and completed Opus controls are unchanged.

The [execution summary](data/frozen/annotation47_results_20261110/actual_execution_summary.json) records actual accepted settings: Astra/Opus Batch at 32,768 requested output tokens; Gemini/DeepSeek standard streaming at 943,718, with Gemini continuation segments recorded separately. The original disabled preparation remains unchanged. Rejected/interrupted attempts, authorized recoveries, request hashes and per-request route metadata remain in the source records. There is one accepted output per logical condition; this does not imply one physical generation. Confirmed campaign charges are **$77.078729829**, with **$6.767982** in retained uncertain holds and **$83.846711829** in total commitment under the approved $90 cap. Offline scoring and plotting make no paid calls.

The [reviewer refresh protocol](docs/revision/reviewer47_credit_batch_protocol.md) prepares Batch-only, one-generation follow-up controls and native Astra funding from the selected account's existing API balance. Its new offline classifiers, coarsening and current-bank calibration are [indexed separately](data/frozen/reviewer47_offline_20261110/index.json). Inference is disabled; donor annotation waits for the other chat's verified 50-sweep B005/B006 outputs and matched cohort admission. This preparation does not replace the current publication results.

## Tables and offline reproduction

Active supplementary tables are **S1, S2A/B, S6a–d and S7**. The [table map](docs/supplementary_table_numbering.md) links their exact inputs. S7 contains only the 12 clustering-diagnostic comparisons and their 96 paired regional observations.

```bash
python3.12 -m pip install -r requirements-publication-figures.txt
python3.12 scripts/render_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S10 S11
python3.12 scripts/verify_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S10 S11
```

[Reproduction instructions](docs/manuscript_reproduction.md) explain scoring replay, immutable source hashes, retained compensation analyses and the separation of current sources from archival entry points. No API key, fitting or live inference is required for the current replay.

## Archived evidence

[The checksum-indexed publication archive](data/historical/publication_before_primary47_20261109/index.json) preserves excluded figures and studies; stable experiment IDs remain in the [registry](configs/experiment_registry.json). Earlier reconstruction code and the immutable [revision release](https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/releases/tag/revision-2026-10-30-v1) remain available as archival evidence. Those inputs do not define the current annotation figures or active manuscript claims. No archival release or frozen preparation was overwritten.
