# Figure S5 and S7 heatmap color scales

Figure S5C now uses **RdYlGn**, the same palette family as Figure 2H and the
updated S7. Both S5C panels share one normalization with symmetric limits of
approximately **−63.887 to +63.887 percentage points**, retaining the original
source-derived range. Zero is centered on yellow, decreases in F1 extend
toward red, and increases extend toward green. Numerical text uses black or
white for contrast. Colors encode effect magnitude and direction.

S7 displays agreement, so its two condition panels share **0–100%** rather than
a zero-centered change scale. The palette family is the same and the numerical
normalization follows each metric. See [the S7 notes](figure_s07_condition_labels.md).

S5A matching conditions and S5B clustering backends use categorical series
colors and are preserved. All 336 S5C values, 28 cell types, six methods,
two backends, original rounding and original image footprint are retained.
The frozen CSV retains source precision and contributing regional counts.
No inferential threshold controls the display.

```bash
python scripts/render_figure_s05.py
python scripts/render_figure_s05.py --check
python scripts/render_figure_s05.py --pdf /tmp/Figure_S5C.pdf
```

The source audit identifies the original table, filters, checksums and original
color-matrix check. The original local segmentation renderer has also been
updated to RdYlGn with luminance-based text contrast. Its small patch is
recorded in `figure_s05_upstream_palette.patch` because that revision package
is outside this repository's baseline. The standalone renderer is portable
and reads only the committed frozen effects. The archived executed-engine
snapshot and analytical results remain unchanged.

## Matching caption addition

Heatmap values summarize mean regional changes for each cell type and
segmentation method. Both heatmaps share a symmetric red–yellow–green scale
centered on zero, with red indicating decreases and green increases in F1
after compensation.

All existing qualifications about within-donor regions and descriptive
resampling intervals are retained. The native image and caption replacement
are prepared and await manual Mac unlock.
