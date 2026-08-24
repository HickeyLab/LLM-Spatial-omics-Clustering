# Evaluation of Clustering Methods and LLMs for CODEX Cell-Type Annotation

The canonical figure notebooks, visible results, input contracts, and shared
analysis code are kept together here. Raw data and generated run artifacts are
excluded from Git.

## Start here

No setup is needed to inspect the results on GitHub. Open a notebook in the
table below.

| Item | Notebook |
| --- | --- |
| Figure 1 | [`figure_01_spillover_compensation.ipynb`](notebooks/final_figures/figure_01_spillover_compensation.ipynb) |
| Figure 2 | [`figure_02_clustering_method_benchmark.ipynb`](notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb) |
| Figure 3 | [`figure_03_llm_annotation_benchmark.ipynb`](notebooks/final_figures/figure_03_llm_annotation_benchmark.ipynb) |
| Figure 4 | [`figure_04_leiden_gpt_end_to_end.ipynb`](notebooks/final_figures/figure_04_leiden_gpt_end_to_end.ipynb) |
| Supplementary Figure S1 | [`figure_s01_clustering_metrics.ipynb`](notebooks/final_figures/figure_s01_clustering_metrics.ipynb) |
| Supplementary Figure S2 | [`figure_s02_spatial_celltypes.ipynb`](notebooks/final_figures/figure_s02_spatial_celltypes.ipynb) |
| Supplementary Figure S3 | [`figure_s03_clustering_inputs_and_diagnostics.ipynb`](notebooks/final_figures/figure_s03_clustering_inputs_and_diagnostics.ipynb) |
| Supplementary Figure S4 | [`figure_s04_annotation_diagnostics.ipynb`](notebooks/final_figures/figure_s04_annotation_diagnostics.ipynb) |
| Supplementary Table S1 | [`table_s01_clustering_methods.ipynb`](notebooks/final_figures/table_s01_clustering_methods.ipynb) |
| Supplementary Table S2 | [`table_s02_marker_summary_optimization.ipynb`](notebooks/final_figures/table_s02_marker_summary_optimization.ipynb) |

Figures 1, S1, and S2 and Tables S1–S2 contain embedded executed outputs;
Figures 2–4 and S3–S4 display validated publication previews and are not
stored as executed notebooks.

Validated publication previews and their audit hashes are available in
[`notebooks/final_figures/previews/`](notebooks/final_figures/previews/README.md).

## Repository layout

```text
.
├── configs/                         # Version-controlled analysis contracts
├── data/                            # Versioned small inputs and ignored source-data caches
├── docs/                            # Figure maps and provenance notes
├── notebooks/
│   ├── final_figures/               # One canonical collection for the manuscript
│   └── supplementary/               # Supporting panel-level figure runners
├── outputs/                         # Gitignored generated tables and figures
├── src/llm_spatial_omics_clustering # Shared loading, clustering, and metrics code
└── tests/                           # Focused contract and runtime tests
```

`notebooks/final_figures/` is the only reviewer-facing figure entry point. A
supporting notebook under `notebooks/supplementary/` can regenerate the five
Supplementary Figure S3 panels independently; it uses the same S3 numbering
throughout and is not a second manuscript figure.

## Local setup

Python 3.12 is the supported runtime.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_final_figures_runtime.py'
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_hubmap_tiff_download.py'
```

Launch the canonical notebooks with:

```bash
.venv/bin/python -m jupyter notebook notebooks/final_figures
```

## Full regeneration

Figure 1 and Supplementary Figure S1 use twelve local H5AD files forming six
before/after REDSEA pairs; Supplementary Figure S2 uses the corresponding
three-method subset. Figure 1 Panels C--F and Supplementary Figure S2 also use
the historical HuBMAP reference
`20260130_HuBMAP_Yang_annotate_with_area.h5ad`. These 13 files are publicly
available in [Duke Research Data Repository record
565](https://research.repository.duke.edu/record/565) (version 1, DOI
[`10.7924/r4r565`](https://doi.org/10.7924/r4r565)). Download them into the
repository-relative `data/processed/` directory before running the Figure 1,
S1, or S2 notebooks. Published filenames, byte sizes, and MD5 checksums are
recorded in [`configs/duke_record_565_manifest.json`](configs/duke_record_565_manifest.json).

Figures 2--4 and Supplementary Figures S3--S4 download and checksum-validate
`20260130_HuBMAP_experted_annotated.h5ad` from [Duke Research Data Repository
record 505](https://research.repository.duke.edu/record/505). Their normal
analytical replay loads the exact source-traced clustering partitions tracked
under [`data/frozen/v3_k300_assignments/`](data/frozen/v3_k300_assignments/README.md):
all methods targeted K=300, with occupied counts 300, 300, 246, and 300 for
Leiden, FlowSOM, SpatialSort, and PIXIE. The notebooks validate decompressed
source hashes and the shared 220,082-cell key set; they do not download the
roughly 46 GiB TIFF collection or rerun the upstream clustering engines.

The annotation notebooks require an OpenRouter API key in live mode or the
corresponding cached raw response bundles. Supply a live key through the
environment:

```bash
export OPENROUTER_API_KEY='...'
```

Re-running the upstream image-native PIXIE or SpatialSort clustering engines
from raw data is a separate provenance task. It requires the paired HuBMAP
OME-TIFF expression/mask assets (roughly 46 GiB), external method software,
and the source-traced settings recorded in the frozen assignment manifest.
That upstream engine rerun is not required to reproduce the published tables
and downstream analyses from the exact frozen partitions.

The Duke record 505 H5AD has the columns needed by the Figure 1
reference-matching step, but equivalence to the historical Figure 1 reference
has not been established; record 505 also does not contain the twelve REDSEA
H5AD inputs.

Generated tables, panels, download receipts, and raw model responses are
written under `outputs/` and remain ignored by Git.
