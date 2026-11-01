# Figure artwork and caption cleanup

The November 1, 2026 update removes explanatory footnotes and redundant text
from all five main and ten supplementary figures. The 17 image files retain
their data, units, scales, coordinates, panel letters, keys and physical
dimensions. Headings identify the panel briefly. The supplied
[Hickey et al. figure reference](https://www.nature.com/articles/s41586-023-05915-x/figures/1)
informs this separation of artwork and caption text.

Figure 5C–D no longer repeats “Equal donor weights, with labeled reference
profiles.” Its caption already states the weighting and reference-assisted
condition. The caption now also preserves the 23-class macro-F1 definition
and the FlowSOM implementation pointer, allowing the superscript footnote
symbols to be removed from the artwork.

| Figure | Caption coverage for removed text |
| --- | --- |
| 1 | Existing caption defines after-minus-before changes and within-donor regions. |
| 2 | Existing caption defines regional and cell-type metrics, processed marker summaries, modal labels and post-hoc spatial examples. |
| 3 | Existing caption defines upper-bound normalization, reference-informed selection, cell/cluster weighting and most-frequent labels. |
| 4 | Existing caption defines the majority-label bound and includes minority-label matches and the causal-interpretation limit. |
| 5 | Existing donor-weighting explanation retained; 23-class macro-F1 and FlowSOM implementation pointer added. |
| S1 | Existing paired-region definition retained; archived-notebook provenance added. |
| S2 | Existing caption supplies B004-A-004 and the displayed cell types. |
| S3 | One-to-one mutual matching, unvalidated upstream geometry, fixed fitted label mappings, shared symmetric color scale and separate regional variation reporting preserved in the caption. |
| S4 | Existing caption supplies the ARI/AMI unit, eight regions, metric definitions, marker scaling and reference colors. |
| S5 | Existing 28-label, Noise and retained-cell explanations kept; single-donor scope, seed 42 and method-specific preprocessing added. |
| S6 | Existing caption defines maximum agreement and the cluster-level comparison. |
| S7 | Existing bound, denominator and minority-match explanations kept; explicit vocabulary-mismatch wording and archived Claude Opus 5 identity added. |
| S8 | Existing caption defines both input conditions, the regional mean and missing-prediction treatment. |
| S9 | Existing caption supplies the 32 conditions and the GPT/Leiden, marker-only and neighborhood-input details. |
| S10 | Existing caption supplies full model names, three repeats, two regions, run SD, 28 labels and missing-prediction treatment. |

The live manuscript changes are 17 image replacement suggestions and nine
caption replacement suggestions. They remain pending author review. The
proposed caption text is mirrored in `configs/manuscript_inventory.json`.
Existing manuscript content outside these scoped edits is preserved.

Google Docs exports retain the original image pixels while image replacement
suggestions are pending. Caption suggestions appear in the DOCX export. Use
`--image-suggestions-pending` with `verify_publication_figures.py --docx` to
check placement without treating those original previews as proof of the new
artwork. The proposed files were checked natively and uploaded through the
live editor's Replace image control in Suggesting mode. A live Figure 5 view
was also checked, including the removed C–D subtitles. No live suggestions
were accepted. The final caption snapshot preserves concurrent author edits.

The canonical regeneration path is `scripts/render_publication_figures.py`,
followed by `scripts/sync_publication_artwork.py`. The latter updates native
PNG copies, notebook previews and their checksums together. The publication
PDF/SVG and 600 dpi PNG/TIFF exports are regenerated from frozen inputs.
Earlier source snapshots and audit receipts remain historical provenance.
No model calls, clustering, matching, fitting or rescoring were performed.
