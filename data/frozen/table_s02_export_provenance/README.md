# Table S2 historical export evidence

`historical_extended_search_summary.csv` contains the archived search selections.
All twenty selected values match the unchanged Table S2 source CSV.
`legacy_pixie_marker_name_lists.json` contains 50 legacy cluster-to-name lists.
It does not identify a current benchmark partition or numerical prompt payload.

`verified_contributing_prompt_records.csv` records the SHA-256 verified request
sources and prompt contents for all 179 contributing calls and 4,584 supplied
target profiles. Every target has 12 high-ranked and eight low-ranked numerical
marker triples. This is prompt-content verification without new model calls.
It does not show that the Table S2 export parameters generated those profiles.

See `docs/table_s02_export_provenance.md` and `docs/table_s02_export_audit.json`.
Original biological marker names and raw source-table method labels are retained.
