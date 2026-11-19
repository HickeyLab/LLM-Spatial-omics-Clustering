# Reviewer refresh: credit-funded Astra, Batch transport, one generation

Status: **prepared; inference disabled**. This protocol supplements the completed primary B004 study. Its prepared request bodies, account gates and donor dependencies do not establish new annotation results. The [versioned configuration](../../configs/reviewer_annotation47_credit_batch_v1.json) does not overwrite any existing protocol, accepted answer, figure or manuscript suggestion.

## Study matrix

| Study | Implementation and reporting boundary |
| --- | --- |
| B005/B006 transfer | Admit the current producer chat's **50 actual sweeps**, DMH=5, seeds 42/43; seed 42 primary and seed 43 sensitivity. Require complete outputs and scheduler evidence for both seeds in each donor. No duplicate SpatialSort submission or modification of that chat's work. |
| Conventional classifiers | Offline nearest-centroid and multinomial logistic regression, 47 means or 94 means/fraction features, on the exact B004 source and frozen memberships. Training-region cell labels provide richer supervision than the LLM input. |
| Granularity | Offline cell-count-weighted Ward coarsening of full-precision profiles to K=100 and K=200. Freeze mappings before loading reference labels. This measures post-clustering partition sensitivity, not new native-K fits or LLM ranking stability. |
| Repeated annotations | One generation per scientific condition. There is no repeated-generation study, repeat SD, within-model majority vote or run-to-run reproducibility claim. |
| Representations | Four models × four methods × selected marker names, selected numerical means, all means, and all means plus fractions. Positive one-versus-rest tie-corrected Wilcoxon selection; at most six markers, transformed-mean and lexical ties, highest-mean fallback. No label-assisted selection. |
| Method-name control | Opus, four methods: the means/fraction evidence with only the correct method identity added; compare against the corresponding blinded condition. |
| Calibration | Retrospective cross-model agreement on the means/fraction arm. Score for each delivered label is the fraction of four model labels that agree with it, with denominator four. Freeze cluster-hash development/evaluation assignment and retain region separation. This is within-donor reference-agreement calibration, not native probability or repeated-call confidence. |
| Neighborhood | Opus–Leiden: identical means/fraction evidence plus measured expression of 15 nearest other cells within each region. Break distance ties by numeric cell ID. No neighbor labels. |

## Evidence and paired requests

B004 uses all 220,082 cells, the frozen 47-marker order and original 28-label dictionary including Noise. The authoritative H5AD SHA-256 is `5d0a59d1e7866dee5a3a06772c3c80ce7328ba6420bc140708be5ec451b8a49a`. The source contains 45 expression columns plus measured CD123/CDX2 in observation fields; all 47 are required. No missing channels are filled with zero, inferred or dropped.

Compute `arcsinh(processed expression / 5)` before cluster means. Use the four existing B004 training regions for marker center and population SD (`ddof=0`). Fractions are computed from processed values strictly above zero before transformation/standardization. These numerical fractions are not validated biological positivity. Encode values as integer thousandths. Compact numerical arms copy the selected integers from the full arm exactly. Marker selection and neighborhoods never consume reference labels.

The neighborhood vector first averages measured transformed values over each cell's nearest neighbors, then averages these vectors within its query cluster, then applies the frozen B004 training scaler. It excludes the target cell even at duplicate coordinates. Selection, cluster IDs and full cell maps stay outside the model-visible anonymous evidence. Within each condition retain the original cluster order, groups of at most 75 and anonymous IDs `0..n-1`. Tools, retrieval, web access, reference profiles and optional sampling parameters are absent. Named prompts add only their prespecified method field.

B004 contains 300 Leiden, 299 FlowSOM, 229 SpatialSort and 300 PIXIE occupied clusters. The representation matrix has **64 logical annotation sets / 256 request items**; four named sets add 16 items and one neighborhood set adds four. Total: **69 logical sets / 276 items**. A request item, a physical generation and a biological replicate are different units.

There are **109 potential exact-condition reuse items**, pending wire/model/route reconciliation: 32 Astra, 32 Opus, 32 Gemini and 13 Morph FP8 DeepSeek. If all are admitted, **167 B004 items** need new inference (32 Astra, 52 Opus, 32 Gemini, 51 DeepSeek). No reuse candidate is automatically admitted. Existing accepted responses remain immutable, and the prepared full arms retain the original model-visible message strings. Reuse must also match model snapshot, provider/precision, seed, reasoning, output ceiling, query boundaries and strict saved-output validation. Reuse is conditional when changing transport; a family-name match alone is insufficient.

## Models, transport and funding

| Family | Target | Reasoning | Combined output ceiling | Binding status |
| --- | --- | --- | --- | --- |
| Astra | Native OpenAI Batch, original Astra snapshot | high | 32,768 | Explicit native inventory/model/seed equivalence and funded project required |
| Opus 5.5 | OpenRouter Anthropic Batch, original snapshot | high | 32,768 | Frozen original binding; reconcile each reused answer |
| Argon | Native Google Batch candidate, original snapshot | high | 943,718 | Long-output/checkpoint behavior, exact schema, account and pricing unadmitted |
| DeepSeek | OpenRouter Morph FP8 Batch, original snapshot | high | 943,718 | Full output/response-format support and route admission required |

Use seed 42 where the frozen endpoint contract supports it; do not silently drop a required seed. These are the recorded high-reasoning settings used by the completed campaign. No model revision, lower reasoning, smaller groups or foreground fallback is automatic. A candidate model ID in a DRAFT file is not a verified available endpoint.

Astra uses the **existing API balance of the selected OpenAI organization/project, regardless of the credit source**. ChatGPT/Codex access is not an API billing credential. There is no requirement to use a Pro promotional allowance, purchase credits, activate a promotion or change recharge settings. Validate access with a secure `OPENAI_API_KEY`; never put keys in protocol files, logs or version control. Account balance evidence must be recent, account-bound and sufficient for all reservations plus headroom. An API key alone does not establish billing balance or authorize generation.

Other providers retain separately accounted funding. The new production cash and OpenAI-credit caps remain unbound. The preparation certificate reports full-output reservations using conservative input-byte proxies and unadmitted price assumptions; these are **not** the expected spend or a launch approval. Donor totals await occupied-cluster counts and admitted populations. The prior campaign's $90 ceiling does not authorize this new campaign.

Technical Batch validation is a separate engineering stage with a proposed **$3 cash limit** and execution disabled. First verify supported native schemas and output/checkpoint semantics using documentation and read-only inventories. A short successful output cannot prove long-output acceptance. Seal the exact engineering probes, reserve their full admitted cost and obtain a separate launch instruction. If the required validation cannot fit its cap, stop for a revised cap; do not quietly lower the scientific ceiling, split clusters or start foreground calls. No synthetic probe contributes a scientific prediction.

## Donor dependency and admission

The producer chat is **Run 47-marker SpatialSort on 5/6** (`01a1c7cb-7c45-7a63-8297-8b4b7f7c3fed`). The user selected its current 50-sweep budget. **B004 remains at its frozen sweep 100**; the donor budget is explicitly 50, never relabelled as 100.

The current H5AD selections have **288,188 B005 cells and 301,280 B006 cells**, eight regions each, total **589,468**. Their full-source SHA-256 is `a159bbeca2a4dd84dc265929d3b1d409c16be5e00a2f9819c012b8a5879c37e0`. Do not substitute the older atlas cohort, its outcome mapping or previously saved donor predictions. The B005/B006 selection hashes are respectively `15e5334fbf49c4527db6f48abab82d9477a7b3781a24435de717b3c9d26b7e8a` and `56143622c8d16427c42fde267169e61d52aa2f900bbb659fd7a2f8351e5cdef7`.

`donors.admit_spatialsort_handoff` consumes a producer export only after exact 47-marker/source/selection and unique `(File_ID, ID)` verification. Each chain needs COMPLETED/exit-zero scheduler evidence, all 50 sweep traces, complete checkpoint/RNG metadata and keyed final assignment parity. Paths must stay inside the approved export root. A missing scheduler entry, receipt or notebook access never proves completion. The module has no submission, resume, cancellation or fitting path.

The new cohort's Leiden/three-pass FlowSOM memberships, native PIXIE image/mask correspondence, label vocabulary and evaluation projection remain explicit dependencies. Require their cohort-matched receipts before annotation. Preserve native image-based PIXIE; do not create a tabular substitute. Freeze the common verified cell population and report its coverage of every intended donor/region. Keep native 28-label outputs, and bind a donor evaluation projection only after auditing this cohort's actual reference labels. Do not automatically reuse the old 23-label map. Use B004 training normalization and frozen classifier parameters for donor predictions, with no donor-label tuning.

## Reproduction and launch separation

Install `requirements-reviewer47.txt` with Python 3.12. Use new output paths; existing artifacts cannot be overwritten.

```bash
python3.12 scripts/reviewer47.py prepare --source-bundle ORIGINAL_SEALED_BUNDLE --h5ad EXACT_B004_H5AD --output NEW_DRAFT_BUNDLE
python3.12 scripts/reviewer47.py verify --bundle NEW_DRAFT_BUNDLE
python3.12 scripts/reviewer47.py donor-status --external-root PRODUCER_ARTIFACTS --verify-hashes --output NEW_OBSERVATION.json
python3.12 scripts/reviewer47.py preflight --bundle NEW_DRAFT_BUNDLE --donor-observation NEW_OBSERVATION.json --output NEW_CERTIFICATE.json
python3.12 scripts/reviewer47.py offline --analysis granularity --output NEW_GRANULARITY
python3.12 scripts/reviewer47.py offline --analysis baselines --h5ad EXACT_B004_H5AD --output NEW_BASELINES
python3.12 scripts/reviewer47.py offline --analysis calibration --output NEW_CALIBRATION
PYTHONPATH=src:. python3.12 -m unittest discover -s tests -p 'test_reviewer47_*.py'
```

The CLI has no paid or scheduler launch command. `transport.py` provides a separately guarded native Astra executor for a future admitted launch. It requires an enabled runtime protocol, exact native model binding, fresh account-credit evidence, a passed transport certificate and a separate explicit user launch record, all bound by hashes to the exact non-reused JSONL items and scientific scope. The checked-in disabled configuration rejects before HTTP or ledger writes. Draft files include reuse candidates and **must not be submitted directly**.

Upload and Batch submission persist/fsync locked pending records before each POST. An ambiguous POST blocks resubmission until read-only reconciliation finds the original receipt; there are no automatic POST retries, model/provider fallback, answer regeneration or unbounded budget increases. Collection joins by unique IDs, pins the strict parser, preserves all missing/invalid conditions in the planned denominator, and records usage/charges per physical attempt once. Invalid outputs do not become the valid Noise class.

## Completed offline preparation

The [new offline artifact index](../../data/frozen/reviewer47_offline_20261110/index.json) preserves actual completed classifier, coarsening and current-bank calibration outputs, fitted parameters, hash receipts and environments. Granularity mappings and calibration splits were sealed before reference/outcome materialization. The calibration uses the current accepted bank; it must be rescored if the admitted bank changes. It is not a final result of unexecuted representation/control/donor calls.

The [preparation record](reviewer47_preparation_20261110.json) reports literal bundle hashes and remaining gates. New paid calls: **zero**. No cloud job was submitted by this pipeline. Figures and manuscript results are unchanged by this preparation. After new accepted outputs are scored, integrate only supported results in Google Docs **Suggesting mode**, preserve unrelated suggestions and original evidence, use IEEE tables/red–green heatmaps and white–red S11 expression plots.
