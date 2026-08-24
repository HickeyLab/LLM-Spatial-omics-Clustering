# Supplementary Figure S3 panel-level reproducibility contract

This contract supports the current Supplementary Figure S3 panel set. The
canonical reviewer-facing source-rebuild notebook is
`notebooks/final_figures/figure_s03_clustering_inputs_and_diagnostics.ipynb`;
the supporting notebook documented here runs each panel independently. Its
configuration, module, test, and output names all use the current S3 number.

Supplementary Figure S3 documents the raw reference-label phenotypes and the
inputs and diagnostics used for the Figure 2 clustering benchmark. The panel
map is fixed by the supplied composite:

- A: raw ground-truth cell-type protein-expression dot plot
- B: all eight B004 tissue regions
- C: cluster composition by clustering method
- D: recovered FlowSOM purity-versus-cluster-count sweep
- E: distributions of six clustering metrics

The manuscript title is **Reference cell-type characteristics and comparative
evaluation of clustering methods**.

## Notebook contract

The notebook is
`notebooks/supplementary/figure_s03_clustering_inputs_and_diagnostics.ipynb`.
It contains exactly five code cells and no setup or narrative cells:

1. Cell 1 runs Panel A.
2. Cell 2 runs Panel B.
3. Cell 3 runs Panel C.
4. Cell 4 runs Panel D.
5. Cell 5 runs Panel E.

Each cell locates the repository, adds `src/` to the Python path, imports only
its panel runner, and writes that panel's CSV, PNG, PDF, and provenance JSON.
Every cell is independently runnable in a fresh kernel; no panel depends on
variables created by a preceding cell. The tracked notebook was executed
top-to-bottom successfully: its stored execution counts are 1--5 and its
stored outputs record the generated artifact paths.

The implementation and frozen panel contract are:

- `src/llm_spatial_omics_clustering/figure_s03.py`
- `configs/figure_s03.yaml`

No LLM or external API call is used in this supplementary figure.

## Shared Figure 2 dependency

Panels A--C and E load data exclusively through the validated public Figure 2
API. They reuse:

- the same eight-file B004 cohort;
- the H5AD `cell_type_update`, `x`, and `y` observations;
- the 45 native H5AD `X` protein markers;
- the source-traced Leiden, FlowSOM, SpatialSort, and TIFF-derived PIXIE K=300
  assignments tracked under `data/frozen/v3_k300_assignments/` and declared in
  `configs/figure_02.yaml`; and
- exact `File_ID` plus `ID` joins, validated one-to-one.

The shared source universe contains 220,082 cells and 28 raw reference labels,
including 10,495 `Noise` cells. Removing `Noise` leaves 209,587 cells and 27
raw labels. Supplementary Figure S3 does **not** use the later 20-class Figure 2
evaluation harmonization.

The configured and observed cluster counts are:

| Method | Configured K | Occupied clusters |
|---|---:|---:|
| Leiden | 300 | 300 |
| FlowSOM | 300 | 300 |
| SpatialSort | 300 | 246 |
| PIXIE | 300 | 300 |

The source H5AD hash, expected cohort size, per-region counts, label counts,
method names, and cluster counts are validated before any dependent panel is
rendered. Set `CELL_MASKS_DATA_ROOT` only when the source H5AD cannot be found
or downloaded through the repository-relative Duke cache; the exact clustering
assignments are version controlled.

## Panel A: ground-truth marker dot plot

Panel A uses the 209,587 non-Noise cells, 27 raw cell types, and exactly the 45
native H5AD `X` markers. The three auxiliary Figure 2 observation markers
`CD123`, `Hoechst1`, and `CDX2` are excluded. No expression transformation is
applied by this panel.

For cell type \(c\) and marker \(m\):

\[
\bar{x}_{c,m} = \frac{1}{n_c}\sum_{i:y_i=c}x_{i,m}
\]

\[
q_{c,m} = \frac{1}{n_c}\sum_{i:y_i=c}\mathbf{1}[x_{i,m}>0]
\]

Dot size encodes \(q_{c,m}\). Dot color encodes the group mean after min-max
scaling within each marker:

\[
s_{c,m} =
\frac{\bar{x}_{c,m}-\min_{c'}\bar{x}_{c',m}}
{\max_{c'}\bar{x}_{c',m}-\min_{c'}\bar{x}_{c',m}}
\]

A constant marker is assigned a scaled value of zero. Cell types and markers
are independently ordered from the raw group-mean matrix using average
linkage with correlation distance. The exact recovered 27-row and 45-column
orders are frozen in `configs/figure_s03.yaml`; the computation must reproduce
both orders or the panel fails validation.

The audit CSV contains one row per cell-type/marker pair, including cell and
marker display ranks, cell count, raw mean expression, fraction positive, and
marker-scaled mean expression.

## Panel B: all tissue regions

Panel B plots all 220,082 cells and all 28 raw labels, including `Noise`, at
their native H5AD `x` and `y` coordinates. The y coordinate is not inverted.
Axes and individual region identifiers are hidden, spatial aspect is equal,
and the title is `All Tissue Regions`.

The 2-by-4 display order is the lexicographic order used by the recovered
legacy montage:

1. `2e65eeef2dd18bee2a0baf1cec6d35a1`
2. `5318485b16983482401c3be24b6c42ad`
3. `63d000170e475af142f6e8673de5eb0f`
4. `768b7adb649959b6a4e354867595032d`
5. `76d3efd17b6fc83aaac13e961824c5ae`
6. `8da8f27977d946b8c912d42c8827b55c`
7. `ae422532f260b3d6fc662aae69b05d33`
8. `dceadbb36871071f30c308ca091fbdc8`

Colors come from `configs/cell_type_colors.csv`. The audit CSV records each
region's display rank, cell count, observed label count, and coordinate bounds.

## Panel C: cluster composition

Panel C uses all 220,082 cells and all 28 raw labels, including `Noise`.
For every method, cluster, and raw cell type, it computes:

\[
n_{k,c} = \#\{i:z_i=k,\ y_i=c\}
\]

Clusters are sorted by total cell count, largest first. Equal-size clusters are
ordered by the string representation of the cluster identifier. Leiden and
PIXIE display all 300 occupied clusters, SpatialSort displays its 246 occupied
clusters, and FlowSOM displays the 60 largest of its 300 occupied clusters and
explicitly labels that truncation.

The exported long table retains every cluster, including the 240 undisplayed
FlowSOM clusters, and records method, cluster, size rank, raw cell type, stack
rank, cell count, cluster total, and whether the cluster is displayed.

### Assignment provenance

Panels C and E use the same four frozen source-traced assignments as Figure 2.
The PIXIE input is the selected image-native TIFF partition with K=300, not an
older table-level substitute. Each assignment is exact-key joined and checked
against its decompressed source CSV SHA-256 before use.

## Panel D: recovered FlowSOM cluster-count sweep

Panel D is the only panel that does not use the selected Figure 2 assignments.
It reproduces the supplied curve from the frozen local table
`data/frozen/figure_s03/flowsom_k_sweep_purity.csv`. The loader validates the
source SHA-256 and all eight rows before rendering.

For requested cluster count \(K\), the plotted weighted purity is:

\[
\mathrm{Purity}(K) =
\frac{1}{N}\sum_{k=1}^{K}\max_c n_{k,c}
\]

The frozen requested counts are 10, 50, 100, 150, 200, 250, 300, and 350. The
last request has only 324 effective clusters because the recovered SOM contains
324 nodes.

This is an archived historical exploratory sweep, not a resolution sweep of
the final Figure 2 FlowSOM method. Historical execution evidence indicates a
48-marker input, `arcsinh(x/1)`, selection of the 30 highest-variance markers,
standard scaling, PCA retaining 90% variance, an 18-by-18 MiniSom, sigma 9,
learning rate 0.4, seed 42, 5,000 random updates, and Ward metaclustering. No
durable repository generator is available, so the frozen source table is the
reproducibility boundary for this panel.

The final Figure 2 FlowSOM artifact instead uses 45 shared protein markers,
`arcsinh(x/5)`, a full-cohort `RobustScaler`, a 32-by-32 MiniSom with sigma
1.0, learning rate 0.3, 10,000 iterations, Ward metaclustering to K=300, and
seed 42. At 300 clusters, the frozen exploratory sweep has 49.25% raw-class
purity, whereas the final partition has approximately 66.93%. Panel D is
therefore a historical illustration only and must not be described as tuning
or validating the final Figure 2 FlowSOM configuration.

## Panel E: clustering metric distributions

Panel E removes `Noise` and evaluates the 209,587 cells in the 27 raw-label
universe. The third subplot is the Shannon diversity index, not a silhouette
score.

The six distributions have different observation grains:

| Metric | Observation grain | Observations per method | Definition |
|---|---|---:|---|
| Adjusted Rand index | region | 8 | `adjusted_rand_score(raw truth, cluster ID)` |
| Adjusted mutual information | region | 8 | `adjusted_mutual_info_score(raw truth, cluster ID)` |
| Shannon index | cluster | method cluster count | \(-\sum_c p_{k,c}\ln p_{k,c}\) |
| F1 score | raw cell type | 27 | one-vs-rest after global majority mapping |
| Recall | raw cell type | 27 | one-vs-rest after global majority mapping |
| Purity (%) | cluster | method cluster count | \(100\max_c n_{k,c}/n_k\) |

ARI and AMI compare raw reference labels directly with cluster identifiers
within each `File_ID`; no cluster-to-cell-type map is involved.

For F1 and recall, each cluster receives its global B004 majority raw label.
Majority ties are resolved by largest count and then lexicographically smallest
label. For raw cell type \(c\):

\[
\mathrm{Precision}_c = \frac{TP_c}{TP_c+FP_c}
\]

\[
\mathrm{Recall}_c = \frac{TP_c}{TP_c+FN_c}
\]

\[
F1_c =
\frac{2\,\mathrm{Precision}_c\,\mathrm{Recall}_c}
{\mathrm{Precision}_c+\mathrm{Recall}_c}
\]

Undefined denominators are represented as zero, and zero-valued cell-type
observations remain in the distribution.

Shannon diversity uses the natural logarithm. Purity is exported as an
equal-weight per-cluster distribution; it is not the cell-count-weighted
upper-bound purity used elsewhere in the manuscript.

## Generated outputs

Each panel writes an audit table, a 300-dpi PNG, a vector PDF, and a provenance
JSON under `outputs/supplementary/figure_s03/`:

| Panel | Audit table | Figure stem | Provenance |
|---|---|---|---|
| A | `figure_s03a_marker_dotplot_summary.csv` | `figure_s03a_marker_dotplot` | `figure_s03a_provenance.json` |
| B | `figure_s03b_region_summary.csv` | `figure_s03b_all_tissue_regions` | `figure_s03b_provenance.json` |
| C | `figure_s03c_cluster_composition.csv` | `figure_s03c_cluster_composition` | `figure_s03c_provenance.json` |
| D | `figure_s03d_flowsom_cluster_sweep.csv` | `figure_s03d_flowsom_cluster_sweep` | `figure_s03d_provenance.json` |
| E | `figure_s03e_clustering_metrics.csv` | `figure_s03e_clustering_metrics` | `figure_s03e_provenance.json` |

The provenance records include source universes, configured and occupied
cluster counts, formulas, input or table hashes, output-table fingerprints,
coordinate orientation, and the archived-source-only boundary for Panel D.

## Generated-file boundary

Generated files under `outputs/supplementary/` are ignored by Git; only the
supplementary output README is retained by the repository ignore rules.
