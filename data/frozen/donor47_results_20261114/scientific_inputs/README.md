# Cross-donor evaluation scoring

This bundle reproduces offline B005/B006 scoring without credentials, model calls or fitting. The study comprises809550 cells across24 regions from3 donors: B004 supplies development and paired-representation analyses; B005/B006 supply cross-donor evaluation. Use Python3.12 and the pinned packages in requirements.txt.

```sh
python score_core.py --bundle . --output reproduced_results
```

For a clustering/baseline-only input bundle, append `--offline-only`. A provisional QA bundle requires `--provisional` and always reports publication_ready:false.

The donor annotation design has one means-plus-fractions arm and one repetition:32 donor/method/model sets,128 logical requests and9468 cluster predictions across589468 cells. Primary scoring retains28 labels including valid Noise(code21). Missing/invalid outputs remain errors in the full planned denominator. Regions are weighted equally within each donor and the two donor scores are weighted equally. Pooled cell-weighted results are separately labeled descriptive.

The shared23-label sensitivity excludes reference cells outside the fixed shared vocabulary. Native28 scoring is also supplied on exactly the same eligible cells. Predictions outside the23-label vocabulary remain errors. Frozen B004 classifiers consume the exact decoded integer-thousandths query values and are never fitted or normalized on these donors.

Raw SSE reasoning, opaque checkpoints, account metadata, credentials and private launch paths remain in the checksum-preserved private response archive. The bundle contains only scientific inputs, anonymous requests, selected visible labels/responses and public lineage when final collection is available. Archival reconstruction inputs reside under archive/ and are excluded from the active scoring pass.
