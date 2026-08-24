# Data

Large manuscript data are not stored in Git. Two small publication-critical
input sets are versioned so their notebooks run from a clean clone:

- [`frozen/v3_k300_assignments/`](frozen/v3_k300_assignments/README.md) contains
  byte-preserving compressed copies of the four source-traced K=300 assignment
  tables and a manifest that pins their decompressed SHA-256 values, common
  220,082-cell key set, and observed cluster counts (300, 300, 246, and 300).
  It also contains the hash-locked four-LLM modal labels used by Figure 2
  Panels I and J.
- [`tables/`](tables/README.md) contains the authoritative Table S2 source.

Keep larger local files in the appropriate tier:

- `raw/`: immutable source data.
- `interim/`: temporary or partially transformed data.
- `processed/`: analysis-ready data used by the figure notebooks.

Document the source, version, and transformation history when data are added.

The annotated H5AD used directly as the Figure 2 ground-truth source and by
the downstream Figures 3--4 and Supplementary Figures S3--S4 is downloaded on
demand from [Duke Research Data Repository record
505](https://research.repository.duke.edu/record/505). The ignored
`raw/duke_research_repository/` cache stores the public `CODEX_annotated.zip`
archive, the extracted `20260130_HuBMAP_experted_annotated.h5ad`, and a
verification receipt. The loader checks the archive MD5 and extracted H5AD
SHA-256 before use.

Record 505 is not presented as the complete Figure 1 source. Figure 1 and
Supplementary Figure S1 require twelve H5AD files forming six before/after
REDSEA pairs; Supplementary Figure S2 uses the corresponding three-method
subset. Figure 1 Panels C--F and Supplementary Figure S2 also use the
historical reference `20260130_HuBMAP_Yang_annotate_with_area.h5ad`.

That exact 13-file input set is published in [Duke Research Data Repository
record 565](https://research.repository.duke.edu/record/565) (version 1, DOI
[`10.7924/r4r565`](https://doi.org/10.7924/r4r565)). Download the files into
the repository-relative `data/processed/` directory before running the Figure
1, S1, or S2 notebooks. The published filenames, byte sizes, and MD5 checksums
are pinned in
[`configs/duke_record_565_manifest.json`](../configs/duke_record_565_manifest.json).

Record 505 does not contain these REDSEA files. Its
`20260130_HuBMAP_experted_annotated.h5ad` has the columns needed by the Figure 1
reference-matching step, but equivalence to record 565's historical
`20260130_HuBMAP_Yang_annotate_with_area.h5ad` has not been established.
