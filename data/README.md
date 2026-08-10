# Data

The manuscript data are not stored in Git. Keep local files in the appropriate
tier:

- `raw/`: immutable source data.
- `interim/`: temporary or partially transformed data.
- `processed/`: analysis-ready data used by the figure notebooks.

Document the source, version, and transformation history when data are added.

The Figure 2 ground-truth source is downloaded on demand from the [Duke
Research Data Repository record 505](https://research.repository.duke.edu/record/505).
The ignored `raw/duke_research_repository/` cache stores the public
`CODEX_annotated.zip` archive, the extracted
`20260130_HuBMAP_experted_annotated.h5ad`, and a verification receipt. The
loader checks the archive MD5 and extracted H5AD SHA-256 before use.
