# Reproduce the retained manuscript

The [active figure inventory](../configs/manuscript_inventory.json), [figure map](figure_map.md) and [table map](supplementary_table_numbering.md) define the current 13 figures and 15 image files. The completed annotation campaign is frozen under [annotation47_results_20261110](../data/frozen/annotation47_results_20261110/manifest.json); primary clustering inputs are separately pinned under [clustering47_primary_20261108](../data/frozen/clustering47_primary_20261108/manifest.json). Figure S4A separately uses the [47-channel reference-profile manifest](../data/frozen/reference47_profiles_20261110/manifest.json), covering all 27 non-Noise reference types and all 47 stored channels. Reproduction is offline after installing Python dependencies. It makes no model calls, fits or clustering updates.

## Current scoring replay

Install Python 3.12 and `requirements-publication-figures.txt`. The scoring replay itself uses NumPy and pandas. Copy the frozen inputs to an ignored output directory so immutable source files remain intact:

```bash
mkdir -p outputs
cp -R data/frozen/annotation47_results_20261110 outputs/annotation47_replay
python3.12 scripts/revision/score_annotation47_completed.py --replay --output outputs/annotation47_replay
```

Use a fresh output directory for each replay. The canonical accepted bank contains 128 logical request items and 9,024 cluster labels across 32 method/model/arm sets. Exact `(File_ID, ID)` joins retain all 220,082 cells. Primary scores use the original 28 labels including Noise and weight the two fixed test regions equally. Fixed-vocabulary macro-F1 assigns zero to absent classes within each region before averaging. Missing or invalid predictions remain in the planned denominator; all final sets were delivered completely. The replay reconstructs cell predictions, regional/pooled metrics, paired contrasts, per-type values, confusion matrices, cluster-bound decompositions and four-method model-consensus CD8+ T profiles.

[The verification record](../data/frozen/annotation47_results_20261110/verification.json) documents source and join checks. [Accepted execution metadata](../data/frozen/annotation47_results_20261110/actual_execution_summary.json) records the actual transports, output ceilings, seeds and amendments, separate from the unchanged disabled preparation. A single accepted output does not imply a single physical generation. Invalid attempts, recoveries, usage and uncertain charge holds remain in the pinned source receipts.

## Current figure generation

```bash
python3.12 scripts/render_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S10 S11
python3.12 scripts/verify_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S10 S11
```

The renderer checks input hashes before producing 600 dpi PNG/TIFF and editable SVG/native PDF exports. The six annotation figures are defined in `scripts/render_annotation47_figures.py`. The clustering-only renderer uses the primary47 bindings. Figures 2E–H retain 20-class non-Noise harmonization, S4D retains original non-Noise diagnostics, and S5A uses all 28 labels including Noise. These populations are distinct from the held-out annotation endpoint.

To synchronize verified changed exports into manuscript artwork and notebook previews, use:

```bash
python3.12 scripts/sync_publication_artwork.py --figures 2 3 4 S4 S5 S6 S7 S10 S11
```

Syncing changes tracked artwork and inventories and is therefore a publication-maintenance command, not necessary for a read-only numerical replay. Final Google Docs placement is checked separately because preview compression and pending image suggestions can differ from native exports.

## Independent compensation analyses

Figures 1, S1, S2 and S3 retain their compensation and matching inputs. Their existing H5AD workflows and compact frozen tables are distinct from the primary cluster annotation study. The external input identities are pinned for [Duke record 565](../configs/duke_record_565_manifest.json). Figure 1B and S1 retain the available source precision rather than claiming recovery of unavailable full-precision metrics. Shared-object matching, coordinate limits and within-donor interpretation remain unchanged. The current renderer can rebuild their published frozen presentations using figure IDs `1 S1 S2 S3A S3B S3C`.

The S4A profiles can also be regenerated from the checksum-matched reference H5AD using `scripts/revision/prepare_reference47_profiles.py`; its arguments specify the H5AD, exact reference-cell keys, protocol and a fresh output directory. The source binds the 45 H5AD X channels plus the CD123/CDX2 observation channels and uses stored values without another transformation. The frozen profile CSV is sufficient for ordinary figure replay.

## Archived entry points

The [publication archive](../data/historical/publication_before_primary47_20261109/index.json) preserves excluded Figure 5/S8/S9, superseded annotation artwork, controls, repeatability and table snapshots. The one-, three- and five-repetition preparation configurations remain byte-preserved; only the completed one-repetition outputs define current annotation results. The [pre-scoring record](../data/historical/annotation47_pre_scoring_20261110/manifest.json) preserves earlier active documentation.

Earlier `render_figure_03_manuscript.py`, `render_figure_04_historical_claude.py` where present, `render_current_tables.py`, `render_figure_s09.py` and revision scripts for donor transfer, means-only replotting and repeated paired decompositions reconstruct archival snapshots. Their labels, vocabularies and model settings can differ from the current study and must not be substituted into active manuscript figures. The same boundary applies to `notebooks/historical_reconstructions`, the prior replay manifest and the unchanged [October 30 release](revision_public_deposition_20261030.md). Archival checksum checks verify preservation, not current scientific results.
