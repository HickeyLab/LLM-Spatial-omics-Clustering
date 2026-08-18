# Data

The manuscript data are not stored in Git. Keep local files in the appropriate
tier:

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
Supplementary Figure S1 require twelve local H5AD files forming six
before/after REDSEA pairs; Supplementary Figure S2 uses the corresponding
three-method subset. Those REDSEA inputs are not in the Duke archive. Figure 1
Panels C--F and Supplementary Figure S2 also use the historical reference
`20260130_HuBMAP_Yang_annotate_with_area.h5ad`. The Duke H5AD has the columns
needed by that reference-matching step, but equivalence between the two H5ADs
has not been established.
