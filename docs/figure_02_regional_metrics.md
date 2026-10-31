# Figure 2 E/G regional metrics

E is reference-cell-count-weighted F1 after region-specific majority assignment. G is cell-count-weighted cluster purity, equal to the fraction matching that regional majority assignment. Eight regions of B004 are evaluated separately on the same 209,587 non-Noise cells, with 20-class harmonization and alphabetical ties.

Frozen values, classwise checks, mappings and a source calculation receipt are under `data/frozen/manuscript_replay/figure_02/`. `scripts/verify_manuscript_replay.py` recomputes the metrics from frozen cell labels and cluster assignments. Use `scripts/render_figure_02_manuscript.py` for current numerical panels. E/G are fractions on a common 0–1 scale. The eight regions are subsamples from one donor, not independent donors.
