# Reproduce the current manuscript outputs

The inventory and exact artwork were checked against the October 31 manuscript export. The manuscript is unchanged. Install `requirements-manuscript-replay.txt` with Python 3.12 for the commands below. No API key or network access is needed after installation.

## Exact artwork replay

The current figure notebooks verify the approved artwork checksums. The new entry points display it directly, and the retained analytical notebooks keep their existing data requirements. `figures/manuscript/` contains all 17 images for Figures 1–5 and S1–S10. Copying or displaying these images verifies artwork only.

## Numerical replots

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

Figure 2 E/G use regional weighted F1 and cell-count-weighted cluster purity. F/H use global cluster-majority F1 and recall. E–H use the same 209,587 non-Noise cells and 20-class harmonization, with alphabetical majority ties. I uses processed marker measurements and the four-model modal annotations. J retains the fixed 1,086-cell and 915-cell windows and the published selection limits.

Figure 3 has A–H. B–E use direct reference agreement and cluster-majority upper-bound normalization. F/G retain reference-informed selection after prediction, with cells or clusters weighted equally, respectively. H displays reference, four individual Leiden model predictions and their modal prediction. Model-order ties use GPT, Claude, Gemini, DeepSeek. Panel A is approved original workflow artwork.

Figure 5 replots donor-transfer summaries. S9 replots exploratory calibration and neighborhood summaries. S10 replots the paired 28-label experiment. The means-only and decomposition scripts provide additional presentations of that frozen paired study. These follow-up protocols remain separate from the 21-label historical benchmark in Figures 3–4.

The source tables and compressed cell-level labels are pinned in `data/frozen/manuscript_replay/manifest.json`. Entries record a SHA-256 and their deposited source paths where applicable. Figure 3 metric summaries are derived from the pinned cell labels and assignments, while native table cells and captions come from the checked manuscript snapshot. Numerical verification independently recomputes Figure 2 E–H and Figure 3 B–G from frozen assignments and cell labels, checks marker-summary arithmetic, fixed-window membership/modal labels, and paired-repeat means and SDs. These checks do not rerun LLMs or clustering.

The recovered F/H and I/J renderers patch only their named panels of an exported Figure 2 copy. Other numerical replots preserve values and definitions but may differ in fonts, spacing or layout from approved artwork. Default outputs are beneath `outputs/manuscript_replay/`.

## Retained analytical workflows

Figures S1/S2 retain their original H5AD analyses and historical embedded outputs, with input identities from Duke record 565. Figure 1 replays its approved composite and the frozen descriptive D–F effects. Its earlier significance-based H5AD notebook is archived and is not the current display. Figure 4 retains the frozen Leiden–Claude numerical replay and reference-H5AD requirements. Their earlier execution receipts remain historical evidence, and this update does not claim a new full-H5AD execution.

New S3/S4/S5/S6/S7/S8 entry points provide exact artwork replay and links to scientific source in the [October 30 release](revision_public_deposition_20261030.md). They do not claim full numerical reruns. The optional S4 supporting runner retains its legacy `figure_s03` import/config identifiers and documented H5AD requirements. Earlier alternative notebook code is preserved under `notebooks/historical_reconstructions/` and is explicitly outside the current replay.

## Table labels and release integrity

Current table headings use S1–S8. The [crosswalk](supplementary_table_numbering.md) preserves the relationship to deposited filenames. Companion bytes and the versioned release archives remain unchanged. This repository update adds omitted plotting scripts and compact replay inputs, rather than replacing the immutable scientific release.
