# Manuscript figure artwork

This is the complete current manuscript artwork set, using the reconciled
Figure 1–5 and S1–S10 numbering. S3 is supplied as three separate panel files,
so the 15 figures occupy 17 PNG files. Sources were checked against the current
manuscript export on 2026-10-31, including its newer Figure 4, S3C, S6 and S7
artwork. This directory and the current notebook index use manuscript numbering.
Earlier analytical notebook versions are preserved in
`notebooks/historical_reconstructions/`.

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

Current notebook previews are byte-identical copies of all 17 images here.
Earlier preview overlays and numbering are preserved as historical records.
See [the current preview policy](../../notebooks/final_figures/previews/README.md).

Figure 3A additionally restores the manuscript's original Cluster Features ->
Optimization artwork. The source snapshot and checksums were updated, while
the title-removal layer and every pixel outside the input-workflow region were
preserved. See [the restoration audit](../../docs/figure_03a_original_restoration_verification.json).
