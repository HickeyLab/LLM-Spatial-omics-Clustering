# Frozen primary clustering publication update

This family updates only membership-dependent, reference-derived diagnostics. It contains no new annotation predictions. `configs/clustering47_publication.json` selects these checksum-pinned inputs without changing the original v3 contracts or deposited release files.

- FlowSOM uses 47 protein markers, three full shuffled passes over all 220,082 B004 cells, seed 42 and 660,246 updates. The requested 300 metaclusters have 299 occupied groups.
- SpatialSort uses 47 protein markers, 100 actual sweeps and `dmh_iter=5`. Seed 42 is primary with 229 occupied groups. Seed 43 is a sensitivity check with 231 groups, never a replacement selected for better scores.
- Leiden and PIXIE memberships are byte-identical to the original frozen assignments.

Figure 2A–H is the current arrangement. D keeps the archived shared UMAP coordinates and recolors the fixed memberships without fitting an embedding. E/G use the 20-class mapping with Paneth mapped to Goblet, exclude reference Noise and assign majorities separately within each region. F/H use one global majority mapping per method. All majority ties are alphabetical. Counts and plotted values are independently checked from the cell-level assignments.

Figure S4A retains its 45-marker reference profiles. S4C uses the original 28 labels including Noise. S4D excludes reference Noise and uses the original 27 remaining labels. Its ARI/AMI plots use all eight regional observations per method. Other S4D plots use pooled cluster or cell-type summaries. Figure S5A uses original 28-label majority bounds including Noise. S5B retains the archived common-45-marker controls and does not run a cluster-count sweep.

Only the 12 `Figure2_EG_12` conditional comparisons and their 96 observations are refreshed. The other 48 comparisons and 384 observations in the combined current companions are retained. The original deposited companions remain unchanged.

Historical annotation scores, bounds, marker profiles and examples continue to use their original memberships and predictions. The native Figure S11A PNG/SVG are byte-preserved historical artwork. Updated annotation results require a separate experiment and are pending. Execution of the planned combined annotation protocol remains disabled.

Reproduce the selected exports without model calls or fitting:

```sh
python scripts/render_publication_figures.py --figures 2 S4 S5
python scripts/sync_publication_artwork.py --figures 2 S4 S5
python scripts/verify_publication_figures.py --figures 2 S4 S5 S11
python scripts/verify_manuscript_replay.py
```

`metrics_receipt.json`, `independent_verification.json` and `per_panel_scoring.json` record the original sources, independent checks, definitions and limitations. These are single-donor reference-informed diagnostics, not evidence of generalization, convergence or biological improvement.
