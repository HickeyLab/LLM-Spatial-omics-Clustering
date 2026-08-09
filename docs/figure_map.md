# Manuscript figure map

This map is derived from the current manuscript captions. It defines notebook
ownership only; it does not add or reproduce any analysis.

## Main figures

| Figure | Caption topic | Panels | Notebook | Output directory |
| --- | --- | --- | --- | --- |
| 1 | Effects of REDSEA spillover correction on downstream cell clustering | A–I | `notebooks/main/figure_01_redsea_spillover_correction.ipynb` | `outputs/figure_01/` |
| 2 | Benchmarking unsupervised cell-type clustering methods | A–J | `notebooks/main/figure_02_clustering_method_benchmark.ipynb` | `outputs/figure_02/` |
| 3 | Benchmarking LLM-assisted cell-type annotation | A–H | `notebooks/main/figure_03_llm_annotation_benchmark.ipynb` | `outputs/figure_03/` |
| 4 | End-to-end evaluation of the Leiden–GPT annotation pipeline | A–F | `notebooks/main/figure_04_leiden_gpt_end_to_end.ipynb` | `outputs/figure_04/` |

Figure 1 remains `VERIFY:` source-unavailable and is intentionally omitted from
the current final publication packet; its reserved notebook and output directory
record the scope without generating placeholder panels.

Figure 3 publication labels are sequential `A–H`. They map to the retained
historical source panels `A, F, G, H, I, J, K, L` respectively; the source
notebook retains its historical panel IDs for provenance.

## Supplementary figures

The user-supplied composites fix Supplementary Figure 1 as Panels A--E and
Supplementary Figure 2 as Panels A--B. Their working titles remain `VERIFY:`
until final captions are supplied.

| Figure | Working topic | Panels | Notebook | Output directory |
| --- | --- | --- | --- | --- |
| S1 | `VERIFY:` Ground-truth phenotypes and clustering diagnostics | A--E | `notebooks/supplementary/figure_s01_clustering_inputs_and_diagnostics.ipynb` | `outputs/supplementary/figure_s01/` |
| S2 | `VERIFY:` Leiden--GPT count confusion and per-cluster accuracy | A--B | `notebooks/supplementary/figure_s02_leiden_gpt_diagnostics.ipynb` | `outputs/supplementary/figure_s02/` |

The manuscript also references `S4` and `S5`, but does not include complete
supplementary captions. Some panel numbers remain reused for different
analyses:

- `S4` is referenced for both compensation metrics and end-to-end pipeline
  analyses.
- `S3` is not referenced.

Create notebooks for the remaining supplementary figures only after their
numbering and captions are reconciled. Until then,
`notebooks/supplementary/` and `outputs/supplementary/` remain their reserved
locations.
