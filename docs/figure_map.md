# Manuscript figure map

This map is derived from the current manuscript captions. It defines notebook
ownership only; it does not add or reproduce any analysis.

## Main figures

| Figure | Caption topic | Panels | Notebook | Output directory |
| --- | --- | --- | --- | --- |
| 1 | Effects of REDSEA spillover correction on downstream cell clustering | A–I | `notebooks/main/figure_01_redsea_spillover_correction.ipynb` | `outputs/figure_01/` |
| 2 | Benchmarking unsupervised cell-type clustering methods | A–J | `notebooks/main/figure_02_clustering_method_benchmark.ipynb` | `outputs/figure_02/` |
| 3 | Benchmarking LLM-assisted cell-type annotation | A–L | `notebooks/main/figure_03_llm_annotation_benchmark.ipynb` | `outputs/figure_03/` |
| 4 | End-to-end evaluation of the Leiden–GPT annotation pipeline | A–F | `notebooks/main/figure_04_leiden_gpt_end_to_end.ipynb` | `outputs/figure_04/` |

## Supplementary figures

The manuscript currently references `S1`, `S2`, `S4`, and `S5`, but does not
include complete supplementary captions. Some panel numbers are reused for
different analyses:

- `S2` is referenced for compensation, clustering, and LLM analyses.
- `S4` is referenced for both compensation metrics and end-to-end pipeline
  analyses.
- `S3` is not referenced.

Create one notebook per supplementary figure only after the supplementary
numbering and captions are reconciled. Until then, use
`notebooks/supplementary/` and `outputs/supplementary/` as reserved locations.
