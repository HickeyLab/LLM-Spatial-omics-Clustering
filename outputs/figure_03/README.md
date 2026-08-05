# Figure 3 outputs

Generated only by `notebooks/main/figure_03_llm_annotation_benchmark.ipynb`.

The publication page contains eight retained panels labeled A–H. Their source
notebook IDs remain historical A, F, G, H, I, J, K, and L respectively, so the
source notebook still contains one code cell per source panel, ordered A
through L. The retained LLM-dependent source panels require real provider API
keys and refuse the checked-in environment-variable fallbacks before reading
caches or creating outputs. Never paste a real key into the tracked notebook.

All biological panels consume the exact Figure 2 selected clustering
assignments, including the image-native 50-cluster TIFF PIXIE artifact.

Generated PNG/PDF files, supporting tables, response caches, and provenance
records remain local and gitignored. Recreate them from the relevant notebook
cell rather than committing generated artifacts or credentials.

The exact historical DeepSeek V3.2 model identifiers were retired on
2026-07-24. Four-provider panels therefore require matching historical
DeepSeek cache entries; otherwise they stop before any active-provider API
call. A newer DeepSeek model would constitute a separately approved analysis.
