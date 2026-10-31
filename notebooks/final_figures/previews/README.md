# Publication previews

These PNG files preserve the source-traced publication results and include
reference terminology, verified metric labels and the restored original Figure 3A
workflow. They are committed so reviewers can inspect the results on GitHub without rerunning
an analysis. Nine previews preserve every pixel outside 53 declared overlay
areas. Figures S5C and S7 are separately rendered from 336 and 32 frozen results
with their revised palettes and labels. All numerical values are retained.
Table S1 is a verified IEEE-style rendering of the current editable manuscript
table, with all 45 cells and all caption words preserved during formatting.
The current S2 style is shown in `table_s02_ieee_page_1.png` and
`table_s02_ieee_page_2.png`; the earlier `table_s02.png` remains the historical
label-overlay snapshot for reproducibility.

The revised map headings use **Reference annotations**. Confusion-matrix
reference axes use **Reference cell type**. Original dataset labels and
harmonized evaluation labels remain distinct. Biological class names, label
normalization maps, biological class colors, predictions and numerical results are unchanged. Figure 2 E/G now identify
the actual post-hoc selected reference agreement score, and H identifies recall
instead of its historical “Purity” display label. See
[the numerical source audit](../../../docs/figure_02_publication_metrics.md).

Figure 3H uses “Modal predicted label.” Figure 3A retains the original
Cluster Features -> Optimization schematic restored in the manuscript. See
[the workflow notes](../../../docs/figure_03_workflow_and_modal_labels.md).

Figures 4D–E and S4B are explicitly Historical majority-based diagnostic
displays. Figure S8 states the corrected aggregate identity. Component labels
are Direct reference agreement, Net annotation gap and Within-cluster bound
gap, matched to the source calculations and retaining minority-label matches.
See [the calculation audit](../../../docs/diagnostic_identity_labels.md).

Figure 1B and S1 use tissue-region terminology for the same eight B004 image
datasets. S3E explicitly identifies only ARI/AMI dots as imaged tissue regions.
S1 was absent from the current manuscript and was recovered from three cached
notebook plot outputs without recalculating metrics. Figure 1A and C–F are
preserved. See [the analysis-unit crosswalk and source notes](../../../docs/tissue_region_analysis_units.md).

S3A and 2I use source-verified strict stored processed `X > 0.0` fractions
for dot size, with min–max-scaled group means identified separately for color.
These operational fractions do not establish biological marker positivity. See
[the threshold and preprocessing audit](../../../docs/marker_expression_thresholds.md).

These previews are not notebook execution state or reconstruction inputs.
The parent notebooks and input contracts still govern analytical regeneration.
The current notebooks may reconstruct panels differently from the historical
publication composites, as documented in their existing provenance records.

To reproduce or verify the display-only previews, use the six pinned original
images from Git, frozen original Figure 1/S1/S8 snapshots and the Matplotlib/Pillow
environment:

```bash
python scripts/update_reference_figure_labels.py
python scripts/update_reference_figure_labels.py --check
python scripts/render_figure_s05.py --check
python scripts/render_figure_s07.py --check
```

The script validates the original image checksums and rejects changes outside
the declared overlay areas. Patch coordinates and provenance are recorded in
[`reference_figure_label_changes.json`](../../../docs/reference_figure_label_changes.json).
No clustering, metric calculation, or model call is performed.

| Preview | Original SHA-256 | Revised SHA-256 |
| --- | --- | --- |
| `figure_01.png` | `4b1fca30056c35d6bb8cbb14494dca7a73d577e173443c646fa9afaede7b7593` | `1739f07c937f9e18d70fd853ea635e5874a87fc40535294bb67467714da9ce89` |
| `figure_02.png` | `44978280393bac9756e3e826e60a244cf7a2845399635e82df93c0a3f8fb6cd7` | `3754e02fd6edc95132a020c68a196fd86edd5d596a8ff23b8dd9f9795a83c1a9` |
| `figure_03.png` | `cc6f8982a657b92fec5ce5df0e015ddf3620f124447824e950ca33d4b154eeb6` | `8721c28b3950b8b7caf8feee3505fb4bf84e152760b64cbe0558e393c0ef60a2` |
| `figure_04.png` | `4e9892f2199cb820048bee54ff25a709899cc668a2b39743bbaa6ec63111934e` | `e28a65852072f7e397d0ecd08f58b36d5f16843424310c314bc0ece5939f3cd3` |
| `figure_s01.png` | `5bff24b93d3610eaae5a83bd8303ed52ba56d60c9408235a0715e115ea10c8f4` | `d8ae34fff07fdbccf20c129355a7e48143877d3d34e4e8f3d677453dd7807b75` |
| `figure_s03.png` | `da81d026d78874653de65c50213fb653db54cd7a8229948a84f9d5359a8c1db5` | `737131b62959d8e5a061d8d68eb15f54980a84bce0f3ef082fa8a5333aba8eaa` |
| `figure_s04.png` | `a278669227eea94741308c821b308d4023de3e22ed73e4699179a0e32086504a` | `994df7cee194c8bfaf116f83bf2722b31ab1e38963b763e4d8c27b7630032d6a` |
| `figure_s05c.png` | `2ca554e61b4767320b768e34884012fc1ecd16391b38ab669ec7efb5be4d4418` | `888324f25bd14f7075e76292b15006212241f6b0f4da117fdf3423ee2e535bd4` |
| `figure_s07.png` | `41190b2a5494d5591c52188e108011805b01baac0ec9fe49f4467a83dbcb507c` | `ffd6e1ce525c37ecde107c1a9d85f62c83a40bc3dd7981aae0dd9e4a6748452d` |
| `figure_s08.png` | `805d5d84b70c3d5c6d0b2c4f02a9a5f185e9b38f70a53a435a9f6747ac6b2168` | `97c63d6c0a5f020b3eadab4379811cee8b13edd9b8e3827e430f3589c9c6b559` |
| `table_s02.png` | `98074b1938e30fc0ed137e9b6ebe0d9c0c864a0b1abb3bde6e2ebbbcb7dde1aa` | `4a7df43e70a1c0a1bf4a03f469c810dc8a0644d07ac0fa7a77ef3d4f6fee9bd1` |

Table S2 uses retrospective marker-name-list parameter selection, removes
displayed version shorthand and identifies recorded export settings. Its legacy
PIXIE-style export remains distinct from the benchmark PIXIE implementation.
The original numerical prompt records do not verify use of the selected export
parameters. See [the source and prompt audit](../../../docs/table_s02_export_provenance.md).

Figure S7 uses Marker-only and Reference-assisted, with labeled reference
profiles described separately. Reference agreement (%) retains missing and
invalid predictions in the planned denominator. Both panels share Figure 2H’s
RdYlGn palette and fixed 0–100% scale. Its frozen table, score definition and
standalone renderer are documented in
[the S7 source notes](../../../docs/figure_s07_condition_labels.md).

Figure S5C uses the same RdYlGn family, with the original symmetric limits
centered on zero for signed changes in F1. Both backends share the same scale.
S5A/B categorical series colors are preserved. See
[the S5 palette and source notes](../../../docs/figure_s05_color_scale.md).

Table S1 matches the supplied IEEE-style example with Times New Roman, a
centered caption above, explanatory notes below, horizontal rules and no
shading or vertical borders. Its editable DOCX and native HTML are generated
from the current manuscript cells. See
[the S1 presentation notes](../../../docs/table_s01_presentation.md).

Table S2 uses the same IEEE-style convention across two readable, editable
pages. All 135 cells and the provenance notes are preserved. See
[the S2 presentation notes](../../../docs/table_s02_ieee.md).

Figure-level titles have been removed from the S4, S7 and S8 previews. Panel headings and labels remain. The complete current manuscript set, using the reconciled S1–S10 numbering, is available in [`figures/manuscript/`](../../../figures/manuscript/README.md).
