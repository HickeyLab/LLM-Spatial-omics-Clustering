# Figure 2 Panels F–J

These five notebook cells use the same B004 H5AD reference labels and selected
method artifacts as Panel D. `Noise` is excluded only where the historical
metric or spatial source did so. Every assignment is joined by exact
`File_ID` + `ID` keys.

## TIFF PIXIE consistency

The supplied legacy panel screenshots used the table-level
`PIXIE/pixie_meta50_styled_clusters.csv` result. Figure 2 now consistently
uses the validated image-native, 50-cluster TIFF artifact configured for Panel
D. Consequently, FlowSOM, Leiden, and SpatialSort reproduce their historical
values, while PIXIE values and maps are recomputed and can differ.

## Metrics and maps

- **F:** global, per-reference-cell-type F1 after non-Noise 20-class
  harmonization and a global cluster-majority label mapping.
- **G:** one tissue-level purity observation per `File_ID` and method; tissue-level
  mappings are made within that region.
- **H:** the historical label “purity” means per-reference-cell-type recall
  after a global majority mapping, not cluster purity.
- **I:** native H5AD-X marker means for all cells in a globally raw-label
  CD8+ T-majority cluster; dot area is the fraction with `X > 0` and color is
  min–max scaled independently per marker. `VERIFY:` the attached Methods do
  not state whether Noise-reference cells in those clusters should be removed;
  the legacy source retained them.
- **J:** raw-label spatial maps exclude only reference Noise cells after
  global majority labeling. Its TIFF-specific low/high windows were selected
  by the local deterministic candidate search. `VERIFY:` seed 42, quantile
  bounds, candidate count, and radius grid are implementation-derived details
  not specified in the attached Methods.

Run only the relevant Figure 2 notebook code cell. Each writes local CSV,
PNG, PDF, and JSON provenance artifacts under `outputs/figure_02/`; generated
artifacts remain gitignored.
