# Figure 4 outputs

Generated only by `notebooks/main/figure_04_leiden_gpt_end_to_end.ipynb`.

The notebook contains one code cell per panel, ordered A through F. Panel A is
a local workflow schematic. Panels B--F require a real `OPENAI_API_KEY` and
refuse the checked-in placeholder before reading data, caches, or creating
outputs.

All biological panels reuse the single Figure 3 optimized, reasoning-enabled
OpenAI annotation for Figure 2's 55 fixed Leiden clusters. They evaluate all
220,082 B004 source cells, including 10,495 reference-label Noise cells. This
full-cohort universe intentionally differs from Figure 3's non-Noise benchmark
metrics.

The first successful biological-panel run writes a local Figure 4 selection
lock. Later cells refuse an annotation mapping whose model, prompt, marker
summary, cache contract, or annotation hash differs from that lock.

Generated PNG/PDF panels, supporting CSV tables, and provenance records remain
local and gitignored. The displayed legacy percentages are never hard-coded.
