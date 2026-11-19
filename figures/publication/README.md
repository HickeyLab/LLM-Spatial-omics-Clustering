# Native figure exports

Native renderer IDs and filenames follow the source snapshots. [Current manuscript artwork and captions](../current_manuscript) use the saved manuscript numbering, including the three parts of Figure S5 and the reference maps in Figure S14. The [figure map](../../docs/figure_map.md) identifies the corresponding native sources.

Native Figures 5, S12 and S13 use the completed cross-donor response bank and scoring outputs. The per-figure receipts describe the available 600 dpi PNG, lossless RGB TIFF and editable PDF/SVG exports.

Typography is at least 5.5 pt at native width (6.6 pt in Figure 2). Each verification JSON records dimensions, minimum proportional placement width, source hashes and export hashes. Keep text at least 5 pt at final placement and reset image cropping.

Native Figures 2, S4 and S5 use the frozen 47-marker clustering assignments. Native Figures 3, 4, S6, S7, S10 and S11 use the frozen B004 primary annotation results. Native Figures S8 and S9 preserve the November 11 reviewer snapshot. Current manuscript Figures S10 and S2 show the [completed B004 reviewer results](../../docs/revision/reviewer47_completed_publication_20261115.md). The [native inventory](../../configs/manuscript_inventory.json) records the source captions and panel identities.

Rebuild with `python scripts/render_publication_figures.py` and verify with `python scripts/verify_publication_figures.py`. These commands make no model calls and perform no fitting. Native export checks and rendered visual review are recorded in [the verification receipt](../../docs/publication_figure_verification.json).

Cross-donor Figure S12 is bound to the [completed donor score bank](../../data/frozen/donor47_deepseek_completion_20261116/manifest.json). Its heatmaps average eight regions equally. The seed 42/43 panel uses global common-cell ARI. Rebuild it with `python scripts/render_donor47_figures.py --figures S12`. Figures 5 and S13 require terminal-source admission, which is preserved in the same bank.
