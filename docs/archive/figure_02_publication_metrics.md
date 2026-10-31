# Figure 2 publication metric verification

The embedded publication panels E and G both plot **post-hoc selected reference
agreement**. They do not plot regional weighted F1 or regional cluster purity.
Each method has eight region points, and both panels repeat the same 32 values
with different y-axis limits. The axes retain fractions on a 0–1 scale.

For method m, model l and region r, the source counts a cell as matching when
`phase7_prediction == reference OR raw_method_model_prediction == reference`.
The plotted point is the arithmetic mean of this fraction across the four
models. Because all four denominators are equal within a region, this also
equals summed selected matches divided by four times the regional cell count.
The score includes all 220,082 cells and 21 reference labels, including Noise.
It selects matches using reference labels on the evaluated cells. It is
selection-biased, retrospective and not a deployable predictor, independent
validation or direct agreement of one fixed prediction map.

## Source verification

The actual production path was `v3_scripts/build_v3_figure02_selector_summary.py`
(`_source_rows`), then `v3_scripts/historical_v1_figure02_replay.py`
(`_four_llm_file_id_selector_means`, `render_panel_e`, `render_panel_g`), then
`v3_scripts/build_historical_v1_figure02_page.py`. This production path is
separate from the later `src/.../figure_02.py` module and the current notebook
reconstruction. Their calculations must not be used to rename publication
preview metrics.

The audit recomputed all 128 method-model-region count rows from the immutable,
exact-key 220,082-cell source tables and matched the saved counts and fractions.
The pinned publication PNG has SHA-256
`44978280393bac9756e3e826e60a244cf7a2845399635e82df93c0a3f8fb6cd7`.
Source hashes, harmonization and all 32 point values are recorded in
[the machine-readable audit](figure_02_publication_metric_audit.json).
The small frozen regional count table supports verification without downloading
cell-level data or calling any model:

```bash
python scripts/verify_figure_02_publication_metrics.py
# Optional independent recomputation when the archived production inputs exist:
python scripts/verify_figure_02_publication_metrics.py --source-root /path/to/cell_masks
```

No clustering fit, model call, parameter selection or new result was performed.
The label revision preserves every plotted value and all pixels outside the
text rectangles recorded in `reference_figure_label_changes.json`.

## Distinct metrics and vocabularies

- F: per-reference-type F1 after global cluster-majority label assignment.
- H: per-reference-type recall, `TP / (TP + FN)`. Its former display term
  “Purity” was incorrect and is changed to “Recall”, with percentages retained.
- Regional cell-count-weighted F1: support-weighted mean of classwise F1 after
  region-specific majority assignment. The later module computes this for E,
  but it is not the metric in the embedded publication E.
- Cluster purity within one cluster: its majority-reference-label cell count
  divided by its total cell count.
- Regional cell-count-weighted cluster purity: `sum_cluster max_reference n(cluster, reference) / N`
  within a region. The later module computes this for G, but it is not the
  metric in the embedded publication G.
- Direct reference agreement: matches from one fixed prediction map divided by
  its evaluated cell count. It does not take a reference-selected union.

F/H retain their historical 20-class non-Noise mapping, including Paneth to
Goblet. E/G retain their 21-label scoring vocabulary, including Noise and
Paneth to Neuroendocrine. These are panel-specific evaluation mappings. Original
dataset biological class names are not renamed globally.

The actual local production renderer now uses the verified E/G display names
and H recall terminology. The reproducible GitHub preview label generator uses
the same names. The later module retains its genuine F1/purity calculations,
and the notebook retains its different reconstructions, with explicit warnings
about the publication boundary.

See [the matching manuscript wording](figure_02_manuscript_metric_wording.md).
