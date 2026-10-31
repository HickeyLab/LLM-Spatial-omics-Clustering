# Tests

The focused tests cover the Duke download and provenance contracts, Figure 2
and current Supplementary Figure S4 configurations (legacy `figure_s03` imports),
shared final-figure runtime, HuBMAP TIFF acquisition, current supplementary labels,
and manuscript replay integrity. The replay test independently recomputes current
Figure 2/3 metrics from frozen cell labels and assignments, verifies paired-repeat
summaries and checks all 17 approved image hashes. Other tests use bounded
fixtures. Data-dependent tests skip when their external inputs are unavailable.

Run the full suite from the repository root with:

```bash
PYTHONPATH=src python3.12 -m unittest discover -s tests -p 'test_*.py'
```

The separate [execution receipt](../docs/manuscript_sync_verification_20261031.json)
records 21 current notebook executions and four compatibility entry points with
external network connections blocked. Full H5AD analyses were not rerun by that
compact validation.
