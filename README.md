# Evaluation of Clustering Methods and LLMs for CODEX Cell-Type Annotation

The notebook index, plotting entry points and table labels follow the manuscript inventory checked on October 31, 2026. Current artwork is in [figures/manuscript](figures/manuscript/README.md). The [publication exports](figures/publication) provide 600 dpi PNG/TIFF and editable PDF/SVG files, with [design and placement guidance](docs/publication_figure_design.md). Figures 2A, 3A and 4A use the author's original BioRender workflows with editable print-size labels. Figure 3A retains the latest optimization steps, and Figure 3E describes its existing reference-selected values accurately.

## Current figure notebooks

| Item | Panels | Notebook |
| --- | --- | --- |
| Figure 1 | A–F | [`figure_01_spillover_compensation.ipynb`](notebooks/final_figures/figure_01_spillover_compensation.ipynb) |
| Figure 2 | A–J | [`figure_02_clustering_method_benchmark.ipynb`](notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb) |
| Figure 3 | A–H | [`figure_03_llm_annotation_benchmark.ipynb`](notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb) |
| Figure 4 | A–E | [`figure_04_leiden_claude_end_to_end.ipynb`](notebooks/final_figures/figure_04_leiden_claude_end_to_end.ipynb) |
| Figure 5 | A–D | [`figure_05_donor_transfer.ipynb`](notebooks/final_figures/figure_05_donor_transfer.ipynb) |
| Figure S1 | A–C | [`figure_s01_clustering_metrics.ipynb`](notebooks/final_figures/figure_s01_clustering_metrics.ipynb) |
| Figure S2 | A–B | [`figure_s02_spatial_celltypes.ipynb`](notebooks/final_figures/figure_s02_spatial_celltypes.ipynb) |
| Figure S3 | A–C | [`figure_s03_matching_and_compensation.ipynb`](notebooks/final_figures/figure_s03_matching_and_compensation.ipynb) |
| Figure S4 | A–E | [`figure_s04_reference_and_clustering_diagnostics.ipynb`](notebooks/final_figures/figure_s04_reference_and_clustering_diagnostics.ipynb) |
| Figure S5 | A–B | [`figure_s05_common_marker_sensitivity.ipynb`](notebooks/final_figures/figure_s05_common_marker_sensitivity.ipynb) |
| Figure S6 | A–B | [`figure_s06_annotation_diagnostics.ipynb`](notebooks/final_figures/figure_s06_annotation_diagnostics.ipynb) |
| Figure S7 | Unlettered | [`figure_s07_agreement_decomposition.ipynb`](notebooks/final_figures/figure_s07_agreement_decomposition.ipynb) |
| Figure S8 | A–B | [`figure_s08_controlled_b004_annotation.ipynb`](notebooks/final_figures/figure_s08_controlled_b004_annotation.ipynb) |
| Figure S9 | A–D | [`figure_s09_calibration_and_neighborhood.ipynb`](notebooks/final_figures/figure_s09_calibration_and_neighborhood.ipynb) |
| Figure S10 | A–D | [`figure_s10_paired_representations.ipynb`](notebooks/final_figures/figure_s10_paired_representations.ipynb) |

## Current supplementary tables

| Current item | Notebook |
| --- | --- |
| Table S1 | [`table_s1_matching_and_retention.ipynb`](notebooks/final_figures/table_s1_matching_and_retention.ipynb) |
| Table S2 | [`table_s2_clustering_and_channels.ipynb`](notebooks/final_figures/table_s2_clustering_and_channels.ipynb) |
| Table S3 | [`table_s3_marker_summary_parameters.ipynb`](notebooks/final_figures/table_s3_marker_summary_parameters.ipynb) |
| Table S4 | [`table_s4_controlled_annotation.ipynb`](notebooks/final_figures/table_s4_controlled_annotation.ipynb) |
| Table S5 | [`table_s5_repeatability_and_prompt_controls.ipynb`](notebooks/final_figures/table_s5_repeatability_and_prompt_controls.ipynb) |
| Table S6 | [`table_s6_paired_representations.ipynb`](notebooks/final_figures/table_s6_paired_representations.ipynb) |
| Table S7 | [`table_s7_conditional_comparisons.ipynb`](notebooks/final_figures/table_s7_conditional_comparisons.ipynb) |
| Table S8 | [`table_s8_label_mapping_sensitivity.ipynb`](notebooks/final_figures/table_s8_label_mapping_sensitivity.ipynb) |

Companion files retain their deposited names and bytes. The [table crosswalk](docs/supplementary_table_numbering.md) maps those filenames to the current display labels. [Supplementary Note 1](notebooks/final_figures/supplementary_note_01_llm_cluster_annotation.ipynb) displays a verified archived benchmark request and parsed output.

## Offline reproduction

Python 3.12 is supported. Install [requirements-manuscript-replay.txt](requirements-manuscript-replay.txt) for the compact frozen replay, or [requirements.txt](requirements.txt) for the original full analysis environment.

```bash
python3.12 -m pip install -r requirements-manuscript-replay.txt
python3.12 scripts/verify_manuscript_replay.py
python3.12 scripts/render_figure_02_manuscript.py
python3.12 scripts/render_figure_03_manuscript.py
python3.12 scripts/render_current_tables.py
```

The current Figure 2/3 notebooks use the manuscript's metrics and panel arrangement. Figure 5, S9 and S10 also provide numerical replots from checksum-pinned frozen tables. All current figure images can be replayed exactly from approved artwork. The [current layout pass](docs/figure_layout_compaction_20261101.md) closes space left by removed notes and titles without reducing type sizes. These are distinct operations: artwork replay verifies the publication pixels, while numerical replots verify data and definitions and may use different fonts or spacing. Some supplementary entry points provide artwork replay only, with the scientific source linked in the versioned release. [Reproduction instructions](docs/manuscript_reproduction.md) state each boundary and list the recovered plotting commands.

Figures 4, S1 and S2 retain their existing analytical notebooks and input requirements. Figure 1 replays the approved composite and the descriptive D–F values, with its original H5AD workflow preserved in the historical collection. Figures 1/S1/S2 require the 13-file historical input set from [Duke record 565](https://research.repository.duke.edu/record/565), pinned in [its manifest](configs/duke_record_565_manifest.json). Figure 4 replays the frozen Leiden–Claude map with the verified reference H5AD from [Duke record 505](https://research.repository.duke.edu/record/505). See [Figure 4 provenance](docs/figure_04_historical_claude_replay.md). Downloaded H5AD inputs remain outside Git.

Earlier analytical reconstructions are preserved under [notebooks/historical_reconstructions](notebooks/historical_reconstructions/README.md). Their panel arrangements or metrics can differ from the current manuscript. They are not invoked by the current offline replay.

## Frozen revision release

The [October 30 revision release](https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/releases/tag/revision-2026-10-30-v1) contains frozen predictions, available request and failure records, settings, analysis source and supporting tables in seven hash-manifested archives. The [release guide](docs/revision_public_deposition_20261030.md) describes retrieval and protocol boundaries. The immutable release retains its original filenames. This source-tree update supplies current navigation, numbering and omitted plotting entry points without rewriting that release.

Generated outputs go beneath `outputs/` and remain ignored by Git. Frozen replay performs no model calls or fitting. Rerunning upstream clustering engines or historical live-inference modes is a separate workflow with separate inputs and authorization.

See the [figure map](docs/figure_map.md) and [current synchronization record](docs/manuscript_sync_20261031.md).
