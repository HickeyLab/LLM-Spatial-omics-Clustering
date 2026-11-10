#!/usr/bin/env python3
"""Collect SAVED response JSONL offline. This command cannot submit/poll an API.

Each line must retain its custom_id (Batch) or saved request_id (standard).
Serving-identity receipts, when needed, must be captured from actual provider
observations and bind request_ids, model_id, canonical_slug and provider_route.
The protocol's requested/expected identity is not an observed serving receipt.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from llm_spatial_omics_clustering.revision.annotation47_results import collect_results, strict_json


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(manifest_path):
    manifest_path = manifest_path.resolve()
    base = manifest_path.parent
    manifest = strict_json(manifest_path.read_text())
    files = manifest.get('files')
    if type(files) is not dict or 'requests.jsonl' not in files or 'protocol.json' not in files:
        raise ValueError('Manifest must seal requests.jsonl and protocol.json')
    for relative, metadata in files.items():
        path = (base / relative).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise ValueError('Invalid or missing sealed bundle path')
        if type(metadata) is not dict or sha(path) != metadata.get('sha256') or \
                path.stat().st_size != metadata.get('bytes'):
            raise ValueError(f'Sealed bundle hash/size mismatch: {relative}')
    requests = [strict_json(line) for line in (base / 'requests.jsonl').read_text().splitlines() if line.strip()]
    return base, manifest, requests


def load_receipts(path):
    if path is None:
        return {}
    data = strict_json(path.read_text())
    if type(data) is dict:
        result = data.get('receipts', data)
        if type(result) is not dict:
            raise ValueError('Expected request-ID receipt mapping')
        return result
    if type(data) is not list:
        raise ValueError('Expected a receipt mapping or list of bound receipts')
    result = {}
    for receipt in data:
        ids = receipt.get('request_ids', [receipt.get('request_id')])
        if type(ids) is not list or not ids or any(not isinstance(i, str) for i in ids):
            raise ValueError('Receipt lacks explicit request-ID coverage')
        for request_id in ids:
            if request_id in result:
                raise ValueError('Duplicate receipt coverage requires reconciliation')
            result[request_id] = receipt
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--results', type=Path, action='append', required=True,
                        help='Saved UTF-8 response JSONL, repeat for multiple files')
    parser.add_argument('--receipts', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='New directory outside the sealed bundle')
    args = parser.parse_args(argv)
    base, manifest, requests = verify_bundle(args.manifest)
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(base):
        raise ValueError('Output must be a new directory outside the sealed bundle')
    if len({p.resolve() for p in args.results}) != len(args.results):
        raise ValueError('A response file was supplied more than once')
    raw_items = []
    for path in args.results:
        raw_items.extend(line for line in path.read_bytes().splitlines() if line.strip())
    collected = collect_results(requests, raw_items, load_receipts(args.receipts))
    collected.update(bundle_manifest_sha256=sha(args.manifest),
                     protocol_sha256=manifest['files']['protocol.json']['sha256'],
                     network_calls=0, annotation_calls=0,
                     collection_mode='saved_files_only_no_submission')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=output.name + '.', dir=output.parent))
    try:
        raw_dir = temporary / 'raw'
        raw_dir.mkdir()
        sources = []
        for path in args.results + ([args.receipts] if args.receipts else []):
            digest = sha(path)
            target = raw_dir / (digest + path.suffix)
            if not target.exists():
                shutil.copyfile(path, target)
            sources.append({'source_name': path.name, 'sha256': digest,
                            'bytes': path.stat().st_size, 'archive': str(target.relative_to(temporary))})
        collected['source_files'] = sources
        (temporary / 'collection.json').write_text(json.dumps(collected, indent=2, allow_nan=False) + '\n')
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    print(json.dumps({'output': str(output / 'collection.json'),
        'status_counts': dict(Counter(o['status'] for o in collected['outcomes'])),
        'collection_complete': collected['collection_complete'], 'network_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
