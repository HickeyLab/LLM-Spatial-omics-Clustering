# Reproduce the retained manuscript

The [current display crosswalk](../configs/manuscript_display_crosswalk.json), [figure map](figure_map.md) and [current notebooks](../notebooks/final_figures/README.md) define 18 manuscript figures and 20 image files. Notebook headings and exact captions follow the November 15 manuscript. Native renderer IDs and frozen filenames remain stable. For example, manuscript Figure S1 uses native source S6, and manuscript Figure S2 uses native source S9.

## Completed annotation replay

Use Python 3.12 and the repository requirements. No API key, H5AD, model calls, network access or new fits are needed after dependencies are installed.

```bash
python3.12 -m pip install -r requirements-reviewer47.txt
python3.12 -B scripts/replay_completed_reviewer47.py --output outputs/reviewer47_completed_replay
```

Choose a new output directory. The replay verifies the original immutable 275-answer snapshot, the newly admitted DeepSeek answer and all eight Astra answers. It checks literal request identities, normal stops, strict query parsing, 47 markers, 28 labels including Noise, exact 220,082-cell keys and the fixed two-region endpoint. All 71 current B004 sets, 284 items and 20,076 predictions are complete. The original snapshot remains independently replayable with its historical pending item. The completion replay performs no fitting.

The [completion record](revision/reviewer47_completed_publication_20261115.md) describes the append-only sources and provider-route qualification. [Cross-donor sources](../data/frozen/donor47_results_20261114/manifest.json) remain separate: their five invalid DeepSeek items remain missing in the planned denominator and are not repaired by the B004 completions.

## Native figures and tables

Current manuscript-number notebooks display checksum-bound artwork and exact current captions. Existing native renderers retain their stable source IDs. For instance, native S6 renders manuscript S1, native S9 renders manuscript S2, and native S8 renders manuscript S10.

```bash
python3.12 scripts/render_publication_figures.py --output outputs/native_replay --figures 2 3 4 S4 S5 S6 S7 S8 S9 S10 S11
python3.12 scripts/render_donor47_figures.py --help
python3.12 scripts/revision/render_reviewer47_tables.py --output outputs/reviewer47_tables
```

Rendering uses saved scored tables. Table S8d includes the completed DeepSeek selected-means condition, and Table S9 includes both Opus and Astra controls. Conventional classifiers use richer training-label supervision than the LLMs. Coarsening is not native-K fitting, and calibration remains retrospective within-donor reference agreement.

## Compensation sources and archival reproduction

The retained compensation sources under [Duke record 565](../configs/duke_record_565_manifest.json) support manuscript Figures 1 and S3–S5. Their native source IDs are 1 and S1–S3. Unavailable segmentation inference metadata remains explicitly unverified. Main clustering and annotation use the published expert-reference dataset in Duke record 505.

The immutable October 30 release, earlier selected-marker experiments and earlier manuscript snapshots remain archival. Their figure numbers, vocabulary or model settings must not be substituted for the current crosswalk. The prior lightweight reviewer command still reconstructs its original pending snapshot, rather than the completed November 15 scope.

Current manuscript PNG artwork is preserved in [the separate-figure package](../figures/current_manuscript/READ_ME.txt), with [checksums and source limits](../figures/current_manuscript/Figure_manifest.json). The current notebook display uses these exact PNG files. Native renderer/vector exports remain separately labeled because their palettes may differ. The original workflow raster in Figure 1A is approximately 300 dpi at its retained placement, so the package does not claim that every element meets a 600 dpi source-resolution requirement.
