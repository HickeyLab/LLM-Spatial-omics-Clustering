#!/usr/bin/env python3
"""Sync checked publication exports to current artwork and notebook previews."""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path
import re
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', nargs='+', help='Sync only these changed native figures and preserve all other exports.')
    args = parser.parse_args()
    folder = ROOT/'figures/publication'
    inventory_path = ROOT/'configs/manuscript_inventory.json'
    inventory = json.loads(inventory_path.read_text())
    preview_manifest_path = ROOT/'docs/reference_figure_label_changes.json'
    preview_manifest = json.loads(preview_manifest_path.read_text())
    manifest_path = ROOT/'figures/manuscript/manifest.json'
    previous = json.loads(manifest_path.read_text())
    by_file = {entry['file']: entry for entry in previous['files']}
    selected = set(args.figures or inventory['figures'])
    unknown = selected - inventory['figures'].keys()
    if unknown:
        raise ValueError(f'Unknown current figures: {sorted(unknown)}')
    for figure_id, record in inventory['figures'].items():
        if figure_id not in selected or record.get('historical_annotation_artwork'):
            continue
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
            if not any(e['source_file'] == entry['path'] for e in preview_manifest['figures']):
                preview_manifest['figures'].append({'file': 'notebooks/final_figures/previews/' + preview,
                    'source_file': entry['path'], 'source_sha256': entry['sha256'],
                    'labels': [], 'size_pixels': receipt['raster_size_pixels']})
            by_file[entry['path']] = {'file':entry['path'],'source_file':str(source.relative_to(ROOT)),
                          'source_sha256':entry['sha256'],'output_sha256':entry['sha256'],
                          'size_pixels':receipt['raster_size_pixels'],
                          'width_mm':receipt['width_mm'],'height_mm':receipt['height_mm'],
                          'minimum_font_pt':receipt['minimum_font_pt'],
                          'minimum_placement_width_mm':receipt['minimum_placement_width_mm'],
                          'dpi':600,'vector_files':[str(source.with_suffix('.'+ext).relative_to(ROOT)) for ext in ['pdf','svg']]}
    # Current S11A was already approved in the live Doc. Copy its original
    # native PNG/SVG bytes without scientific re-rendering or invented formats.
    archive_path = ROOT/'configs/historical_annotation_artwork.json'
    archived = json.loads(archive_path.read_text())['figures'] if archive_path.exists() else {}
    for key, source_record in archived.items():
        if key not in inventory['figures']:
            continue
        for kind, source_entry in source_record['files'].items():
            source = ROOT/source_entry['path']
            if digest(source) != source_entry['sha256']:
                raise ValueError(f'Historical annotation artwork changed: {source.name}')
            target = ROOT/'figures/manuscript'/f'Figure_{key}.{kind}'
            shutil.copyfile(source,target)
        source_entry=source_record['files']['png'];source=ROOT/source_entry['path']
        image_entry=inventory['figures'][key]['images'][0]
        image_entry['sha256']=source_entry['sha256']
        preview=ROOT/'notebooks/final_figures/previews'/f'figure_s{int(key[1:]):02d}.png'
        shutil.copyfile(source,preview)
        with Image.open(source) as im:
            size=list(im.size)
        by_file[image_entry['path']]={'file':image_entry['path'],'source_file':source_entry['path'],
            'source_sha256':source_entry['sha256'],'output_sha256':source_entry['sha256'],
            'size_pixels':size,'width_mm':source_record['width_mm'],'height_mm':source_record['height_mm'],
            'minimum_font_pt':source_record['minimum_font_pt'],
            'minimum_placement_width_mm':source_record['minimum_placement_width_mm'],
            'dpi':600,'vector_files':[source_record['files']['svg']['path']],
            'status':source_record['status'],'available_native_formats':source_record['native_formats']}
        if not any(e['source_file']==image_entry['path'] for e in preview_manifest['figures']):
            preview_manifest['figures'].append({'file':str(preview.relative_to(ROOT)),
                'source_file':image_entry['path'],'source_sha256':source_entry['sha256'],
                'labels':[],'size_pixels':size})
    files=[by_file[e['path']] for r in inventory['figures'].values() for e in r['images']]
    manifest = {'schema':'manuscript.artwork.v2','figure_count':len(inventory['figures']),'image_count':len(files),
                'policy':'Figure numbers, figure-level titles, descriptive panel titles and explanatory notes stay in captions. Artwork retains distinguishing condition, model, method, population and metric labels, plain uppercase bold panel letters, axes, keys, units and values. Physical-size typography and proportional placement follow the publication design configuration.',
                'native_renderer':'scripts/render_publication_figures.py',
                'style_file':'configs/publication_figure_style.json',
                'style_sha256':digest(ROOT/'configs/publication_figure_style.json'),
                'files':files}
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    inventory_path.write_text(json.dumps(inventory,indent=2,ensure_ascii=False)+'\n')
    active_images={e['path'] for r in inventory['figures'].values() for e in r['images']}
    preview_manifest['figures']=[e for e in preview_manifest['figures'] if e['source_file'] in active_images]
    for entry in preview_manifest['figures']:
        source = ROOT/entry['source_file']
        entry['source_sha256'] = digest(source)
        entry['size_pixels'] = by_file[str(source.relative_to(ROOT))]['size_pixels']
        entry['labels'] = []
    preview_manifest['policy'] = 'Current previews copy the native publication exports with no overlays. Earlier label overlays remain historical.'
    preview_manifest_path.write_text(json.dumps(preview_manifest,indent=2,ensure_ascii=False)+'\n')
    print(f'Synced selected figures {sorted(selected)} and preserved {len(files)} current images.')


if __name__ == '__main__':
    main()
