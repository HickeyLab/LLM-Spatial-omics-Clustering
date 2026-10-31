# Frozen publication inputs

This directory contains small, immutable inputs needed to reproduce the
published analyses from a clean clone. Unlike raw source data and generated
outputs, these files are version-controlled because they define the exact
cell-level partitions used by the manuscript.

See [`v3_k300_assignments/`](v3_k300_assignments/README.md) for the four
source-traced clustering assignments used by Figures 2–4 and current
Supplementary Figures S4/S6. The legacy `figure_s03` module belongs to S4.

`figure_s03/flowsom_k_sweep_purity.csv` is the hash-locked eight-row source
for current Supplementary Figure S4D. It is retained as an archived historical
illustration; its generator is unavailable and it is not equivalent to the
final FlowSOM method.

`manuscript_replay/` supplies compact checksum-pinned tables, frozen cell labels,
fixed spatial windows, current table cells and byte-preserved release companions.
See `docs/manuscript_reproduction.md` for current metrics and replay boundaries.
