# October 2026 revision deposition

The versioned release `revision-2026-10-30-v1` deposits the recovered model
outputs and the code and supporting records for the October revision:

https://github.com/HickeyLab/LLM-Spatial-omics-Clustering/releases/tag/revision-2026-10-30-v1

The release assets are the authoritative revision snapshot. The repository's
earlier figure notebooks remain available at their existing paths. The local
analysis-source snapshot is deposited separately to avoid silently replacing
newer public figure code with an older workspace copy.

## Contents

| Asset | Contents |
| --- | --- |
| `analysis_source.zip` | Analysis source, configuration, requirements and focused verification code |
| `historical_benchmark.zip` | Recovered historical requests/responses, source-to-map records, all 16 final maps, call settings, cell keys and reference-label records |
| `controlled_annotation.zip` | Frozen four-model donor-transfer and prompt-control study, available attempts, raw responses, predictions, scoring caches and its portable verifier |
| `archived_repeated_benchmark.zip` | Earlier three-attempt full-marker benchmark, with its preserved requests, responses and reports, kept separate from the later controlled studies |
| `supplementary_analyses.zip` | Paired means/fractions study, calibration and spatial-input study, conditional comparisons, mapping sensitivity, channel membership and current numerical supplementary tables |
| `clustering_and_matching.zip` | Common-marker clustering evidence, fitted artifacts and matching/retention sensitivity outputs |
| `donor_correspondence.zip` | B005/B006 public-mask correspondence, native cell-clustering and scoring records |

`PUBLIC_MANIFEST.json` records every deposited file's SHA-256 and size.
`SOURCE_EXPORT_MAPPING.json` relates original local hashes to the deposited
copies. Provider account identifiers and local credential-discovery helpers
are removed from public copies. The numerical predictions and scientific
request/response content are retained. Original internal manifests retain
their original hashes as provenance records. Use `PUBLIC_MANIFEST.json` for
verification of exported bytes.

## Retrieve and verify

Download the seven ZIP assets, `PUBLIC_MANIFEST.json`, `SOURCE_EXPORT_MAPPING.json`,
`verify_revision_deposit.py` and the replay requirements into one folder.
Extract all seven ZIPs into that same folder, preserving their paths. Verify the
archive hashes using `SHA256SUMS.txt`. With Python 3.12:

```sh
python -m pip install -r requirements-replay.txt
python verify_revision_deposit.py --root .
```

The verifier checks deposited-file hashes, decodes frozen responses and
reconstructs prediction maps and regional metrics. It independently checks the
paired representation summaries, calibration metrics, spatial-input controls
and reference-label sensitivity. It does not invoke an LLM, fit a model or
download data. Use `--hashes-only` for the file-integrity check alone.

## Source data and scope

Large original imaging and H5AD datasets remain at their source repositories.
Figure-specific acquisition contracts and checksums are retained in the code
and evidence assets. The compensation source is Duke Research Data Repository
record 565, and the main cohort source is record 505. The additional donors
come from the same HuBMAP intestine source rather than an independent external
study. See the source manifests for the exact files and matching coverage.

The historical benchmark and later controlled experiments have different
vocabularies, inputs and inference settings. They are not pooled as repeated
measurements of one protocol. Available historical contributing-call records
are deposited, but the complete historical failed/rejected-request history,
immutable provider snapshots and total development cost were not recovered.
Their absence is documented rather than reconstructed. This release does not
add independent biological reference labels or segmentation-boundary truth.
It is a research-output deposition, not a journal submission or acceptance of
pending manuscript suggestions.
