#!/usr/bin/env python3
"""Display current manuscript table cells and byte-preserved release companions."""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from llm_spatial_omics_clustering.manuscript import INPUTS, verify_inputs


def _belongs(label, group):
    return label == group or (label.startswith(group) and label[len(group):].isalpha())


def current_tables(label):
    verify_inputs()
    records = json.loads((INPUTS / 'tables/current_tables.json').read_text())['tables']
    return [record for record in records if _belongs(record['label'], label)]


def companion_tables(label):
    """Return current display labels alongside unchanged deposited filenames."""
    crosswalk = json.loads((ROOT / 'configs/supplementary_table_crosswalk.json').read_text())
    result = []
    for record in crosswalk['tables']:
        if not _belongs(record['current_label'], label):
            continue
        path = ROOT / record['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Companion checksum changed: {path.name}')
        item = dict(record)
        if path.suffix == '.csv':
            item['data'] = pd.read_csv(path)
        elif path.suffix == '.json':
            item['data'] = json.loads(path.read_text())
        result.append(item)
    return result


def table_html(label):
    fragments = [f'<h1>Table {escape(label)}</h1>']
    for record in current_tables(label):
        rows = record['rows']
        frame = pd.DataFrame(rows[1:], columns=rows[0])
        fragments.extend([f'<h2>Table {escape(record["label"])}</h2>',
                          frame.to_html(index=False, escape=True),
                          f'<p>{escape(record.get("notes", ""))}</p>'])
    for record in companion_tables(label):
        fragments.append(f'<h2>Table {escape(record["current_label"])}: {escape(record["filename"])}</h2>')
        fragments.append('<p>Deposited filename retained for provenance. The heading uses the current manuscript number.</p>')
        if isinstance(record.get('data'), pd.DataFrame):
            # Native table cells above take precedence when the manuscript has
            # an edited display table. Complete companion data remain below.
            fragments.append(record['data'].to_html(index=False, escape=True))
        elif 'data' in record:
            fragments.append('<pre>' + escape(json.dumps(record['data'], indent=2)) + '</pre>')
        else:
            fragments.append(f'<p>Preserved source document: {escape(record["path"])}</p>')
    if len(fragments) == 1:
        raise ValueError(f'No current table or companion for {label}')
    return '\n'.join(fragments)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table', choices=[f'S{i}' for i in range(1, 9)])
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/manuscript_replay/tables')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for label in ([args.table] if args.table else [f'S{i}' for i in range(1, 9)]):
        content = table_html(label)
        path = args.output_dir / f'Table_{label}.html'
        path.write_text('<!doctype html><meta charset="utf-8"><style>body{font:14px sans-serif;padding:24px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px;text-align:left}th{background:#eee}</style>' + content)
        print(path)


if __name__ == '__main__':
    main()
