# Figure 4 frozen historical Claude replay

The canonical notebook is
[`figure_04_leiden_claude_end_to_end.ipynb`](../notebooks/final_figures/figure_04_leiden_claude_end_to_end.ipynb).
The old GPT-named notebook forwards execution to this entry point. Its name
is retained for existing reviewer links. It no longer contains a GPT renderer
or a live inference implementation. The prior reconstruction is preserved in
the local author backup under
`outputs/revision_20261029/figure4_historical_claude_reconciliation/before/`.

The model identity is the historical `leiden__claude` column. Its labels are
already preserved in the checksum-pinned 300-row
[`cluster_counts.csv`](../data/frozen/leiden_claude_diagnostic_identity/cluster_counts.csv),
whose [existing audit](leiden_claude_diagnostic_identity_audit.json) records
verification against the original cell-level source column. The replay expands
those labels through the exact frozen Leiden assignments and joins the
reference H5AD by `(File_ID, ID)`. It never substitutes consensus labels,
later Claude results or newly generated predictions.

The [replay contract](../configs/figure_04_historical_claude.json) pins the
cluster table, count audit, compressed assignments, decompressed assignment
identity and reference H5AD. Every cluster is independently checked against
the reference under both the historical 21-label vocabulary and original 28
labels. The 220,082 keys must be unique and match exactly across inputs.
All eight tissue regions come from donor B004.

For the historical vocabulary, the replay must recover:

| Quantity | Cells |
| --- | ---: |
| Direct reference matches | 123,099 |
| Cluster-majority bound | 157,015 |
| Within-cluster bound gap | 63,067 |
| Net annotation gap | 33,916 |
| Minority-label matches retained | 7,486 |

Historical harmonization includes Paneth to Neuroendocrine, M1 to M2
macrophage and NK to CD7+ Immune. The original-28 comparison uses exactly the
same historical predictions and is a vocabulary-mismatch diagnostic. These
historical results are descriptive reference-agreement measurements on a
retrospectively selected partition. They do not establish biological
correctness or causal attribution of errors to pipeline stages.

The numerical reconstruction contains manuscript panels A–E. Panel A
describes the frozen workflow, B is the row-normalized confusion matrix, C
shows pooled and regional F1, D preserves the three historical example
clusters, and E is the weighted aggregate. The diagnostic labels are Direct
reference agreement (A), Net annotation gap (U − A) and Within-cluster bound
gap (1 − U), where U is the cluster reference-majority fraction. Direct
agreement includes minority-label matches.

The numerical panels are redrawn from data. Exact typography and composition
of the publication artwork remain in the separate versioned preview. The
preview is an output snapshot and is never loaded as an analysis input.

## Run locally

Use the repository's Python 3.12 environment and `requirements.txt`. The
verified reference H5AD is distributed in `CODEX_annotated.zip` from
[Duke record 505](https://research.repository.duke.edu/record/505).
Place `20260130_HuBMAP_experted_annotated.h5ad` under
`data/raw/duke_research_repository/`, or set `FIGURE4_H5AD_PATH` before
launching the notebook. The script accepts `--h5ad` for an alternate path.
No download is initiated automatically.

```bash
python scripts/replay_figure_04_historical_claude.py
```

The notebook and script export PNG panels, a multipage PDF, the frozen
cluster map, the confusion counts, pooled and regional F1 tables, and
`replay_receipt.json` under
`outputs/source_rebuilt/figure_04_historical_claude/`. The receipt records
source and output hashes, both recomputed count summaries, model identity
and zero inference calls, classifier fits and clustering fits. Archived raw
API responses are not re-parsed by this replay. Their historical cell-source
identities remain recorded in the existing count audit.

The published [execution receipt](figure_04_historical_claude_execution.json)
records both entry-point executions, the recomputed counts and independent
metric checks. Full local notebooks and generated figures are retained in the
author workspace. Source notebooks keep empty outputs.
