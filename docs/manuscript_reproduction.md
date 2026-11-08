# Reproduce retained manuscript results

The [figure map](figure_map.md) and [table crosswalk](supplementary_table_numbering.md) define the November 6 manuscript display labels. The frozen replay, artwork and scripts retain earlier layouts and complete underlying results. The November 8 clustering-only update redraws Figure 2A–H, S4C–D and S5A from the frozen primary memberships. Other annotation results remain historical pending a separate rerun. Install `requirements-manuscript-replay.txt` with Python 3.12 for the commands below. No API key or network access is needed after installation.

## Retained artwork replay

The figure notebooks verify the retained artwork checksums. Some entry points display it directly, and analytical notebooks keep their existing data requirements. `figures/manuscript/` contains 18 PNG images for Figures 1–5 and S1–S11, with three image parts for S3. Figure 2, S4 and S5 use the frozen primary clustering update. Unchanged annotation artwork remains tied to historical predictions and memberships. The current manuscript ends Figure 2 at H and Figure 3 at E. Figure S11A has byte-preserved native PNG/SVG artwork and a dedicated replay notebook. No PDF or TIFF is asserted for that historical panel.

## Retained numerical replots

```bash
python scripts/verify_manuscript_replay.py
python scripts/render_figure_02_manuscript.py
python scripts/render_figure_03_manuscript.py
python scripts/render_figure_02_celltype_metrics.py
python scripts/render_figure_02_ij_verified.py
python scripts/revision/render_figure_05_red_green.py
python scripts/render_figure_s09.py
python scripts/revision/render_paired_means_fractions.py
python scripts/revision/render_means_only_results.py
python scripts/revision/render_paired_decomposition.py
python scripts/render_current_tables.py
python scripts/update_reference_figure_labels.py --check
```

Current Figure 2 E/G use regional weighted F1 and cell-count-weighted cluster purity. F/H use global cluster-majority F1 and recall. E–H use the same 209,587 non-Noise cells and 20-class harmonization, with alphabetical majority ties. The former I marker profiles are now Figure S11A. Its source is `data/frozen/manuscript_replay/figure_02/panel_I_marker_summaries.csv`. The former J selected spatial windows are archived, with their source records unchanged.

The native Figure 3 caption has A–E, while the stored historical artwork and replay retain A–H. Separate inventory fields record both layouts. The stored image is not a replacement for the reduced native arrangement. B/D use direct reference agreement and C uses cluster-majority upper-bound normalization. E is the spatial comparison formerly labeled H: reference labels, four individual Leiden model predictions and each cluster's most frequent prediction. Ties use GPT, Claude, Gemini and DeepSeek order without reference labels. Earlier reference-informed selection panels remain in the frozen replay as archived analyses and do not define current Figure 3E. Panel A's retained schematic describes retrospective marker-name settings, which are distinct from the numerical benchmark inputs.

Figure 5 replots donor-transfer summaries. S9 replots exploratory calibration and neighborhood summaries. S10 replots the paired 28-label experiment. The means-only and decomposition scripts provide additional presentations of that frozen paired study. These follow-up protocols remain separate from the 21-label historical benchmark in Figures 3–4.

The source tables and compressed cell-level labels are pinned in `data/frozen/manuscript_replay/manifest.json`. Entries record a SHA-256 and their deposited source paths where applicable. Figure 3 metric summaries are derived from the pinned cell labels and assignments, while native table cells and captions retain their earlier snapshot labels. Numerical verification recomputes Figure 2 E–H and the earlier Figure 3 B–G from frozen assignments and cell labels, checks marker-summary arithmetic, archived window membership and most-frequent labels, and paired-repeat means and SDs. These checks do not rerun LLMs or clustering.

The scoped native renderer redraws current Figure 2A–H, S4A–D and S5A–B from checksum-pinned inputs without fitting. Use `python scripts/render_publication_figures.py --figures 2 S4 S5`, `python scripts/verify_publication_figures.py --figures 2 S4 S5 S11` and `python scripts/sync_publication_artwork.py --figures 2 S4 S5`. S11 native PNG/SVG bytes are copied and verified, never scientifically rerendered. Other figures retain their historical exports. The older recovered F/H and I/J utilities patch only their named panels of an exported Figure 2 copy and remain analytical compatibility paths. Other numerical replots preserve values and definitions but may differ in fonts, spacing or layout from approved artwork. Default outputs are beneath `outputs/manuscript_replay/`.

## Retained analytical workflows

Figures S1/S2 retain their original H5AD analyses and historical embedded outputs, with input identities from Duke record 565. The publication renderer uses compact frozen spatial tables and the archived notebook metrics. Figure 1B and S1 retain four-decimal source precision rather than claiming recovery of unavailable full-precision metrics. Figure 1 replays its approved composite and the frozen descriptive D–F effects. Its earlier significance-based H5AD notebook is archived and is not the current display. Figure 4 retains the frozen Leiden–Claude numerical replay and reference-H5AD requirements. Their earlier execution receipts remain historical evidence, and this update does not claim a new full-H5AD execution.

New S3/S4/S5/S6/S7/S8 entry points provide exact artwork replay and links to scientific source in the [October 30 release](revision_public_deposition_20261030.md). They do not claim full numerical reruns. The optional S4 supporting runner retains its legacy `figure_s03` import/config identifiers and documented H5AD requirements. Earlier alternative notebook code is preserved under `notebooks/historical_reconstructions/` and is explicitly outside the current replay.

## Table labels and release integrity

Current supplementary display labels run through S9. The [crosswalk](supplementary_table_numbering.md) identifies printed tables, data-file entries and archived grids. S9 reuses the unchanged former main Table 2 values in `data/frozen/manuscript_replay/tables/current_tables.json` and the deposited donor/equal-donor records. The table renderer retains its earlier native-cell snapshot and labels. The original companion bytes, frozen replay inputs and versioned release archives remain unchanged. Current S2A/B and the12Figure 2conditional comparisons use separately pinned overrides. Historical annotation tables keep their original settings and values.

The [publication design notes](publication_figure_design.md) document physical typography, EXO panel-letter examples, source precision and the difference between submission originals and compressed Google Docs previews.

## Frozen 47-marker clustering scope

[The current contract](../data/frozen/clustering47_primary_20261108/README.md) records full-cohort FlowSOM, SpatialSort100/DMH5 primary seed 42, sensitivity seed 43, and unchanged Leiden/PIXIE memberships. It also distinguishes Figure 2’s 20-class non-Noise scoring, S4D’s raw 27 non-Noise diagnostics and S5A’s raw 28 including Noise bounds. The archived shared UMAP coordinates and historical common 45-marker controls are retained. Execution of the combined annotation protocol remains disabled.
