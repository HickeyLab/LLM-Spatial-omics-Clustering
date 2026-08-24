# HuBMAP OME-TIFF inputs

This directory is a cache for TIFFs acquired from HuBMAP. The final figure
notebooks do not support a separate on-disk TIFF input source, and never
commit the large image payloads.

The active final source-rebuild notebooks automatically download and
checksum-validate the annotated H5AD from Duke Research Data Repository record
505 before acquiring the eight B004 expression/mask pairs from HuBMAP. To
populate the same repository-local caches from the command line, run:

```bash
PYTHONPATH=src python3.12 -m llm_spatial_omics_clustering.duke_h5ad

PYTHONPATH=src python3.12 -m llm_spatial_omics_clustering.final_figures_runtime.hubmap \
  --h5ad data/raw/duke_research_repository/20260130_HuBMAP_experted_annotated.h5ad \
  --tiff-root data/tiff
```

The full paired TIFF set is approximately 46 GiB; acquisition first requires
the missing bytes plus a 1 GiB free-space reserve and leaves resumable `.part`
files if interrupted. Each completed TIFF carries a HuBMAP source receipt, so
an arbitrary pre-existing local file is not accepted as a source. The downloader
writes `hubmap_tiff_manifest.json` only after all required TIFFs are complete;
the source runtime checks the receipts again before invoking PIXIE.
