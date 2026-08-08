# Figure 2, Panel B — Ground-truth cell type distribution

## Scope

Panel B uses only the eight B004 `File_ID` values declared in
[`configs/figure_02.yaml`](../configs/figure_02.yaml). It reads
`obs.cell_type_update` directly from
`20251007_cleaned_trainingdata_yang.h5ad`; neither `master.csv` nor
`truth.csv` is required for the panel.

The input contract validates 220,082 unique `(File_ID, ID)` cells, the eight
expected region-level cell counts, and nonmissing reference labels before any
counts are plotted.

## Displayed labels

The supplied Panel B reference is a descending bar chart of the raw
`cell_type_update` labels. It omits only the raw `Noise` label (10,495 cells),
leaving 209,587 plotted cells across 27 labels. It does not apply the later
20-class evaluation harmonization; doing so would not reproduce the supplied
panel.

The exact 27 category counts and the one omitted-label count are declared in
the configuration and checked at runtime. Colors come from the compact,
tracked [`configs/cell_type_colors.csv`](../configs/cell_type_colors.csv)
snapshot; a same-named local color key is only a fallback if that tracked file
is unavailable. The configuration also records the source H5AD's SHA-256:
`a159bbeca2a4dd84dc265929d3b1d409c16be5e00a2f9819c012b8a5879c37e0`.

## Running from a clone

The H5AD and clustering artifacts remain local. After making them available,
set `CELL_MASKS_DATA_ROOT` to the directory containing the H5AD and install
the pinned Figure 2 environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-figure-02.txt
CELL_MASKS_DATA_ROOT=/path/to/cell_masks \
  PYTHONPATH=src .venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace \
  notebooks/main/figure_02_clustering_method_benchmark.ipynb \
  --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.kernel_name=python3
```

## Outputs

The Panel B notebook cell writes these local, gitignored artifacts:

- `outputs/figure_02/figure_02b_b004_ground_truth_cell_type_counts.csv`
- `outputs/figure_02/figure_02b_b004_ground_truth_cell_type_distribution.png`
- `outputs/figure_02/figure_02b_b004_ground_truth_cell_type_distribution.pdf`
- `outputs/figure_02/figure_02b_b004_provenance.json`

The PNG and PDF use raw count values, a zero baseline, descending category
order, and the `B` panel label shown in the supplied reference.
