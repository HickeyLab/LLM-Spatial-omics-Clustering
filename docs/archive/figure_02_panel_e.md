# Figure 2, Panel E — Regional weighted F1

> **Publication boundary:** This document describes the later module function
> `load_panel_e_metrics`, not the embedded publication panel E. That panel
> displays post-hoc selected reference agreement, not weighted F1. See
> [the publication metric audit](figure_02_publication_metrics.md).

## Scope

Panel E compares the four configured clustering methods across the eight B004
`File_ID` values. It uses `obs.cell_type_update` from the Duke archive member
`CODEX_annotated/20260130_HuBMAP_experted_annotated.h5ad` as the reference
annotation, excludes `Noise`, and harmonizes the remaining labels into 20
evaluation classes.

## Calculation

For every method and tissue region separately, the module assigns each
cluster its most frequent harmonized reference label. It then computes
precision, recall, and F1 for every reference class present in that region;
the panel's regional statistic is the reference-cell-count-weighted mean of
those F1 values. The boxplot shows all eight regional observations with the
median, interquartile range, and Matplotlib's default 1.5-IQR whiskers.

The attached Methods text supports the regional majority mapping, exclusion of
absent classes, cell-count weighting, and eight plotted observations. For an
equal-count majority tie, the source implementation preserves the fixed H5AD
observation order and uses the first label returned by the legacy
`value_counts().idxmax()` calculation. This deterministic implementation rule
is recorded explicitly in the configuration.

## Assignment sources

All methods use the source-traced Panel D assignments tracked beneath
`data/frozen/v3_k300_assignments/`. Every method targeted K=300; the observed
occupied-cluster counts are Leiden 300, FlowSOM 300, SpatialSort 246, and PIXIE
300. The loader validates their source CSV hashes and exact 220,082-cell key
coverage against the frozen assignment manifest before calculating this panel.

## Reproduction

The later Figure 2 module loader downloads the H5AD into its ignored Duke cache when absent;
the exact assignment inputs are version controlled. Use `load_panel_e_metrics`, `render_panel_e` and `save_panel_e_provenance` in
`src/llm_spatial_omics_clustering/figure_02.py` for this reconstruction. The
current notebook is another reconstruction and does not produce the embedded
publication E/G metrics.

The module helpers write the regional score table, PNG, PDF, and JSON provenance record
to `outputs/figure_02/`; those generated artifacts stay local and gitignored.
