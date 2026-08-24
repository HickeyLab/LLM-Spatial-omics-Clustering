# Supplementary figure notebooks

## Supplementary Figure S3 panel runner

`figure_s03_clustering_inputs_and_diagnostics.ipynb` contains one independent
code cell for each of Panels A--E:

- A: ground-truth protein-expression dot plot
- B: ground-truth maps for all eight B004 tissue regions
- C: ground-truth cluster composition for the four Figure 2 methods
- D: recovered exploratory FlowSOM cluster-count sensitivity curve
- E: clustering metric distributions

Panels A--C and E reuse the validated B004 cohort and frozen K=300 clustering
assignments from Figure 2. Their observed occupied-cluster counts are Leiden
300, FlowSOM 300, SpatialSort 246, and PIXIE 300. Panel D uses a frozen,
hash-validated historical table. No durable generator exists for that archived
sweep, and it is explicitly not a tuning or validation run of the final
FlowSOM pipeline.

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
