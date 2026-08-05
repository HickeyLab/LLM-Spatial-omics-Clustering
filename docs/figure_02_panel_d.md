# Figure 2, Panel D — B004 UMAP comparison

## Scope

Panel D uses only the eight `File_ID` values declared in
[`configs/figure_02.yaml`](../configs/figure_02.yaml), which are the specified
B004 tissue regions. The source is
`20251007_cleaned_trainingdata_yang.h5ad`; the panel input is built directly
from its 45 `X` variables plus `obs` columns `CD123`, `Hoechst1`, and `CDX2`.
The reference label is `obs.cell_type_update`.

Each of the five views uses one shared UMAP geometry and colors cells by:

1. their reference label (Ground Truth); or
2. the majority reference label of their Leiden, FlowSOM, SpatialSort, or
   TIFF-derived PIXIE cluster.

Cluster identifiers are unsupervised labels and are not plotted directly.

## Method-derived assignments

Leiden, FlowSOM, and SpatialSort use the existing selected B004 assignment
tables named in the configuration. They are exact-key validated against the
H5AD cohort and must contain 55, 300, and 60 clusters respectively.

PIXIE must use the TIFF-derived artifact, not the pre-existing table-level
50-cluster result. The local, gitignored artifact is produced by:

```bash
export CELL_MASKS_DATA_ROOT=/path/to/cell_masks
python3.12 "$CELL_MASKS_DATA_ROOT/PIXIE/run_streaming_tiff_pixie.py" \
  --master "$CELL_MASKS_DATA_ROOT/master.csv" \
  --tiffs-dir "$(dirname "$CELL_MASKS_DATA_ROOT")/Tiffs" \
  --output-dir data/processed/figure_02/pixie_tiff_methods_50 \
  --include-hoechst --blur-sigma 2 --pixel-som-side 10 \
  --pixel-meta-clusters 20 --som-passes 1 --cell-som-side 20 \
  --cell-meta-clusters 50 --cell-som-sigma 2.0 \
  --cell-som-learning-rate 0.3 --cell-som-iterations 5000 \
  --cell-som-decay asymptotic --cell-som-initialization minisom_default \
  --seed 42 --zero-signal-policy fail
```

The Panel D loader refuses incomplete PIXIE output or any manifest whose
critical parameters differ from the configuration.

The runner is the local streaming implementation: it preserves the documented
pixel-SOM → pixel-metacluster → pixel-to-cell composition → cell-SOM →
cell-metacluster sequence while avoiding full-resolution pixel-table staging.
It is therefore not represented as a byte-identical invocation of the archived
ARK/PIXIE stack.

## UMAP provenance

The attached Methods text gives exact clustering settings but not UMAP
settings. The current shared-UMAP settings were recovered from the existing
local implementation (`umap_flowsom_simple.py`) and are recorded as
`VERIFY:` in the configuration. They need author confirmation before being
claimed as manuscript methods.

The regenerated coordinates are not assumed to be byte-identical to any older
untracked coordinate export: UMAP and Harmony results can vary with software
versions despite a fixed seed. The visual geometry and declared B004 key set
are validated here; the manuscript method statement remains unresolved until
the intended embedding specification is confirmed.
