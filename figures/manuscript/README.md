# Manuscript figure artwork

This is the complete current manuscript artwork set, using the reconciled
Figure 1–5 and S1–S10 numbering. S3 is supplied as three separate panel files,
so the 15 figures occupy 17 PNG files. Sources were checked against the current
manuscript export on 2026-10-31, including its newer Figure 4, S3C, S6 and S7
artwork. This directory uses manuscript numbering. The older analytical
notebooks retain their existing identifiers.

Figure numbers and figure-level titles belong in the separate manuscript
captions. They are removed from 10 images here. Panel headings, panel letters,
axis labels, legends, methodological notes and scientific values remain.
Image dimensions are unchanged. Every pixel outside the declared title
rectangles matches the corresponding source snapshot exactly. The seven
images that already followed this convention are unchanged.

`manifest.json` records all source and output checksums, dimensions and title
rectangles. The affected original snapshots are retained under
`data/frozen/publication_artwork/title_cleanup/` for reproducibility.

Reproduce or verify the image exports using the existing Matplotlib, NumPy
and Pillow environment:

```bash
python scripts/render_manuscript_figures.py
python scripts/render_manuscript_figures.py --check
```

The script does no analysis, clustering, scoring, fitting or model inference.
Validation is recorded in `docs/figure_title_cleanup_verification.json`.

The three affected historical notebook previews (S4, S7 and S8) are also
caption-free. These notebook labels differ from the reconciled manuscript
numbering. S7's PNG renderer retains a checksum-pinned publication raster so
font or Matplotlib-version differences cannot redraw its panels during this
formatting change. Its analytical builder still supports reconstruction from
the same 32 frozen condition results and omits the figure-level title.

Figure 3A additionally restores the manuscript's original Cluster Features ->
Optimization artwork. The source snapshot and checksums were updated, while
the title-removal layer and every pixel outside the input-workflow region were
preserved. See [the restoration audit](../../docs/figure_03a_original_restoration_verification.json).
