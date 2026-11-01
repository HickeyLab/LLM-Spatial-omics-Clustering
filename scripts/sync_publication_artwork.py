#!/usr/bin/env python3
"""Sync checked publication exports to current artwork and notebook previews."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT/'figures/publication'
    inventory_path = ROOT/'configs/manuscript_inventory.json'
    inventory = json.loads(inventory_path.read_text())
    preview_manifest_path = ROOT/'docs/reference_figure_label_changes.json'
    preview_manifest = json.loads(preview_manifest_path.read_text())
    files = []
    for record in inventory['figures'].values():
        for entry in record['images']:
            target = ROOT/entry['path']
            source = folder/target.name
            receipt = json.loads(source.with_name(source.stem+'_verification.json').read_text())
            assert digest(source) == receipt['files'][source.name]['sha256']
            shutil.copyfile(source,target)
            entry['sha256'] = digest(target)
            key = source.stem.removeprefix('Figure_')
            if key.startswith('S'):
                number,letter = re.fullmatch(r'S(\d+)([A-C]?)',key).groups()
                preview = f'figure_s{int(number):02d}'+('_'+letter.lower() if letter else '')+'.png'
            else:
                preview = f'figure_{int(key):02d}.png'
            shutil.copyfile(source,ROOT/'notebooks/final_figures/previews'/preview)
            files.append({'file':entry['path'],'source_file':str(source.relative_to(ROOT)),
                          'source_sha256':entry['sha256'],'output_sha256':entry['sha256'],
                          'size_pixels':receipt['raster_size_pixels'],
                          'width_mm':receipt['width_mm'],'height_mm':receipt['height_mm'],
                          'minimum_font_pt':receipt['minimum_font_pt'],
                          'minimum_placement_width_mm':receipt['minimum_placement_width_mm'],
                          'dpi':600,'vector_files':[str(source.with_suffix('.'+ext).relative_to(ROOT)) for ext in ['pdf','svg']]})
    manifest = {'schema':'manuscript.artwork.v2','figure_count':15,'image_count':17,
                'policy':'Figure numbers, figure-level titles and explanatory notes stay in captions. Artwork retains concise identifying headings, plain uppercase bold panel letters, axes, keys, units and values. Physical-size typography and proportional placement follow the publication design configuration.',
                'native_renderer':'scripts/render_publication_figures.py',
                'style_file':'configs/publication_figure_style.json',
                'style_sha256':digest(ROOT/'configs/publication_figure_style.json'),
                'files':files}
    assert len(files) == 17
    (ROOT/'figures/manuscript/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    inventory_path.write_text(json.dumps(inventory,indent=2,ensure_ascii=False)+'\n')
    for entry in preview_manifest['figures']:
        source = ROOT/entry['source_file']
        entry['source_sha256'] = digest(source)
        entry['size_pixels'] = json.loads((folder/(source.stem+'_verification.json')).read_text())['raster_size_pixels']
        entry['labels'] = []
    preview_manifest['policy'] = 'Current previews copy the native publication exports with no overlays. Earlier label overlays remain historical.'
    preview_manifest_path.write_text(json.dumps(preview_manifest,indent=2,ensure_ascii=False)+'\n')
    print(f'Synced {len(files)} publication images and their current notebook previews.')


if __name__ == '__main__':
    main()
