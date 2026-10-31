# Repository synchronization audit — 2026-10-29

The default branch and the active revision branch contain different versions.
At this audit, `main` was `c24ef05344a9fd008d2586d03b1707dbc29d4f77`.
[Draft PR #20](https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/pull/20)
was based on `codex/reference-figure-labels`, with pre-update head
`7229812c1432396d8a6fcc20350376c1c5352859`. That head was 15 commits and 97
changed paths ahead of `main`. Publication in a PR branch does not mean the
changes are present on the default branch.

## Included in this update

- Figure 4 now uses the audited frozen historical Claude cluster-label map.
  The canonical notebook is `figure_04_leiden_claude_end_to_end.ipynb`, and
  the old GPT-named link forwards to it. Root and notebook indexes agree.
- Replay provenance pins the count audit, label map, exact Leiden assignments
  and reference H5AD. Both notebook entry points reconstruct all 220,082 cells,
  retain 7,486 minority-label matches and recover 123,099 direct matches.
  See [the execution receipt](figure_04_historical_claude_execution.json).
- The repository's H5AD digest was missing its final hexadecimal character.
  The downloader, relevant figure contracts, embedded notebook checks and
  associated tests now use the complete verified 64-character SHA-256:
  `5d0a59d1e7866dee5a3a06772c3c80ce7328ba6420bc140708be5ec451b8a49a`.
  This corrects file validation without changing the reference data.
- The existing revision branch's updated publication previews and terminology
  are preserved. Older local copies were not copied over those changes.

## Already on the revision branch, awaiting merge into main

The pre-existing PR includes publication terminology and interpretation fixes,
historical Leiden–Claude diagnostic labels, tissue-region definitions, marker
summary provenance, S5/S7 palettes, restored descriptive Figure 1 outputs and
editable IEEE-style S1/S2 table assets. These 15 commits remain subject to the
PR's review and merge status.

## Newer local work still absent from the revision branch

| Area | Evidence in the local revision | Remaining GitHub work |
| --- | --- | --- |
| Current Figure 2 E/G | `build_figure_02_regional_clustering_metrics.py`, `docs/figure_02_regional_metrics.md` and a saved regional-metric package | Replace the superseded selector panels with the verified regional weighted F1 and purity outputs. Merge current definitions and frozen input/output evidence into the existing branch without reverting its terminology fixes. |
| Figure 2 F/H | `render_figure_02_celltype_metrics.py`, `verify_figure_02_celltype_metrics.py` and `docs/figure_02_celltype_metrics.md` | Publish the verified global majority mapping, F1/recall calculation, support counts and current artwork. |
| Figure 2 I/J | `render_figure_02_ij_verified.py`, `verify_figure_02_ij_sources.py` and `docs/figure_02_ij_sources.md` | Package the current marker-summary and fixed-window source checks and align the notebook's alternative panels with the manuscript. |
| Controlled four-model study and donor transfer | `scripts/revision/four_llm_followup.py`, related scoring/verification code and the local integrated revision notebook | Release a coherent, offline-replayable source and frozen-evidence package. The current public notebook collection has no Figure 5 donor-transfer entry point. |
| Paired marker means versus fractions | `scripts/revision/paired_means_fractions.py`, scorer, decomposition and tests | Publish the registered protocol, versioned source and compact verified results with the relevant input manifests. |
| Conditional comparative statistics | `scripts/revision/hybrid_comparative_statistics.py` and its saved 60-comparison summary | Release the frozen comparison families, paired observations, conditional interpretation and compact result tables. |
| Calibration and spatial-neighborhood follow-up | `uncertainty_spatial.py`, scoring/verification code and the saved calibration/spatial package | Release source, frozen predictions and compact tables/figure with the documented exploratory limits. |
| Current supplemental figures/tables | Local Figure 5 palette update, Figure S9 and Tables S4/S5 extensions | Add current source contracts, previews and reader-facing navigation after aligning them with the final manuscript inventory. |
| Manuscript and response state | Current manuscript exports, pending suggestions, response ledger and October 29 citation audit | Synchronize a final release snapshot and response status. Do not equate pending Google Docs suggestions with accepted text. Original correspondence and author-side account records are not needed for the public code release. |

These are presence/version gaps, not a claim that every local file is final,
ready for publication or independently reproduced by this audit. Some local
manuscript cross-references are still being reconciled. The GitHub code and
figure numbering should follow the final agreed manuscript inventory.

## Audit coverage and uncertainty

The pre-update inventory examined 309 local source/configuration/test/notebook,
documentation and compact frozen-input paths. Of those, 228 paths were absent
from the revision branch, including the Figure 4 files added by this update.
Ninety resident file contents were compared, with 17 differences from the
revision branch. Some differences were older local copies of newer GitHub
fixes. In addition, 70 revision-branch paths were absent from the local source
tree. The local directory must therefore be reconciled rather than uploaded
wholesale.

The other 219 inventoried local paths were cloud placeholders. Their existence
and sizes were checked, but their contents were not assumed to match GitHub.
Acquired raw data, generated output trees, caches and temporary files were
excluded from the blanket source-file counts. Selected output inventories and
resident receipts were inspected to identify the backlog above. This audit did
not rerun those studies or validate every missing artifact. Full per-path
comparison evidence is retained in the author workspace.

## Keep the sources synchronized

For each completed manuscript or figure change, update its source, notebook
entry point, compact frozen inputs, labels, provenance and focused validation
on the revision branch in the same release. Recheck current remote HEAD before
pushing and keep a scoped commit. Report whether the result is on a PR branch
or merged into `main`. Keep raw acquired data in the documented deposit and
publish small source manifests and replay inputs in Git. Update this backlog
as each research package is released.
