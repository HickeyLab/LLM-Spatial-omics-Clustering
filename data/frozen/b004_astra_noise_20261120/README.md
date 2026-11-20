# Figure S15 score bank

This bank contains four accepted B004 Leiden annotation maps from GPT-6.2 Astra at maximum reasoning, submitted through OpenAI Batch. Each call annotated the same 300 clusters from 47-marker summaries. One call was designated for each combination of Noise eligibility and reference scoring policy.

- [Cluster predictions](cluster_predictions.csv) contains 1,200 cluster labels keyed by local call ID and cluster ID.
- [Designated scores](metrics.csv) contains the four scores per evaluation scope. Agreement and macro-F1 weight the transverse colon and mid-jejunum equally in the primary test scope.
- [Paired differences](paired_contrasts.csv) compares the same two call pairs under both reference scoring policies. Noise predictions on cells with biological reference labels count as errors.
- [Manifest](manifest.json) records the model settings, independent verification counts and input checksums. The reference labels and cluster assignments are pinned to the [existing B004 bank](../annotation47_results_20261111/manifest.json).

Render the figure from the repository root with the [offline renderer](../../../scripts/render_figure_s15.py) and the publication figure dependencies.

```bash
python3.12 scripts/render_figure_s15.py --output outputs/figure_s15/Figure_S15.png
```
