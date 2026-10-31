> Current table number: S3. Legacy `table_s02` paths and the audit below retain their original identifiers.

# Table S2 export selection and implementation provenance

Use **retrospective marker-name-list parameter selection** for this table.
The display retains **PIXIE-style export**, defined as the historical source-table
row `PIXIE-style adaptation`. It is not standardized to the main benchmark's PIXIE.
Displayed “V3” headings are removed. Historical version names remain in source
paths and machine-readable provenance only.

## What the sources establish

The twenty selected parameter values exactly match
`threshold_optimization_extended_summary.csv` and `optimized_marker_thresholds.json`.
The matching `optimize_marker_thresholds_extended.py` uses stored 45-marker H5AD
expression and `best_clusters_combined.csv`, specifically its `pixie_cluster`
column. The recorded producer `combined_best_clusters.py` traces that column
to `PIXIE/pixie_meta50_styled_clusters.csv`. The canonical benchmark panel map
explicitly excludes this legacy 50-cluster file and combined-table PIXIE column.
It evaluates name-list exports using the script's rule-based
`annotate_cluster`, with the full reference-labeled cohort used for scoring.
This is a retrospective marker-list procedure, not an LLM request log.
The archived legacy PIXIE name-list JSON has 50 cluster keys. The main manuscript
uses the TIFF-derived PIXIE artifact with 300 occupied clusters. The historical
assignment CSV is currently an iCloud placeholder, and the table's small source
CSV contains no hashed assignment or implementation manifest. Exact equivalence
to the benchmark partition or implementation is therefore not verified. The name
is preserved with that qualification instead of assuming the implementations match.
The canonical benchmark method names are unchanged.

All declared grids and selected numbers are retained. Grid cardinalities are
1,152 for FlowSOM and 960 each for Leiden, SpatialSort and the legacy PIXIE-style
export. The caption describes declared grids and recorded selections. It does
not assert that these selected export settings were used for the original benchmark.

## Archived original prompts

All 179 contributing request records were read from their recorded response or
failure-evidence files and matched against the stored source-file and prompt
SHA-256 values. The parsed 4,584 target profiles each contain 12 high-ranked and
eight low-ranked entries of `[marker, mean_asinh, full_cohort_delta_z]`, with
numerical values in the final two fields. These are numerical marker-expression
profiles, accompanied by task context, rather than short marker-name lists.
The existing source-chain audit identifies the final benchmark maps. This check
verifies their contributing prompt contents without reexecuting any model.

These records do not support the artwork statement “Selected V3 parameters used
for benchmark.” It is replaced by “Recorded marker-name-list export parameters.”
A claim about a particular export setting being used in the original benchmark
would require a verified link from that setting to the archived model-visible
request. No such link is asserted here. The separate controlled revision's
marker-choice experiments are outside the scope of Table S2 and are unchanged.

The frozen evidence is in `data/frozen/table_s02_export_provenance/`. Source hashes
and the exact boundaries of this verification are in `table_s02_export_audit.json`.
Matching Methods, Results, Discussion, limitation and caption wording is in
`table_s02_manuscript_wording.md`. The raw source CSV retains its original
`PIXIE-style adaptation` field and byte checksum for compatibility.

The current table uses the same IEEE-style presentation as S1, retaining all
four parts as editable tables over two pages. All provenance wording and source
values are preserved. See `table_s02_ieee.md` for layout and verification.
