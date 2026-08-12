# Figure 2, Panel C — Ground-truth tissue region

## Scope

Panel C is the B004 tissue region `B004-A-404`, whose H5AD `File_ID` is
`8da8f27977d946b8c912d42c8827b55c`. The supplied reference was matched to
this region's distinctive spatial geometry and checked against the B004
slide-to-`File_ID` map.

The panel reads only `File_ID`, `ID`, `x`, `y`, and `cell_type_update` from the
Duke archive member `CODEX_annotated/20260130_HuBMAP_experted_annotated.h5ad`.
It validates 36,464 unique cells, the Duke H5AD native-coordinate bounds
`x=13..9985` and `y=301..9509`, and the exact raw-label distribution before
rendering. The older local export used these two coordinate axes in the
opposite order; the Figure 2 contract now follows the Duke source without an
implicit axis swap.

## Rendering choices

The panel directly reproduces the verified legacy spatial rendering choices:
raw H5AD `x`/`y` coordinates without an axis inversion, equal aspect ratio,
hidden axes, 2-point markers, 0.8 alpha, and the tracked
[`configs/cell_type_colors.csv`](../configs/cell_type_colors.csv) palette.

All 27 raw labels are plotted, including 3,202 pale-pink `Noise` cells. This
is intentionally different from Panel B, which removes `Noise` only from its
cell-type distribution bar chart.

## Running from a clone

The H5AD remains local in the ignored Duke cache. The loader downloads it when
absent; run the Figure 2 notebook with the pinned local environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace \
  notebooks/final_figures/figure_02_clustering_method_benchmark.ipynb \
  --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.kernel_name=python3
```

## Outputs

The Panel C notebook cell writes these local, gitignored artifacts:

- `outputs/figure_02/figure_02c_b004_a404_ground_truth_tissue_cells.csv`
- `outputs/figure_02/figure_02c_b004_a404_ground_truth_tissue_region.png`
- `outputs/figure_02/figure_02c_b004_a404_ground_truth_tissue_region.pdf`
- `outputs/figure_02/figure_02c_b004_a404_provenance.json`
