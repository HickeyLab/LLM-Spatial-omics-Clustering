# Evaluation of Clustering Methods and LLMs for CODEX Cell-Type Annotation

The figure and table display labels follow the manuscript checked on November 6, 2026. The [figure map](docs/figure_map.md) and [table crosswalk](docs/supplementary_table_numbering.md) define the current inventory. Retained artwork, notebook outputs and frozen replay inputs include earlier panel arrangements, which are identified in the [reproduction guide](docs/manuscript_reproduction.md). The [publication exports](figures/publication) retain their original bytes and submission-resolution formats.

## Current figure notebooks

| Item | Panels | Notebook or source |
| --- | --- | --- |
| Figure 1 | A–F | [`figure_01_spillover_compensation.ipynb`](notebooks/final_figures/figure_01_spillover_compensation.ipynb) |
| Figure 2 | A–H | [`figure_02_clustering_method_benchmark.ipynb`](notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb) |
| Figure 3 | A–E | [`figure_03_llm_annotation_benchmark.ipynb`](notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb) |
| Figure 4 | A–E | [`figure_04_leiden_claude_end_to_end.ipynb`](notebooks/final_figures/figure_04_leiden_claude_end_to_end.ipynb) |
| Figure 5 | A–D | [`figure_05_donor_transfer.ipynb`](notebooks/final_figures/figure_05_donor_transfer.ipynb) |
| Figure S1 | A–C | [`figure_s01_clustering_metrics.ipynb`](notebooks/final_figures/figure_s01_clustering_metrics.ipynb) |
| Figure S2 | A–B | [`figure_s02_spatial_celltypes.ipynb`](notebooks/final_figures/figure_s02_spatial_celltypes.ipynb) |
| Figure S3 | A–C | [`figure_s03_matching_and_compensation.ipynb`](notebooks/final_figures/figure_s03_matching_and_compensation.ipynb) |
| Figure S4 | A–D | [`figure_s04_reference_and_clustering_diagnostics.ipynb`](notebooks/final_figures/figure_s04_reference_and_clustering_diagnostics.ipynb) |
| Figure S5 | A–B | [`figure_s05_common_marker_sensitivity.ipynb`](notebooks/final_figures/figure_s05_common_marker_sensitivity.ipynb) |
| Figure S6 | A–B | [`figure_s06_annotation_diagnostics.ipynb`](notebooks/final_figures/figure_s06_annotation_diagnostics.ipynb) |
| Figure S7 | Unlettered | [`figure_s07_agreement_decomposition.ipynb`](notebooks/final_figures/figure_s07_agreement_decomposition.ipynb) |
| Figure S8 | A–B | [`figure_s08_controlled_b004_annotation.ipynb`](notebooks/final_figures/figure_s08_controlled_b004_annotation.ipynb) |
| Figure S9 | A–D | [`figure_s09_calibration_and_neighborhood.ipynb`](notebooks/final_figures/figure_s09_calibration_and_neighborhood.ipynb) |
| Figure S10 | A–D | [`figure_s10_paired_representations.ipynb`](notebooks/final_figures/figure_s10_paired_representations.ipynb) |
| Figure S11 | A | [Marker-profile source](data/frozen/manuscript_replay/figure_02/panel_I_marker_summaries.csv), formerly Figure 2I |

## Current supplementary tables

| Current item | Entry point or source |
| --- | --- |
| Table S1 | [`table_s1_matching_and_retention.ipynb`](notebooks/final_figures/table_s1_matching_and_retention.ipynb) |
| Table S2 | [`table_s2_clustering_and_channels.ipynb`](notebooks/final_figures/table_s2_clustering_and_channels.ipynb) |
| Table S3 | [`table_s3_marker_summary_parameters.ipynb`](notebooks/final_figures/table_s3_marker_summary_parameters.ipynb) |
| Table S4 | [`table_s4_controlled_annotation.ipynb`](notebooks/final_figures/table_s4_controlled_annotation.ipynb) |
| Table S5 | [`table_s5_repeatability_and_prompt_controls.ipynb`](notebooks/final_figures/table_s5_repeatability_and_prompt_controls.ipynb) |
| Table S6 | [`table_s6_paired_representations.ipynb`](notebooks/final_figures/table_s6_paired_representations.ipynb) |
| Table S7 | [`table_s7_conditional_comparisons.ipynb`](notebooks/final_figures/table_s7_conditional_comparisons.ipynb) |
| Table S8 | [`table_s8_label_mapping_sensitivity.ipynb`](notebooks/final_figures/table_s8_label_mapping_sensitivity.ipynb) |
| Table S9 | [Paired donor values](data/frozen/manuscript_replay/tables/current_tables.json), retained under the former main Table 2 label, with [donor](data/frozen/manuscript_replay/tables/companions/S3b_donor_metrics.csv) and [equal-donor](data/frozen/manuscript_replay/tables/companions/S3c_equal_donor_metrics.csv) records |

Figure 3E shows reference labels, individual predictions and each cluster's most frequent model label. Ties use GPT, Claude, Gemini and DeepSeek order without reference labels. Former Figure 2J and the earlier reference-informed selection panels are archived analyses. Figure S11 retains the former Figure 2I marker profiles without the selected spatial windows.

Companion files retain their deposited names and bytes. The [table crosswalk](docs/supplementary_table_numbering.md) maps those filenames to the current display labels. [Supplementary Note 1](notebooks/final_figures/supplementary_note_01_llm_cluster_annotation.ipynb) displays a verified archived benchmark request and parsed output.

## Offline reproduction

The commands below replay the retained source snapshot. They can include panels removed or relocated in the current manuscript. Python 3.12 is supported. Install [requirements-manuscript-replay.txt](requirements-manuscript-replay.txt) for the compact frozen replay, or [requirements.txt](requirements.txt) for the original full analysis environment.

```bash
python3.12 -m pip install -r requirements-manuscript-replay.txt
python3.12 scripts/verify_manuscript_replay.py
python3.12 scripts/render_figure_02_manuscript.py
python3.12 scripts/render_figure_03_manuscript.py
python3.12 scripts/render_current_tables.py
```

The Figure 2/3 notebooks retain numerical and artwork replays from before the current panel reductions. Figure 5, S9 and S10 provide numerical replots from checksum-pinned frozen tables. Retained figure images can be replayed exactly from their pinned files. This documentation update does not regenerate artwork or change frozen results. The [November 1 layout pass](docs/figure_layout_compaction_20261101.md) closes space left by removed notes and titles without reducing type sizes. These are distinct operations: artwork replay verifies the publication pixels, while numerical replots verify data and definitions and may use different fonts or spacing. Some supplementary entry points provide artwork replay only, with the scientific source linked in the versioned release. [Reproduction instructions](docs/manuscript_reproduction.md) state each boundary and list the recovered plotting commands.

Figures 4, S1 and S2 retain their existing analytical notebooks and input requirements. Figure 1 replays the approved composite and the descriptive D–F values, with its original H5AD workflow preserved in the historical collection. Figures 1/S1/S2 require the 13-file historical input set from [Duke record 565](https://research.repository.duke.edu/record/565), pinned in [its manifest](configs/duke_record_565_manifest.json). Figure 4 replays the frozen Leiden–Claude map with the verified reference H5AD from [Duke record 505](https://research.repository.duke.edu/record/505). See [Figure 4 provenance](docs/figure_04_historical_claude_replay.md). Downloaded H5AD inputs remain outside Git.

Earlier analytical reconstructions are preserved under [notebooks/historical_reconstructions](notebooks/historical_reconstructions/README.md). Their panel arrangements or metrics can differ from the current manuscript. They are not invoked by the current offline replay.

## Frozen revision release

The [historical FlowSOM sweep retirement](docs/flowsom_sweep_retirement_20261103.md) removes its panel from active Figure S4 while preserving checksum-indexed historical evidence. The [combined experiments 7/9/14 protocol](docs/revision/combined_annotation47_protocol.md) is planned and execution-disabled; it has made no annotation calls and will not start automatically when SpatialSort finishes.

The [October 30 revision release](https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/releases/tag/revision-2026-10-30-v1) contains frozen predictions, available request and failure records, settings, analysis source and supporting tables in seven hash-manifested archives. The [release guide](docs/revision_public_deposition_20261030.md) describes retrieval and protocol boundaries. The immutable release retains its original filenames. Current display labels and source links are documented without rewriting that release or changing its data.

Generated outputs go beneath `outputs/` and remain ignored by Git. Frozen replay performs no model calls or fitting. Rerunning upstream clustering engines or historical live-inference modes is a separate workflow with separate inputs and authorization.

Current supplementary prose is organized as Supplementary Methods SM1–SM5 and Notes 1–3. There is no Supplementary Note 4. See the [figure map](docs/figure_map.md), [table crosswalk](docs/supplementary_table_numbering.md) and [historical October 31 synchronization record](docs/manuscript_sync_20261031.md).
