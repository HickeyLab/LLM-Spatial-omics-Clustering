# Configuration

Version-controlled figure contracts and small supporting manifests live here:

- `cell_type_colors.csv`: shared manuscript cell-type color map
- `duke_record_565_manifest.json`: published Figure 1/S1/S2 input identities
- `figure_02.yaml`: B004 cohort and clustering-method benchmark
- `figure_s03.yaml`: Supplementary Figure S3 ground-truth and clustering
  diagnostics

`figure_02.yaml` points to the source-traced, versioned K=300 assignment tables
under `data/frozen/v3_k300_assignments/`. `figure_s03.yaml` imports that same
cohort and assignment contract rather than defining another clustering result.
It also hash-locks Supplementary Figure S3 Panel D as an archived historical
FlowSOM sensitivity table with no durable generator; that panel is explicitly
not equivalent to the final FlowSOM method.

Do not add credentials or machine-specific paths.
