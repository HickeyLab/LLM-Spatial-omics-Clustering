# Supplementary figure notebooks

## Supplementary Figure S3 panel runner

`figure_s03_clustering_inputs_and_diagnostics.ipynb` contains one independent
code cell for each of Panels A--E:

- A: ground-truth protein-expression dot plot
- B: ground-truth maps for all eight B004 tissue regions
- C: ground-truth cluster composition for the four Figure 2 methods
- D: recovered exploratory FlowSOM cluster-count sensitivity curve
- E: clustering metric distributions

Panels A--C and E reuse the validated B004 cohort and clustering assignments
from Figure 2, including the image-native TIFF-derived PIXIE result. Panel D
uses a frozen, hash-validated historical table and remains explicitly marked
`VERIFY:` because it is not a sweep of the final Figure 2 FlowSOM pipeline.

Runtime dependencies are recorded in `requirements-figure-s03.txt`.

This supporting notebook, its `figure_s03` configuration and module, and its
generated output names all follow the current manuscript numbering. The
canonical reviewer-facing source-rebuild notebook is
`../final_figures/figure_s03_clustering_inputs_and_diagnostics.ipynb`.

## Current Supplementary Figure S4

The final source notebook
`../final_figures/figure_s04_annotation_diagnostics.ipynb` renders two panels:

- A: unnormalized cell-count confusion matrix
- B: per-Leiden-cluster correctness, annotation loss, and clustering loss

Both cells use the source-locked final model set and the same environment-only
or cached raw-response boundary as the other final figure notebooks. Generated
artifacts are written outside the versioned notebook source tree.

## Future supplementary figures

Add one notebook per supplementary figure after its number, caption, and panel
map are finalized.

Use the naming convention:

```text
figure_sXX_short_descriptive_name.ipynb
```

Do not combine unrelated supplementary figures in a single notebook.
