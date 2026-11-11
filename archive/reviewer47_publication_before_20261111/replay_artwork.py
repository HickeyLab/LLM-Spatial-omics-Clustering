"""Replay the four superseded annotation figures using preserved sources.

Offline only. The unchanged 20261110 frozen data remain in the repository.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures", nargs="+", choices=["3", "S7", "S10", "S11"],
                        default=["3", "S7", "S10", "S11"])
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/reviewer47_archival_artwork_replay")
    args = parser.parse_args()
    index = json.loads((HERE / "artwork_index.json").read_text())
    for entry in index["entries"]:
        if sha(ROOT / entry["archive_path"]) != entry["sha256"]:
            raise ValueError("Archived source changed: " + entry["original_path"])
    sys.path.insert(0, str(ROOT / "scripts"))
    source = HERE / "artwork/scripts"
    sys.path.insert(0, str(source))
    # The archived design source loads its archived style, then resolves the
    # deliberately retained old frozen input bank against the repository root.
    import publication_figure_design as design
    design.ROOT = ROOT
    spec = importlib.util.spec_from_file_location("reviewer47_archived_annotation_renderer",
                                                source / "render_annotation47_figures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.DATA != ROOT / "data/frozen/annotation47_results_20261110":
        raise ValueError("Archived renderer is not bound to its original bank")
    with (HERE / "artwork/configs/cell_type_colors.csv").open(newline="") as f:
        palette = {row["cell_type_update"]: row["color_hex"] for row in csv.DictReader(f)}
    module.palette = lambda: palette.copy()
    for figure in args.figures:
        receipt = module.RENDERERS[figure](args.output)
        expected = HERE / "artwork/figures/publication" / ("Figure_" + figure + ".png")
        actual = args.output / expected.name
        with Image.open(actual) as left, Image.open(expected) as right:
            np.testing.assert_array_equal(np.asarray(left.convert("RGBA")),
                                          np.asarray(right.convert("RGBA")))
        print(figure, "decoded PNG pixel identity verified; file encoding identical:",
              sha(actual) == sha(expected), receipt["files"][actual.name]["sha256"])


if __name__ == "__main__":
    main()
