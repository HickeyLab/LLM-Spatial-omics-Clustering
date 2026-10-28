# Publication previews

These PNG files preserve the source-traced publication results and include
reference terminology, verified metric labels and a prompt-provenance workflow
revision. They
are committed so reviewers can inspect the results on GitHub without rerunning
an analysis. Every pixel outside the 45 declared overlay areas is unchanged.

The revised map headings use **Reference annotations**. Confusion-matrix
reference axes use **Reference cell type**. Original dataset labels and
harmonized evaluation labels remain distinct. Biological class names, label
normalization maps, biological class colors, predictions and numerical results are unchanged. Figure 2 E/G now identify
the actual post-hoc selected reference agreement score, and H identifies recall
instead of its historical “Purity” display label. See
[the numerical source audit](../../../docs/figure_02_publication_metrics.md).

Figure 3H uses “Modal predicted label.” Figure 3A separates original numerical
marker-expression profiles and task context from retrospective marker-name-list
exports, which have their own branch. No export-to-LLM arrow is shown. See
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

To reproduce or verify the display-only previews, use the five pinned original
images from Git, frozen original Figure 1/S1/S8 snapshots and the Matplotlib/Pillow
environment:

```bash
python scripts/update_reference_figure_labels.py
python scripts/update_reference_figure_labels.py --check
```

The script validates the original image checksums and rejects changes outside
the declared overlay areas. Patch coordinates and provenance are recorded in
[`reference_figure_label_changes.json`](../../../docs/reference_figure_label_changes.json).
No clustering, metric calculation, or model call is performed.

| Preview | Original SHA-256 | Revised SHA-256 |
| --- | --- | --- |
| `figure_01.png` | `4b1fca30056c35d6bb8cbb14494dca7a73d577e173443c646fa9afaede7b7593` | `1739f07c937f9e18d70fd853ea635e5874a87fc40535294bb67467714da9ce89` |
| `figure_02.png` | `44978280393bac9756e3e826e60a244cf7a2845399635e82df93c0a3f8fb6cd7` | `3754e02fd6edc95132a020c68a196fd86edd5d596a8ff23b8dd9f9795a83c1a9` |
| `figure_03.png` | `cc6f8982a657b92fec5ce5df0e015ddf3620f124447824e950ca33d4b154eeb6` | `fc57a50fbb04388a3cbcc0e0d963c142506f15f457e6cac7c3fc44e912138aa0` |
| `figure_04.png` | `4e9892f2199cb820048bee54ff25a709899cc668a2b39743bbaa6ec63111934e` | `e28a65852072f7e397d0ecd08f58b36d5f16843424310c314bc0ece5939f3cd3` |
| `figure_s01.png` | `5bff24b93d3610eaae5a83bd8303ed52ba56d60c9408235a0715e115ea10c8f4` | `d8ae34fff07fdbccf20c129355a7e48143877d3d34e4e8f3d677453dd7807b75` |
| `figure_s03.png` | `da81d026d78874653de65c50213fb653db54cd7a8229948a84f9d5359a8c1db5` | `737131b62959d8e5a061d8d68eb15f54980a84bce0f3ef082fa8a5333aba8eaa` |
| `figure_s04.png` | `a278669227eea94741308c821b308d4023de3e22ed73e4699179a0e32086504a` | `a45b758a2a0453f2f1cecd78eac369abc6ba682ac97390d3157de6bad26515ad` |
| `figure_s08.png` | `805d5d84b70c3d5c6d0b2c4f02a9a5f185e9b38f70a53a435a9f6747ac6b2168` | `2e122310bf5195939f257f5d255cbd82220e75d194f306b32fb342bddecb6622` |

The unchanged `table_s02.png` SHA-256 is
`98074b1938e30fc0ed137e9b6ebe0d9c0c864a0b1abb3bde6e2ebbbcb7dde1aa`.
