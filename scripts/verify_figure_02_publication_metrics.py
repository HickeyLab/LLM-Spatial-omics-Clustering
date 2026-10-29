#!/usr/bin/env python3
"""Verify the actual publication E/G metric, independently of reconstruction code.

With --source-root, also recompute the frozen regional counts from the archived
exact-key cell tables. No downloading, fitting, or model calls occur.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify(source_root: Path | None = None) -> None:
    audit = json.loads((ROOT / 'docs/figure_02_publication_metric_audit.json').read_text())
    table = ROOT / audit['frozen_count_table']
    if sha256(table) != audit['frozen_count_table_sha256']:
        raise ValueError('Frozen regional count table checksum differs')
    with table.open() as handle:
        rows = list(csv.DictReader(handle))
    keys = [(r['clustering_method'], r['llm'], r['File_ID']) for r in rows]
    if len(rows) != 128 or len(set(keys)) != 128:
        raise ValueError('Expected 128 unique method-model-region rows')
    methods = {'flowsom', 'leiden', 'spatialsort', 'pixie_tiff'}
    models = {'gpt', 'claude', 'gemini', 'deepseek'}
    if {k[0] for k in keys} != methods or {k[1] for k in keys} != models:
        raise ValueError('Unexpected method/model coverage')
    expected = {(r['method'], r['region']): r for r in audit['values']}
    if len(expected) != 32 or len({k[1] for k in expected}) != 8:
        raise ValueError('Expected 32 method-region points across eight regions')
    for key, point in expected.items():
        group = [r for r in rows if (r['clustering_method'], r['File_ID']) == key]
        if len(group) != 4 or {r['llm'] for r in group} != models:
            raise ValueError(f'Expected four models for {key}')
        if {int(r['n_cells']) for r in group} != {point['n_cells']}:
            raise ValueError(f'Model denominators differ for {key}')
        for row in group:
            n, correct = int(row['n_cells']), int(row['correct_cells'])
            if not 0 <= correct <= n or abs(correct / n - float(row['exact_cell_accuracy'])) > 1e-12:
                raise ValueError(f'Invalid saved count/fraction for {key}')
        denominator = sum(int(r['n_cells']) for r in group)
        correct = sum(int(r['correct_cells']) for r in group)
        if denominator != point['n_cell_model_evaluations'] or correct != point['selected_matches']:
            raise ValueError(f'Aggregated counts differ for {key}')
        if abs(correct / denominator - point['mean_selected_reference_agreement']) > 1e-12:
            raise ValueError(f'Plotted agreement differs for {key}')
    for method in methods:
        if sum(p['n_cells'] for (m, _), p in expected.items() if m == method) != 220082:
            raise ValueError(f'Regional cell coverage differs for {method}')

    if source_root is not None:
        for name, expected_hash in audit['source_file_sha256'].items():
            if sha256(source_root / name) != expected_hash:
                raise ValueError(f'Archived cell-source checksum differs: {name}')
        truth = {}
        with (source_root / 'truth.csv').open() as handle:
            for row in csv.DictReader(handle):
                key = row['File_ID'], row['ID']
                if key in truth:
                    raise ValueError('Duplicate reference cell key')
                truth[key] = audit['harmonization'].get(row['cell_type_update'], row['cell_type_update'])
        if len(truth) != 220082 or len(set(truth.values())) != 21:
            raise ValueError('Archived reference cohort differs')
        annotation = next(name for name in audit['source_file_sha256'] if name.endswith('final_all_four_annotations.csv'))
        counts = collections.defaultdict(lambda: [0, 0])
        seen = set()
        with (source_root / annotation).open() as handle:
            for row in csv.DictReader(handle):
                key = row['File_ID'], row['ID']
                if key in seen or key not in truth:
                    raise ValueError('Duplicate or unmatched prediction cell key')
                seen.add(key)
                reference = truth[key]
                baseline_matches = row['phase7_prediction'] == reference
                for method in methods:
                    for model in models:
                        count = counts[method, model, row['File_ID']]
                        count[0] += 1
                        count[1] += baseline_matches or row[f'{method}__{model}'] == reference
        if seen != set(truth) or set(counts) != set(keys):
            raise ValueError('Archived prediction key coverage differs')
        for row, key in zip(rows, keys):
            if counts[key] != [int(row['n_cells']), int(row['correct_cells'])]:
                raise ValueError(f'Independent source-cell recomputation differs: {key}')
        print('Verified all 128 regional rows from 220,082 exact-key source cells.')
    print('Verified 32 regional post-hoc selected reference agreement values, repeated in E and G.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, help='Archived cell_masks workspace containing the immutable production inputs')
    args = parser.parse_args()
    verify(args.source_root)


if __name__ == '__main__':
    main()
