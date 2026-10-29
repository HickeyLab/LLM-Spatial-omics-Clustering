# Figure S7 frozen presentation values

The 32 rows are the original B004 test-region means for two conditions, four
clustering methods and four LLMs. Raw source precision is retained. `agreement`
is the unweighted mean of the two regional correct/planned-cell fractions.
Missing and invalid predictions remain errors in those denominators.
Coverage is a distinct field. No valid-prediction-only score is substituted.
The display maps `marker_only` to Marker-only and `retrieval` to
Reference-assisted, with labeled B004 training-region reference profiles.

Original values and source provenance are in `docs/figure_s07_source_audit.json`.
The renderer validates this CSV checksum using `configs/figure_s07.json` and
requires its palette and color limits to match Figure 2H.
