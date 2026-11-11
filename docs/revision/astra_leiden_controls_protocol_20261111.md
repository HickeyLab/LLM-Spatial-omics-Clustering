# B004 Astra–Leiden control extension

**Version:** `b004-astra-leiden-controls-20261111-v1`. **Status: planned—not executed.** The [configuration](../../configs/astra_leiden_controls_1repeat_v1.json) disables inference and automatic launch. This preparation makes zero paid calls and contains no submission client or launch hook.

The B004 benchmark motivated choosing Astra–Leiden for the detailed illustration after observing its results. This extension supplies matched controls for that illustration. It does not change the completed all-model benchmark, the original protocol's Opus illustration specification, or the existing Opus control evidence. A presentation amendment records the figure-selection decision separately. It makes no repeatability or general model-superiority claim.

## Scope and reuse

Use the same 220,082 B004 cells, frozen 300 occupied Leiden memberships, 47-marker order, fixed 28-label vocabulary including Noise, four training regions, two validation regions and two test regions as the completed study. Preserve the original four groups of 75 clusters, anonymous query maps and integer-thousandths encoding. Do not change B005/B006 or any active runner.

Prepare exactly **two new annotation sets, eight Batch items and 600 planned cluster predictions**, with one generation per new condition:

| Condition | New items | Added model-visible evidence |
| --- | ---: | --- |
| Named method | 4 | Only `clustering_method: Leiden` |
| Measured neighborhood | 4 | Previously prepared numerical neighborhood means and their definition |

Reuse the four accepted blinded Astra–Leiden means-plus-fractions items as the comparator for both controls. The bundle records each baseline's accepted response hash, request hash, cluster order and labels separately from model inputs. These baseline items are not present in the submission JSONL. Preserve all completed Opus controls; this is an additional focused comparison rather than a replacement or rerun.

## Evidence and settings

The baseline consists of identical cluster means of `arcsinh(processed X/5)`, standardized with the frozen four-training-region center and SD, plus fractions of processed values strictly above zero computed before transformation or standardization. Values remain encoded as integer thousandths. Label definitions, task instructions, marker order, cluster order and batch boundaries stay fixed. Reference labels, cell identifiers and unrequested method identity are excluded from submitted bodies.

The neighborhood arm reuses the exact numerical evidence of the prepared Opus–Leiden control: for each cell, average measured transformed expression over up to 15 nearest other cells within its region; resolve distance ties by numeric cell ID; average these vectors within the target cluster and apply the frozen B004 training scaler. Self is excluded even for coincident coordinates. No neighboring labels are supplied. The two arms retain the same baseline means and fractions.

Use native OpenAI Batch, `/v1/chat/completions`, the admitted published model alias `gpt-6-astra`, `reasoning_effort=high`, `seed=42`, `max_completion_tokens=32768`, JSON-object response format and a 24-hour Batch window. Omit tools, optional sampling parameters and fallback. The 32,768 ceiling includes reasoning and visible output; it is finite and does not guarantee that every generation fits. Native seed support is best effort and does not establish deterministic replay. The published alias matches the admitted catalog identity; immutable weight identity is not independently attested.

## Cost and launch gates

The [exact request bundle](../../data/frozen/astra_leiden_controls_prepared_20261111/manifest.json) and [reservation](../../data/frozen/astra_leiden_controls_prepared_20261111/cost_reservation.json) reserve the full combined output ceiling for every item, plus an input-token upper bound of each entire native body's UTF-8 byte count plus 4,096. The admitted Stage 1 price snapshot is $5/M Batch input and $25/M Batch output; use $6.25/M input for the conservative default cache-write reservation. This yields an **$8.71 rounded-up reservation** from existing OpenAI API credits. This is a ceiling calculation under the recorded rates, not an observed charge or a claim that current credit access has been rechecked.

Before any paid submission, refresh model/parameter, pricing and funded-project balance checks, independently verify the bundle and response parser, and obtain both a separate spending ceiling and a separate user launch instruction. The previous Stage 1 approval is not transferred to this extension. The prepared configuration has no approved spending cap. No credits are purchased.

Persist the submission receipt before polling. Match results by unique custom IDs, not returned order. Reconcile ambiguous submission state before any resubmission. Invalid generations remain missing: no regeneration, continuation, automatic retry after generation or automatic budget increase is included.

## Acceptance and analysis

Require exactly one object per anonymous ID in `{"a":[{"i":0,"l":0}, ...]}`, integer IDs 0–74 and integer original label codes 0–27. Reject duplicate JSON keys, duplicate/missing/extra IDs, extra fields, wrong types, refusals and truncated outputs. Noise code 21 is valid. Missing predictions stay errors in the planned denominator and are reported separately from Noise.

Report equal-weighted reference agreement across the two fixed B004 test regions, each region separately, fixed-28-label macro-F1, cell/cluster coverage, paired label changes and observed token/cost usage. The named and neighborhood comparisons reuse one existing baseline and do not count its physical generation or cost again. These are single-generation descriptive controls; do not report repeat SD, within-model majority voting, repeatability or calibrated confidence from them.

## Offline checks

The self-contained [offline preparer/checker](../../scripts/revision/prepare_astra_leiden_controls.py) has no network or credential path. Its frozen input snapshots allow independent checks without the unmerged reviewer-tooling branch:

```sh
python3 scripts/revision/prepare_astra_leiden_controls.py check \
  --bundle data/frozen/astra_leiden_controls_prepared_20261111
python3 -m unittest discover -s tests -p test_astra_leiden_controls.py -v
```

The checks reject missing/reordered markers, invalid numerical shape/types, mismatched paired evidence, reference/method metadata leakage, duplicate request IDs, incorrect baseline/cluster joins, incomplete eight-item coverage, under-reservation and accidental activation. Mutation tests also verify strict output acceptance. The sealed manifest hashes every literal body, source snapshot, join, protocol and price record. Fresh live funding and launch approval remain separate gates.
