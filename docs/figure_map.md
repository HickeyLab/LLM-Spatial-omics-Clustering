# Current manuscript figure map

The [current figure index](../configs/manuscript_display_crosswalk.json) records 19 figures in 21 PNG files. Each image is pinned by SHA-256. The [caption file](../figures/current_manuscript/Figure_captions.txt) follows the saved manuscript.

Native source IDs and filenames identify the reproducibility snapshots. The PNGs and captions use the manuscript display numbers. Figure S5 is supplied in three parts. Figure S14 is available as saved artwork. The native notebooks linked for S2 and S10 replay the November 11 snapshot. The [completed B004 replay](revision/reviewer47_completed_publication_20261115.md) verifies the saved manuscript's supplemental results, and the [completed figure renderer](../scripts/render_reviewer47_figures.py) rebuilds S2 and S10 from those results.

| Manuscript figure | Panels | Current artwork | Native source |
| --- | --- | --- | --- |
| 1. Spillover compensation | A–F | [PNG](../figures/current_manuscript/PNG/Figure_1.png) | 1 · [figure_01_spillover_compensation.ipynb](../notebooks/final_figures/figure_01_spillover_compensation.ipynb) |
| 2. Clustering benchmark | A–H | [PNG](../figures/current_manuscript/PNG/Figure_2.png) | 2 · [figure_02_clustering_method_benchmark.ipynb](../notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb) |
| 3. LLM annotation benchmark | A–E | [PNG](../figures/current_manuscript/PNG/Figure_3.png) | 3 · [figure_03_llm_annotation_benchmark.ipynb](../notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb) |
| 4. Selected Leiden–Astra pipeline | A–E | [PNG](../figures/current_manuscript/PNG/Figure_4.png) | 4 · [figure_04_leiden_gpt_end_to_end.ipynb](../notebooks/final_figures/figure_04_leiden_gpt_end_to_end.ipynb) |
| 5. Cross-donor annotation | A–D | [PNG](../figures/current_manuscript/PNG/Figure_5.png) | [Donor renderer](../scripts/render_donor47_figures.py) |
| S1. Leiden–Opus 5.5 diagnostics | A–B | [PNG](../figures/current_manuscript/PNG/Figure_S1.png) | S6 · [figure_s06_annotation_diagnostics.ipynb](../notebooks/final_figures/figure_s06_annotation_diagnostics.ipynb) |
| S2. Matched prompt controls and cross-model support calibration | A–D | [PNG](../figures/current_manuscript/PNG/Figure_S2.png) | S9 · [figure_s09_prompt_controls_and_calibration.ipynb](../notebooks/final_figures/figure_s09_prompt_controls_and_calibration.ipynb) (Nov. 11 snapshot) |
| S3. Cluster quality after compensation | A–C | [PNG](../figures/current_manuscript/PNG/Figure_S3.png) | S1 · [figure_s01_clustering_metrics.ipynb](../notebooks/final_figures/figure_s01_clustering_metrics.ipynb) |
| S4. Spatial label changes after compensation | A–B | [PNG](../figures/current_manuscript/PNG/Figure_S4.png) | S2 · [figure_s02_spatial_celltypes.ipynb](../notebooks/final_figures/figure_s02_spatial_celltypes.ipynb) |
| S5. Matching-rule sensitivity and shared-object compensation | A–C | [Part A](../figures/current_manuscript/PNG/Figure_S5_part_A.png) · [Part B](../figures/current_manuscript/PNG/Figure_S5_part_B.png) · [Part C](../figures/current_manuscript/PNG/Figure_S5_part_C.png) | S3 · [figure_s03_matching_and_compensation.ipynb](../notebooks/final_figures/figure_s03_matching_and_compensation.ipynb) |
| S6. Reference cell types and clustering diagnostics | A–D | [PNG](../figures/current_manuscript/PNG/Figure_S6.png) | S4 · [figure_s04_reference_and_clustering_diagnostics.ipynb](../notebooks/final_figures/figure_s04_reference_and_clustering_diagnostics.ipynb) |
| S7. Reference-agreement upper bounds | A | [PNG](../figures/current_manuscript/PNG/Figure_S7.png) | S5 · [figure_s05_reference_bounds.ipynb](../notebooks/final_figures/figure_s05_reference_bounds.ipynb) |
| S8. Reference-agreement decomposition | Unlettered | [PNG](../figures/current_manuscript/PNG/Figure_S8.png) | S7 · [figure_s07_agreement_decomposition.ipynb](../notebooks/final_figures/figure_s07_agreement_decomposition.ipynb) |
| S9. Paired means and fractions comparison | A–D | [PNG](../figures/current_manuscript/PNG/Figure_S9.png) | S10 · [figure_s10_paired_representations.ipynb](../notebooks/final_figures/figure_s10_paired_representations.ipynb) |
| S10. Marker-representation controls | A–D | [PNG](../figures/current_manuscript/PNG/Figure_S10.png) | S8 · [figure_s08_marker_representation_controls.ipynb](../notebooks/final_figures/figure_s08_marker_representation_controls.ipynb) (Nov. 11 snapshot) |
| S11. CD8+ T marker-expression profiles | A | [PNG](../figures/current_manuscript/PNG/Figure_S11.png) | S11 · [figure_s11_cd8_profiles.ipynb](../notebooks/final_figures/figure_s11_cd8_profiles.ipynb) |
| S12. Donor clustering and SpatialSort seed sensitivity | A–C | [PNG](../figures/current_manuscript/PNG/Figure_S12.png) | [Donor renderer](../scripts/render_donor47_figures.py) |
| S13. Original 28-label and projected 23-label evaluation | A–D | [PNG](../figures/current_manuscript/PNG/Figure_S13.png) | [Donor renderer](../scripts/render_donor47_figures.py) |
| S14. Reference cell maps for all 24 regions | Unlettered | [PNG](../figures/current_manuscript/PNG/Figure_S14.png) | Saved manuscript artwork |

- Figures 1 and S3–S5 cover the independent spillover-compensation and matching analyses. Figures 2, S6 and S7 use the frozen B004 clustering partitions. Figure 2E–H scores 220,082 cells using the original 28-label vocabulary, including Noise. Figure S7 uses the original 28-label vocabulary including Noise.
- Figures 3, 4, S1, S8, S9 and S11 use the [completed B004 primary annotation bank](../data/frozen/annotation47_results_20261111/manifest.json). Figure 4 shows the selected Leiden–Astra pipeline. Figure S1 is the supplementary Leiden–Opus 5.5 comparison.
- Figure S2 uses the completed matched prompt controls and the cross-model support calibration. Figure S10 uses all 64 completed marker-representation conditions. The [completed B004 replay](revision/reviewer47_completed_publication_20261115.md) verifies the recovered DeepSeek item and the Astra extension.
- Figures 5, S12 and S13 use the [completed cross-donor bank](../data/frozen/donor47_deepseek_completion_20261116/manifest.json). Figure S14 shows the dataset reference annotations across all 24 regions.

The [native exports](../figures/publication) and [reproduction instructions](manuscript_reproduction.md) retain the stable source paths for replay and editable artwork.
