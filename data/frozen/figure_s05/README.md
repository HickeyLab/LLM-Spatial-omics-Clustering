# Figure S5C frozen presentation values

These 336 full-precision means are the existing paired compensation effects for
28 cell types, six segmentation methods and two clustering backends. They are
selected from the original `paired_statistics.csv` using `variant=directed_10`
and `population=shared_fixed_objects`. `mean_difference` is F1 after minus F1
before compensation, averaged across contributing B004 tissue regions.
The renderer multiplies the fraction by 100 and retains the original integer
annotations. `n_regions` is retained for provenance.

The original source and original artwork hashes are in
`docs/figure_s05_source_audit.json`. Every original cell background agrees with
its source mean under the original RdBu_r mapping to within one 8-bit RGB unit.
The new display uses RdYlGn with exactly the original symmetric limits and
zero center. Neither p-values nor q-values determine its colors.

The frozen results are unchanged. The renderer does not fit models, rescore
predictions, rerun the regional analysis or perform parameter selection.
