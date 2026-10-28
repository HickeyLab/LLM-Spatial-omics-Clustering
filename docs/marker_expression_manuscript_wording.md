# Matching manuscript wording

## Methods 2.6

Spatial coordinates were used only by SpatialSort.

For the expression dot plots in Figures 2I and S3A, we used the stored processed values of the 45-marker H5AD X matrix, exported through master.csv for Figure 2I. Dot size encodes the percentage of cells with a value strictly greater than 0.0, without an additional arcsinh, logarithmic or standardizing transformation before thresholding. S3A groups the 209,587 non-Noise cells by their 27 original reference cell types. Figure 2I groups cells assigned CD8+ T by each method’s modal predicted label. Color represents the mean stored expression across all cells in each displayed group, min–max scaled to 0–1 separately for each marker across those groups. This color scaling is applied after the above-threshold fractions are calculated. The source H5AD does not record its upstream transformation history, so these values are not assumed to be raw fluorescence intensities. These operational above-threshold fractions are descriptive and are not validated marker-positive fractions. Cutoffs used by other analyses are reported separately.

## Figure S3A caption

(A) Protein-expression profiles across the 27 original non-Noise reference cell types. Dot size encodes the percentage of cells within each type with a stored processed marker value strictly greater than 0.0, using the 45-marker H5AD X matrix without an additional expression transformation. Color shows mean stored expression, min–max scaled to 0–1 independently for each marker across the displayed reference cell types. These fractions are not validated marker-positive fractions.

## Figure 2I caption

(I) Protein marker expression among cells assigned the modal predicted label CD8+ T in each clustering partition. Dot size encodes the percentage with a stored processed marker value strictly greater than 0.0, without an additional expression transformation before thresholding. Color shows mean stored expression, min–max scaled to 0–1 for each marker across the four method groups. These fractions are not validated marker-positive fractions.

## Results 3.2

The profile differences therefore reflect which cells each clustering-and-annotation mapping included in the CD8+ T group, rather than changes in segmentation masks or marker measurements of individual cells (Figure 2I). Dot sizes summarize the percentage of stored processed values strictly above 0.0, as in Figure S3A, and do not establish biological marker positivity.
