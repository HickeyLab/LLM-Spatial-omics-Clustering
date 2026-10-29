#!/usr/bin/env python3
"""Verify descriptive agreement gaps without fitting or calling a model."""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOCABULARIES = ('historical_21', 'original_28')


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def verify(source_root: Path | None = None) -> None:
    audit = json.loads((ROOT / 'docs/leiden_claude_diagnostic_identity_audit.json').read_text())
    table = ROOT / audit['cluster_count_table']
    if sha256(table) != audit['cluster_count_table_sha256']:
        raise ValueError('Frozen cluster-count table checksum differs')
    with table.open() as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 300 or len({r['cluster'] for r in rows}) != 300:
        raise ValueError('Expected 300 unique clusters')
    for vocab in VOCABULARIES:
        total = bound = matches = minority = majority_mismatches = 0
        for row in rows:
            n = int(row['n_cells'])
            u = int(row[vocab + '_bound_cells'])
            a = int(row[vocab + '_direct_matches'])
            recovered = int(row[vocab + '_minority_matches'])
            disagreed = int(row[vocab + '_majority_mismatches'])
            if not 0 <= a <= u <= n or u - a != disagreed - recovered:
                raise ValueError(f'Invalid component identity: {row["cluster"]}/{vocab}')
            total += n; bound += u; matches += a
            minority += recovered; majority_mismatches += disagreed
        expected = next(s for s in audit['summary'] if s['reference_vocabulary'] == vocab)
        observed = {'n_cells': total, 'direct_matches': matches, 'cluster_majority_bound_cells': bound,
                    'within_cluster_bound_gap_cells': total - bound, 'net_annotation_gap_cells': bound - matches,
                    'minority_matches': minority, 'majority_mismatches': majority_mismatches}
        if total != 220082 or any(expected[k] != v for k, v in observed.items()):
            raise ValueError(f'Aggregate count contract differs: {vocab}')
        if matches + (total - bound) + (bound - matches) != total:
            raise ValueError('Aggregate identity does not sum to the cell total')
        print(f'{vocab}: Direct reference agreement {100*matches/total:.3f}%, '
              f'Within-cluster bound gap {100*(total-bound)/total:.3f}%, '
              f'Net annotation gap {100*(bound-matches)/total:.3f}%. '
              f'Minority-label matches retained: {minority:,}.')

    if source_root is not None:
        sources = audit['source_inputs']
        for spec in sources.values():
            if sha256(source_root / spec['path']) != spec['sha256']:
                raise ValueError(f'Cell-source checksum differs: {spec["path"]}')
        reference = {}
        with (source_root / sources['truth']['path']).open() as handle:
            for row in csv.DictReader(handle):
                key = row['File_ID'], row['ID']
                if key in reference:
                    raise ValueError('Duplicate reference key')
                raw = row['cell_type_update']
                reference[key] = (audit['historical_harmonization'].get(raw, raw), raw)
        assignments = {}
        with (source_root / sources['leiden_assignment']['path']).open() as handle:
            for row in csv.DictReader(handle):
                key = row['File_ID'], row['ID']
                if key in assignments:
                    raise ValueError('Duplicate assignment key')
                assignments[key] = row['cluster']
        if set(assignments) != set(reference) or len(reference) != 220082:
            raise ValueError('Assignment/reference exact-key coverage differs')
        groups = collections.defaultdict(lambda: [collections.Counter(), collections.Counter(), set()])
        seen = set()
        with (source_root / sources['raw_leiden_claude']['path']).open() as handle:
            for row in csv.DictReader(handle):
                key = row['File_ID'], row['ID']
                if key in seen or key not in reference:
                    raise ValueError('Duplicate or unmatched prediction key')
                seen.add(key)
                group = groups[assignments[key]]
                group[0][reference[key][0]] += 1
                group[1][reference[key][1]] += 1
                group[2].add(row['leiden__claude'])
        if seen != set(reference) or set(groups) != {r['cluster'] for r in rows}:
            raise ValueError('Prediction key/cluster coverage differs')
        for row in rows:
            group = groups[row['cluster']]
            if group[2] != {row['predicted_label']}:
                raise ValueError('Raw prediction is not the expected constant cluster label')
            for index, vocab in enumerate(VOCABULARIES):
                counts = group[index]; top = max(counts.values())
                majority = sorted(k for k, v in counts.items() if v == top)[0]
                prediction = row['predicted_label']; direct = counts[prediction]
                recovered = direct if prediction != majority else 0
                disagreed = top if prediction != majority else 0
                actual = [sum(counts.values()), top, direct, recovered, disagreed]
                saved = [int(row['n_cells'])] + [int(row[vocab + suffix]) for suffix in
                        ('_bound_cells', '_direct_matches', '_minority_matches', '_majority_mismatches')]
                if actual != saved or majority != row[vocab + '_majority_label']:
                    raise ValueError(f'Cell-source recomputation differs: {row["cluster"]}/{vocab}')
        print('Independently verified all 300 clusters from 220,082 exact-key source cells.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, help='Archived cell_masks workspace for independent cell-source recomputation')
    verify(parser.parse_args().source_root)
