# Canonical figure notebooks

This is the single current notebook collection for the manuscript. The
notebooks declare their runtime inputs and write generated artifacts outside
the versioned source tree.

## Figures

- `figure_01_spillover_compensation.ipynb`
- `figure_02_clustering_method_benchmark.ipynb`
- `figure_03_llm_annotation_benchmark.ipynb`
- `figure_04_leiden_gpt_end_to_end.ipynb`
- `figure_s01_clustering_metrics.ipynb`
- `figure_s02_spatial_celltypes.ipynb`
- `figure_s03_clustering_inputs_and_diagnostics.ipynb`
- `figure_s04_annotation_diagnostics.ipynb`

Figure 1 and Supplementary Figures S1--S2 retain verified executed outputs.
The active Figure 2--4 and S3--S4 notebooks display hash-verified publication
previews from the validated run; their code-cell execution state remains empty
until a reviewer performs a full local rebuild.

## Supporting notebooks

- `00_metric_contract_and_artifact_registry.ipynb`
- `supplementary_note_01_llm_cluster_annotation.ipynb`
- `table_01_clustering_methods.ipynb`
- `table_s01_clustering_methods.ipynb`
- `table_s02_marker_summary_optimization.ipynb`

The small `previews/` collection is intentionally tracked for review. Its
files are output snapshots, never runtime inputs.

Before rebuilding Figures 2--4 or S3--S4, the notebooks acquire the verified
Duke H5AD and the paired B004 OME-TIFF inputs from HuBMAP. The TIFF downloader
validates the eight declared H5AD `File_ID` values, supports resumable
transfers, and performs a free-space preflight before writing the roughly
46 GiB cache.

Figure 1 and S1 use a separate historical input set: twelve H5AD files forming
six before/after REDSEA pairs; S2 uses the corresponding three-method subset.
Figure 1 Panels C--F and S2 also use the historical HuBMAP reference. The exact
13-file input set is published in [Duke Research Data Repository record
565](https://research.repository.duke.edu/record/565) (version 1, DOI
[`10.7924/r4r565`](https://doi.org/10.7924/r4r565)); place the files in the
repository-relative `data/processed/` directory. Record 505 remains the source
for Figure 2 and later figures and is not treated as equivalent to the
historical Figure 1 reference.

The Figure 1, S1, and S2 notebooks preserve plots from their verified
historical executions. Their source-discovery cells were updated for the
published record 565 layout but were not followed by a full data-backed rerun;
those cells are intentionally unexecuted, and the retained plots are review
evidence rather than proof that the new local path has been executed.

Shared clustering and validation code lives in
`src/llm_spatial_omics_clustering/final_figures_runtime/`.
