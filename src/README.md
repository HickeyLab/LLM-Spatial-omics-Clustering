# Shared source code

Reusable loading, preprocessing, evaluation, and plotting code lives in the
`llm_spatial_omics_clustering` package:

- `duke_h5ad.py`: checksum-validated Duke record 505 H5AD acquisition
- `figure_02.py`: B004 cohort and clustering-method benchmark
- `figure_s03.py`: Supplementary Figure S3 ground-truth and clustering
- `final_figures_runtime/`: shared H5AD-derived clustering, TIFF validation,
  HuBMAP TIFF acquisition, and metric helpers used by the final figure notebooks

The Supplementary Figure S3 module reuses Figure 2's validated cohort and
method-assignment loaders so its PIXIE panels use the image-native TIFF result.
Its recovered historical FlowSOM sensitivity input is isolated and
hash-validated rather than presented as a rerun of the final method.
