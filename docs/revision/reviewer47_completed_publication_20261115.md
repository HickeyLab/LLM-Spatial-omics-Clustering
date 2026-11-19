# Completed B004 reviewer output deposition

The current B004 release contains **71 completed annotation sets, 284 accepted logical items and 20,076 cluster predictions**. Its 32 primary sets contain 9,024 predictions. The [release record](../../configs/reviewer47_completed_publication_20261115.json) links the frozen inputs and execution provenance.

The [November 11 reviewer bank](../../data/frozen/reviewer47_results_20261111/manifest.json) is the immutable original snapshot. The [DeepSeek completion bundle](../../data/frozen/reviewer47_deepseek_completion_20261115/manifest.json) admits one previously pending 75-cluster item, completing all 69 base sets, 276 items and 19,476 predictions. It preserves the prior 275 accepted items. DeepSeek–Leiden selected numerical means reached 41.4217% reference agreement and 0.357583 fixed-28-label macro-F1 (Table S8d).

The [Astra extension](../../data/frozen/astra_prompt_controls_results_20261115/manifest.json) adds two completed Leiden conditions, eight requests and 600 predictions. The blinded baseline, method-name control and neighborhood control reached 58.1200%, 53.5251% and 51.4345% agreement, respectively (Table S9). The single-generation comparisons used native OpenAI Batch for the controls and reused the OpenRouter Batch baseline, so their contrasts also differ in execution route. The extension includes [metrics for all 71 sets](../../data/frozen/astra_prompt_controls_results_20261115/set_metrics.csv) and [all seven prompt-control contrasts](../../data/frozen/astra_prompt_controls_results_20261115/control_contrasts.csv).

Both completion manifests cover literal requests or their original immutable request reference, visible terminal answers, accepted labels, settings, metrics and verification. Public files contain no credentials, private filesystem paths or hidden reasoning text. Provider identities, timestamps, opaque generation IDs and token-use counts are retained for provenance. Older pending metadata remains historical and is not overwritten.

```bash
python3.12 -B scripts/replay_completed_reviewer47.py --output outputs/reviewer47_completed_replay
```

Run the command with Python 3.12 from the repository root and choose a new output directory. The replay validates manifests and literal responses before independently scoring the completed base sets and Astra controls. It confirms that one base item was newly admitted and that all 275 previously accepted items were preserved. It writes `verification.json` for the completed scope and `original_snapshot/` for the November 11 replay. It makes zero model calls and performs zero scheduler actions and fits. The [figure crosswalk](../../configs/manuscript_display_crosswalk.json) maps manuscript numbers to reproducible source assets. The [B005/B006 replay](../manuscript_reproduction.md#completed-cross-donor-scoring) is a separate scoring entry point.
