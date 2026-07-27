# Notebooks

`main/` contains one structure-only notebook for each defined main manuscript
figure. Notebook filenames begin with the two-digit figure number so they sort
in manuscript order.

Each notebook should eventually:

1. declare its inputs and configuration;
2. call shared functions from `src/`;
3. generate only its assigned figure panels and supporting tables;
4. write artifacts to its matching directory under `outputs/`; and
5. finish with figure-specific validation checks.

`supplementary/` is reserved until the manuscript's supplementary numbering is
finalized.
