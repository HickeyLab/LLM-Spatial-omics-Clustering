# Recompute the frozen 47-marker clustering metrics

`scripts/recompute_clustering47_publication.py` reproduces the clustering-only
tables for the November 8, 2026 publication refresh. It reads fixed assignments
and reference labels. It does not fit clustering or embeddings, call annotation
models, change scientific parameters, modify frozen inputs, or publish figures.

From the repository root, use an environment with the packages recorded in
`data/frozen/clustering47_primary_20261108/environment_freeze.txt`:

```sh
python scripts/recompute_clustering47_publication.py \
  --output-dir /absolute/path/to/new/clustering47-recompute
```

The output directory must be new or empty. Directories containing repository
inputs, source code, documentation, figures, and notebooks are refused. The
command can be launched from another working directory by using an absolute
script path. It resolves all inputs relative to the script's repository.

For an input audit without recomputing tables:

```sh
python scripts/recompute_clustering47_publication.py \
  --verify-inputs-only \
  --output-dir /absolute/path/to/new/clustering47-input-check
```

Both commands verify the binding in `configs/clustering47_publication.json`, its
manifest hash, all manifest members, and the retained baseline inputs. Every
assignment joins by exactly `File_ID,ID` across all 220,082 cells. The unchanged
Leiden and PIXIE memberships are checked against their pinned assignment files.
The completed SpatialSort seed 42 chain is primary. Seed 43 remains sensitivity
evidence. The original FlowSOM manifest and SpatialSort completion receipt are
read as provenance, without following their historical absolute source paths.

The scoring scopes are deliberately different:

- Figure 2E–H uses 209,587 non-Noise cells and the manuscript's 20-class map,
  including Paneth to Goblet. E/G maps majorities within each region. F/H uses
  one global mapping per method. Ties are alphabetical.
- Figure S4C uses raw 28-label compositions including Noise. S4D uses raw 27
  non-Noise labels. Its ARI/AMI points are the eight regional observations,
  while its cluster and cell-type summaries use global assignments.
- Figure S5A uses raw 28 labels including Noise, with pooled and regional
  summaries. The historical shared-marker controls in S5B are outside this
  recomputation.
- The historical 21-label diagnostic uses the separate 15-entry mapping in
  `four_llm_consensus.truth_normalization_map`, including Paneth to
  Neuroendocrine. This map was checked for exact equality to the original
  diagnostic configuration. It is never substituted into the publication panels.

The command independently checks weighted F1, purity, ARI, and the 12 exact
paired sign-flip comparisons for Figure 2E/G. Holm correction applies within
that family only. Other historical test families remain unchanged. It compares
every regenerated publication table to its pinned counterpart, allowing an
absolute numeric tolerance of `2e-12`, and records byte equality separately.

`metrics_receipt.json` records input hashes, package versions, regenerated
output hashes, checks against publication tables, and zero new fits and
annotations. Receipts and newly computed tables stay in the requested output
directory. Existing scientific outputs are not replaced. Do not invoke Python
with `-O`, which would disable retained scientific invariant assertions.

Minimal offline admission checks:

```sh
python -m unittest discover -s tests -p 'test_clustering47_recomputation.py'
```

These checks cover tampered inputs and manifests, unsafe paths, protected
outputs, exact cell joins, alphabetical ties, and preservation of the original
generator. The full-data replay is documented separately in
`docs/clustering47_recomputation_validation_20261108.json`.

The original generator is archived unchanged at
`scripts/archive/recompute_publication_metrics_20261108_original.py`, SHA-256
`cd235843e16c77723a13ac2c3b3b2570f611c6d267a5e414fe051557dd592e62`.
It contains original machine-specific paths and is retained as historical
provenance. The supported entry point is the portable command above.
