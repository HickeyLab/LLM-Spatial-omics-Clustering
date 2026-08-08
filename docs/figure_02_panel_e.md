# Figure 2, Panel E — Regional weighted F1

## Scope

Panel E compares the four configured clustering methods across the eight B004
`File_ID` values. It uses `obs.cell_type_update` from
`20251007_cleaned_trainingdata_yang.h5ad` as the reference annotation, excludes
`Noise`, and harmonizes the remaining labels into 20 evaluation classes.

## Calculation

For every method and tissue region separately, the notebook assigns each
cluster its most frequent harmonized reference label. It then computes
precision, recall, and F1 for every reference class present in that region;
the panel's regional statistic is the reference-cell-count-weighted mean of
those F1 values. The boxplot shows all eight regional observations with the
median, interquartile range, and Matplotlib's default 1.5-IQR whiskers.

The attached Methods text supports the regional majority mapping, exclusion of
absent classes, cell-count weighting, and eight plotted observations. `VERIFY:`
the Methods text does not define a tie-break when multiple labels are equally
common in a cluster. The implementation preserves the fixed H5AD observation
order and the legacy `value_counts().idxmax()` behavior for those ties.

## Assignment sources

FlowSOM, Leiden, and SpatialSort use the selected assignment tables configured
for Panel D. PIXIE uses the image-native, 50-cell-cluster TIFF artifact at
`data/processed/figure_02/pixie_tiff_methods_50/master_pixie_clusters.csv` and
validates its manifest against the configured TIFF parameters.

This choice intentionally differs from the supplied legacy screenshot's PIXIE
series: that screenshot was generated from the older table-level
`PIXIE/pixie_meta50_styled_clusters.csv` artifact, not TIFF-based PIXIE. The
three non-PIXIE series reproduce its regional values; the TIFF PIXIE points are
recomputed and therefore differ.

## Reproduction

Set `CELL_MASKS_DATA_ROOT` to the directory containing the H5AD and the three
non-PIXIE assignment CSVs. The TIFF PIXIE output remains local and gitignored
under the repository's `data/processed/` tree. Execute only the fifth code cell
of [`figure_02_clustering_method_benchmark.ipynb`](../notebooks/main/figure_02_clustering_method_benchmark.ipynb).

The cell writes the regional score table, PNG, PDF, and JSON provenance record
to `outputs/figure_02/`; those generated artifacts stay local and gitignored.
