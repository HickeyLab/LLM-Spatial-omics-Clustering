# Completed B004 reviewer output deposition

The current completed scope contains 71 B004 annotation sets, 284 accepted logical items and 20,076 cluster predictions. Its primary 32 sets and 9,024 predictions are unchanged.

The original reviewer bank remains immutable under `data/frozen/reviewer47_results_20261111`. The append-only `reviewer47_deepseek_completion_20261115` bundle admits one previously pending 75-cluster item, completing all 69 base sets, 276 items and 19,476 predictions. It preserves the prior 275 accepted items. DeepSeek–Leiden selected numerical means reached 41.4217% reference agreement and 0.357583 fixed-28-label macro-F1.

The append-only `astra_prompt_controls_results_20261115` bundle adds two completed Leiden conditions, eight requests and 600 predictions. The blinded baseline, method-name control and neighborhood control reached 58.1200%, 53.5251% and 51.4345% agreement, respectively. The controls used native OpenAI Batch while the reused baseline used OpenRouter Batch. These single-generation comparisons do not isolate prompt content from provider route or establish repeatability.

Both completion manifests cover literal requests or their original immutable request reference, visible terminal answers, accepted labels, settings, metrics and verification. Public files contain no credentials, private filesystem paths or hidden reasoning text. Provider identities, timestamps, opaque generation IDs and token-use counts are retained for provenance. Older pending metadata remains historical and is not overwritten.

```bash
python3.12 -B scripts/replay_completed_reviewer47.py --output outputs/reviewer47_completed_replay
```

The output directory must be new. The replay validates manifests and literal responses before its independent score arithmetic, verifies the original snapshot, confirms exactly one base item was newly admitted, and checks all completed base and Astra conditions. It performs zero model calls, zero scheduler actions and zero fits. Cross-donor missing outputs remain separate and unchanged. Notebook display labels follow `configs/manuscript_display_crosswalk.json`, with stable source IDs and image filenames.
