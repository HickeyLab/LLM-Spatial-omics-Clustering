# Current manuscript previews

These 17 PNGs are byte-identical copies of the approved Figure 1–5 and S1–S10 artwork in `figures/manuscript/`. Figure S3 has three image parts. The publication design pass updates all 17 images. Figure 3A follows the latest manuscript workflow, and Figure 3E preserves its reference-selected values with the corrected metric heading. The [native exports](../../../figures/publication) include editable vectors and 600 dpi raster originals.

```bash
python scripts/update_reference_figure_labels.py --check
```

The [manifest](../../../docs/reference_figure_label_changes.json) pins each source and target. Its current entries have no overlays. Previous screenshots, old table-number previews and their overlay coordinates are retained under `notebooks/historical_reconstructions/previews/` and `docs/archive/` for provenance. They do not define the current manuscript.

Current Table S1–S8 notebooks display native manuscript cells and complete frozen companion data with current headings. Use `python scripts/render_current_tables.py` to export HTML previews. Tables S2A and S3 also have editable table renderers documented in the [table crosswalk](../../../docs/supplementary_table_numbering.md).
