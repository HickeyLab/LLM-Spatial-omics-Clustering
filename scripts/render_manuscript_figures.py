#!/usr/bin/env python3
"""Replay verified publication PNGs at the current manuscript image paths.

Use render_publication_figures.py to rebuild native plots from frozen tables.
This command copies exact artwork and does not alter scientific data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "figures/manuscript/manifest.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    for spec in manifest["files"]:
        source = ROOT / spec["source_file"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != spec["source_sha256"]:
            raise ValueError(f"Publication source checksum differs: {source.name}")
        output = ROOT / spec["file"]
        if args.check:
            if hashlib.sha256(output.read_bytes()).hexdigest() != spec["output_sha256"]:
                raise ValueError(f"Manuscript artwork checksum differs: {output.name}")
        else:
            shutil.copyfile(source, output)
        with Image.open(output) as image:
            if list(image.size) != spec["size_pixels"]:
                raise ValueError(f"Manuscript dimensions differ: {output.name}")
        print(f"{'Verified' if args.check else 'Copied'} {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
