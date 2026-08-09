# Evaluation of Clustering Methods and LLMs for CODEX Cell-Type Annotation

Repository for the manuscript analysis:

> *Evaluation of Clustering Methods and Large Language Models for Spatial
> Proteomic Cell Type Annotation*

This repository contains source-traced figure notebooks and the shared code
and contracts needed to rerun the available analyses. Raw data and generated
artifacts remain local-only.

## Repository layout

```text
.
├── configs/                         # Version-controlled figure contracts
├── data/                            # Local-only raw, interim, and processed data
├── docs/                            # Figure map and project documentation
├── notebooks/
│   ├── main/                        # Core Figure 2 notebook
│   ├── final_figures/               # Source-locked final figure notebooks
│   └── supplementary/               # Reserved for finalized supplementary figures
├── outputs/                         # Generated outputs, separated by figure
├── src/
│   └── llm_spatial_omics_clustering # Shared Python code
└── tests/                           # Focused contract tests
```

## Main figure notebooks

| Figure | Topic | Notebook |
| --- | --- | --- |
| 1 | REDSEA spillover correction | `notebooks/final_figures/figure_01_redsea_spillover_correction.ipynb` |
| 2 | Clustering-method benchmark | `notebooks/main/figure_02_clustering_method_benchmark.ipynb` |
| 3 | LLM annotation benchmark | `notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb` |
| 4 | End-to-end Leiden–GPT pipeline | `notebooks/final_figures/figure_04_leiden_gpt_end_to_end.ipynb` |

The current manuscript references supplementary figures, but does not define a
stable supplementary figure map. See
[`docs/figure_map.md`](docs/figure_map.md) before adding those notebooks.

## Working conventions

- Keep one notebook as the entry point for each manuscript figure.
- Put reusable data processing, metrics, and plotting functions in `src/`
  rather than copying them between notebooks.
- Write generated tables and panels to the matching `outputs/figure_XX/`
  directory.
- Keep raw and derived data out of Git; each local data tier is documented in
  `data/`.
- Make every completed notebook runnable from top to bottom without hidden
  state.

Environment and data-access instructions will be added when the analysis
dependencies and data locations are finalized.
