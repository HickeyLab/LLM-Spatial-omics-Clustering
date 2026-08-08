# Supplementary figure notebooks

## Supplementary Figure 1

`figure_s01_clustering_inputs_and_diagnostics.ipynb` contains one independent
code cell for each of Panels A--E:

- A: ground-truth protein-expression dot plot
- B: ground-truth maps for all eight B004 tissue regions
- C: ground-truth cluster composition for the four Figure 2 methods
- D: recovered exploratory FlowSOM cluster-count sensitivity curve
- E: clustering metric distributions

Panels A--C and E reuse the validated B004 cohort and clustering assignments
from Figure 2, including the image-native TIFF-derived PIXIE result. Panel D
uses a frozen, hash-validated historical table and remains explicitly marked
`VERIFY:` because it is not a sweep of the final Figure 2 FlowSOM pipeline.

Runtime dependencies are recorded in `requirements-figure-s01.txt`.

## Supplementary Figure 2

`figure_s02_leiden_gpt_diagnostics.ipynb` contains exactly two
independently runnable code cells:

- A: unnormalized cell-count confusion matrix
- B: per-Leiden-cluster correctness, annotation loss, and clustering loss

Both cells reuse Figure 4's one provenance-locked
OpenAI/reasoning/optimized-Leiden annotation result. They read
`OPENAI_API_KEY` and fail closed on the checked-in placeholder before reading
the H5AD or cache or writing outputs. The notebook is therefore intentionally
unexecuted until a real local key is supplied. See `docs/figure_s02.md`.

## Future supplementary figures

Add one notebook per supplementary figure after its number, caption, and panel
map are finalized.

Use the naming convention:

```text
figure_sXX_short_descriptive_name.ipynb
```

Do not combine unrelated supplementary figures in a single notebook.
