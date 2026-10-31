# Figure 2 I/J source boundaries

I uses stored processed marker summaries for modal-annotation CD8+ T groups, including reference-Noise cells. Dot size encodes the fraction of numerical marker values strictly above zero, and color is the group mean scaled per marker. The four-model modal tie order is GPT, Claude, Gemini, DeepSeek.

J uses the fixed descriptive low/high-agreement windows with 1,086 and 915 non-Noise cells. All zoom columns share cells and coordinates. These post-hoc examples were chosen using reference agreement, composition and density. They are not independent validation. They use the annotation-scoring vocabulary, including Paneth to Neuroendocrine, and retain predicted Noise.

Marker rows, selected groups, all-cell locators, exact zoom membership, window counts and the calculation receipt are pinned under `data/frozen/manuscript_replay/figure_02/`. Run `scripts/verify_manuscript_replay.py` for numerical and modal-label checks, and `scripts/render_figure_02_ij_verified.py` for the portable rendering. It verifies pixels outside I/J are preserved in a separate exported Figure 2 copy.
