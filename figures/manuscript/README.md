# Current manuscript figure artwork

The 15 manuscript figures occupy 17 PNG files because Figure S3 has separate
A, B and C images. These are byte-identical copies of the native 600 dpi
[publication exports](../publication). Editable PDF/SVG and lossless RGB TIFF
versions accompany every figure there.

Figure numbers and figure-level titles remain in manuscript captions. Panel
headings, axes, legends and scientific values are retained. Panel letters are
plain uppercase bold Arial, following the published EXO examples documented in
the [design notes](../../docs/publication_figure_design.md).

Figures 2A, 3A and 4A use the author's original BioRender illustrations, with
small imported labels retyped as editable Arial. Figure 2 gives its workflow
a full-width row.

The layout is rebuilt at a declared physical size. Every native text element
is at least 5.5 pt, with Figure 2 at least 6.6 pt. The per-image manifest records
minimum placement widths needed to keep all text at least 5 pt. Place images
proportionally and use the original files for submission. Google Docs exports
compressed previews that do not preserve the submission resolution.

```bash
python scripts/render_publication_figures.py
python scripts/verify_publication_figures.py
python scripts/sync_publication_artwork.py
python scripts/render_manuscript_figures.py --check
```

These commands use frozen numerical inputs and stored coordinates. They make
no model calls and perform no fits. Figure 3A follows the latest manuscript's
Cluster Features → Optimization workflow. Figure 3E preserves its original
reference-selected values, with its heading and caption corrected with author
approval. The numerical replot uses that same selected metric.

The earlier title-cleanup snapshots and Figure 3A restoration audits remain
historical provenance. Their former pixel-preservation claims describe those
older operations, not this native publication redesign. Current notebook
previews are exact copies of the files in this directory.
