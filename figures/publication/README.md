# Submission figure files

The 13 retained figures comprise 15 image files: Figures 1–4, S1–S7, S10 and S11. Figure S3 has separate A, B and C files. Every current image has a native 600 dpi PNG, lossless RGB TIFF and editable PDF/SVG export. Use these originals for submission; Google Docs exports compressed previews.

Typography is at least 5.5 pt at native width (6.6 pt in Figure 2). Each verification JSON records dimensions, minimum proportional placement width, source hashes and export hashes. Keep text at least 5 pt at final placement and reset image cropping.

Figures 2, S4 and S5 use the frozen 47-marker primary clustering assignments. Figures 3, 4, S6, S7, S10 and S11 use the completed one-annotation campaign and checksum-pinned [scoring outputs](../../data/frozen/annotation47_results_20261110). The [inventory](../../configs/manuscript_inventory.json) contains the matching captions and panel identities. Removed studies and original artwork remain in the checksum-linked archive.

Rebuild with `python scripts/render_publication_figures.py` and verify with `python scripts/verify_publication_figures.py`. These commands make no model calls and perform no fitting. Native export checks and rendered visual review are recorded in [the verification receipt](../../docs/publication_figure_verification.json).
