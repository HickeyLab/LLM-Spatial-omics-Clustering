# Frozen publication inputs

This directory contains small, immutable inputs needed to reproduce the
published analyses from a clean clone. Unlike raw source data and generated
outputs, these files are version-controlled because they define the exact
cell-level partitions used by the manuscript.

See [`v3_k300_assignments/`](v3_k300_assignments/README.md) for the four
source-traced clustering assignments used by Figures 2--4 and Supplementary
Figures S3--S4.

`figure_s03/flowsom_k_sweep_purity.csv` is the hash-locked eight-row source
for Supplementary Figure S3D. It is retained as an archived historical
illustration; its generator is unavailable and it is not equivalent to the
final FlowSOM method.
