# Frozen original artwork

`figure_s08_original.png` is the exact original S8 image exported from the
manuscript before the display-label revision. It is a reproduction input,
not the revised publication preview. Its SHA-256 is
`805d5d84b70c3d5c6d0b2c4f02a9a5f185e9b38f70a53a435a9f6747ac6b2168`.
The coordinate manifest and preview script verify this hash, relabel only
declared text regions and preserve every other pixel. Calculation provenance
is in `docs/leiden_claude_diagnostic_identity_audit.json`.

`figure_01_original.png` is the exact current-manuscript Figure 1 exported
before the analysis-unit wording change. The revised preview preserves the
original A visual and all C–F pixels.
The current publication renderer also uses its original illustrated panel A,
with only its original raster text rectangles cleared and replaced by larger
editable Arial labels. Source crop, text rectangles, and label geometry are
declared in `configs/figure_01_original_workflow.json`. The current native A letter and
panels B–F are retained.

`figure_s01_original.png` stacks three existing cached notebook outputs
(cells 16–18) with A–C panel letters. It restores the image missing from the
current manuscript. No metric was recalculated. Component checksums, placement
coordinates and the eight-region crosswalk are recorded in
`docs/tissue_region_analysis_units.json`. The original cached notebook outputs
remain historical snapshots. Source and revised composite checksums are in
`docs/reference_figure_label_changes.json`.

`figure_s07_original.png` is the exact original S7 PNG exported from the
manuscript before the condition-label and palette revision. It is kept for
provenance and comparison. The revised S7 is rendered from its separate frozen
32-row result table, with source hashes in `docs/figure_s07_source_audit.json`.
