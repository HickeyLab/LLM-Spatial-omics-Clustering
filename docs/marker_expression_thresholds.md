# Publication marker-expression dot sizes

The embedded S4A and 2I publication panels both use a strict operational cutoff
of **stored processed marker value > 0.0**. This equality was verified from each
actual producer separately. It is not a rule for all marker analyses.

| Panel | Cells in the denominator | Values compared with cutoff | Added expression transform | Color |
| --- | --- | --- | --- | --- |
| S4A | All cells of each original reference type, excluding Noise, 209,587 cells across 27 types | 45 stored H5AD `X` marker values | None in the dot-plot calculation | All-cell group means, min–max scaled per marker across 27 reference types |
| 2I | Cells assigned CD8+ T by each method's modal raw LLM prediction | 45 historical H5AD marker columns exported through `master.csv` and converted to float32 `AnnData.X` | None in the dot-plot calculation | All-cell group means, min–max scaled per marker across four method groups |

For each displayed group g and marker m, the encoded fraction is
`q(g,m) = count(i in g: X[i,m] > 0.0) / n(g)`. The size key expresses it as a
percentage. Values equal to zero are excluded from the numerator. All cells
in the group remain in the denominator and in the color mean. Min–max scaling
is applied to the group means for color after the fractions are calculated,
not to individual values before thresholding. Dot area is a visual encoding,
including the producer's size floor/size scaling, not a calibrated positive-cell count.

S4A is produced by `v3_scripts/historical_v1_figure_s01_replay.py`, historically
numbered S1. It reads `20251007_cleaned_trainingdata_yang.h5ad` directly and
compares `X > 0`. Its retained biological vocabulary is the original 27
non-Noise cell types. It does not use a harmonized evaluation vocabulary.

The current 2I producer is `v3_scripts/historical_v1_figure02_ij_replay.py`,
adapted from `dotplot_cd8t_methods.py`. It constructs `AnnData.X` from stored
`master.csv` values, without `.raw` or another layer, and calls Scanpy dotplot
with `standard_scale="var"`. The historical call used Scanpy's strict default
cutoff of 0.0, `log=False` and `mean_only_expressed=False`. Those values are now
explicit in the actual producer. Scanpy's [primary implementation](https://github.com/scverse/scanpy/blob/1.11.5/src/scanpy/plotting/_dotplot.py#L127-L210)
confirms the strict comparison and that `standard_scale` changes the color
means, not the above-cutoff fractions. This implementation lookup does not
establish the exact historical library version.

The source H5AD is checksum-matched to the publication audit. It has 2,158,155
rows and 45 columns, an empty `uns`, no `.raw` and no expression layers.
Inspected stored values include negatives. Its upstream transformation history
cannot be recovered from that metadata. Do not describe `X` as unprocessed
fluorescence intensity or the thresholded fraction as validated biological
marker positivity. No marker-specific positivity validation for this cutoff
was established by these plotting sources. The 2I master export is currently
an iCloud placeholder, so its numerical table was not independently rerun in
this display revision. Its existing source hash and selected-cell counts are
preserved in the audit.

## Source boundaries and future rendering

The later package modules also use configurable above-cutoff fractions. Their
legend and provenance text now state the configured cutoff and stored-value
matrix. Internal `fraction_positive` is retained as a legacy compatibility
column and is documented as an operational fraction. `render_panel_i` carries
the loader's cutoff through DataFrame attrs, accepts an explicit cutoff for
CSV-loaded tables and falls back to the configured panel cutoff for legacy
inputs. Other analysis-specific cutoffs are unchanged.

The final-figures notebook reconstructions are different calculations. S4A
there applies arcsinh(x/5), selects 12 markers and 10 harmonized types and sizes
dots by scaled means. Its corresponding 2I is a clustering-metric overview.
They are now explicitly marked as alternatives and must not inherit this
publication fraction caption. No notebook was executed, no model called and
no threshold selected to prepare these display changes.

Machine-readable source hashes, exact calculation snippets, group counts and
metadata observations are in `marker_expression_threshold_audit.json`.
