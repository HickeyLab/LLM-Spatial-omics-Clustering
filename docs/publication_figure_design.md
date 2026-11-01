# Publication figure design

All five main and ten supplementary figures are supplied as 17 native image
sets because S3A, S3B and S3C are separate. The manuscript and current notebook
previews use the same compositions. Whole-figure numbers and titles belong in
captions, while panel headings, axes, legends and methodological notes remain
in the artwork.

## Typography and panel letters

The nominal artwork width is 165.1 mm (6.5 inches). Arial is used throughout,
with 8 pt bold panel letters, 6.5 pt panel headings, and no text below 5.5 pt.
Figure 2 uses a 6.6 pt minimum and 10.3 pt panel letters at native size to
allow its taller composition and narrower manuscript placement. At the
recommended placement, its panel letters are approximately 8 pt.
PDF fonts are embedded TrueType and SVG labels remain editable text. An
installed Arial is needed to reproduce the committed font appearance.

The [EXO author instructions](https://sciexplor.com/exo/author_instructions)
describe distinct labels as “(A), (B), (C)”. Actual Figure 2 artwork in both
[Kandinsky](https://sciexplor.com/exo/articles/EXO.2025.0017) and
[STAMP](https://sciexplor.com/exo/articles/EXO.2026.0012), visually inspected on
31 October 2026, uses plain uppercase letters without parentheses. Their
captions use parenthesized panel references. This artwork follows those
published examples with bold A, B, C and retains (A), (B), (C) in captions.
Figure 5 and S10 now have A–D, and S8 has A–B. Single-panel S7 is unlettered.

The [Nature research figure guide](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)
and the supplied [Hickey et al. Nature example](https://www.nature.com/articles/s41586-023-05915-x)
inform the restrained sans-serif typography, aligned layouts and editable
labels. Nature's lowercase-letter convention is not substituted for EXO's
published uppercase examples.

## Resolution and placement

Every PNG is rendered from the final native composition at 600 dpi. TIFF is a
lossless RGB conversion of those exact pixels with 600 dpi metadata and LZW
compression. Every figure also has PDF and SVG exports. Graph lines, diagrams,
heatmap cells and text are vectors. Dense point layers and color gradients
are drawn natively at approximately 610 dpi in the vector containers. Figures 2A, 3A and 4A reuse the author's native BioRender PDF export, preserving
its original vectors and microscopy/logo pixels. Small imported text tables
and lists are replaced by editable Arial. Generic template phase captions
and the unused color-key label are removed. There is no artificial
upsampling or refitting.

These exports meet EXO's minimum 300 dpi requirement and its 600 dpi or
editable-vector requirement for graphs and diagrams. The small microscopy images in the restored BioRender workflows retain
their original pixels at an effective resolution above 600 dpi.

Use proportional resizing with the aspect ratio locked. Spatial plots and
UMAP coordinates use equal x/y units, and square matrices have square cells.
No coordinates are independently stretched to fill a panel. Existing image
orientations and fixed zoom windows are retained.

The manuscript placement widths are 128.27 mm for Figure 2, 152.4 mm for
Figure 3, S1 and S4, and 165.1 mm for the remaining images. At these widths the
smallest placed font is above 5 pt. Exact minimum placement widths and native
dimensions are recorded in each `Figure_*_verification.json`. Do not reduce
the width below that recorded minimum without rebuilding with larger text.

In the checked manuscript export, Google Docs reduced each image’s longest
edge to 2,048 pixels. Its exported images are manuscript previews, and several fall below
300 dpi at page size. Submit the original 600 dpi TIFF/PNG or editable
PDF/SVG files in `figures/publication`, rather than extracting figures from
the Google Doc. The final document geometry was checked against all 17
native compositions, with aspect-ratio rounding below 0.2% and a minimum
placed font above 5 pt.

## Frozen evidence and scientific scope

The renderer uses compact checksum-pinned tables in
`data/frozen/publication_design`. The release source paths and hashes are
recorded in `source_manifest.json`. Preparation verification records the
original H5AD and archived coordinate identities. No clustering, UMAP fit,
model inference, new matching or new statistical experiment is performed.

Figure 3A follows the latest live-manuscript workflow, including Cluster
Features and the five marker-selection settings under Optimization. All
three main workflow panels now use the original BioRender illustrations.
Figure 2 is reflowed to give its workflow the full figure width; the other
numerical panels retain their frozen data and definitions. Its
caption preserves the distinction between retrospective marker-name-list
settings and the numerical benchmark prompt inputs.

Figure 3E keeps the original archived values. Its metric is the fraction of
cells for which the Phase 7 prediction or the individual Leiden–LLM prediction
matches the reference label. It is a full-data, post-hoc reference-selected
union and does not estimate performance on unlabeled data. The author
approved correcting the old upper-bound-normalization heading and caption.
The numerical E replot now reads the same selected values as the artwork.
All 80 archived cell-type/model rows are independently checked against the
frozen cell-level predictions.

Figure 1B and S1 retain the four-decimal precision saved in the executed
historical notebook. Full-precision original metrics were not recovered.
This precision limit does not affect the frozen descriptive Figure 1D–F
tables. The original UMAP coordinates, spatial cells and selected windows
are reused, and existing selection and single-donor limits remain in captions.

## Reproduction and checks

```bash
python -m pip install -r requirements-publication-figures.txt
python scripts/render_publication_figures.py
python scripts/verify_publication_figures.py --render-qa outputs/publication_design/pdf_qa
python scripts/sync_publication_artwork.py
python scripts/render_manuscript_figures.py --check
python scripts/update_reference_figure_labels.py --check
python scripts/verify_manuscript_replay.py
```

The optional `--docx` argument to `verify_publication_figures.py` checks
exported manuscript image identity, cropping, aspect ratios and placed text
size. It records the compressed preview resolution separately from the
submission files. Native verification checks all frozen-input and export
hashes, PDF typography, panel letters, editable SVG text, effective PDF
image resolution, raster dimensions and pixel-identical PNG/TIFF data.
Every PDF page was also rendered and inspected for spacing and clipping.

The earlier title-removal and Figure 3A restoration audits remain historical.
They are not assertions that this redesigned artwork preserves old pixels.

## BioRender source and attribution

The original authoring export and its checksum are recorded in
`data/frozen/biorender_workflows` and `configs/biorender_workflows.json`.
The original online canvas is unchanged. The repository renderer makes the
print-size typography changes reproducibly. Captions 2–4 credit BioRender.
The open-access publication-license form was left unsubmitted at the
author's request; no CC-BY license or public BioRender citation URL is
asserted here. BioRender content remains subject to its own permissions.
