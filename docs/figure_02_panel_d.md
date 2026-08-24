# Figure 2, Panel D — B004 UMAP comparison

## Scope

Panel D uses only the eight `File_ID` values declared in
[`configs/figure_02.yaml`](../configs/figure_02.yaml), which are the specified
B004 tissue regions. The source is the Duke Research Data Repository member
`CODEX_annotated/20260130_HuBMAP_experted_annotated.h5ad`; the panel input is
built directly from its 45 `X` variables plus `obs` columns `CD123`,
`Hoechst1`, and `CDX2`. If the source is absent, the Figure 2 loader downloads
and verifies the public archive into the ignored
`data/raw/duke_research_repository/` cache.
The reference label is `obs.cell_type_update`.

Each of the five views uses one shared UMAP geometry and colors cells by:

1. their reference label (Ground Truth); or
2. the majority reference label of their Leiden, FlowSOM, SpatialSort, or
   TIFF-derived PIXIE cluster.

Cluster identifiers are unsupervised labels and are not plotted directly.

The source record is [Duke Research Data Repository record 505](https://research.repository.duke.edu/record/505),
DOI [10.7924/r4r505](https://doi.org/10.7924/r4r505). The archive is about 2.2
GB; the extracted H5AD is about 105 MB. To acquire it explicitly before
running the figure:

```bash
PYTHONPATH=src python3.12 -m llm_spatial_omics_clustering.duke_h5ad
```

## Frozen source-traced assignments

Panel D uses the exact selected V3 cell assignments tracked under
[`data/frozen/v3_k300_assignments/`](../data/frozen/v3_k300_assignments/README.md).
All four methods were configured with a target of 300 clusters. Leiden,
FlowSOM, and PIXIE occupy all 300 labels; SpatialSort occupies 246 of its 300
configured labels. Every table contains the same 220,082 unique
`File_ID` + `ID` keys.

| Method | Tracked assignment | Source CSV SHA-256 | Configured K | Occupied clusters |
| --- | --- | --- | ---: | ---: |
| Leiden | `data/frozen/v3_k300_assignments/leiden/assignments.csv.gz` | `1e9be030ebdbadb60ae3785786ea0621decd931289b2902c72ec08a6b5c39e18` | 300 | 300 |
| FlowSOM | `data/frozen/v3_k300_assignments/flowsom/assignments.csv.gz` | `9c2d4cb5981214d07505d83346c47817d6e1761587a306cf123f6aa5b2adfe78` | 300 | 300 |
| SpatialSort | `data/frozen/v3_k300_assignments/spatialsort/master_spatialsort_clusters.csv.gz` | `8e6f09377be96fbb998a16ca35a6376e89029edb0f855756f5533f4ff003e56e` | 300 | 246 |
| PIXIE | `data/frozen/v3_k300_assignments/pixie/master_pixie_clusters.csv.gz` | `7d017a95e0a816612ea29c3d8aab9a02e4a8b5cc10d6c8056f5fbce9aa4dfbd6` | 300 | 300 |

The loader validates each decompressed source hash, row count, exact key set,
and occupied-cluster count against
[`manifest.json`](../data/frozen/v3_k300_assignments/manifest.json).

The source-traced method contracts are:

- **Leiden:** 47 markers excluding `Hoechst1`, `arcsinh(x/5)`, and a
  `StandardScaler` fit separately within each `File_ID`; a local Leiden
  hierarchy with 24 PCs, 24 neighbors, resolution 1.1, minimum child size 100,
  maximum 7 children, and seed 42 produced a 320-cluster base partition, then
  20 deterministic within-parent Ward-style centroid merges produced K=300.
  Harmony was not used.
- **FlowSOM:** the 45 shared protein markers, `arcsinh(x/5)`, a full-cohort
  `RobustScaler`, a 32-by-32 MiniSom with sigma 1.0, learning rate 0.3, 10,000
  iterations, Ward metaclustering to K=300, and seed 42.
- **SpatialSort:** the 45 shared protein markers, `arcsinh(x/5)`, a
  full-cohort `RobustScaler`, within-region 24-nearest-neighbor graphs,
  precision scale 0.65, an 8-entry trace containing 6 MCMC sweeps, one inner
  double-Metropolis-Hastings iteration, the last-iteration point estimate, and
  seed 42. The K=300 run has 246 occupied clusters.
- **PIXIE:** paired 48-channel expression and integer-mask OME-TIFFs including
  Hoechst, a 2-pixel Gaussian blur, a 10-by-10 pixel SOM and 20 pixel
  metaclusters (sigma 5.0, learning rate 0.05, one pass), followed by a
  24-by-24 cell SOM and 300 cell metaclusters; the cell SOM used sigma 2.0,
  learning rate 0.3, 5,000 iterations, and seed 42.

These files are frozen publication inputs. Tracking them makes the published
partition reproducible without implying that a clean clone reruns the original
external clustering engines.

## UMAP provenance

The shared UMAP is a visualization-only geometry and is not part of any
clustering method. Its recovered coordinate source is locked by SHA-256
`0bf956a2c03d3371a07c675b0caa3f663765d49e4ae322e25b8b475d6728ceb9`.
The recorded reconstruction contract uses `arcsinh(x/1)`, standardization,
PCA retaining 90% variance, `File_ID` batch correction, 30 neighbors,
`min_dist=0.3`, Euclidean distance, and seed 42. The zoom bounds are likewise
source locked.

This recovered display contract does not redefine the source-traced clustering
settings. In particular, Harmony-style batch correction belongs only to the
shared visualization; the authoritative Leiden K=300 artifact did not use
Harmony.
