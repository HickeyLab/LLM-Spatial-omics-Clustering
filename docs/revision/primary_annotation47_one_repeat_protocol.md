# One-annotation 47-marker protocol: experiments 7 and 14

**Status: planned and not executed. Execution is disabled. No annotation calls or jobs have been submitted for this preparation. Figure replacements remain paused.**

The active preparation is [primary_annotation47_1repeat_opus55_v1.json](../../configs/primary_annotation47_1repeat_opus55_v1.json). The [active-study record](../../configs/annotation47_active_study.json) selects this preparation and records the checksum-linked archive for experiment 9. This selection supersedes the three-repeat planning choice only. The three-repeat and five-repeat preparations, their evidence, and the unapplied manuscript ledgers remain intact.

## Scientific question and scope

Use the same 220,082 B004 cells and four frozen clustering partitions to test whether adding fractions of processed marker values above zero to all 47 marker means changes LLM annotation agreement. Experiment 7 uses the means-plus-fractions arm as the full-marker benchmark. Experiment 14 compares that arm with means alone. Both analyses reuse the same physical responses and record each request and charge once.

There is one annotation set for each method, model and arm. There is no repeated-call analysis, repeat consistency, within-model voting, sample SD across annotations, or new calibration experiment. Experiment 9 keeps its stable ID and archived evidence but is not an active result of this study. The reference-assisted, donor-transfer, compact-marker, identity-prompt and neighborhood interventions are outside this campaign.

## Frozen inputs

All assignments join by exact, unique `File_ID,ID` keys across all 220,082 cells. The [primary clustering manifest](../../data/frozen/clustering47_primary_20261108/manifest.json) pins memberships and provenance.

| Method | Occupied clusters | Primary partition |
|---|---:|---|
| Leiden | 300 | Frozen B004 membership |
| FlowSOM | 299 | Seed 42, three shuffled whole-cohort passes |
| SpatialSort | 229 | Seed 42, actual sweep 100, `dmh_iter=5` |
| PIXIE | 300 | Frozen B004 image-derived membership |

SpatialSort seed 43 is clustering sensitivity evidence, not another annotation input. Do not fit clusters, change occupied memberships or select a checkpoint using annotation outcomes. The annotation evidence uses the same 47 protein markers for every method, including CD123 and CDX2. Hoechst1 is not an annotation marker.

Preserve the original 28-label vocabulary, its order and its exact code lookup. Noise, Paneth, NK and M1/M2 macrophages remain distinct allowed outputs. Do not substitute the 20-class clustering-diagnostic map or a 21-label annotation vocabulary.

## Paired evidence and preprocessing

Retain the four training, two validation and two test region assignments. They contain 90,296, 60,210 and 69,576 cells, respectively. The protocol's `calibration` split label refers to these same two validation regions and does not authorize a calibration experiment.

For each marker, transform the authoritative processed expression measurements as `arcsinh(x / 5)`. Fit marker centers and population SD (`ddof=0`) on the pooled training cells only. Use scale 1 only for an exactly constant marker. Calculate each cluster's mean of transformed expression and standardize with those frozen parameters. Do not use `arcsinh(mean(x) / 5)` or the RobustScaler matrix used for SOM fitting.

Calculate the fraction of processed measurements strictly above zero before transformation or standardization. These are numerical fractions, not validated biological marker positivity. Compute statistics in float64 and encode values as integer thousandths using `numpy.rint`. Reuse the same mean integers within each pair.

| Arm | Evidence |
|---|---|
| `all_means` | All 47 training-standardized marker means |
| `all_means_fractions` | Exactly the same means plus the 47 fractions |

Within each pair, preserve memberships, opaque query IDs, marker and cluster order, batch boundaries, ontology, means, prompt, parser, provider and generation settings. Only the fractions matrix changes. Prompts contain no reference labels or profiles, clustering-method names, neighborhood summaries, tools or web access. Full-cohort cluster profiles include training and evaluation cells, making this a transductive study of previously examined B004 data.

## Models, transport and request counts

| Model | OpenRouter ID | Transport | Initial request items |
|---|---|---|---:|
| GPT-6 Astra | `openai/gpt-6-astra` | Batch | 32 |
| Claude Opus 5.5 | `anthropic/claude-opus-5.5` | Batch | 32 |
| Gemini 4 Argon | `google/gemini-4-argon` | Batch | 32 |
| DeepSeek V4.1 Flash 1017 | `deepseek/deepseek-v4.1-flash-1017` | Standard, pinned DeepSeek provider | 32 |

Use supported high reasoning for all four models. Specify annotation seed 42 only where the admitted endpoint supports it. Record omitted or unsupported settings. Do not substitute a model, provider, tier or reasoning level. Exact canonical versions, routes, settings and prices must pass preflight.

The 1,128 occupied clusters require four request batches per method at a maximum of 75 clusters. The design therefore contains **32 requested annotation sets, 128 initial request items and 9,024 requested cluster labels**. Sixteen sets supply the fractions benchmark. The paired contrast uses all 16 method-model pairs. The first three models contribute 96 Batch request items and DeepSeek contributes 32 standard requests. A request item is not a Batch job or an independent biological replicate.

Request a 32,768-token output limit for every model. Preflight must distinguish that requested limit from the route's total billable output, including hidden reasoning. Until the exact DeepSeek billing contract is admitted, reserve finances conservatively for **393,216 output tokens per DeepSeek request**. This reservation does not change its requested 32,768-token limit or authorize longer generation.

Use one annotation block and deterministic counterbalancing of paired arm submission order. Provider-controlled Batch execution order is not asserted. Batch envelopes use only their admitted routing fields rather than copying standard-request routing options. Freeze all 128 literal request items and their hashes before dispatch.

## Response handling and cost admission

Use the exact declared JSON schema and the fixed 28-label code dictionary. Accept each batch atomically only when it has every expected query ID once, no extra or duplicate keys/IDs/fields, correct integer types and label-code range, and a valid terminal response. Reject refusals, truncation and malformed or incomplete batches. All labels in a rejected batch remain missing in planned denominators.

Do not repair, continue or regenerate a generated invalid response. At most two technical retries are allowed only for definitely pre-generation transport failures. Ambiguous submission or delivery outcomes require reconciliation before resubmission. Request IDs map results to observations and do not by themselves establish exactly-once execution. Retain raw requests, responses, attempts, model/provider metadata, usage and charges.

The **US$65 planning ceiling is not spending approval**. The approximately **US$26 expectation is a prior proxy**, not observed spending or a quote from frozen payloads. Exact expected cost and conservative reservations must be recalculated after payload and route admission. An approved spending cap and separate explicit launch instruction are still required. No automatic launch hook is permitted.

## Evaluation and prespecified displays

The primary endpoint is agreement within each of the two test regions, followed by their equal-weighted mean. Retain missing and invalid assignments as errors in each full planned denominator. Calculate macro-F1 within each region over all 28 labels, with absent-class F1 zero, then weight the two region scores equally. Report region values, the equal-region value, cell/cluster delivery coverage, paired agreement differences, label changes on jointly valid pairs, and failure-inclusive agreement bounds. Do not manufacture an annotation SD from regions, batches, cells or different model families.

The paired contrast is fractions minus means for the same method, model, batch, cluster and region. Report joint-valid label changes alongside joint-delivery coverage and planned-denominator outcome differences. Secondary reference-Noise exclusion occurs at scoring only. Noise remains a valid output, and predicted Noise on retained non-Noise cells remains an error. Single annotations do not establish repeated-call stability, calibrated probabilities or donor generalization.

Figure 4's illustrative pipeline is prespecified as **Leiden–Opus 5.5**, not selected for the highest agreement. Its three example clusters are the largest occupied Leiden clusters by cell count, with cluster-ID tie breaks and no reference-label selection. Spatial examples use the fixed Figure 2C region. Within a model, display its single valid prediction, not a repeat vote. An explicitly labeled across-model display may use one prediction per model, with ties in Astra, Opus, Argon, DeepSeek order. That display is not a repeat-consistency analysis.

## Publication and archive boundary

All figure replacements remain paused. Do not edit the live Google Doc, manuscript inventory or artwork as part of this preparation. After valid outputs are verified, regenerate exact manuscript anchors against a fresh live export and integrate in Suggesting mode. Present the 47-marker study directly, using only verified result values. Replace repeated-annotation/SD/vote claims with single-annotation descriptions. Do not apply the partially prepared three-repeat/Fable prose ledger without regeneration.

Experiment 9's archived notebook, inventory and replay manifest are members of the [175-file checksum archive](../../data/historical/publication_before_primary47_20261109/index.json). The unchanged, manifest-pinned `S4a_repeat_variability.csv` and `S4b_consistency_and_review_coverage.csv` paths and hashes are retained in the active-study record. These files are archival evidence, not new measurements or active one-annotation results. Existing versioned evidence and release records remain intact.

The [registry snapshot manifest](../../data/historical/annotation47_pre_one_repeat_20261109/manifest.json) preserves the exact registry bytes before this selection. The active registry points only experiments 7 and 14 to the one-annotation preparation and marks experiment 9 archived without a planned successor. Unrelated stable experiment entries are unchanged.

## Offline implementation and review commands

Install the pinned preparation requirements from `requirements-annotation47.txt` and run scripts from the repository root. The commands below have no generation or submission implementation.

- `scripts/prepare_annotation47.py --protocol configs/primary_annotation47_1repeat_opus55_v1.json --sources-root . --h5ad PATH --output NEW_BUNDLE` builds full-precision profiles, the scaler, anonymous maps, all literal bodies and the three Batch envelopes. Existing outputs cannot be overwritten.
- `scripts/prepare_annotation47.py --verify-bundle BUNDLE` rechecks frozen source/protocol/builder hashes, all sealed files, Cartesian coverage, evidence allowlists, paired means, model settings and envelopes.
- `scripts/preflight_annotation47.py --protocol PROTOCOL --bundle BUNDLE --metadata METADATA --account-receipt ACCOUNT_JSON --output NEW_CERTIFICATE` recomputes provider admission and cost reservations. It always records execution disabled and unresolved launch gates.
- `scripts/collect_annotation47.py --manifest BUNDLE/manifest.json --results SAVED_RESULTS_JSONL --receipts OBSERVED_RECEIPTS_JSON --output NEW_COLLECTION` collects saved responses only. It preserves raw evidence and reconciles request IDs, serving identities, missing/invalid results and charges. It cannot poll or submit an API.

The chosen final bundle is pinned in the active-study record. Its 128 literal bodies and request registry match the initial offline seal exactly. A metadata-only seal update clarified the external manifest binding and canonical-JSON arm-order rule. No scientific request changed. The byte-based central scenario is approximately US$24.69 and the conservative engineering reservation is US$63.78 before fees/taxes. These use actual message contents, but exact provider tokenization and hidden-wrapper bounds remain unverified. The reservation is not a provider-enforced spending guarantee. Account authentication and a separate paid launch instruction remain outstanding.
