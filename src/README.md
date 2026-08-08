# Shared source code

Reusable loading, preprocessing, evaluation, and plotting code lives in the
`llm_spatial_omics_clustering` package:

- `figure_02.py`: B004 cohort and clustering-method benchmark
- `figure_03.py`: LLM annotation benchmark
- `figure_04.py`: end-to-end Leiden--GPT evaluation
- `figure_s01.py`: Supplementary Figure 1 ground-truth and clustering
  diagnostics
- `figure_s02.py`: Supplementary Figure 2 count confusion and per-Leiden-
  cluster accuracy

The Supplementary Figure 1 module reuses Figure 2's validated cohort and
method-assignment loaders so its PIXIE panels use the image-native TIFF result.
Its recovered historical FlowSOM sensitivity input is isolated and
hash-validated rather than presented as a rerun of the final method.

The Supplementary Figure 2 module delegates analysis loading to Figure 4 so
both panels share its selected OpenAI/reasoning/optimized-Leiden mapping,
selection lock, and fail-closed credential guard. Legacy S2 maps are retained
only as provenance warnings.
