# Figure 4 implementation contract

Figure 4 evaluates one end-to-end Leiden-to-GPT pipeline. The notebook has
exactly six code cells, one for each panel A through F. Every cell is
self-contained and can be run without executing an earlier panel.

## Shared dependency

Figure 4 does not rerun clustering and does not search the legacy annotation
JSON files. Panels B--F all request the same Figure 3 result:

- clustering: Figure 2's fixed 55-cluster Leiden assignment;
- provider: OpenAI;
- condition: reasoning;
- marker state: optimized;
- requested model: the model snapshot tracked in `configs/figure_03.yaml`;
- response cache:
  `outputs/figure_03/cache/llm_annotations/openai_reasoning_leiden_optimized.json`.

The cache is created or reused through Figure 3's validated request contract.
It records the requested and returned model IDs and the prompt, marker-summary,
annotation, and cache-contract hashes. No mapping is copied into Figure 4.
Figure 4 verifies the cache's stored annotation hash and creates a local
selection lock on the first successful biological-panel run. Every later panel
must match that lock, so a refreshed or edited mapping cannot be mixed into the
same figure silently.

The checked-in notebook reads `OPENAI_API_KEY` from the environment and falls
back to `PASTE_OPENAI_API_KEY_HERE`. Panels B--F reject that placeholder before
loading the H5AD, reading a cache, or writing an output. Panel A is a local
workflow schematic and needs no key.

## Evaluation universe

Figure 3's benchmark metrics use 209,587 non-Noise cells. Figure 4 instead
matches the displayed end-to-end analysis universe: all 220,082 B004 cells
from eight File_ID regions, including 10,495 cells whose reference label is
`Noise`. The truth vocabulary therefore has 21 labels. GPT still chooses from
the 20 biological labels defined by Figure 3, so the predicted vocabulary
does not contain `Noise`.

Exact `(File_ID, ID)` keys, 55 Leiden cluster IDs, eight regions, the truth
vocabulary, and full annotation-map coverage are validated before metrics are
computed.

## Panels

- **A:** frozen H5AD -> Figure 2 Leiden -> Figure 3 optimized marker summary ->
  GPT -> Figure 4 evaluation workflow.
- **B:** count and row-normalized confusion matrices over all source cells.
- **C:** pooled one-vs-rest F1 bars plus F1 recalculated within each File_ID.
- **D:** deterministic annotation-limited, clustering-limited, and mixed-loss
  cluster examples from the current shared annotation mapping. Named limited
  examples require positive loss of the named type greater than the other
  loss component.
- **E:** cell-count-weighted overall outcome fractions.
- **F:** the same outcome fractions for each Leiden cluster.

## Error-decomposition definition

For each Leiden cluster:

1. `purity` is the fraction of cells with the cluster's majority truth label.
2. `final_correct` is the fraction whose truth label equals the GPT-assigned
   cluster label.
3. `annotation_loss = max(purity - final_correct, 0)`.
4. `clustering_loss = 1 - purity`.

The three displayed components sum to one. They are an arithmetic
upper-bound decomposition and should not be described as mutually exclusive
causal labels assigned to individual cells.

The supplied composite is used as a layout reference only. Its legacy Panels
B, C/D, and E were produced from different annotation maps, and Panel E
hard-coded its displayed percentages. Figure 4 deliberately recomputes B--F
from one provenance-tracked annotation result, so the new numerical results
are not expected to reproduce those mixed legacy values.
