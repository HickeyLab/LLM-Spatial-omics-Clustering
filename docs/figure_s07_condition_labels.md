# Figure S7 conditions, denominator and color scale

The two displayed conditions are **Marker-only** and **Reference-assisted**.
The latter is described as **With labeled reference profiles**. These are the
B004 training-region-by-cell-type mean expression profiles defined in Section
2.15. The reference-assisted condition adds five nearby labeled profiles to
the same query profiles used by Marker-only. Internal `retrieval`, `prototype`
and legacy delivery field names remain for compatibility.

The colorbar is **Reference agreement (%)**. The actual score function includes
unknown/missing predictions as errors: its denominator is `n = len(y)` for all
eligible planned reference cells in each region, and agreement is `correct/n`.
The distinct `conditional_delivered_agreement = correct/covered` is not used
in this figure. S7 displays an unweighted mean across the two B004 test regions,
not a score conditional on successful prediction delivery.

Both condition panels share **RdYlGn** with fixed **0–100%** limits, matching
Figure 2H's performance-heatmap palette and scale. Higher values use the green
end and lower values the red end. Numerical text uses black or white solely
for contrast. There is no panel-specific autoscaling.

All 32 full-precision values were copied from the frozen source table and
verified against the original artwork's one-decimal numbers. The source score
and existing results are unchanged. The original PNG is retained in
`data/frozen/publication_artwork/figure_s07_original.png`; values are in
`data/frozen/figure_s07/condition_agreement.csv`, protected by checksum.

```bash
python scripts/render_figure_s07.py
python scripts/render_figure_s07.py --check
python scripts/render_figure_s07.py --pdf /tmp/Figure_S7.pdf
```

This renderer only reads the frozen table. It does not call models, fit
classifiers, select parameters or rescore predictions. The original builder's
human-facing labels and palette are aligned, while original saved results and
protocol keys are preserved. See `figure_s07_source_audit.json` for source hashes
and a denominator check using an invalid prediction.

## Matching manuscript caption

Figure S7. Controlled direct LLM annotation in the B004 test regions. Marker-only uses marker-expression profiles without labeled reference profiles. Reference-assisted uses the same query profiles together with five nearby labeled reference profiles constructed from the four B004 training regions (Section 2.15). Columns show GPT-5.6-Sol, Claude Opus 5, Gemini 3.1 Pro Preview and DeepSeek V4 Pro. Values are mean reference agreement (%) across the two B004 test regions. Both panels share the same RdYlGn color scale from 0 to 100%. Missing or invalid predictions remain errors in each region’s full planned denominator. Prediction coverage is reported separately.
