# final source-rebuild notebooks

This directory contains the canonical final source notebooks copied from the
local final analysis track. The notebooks declare their runtime inputs and write
generated artifacts outside the versioned notebook source tree.

Included notebooks:

- `00_metric_contract_and_artifact_registry.ipynb`
- `figure_01_redsea_spillover_correction.ipynb`
- `figure_02_clustering_method_benchmark.ipynb`
- `figure_03_llm_annotation_benchmark.ipynb`
- `figure_04_leiden_gpt_end_to_end.ipynb`
- `figure_s01_clustering_metrics.ipynb`
- `figure_s02_spatial_celltypes.ipynb`
- `figure_s03_clustering_inputs_and_diagnostics.ipynb`
- `figure_s04_annotation_diagnostics.ipynb`
- `supplementary_note_01_llm_cluster_annotation.ipynb`
- `table_01_clustering_methods.ipynb`
- `table_s01_clustering_methods.ipynb`
- `table_s02_marker_summary_optimization.ipynb`

`figure_01_redsea_spillover_correction.ipynb` is a source-availability
record only: Figure 1 is intentionally omitted from the current final packet
until its REDSEA inputs are recovered. The supplementary notebooks use the
current manuscript numbering: `figure_s01_*` and `figure_s02_*` are S1/S2,
while `figure_s03_*` and `figure_s04_*` are the source-rebuilt S3/S4 packet
figures.

Executed notebooks, nested archive/reproduction copies, short-name aliases,
rendered PDFs/PNGs, and generated manifests remain outside this source
directory.

The shared clustering implementation used by the final figure notebooks is
tracked in `src/llm_spatial_omics_clustering/final_figures_runtime/`.

Before rebuilding a figure, each active source-rebuild notebook acquires the
paired B004 OME-TIFF inputs exclusively from the public HuBMAP asset service.
`SOURCE_REBUILD_TIFF_ROOT` is only the cache location for those downloads, not
an alternative TIFF input source. The downloader validates the eight declared
H5AD `File_ID` values, supports resumable transfers, and requires a
free-space preflight before it writes the roughly 46 GiB TIFF cache.
