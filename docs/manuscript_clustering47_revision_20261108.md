# Manuscript revision for the frozen 47-marker clustering results

The [Google Doc](https://docs.google.com/document/d/1aqZgv5aFS-fgXT2KnZw3CXcxD_W3X1HgjRz_KXf1L18/edit?tab=t.epoyu1tdr39l) was revised on November 8, 2026 in **Suggesting mode**. Prose, the 13 edited cells in Tables S2A/S2B, and the replacements of Figure 2, Figure S4 and Figure S5 remain pending. They have not been accepted. This repository records the refreshed artwork and scoped revisions without including a private manuscript export.

## Completed clustering and provenance

All partitions contain the same 220,082 B004 cells joined by exact `File_ID,ID` keys. Leiden and PIXIE memberships remain unchanged. FlowSOM uses all 47 protein markers, seed 42 and three shuffled whole-cohort passes, giving 660,246 updates and 299 occupied clusters from a target of 300. SpatialSort uses all 47 markers and 100 actual sweeps with `dmh_iter=5`. Seed 42 is primary with 229 occupied clusters. Seed 43 is sensitivity evidence with 231. Their endpoint partition ARI is 0.458. This is seed sensitivity evidence and does not establish convergence.

Inputs, hashes and completion evidence are pinned in [the frozen input bundle](../data/frozen/clustering47_primary_20261108/manifest.json). The [metric receipt](../data/frozen/clustering47_primary_20261108/metrics_receipt.json) and [portable recomputation instructions](clustering47_metric_recomputation.md) document scoring without new clustering fits or annotation calls. The FlowSOM three-pass budget was frozen after diagnostic results were available, so it is not described as a prospective preregistration.

Figure 2 E–H uses 209,587 non-Noise cells and the existing 20-class map, including Paneth to Goblet. The eight regions are observations within donor B004. Regional means are:

| Method | Weighted F1 | Cluster purity |
|---|---:|---:|
| Leiden | 0.7391 | 0.7464 |
| FlowSOM | 0.5323 | 0.5747 |
| SpatialSort primary | 0.5278 | 0.5583 |
| PIXIE | 0.6154 | 0.6446 |

Relative to the retained publication baseline, FlowSOM regional weighted F1 and purity decreased by 10.07 and 7.79 percentage points. SpatialSort increased by 3.34 and 2.59 points. These are descriptive, reference-informed comparisons with different fitting budgets and marker inputs. They do not establish biological improvement. The separate raw-label and historical 21-label scores are not substituted into Figure 2. Figure S4D uses 27 raw non-Noise labels, while Figure S5A uses all 28 raw labels including Noise.

## Current and historical scope

Only clustering-dependent Figure 2 A–H, Figure S4 and Figure S5 artwork is refreshed. Figure S5B retains the historical shared-45-marker controls and their fitting budgets. It does not isolate a marker-only effect against the refreshed primary partitions. The retired FlowSOM cluster-count sweep remains archived and is not restored to Figure S4.

Figure 3 B–E, Figure 4 B–E, Figures S6, S7, S10 and S11A retain their actual historical predictions and values. Their pending captions identify that status. The historical Leiden–Claude case, 21-label vocabulary sensitivities, reference-assisted controls, compact-marker experiments and B005/B006 analyses are not silently reassigned to the new clusters.

## Planned annotation and author placeholders

The refreshed methods are drafted in future-complete manuscript style for the planned combined experiments #7/#9/#14. One explicit author note identifies that status. Verified model/provider bindings, supported high-reasoning settings, token budgets, execution dates, annotation outcomes, coverage and costs remain author placeholders. No result is inferred from a clustering-only update.

The design compares all-47-marker means alone against the same means plus fractions of processed values above zero, using the original 28-label vocabulary including Noise. Four methods, four model families, two arms and five fresh repetitions specify 160 requested annotation sets. The 1,128 primary clusters require 640 initial requests at a maximum of 75 clusters per batch. Primary reporting equally weights the two existing B004 test regions. Missing or invalid predictions remain errors in the planned denominator. The [versioned combined protocol](../configs/combined_annotation47_7_9_14_v1.json) remains planned, disabled and unexecuted. Model bindings, spending approval and a separate launch instruction are still required.

## Scoped revision and verification records

- [Ordered text replacement ledger](manuscript_clustering47_text_edits_20261108.json) records 46 exact sequential replacements, including six historical-scope clarifiers.
- [Native table-cell ledger](manuscript_clustering47_table_edits_20261108.json) records the 13 exact cell edits.
- [Native readback receipt](manuscript_clustering47_readback_20261108.json) verifies that proposed text equals those changes, all original text remains in the tracked revisions, and the document retains 617 body elements, 11 tables, 18 drawings and five equations. It contains 58 insertion and 59 deletion nodes. One earlier count suggestion was amended, so node counts differ from the number of replacements.

Native Word/PDF exports represent accepted/current image content and omit the pending media replacements. In the checked export, all 18 image payloads still match the accepted baseline. This is an export limitation, not proof that the pending images are absent from Google Docs. Inspect the live pending image suggestions or the repository artwork for the refreshed figures. The [live image proof receipt](manuscript_clustering47_live_image_proof_20261108.json) independently compares copied pending images against new and old artwork. It also records live widths, rounded proportional heights, locked aspect ratios, 100% scales, zero rotation and the editor-observed crop resets for all three. The prose/table readback receipt makes no image-verification claim. Private exports and full manuscript text are retained outside this repository.
