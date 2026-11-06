# Retained manuscript previews

These 17 PNGs are byte-identical copies of the retained Figure 1–5 and
S1–S10 artwork in `figures/manuscript/`. Figure S3 has three image parts.
They predate the current manuscript panel reductions. Use the
[figure map](../../../docs/figure_map.md) and
[table crosswalk](../../../docs/supplementary_table_numbering.md) for the
November 6 display inventory, including Figure S11A and Table S9.

The retained Figure 3 artwork includes earlier reference-informed selection
panels. Current Figure 3E is the spatial comparison formerly labeled H and
uses each cluster's most frequent model label, with GPT, Claude, Gemini and
DeepSeek tie order without reference labels. Retained Figure 2I marker
profiles now support S11A, while the selected spatial windows are archived.

The [native exports](../../../figures/publication) retain editable vectors
and 600 dpi raster originals. The
[manifest](../../../docs/reference_figure_label_changes.json) pins those
source and target files. This documentation update changes no image bytes.

`python scripts/update_reference_figure_labels.py --check` verifies the
retained preview snapshot. `python scripts/render_current_tables.py` exports
the earlier frozen native-cell table snapshot, whose labels can differ from
the current manuscript crosswalk. Earlier screenshots and overlay coordinates
remain under `notebooks/historical_reconstructions/previews/` and `docs/archive/`.
