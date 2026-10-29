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
changes, six source-verified metric-label changes in Figure 2, a descriptive
modal-map heading in Figure 3H and a prompt-provenance overlay in Figure 3A. See
[the metric audit](figure_02_publication_metrics.md).
Their data are retained from the pinned original Git revision. The plotting
code and configuration titles use the same terminology for future rendering.
Internal `Ground Truth` table keys and `truth_label` fields remain unchanged
for compatibility and are not rendered as map headings.

See [the preview provenance](../notebooks/final_figures/previews/README.md) and
[the coordinate manifest](reference_figure_label_changes.json) for exact source
and output hashes. The patch script verifies that all pixels outside its
overlay rectangles remain identical. There are no new fits, model calls or biological label merges. A read-only
recalculation verifies the existing Figure 2 E/G count tables and changes no
score.

The Figure 3 changes and matching caption are documented in
[the prompt-provenance and modal-label notes](figure_03_workflow_and_modal_labels.md).

Figures 4D–E and S4B now identify the Historical majority-based diagnostic.
Figure S8 uses the corrected aggregate-identity terminology. These source
calculations retain minority-label matches. See
[the source/count audit](diagnostic_identity_labels.md). Nine previews now have
54 declared overlay regions, including frozen Figure 1, S1 and S8 source snapshots.

Figure 1B and S1 use “Tissue-region-level change” and/or “Mean across tissue
regions.” S3E identifies its ARI/AMI dots as imaged tissue regions. The legacy
`slide_name`, `sample_ID` and `File_ID` fields resolve to the same eight B004
image datasets. No distinct physical-slide or FOV replicate is asserted. S1 was
restored from existing cached plots. See [the crosswalk and manuscript wording](tissue_region_analysis_units.md).

S3A and 2I identify their source-verified strict cutoff in stored processed
values, with scaled means identified separately for color. See
[the marker-expression audit](marker_expression_thresholds.md).

Table S2 removes displayed “V3” shorthand and the unsupported benchmark-use
claim. Its PIXIE-style export identity is preserved with an explicit qualification.
See [the implementation and archived-prompt audit](table_s02_export_provenance.md).

Figure S7 adds a tenth preview, rendered separately from 32 frozen values.
Condition and metric labels match the manuscript, and both panels use the
performance-heatmap palette with a shared 0–100% scale. It is outside the
nine-image text-overlay manifest because its quantitative color mapping
changes. See [the S7 notes](figure_s07_condition_labels.md).
