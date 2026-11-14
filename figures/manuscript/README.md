# Retained manuscript figure artwork

These 17 PNG files contain the current artwork for 15 figure identifiers.
Figure S3 has separate A, B and C images. They are byte-identical copies of
the 600 dpi [publication exports](../publication), with editable PDF/SVG and
lossless RGB TIFF versions. Use the current
[figure map](../../docs/figure_map.md) for manuscript display labels.

Figure numbers, figure-level titles and explanatory notes remain in manuscript
captions. Descriptive subfigure titles are omitted. Distinguishing condition,
model, method, population and metric labels, axes, keys, units and scientific
values are retained. Panel letters are
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
no model calls and perform no fits. Figure 3A uses the original BioRender
artwork with current 47-marker summaries and fixed input representations.
Figure 4A uses the OpenAI logo for Astra. Comparison panels use ranked display
orders while retaining shared orders for paired views. Frozen numerical
values and scoring vocabularies are unchanged. Figure 3E shows a fixed
spatial region. Figure S11 uses the four-model most-frequent-label summary,
with ties in Astra, Opus, Argon and DeepSeek order without reference labels.
Earlier reference-selected panels and windows remain archived.

The earlier title-cleanup snapshots and Figure 3A restoration audits remain
historical provenance. Their former pixel-preservation claims describe those
older operations, not this native publication redesign. Current notebook
previews are exact copies of the files in this directory. The current
[figure inventory](../../configs/manuscript_inventory.json) defines panels and captions.
