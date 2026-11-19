#!/usr/bin/env python3
"""Replay the completed Astra controls offline, without generation or fitting."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from replay_reviewer47_publication import (verify_manifest, read_json, read_csv,
    canonical_sha, condition_map, region_metrics)
from llm_spatial_omics_clustering.revision.annotation47_results import parse_labels

def replay():
    directory = ROOT / 'data/frozen/astra_prompt_controls_results_20261115'
    base = ROOT / 'data/frozen/reviewer47_deepseek_completion_20261115'
    primary = ROOT / 'data/frozen/annotation47_results_20261111'
    for path in (directory, base, primary):
        verify_manifest(path)
    records = read_json(directory / 'prediction_freeze.json')['records']
    planned = {r['request_id']: r for r in records}
    bodies = {r['custom_id']: r['body'] for r in
              [json.loads(line) for line in (directory / 'requests.jsonl').read_text().splitlines()]}
    assert len(planned) == len(bodies) == 8
    accepted, generations = set(), set()
    for line in (directory / 'raw_output.jsonl').read_text().splitlines():
        item = json.loads(line)
        rid = item['custom_id']
        assert rid in planned and rid not in accepted
        record = planned[rid]
        assert canonical_sha(bodies[rid]) == record['native_body_sha256']
        assert item.get('error') is None and item['response']['status_code'] == 200
        body = item['response']['body']
        assert body['model'] == 'gpt-6-astra' and len(body['choices']) == 1
        choice = body['choices'][0]
        assert choice['finish_reason'] == 'stop'
        assert not choice['message'].get('refusal') and not choice['message'].get('tool_calls')
        assert parse_labels(choice['message']['content'], record['expected_n']) == record['labels']
        assert body['id'] == record['generation_id'] and body['id'] not in generations
        accepted.add(rid)
        generations.add(body['id'])
    assert accepted == set(planned)
    # Fixed reference labels enter only after output and request validation.
    cells = read_csv(primary / 'reference_cells.csv.gz')
    protocol = read_json(primary / 'protocol.json')
    regions = sorted(k for k, value in protocol['split'].items() if value == 'test')
    prior = read_json(base / 'prediction_freeze.json')['records']
    baseline = condition_map([r for r in prior if (r['family'], r['method'], r['arm']) ==
                              ('openai', 'leiden', 'all_means_fractions')])
    saved = {(r['family'], r['method'], r['arm']): r for r in read_csv(directory / 'set_metrics.csv')}
    scores = {}
    for arm in ('method_named', 'neighborhood'):
        mapping = condition_map([r for r in records if r['arm'] == arm])
        assert set(mapping) == set(baseline) and len(mapping) == 300
        regional = region_metrics([int(c['truth_label_code']) for c in cells],
            [mapping[c['leiden']] for c in cells], [c['File_ID'] for c in cells], regions)
        metrics = {key: sum(r[key] for r in regional) / 2 for key in ('agreement', 'fixed28_macro_f1')}
        for key, value in metrics.items():
            assert abs(value - float(saved['openai', 'leiden', arm][key])) < 1e-12
        scores[arm] = metrics
    return {'passed': True, 'requests_reparsed': 8, 'predictions_reparsed': 600,
            'planned_clusters_per_condition': 300, 'test_cells': 69576,
            'equal_region_scores': scores, 'new_generation_calls': 0, 'fits': 0,
            'transport_qualification': 'Native OpenAI Batch controls reuse an OpenRouter Batch baseline.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    result = replay()
    if args.receipt:
        args.receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
