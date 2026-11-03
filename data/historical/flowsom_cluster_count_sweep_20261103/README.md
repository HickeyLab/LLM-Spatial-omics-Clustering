# Archived experiment 4: historical FlowSOM cluster-count sweep

This historical experiment was removed from the active manuscript and Figure S4 on November 3, 2026. It is retained here for provenance, including the original eight-row numerical table, configuration, plotting sources, original A–E artwork in PNG/TIFF/PDF/SVG, and its verification receipt. `manifest.json` records SHA-256 hashes and immutable source-commit links for every archived file.

The sweep requested K=10, 50, 100, 150, 200, 250, 300 and 350 (324 effective groups at the final request). Its historical protocol used a 48-marker input, selected the 30 highest-variance markers, arcsinh(x/1), standard scaling, 90%-variance PCA, an 18×18 MiniSom, sigma 9, learning rate 0.4, seed 42, 5,000 random updates and Ward metaclustering. These settings differ from the updated primary FlowSOM protocol. The table is a recovered historical result, not evidence of a new execution.

Original frozen inputs and the October 30 release remain unchanged. The active Figure S4 now retains A–C and relabels the former metric panel E as D. Archived source copies describe the original figure and retain their old panel letters. They are not active publication entry points.

The original exploratory-sweep reconstruction remains documented in `docs/figure_s03.md` under its historical boundary.
