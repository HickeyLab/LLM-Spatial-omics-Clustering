# Supplementary Figure 2 reproducibility contract

Supplementary Figure 2 expands the end-to-end Leiden--GPT evaluation from
Figure 4:

- A: unnormalized cell-count confusion matrix
- B: per-Leiden-cluster accuracy and upper-bound loss decomposition

The working title remains
`VERIFY: Leiden-GPT count confusion and per-cluster accuracy` because no final
manuscript title was supplied.

## Notebook contract

The notebook is
`notebooks/supplementary/figure_s02_leiden_gpt_diagnostics.ipynb`. It
contains exactly two code cells and no setup or narrative cells:

1. Cell 1 runs Panel A.
2. Cell 2 runs Panel B.

Each cell locates the repository, adds `src/` to the Python path, imports only
its panel runner, and passes the OpenAI key read from `OPENAI_API_KEY`. Neither
cell depends on a variable produced by the other, so either panel can be run
independently in a fresh kernel.

The implementation and frozen panel contract are:

- `src/llm_spatial_omics_clustering/figure_s02.py`
- `configs/figure_s02.yaml`

## Shared Figure 4 dependency

Supplementary Figure 2 does not rerun clustering and does not select a separate
LLM annotation map. Both panels load the single provenance-locked Figure 4
analysis:

- B004 cohort: 220,082 cells from eight `File_ID` regions;
- clustering: Figure 2's fixed 55-cluster Leiden assignment;
- provider and condition: OpenAI with reasoning;
- marker state: optimized;
- reference vocabulary: 21 classes, including 10,495 `Noise` cells; and
- prediction source: the Figure 3 annotation cache selected and locked by
  Figure 4.

The Figure 4 loader validates exact `(File_ID, ID)` keys, cluster coverage,
annotation-map coverage, the response-cache contract, the selected annotation
hash, and the local selection lock. Supplementary Figure 2 records those
fingerprints in each panel's provenance JSON. A changed Figure 3 response
cannot be mixed silently with an earlier Figure 4 or Supplementary Figure 2
panel.

## Credential and execution contract

The checked-in notebook reads `OPENAI_API_KEY` from the environment and falls
back to the literal placeholder `PASTE_OPENAI_API_KEY_HERE`. The placeholder is
intentionally rejected before H5AD or cache access and before any
Supplementary Figure 2 output directory or file is created.

Consequently, the checked-in notebook is deliberately unexecuted and contains
no stored panel output. This is an intentional execution gap, not evidence
that the panels were generated. To execute both cells locally after supplying
a real key:

```bash
cd /Users/zacharydeutsch/Desktop/cell_masks/LLM-Spatial-omics-Clustering
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-figure-s02.txt
export OPENAI_API_KEY='REPLACE_WITH_A_REAL_KEY'
PYTHONPATH=src .venv/bin/python -m jupyter nbconvert \
  --execute --to notebook --inplace \
  notebooks/supplementary/figure_s02_leiden_gpt_diagnostics.ipynb
```

When Jupyter is launched outside the repository, set
`FIGURE_REPOSITORY_ROOT` to the repository's absolute path.

## Legacy composite audit

The supplied screenshot is a layout reference, not a numerical input. Its two
panels were generated with inconsistent legacy annotations:

- Panel A read the legacy workspace file
  `../data/cluster_celltype_leiden.json`. That file is
  byte-identical to the legacy Gemini Leiden map, so the historical panel was
  mislabeled as GPT.
- Panel B read the separate file
  `../data/cluster_celltype_gpt52_leiden.json`. Despite its name, the local
  generator documents that mapping as deterministic marker-driven expert
  logic with no external API call; it is not evidence of a real GPT response.
- The two maps disagree for Leiden clusters 34, 37, and 46: respectively
  Endothelial versus DC, Smooth muscle versus Neuroendocrine, and CD8+ T versus
  Cycling TA.

The legacy mapping paths and SHA-256 hashes are retained in the configuration
for auditability, but neither mapping is an analysis input. Both new panels are
recomputed from Figure 4's one selected OpenAI/reasoning/optimized-Leiden
annotation result. Their values are therefore not expected to reproduce the
mixed legacy screenshot exactly.

## Panel A: cell-count confusion matrix

Panel A uses Figure 4's `confusion_counts` table. Rows are harmonized
ground-truth cell types, columns are GPT-assigned labels for Leiden clusters,
and values are unnormalized cell counts:

\[
C_{a,b} = \#\{i:y_i=a,\ \hat{y}_i=b\}.
\]

The 21-by-21 matrix includes all 220,082 B004 cells, including `Noise` in the
reference-label order. GPT predicts only the 20 biological labels, so a
predicted `Noise` column can be present in the shared matrix order while
containing zero cells. Before rendering, the panel validates the row and
column order, integer counts, matrix shape, and total cell count.

## Panel B: per-cluster accuracy

For each of the 55 Leiden clusters \(k\), let:

- \(p_k\) be the fraction of cells with the cluster's majority truth label;
- \(c_k\) be the fraction whose truth equals the GPT-assigned cluster label.

The displayed components are:

\[
\mathrm{final\_correct}_k = c_k
\]

\[
\mathrm{annotation\_loss}_k = \max(p_k-c_k, 0)
\]

\[
\mathrm{clustering\_loss}_k = 1-p_k.
\]

The three components are nonnegative and sum to one for every cluster. They
are an arithmetic upper-bound decomposition, not mutually exclusive causal
labels assigned to individual cells. The exported component columns are
`final_correct`, `annotation_loss`, and `clustering_loss`.

Rows are sorted by decreasing purity, then decreasing final-correct fraction,
then decreasing cluster size, and finally increasing cluster identifier. Each
row label has the form `Cluster {cluster} - {majority_truth}`. The suffix is
the cluster's majority reference label, not its GPT-predicted label; the
corrected y-axis says `Leiden Cluster and Majority Ground-Truth Label`.

## Generated outputs

After successful execution, each panel writes one audit table, a 300-dpi PNG,
a vector PDF, and a provenance JSON under
`outputs/supplementary/figure_s02/`:

| Panel | Audit table | Figure stem | Provenance |
|---|---|---|---|
| A | `figure_s02a_cell_count_confusion_matrix.csv` | `figure_s02a_cell_count_confusion_matrix` | `figure_s02a_provenance.json` |
| B | `figure_s02b_leiden_cluster_accuracy.csv` | `figure_s02b_leiden_cluster_accuracy` | `figure_s02b_provenance.json` |

Generated files remain local and are ignored by Git. No Supplementary Figure 2
panel is represented as generated until a real key has completed the
provenance-locked Figure 4 dependency.
