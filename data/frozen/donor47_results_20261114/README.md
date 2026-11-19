# Cross-donor evaluation

This is the final offline scoring bank for B005/B006. The study includes 809,550 cells across 24 regions from three donors. B004 supplies development and paired-representation analyses; B005/B006 supply cross-donor evaluation of 589,468 cells across 16 regions.

The donor annotation design has one means-plus-fractions arm and one repetition: 32 donor/method/model sets, 128 logical requests and 9,468 planned cluster predictions. Astra, Opus and Gemini each delivered all 32 items. DeepSeek delivered 27 of 32 items. The five invalid DeepSeek responses remain errors in every planned denominator, giving 123 accepted items and 9,093 delivered predictions overall.

Primary evaluation uses the native 28 labels, including valid Noise (code 21). Regions receive equal weight within each donor; the two donor summaries receive equal weight. Pooled cell-weighted metrics are separately labeled descriptive. The shared 23-label sensitivity uses a fixed reference-eligible population, with native 28-label scoring also reported on exactly the same cells. Predictions outside the shared vocabulary remain errors.

Install the packages in `scientific_inputs/requirements.txt`, then reproduce all active scores without credentials, model calls, fitting or network access:

```sh
python scientific_inputs/score_core.py --bundle scientific_inputs --output reproduced
```

Flat CSV files support manuscript figures and tables. `score_manifest.json` binds the exact score files. `scientific_inputs/manifest.json` binds all portable inputs and the scorer. `FINAL_HANDOFF.json` records the terminal-response, strict-acceptance, privacy and byte-identical replay gates. Unmodified archival controls under `scientific_inputs/archive/` are excluded from the active scoring pass.

Raw reasoning, opaque checkpoints, account metadata and private launch paths remain in the checksum-preserved private archive. Financial summaries distinguish known settled charges from retained uncertain holds; holds are not invoices.
