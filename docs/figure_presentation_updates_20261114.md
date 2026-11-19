# Manuscript figure presentation updates, 2026-11-14

Figure 3A retains the original six-stage BioRender workflow artwork, including the original JSON marker-list and five-setting threshold images in its third and fourth steps. Their pixels and transparency masks are preserved. The headings identify these as a marker-list example and selection settings. These panels are schematic. The primary benchmark uses fixed all-marker profiles, and selected-marker controls follow Section 2.11. Figure 4A identifies Astra with the exact OpenAI logo PNG supplied by the author. The supplied source, placement description and checksums are recorded in `data/frozen/provider_logos/manifest.json`.

Comparison panels rank their existing displayed summaries. Figure 3D ranks cell types by decreasing mean recall across the four models. Figure 4B and C share cell-type order by decreasing pooled-test F1 on both confusion-matrix axes and the bar rows. Directly paired panels share the same order, and exact ties retain their prior category order. The complete panel-by-panel rules and values are recorded in `figure_ordering_audit_20261114.json`.

Fifteen figure images were regenerated for presentation: 1, 2, 3, 4, S1, S3A, S3B, S3C, S4, S5, S6, S7, S8, S9 and S10. S8 and S9A share the complete primary benchmark method order, while control sequences and coverage curves retain their scientific ordering. Native PDF and SVG, 600-dpi PNG and TIFF, manuscript copies and notebook preview copies are synchronized. The updated Figure S10 panel mapping is Opus (A), Astra (B), Argon (C), DeepSeek (D).

Independent before/after artist comparisons confirmed that plotted metric values are unchanged. Frozen scientific inputs remain unchanged. Native typography, bounds, image resolution, PNG/TIFF pixel identity, source checksums and panel lettering passed verification for all fifteen regenerated figures. Results are recorded in `figure_updates_native_verification_20261114.json`.

The scientific source is the exact November 11 frozen result bank in PR #38 at commit `5e4f11c91b24d14b6376b35892516562d0c8e475`, which matches the manuscript baseline. Every imported frozen-result file was checked byte-for-byte against that commit. No model calls, fitting, scoring changes or newly completed conditions are part of this presentation update.

The author-supplied 534 × 474 pixel OpenAI PNG is embedded with unchanged pixels in the native Figure 4 PDF. Its decoded RGB pixels match the supplied image exactly, with matching horizontal and vertical effective resolution of approximately 848 dpi.

Figure 3A places the table on the original flow line and preserves the original marker-list and threshold-setting artwork. Its original short headed connectors are approximately 2.89, 2.75 and 2.89 mm long. Panels B–E and full-figure dimensions are unchanged. Figure 2A keeps the native arrow and the table right edge fixed, with 1.83 mm clearance between the incoming arrow tip and table. Panels B–H are unchanged.
