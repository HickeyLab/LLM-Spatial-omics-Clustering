# Reproduce the retained manuscript

The [active figure inventory](../configs/manuscript_inventory.json), [figure map](figure_map.md) and [table map](supplementary_table_numbering.md) define the current 15 figures and 17 image files. The completed annotation campaign is frozen under [annotation47_results_20261111](../data/frozen/annotation47_results_20261111/manifest.json); primary clustering inputs are separately pinned under [clustering47_primary_20261108](../data/frozen/clustering47_primary_20261108/manifest.json). Figure S4A separately uses the [47-channel reference-profile manifest](../data/frozen/reference47_profiles_20261110/manifest.json), covering all 27 non-Noise reference types and all 47 stored channels. Reproduction is offline after installing Python dependencies. It makes no model calls or clustering updates. Optional recalibration fits use the frozen development data only.

## Current scoring replay

Install Python 3.12 and `requirements-publication-figures.txt`. The scoring replay itself uses NumPy and pandas. Copy the frozen inputs to an ignored output directory so immutable source files remain intact:

```bash
mkdir -p outputs
cp -R data/frozen/annotation47_results_20261111 outputs/annotation47_replay
python3.12 scripts/revision/score_annotation47_completed.py --replay --output outputs/annotation47_replay
```

Use a fresh output directory for each replay. The canonical accepted bank contains 128 logical request items and 9,024 cluster labels across 32 method/model/arm sets. Exact `(File_ID, ID)` joins retain all 220,082 cells. Primary scores use the original 28 labels including Noise and weight the two fixed test regions equally. Fixed-vocabulary macro-F1 assigns zero to absent classes within each region before averaging. Missing or invalid predictions remain in the planned denominator; all final sets were delivered completely. The replay reconstructs cell predictions, regional/pooled metrics, paired contrasts, per-type values, confusion matrices, cluster-bound decompositions and four-method model-consensus CD8+ T profiles.

[The verification record](../data/frozen/annotation47_results_20261111/verification.json) documents source and join checks. [Current execution metadata](revision/reviewer47_execution_summary_20261111.json) records the actual transports, output ceilings, seeds and amendments, separate from the unchanged disabled preparation. A single accepted output does not imply a single physical generation. Invalid attempts, recoveries, usage and uncertain charge holds remain in the pinned source receipts.

## Reviewer controls and recalibration replay

The [portable replay instructions](revision/reviewer47_publication_replay.md) bind the completed primary bank, all 69 planned reviewer sets and safe visible-response evidence. They verify all 276 literal request bodies and strictly re-parse the 275 accepted answers before opening reference values:

```bash
python3.12 -m pip install -r requirements-reviewer47.txt
python3.12 -B scripts/replay_reviewer47_publication.py \
  --output outputs/reviewer47_replay_fresh \
  --recompute-calibration
```

Use a new output path. Sixty-eight reviewer sets are complete. DeepSeek–Leiden selected numerical means retains its pending 75-cluster item, null accuracy and macro-F1, and all planned denominators. The two Astra control sets add eight pending Batch items and contribute no plotted result. B005/B006 and the private HIGH/XHIGH pilot are excluded. No aggregate silently removes an incomplete condition.

The replay recomputes per-set metrics and the five completed Opus contrasts with independent Counter arithmetic, compares the 32 primary conditions against the same admitted full-arm bank, and optionally refits the 16 frozen-development logistic calibrators. With recalibration enabled, its split and calibration/risk CSV hashes must match the frozen export. Marker selection and literal neighborhood vectors are already present in the published request bodies; no original H5AD is needed for this replay.

IEEE table exports are regenerated from checked tables, retaining explicit pending cells:

```bash
python3.12 scripts/revision/render_reviewer47_tables.py \
  --output outputs/reviewer47_ieee_replay
```

The current S6a–d, S8a–d, S9, S10, S11 and S12a–d display tables are under [ieee_reviewer47_20261111](tables/ieee_reviewer47_20261111/manifest.json), rather than embedded in the primary result folder. S1, S2A/B and S7 retain their separately documented inputs. The new conventional classifiers use richer reference-label training supervision; coarsening is post-clustering rather than native-K fitting; calibration is retrospective within-donor reference agreement, not native confidence or repeated-call consistency.

## Current figure generation

```bash
python3.12 scripts/render_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S8 S9 S10 S11
python3.12 scripts/verify_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S8 S9 S10 S11
```

The renderer checks input hashes before producing 600 dpi PNG/TIFF and editable SVG/native PDF exports. The primary annotation figures are defined in `scripts/render_annotation47_figures.py`; S8 and S9 use `scripts/render_reviewer47_figures.py` and the separate reviewer result manifest. Figure 4 and S6 preserve their rendered scientific bytes, with current-bank equivalence verified for all 24 non-DeepSeek full-arm conditions. The clustering-only renderer uses the primary47 bindings. Figures 2E–H retain 20-class non-Noise harmonization, S4D retains original non-Noise diagnostics, and S5A uses all 28 labels including Noise. These populations are distinct from the held-out annotation endpoint.

To synchronize verified changed exports into manuscript artwork and notebook previews, use:

```bash
python3.12 scripts/sync_publication_artwork.py --figures 2 3 4 S4 S5 S6 S7 S8 S9 S10 S11
```

Syncing changes tracked artwork and inventories and is therefore a publication-maintenance command, not necessary for a read-only numerical replay. Final Google Docs placement is checked separately because preview compression and pending image suggestions can differ from native exports.

## Independent compensation analyses

Figures 1, S1, S2 and S3 retain their compensation and matching inputs. Their existing H5AD workflows and compact frozen tables are distinct from the primary cluster annotation study. The external input identities are pinned for [Duke record 565](../configs/duke_record_565_manifest.json). Figure 1B and S1 retain the available source precision rather than claiming recovery of unavailable full-precision metrics. Shared-object matching, coordinate limits and within-donor interpretation remain unchanged. The current renderer can rebuild their published frozen presentations using figure IDs `1 S1 S2 S3A S3B S3C`.

The S4A profiles can also be regenerated from the checksum-matched reference H5AD using `scripts/revision/prepare_reference47_profiles.py`; its arguments specify the H5AD, exact reference-cell keys, protocol and a fresh output directory. The source binds the 45 H5AD X channels plus the CD123/CDX2 observation channels and uses stored values without another transformation. The frozen profile CSV is sufficient for ordinary figure replay.

## Archived entry points

The [publication archive](../data/historical/publication_before_primary47_20261109/index.json) preserves the excluded Figure 5 and earlier S8/S9, annotation artwork, controls, repeatability and table snapshots. The active S8/S9 are newly rendered from the current reviewer export. The one-, three- and five-repetition preparation configurations remain byte-preserved; only the completed one-repetition outputs define current annotation results. The [pre-scoring record](../data/historical/annotation47_pre_scoring_20261110/manifest.json) preserves earlier active documentation.

Earlier `render_figure_03_manuscript.py`, `render_figure_04_historical_claude.py` where present, `render_current_tables.py`, `render_figure_s09.py` and revision scripts for donor transfer, means-only replotting and repeated paired decompositions reconstruct archival snapshots. Their labels, vocabularies and model settings can differ from the current study and must not be substituted into active manuscript figures. The same boundary applies to `notebooks/historical_reconstructions`, the prior replay manifest and the unchanged [October 30 release](revision_public_deposition_20261030.md). Archival checksum checks verify preservation, not current scientific results.

The [publication metadata archive](../archive/reviewer47_publication_before_20261111/metadata_index.json) preserves the exact previous Git HEAD records and original financial scope. The artwork archive has its own index. Neither the earlier $77.08 charge record nor its $90 cap represents the enlarged current study; native billing and unresolved attempts remain separately documented in the current execution metadata.
