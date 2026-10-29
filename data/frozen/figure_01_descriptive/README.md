# Figure 1D–F descriptive display values

These are the previously prepared regional F1 differences used for the current
Figure 1D–F manuscript display. There are 663 paired region/cell-type rows,
84 method/cell-type summaries and 28 cell types, across the eight B004 regions.
The input-matching hashes and historical pairing rules are in `source_receipt.json`.
No values are selected by p-values. Gray dots show individual regional changes,
black diamonds show the mean and gray lines show the observed regional range.
An absent cell type in one condition is excluded by the historical inner pairing,
so n can be below eight. The n labels report the actual number of paired regions.

The historical Figure 1 notebook retains its old volcano implementation and cached
plots as source records. The current composite is frozen separately in
`data/frozen/publication_artwork/figure_01_original.png` and receives only the
Figure 1B unit-label overlay. To render the current descriptive D–F values as a
standalone view, run:

```bash
python scripts/plot_figure_01_regional_effects.py --output outputs/figure_01/regional_effects
```

This reads the frozen regional table and does not run clustering, matching,
significance tests or model calls. It preserves biological class names.
