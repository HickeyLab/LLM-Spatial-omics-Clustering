# Tests

The focused tests cover the Duke download and provenance contracts, Figure 2
and Supplementary Figure S3 configurations, shared final-figure runtime,
HuBMAP TIFF acquisition, and supplementary-figure labels. They use bounded
fixtures and do not rerun the complete manuscript notebooks.

Run the full suite from the repository root with:

```bash
PYTHONPATH=src python3.12 -m unittest discover -s tests -p 'test_*.py'
```
