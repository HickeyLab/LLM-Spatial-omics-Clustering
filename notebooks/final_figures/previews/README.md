# Publication previews

These PNG files preserve the validated source-traced publication results and
include a display-label revision for reference-annotation uncertainty. They
are committed so reviewers can inspect the results on GitHub without rerunning
an analysis. Every pixel outside the nine declared label areas is unchanged.

The revised map headings use **Reference annotations**. Confusion-matrix
reference axes use **Reference cell type**. Original dataset labels and
harmonized evaluation labels remain distinct. Biological class names, label
normalization maps, legends, predictions, and numerical results are unchanged.

These previews are not notebook execution state or reconstruction inputs.
The parent notebooks and input contracts still govern analytical regeneration.
The current notebooks may reconstruct panels differently from the historical
publication composites, as documented in their existing provenance records.

To reproduce or verify the label-only previews, use the pinned original images
from Git and the Matplotlib/Pillow environment:

```bash
python scripts/update_reference_figure_labels.py
python scripts/update_reference_figure_labels.py --check
```

The script validates the original image checksums and rejects changes outside
the declared text areas. Patch coordinates and provenance are recorded in
[`reference_figure_label_changes.json`](../../../docs/reference_figure_label_changes.json).
No clustering, metric calculation, or model call is performed.

| Preview | Original SHA-256 | Revised SHA-256 |
| --- | --- | --- |
| `figure_02.png` | `44978280393bac9756e3e826e60a244cf7a2845399635e82df93c0a3f8fb6cd7` | `655b8b3a844c608b4bf767101f7b282855ed9f562da82434292434b3fcd38c75` |
| `figure_03.png` | `cc6f8982a657b92fec5ce5df0e015ddf3620f124447824e950ca33d4b154eeb6` | `6d2e2e744e20c3dc1ebaccdcb54d557dd8624327b1abc160da7786a3b350bbc0` |
| `figure_04.png` | `4e9892f2199cb820048bee54ff25a709899cc668a2b39743bbaa6ec63111934e` | `4a69bc025a8ce8125520627697b1f584c89a66bdf0632b2d49ed9b598fc41115` |
| `figure_s03.png` | `da81d026d78874653de65c50213fb653db54cd7a8229948a84f9d5359a8c1db5` | `8cd3209e6e846cd71fb538e6d6184c8661516cbee7b77cb6da2ec8694b87306c` |
| `figure_s04.png` | `a278669227eea94741308c821b308d4023de3e22ed73e4699179a0e32086504a` | `344e9823bad0da078d8eb0aa6f8bdf4ba3aed56cf4d63a2da8fd14ac46ffc2c7` |

The unchanged `table_s02.png` SHA-256 is
`98074b1938e30fc0ed137e9b6ebe0d9c0c864a0b1abb3bde6e2ebbbcb7dde1aa`.
