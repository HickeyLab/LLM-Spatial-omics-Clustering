# Configuration

Version-controlled figure contracts and small supporting manifests live here:

- `cell_type_colors.csv`: shared manuscript cell-type color map
- `duke_record_565_manifest.json`: published Figure 1/S1/S2 input identities
- `figure_02.yaml`: B004 cohort and clustering-method benchmark
- `figure_s03.yaml`: Supplementary Figure S3 ground-truth and clustering
  diagnostics

`figure_s03.yaml` imports the Figure 2 cohort and selected assignments rather
than defining another clustering result. It also hash-locks the recovered
Panel D FlowSOM sweep and preserves its unresolved provenance as `VERIFY:`.

Do not add credentials or machine-specific paths.
