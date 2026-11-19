# Reproduce the B004 reviewer results offline

The current publication data are independently versioned:

- `data/frozen/annotation47_results_20261111/`: the complete primary bank, 32 annotation sets, 128 logical requests and 9,024 cluster predictions.
- `data/frozen/reviewer47_results_20261111/`: all 69 planned B004 reviewer conditions, their literal scientific request bodies, query maps, selected-marker evidence, training scaler, model settings, prediction freeze, scored tables and offline comparisons.
- `data/frozen/reviewer47_response_evidence_20261111/`: literal saved visible answers for all 275 accepted reviewer requests. Internal reasoning, opaque checkpoints, credentials and private paths are omitted; source hashes and safe completion metadata remain.

The base reviewer scope contains **68 complete sets and one pending set**. DeepSeek–Leiden with selected numerical markers has a pending 75-cluster request; all 300 clusters remain planned, and the set's public agreement and macro-F1 remain null. The separate Astra–Leiden named/neighborhood Batch adds two pending sets and eight requests. Neither it nor B005/B006 supplies results to this snapshot. The private HIGH/XHIGH pilot is excluded.

From the repository root, install the existing Python 3.12 reviewer requirements, then replay to a fresh output directory:

```bash
python3.12 -m pip install -r requirements-reviewer47.txt
python3.12 -B scripts/replay_reviewer47_publication.py \
  --output outputs/reviewer47_replay_fresh \
  --recompute-calibration
```

The script verifies all three manifests, the reference-blind prediction seal, all 276 literal request hashes and message hashes, and strictly parses all 275 saved visible responses. It checks unique physical final-generation identities and normal-stop/refusal metadata before opening reference labels. It then checks the exact 220,082-cell key join, memberships, 47 markers, fixed 28-label vocabulary including Noise and existing region split; recomputes all 68 completed sets and five completed controls with independent Counter arithmetic; and verifies agreement with the frozen tables. The incomplete set stays in the output with null scores, and no aggregate silently excludes it. With `--recompute-calibration`, the deterministic cluster split and all calibration/risk CSVs must match their frozen hashes.

The output directory must not already exist. Every replay creates a new verification receipt, fresh per-set/per-region metrics and control contrasts. No H5AD, local user path, API key, network access, model call or scheduler action is needed. Omit `--recompute-calibration` for the lightweight standard-library metric replay; this still verifies the frozen calibration files through their manifest.

Focused failure and denominator checks:

```bash
python3.12 -B -m unittest discover -s tests \
  -p 'test_reviewer47_publication_replay.py' -v
```

The main benchmark and paired comparison consistently use the completed second-wave full-arm bank. Nineteen DeepSeek full-arm requests were replaced under the sealed pre-inference route reconciliation; their task/evidence messages are exact matches. Selection used request identity, route/wire criteria and strict acceptance, never reference accuracy. All 24 non-DeepSeek full-arm cell-prediction arrays are unchanged. Earlier frozen exports remain intact.

There are 109 exact reused logical items and 166 newly accepted items. Logical items are not physical generations: continuation/recovery attempts and failed validation are preserved in `physical_attempts.json` and `logical_physical_accounting.json`, with each unique known generation counted once and unknown billing retained as unknown. The Opus Batch aggregate must not be added again to its per-item token records.

All annotation conditions have one accepted generation. These B004 comparisons do not estimate repeated-call consistency or independent donor generalization. Classifier training labels provide richer supervision than the LLM evidence. Granularity measures post-clustering Ward coarsening rather than native-K fitting. Calibration is retrospective within-donor reference-agreement calibration with cluster and region separation, rather than biological confidence.
