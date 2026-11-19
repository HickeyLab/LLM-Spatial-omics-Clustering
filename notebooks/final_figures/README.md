# Manuscript figure notebooks and replay

The [current figure index](../../configs/manuscript_display_crosswalk.json) records the saved manuscript's 19 figures in 21 PNG files. The [current captions](../../figures/current_manuscript/Figure_captions.txt) use the same figure numbers as the manuscript.

Native source IDs and filenames identify the reproducibility snapshots. The PNGs and captions use the manuscript display numbers. Figure S5 is supplied in three parts. Figure S14 is available as saved artwork. The native notebooks linked for S2 and S10 replay the November 11 snapshot. The [completed figure renderer](../../scripts/render_reviewer47_figures.py) rebuilds current S2 and S10 from the completed B004 result bank.

| Manuscript figure | Panels | Current artwork | Native source |
| --- | --- | --- | --- |
| 1. Spillover compensation | A–F | [PNG](../../figures/current_manuscript/PNG/Figure_1.png) | 1 · [figure_01_spillover_compensation.ipynb](figure_01_spillover_compensation.ipynb) |
| 2. Clustering benchmark | A–H | [PNG](../../figures/current_manuscript/PNG/Figure_2.png) | 2 · [figure_02_clustering_method_benchmark.ipynb](figure_02_clustering_method_benchmark.ipynb) |
| 3. LLM annotation benchmark | A–E | [PNG](../../figures/current_manuscript/PNG/Figure_3.png) | 3 · [figure_03_llm_annotation_benchmark.ipynb](figure_03_llm_annotation_benchmark.ipynb) |
| 4. Selected Leiden–Astra pipeline | A–E | [PNG](../../figures/current_manuscript/PNG/Figure_4.png) | 4 · [figure_04_leiden_gpt_end_to_end.ipynb](figure_04_leiden_gpt_end_to_end.ipynb) |
| 5. Cross-donor annotation | A–D | [PNG](../../figures/current_manuscript/PNG/Figure_5.png) | [Donor renderer](../../scripts/render_donor47_figures.py) |
| S1. Leiden–Opus 5.5 diagnostics | A–B | [PNG](../../figures/current_manuscript/PNG/Figure_S1.png) | S6 · [figure_s06_annotation_diagnostics.ipynb](figure_s06_annotation_diagnostics.ipynb) |
| S2. Matched prompt controls and cross-model support calibration | A–D | [PNG](../../figures/current_manuscript/PNG/Figure_S2.png) | S9 · [figure_s09_prompt_controls_and_calibration.ipynb](figure_s09_prompt_controls_and_calibration.ipynb) (Nov. 11 snapshot) |
| S3. Cluster quality after compensation | A–C | [PNG](../../figures/current_manuscript/PNG/Figure_S3.png) | S1 · [figure_s01_clustering_metrics.ipynb](figure_s01_clustering_metrics.ipynb) |
| S4. Spatial label changes after compensation | A–B | [PNG](../../figures/current_manuscript/PNG/Figure_S4.png) | S2 · [figure_s02_spatial_celltypes.ipynb](figure_s02_spatial_celltypes.ipynb) |
| S5. Matching-rule sensitivity and shared-object compensation | A–C | [Part A](../../figures/current_manuscript/PNG/Figure_S5_part_A.png) · [Part B](../../figures/current_manuscript/PNG/Figure_S5_part_B.png) · [Part C](../../figures/current_manuscript/PNG/Figure_S5_part_C.png) | S3 · [figure_s03_matching_and_compensation.ipynb](figure_s03_matching_and_compensation.ipynb) |
| S6. Reference cell types and clustering diagnostics | A–D | [PNG](../../figures/current_manuscript/PNG/Figure_S6.png) | S4 · [figure_s04_reference_and_clustering_diagnostics.ipynb](figure_s04_reference_and_clustering_diagnostics.ipynb) |
| S7. Reference-agreement upper bounds | A | [PNG](../../figures/current_manuscript/PNG/Figure_S7.png) | S5 · [figure_s05_reference_bounds.ipynb](figure_s05_reference_bounds.ipynb) |
| S8. Reference-agreement decomposition | Unlettered | [PNG](../../figures/current_manuscript/PNG/Figure_S8.png) | S7 · [figure_s07_agreement_decomposition.ipynb](figure_s07_agreement_decomposition.ipynb) |
| S9. Paired means and fractions comparison | A–D | [PNG](../../figures/current_manuscript/PNG/Figure_S9.png) | S10 · [figure_s10_paired_representations.ipynb](figure_s10_paired_representations.ipynb) |
| S10. Marker-representation controls | A–D | [PNG](../../figures/current_manuscript/PNG/Figure_S10.png) | S8 · [figure_s08_marker_representation_controls.ipynb](figure_s08_marker_representation_controls.ipynb) (Nov. 11 snapshot) |
| S11. CD8+ T marker-expression profiles | A | [PNG](../../figures/current_manuscript/PNG/Figure_S11.png) | S11 · [figure_s11_cd8_profiles.ipynb](figure_s11_cd8_profiles.ipynb) |
| S12. Donor clustering and SpatialSort seed sensitivity | A–C | [PNG](../../figures/current_manuscript/PNG/Figure_S12.png) | [Donor renderer](../../scripts/render_donor47_figures.py) |
| S13. Original 28-label and projected 23-label evaluation | A–D | [PNG](../../figures/current_manuscript/PNG/Figure_S13.png) | [Donor renderer](../../scripts/render_donor47_figures.py) |
| S14. Reference cell maps for all 24 regions | Unlettered | [PNG](../../figures/current_manuscript/PNG/Figure_S14.png) | Saved manuscript artwork |

- [Completed B004 offline replay](../../docs/revision/reviewer47_completed_publication_20261115.md) verifies the recovered DeepSeek result, the completed Astra controls and the earlier frozen results.
- [Cross-donor offline replay](../../docs/manuscript_reproduction.md#completed-cross-donor-scoring) verifies the donor panel inputs and tables.
- [Current supplementary table index](../../docs/supplementary_table_numbering.md) lists active table exports and their sources.
- [Supplementary Note 1](supplementary_note_01_llm_cluster_annotation.ipynb) displays a frozen 47-marker Leiden–Opus request and its accepted final response. It verifies source hashes before display.
