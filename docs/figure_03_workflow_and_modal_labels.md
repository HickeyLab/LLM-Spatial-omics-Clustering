# Figure 3 workflow and annotation benchmark

The current manuscript has panels A–E. B reports equal-test-region reference
agreement and C reports fixed-28-label macro-F1 for the means-plus-fractions
arm. D reports pooled-test cell-type recall for four models applied to Leiden
clusters. E shows the reference labels and the four models' predictions in the
fixed mid-jejunum region used in Figure 2C. Each condition contributes one
accepted annotation per cluster and arm.

Panel A restores the author's six-stage BioRender artwork. Its editable labels
now describe the current 47-marker cluster summaries, anonymous cluster IDs,
all-marker means and means-plus-fractions representations, and fixed 28-label
ontology. The historical marker-name-list and threshold-optimization wording
is not part of the current workflow. The original authoring export and crop
metadata remain pinned in `configs/biorender_workflows.json`.

Panels B and C share model and method orders ranked by decreasing mean
macro-F1 from C. D orders cell types by decreasing mean recall across the four
models. The same model order is used in D and E. These display permutations
do not change scores, the scoring vocabulary, input profiles or spatial
coordinates.

The earlier reference-informed selection panels and most-frequent-label
spatial maps are archived analyses. The current four-model most-frequent-label
summary is used for Figure S11 profiles, with ties in Astra, Opus, Argon and
DeepSeek order without reference labels. Internal `modal_consensus` keys
remain for compatibility.

The [figure map](figure_map.md) defines current display labels. The
[reproduction guide](manuscript_reproduction.md) identifies the frozen inputs
and archived reconstruction boundaries. Earlier restoration and design
verification files remain historical records.
