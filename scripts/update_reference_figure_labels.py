#!/usr/bin/env python3
"""Reproduce label-only publication previews without rerunning an analysis.

The original PNGs are read from the pinned Git revision and checksum-verified.
Internal truth-column names and biological label vocabularies are not changed.
"""
from __future__ import annotations
import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/reference_figure_label_changes.json'


def render(source: bytes, spec: dict, font_path: Path) -> Image.Image:
    if hashlib.sha256(source).hexdigest() != spec['source_sha256']:
        raise ValueError(f"Source checksum differs: {spec['file']}")
    original = Image.open(BytesIO(source)).convert('RGB')
    result = original.copy()
    draw = ImageDraw.Draw(result)
    mask = np.zeros((original.height, original.width), dtype=bool)
    for label in spec['labels']:
        x, y, width, height = label['rect']
        draw.rectangle((x, y, x + width - 1, y + height - 1), fill='white')
        mask[y:y + height, x:x + width] = True
        font = ImageFont.truetype(str(font_path), round(label['size']))
        if label.get('rotate'):
            bounds = font.getbbox(label['new'])
            tile = Image.new('RGBA', (bounds[2] - bounds[0] + 20, bounds[3] - bounds[1] + 20))
            ImageDraw.Draw(tile).text((10 - bounds[0], 10 - bounds[1]), label['new'], font=font, fill='black')
            tile = tile.rotate(90, expand=True)
            result.paste(tile, (round(label['x'] - tile.width / 2), round(label['y'] - tile.height / 2)), tile)
        else:
            anchor = 'ls' if label.get('align') == 'left' else 'ms'
            draw.text((label['x'], label['y']), label['new'], font=font, fill='black', anchor=anchor)
    differences = np.any(np.asarray(original) != np.asarray(result), axis=2)
    if np.any(differences & ~mask):
        raise ValueError(f"Label rendering escaped its declared text areas: {spec['file']}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare committed previews with the reproduced pixels.')
    parser.add_argument('--font', type=Path, help='Path to the DejaVuSans.ttf font bundled with Matplotlib.')
    args = parser.parse_args()
    import matplotlib
    font_path = args.font or Path(matplotlib.get_data_path()) / 'fonts/ttf/DejaVuSans.ttf'
    manifest = json.loads(MANIFEST.read_text())
    for spec in manifest['figures']:
        source = subprocess.check_output(['git', 'show', f"{manifest['source_revision']}:{spec['file']}"], cwd=ROOT)
        result = render(source, spec, font_path)
        path = ROOT / spec['file']
        if args.check:
            actual = Image.open(path).convert('RGB')
            if actual.size != result.size or actual.tobytes() != result.tobytes():
                raise ValueError(f"Preview differs from reproducible label revision: {path}")
        else:
            result.save(path, compress_level=9)
        print(f"{'Verified' if args.check else 'Updated'} {spec['file']}")


if __name__ == '__main__':
    main()
