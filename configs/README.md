# Configuration

Version-controlled figure contracts live here:

- `figure_02.yaml`: B004 cohort and clustering-method benchmark
- `figure_03.yaml`: LLM annotation benchmark
- `figure_04.yaml`: end-to-end Leiden--GPT evaluation
- `figure_s01.yaml`: Supplementary Figure 1 ground-truth and clustering
  diagnostics
- `figure_s02.yaml`: Supplementary Figure 2 Leiden--GPT count confusion and
  per-cluster accuracy

`figure_s01.yaml` imports the Figure 2 cohort and selected assignments rather
than defining another clustering result. It also hash-locks the recovered
Panel D FlowSOM sweep and preserves its unresolved provenance as `VERIFY:`.

`figure_s02.yaml` imports Figure 4's one selected
OpenAI/reasoning/optimized-Leiden analysis. Its legacy mapping paths and hashes
are reference-audit metadata only and are never used as panel inputs.

Do not add credentials or machine-specific paths.
