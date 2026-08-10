# Tests

Focused figure tests mirror the reusable modules under `src/`:

- `test_figure_02.py`
- `test_figure_s01.py`
- `test_final_figures_runtime.py`
- `test_hubmap_tiff_download.py`

The Supplementary Figure 1 tests cover its configuration and five-cell
notebook contract, exact-key Figure 2 dependencies, frozen FlowSOM sweep, and
panel metric calculations without rerunning the complete notebook.

Run the focused suite from the repository root with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_final_figures_runtime.py'
PYTHONPATH=src python -m unittest discover -s tests -p 'test_hubmap_tiff_download.py'
```
