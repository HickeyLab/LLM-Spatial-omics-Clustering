# Planned combined 47-marker annotation protocol: experiments 7, 9 and 14

**Status: planned—not executed. Execution is disabled. Zero annotation calls and zero jobs have been submitted for this protocol.** SpatialSort finishing will not launch it automatically. A separate user launch instruction and an approved spending cap are required.

The machine-readable specification is [combined_annotation47_7_9_14_v1.json](../../configs/combined_annotation47_7_9_14_v1.json). Stable experiment IDs are recorded in the [experiment registry](../../configs/experiment_registry.json). Preparation does not replace any existing manuscript result.

## Scientific design

Use all 220,082 B004 cells, all occupied clusters in four frozen partitions, all 47 protein-marker measurements, and the original 28-label vocabulary including Noise. Preserve Paneth, NK, and M1/M2 macrophages as distinct allowed labels. The annotation evidence uses the same 47-marker order for every method, irrespective of the representation originally used for clustering.

The primary FlowSOM partition is the frozen seed-42, three-full-pass partition (299 occupied groups). The primary SpatialSort partition will be seed 42 at actual sweep 100, DMH=5. Both SpatialSort chains must finish and pass output validation; seed 43 remains a clustering sensitivity rather than an additional annotation campaign. Preserve the existing Leiden and PIXIE memberships. Their exact source hashes and the FlowSOM contract are pinned in the configuration; final SpatialSort hashes remain unbound.

| Input arm | Evidence |
| --- | --- |
| `all_means` | All 47 transformed, training-standardized cluster marker means |
| `all_means_fractions` | Exactly those means plus 47 fractions of processed values strictly above zero |

Calculate means after arcsinh(processed expression / 5), and standardize using center and SD fitted on the four existing B004 training regions. Calculate fractions from the deposited processed values before transformation or standardization. The additional CD123/CDX2 vectors come from the H5AD observations; do not use the RobustScaler SOM feature matrix for annotation summaries. Fractions are numerical summaries, not independently validated biological marker positivity.

Encode values as integer thousandths. Within each pair, preserve memberships, means, marker/cluster ordering, prompt, vocabulary, provider, model settings, seeds where supported, batch boundaries and parser. Only the fraction matrix changes. Neither arm receives reference profiles, method names, neighborhood information, tools, web access or reference outcomes.

Five fresh repetitions per arm, model and method produce **160 complete annotation sets** (4 methods × 4 model families × 2 arms × 5 repetitions). Batches contain at most 75 clusters. The final number of requests is `40 × sum(ceil(occupied_clusters_method / 75))`, before eligible transport retries; it awaits SpatialSort's occupied count. Use five complete repeat blocks and deterministic hash-based counterbalancing of arm order. Repetitions must never share a provider response.

Use updated frontier versions from OpenAI, Anthropic, Google and DeepSeek, with supported high-reasoning settings verified for each model. Exact IDs, providers, token budgets and prices remain explicitly unbound. Provider-specific high reasoning does not imply equal compute. There is no low-versus-high reasoning experiment in this protocol.

## Shared outputs and scoring

- Experiment 7: report the fractions arm as the refreshed full-marker benchmark.
- Experiment 14: report the paired fractions-minus-means contrast.
- Experiment 9: derive repeat variability and label consistency from these same fresh repeated calls. Historical reference-assisted repeatability remains separate; it is not claimed to have been repeated by this two-arm study.

Retain the existing four-training/two-validation/two-test region split. Query every cluster using its full-cohort, label-blind summary; freeze predictions before scoring the test outcomes. The primary endpoint is equal-weighted agreement across the two existing test regions. Missing or invalid predictions remain errors in the full planned denominator. Report fixed-28-label macro-F1 (absent classes contribute zero), cell and cluster delivery coverage, paired label changes, missing-prediction agreement bounds, repeat mean and sample SD, consistency, token usage and observed cost. A secondary Noise exclusion applies to reference-Noise cells at scoring only.

For consistency, divide the modal valid-label count by all five requested repetitions; missing outputs supply no vote. Resolve modal ties using the frozen ontology order. No valid votes means no delivered prediction. Noise remains an allowed cell-type output rather than an abstention symbol. These repeats measure computational variation within previously examined B004 data; they do not establish donor replication or calibrated probabilities.

One physical request/response is recorded and charged once even when its predictions support several declared analyses. Keep raw responses, settings, usage and every attempt. Validate every requested cluster exactly once with no extra IDs or unsupported labels. Invalid or incomplete batches remain unresolved. At most two retries are allowed only for definitely pre-generation transport failures. Do not regenerate invalid annotations or formatting failures. Ambiguous dispatch outcomes retain their cost reservation until reconciled.

The historical 21-label benchmark, earlier three-attempt full-marker benchmark, three-run paired study and reference-assisted repeatability remain archived and separately reported. Do not pool them with the future 47-marker cohort.

## Offline preparation and activation boundary

```bash
python scripts/validate_combined_annotation47.py
PYTHONPATH=src python -m unittest discover -s tests -p 'test_combined_annotation47.py'
```

The validator has no transport, credential lookup, generation or scheduler implementation. It admits only a disabled preparation and rejects accidental activation. Additional checks require 47-marker paired evidence, exact cell-key joins and unique request identities. Passing these checks does not authorize inference or verify the still-unavailable SpatialSort outputs.

Before a separate launch, verify both SpatialSort chains at sweep 100 and expected final outputs; admit all frozen assignments, keys and measurement evidence; freeze current model/provider/reasoning/token/price bindings; produce an exact request-count and cost preflight; obtain an explicitly approved total cap and a separate user launch instruction. Produce a separately versioned bound execution specification referencing this preparation; v1 remains a dormant record. There is no executor entry point or automatic launch hook in this preparation.
