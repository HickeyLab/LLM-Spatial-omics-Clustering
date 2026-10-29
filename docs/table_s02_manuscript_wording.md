# Table S2 matching manuscript wording

## Methods 2.10 export terminology and original prompt boundary

For retrospective marker-name-list parameter selection, we generated short marker-name lists from the 45-marker H5AD matrix. For every cluster-marker pair, we calculated mean stored expression and the fraction of cluster cells strictly above the specified expression cutoff. A marker was retained when both this above-cutoff fraction and the cluster mean strictly exceeded their respective thresholds. Retained markers were ranked by descending within-cluster mean expression and capped at the specified maximum number of markers. If no marker passed both filters, the specified fallback number of markers with the highest cluster means was used. The exports were JSON objects mapping cluster identifiers to marker-name lists. They are distinct from the numerical marker-expression profiles in the archived original LLM prompts. Each original target profile contained 12 high-ranked and eight low-ranked [marker, mean_asinh, full_cohort_delta_z] entries and task context, with a historical scored vocabulary of 21 labels including Noise (Supplementary Note 1). The prompt requested exactly one allowed label per cluster and a JSON-object response. The archived requests do not verify use of the Table S2 export settings in constructing those original profiles.

## Methods 2.10 selection provenance

Table S2 reports retrospective marker-name-list parameter selection using the full reference-labeled cohort. The recorded values match the archived extended search, which evaluated a rule-based marker-list annotator using best_clusters_combined.csv. The available legacy PIXIE-style export contains 50 cluster lists. Its equivalence to the TIFF-derived PIXIE implementation with 300 occupied clusters in the main benchmark has not been verified, so the legacy label is retained. These recorded export selections do not establish the input representation used in the original LLM benchmark.

## Results 3.3

Table S2 summarizes retrospective marker-name-list parameter selection using the full reference-labeled cohort. These export settings do not identify the numerical inputs supplied in the original LLM prompts.

## Discussion benchmark representation

Clustering and annotation performance varied across methods, models, cell types, tissue regions, evaluation metrics and recorded prompt conditions.

## Limitations selection scope

For retrospective marker-name-list parameter selection (Table S2), the full reference-labeled cohort was reused to select and score the rule-based annotation procedure. These exports do not establish the original LLM prompt content.

## Table S2 caption

Table S2. Retrospective marker-name-list parameter selection. (A) Declared candidate ranges by source-table method. (B) Candidate-grid cardinalities. (C) Declared fine-grid search spaces. (D) Recorded parameters for marker-name-list exports. The display label PIXIE-style export preserves the source-table label PIXIE-style adaptation. The available legacy export contains 50 cluster lists, and equivalence to the main benchmark’s TIFF-derived PIXIE implementation with 300 occupied clusters has not been verified. These are retrospective selections using the full reference-labeled cohort and are not independently validated settings. They do not establish which inputs were supplied to the original LLMs. Archived original prompts instead contain numerical marker-expression profiles and task context (Supplementary Note 1).
