# HuBMAP OME-TIFF inputs

This directory is a cache for TIFFs acquired from HuBMAP. The final figure
notebooks do not support a separate on-disk TIFF input source, and never
commit the large image payloads.

The active final source-rebuild notebooks automatically acquire the eight B004
expression/mask pairs from HuBMAP before source rebuilding. To populate the
same cache from the command line, first place the registered Yang H5AD on disk
and run:

```bash
PYTHONPATH=src python -m llm_spatial_omics_clustering.final_figures_runtime.hubmap \
  --h5ad /path/to/20251007_cleaned_trainingdata_yang.h5ad \
  --tiff-root data/tiff
```

The full paired TIFF set is approximately 46 GiB; acquisition first requires
the missing bytes plus a 1 GiB free-space reserve and leaves resumable `.part`
files if interrupted. Each completed TIFF carries a HuBMAP source receipt, so
an arbitrary pre-existing local file is not accepted as a source. The downloader
writes `hubmap_tiff_manifest.json` only after all required TIFFs are complete;
the source runtime checks the receipts again before invoking PIXIE.
