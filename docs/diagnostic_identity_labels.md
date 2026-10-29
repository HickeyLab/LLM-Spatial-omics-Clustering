# Historical diagnostics and the corrected aggregate identity

Publication Figure 4D–E and S4B are labelled **Historical majority-based
diagnostic**. This identifies their source-era display, not a causal assignment
of errors to pipeline stages. The source calculation already retains minority
reference-label matches in the green component. It does not display three
disjoint groups of correctly, incorrectly annotated and incorrectly clustered
cells.

For a cluster with N cells, U is its reference-majority fraction and A is the
fraction matching its fixed Claude label, including minority-label matches:

- **Direct reference agreement:** A.
- **Within-cluster bound gap:** 1 − U.
- **Net annotation gap:** U − A.

The components satisfy A + (1 − U) + (U − A) = 1. At aggregate level they are
weighted by cluster cell counts. The net annotation-gap cell count equals
majority-reference mismatches minus minority-label matches. There is no claim
of causal attribution, independent validation or annotation of a different
label list.

The frozen 300-cluster table was recomputed from all 220,082 exact-key source
cells. Every S4 cluster component matches its source CSV. For the historical
21-label scoring vocabulary, direct agreement is 123,099/220,082, the bound-gap
count is 63,067 and the net annotation-gap count is 33,916. The latter is
41,402 majority-label mismatches minus 7,486 minority-label matches. These give
55.933%, 28.656% and 15.411%, respectively. The same predictions evaluated
against the original 28 reference labels give 32.024%, 31.315% and 36.662%.
The latter remains a vocabulary-mismatch diagnostic. The source predictions,
reference vocabularies and plotted values are unchanged.

Figure S8 labels the corrected identity explicitly and uses the three exact
metric names above. Its original image is retained as a checksum-verified
source snapshot solely to reproduce the display-label changes. Later package
notebook reconstructions originally used a separate GPT workflow. The
canonical Figure 4 notebook now replays the frozen historical Claude map
and checks both reference vocabularies against this audit. The prior GPT
reconstruction is retained only in the local author backup. See the
[Figure 4 replay contract](figure_04_historical_claude_replay.md).

## Verification and provenance

See [the frozen-count audit](leiden_claude_diagnostic_identity_audit.json).
`verify_leiden_claude_diagnostic_identity.py` verifies the count table, both
aggregate identities and minority-match correction. The display-overlay script
checks numerical-pixel preservation independently. The source producers are
`v3_scripts/historical_v1_figure04_replay.py` and
`v3_scripts/historical_v1_figure_s02_replay.py`; the latter was composed as S4.
Their legacy internal loss-column names remain for compatibility. Only their
visible terminology is changed.

## Matching manuscript wording

### Section 3.4 diagnostic definitions

Figures 4D–E and S4B retain source-era displays labelled “Historical majority-based diagnostic.” For each cluster, U is its reference-majority fraction and A is the fraction of cells whose reference label matches the assigned Claude label. The displayed components are Direct reference agreement (A), Net annotation gap (U − A) and Within-cluster bound gap (1 − U). The source calculations already count minority-label matches in A. These quantities compare agreement with a fixed-partition bound. They are not disjoint cell categories or causal attributions to clustering and annotation stages. Figure 4E weights the cluster components by cell count. Figure S8 states the corrected aggregate identity, A + (1 − U) + (U − A) = 1, and distinguishes the net annotation gap from the uncorrected majority-label disagreement count.

### Section 3.4 cluster examples

The representative examples include a Smooth muscle-majority cluster assigned Stroma by Claude, a Neutrophil-majority cluster assigned Neutrophil, and a Cycling TA-majority cluster assigned Goblet (Figure 4D). Their bar patterns compare direct reference agreement with the majority-reference bound without assigning a cause to an individual error.

### Figure 4 caption D–E

(D) Representative Leiden clusters shown as a Historical majority-based diagnostic. Row labels state the reference-majority cell type and Claude-predicted label. (E) Cell-count-weighted aggregate of the same diagnostic. In (D–E), green shows Direct reference agreement (A), orange Net annotation gap (U − A) and gray Within-cluster bound gap (1 − U), where U is the cluster-majority upper bound at the displayed level. Direct reference agreement retains minority-label matches. These arithmetic comparisons do not attribute errors causally to pipeline stages. Figure S8 presents the corrected aggregate identity and its vocabulary-mismatch comparison.

### Figure S4 caption

(A) Cell-count and row-normalized confusion matrices comparing reference cell-type labels (rows) with Claude-predicted labels assigned to Leiden clusters (columns). (B) Historical majority-based diagnostic for all 300 Leiden clusters, ordered by decreasing cluster-majority upper bound. Row labels identify the cluster and its reference-majority cell type. Green shows Direct reference agreement (A), orange Net annotation gap (U − A) and gray Within-cluster bound gap (1 − U), where U is the cluster reference-majority fraction. All direct matches, including minority-label matches, contribute to A. The segments are arithmetic quantities rather than mutually exclusive causal error categories. Figure S8 presents their cell-count-weighted aggregate identity.

### Figure S8 caption title

Corrected aggregate error identity for the historical Leiden–Claude prediction map, retaining minority-label matches.

### Figure S8 caption body

Green shows Direct reference agreement (A), gray Within-cluster bound gap (1 − U) and orange Net annotation gap (U − A), where U is the fixed-partition cluster-majority upper bound. The components sum to one and include all 220,082 cells, including Noise. The net annotation gap subtracts minority-label matches from majority-label mismatches. The upper row uses the historical 21-label scoring vocabulary. The lower row compares the same predictions restricted to that historical label list with the original 28-label reference annotations. This lower row is a vocabulary-mismatch diagnostic, not a new benchmark under a 28-label prompt.
