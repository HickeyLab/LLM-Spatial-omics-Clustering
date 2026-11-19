#!/usr/bin/env python3
"""Verify completed B004 reviewer answers and scores offline, without fitting."""
from collections import defaultdict
from pathlib import Path
import argparse
import json
from replay_reviewer47_publication import (ROOT, PENDING_ID, read_json, read_csv,
    verify_manifest, parse_labels, region_metrics, condition_map, replay, write_json)
from replay_astra_prompt_controls import replay as replay_astra


def completed_replay(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Choose a new output directory to preserve prior evidence')
    original = ROOT / 'data/frozen/reviewer47_results_20261111'
    primary = ROOT / 'data/frozen/annotation47_results_20261111'
    evidence = ROOT / 'data/frozen/reviewer47_response_evidence_20261111'
    completion = ROOT / 'data/frozen/reviewer47_deepseek_completion_20261115'
    astra = ROOT / 'data/frozen/astra_prompt_controls_results_20261115'
    for folder in (original, primary, evidence, completion, astra):
        verify_manifest(folder)
    old = read_json(original / 'prediction_freeze.json')['records']
    records = read_json(completion / 'prediction_freeze.json')['records']
    old_by_id = {r['request_id']: r for r in old}
    current_by_id = {r['request_id']: r for r in records}
    if len(old_by_id) != 276 or set(current_by_id) != set(old_by_id):
        raise ValueError('Base request identities changed')
    for old_record in old:
        if old_record['request_id'] != PENDING_ID and current_by_id[old_record['request_id']] != old_record:
            raise ValueError('A previously accepted request was altered')
    pending = old_by_id[PENDING_ID]
    added = current_by_id[PENDING_ID]
    planned_fields = ('request_id', 'cohort', 'family', 'method', 'arm', 'repeat',
        'batch', 'cluster_ids', 'expected_n', 'model_id', 'effort', 'body_sha256',
        'evidence_sha256', 'model_visible_messages_sha256', 'source_request_id')
    if any(pending[k] != added[k] for k in planned_fields):
        raise ValueError('Completion changed the original planned scientific request')
    visible = read_json(completion / 'accepted_response.json')
    if visible['request_id'] != PENDING_ID or visible['finish_reason'] != 'stop':
        raise ValueError('Completed response lacks the expected identity or terminal stop')
    if parse_labels(visible['visible_content'], added['expected_n']) != added['labels']:
        raise ValueError('Completed visible answer and accepted labels differ')
    receipt = visible['response_receipt']
    if receipt['id'] != added['generation_id'] or receipt['model'] != added['model_id']:
        raise ValueError('Completed generation or served model binding differs')
    if added['status'] != 'accepted' or any(r['status'] != 'accepted' for r in records):
        raise ValueError('The completed base bank is not fully delivered')
    # This checks the original 275 visible answers and all request hashes before
    # reading the original reference values. It retains its historical null item.
    legacy = replay(original, primary, evidence, output / 'original_snapshot', False)
    cells = read_csv(primary / 'reference_cells.csv.gz')
    protocol = read_json(primary / 'protocol.json')
    test_regions = sorted(k for k, split in protocol['split'].items() if split == 'test')
    groups = defaultdict(list)
    for row in records:
        groups[row['family'], row['method'], row['arm']].append(row)
    expected = {(r['family'], r['method'], r['arm']): r for r in read_csv(completion / 'set_metrics.csv')}
    if len(groups) != 69 or set(expected) != set(groups):
        raise ValueError('Completed base annotation-set coverage differs')
    truth = [int(row['truth_label_code']) for row in cells]
    regions = [row['File_ID'] for row in cells]
    maximum_difference = 0.0
    for key, request_records in groups.items():
        mapping = condition_map(request_records)
        scores = region_metrics(truth, [mapping[row[key[1]]] for row in cells], regions, test_regions)
        saved = expected[key]
        if saved['status'] != 'complete' or int(saved['delivered_clusters']) != len(mapping):
            raise ValueError('Completed base delivery coverage differs')
        for name in ('agreement', 'fixed28_macro_f1'):
            value = sum(row[name] for row in scores) / 2
            difference = abs(value - float(saved[name]))
            maximum_difference = max(maximum_difference, difference)
            if difference > 1e-12:
                raise ValueError('Independent completed score differs: ' + str(key))
    extension = replay_astra()
    latest = {(r['family'], r['method'], r['arm']): r for r in read_csv(astra / 'set_metrics.csv')}
    if len(latest) != 71 or any(r['status'] != 'complete' for r in latest.values()):
        raise ValueError('Current complete-set coverage differs')
    for key, row in expected.items():
        if latest[key] != row:
            raise ValueError('A base completed set changed in the Astra extension')
    if len(records) + extension['requests_reparsed'] != 284:
        raise ValueError('Current logical request denominator differs')
    total_predictions = sum(r['expected_n'] for r in records) + extension['predictions_reparsed']
    if total_predictions != 20076:
        raise ValueError('Current prediction denominator differs')
    result = {'passed': True, 'original_visible_answers_reparsed': 275,
        'original_accepted_records_preserved': 275, 'newly_admitted_deepseek_items': 1,
        'newly_admitted_deepseek_predictions': added['expected_n'],
        'complete_base_sets': len(groups), 'complete_current_sets': len(latest),
        'accepted_current_items': 284, 'current_predictions': total_predictions,
        'astra_visible_answers_reparsed': extension['requests_reparsed'],
        'unique_cell_keys': legacy['unique_cell_keys'], 'test_cells': legacy['test_cells'],
        'maximum_completed_score_difference': maximum_difference,
        'astra': extension, 'new_generation_calls': 0, 'scheduler_actions': 0, 'fits': 0}
    write_json(output / 'verification.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(completed_replay(args.output), indent=2))
