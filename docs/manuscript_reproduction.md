# Reproduce the retained manuscript

The [figure map](figure_map.md), [display crosswalk](../configs/manuscript_display_crosswalk.json) and [table index](supplementary_table_numbering.md) define the current manuscript figures and tables. The [B004 primary annotation bank](../data/frozen/annotation47_results_20261111/manifest.json) and [primary clustering manifest](../data/frozen/clustering47_primary_20261108/manifest.json) pin the primary results and inputs. Figure S6A uses the [47-channel reference-profile manifest](../data/frozen/reference47_profiles_20261110/manifest.json), covering all 27 non-Noise reference types and all 47 stored channels. Reproduction works offline after installing Python dependencies. It makes no model calls or clustering updates. Optional recalibration fits use the frozen development data.

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

The [completed B004 package](revision/reviewer47_completed_publication_20261115.md) contains 71 completed sets, 284 accepted logical requests and 20,076 cluster predictions. It includes the 32-set primary benchmark, the recovered 75-cluster DeepSeek–Leiden selected-means item and eight native OpenAI Batch requests for the two Leiden–Astra controls.

```bash
python3.12 -m pip install -r requirements-reviewer47.txt
python3.12 -B scripts/replay_completed_reviewer47.py \
  --output outputs/reviewer47_completed_replay
```

Use a fresh output path. The replay checks the immutable manifests, re-parses the saved visible answers and recomputes scores for the 69 base conditions and two Astra extensions. It writes the completed counts and verification to `verification.json` and the November 11 replay to `original_snapshot/`. The [complete score table](../data/frozen/astra_prompt_controls_results_20261115/set_metrics.csv) and [seven matched contrasts](../data/frozen/astra_prompt_controls_results_20261115/control_contrasts.csv) record the expected values. The replay uses saved inputs and requires no local H5AD or API key.

To refit the 16 frozen-development logistic calibrators and compare calibration and risk-coverage hashes, use the [November 11 replay](revision/reviewer47_publication_replay.md) with `--recompute-calibration`. Those summaries use the 32 primary B004 sets, which were complete in that snapshot.

The [current B004 and processing table exports](tables/ieee_reviewer47_20261119/manifest.json) match the displayed manuscript tables. The [table index](supplementary_table_numbering.md) links the complete results, donor tables and file-only Table S7. The conventional classifiers use training reference labels. K100/200 coarsening merges existing clusters. Calibration estimates within-donor reference agreement.

## Manuscript artwork and figure generation

The [saved manuscript artwork](../figures/current_manuscript/PNG) uses the current figure numbers, including S14. The [figure and notebook index](../notebooks/final_figures/README.md) maps current figure numbers to stable renderer identifiers and source files. In the native renderer, figures S1–S10 refer to the earlier file identifiers documented in the index.

To render current Figures S2 and S10 from the completed B004 results, use a fresh output directory:

```bash
python3.12 scripts/render_reviewer47_figures.py --output outputs/reviewer47_completed_figures
```

For the other native figure exports, use the renderer identifiers below:

```bash
python3.12 scripts/render_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S10 S11
python3.12 scripts/verify_publication_figures.py --figures 2 3 4 S4 S5 S6 S7 S10 S11
```

The renderer checks input hashes before producing 600 dpi PNG/TIFF and editable SVG/native PDF exports. The [figure map](figure_map.md) identifies the source for each panel. Figure 2E–H uses the original 28-label vocabulary, including Noise. The [Figure 2 scoring bundle](../data/frozen/figure2_native28_20261119/README.md) links the numerical replay for the current manuscript composite and Table S7. Figure S6D uses the original non-Noise labels and Figure S7A uses the original 28-label vocabulary including Noise.

To synchronize verified changed exports into manuscript artwork and notebook previews, use:

```bash
python3.12 scripts/sync_publication_artwork.py --figures 2 3 4 S4 S5 S6 S7 S10 S11
```

This maintenance command updates the native artwork and notebook previews. The saved Google Docs artwork is published under `figures/current_manuscript`.

## Independent compensation analyses

Figures 1, S3, S4 and S5 use the compensation and matching inputs pinned to [Duke record 565](../configs/duke_record_565_manifest.json). The native renderer can reconstruct them from frozen inputs with the identifiers `1 S1 S2 S3A S3B S3C`.

The Figure S6A profiles can be regenerated from the checksum-matched reference H5AD using `scripts/revision/prepare_reference47_profiles.py`. Its arguments specify the H5AD, exact reference-cell keys, protocol and a fresh output directory. The source uses the stored values for the 45 H5AD X channels and the CD123/CDX2 observation channels. The frozen profile CSV is sufficient for ordinary figure replay.

## Completed cross-donor scoring

The [completed B005/B006 score bank](../data/frozen/donor47_deepseek_completion_20261116/README.md) includes the exact frozen references, assignments, profiles, accepted labels, scorer and expected outputs. It delivers all 128 requests and all 9,468 cluster predictions. Run from the repository root with Python 3.12:

```bash
DONOR_BANK=data/frozen/donor47_deepseek_completion_20261116
python3.12 -m pip install -r "$DONOR_BANK/scientific_inputs/requirements.txt"
DONOR_REPLAY=$(mktemp -d)
python3.12 "$DONOR_BANK/scientific_inputs/score_core.py" --bundle "$DONOR_BANK/scientific_inputs" --output "$DONOR_REPLAY/replayed"
```

The scoring replay uses saved labels and frozen classifiers. It requires no credentials or model calls and reproduces the files indexed by the [score manifest](../data/frozen/donor47_deepseek_completion_20261116/score_manifest.json). Figure 5 reports equal-region and equal-donor annotation scores. S12 reports the unchanged clustering results. S13 scores both vocabularies on the same reference-eligible cells. The [saved manuscript PNGs](../figures/current_manuscript/PNG) preserve manuscript layout. The renderer produces editable native exports from the same scores.

To regenerate and verify donor figures and tables, install `requirements-publication-figures.txt` and use the same scratch directory:

```bash
python3.12 scripts/render_donor47_figures.py --figures 5 S12 S13 --output "$DONOR_REPLAY/figures"
python3.12 scripts/verify_publication_figures.py --figures 5 S12 S13 --folder "$DONOR_REPLAY/figures"
python3.12 scripts/revision/render_donor47_tables.py --output "$DONOR_REPLAY/tables"
```

The [November 14 donor bank](../data/frozen/donor47_results_20261114/manifest.json) preserves the original 123 accepted items and 9,093 delivered predictions. Its replay and [table exports](tables/ieee_donor47_20261114/manifest.json) document that historical snapshot. The [current donor table package](tables/ieee_donor47_20261116/manifest.json) follows the saved manuscript.

## Archived entry points

The [publication archive](../data/historical/publication_before_primary47_20261109/index.json) preserves figures, controls, repeatability and table snapshots from earlier revisions. The one-, three- and five-repetition preparation configurations are preserved with the [pre-scoring record](../data/historical/annotation47_pre_scoring_20261110/manifest.json). The completed single-repetition outputs define the current annotation results.

Earlier `render_figure_03_manuscript.py`, `render_figure_04_historical_claude.py` where present, `render_current_tables.py`, `render_figure_s09.py` and revision scripts for donor transfer, means-only replotting and repeated paired decompositions reconstruct archival snapshots. Their labels, vocabularies and model settings can differ from the current study and must not be substituted into active manuscript figures. The same boundary applies to `notebooks/historical_reconstructions`, the prior replay manifest and the unchanged [October 30 release](revision_public_deposition_20261030.md). Archival checksum checks verify preservation, not current scientific results.

The [publication metadata archive](../archive/reviewer47_publication_before_20261111/metadata_index.json) preserves the exact previous Git HEAD records and original financial scope. The artwork archive has its own index. Neither the earlier $77.08 charge record nor its $90 cap represents the enlarged current study; native billing and unresolved attempts remain separately documented in the current execution metadata.
