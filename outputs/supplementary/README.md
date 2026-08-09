# Supplementary outputs

Use one subdirectory per finalized supplementary figure.

## Supplementary Figure 1

`figure_s01/` contains the panel-level PNG/PDF figures, analysis tables, and
provenance JSON files produced by
`notebooks/supplementary/figure_s01_clustering_inputs_and_diagnostics.ipynb`.
Each filename starts with its panel identifier (`figure_s01a` through
`figure_s01e`).

## Supplementary Figure 2

The final source notebook
`notebooks/final_figures/figure_s02_annotation_diagnostics.ipynb` writes its
Panel A/B artifacts under the ignored `outputs/source_rebuilt/` directory.
No checked-in placeholder execution is represented as a generated panel.

Future finalized supplementary figures should use sibling directories named
`figure_sXX/`.
