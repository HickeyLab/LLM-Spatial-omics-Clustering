# Author-provided BioRender workflows

`source_canvas.pdf` is the author's original 600 dpi/native-vector BioRender
export from https://app.biorender.com/illustrations/69a8866b418c74cd641a8cfc.
It contains the source illustrations for Figures 2A, 3A and 4A.

The source SHA-256, proportional clip rectangles and placements are in
`configs/biorender_workflows.json`. `scripts/biorender_workflows.py` removes
sub-print-size imported text and template captions; the figure renderer
retypes the retained scientific labels as editable Arial. No scientific
values are inferred from the schematic examples.

Created with BioRender.com by Zachary Deutsch. BioRender icons and other
third-party content remain subject to their own permissions. Inclusion does
not grant a separate license to extract or redistribute individual icons.
The author deferred the open-access publication-license form; this snapshot
does not assert a completed CC-BY license or a public BioRender citation URL.
