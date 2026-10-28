# Imaged tissue-region analysis units

For publication Figure 1B and S1, the compensation notebook groups independently
by the legacy `slide_name` field and pairs shared identifiers across before and
after conditions. Its matched HuBMAP reference field is `sample_ID`. The eight
B004-A-… identifiers correspond one-to-one to the eight B004 `File_ID` dataset
UUIDs in the workbook-derived repository crosswalk. The File_ID grouping is
also the actual unit used for publication S3E's ARI and AMI calculations.

Use **Tissue-region-level change** and **Mean across tissue regions** in
Figure 1B. Use **Mean across tissue regions** for the three S1 metric panels.
Use **imaged tissue region** for S3E's ARI/AMI black dots. Keep Shannon diversity
and purity cluster-level, and F1/recall cell-type-level. Do not rename the
biological classes or the internal legacy columns/compatibility variables.

These are eight imaged tissue regions from donor B004. The analysis identifiers
do not establish a distinct physical-slide or acquisition-FOV replicate, and no
such extra unit is asserted. The workbook-derived dataset/region crosswalk and
cached-image provenance are in `tissue_region_analysis_units.json`.

S1's caption was present but its image was absent from the current manuscript.
The restored source was recovered from the three existing cached PNG outputs
(cells 16–18) in `figure_s01_clustering_metrics.ipynb`. Those plots were stacked
without recalculating metrics. Only the headings and the already standardized
CellposeCyto3 display name were changed. The cached notebook outputs remain
historical source snapshots. No new clustering or model calls occurred.

Figure 1A and all Figure 1C–F pixels are preserved. The longer B legend is moved
above its plot; the pre-existing vertical whisker crossing the old legend is
preserved at the same position using an adjacent source scanline. All points,
boxes and whisker coordinates and all numerical values remain unchanged. The
reproducible overlay manifest records the exact source/destination rectangles.

## Matching manuscript wording

### Methods analysis units

The clustering input tables contained 220,082 cells from eight imaged tissue regions from one donor. For Figures 1B, S1 and the regional metrics in S3E, one imaged tissue region is one B004 image dataset. The legacy fields slide_name and sample_ID store its B004-A-… region identifier, while File_ID stores the corresponding dataset UUID. These are regional observations within one donor.

### Figure 1B caption

Points show tissue-region-level changes, diamonds show the mean across tissue regions for each method, and boxes summarize the distributions of tissue-region-level changes.

### Figure S1 caption

Gray and blue bars show the mean across tissue regions before and after REDSEA compensation, respectively. Each point represents one imaged tissue region (n = 8), and lines connect paired measurements from the same imaged tissue region.

### Figure S3E caption

(E) Adjusted Rand index and adjusted mutual information computed separately for each of the eight imaged tissue regions (black dots, n = 8).

The previously restored descriptive D–F regional values and a standalone plotting
entrypoint are also committed in `data/frozen/figure_01_descriptive/`. This
distinguishes the current display from the historical notebook volcano outputs.
