"""Checksum-pinned current clustering inputs, separate from archived annotations.

Only fixed memberships and reference-derived descriptive diagnostics are read.
This module never fits a model, annotates a cluster or changes a frozen input.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = 'configs/clustering47_publication.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract(root=ROOT):
    root = Path(root)
    path = root / CONFIG
    if not path.exists():
        return None
    config = json.loads(path.read_text())
    manifest_path = root / config['manifest']
    if digest(manifest_path) != config['manifest_sha256']:
        raise ValueError('Current clustering manifest checksum differs')
    manifest = json.loads(manifest_path.read_text())
    if manifest['schema'] != 'clustering.publication.primary47.v1':
        raise ValueError('Unsupported current clustering contract')
    if manifest['primary_spatialsort_seed'] != 42 or manifest['spatialsort_sensitivity_seed'] != 43:
        raise ValueError('Frozen SpatialSort primary/sensitivity selection changed')
    return config, manifest


def _checked_path(relative, manifest, root):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Current clustering input escapes the repository')
    entry = manifest['files'].get(relative)
    if entry is None or digest(path) != entry['sha256']:
        raise ValueError(f'Current clustering input checksum differs: {relative}')
    return path


def override_path(name, collection='publication_table_overrides', root=ROOT):
    current = contract(root)
    if current is None:
        return None
    config, manifest = current
    relative = config.get(collection, {}).get(name)
    return None if relative is None else _checked_path(relative, manifest, root)


def verify_current_inputs(root=ROOT):
    current = contract(root)
    if current is None:
        return 0
    _, manifest = current
    for relative in manifest['files']:
        _checked_path(relative, manifest, root)
    return len(manifest['files'])


def clustering_assignment_specs(root=ROOT):
    """Return only current clustering specs, never annotation-bound memberships."""
    current = contract(root)
    if current is None:
        return None
    _, manifest = current
    result = {}
    for method, spec in manifest['methods'].items():
        entry = dict(spec)
        entry['assignment_path'] = _checked_path(spec['path'], manifest, root)
        result[method] = entry
    return result
