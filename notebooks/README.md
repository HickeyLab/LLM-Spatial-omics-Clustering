# Notebooks

`final_figures/` is the single canonical notebook collection for the current
publication packet. It contains Figures 1--4, Supplementary Figures S1--S4,
Tables S1--S2, and Supplementary Note 1.

Figure 1, Supplementary Figures S1--S2, Tables S1--S2, and Supplementary Note 1
contain executed outputs. Figures 2--3 and Supplementary Figures S3--S4 show
hash-verified publication previews near the top and keep the full
reconstruction code below them. Figure 4 uses the frozen historical Claude map
through `final_figures/figure_04_leiden_claude_end_to_end.ipynb`. Its old
GPT-named entry point forwards to that notebook. The replay performs no new
inference or fitting and records verification in
`docs/figure_04_historical_claude_execution.json`.

`supplementary/` contains an independently executable panel runner for
Supplementary Figure S3. It uses the same S3 numbering as the current
manuscript and supports panel-level regeneration; it is not an alternative
reviewer-facing figure entry point.

Generated figures, manifests, raw model responses, and newly executed notebook
copies belong under `outputs/` and remain untracked.
