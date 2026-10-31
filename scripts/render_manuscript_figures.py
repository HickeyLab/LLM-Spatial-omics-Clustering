#!/usr/bin/env python3
"""Reproduce caption-free manuscript artwork from checksum-pinned snapshots.

Only the declared figure-title rectangles are cleared. Every panel, label,
legend and data pixel outside those rectangles must remain identical.
"""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path

from PIL import Image
from update_reference_figure_labels import render

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "figures/manuscript/manifest.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    for spec in manifest["files"]:
        source = (ROOT / spec["source_file"]).read_bytes()
        if hashlib.sha256(source).hexdigest() != spec["source_sha256"]:
            raise ValueError(f"Source checksum differs: {spec['file']}")
        if spec["labels"]:
            # Erase-only layers do not load a font or redraw any panel content.
            result = render(source, spec, Path("unused-for-erase-only-layers.ttf"))
        else:
            result = Image.open(BytesIO(source)).convert("RGB")
        output = ROOT / spec["file"]
        if args.check:
            actual = Image.open(output).convert("RGB")
            if actual.size != result.size or actual.tobytes() != result.tobytes():
                raise ValueError(f"Artwork differs from its declared title layers: {output}")
        elif spec["labels"]:
            result.save(output, compress_level=9)
        if list(result.size) != spec["size_pixels"]:
            raise ValueError(f"Figure dimensions changed: {output}")
        print(f"{'Verified' if args.check else 'Rendered'} {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
