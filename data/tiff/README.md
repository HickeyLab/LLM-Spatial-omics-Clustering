# HuBMAP OME-TIFF inputs

This directory is a cache for TIFFs acquired from HuBMAP. The final figure
notebooks do not support a separate on-disk TIFF input source, and never
commit the large image payloads.

The active final notebooks automatically download and checksum-validate the
annotated H5AD from Duke Research Data Repository record 505, then load the
tracked frozen assignments. They do not download TIFFs during normal replay.

The eight B004 expression/mask pairs are needed only for a separate upstream
rerun of the image-native PIXIE clustering engine. To populate the
repository-local H5AD and TIFF caches for that workflow, run:

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
