# Figure 2 F/H cell-type metrics

F shows F1 as fractions and H shows recall as percentages, with reference cell counts. Both use one global reference-majority map per fixed clustering method across eight regions, the same non-Noise cells, the 20-class vocabulary and alphabetical ties. This differs intentionally from the regional E/G mappings.

The pinned `celltype_metrics.csv`, F/H panel tables, majority maps and calculation receipt are under `data/frozen/manuscript_replay/figure_02/`. `scripts/verify_manuscript_replay.py` checks all 160 values. `scripts/render_figure_02_celltype_metrics.py` exports updated F/H while verifying that pixels outside those panels are preserved in the exported copy. The default source is the current approved Figure 2. The manuscript file is never written.
