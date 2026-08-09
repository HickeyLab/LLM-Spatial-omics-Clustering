# Tests

Focused figure tests mirror the reusable modules under `src/`:

- `test_figure_02.py`
- `test_figure_s01.py`

The Supplementary Figure 1 tests cover its configuration and five-cell
notebook contract, exact-key Figure 2 dependencies, frozen FlowSOM sweep, and
panel metric calculations without rerunning the complete notebook.

Run the focused suite from the repository root with:

```bash
python -m pytest tests/test_figure_s01.py
```
