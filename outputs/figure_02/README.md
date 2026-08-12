# Figure 2 outputs

This directory retains panel-level outputs from the earlier Figure 2
reconstruction. The canonical publication notebook is
`notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb`; its
current source-rebuilt artifacts are written under `outputs/source_rebuilt/`.

Current executable panels:

- **A:** supplied CODEX feature-extraction and clustering workflow artwork,
  hash-checked when the local source image is available;
- **B:** raw non-Noise B004 ground-truth cell-type distribution;
- **C:** B004-A-404 raw ground-truth tissue-region map;
- **D:** B004 ground-truth and method-derived UMAP comparison.
- **E:** B004 region-level, weighted cell-type F1 by clustering method.
- **F:** global per-cell-type F1 heatmap with reference-cell counts.
- **G:** B004 region-level tissue-level purity box-and-strip plot.
- **H:** global per-cell-type recovery-purity heatmap with reference-cell counts.
- **I:** CD8+ T-majority cluster protein-marker dot plot.
- **J:** TIFF-PIXIE low/high spatial agreement examples.

The rendered PNG/PDF files, count tables, coordinates, and provenance records
remain local and gitignored. Recreate them from the notebook rather than
committing generated data artifacts.
