# Figure 2 on the native reference labels

Figure 2B includes all 220,082 B004 cells and displays the 10,495 cells labeled Noise. Panels E–H use the frozen primary cluster memberships and all 28 native labels. E and G use within-region cluster majorities. F and H use one global mapping per method. Ties are resolved alphabetically.

Table S7 uses the same regional scores as E and G. It contains all 12 paired comparisons, with 256 exact sign flips per comparison and Holm adjustment across the family. The 96 paired observations are included.

To reconstruct the current figure and tables from a checkout with the pinned base commit:

```sh
python scripts/score_render_figure2_native28.py --output outputs/figure_02_native28
```

For a shallow checkout, fetch the previous artwork from the pinned base commit named in [the scoring receipt](scoring_manifest.json) and pass it as `--base-figure`. The replay checks the base artwork hash, preserves panels A, C and D, and checks the regional scores against the frozen reference calculation. It uses the existing cluster memberships and makes no model calls.

The [input contract](manifest.json) pins the scored tables, replay script and manuscript artwork. The [earlier 20-label scoring files](../clustering47_primary_20261108) preserve the previous evaluation.
