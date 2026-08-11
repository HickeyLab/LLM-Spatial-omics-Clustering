# Supplementary outputs

Use one subdirectory per finalized supplementary figure.

## Historical Supplementary Figure 1 outputs (current S3 compatibility path)

`figure_s01/` contains the panel-level PNG/PDF figures, analysis tables, and
provenance JSON files produced by
`notebooks/supplementary/figure_s01_clustering_inputs_and_diagnostics.ipynb`.
Each filename starts with its panel identifier (`figure_s01a` through
`figure_s01e`). These are retained under the historical compatibility path;
the current publication mapping for this panel set is Supplementary Figure S3.

## Current Supplementary Figures S1--S4

The four current supplementary source notebooks under
`notebooks/final_figures/` write their generated artifacts under the ignored
`outputs/source_rebuilt/` directory. No checked-in placeholder execution is
represented as a generated panel.

Future finalized supplementary figures should use sibling directories named
`figure_sXX/`.
