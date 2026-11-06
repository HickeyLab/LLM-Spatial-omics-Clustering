# Figure S11 marker profiles and archived spatial examples

Current Figure S11A retains the former Figure 2I marker profiles for CD8+ T
groups assigned by each cluster's most frequent prediction across four LLMs.
The tie order is GPT, Claude, Gemini and DeepSeek, without reference labels.
Reference-Noise cells are included. Dot size encodes the fraction of stored
processed values strictly above zero, and color shows group means scaled
per marker across methods. These numerical fractions are not validated
biological positivity, and the profiles do not independently validate labels.

Verified sources are [marker summaries](../data/frozen/manuscript_replay/figure_02/panel_I_marker_summaries.csv)
and [group counts](../data/frozen/manuscript_replay/figure_02/panel_I_selected_groups.csv).
The original filenames remain unchanged.

The former Figure 2J and S11B selected spatial windows are archived. Their
1,086-cell and 915-cell examples used reference agreement, composition and
density for selection and do not provide independent validation. Their
membership, coordinates and calculation receipt remain under
`data/frozen/manuscript_replay/figure_02/`.

`scripts/render_figure_02_ij_verified.py` retains the earlier I/J layout for
historical numerical verification. It does not regenerate the current
Figure 2 A–H or a standalone public S11 image. The current
[figure map](figure_map.md) identifies manuscript display labels.
