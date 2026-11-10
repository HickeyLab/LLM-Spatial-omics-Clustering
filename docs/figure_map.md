# Current manuscript figure map

The [inventory](../configs/manuscript_inventory.json) records the retained 47-marker study and the checked manuscript artwork. Display identifiers are retained even where intervening archived figures have been removed.

| Figure | Panels | Notebook |
| --- | --- | --- |
| 1 | A–F | [figure_01_spillover_compensation.ipynb](../notebooks/final_figures/figure_01_spillover_compensation.ipynb) |
| 2 | A–H | [figure_02_clustering_method_benchmark.ipynb](../notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb) |
| 3 | A–E | [figure_03_llm_annotation_benchmark.ipynb](../notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb) |
| 4 | A–E | [figure_04_leiden_claude_end_to_end.ipynb](../notebooks/final_figures/figure_04_leiden_claude_end_to_end.ipynb) |
| S1 | A–C | [figure_s01_clustering_metrics.ipynb](../notebooks/final_figures/figure_s01_clustering_metrics.ipynb) |
| S2 | A–B | [figure_s02_spatial_celltypes.ipynb](../notebooks/final_figures/figure_s02_spatial_celltypes.ipynb) |
| S3 | A–C | [figure_s03_matching_and_compensation.ipynb](../notebooks/final_figures/figure_s03_matching_and_compensation.ipynb) |
| S4 | A–D | [figure_s04_reference_and_clustering_diagnostics.ipynb](../notebooks/final_figures/figure_s04_reference_and_clustering_diagnostics.ipynb) |
| S5 | A | [figure_s05_reference_bounds.ipynb](../notebooks/final_figures/figure_s05_reference_bounds.ipynb) |
| S6 | A–B | [figure_s06_annotation_diagnostics.ipynb](../notebooks/final_figures/figure_s06_annotation_diagnostics.ipynb) |
| S7 | Unlettered | [figure_s07_agreement_decomposition.ipynb](../notebooks/final_figures/figure_s07_agreement_decomposition.ipynb) |
| S10 | A–D | [figure_s10_paired_representations.ipynb](../notebooks/final_figures/figure_s10_paired_representations.ipynb) |
| S11 | A | [figure_s11_cd8_profiles.ipynb](../notebooks/final_figures/figure_s11_cd8_profiles.ipynb) |

Figures 1, S1, S2 and S3 retain the independent spillover-compensation and matching analyses. Figure 2A–H uses the frozen primary clustering partitions; E–H score 209,587 non-Noise cells with the stated 20-class mapping. S4 uses [all-47-channel reference profiles](../data/frozen/reference47_profiles_20261110/manifest.json) and clustering diagnostics, and S5A reports fixed-partition upper bounds with the original 28 labels including Noise. S5 has no shared-45-marker cluster-count sensitivity panel.

Figures 3, 4, S6, S7, S10 and S11 are numerically rebuilt from the [completed annotation results](../data/frozen/annotation47_results_20261110/manifest.json). Figure 3B/C report equal-test-region agreement and fixed-28-label macro-F1; D uses pooled Leiden test cells, and E shows the fixed Figure 2C mid-jejunum region. Figure 4 uses the prespecified Leiden–Opus 5.5 pipeline: B/C use test cells and D/E use all cells. Figure S6 uses the corresponding test confusion and full-cohort cluster diagnostics. S7 decomposes the 16 primary test-region outcomes; S10 compares the two input arms without repeated-generation SD. S11 displays raw processed marker profiles of four model-consensus CD8+ T groups, with ties in Astra, Opus, Argon and DeepSeek order and no reference-label selection.

Thirteen figure identifiers correspond to 15 PNG images because S3 has three image parts. The PNG/TIFF/PDF/SVG exports, notebook previews and image hashes are synchronized. Figure 5, S8, S9 and superseded panel arrangements are preserved only in the [archive](../data/historical/publication_before_primary47_20261109/index.json). They are not current manuscript figures. [Reproduction instructions](manuscript_reproduction.md) identify the current renderers and clearly separate archival reconstruction commands.
