# Figure 3 notebook contract

`notebooks/main/figure_03_llm_annotation_benchmark.ipynb` retains exactly
twelve source-panel code cells in historical order, A through L. The current
publication page retains source panels `A, F, G, H, I, J, K, L` and relabels
them sequentially as publication panels `A–H`:

| Publication panel | Historical source panel |
| --- | --- |
| A | A |
| B | F |
| C | G |
| D | H |
| E | I |
| F | J |
| G | K |
| H | L |

Panel A is a local workflow schematic. The notebook has one cleared runnable
code cell per historical source panel. LLM-dependent cells fail closed when
their environment-variable lookups resolve to tracked placeholder values; no
credential is embedded in the notebook. Export the corresponding
`*_API_KEY` variable or use a notebook secret manager. Each cell searches
upward from the working directory for the repository; when Jupyter starts
elsewhere, set `FIGURE_REPOSITORY_ROOT`.

## Figure 2 dependency

Figure 3 does not rerun clustering. It imports the exact selected assignments
from the Figure 2 Panel D contract:

- FlowSOM: 300 clusters;
- Leiden: 55 clusters;
- SpatialSort: 60 clusters;
- PIXIE: 50 image-native clusters derived from the TIFF workflow.

All tables are joined by exact `File_ID` + `ID`. The evaluation cohort is the
same eight-region B004 subset used in Figure 2: 220,082 source cells and
209,587 cells after excluding the 10,495 `Noise` reference cells. Figure 2's
20-class harmonization map is reused unchanged, including `Paneth -> Goblet`.

This deliberately supersedes the legacy Figure 3 scripts that read the
table-level PIXIE adaptation. PIXIE results produced by this notebook can
therefore differ from the supplied composite screenshot.

## Marker-summary contract

The inputs are the 45 protein-marker columns from H5AD `X`; the three
observation-only Figure 2 features are excluded. Marker summaries use all
220,082 assigned B004 cells. `Noise` and all other reference labels are
evaluation-only and cannot change an LLM prompt. For each cluster, markers are
ranked by within-cluster mean expression and filtered with strict `>`
comparisons for the expression, positive-fraction, and mean-expression
thresholds. A fallback list is used only when no marker passes. A nonempty
short list is not padded.

Default and method-specific optimized thresholds are tracked in
`configs/figure_03.yaml`. The prompt text and allowed 20-label vocabulary are
tracked in `prompts/figure_03_cluster_annotation_v1.txt`.
The exact harmonized-label palette used for spatial maps is tracked in
`configs/figure_03_cell_type_colors.csv`; all 20 labels must be present.

## LLM and cache safety

No credential is read from or written to the repository. Every LLM-dependent
panel calls the credential guard before loading the H5AD, creating marker
summaries, reading an LLM cache, or writing panel artifacts. Consequently, the
checked-in placeholder keys cannot generate the LLM-dependent source panels.

After real keys are provided locally, marker-summary caches require the exact
marker parameters, Figure 2 assignments, H5AD expression fingerprint, and
source-cell contract. LLM responses use prompt-equivalence reuse: their cache
requires the provider endpoint/version, requested model, complete condition
configuration, temperature, output-token limit, prompt hash, marker-summary
hash, and allowed-label vocabulary to match. Current upstream fingerprints
remain recorded in panel provenance even when they produce an unchanged prompt.
Requested and provider-reported model identifiers, annotation hashes, and
cache hashes are retained in provenance. Reasoning/thinking blocks and
signatures are removed from the stored provider response. A replaced cache is
archived under `outputs/figure_03/cache/llm_annotations/history/`.

The historical DeepSeek V3.2 aliases were retired on 2026-07-24. Fresh
DeepSeek generation is therefore blocked before calls to any active provider;
only a contract-matched historical cache can complete the four-provider
panels. A V4 migration would be a new analysis and requires explicit author
approval. Gemini's historical `non_reasoning` condition uses `minimal`
thinking, which provider documentation says may still think on complex tasks,
so it is not a guaranteed no-reasoning condition. OpenAI requests use the
`gpt-5.2-2025-12-11` snapshot; preview-model responses also retain the
provider-reported served version.

## Consensus caveat

Source panels J/K/L (publication panels F/G/H) reproduce the attached Methods policy: all 24 provider priority
orders were evaluated against the same reference labels, and the best
cell-level order was retained separately for each clustering method.
Consequently, the displayed historical vote is exploratory and is not an
outcome-independent consensus. Each run exports all 24 priority-order scores
for every included method as a sensitivity CSV, and the plotted vote is marked
with an asterisk.

## Publication panel definitions

- **A (source A):** Figure 2 cluster-to-evaluation workflow.
- **B (source F):** global provider-by-method cell-level heatmap.
- **C (source G):** global provider-by-method cluster-level heatmap.
- **D (source H):** Leiden per-cell-type absolute annotation accuracy.
- **E (source I):** Leiden per-cell-type upper-bound-normalized accuracy.
- **F/G (sources J/K):** reasoning LLMs plus the historical, truth-tuned four-LLM tie policy
  at cell/cluster level; all 24 tie orders are exported.
- **H (source L):** corrected deterministic low/high windows selected over all B004 cells
  by agreement among the four independent LLM votes. Reference labels and the
  derived historical vote are excluded from eligibility and selection. This is
  a corrected reanalysis, not an exact reproduction of the legacy screenshot,
  whose selector used reference-derived terms.

Generated PNG, PDF, CSV, cache, and provenance artifacts stay local under
`outputs/figure_03/` and remain gitignored.
