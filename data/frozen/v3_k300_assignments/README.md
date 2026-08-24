# Frozen V3 K=300 clustering assignments

These gzip files are byte-preserving compressed copies of the selected V3
cell-assignment CSVs. All four methods were configured with a target of 300
clusters. Leiden, FlowSOM, and PIXIE occupy all 300 labels; SpatialSort
occupies 246 of the 300 configured labels.

Every table contains the same 220,082 unique `(File_ID, ID)` cell keys across
the eight B004 fields of view. The loader verifies the decompressed SHA-256,
row count, exact key coverage, and observed occupied-cluster count before a
table can be used. [`manifest.json`](manifest.json) records the source-traced
method contracts and hashes.

`panel_i_j_four_llm_consensus.csv.gz` stores the deterministic per-cell modal
labels used by the source-traced Panel I and J replays. It is derived from the
16 frozen method-by-model annotation columns using GPT, Claude, Gemini, then
DeepSeek as the tie order; both its source annotation hash and derived CSV hash
are locked in the manifest.

The files are frozen analysis inputs, not claims that the repository can rerun
the original clustering engines without their separately documented external
software and raw inputs.
