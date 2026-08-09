# Notebooks

`main/` contains the executable legacy Figure 2 benchmark notebook. Notebook
filenames begin with the two-digit figure number so they sort in manuscript
order.

Each notebook should eventually:

1. declare its inputs and configuration;
2. call shared functions from `src/`;
3. generate only its assigned figure panels and supporting tables;
4. write artifacts to its matching directory under `outputs/`; and
5. finish with figure-specific validation checks.

`supplementary/` is reserved until the manuscript's supplementary numbering is
finalized.

## final source-rebuild notebooks

`final_figures/` contains the source notebooks from the final
annotation-accuracy track.
They are kept as one isolated notebook namespace and use the declared H5AD,
paired OME-TIFF, and raw-LLM input contract. Generated figures, manifests,
executed copies, archive copies, and duplicate short-name aliases are not
versioned here.
