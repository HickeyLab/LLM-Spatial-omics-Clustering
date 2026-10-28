# Reference terminology in figure artwork

Figures 2–4 and S3–S4 use “Reference annotations” for reference maps and
“Reference cell type” for confusion-matrix reference axes. Supplementary
Figure S3A uses “Protein expression by reference cell type,” and S3B uses
“Reference annotations across tissue regions.”

This terminology acknowledges uncertainty in the dataset annotations. It does
not equate the original dataset vocabulary with the harmonized evaluation
vocabulary. The existing class names, ordering, normalization maps, class
counts, and predictions are preserved.

The five historical publication previews receive nine reference-terminology
changes plus six source-verified metric-label changes in Figure 2. See
[the metric audit](figure_02_publication_metrics.md).
Their data are retained from the pinned original Git revision. The plotting
code and configuration titles use the same terminology for future rendering.
Internal `Ground Truth` table keys and `truth_label` fields remain unchanged
for compatibility and are not rendered as map headings.

See [the preview provenance](../notebooks/final_figures/previews/README.md) and
[the coordinate manifest](reference_figure_label_changes.json) for exact source
and output hashes. The patch script verifies that all pixels outside its
text rectangles remain identical. There are no new fits, model calls or biological label merges. A read-only
recalculation verifies the existing Figure 2 E/G count tables and changes no
score.
