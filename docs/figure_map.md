# Manuscript figure map

This map is derived from the current manuscript captions. It defines notebook
ownership only; it does not add or reproduce any analysis.

## Main figures

| Figure | Caption topic | Panels | Notebook | Output directory |
| --- | --- | --- | --- | --- |
| 1 | Effects of REDSEA spillover correction on downstream cell clustering | A–I | `notebooks/final_figures/figure_01_redsea_spillover_correction.ipynb` | `outputs/figure_01/` |
| 2 | Benchmarking unsupervised cell-type clustering methods | A–J | `notebooks/main/figure_02_clustering_method_benchmark.ipynb` | `outputs/figure_02/` |
| 3 | Benchmarking LLM-assisted cell-type annotation | A–L | `notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb` | `outputs/source_rebuilt/` |
| 4 | End-to-end evaluation of the Leiden–GPT annotation pipeline | A–F | `notebooks/final_figures/figure_04_leiden_gpt_end_to_end.ipynb` | `outputs/source_rebuilt/` |

Figure 1 remains `VERIFY:` source-unavailable and is intentionally omitted from
the current final publication packet; its reserved notebook and output directory
record the scope without generating placeholder panels.

## Supplementary figures

The current tracked figure files contain four distinct supplementary figures.
The older `notebooks/supplementary/` S1 contract is retained for reproducibility
but is a compatibility artifact for the current S3 panel set; it is not another
current S1 figure.

| Figure | Working topic | Panels | Notebook | Output directory |
| --- | --- | --- | --- | --- |
| S1 | Before/after compensation clustering metrics | A--C | `notebooks/final_figures/figure_s01_clustering_metrics.ipynb` | `outputs/source_rebuilt/` |
| S2 | Before/after compensation spatial cell-type comparisons | A--B | `notebooks/final_figures/figure_s02_spatial_celltypes.ipynb` | `outputs/source_rebuilt/` |
| S3 | `VERIFY:` Ground-truth phenotypes and clustering diagnostics | A--E | `notebooks/final_figures/figure_s03_clustering_inputs_and_diagnostics.ipynb` | `outputs/source_rebuilt/` |
| S4 | Source-rebuilt LLM annotation diagnostics | A--B | `notebooks/final_figures/figure_s04_annotation_diagnostics.ipynb` | `outputs/source_rebuilt/` |

The manuscript still references `S5` without a complete caption or source
notebook. It remains `VERIFY:` and is not assigned a tracked figure file.

The compatibility notebook
`notebooks/supplementary/figure_s01_clustering_inputs_and_diagnostics.ipynb`
and its `configs/figure_s01.yaml`/`src/.../figure_s01.py` implementation retain
their historical S1 names. Their current publication mapping is S3; the
canonical source-rebuild notebook is the S3 path in the table above.
