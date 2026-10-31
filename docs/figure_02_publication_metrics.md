# Current Figure 2 metric definitions

Figure 2 E is regional cell-count-weighted F1 and G is regional cell-count-weighted cluster purity. These use region-specific reference-majority labels. F is cell-type F1 and H is cell-type recall after a global majority mapping. E–H use 209,587 non-Noise cells, 20-class harmonization and alphabetical ties. E/G and F/H intentionally use different mapping scopes.

The earlier post-hoc selected-agreement panels were superseded. Their audit and calculation records remain historical evidence under `docs/archive/` and `data/frozen/figure_02_publication_metrics/`. That selector is still relevant to Figure 3 F/G, not current Figure 2 E/G.

Run `python scripts/verify_manuscript_replay.py` to independently check current regional and cell-type values against frozen cell labels and assignments, then `python scripts/render_figure_02_manuscript.py` for numerical replots. Current [reproduction instructions](manuscript_reproduction.md) describe I/J and the fixed spatial windows. The exact current caption is frozen in `data/frozen/manuscript_replay/captions.json`. No caption or Results text is proposed or applied here.
