# Figure 3 prompt provenance and modal-label terminology

Publication panel A retains the CODEX feature table, clustering icons, model
icons and evaluation graphic. Its central schematic now has two distinct paths:

- Numerical marker-expression profiles and task context feed the original LLM
  prompt/annotation path.
- Retrospective marker-name-list exports have a separate branch, labelled as
  threshold- and marker-count-based exports that do not verify original prompt
  content. There is no arrow from the short-list export to the LLMs.

The old marker-list → optimization → LLM chain is removed. This is a correction
to the explanatory workflow, with no changes to input data, predictions,
parameter settings or results. The distinction follows the manuscript’s source
interpretation in Section 2.10, Section 3.3, Supplementary Note 1 and the caption.
It does not claim that the notebook reconstruction's generated summaries
establish the historical prompts.

Publication panel H uses **Modal predicted label**. This describes the most
frequent predicted label with the existing deterministic tie rule. It does not
claim independently validated consensus. The underlying modal labels and maps
are unchanged, and internal `modal_consensus` keys remain for compatibility.

The reproducible display-overlay manifest records exact rectangles and source
and output hashes. The preview generator verifies that every pixel outside its
declared rectangles remains identical. The canonical notebook schematic also
uses the two separate branches. The historical local production renderers use
the same workflow helper and modal map heading.

## Matching Figure 3 caption wording

Figure 3. Benchmarking large language model cell-type annotation. (A) Workflow showing numerical marker-expression profiles and task context supplied in the original LLM prompts, followed by annotation with GPT-5.6-Sol, Claude Opus 5, Gemini 3.1 Pro Preview or DeepSeek V4 Pro and evaluation against reference labels. Retrospective threshold-based marker-name-list exports are shown on a separate branch and do not establish the original prompt content. (B) Cell-level reference agreement across the 16 raw method-model maps. (C) Reference agreement as a percentage of the cluster-majority upper bound. (D) Cell-type-specific reference agreement for the four models applied to Leiden clusters. (E) Cell-type-specific reference agreement as a percentage of the cluster-majority upper bound. Bars at right in (D) and (E) show reference cell counts. (F–G) We used the known reference labels to select among candidate annotation outputs after prediction. Panel F gives each cell equal weight, while panel G gives each cluster equal weight. Because this selection uses reference labels, it does not measure performance on unlabeled data. (H) Reference and model-predicted spatial maps for representative low- and high-agreement regions. The modal predicted-label map is descriptive and is not an independently validated consensus pipeline. Cell-type colors correspond to Figure 2B. Panel C is recalculated from the verified final maps and fixed-partition majority bounds using Equation (4).
