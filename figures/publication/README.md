# Submission figure files

The inventory reserves Figures 1–5 and S1–S13, comprising 20 image files because Figure S3 has separate A, B and C files. B004 artwork remains unchanged. Figures 5, S12 and S13 are bound to the terminal cross-donor response bank and final scoring outputs. Every ready image has a native 600 dpi PNG, lossless RGB TIFF and editable PDF/SVG export. Use these originals for submission; Google Docs exports compressed previews.

Typography is at least 5.5 pt at native width (6.6 pt in Figure 2). Each verification JSON records dimensions, minimum proportional placement width, source hashes and export hashes. Keep text at least 5 pt at final placement and reset image cropping.

Figures 2, S4 and S5 use the frozen 47-marker primary clustering assignments. Figures 3, 4, S6, S7, S10 and S11 use the completed one-annotation campaign and checksum-pinned [scoring outputs](../../data/frozen/annotation47_results_20261110). The [inventory](../../configs/manuscript_inventory.json) contains the matching captions and panel identities. Removed studies and original artwork remain in the checksum-linked archive.

Rebuild with `python scripts/render_publication_figures.py` and verify with `python scripts/verify_publication_figures.py`. These commands make no model calls and perform no fitting. Native export checks and rendered visual review are recorded in [the verification receipt](../../docs/publication_figure_verification.json).

Cross-donor Figure S12 is bound to the [donor score bank](../../data/frozen/donor47_results_20261114/manifest.json). Its heatmaps average eight regions equally; the seed 42/43 panel uses global common-cell ARI. Rebuild it with `python scripts/render_donor47_figures.py --figures S12`. Figures 5 and S13 require terminal-source admission, which is preserved in the final donor bank.
