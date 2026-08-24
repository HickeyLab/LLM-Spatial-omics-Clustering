# Figure 2 Panels F–J

These five notebook cells use the same B004 H5AD reference labels and frozen
source-traced assignments as Panel D. All methods targeted K=300; Leiden,
FlowSOM, SpatialSort, and PIXIE have 300, 300, 246, and 300 occupied clusters,
respectively. `Noise` is excluded only where the historical metric or spatial
source did so. Every assignment is joined by exact `File_ID` + `ID` keys and
validated against `data/frozen/v3_k300_assignments/manifest.json`.

## Metrics and maps

- **F:** global, per-reference-cell-type F1 after non-Noise 20-class
  harmonization and a global cluster-majority label mapping.
- **G:** one tissue-level purity observation per `File_ID` and method; tissue-level
  mappings are made within that region.
- **H:** the historical label “purity” means per-reference-cell-type recall
  after a global majority mapping, not cluster purity.
- **I:** native H5AD-X marker means for cells whose deterministic, per-method
  four-LLM modal label is `CD8+ T`; dot area is the fraction with `X > 0` and
  color is min–max scaled independently per marker. Modal ties use GPT,
  Claude, Gemini, then DeepSeek order. No reference-truth filter is applied,
  so cells whose reference label is `Noise` remain in the summaries. The
  source-selected cell counts are 15,970 (Leiden), 8,929 (FlowSOM), 15,535
  (SpatialSort), and 12,042 (PIXIE).
- **J:** normalized 21-class reference maps exclude reference `Noise`; each
  method map uses the same deterministic four-LLM modal labels as Panel I.
  The recovered historical search draws 120 candidate
  centers per FOV with seed 42, restricts centers to the inner 5%--95%
  coordinate range, evaluates radius fractions 0.05, 0.06, 0.07, 0.08, 0.09,
  0.10, 0.12, and 0.14, and retains windows containing 900--1,100 cells. Its
  score combines agreement or disagreement (60%), reference-label diversity
  (15%), and density (25%). The resulting low- and high-agreement windows are
  explicitly post-hoc illustrations selected using reference agreement, not an
  independent validation set. The recovered selections are:

  - low agreement: `File_ID=768b7adb649959b6a4e354867595032d`,
    bounds `[x0, x1, y0, y1] = [4546.435323674194, 6230.835323674193,
    8121.140794695537, 9682.140794695537]`, 1,086 cells;
  - high agreement: `File_ID=76d3efd17b6fc83aaac13e961824c5ae`,
    bounds `[6698.995539724947, 8237.795539724948, 6947.954817410747,
    8268.104817410747]`, 915 cells.

The per-cell consensus input is tracked as
`data/frozen/v3_k300_assignments/panel_i_j_four_llm_consensus.csv.gz`; its
source-annotation, derived-CSV, and gzip hashes are locked in the frozen
assignment manifest.

Run only the relevant Figure 2 notebook code cell. Each writes local CSV,
PNG, PDF, and JSON provenance artifacts under `outputs/figure_02/`; generated
artifacts remain gitignored.
