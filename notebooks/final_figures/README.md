# Current manuscript figure entry points

The current inventory contains 15 retained figures and 17 image files. Figure S3 has three image parts. Use the checksum-pinned [inventory](../../configs/manuscript_inventory.json) for captions and panel identities.

| Figure | Panels | Notebook |
| --- | --- | --- |
| 1 | A–F | [figure_01_spillover_compensation.ipynb](figure_01_spillover_compensation.ipynb) |
| 2 | A–H | [figure_02_clustering_method_benchmark.ipynb](figure_02_clustering_method_benchmark.ipynb) |
| 3 | A–E | [figure_03_llm_annotation_benchmark.ipynb](figure_03_llm_annotation_benchmark.ipynb) |
| 4 | A–E | [figure_04_leiden_gpt_end_to_end.ipynb](figure_04_leiden_gpt_end_to_end.ipynb) |
| S1 | A–C | [figure_s01_clustering_metrics.ipynb](figure_s01_clustering_metrics.ipynb) |
| S2 | A–B | [figure_s02_spatial_celltypes.ipynb](figure_s02_spatial_celltypes.ipynb) |
| S3 | A–C | [figure_s03_matching_and_compensation.ipynb](figure_s03_matching_and_compensation.ipynb) |
| S4 | A–D | [figure_s04_reference_and_clustering_diagnostics.ipynb](figure_s04_reference_and_clustering_diagnostics.ipynb) |
| S5 | A | [figure_s05_reference_bounds.ipynb](figure_s05_reference_bounds.ipynb) |
| S6 | A–B | [figure_s06_annotation_diagnostics.ipynb](figure_s06_annotation_diagnostics.ipynb) |
| S7 | Unlettered | [figure_s07_agreement_decomposition.ipynb](figure_s07_agreement_decomposition.ipynb) |
| S8 | A–D | [figure_s08_marker_representation_controls.ipynb](figure_s08_marker_representation_controls.ipynb) |
| S9 | A–D | [figure_s09_prompt_controls_and_calibration.ipynb](figure_s09_prompt_controls_and_calibration.ipynb) |
| S10 | A–D | [figure_s10_paired_representations.ipynb](figure_s10_paired_representations.ipynb) |
| S11 | A | [figure_s11_cd8_profiles.ipynb](figure_s11_cd8_profiles.ipynb) |

The annotation-dependent notebooks display and reproduce the completed 47-marker, fixed-28-label study from [frozen offline scores](../../data/frozen/annotation47_results_20261111). The benchmark uses the means-plus-fractions arm. The paired comparison uses the same final accepted outputs alongside means alone. Each logical condition has one accepted prediction per cluster; no across-repetition SD or repeated-call consistency is calculated.

Figure 4 uses the Leiden–Astra pipeline selected for detailed presentation from the B004 benchmark results. Figure S6 retains Leiden–Opus 5.5 as a supplementary comparison. Figure S11 uses one label per model to form a four-model most-frequent-label display with fixed model-order tie-breaking. This cross-model display is separate from repeated-call consistency.

Current supplementary tables are S1, S2A/B, S6a–d, S7, S8a–d, S9–S11 and S12a–d. The [table crosswalk](../../docs/supplementary_table_numbering.md) controls labels and source paths. Original artifacts and superseded scientific workflows remain available through the checksum-linked archive and the unchanged versioned release; they are not results of the current annotation campaign.

The notebooks contain no automatic endpoint submission path. Stored code outputs are empty; native rendering, scoring validation and visual checks are recorded separately. Compatibility entry points are not additional manuscript figures.

[Supplementary Note 1](supplementary_note_01_llm_cluster_annotation.ipynb) displays one exact 47-marker Leiden–Opus request and its accepted 75-label final response. Source hashes are verified before display; the entry point makes no live calls and includes no hidden reasoning.

S8 and S9 display the checksum-bound [reviewer controls](../../data/frozen/reviewer47_results_20261111). S8 masks the one pending selected-means condition rather than publishing partial accuracy; S9 includes complete Opus controls and retrospective agreement calibration. The separate Astra prompt-control extension remains pending. These notebooks do not run inference or fit new calibration models.
