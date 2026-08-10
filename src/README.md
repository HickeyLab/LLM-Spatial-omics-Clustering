# Shared source code

Reusable loading, preprocessing, evaluation, and plotting code lives in the
`llm_spatial_omics_clustering` package:

- `figure_02.py`: B004 cohort and clustering-method benchmark
- `figure_s01.py`: Supplementary Figure 1 ground-truth and clustering
- `final_figures_runtime/`: shared H5AD-derived clustering, TIFF validation,
  HuBMAP TIFF acquisition, and metric helpers used by the final figure notebooks

The Supplementary Figure 1 module reuses Figure 2's validated cohort and
method-assignment loaders so its PIXIE panels use the image-native TIFF result.
Its recovered historical FlowSOM sensitivity input is isolated and
hash-validated rather than presented as a rerun of the final method.
