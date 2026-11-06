# Current manuscript figure map

Display labels were checked against the November 6, 2026 manuscript. This page defines the current figure inventory. The pinned [replay inventory](../configs/manuscript_inventory.json) retains the earlier panel layout and image checksums for reproducibility.

| Item | Panels | Notebook or source |
| --- | --- | --- |
| Figure 1 | A–F | [`figure_01_spillover_compensation.ipynb`](../notebooks/final_figures/figure_01_spillover_compensation.ipynb) |
| Figure 2 | A–H | [`figure_02_clustering_method_benchmark.ipynb`](../notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb) |
| Figure 3 | A–E | [`figure_03_llm_annotation_benchmark.ipynb`](../notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb) |
| Figure 4 | A–E | [`figure_04_leiden_claude_end_to_end.ipynb`](../notebooks/final_figures/figure_04_leiden_claude_end_to_end.ipynb) |
| Figure 5 | A–D | [`figure_05_donor_transfer.ipynb`](../notebooks/final_figures/figure_05_donor_transfer.ipynb) |
| Figure S1 | A–C | [`figure_s01_clustering_metrics.ipynb`](../notebooks/final_figures/figure_s01_clustering_metrics.ipynb) |
| Figure S2 | A–B | [`figure_s02_spatial_celltypes.ipynb`](../notebooks/final_figures/figure_s02_spatial_celltypes.ipynb) |
| Figure S3 | A–C | [`figure_s03_matching_and_compensation.ipynb`](../notebooks/final_figures/figure_s03_matching_and_compensation.ipynb) |
| Figure S4 | A–D | [`figure_s04_reference_and_clustering_diagnostics.ipynb`](../notebooks/final_figures/figure_s04_reference_and_clustering_diagnostics.ipynb) |
| Figure S5 | A–B | [`figure_s05_common_marker_sensitivity.ipynb`](../notebooks/final_figures/figure_s05_common_marker_sensitivity.ipynb) |
| Figure S6 | A–B | [`figure_s06_annotation_diagnostics.ipynb`](../notebooks/final_figures/figure_s06_annotation_diagnostics.ipynb) |
| Figure S7 | Unlettered | [`figure_s07_agreement_decomposition.ipynb`](../notebooks/final_figures/figure_s07_agreement_decomposition.ipynb) |
| Figure S8 | A–B | [`figure_s08_controlled_b004_annotation.ipynb`](../notebooks/final_figures/figure_s08_controlled_b004_annotation.ipynb) |
| Figure S9 | A–D | [`figure_s09_calibration_and_neighborhood.ipynb`](../notebooks/final_figures/figure_s09_calibration_and_neighborhood.ipynb) |
| Figure S10 | A–D | [`figure_s10_paired_representations.ipynb`](../notebooks/final_figures/figure_s10_paired_representations.ipynb) |
| Figure S11 | A | [Marker-profile source](../data/frozen/manuscript_replay/figure_02/panel_I_marker_summaries.csv), formerly Figure 2I |

Figure 2 has panels A–H. Its former marker-profile panel I is now Figure S11A, and the former selected-window panel J is archived. Figure 3 has panels A–E. Its current E is the spatial comparison previously labeled H. Earlier reference-informed selection panels are archived and do not define current Figure 3E. Figure 4 has panels A–E and uses Leiden–Claude.

In Figure 3E and S11, each cluster's most frequent label across GPT, Claude, Gemini and DeepSeek is used, with ties resolved in that order without reference labels. These summaries do not provide independent validation.

Figure S3 is matching/compensation, S4 is reference/clustering diagnostics, and S6 is annotation diagnostics. Former S3/S4 notebook paths remain compatibility links. Retained notebooks and image files can include earlier panels. They are historical replay sources where they differ from this display map. Figure S11 currently links to its verified numerical source rather than a standalone public artwork file.

[Reproduction modes and source boundaries](manuscript_reproduction.md) distinguish exact artwork replay from numerical reconstruction.
