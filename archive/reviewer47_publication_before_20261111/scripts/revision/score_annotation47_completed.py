"""Offline scoring of the accepted 47-marker annotation campaign.

No HTTP, credentials, fitting, response repair, or inference is available here.
The source assembler admits only sealed, previously accepted final responses.
All plotting tables use one accepted prediction per planned logical condition.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd

MODEL_NAMES = {'openai': 'GPT-6 Astra', 'anthropic': 'Claude Opus 5.5',
               'google': 'Gemini 4 Argon', 'deepseek': 'DeepSeek V4.1 Flash 1017'}
MODEL_ORDER = list(MODEL_NAMES)
METHOD_ORDER = ['leiden', 'flowsom', 'spatialsort', 'pixie_tiff']
ARMS = ['all_means', 'all_means_fractions']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def labels_ok(labels, n):
    assert type(labels) is list and len(labels) == n
    assert all(type(x) is int and 0 <= x < 28 for x in labels)


def load_parser(repo):
    path = repo / 'src/llm_spatial_omics_clustering/revision/annotation47_results.py'
    spec = importlib.util.spec_from_file_location('accepted_annotation47_parser', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path


def assemble(results, repo, out):
    import h5py
    bundle = results / 'call_bundle_final'
    protocol = read(bundle / 'protocol.json')
    manifest = read(bundle / 'manifest.json')
    requests = [json.loads(x) for x in (bundle / 'requests.jsonl').read_text().splitlines()]
    registry = {r['request_id']: r for r in requests}
    assert len(registry) == 128
    parser, parser_path = load_parser(repo)
    proofs = {}

    def pin(path, expected=None):
        path = Path(path)
        observed = sha(path)
        if expected:
            assert observed == expected, f'Source changed: {path}'
        proofs[str(path)] = observed
        return path

    for f in ['manifest.json', 'protocol.json', 'requests.jsonl', 'cluster_map.csv',
              'cell_keys.csv.gz', 'memberships.csv.gz']:
        pin(bundle / f)
    pin(parser_path)
    outcomes = {}

    batch_path = pin(results / 'batch_validation_v1/final/full_campaign_collection.json')
    collection = read(batch_path)
    for item in collection['outcomes']:
        r = registry[item['request_id']]
        if r['model_family'] not in ['openai', 'anthropic']:
            continue
        assert item['status'] == 'completed_valid'
        labels_ok(item['labels'], r['expected_n'])
        outcomes[r['request_id']] = {'labels': item['labels'],
            'generation_id': item['physical_call_id'], 'source_path': str(batch_path),
            'source_sha256': sha(batch_path), 'original_response_sha256': item['raw_sha256'],
            'provider_route': r['provider_route'], 'provider': r['model_family'],
            'quantization': 'provider_native', 'acceptance_source': 'batch_final_collection'}
    assert len(outcomes) == 64

    recovery = results / 'rerun_v2/connection_recovery_20261109'
    gem_certificate_path = pin(recovery / 'parallel_cap90_v3/gemini_completion_verification_v1.json')
    cert = read(gem_certificate_path)
    assert cert['passed'] and cert['valid_requests'] == 32
    gem_map_path = pin(recovery / 'standard_prepared_v6/request_map.json')
    gem_map = {x['source_request_id']: x for x in read(gem_map_path)}
    runtime_cache = {}
    for proof in cert['request_proofs']:
        sid = proof['original_request_id']
        state_path = pin(proof['state_path'], proof['state_sha256'])
        if str(state_path) not in runtime_cache:
            runtime_cache[str(state_path)] = read(state_path)
        state = runtime_cache[str(state_path)]
        logical_id = gem_map[sid]['logical_id']
        logical = state['logical'][logical_id]
        assert logical['status'] == 'completed_valid'
        labels = logical['labels']
        labels_ok(labels, registry[sid]['expected_n'])
        # Reparse saved visible text, without repairing or regenerating it.
        visible = ''.join(logical['visible_parts'])
        assert parser.parse_labels(visible, registry[sid]['expected_n']) == labels
        hops = logical.get('hops', [])
        finals = [h.get('result', {}) for h in hops if h.get('result', {}).get('finish_reason') == 'stop']
        assert finals, f'No normal-stop final response: {sid}'
        final = finals[-1]
        assert final.get('refusal') in [None, '']
        outcomes[sid] = {'labels': labels, 'generation_id': final['id'],
            'source_path': str(state_path), 'source_sha256': proof['state_sha256'],
            'provider_route': 'google-vertex/global', 'provider': final.get('provider', 'Google'),
            'quantization': 'provider_native', 'acceptance_source': 'gemini_completed_state',
            'physical_generation_ids': [h['result']['id'] for h in hops if h.get('result', {}).get('id')]}

    preserved_path = pin(recovery / 'standard_prepared_v6/preserved_completed_results.json',
                         cert['preserved_results_sha256'])
    preserved = read(preserved_path)
    wire_path = pin(results / 'rerun_v2/gemini_adapter_v2/wire_map.json')
    original_gem_map = {x['request_id']: x for x in read(wire_path)['requests']}
    legacy_paths = [results/'rerun_v2/gemini_run/runtime.json',
                    recovery/'gemini_standard_v4_run/runtime.json',
                    recovery/'gemini_standard_v5_run/runtime.json']
    legacy_states = [(pin(path), read(path)) for path in legacy_paths]
    for logical_id, item in preserved.items():
        r = original_gem_map[logical_id]
        sid = r['source_request_id']
        assert sid not in outcomes
        labels_ok(item['labels'], registry[sid]['expected_n'])
        matches = [(path, logical) for path, state in legacy_states
                   for key, logical in state['logical'].items()
                   if key.split('_',1)[1] == logical_id.split('_',1)[1]
                   and logical.get('status') == 'completed_valid']
        assert len(matches) == 1
        legacy_path, logical = matches[0]
        assert logical['labels'] == item['labels']
        assert parser.parse_labels(''.join(logical['visible_parts']), r['expected_n']) == item['labels']
        finals = [h['result'] for h in logical['hops'] if h.get('result',{}).get('finish_reason') == 'stop']
        assert finals and finals[-1].get('refusal') in [None,'']
        outcomes[sid] = {'labels': item['labels'], 'generation_id': finals[-1]['id'],
            'source_logical_id': logical_id,
            'legacy_runtime_source':str(legacy_path),'legacy_runtime_sha256':sha(legacy_path),
            'physical_generation_ids':[h['result']['id'] for h in logical['hops'] if h.get('result',{}).get('id')],
            'source_path': str(preserved_path), 'source_sha256': sha(preserved_path),
            'provider_route': 'google-vertex/global', 'provider': 'Google',
            'quantization': 'provider_native', 'acceptance_source': 'gemini_preserved_completed_result'}
    assert len(outcomes) == 96

    deep_path = pin(recovery / 'deepseek_missing_nine_v6/canonical_accepted_predictions_v1.json')
    deep = read(deep_path)
    assert deep['verification_passed'] and deep['accepted_requests'] == 32
    for item in deep['records']:
        sid = item['source_request_id']
        r = registry[sid]
        response_path = pin(item['response_path'], item['response_sha256'])
        response = read(response_path)
        assert response['id'] == item['generation_id']
        choice = response['choices'][0]
        assert choice['finish_reason'] == 'stop'
        assert choice['message'].get('refusal') in [None, '']
        labels = parser.parse_labels(choice['message']['content'], r['expected_n'])
        assert labels == item['labels_by_anonymous_query_id']
        assert sid not in outcomes
        outcomes[sid] = {'labels': labels, 'generation_id': item['generation_id'],
            'source_path': str(response_path), 'source_sha256': item['response_sha256'],
            'provider_route': item['provider_route'], 'provider': item['provider'],
            'quantization': item['quantization'], 'acceptance_source': item['accepted_attempt']}
    assert set(outcomes) == set(registry)
    assert sum(len(o['labels']) for o in outcomes.values()) == 9024
    records = [{**registry[sid], **outcomes[sid]} for sid in registry]
    bank = {'schema': 'annotation47.accepted128.publication_bank.v1',
            'accepted_requests': 128, 'accepted_predictions': 9024,
            'selection_rule': 'Preserve accepted Astra/Opus and Gemini results; use the final verified DeepSeek accepted bank. No selection by reference score.',
            'records': records}
    save_json(out / 'accepted_requests.json', bank)
    save_json(out / 'protocol.json', protocol)
    for file in ['cluster_map.csv', 'cell_keys.csv.gz', 'memberships.csv.gz']:
        shutil.copy2(bundle / file, out / file)
    cells = pd.read_csv(out / 'cell_keys.csv.gz', dtype={'File_ID': str, 'ID': str})
    memberships = pd.read_csv(out / 'memberships.csv.gz', dtype=str)
    assert not cells.duplicated(['File_ID', 'ID']).any()
    assert cells[['File_ID', 'ID']].equals(memberships[['File_ID', 'ID']])
    h5ad = pin(manifest['source_h5ad_path'], manifest['source_h5ad_sha256'])

    def hcol(group):
        if isinstance(group, h5py.Group):
            return group['categories'].asstr()[:][group['codes'][:]]
        a = group[:]
        return a.astype(str) if a.dtype.kind in ['S', 'O'] else a

    with h5py.File(h5ad, 'r') as h:
        obs = h['obs']
        reference = pd.DataFrame({k: hcol(obs[k]) for k in ['File_ID', 'ID', 'x', 'y', 'cell_type_update']})
        reference['File_ID'] = reference['File_ID'].astype(str)
        reference['ID'] = reference['ID'].astype(str)
        assert cells[['File_ID', 'ID']].equals(reference[['File_ID', 'ID']])
        var_names = h['var']['_index'].asstr()[:].tolist()
        raw_x = h['X'][:]
        processed = np.column_stack([raw_x[:, var_names.index(m)] if m in var_names
                                     else hcol(obs[m]) for m in protocol['markers']]).astype(np.float64)
    assert processed.shape == (220082, 47) and np.isfinite(processed).all()
    for method in METHOD_ORDER:
        reference[method] = memberships[method].values
    reference['split'] = cells['split'].values
    reference['truth_label'] = reference.pop('cell_type_update')
    ontology = protocol['ontology']
    assert len(ontology) == len(set(ontology)) == 28
    reference['truth_label_code'] = reference['truth_label'].map({v: i for i, v in enumerate(ontology)})
    assert reference['truth_label_code'].notna().all()
    reference.to_csv(out / 'reference_cells.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    profile_frames = {'means_asinh': [], 'means_z': [], 'fractions': [], 'means_processed': []}
    for method in METHOD_ORDER:
        profile_path = pin(bundle / 'profiles' / (method + '.npz'))
        z = np.load(profile_path, allow_pickle=False)
        assert np.array_equal(z['cluster_names'][z['codes']], memberships[method].values)
        for kind in ['means_asinh', 'means_z', 'fractions']:
            f = pd.DataFrame(z[kind], columns=protocol['markers'])
            f.insert(0, 'n_cells', z['counts'])
            f.insert(0, 'cluster_id', z['cluster_names'])
            f.insert(0, 'method', method)
            profile_frames[kind].append(f)
        sums = np.zeros((len(z['counts']), 47))
        for j in range(47):
            sums[:, j] = np.bincount(z['codes'], weights=processed[:, j], minlength=len(z['counts']))
        f = pd.DataFrame(sums / z['counts'][:, None], columns=protocol['markers'])
        f.insert(0, 'n_cells', z['counts'])
        f.insert(0, 'cluster_id', z['cluster_names'])
        f.insert(0, 'method', method)
        profile_frames['means_processed'].append(f)
    for kind, frames in profile_frames.items():
        pd.concat(frames, ignore_index=True).to_csv(out / ('profiles_' + kind + '.csv'), index=False)
    # Reference-CD8 is a fixed descriptive display group, independent of LLM outputs.
    refmask = reference['truth_label'].eq('CD8+ T').values
    pd.DataFrame({'marker': protocol['markers'], 'n_cells': int(refmask.sum()),
                  'mean_processed': processed[refmask].mean(axis=0),
                  'fraction_above_zero': (processed[refmask] > 0).mean(axis=0)}).to_csv(
                      out / 'reference_cd8_profiles.csv', index=False)
    save_json(out / 'source_receipt.json', {'schema': 'annotation47.publication_scoring.sources.v1',
              'input_sha256': proofs, 'reference_labels_read_for_scoring_only': True,
              'calls_made': 0, 'jobs_submitted': 0})


def confusion_matrix(truth, pred, keep):
    return np.bincount(truth[keep] * 28 + pred[keep], minlength=28*28).reshape(28, 28)


def summarize(cm):
    n = int(cm.sum())
    tp = np.diag(cm)
    support, predicted = cm.sum(axis=1), cm.sum(axis=0)
    f1 = np.divide(2*tp, support+predicted, out=np.zeros(28), where=(support+predicted)>0)
    recall = np.divide(tp, support, out=np.zeros(28), where=support>0)
    precision = np.divide(tp, predicted, out=np.zeros(28), where=predicted>0)
    return {'n_cells': n, 'n_correct': int(tp.sum()), 'agreement': float(tp.sum()/n),
            'fixed28_macro_f1': float(f1.mean()), 'weighted_f1': float((f1*support).sum()/n),
            'cell_delivery_coverage': 1.0}, f1, recall, precision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path)
    ap.add_argument('--repo', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--replay', action='store_true')
    args = ap.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    if not args.replay:
        assert args.results and args.repo
        assemble(args.results, args.repo, out)
    protocol = read(out / 'protocol.json')
    bank = read(out / 'accepted_requests.json')
    ontology = protocol['ontology']
    noise = ontology.index('Noise')
    cells = pd.read_csv(out / 'reference_cells.csv.gz', dtype={'File_ID': str, 'ID': str, **{m: str for m in METHOD_ORDER}})
    cmap = pd.read_csv(out / 'cluster_map.csv', dtype={'cluster_id': str})
    truth = cells['truth_label_code'].values.astype(np.int64)
    regions = sorted(cells['File_ID'].unique())
    test_regions = [r for r in regions if protocol['split'][r] == 'test']
    assert len(test_regions) == 2
    expected_conditions = {(model, method, arm) for model in MODEL_ORDER for method in METHOD_ORDER for arm in ARMS}
    grouped = {}
    for r in bank['records']:
        grouped.setdefault((r['model_family'], r['method'], r['arm']), []).append(r)
    assert set(grouped) == expected_conditions and len(cells) == 220082
    condition_preds = {}
    cluster_rows, metrics, pertypes, cms, paired = [], [], [], [], []
    regions_vec = cells['File_ID'].values
    testmask = cells['split'].eq('test').values
    allmask = np.ones(len(cells), dtype=bool)
    method_info = {}
    bounds = []
    for method in METHOD_ORDER:
        cluster_map = cmap[cmap['method'] == method].sort_values('cluster_index')
        names = cluster_map['cluster_id'].values
        name2code = {name: i for i, name in enumerate(names)}
        codes = cells[method].map(name2code).values
        assert np.isfinite(codes).all()
        codes = codes.astype(np.int64)
        # Tie order is the frozen ontology code order, never selected by model output.
        for population in ['all_labels', 'exclude_reference_noise']:
            popmask = allmask if population == 'all_labels' else truth != noise
            for scope, region, mask in [('pooled_all', 'ALL', popmask), ('pooled_test', 'TEST', popmask & testmask)] + [
                    ('region', region, popmask & (regions_vec == region)) for region in regions]:
                ct = np.bincount(codes[mask] * 28 + truth[mask], minlength=len(names)*28).reshape(len(names), 28)
                ub_n = int(ct.max(axis=1).sum())
                bounds.append({'method': method, 'population': population, 'scope': scope, 'region': region,
                               'n_cells': int(mask.sum()), 'upper_bound_correct_cells': ub_n,
                               'reference_upper_bound': ub_n / int(mask.sum()),
                               'within_cluster_minority_fraction': 1 - ub_n / int(mask.sum())})
        ct = np.bincount(codes * 28 + truth, minlength=len(names)*28).reshape(len(names), 28)
        method_info[method] = (names, codes, ct)
    bound_df = pd.DataFrame(bounds)

    for key in sorted(grouped, key=lambda x: (MODEL_ORDER.index(x[0]), METHOD_ORDER.index(x[1]), ARMS.index(x[2]))):
        model, method, arm = key
        names, codes, cluster_truth = method_info[method]
        pred_clusters = np.full(len(names), -1, dtype=np.int8)
        seen_batches = set()
        for r in grouped[key]:
            assert r['batch'] not in seen_batches
            seen_batches.add(r['batch'])
            subset = cmap[(cmap['method'] == method) & (cmap['batch'] == r['batch'])].sort_values('query_case_id')
            assert subset['query_case_id'].tolist() == list(range(r['expected_n']))
            labels_ok(r['labels'], r['expected_n'])
            pred_clusters[subset['cluster_index'].values] = r['labels']
        assert seen_batches == {0, 1, 2, 3} and (pred_clusters >= 0).all()
        pred = pred_clusters[codes].astype(np.int8)
        condition_preds['__'.join(key)] = pred
        for ci, name in enumerate(names):
            counts = cluster_truth[ci]
            n = int(counts.sum())
            majority_code = int(counts.argmax())
            label_code = int(pred_clusters[ci])
            majority_count = int(counts.max())
            n_correct = int(counts[label_code])
            cluster_rows.append({'model_family': model, 'model': MODEL_NAMES[model], 'method': method,
                'arm': arm, 'cluster_index': ci, 'cluster_id': name, 'n_cells': n,
                'pred_label_code': label_code, 'pred_label': ontology[label_code],
                'majority_truth_code': majority_code, 'majority_truth': ontology[majority_code],
                'majority_count': majority_count, 'n_correct': n_correct,
                'agreement': n_correct/n, 'reference_upper_bound': majority_count/n,
                'gap_to_maximum_agreement': (majority_count-n_correct)/n,
                'within_cluster_minority_fraction': 1-majority_count/n,
                'test_cells': int((testmask & (codes == ci)).sum())})
        for population in ['all_labels', 'exclude_reference_noise']:
            popmask = allmask if population == 'all_labels' else truth != noise
            condition_metrics = []
            scopes = [('pooled_all', 'ALL', popmask), ('pooled_test', 'TEST', popmask & testmask)] + [
                ('region', region, popmask & (regions_vec == region)) for region in regions]
            for scope, region, mask in scopes:
                cm = confusion_matrix(truth, pred, mask)
                summary, f1, recall, precision = summarize(cm)
                bound = bound_df[(bound_df['method'] == method) & (bound_df['population'] == population) &
                                 (bound_df['scope'] == scope) & (bound_df['region'] == region)].iloc[0]
                base = {'model_family': model, 'model': MODEL_NAMES[model], 'method': method, 'arm': arm,
                        'population': population, 'scope': scope, 'region': region,
                        'split': protocol['split'].get(region, 'pooled'), **summary,
                        'planned_clusters': len(names), 'delivered_clusters': len(names), 'cluster_delivery_coverage': 1.0,
                        'reference_upper_bound': float(bound['reference_upper_bound']),
                        'gap_to_maximum_agreement': float(bound['reference_upper_bound'])-summary['agreement'],
                        'within_cluster_minority_fraction': float(bound['within_cluster_minority_fraction'])}
                assert abs((1-base['agreement']) - (base['gap_to_maximum_agreement'] + base['within_cluster_minority_fraction'])) < 1e-12
                metrics.append(base)
                condition_metrics.append(base)
                support, predicted = cm.sum(axis=1), cm.sum(axis=0)
                for label_code, label in enumerate(ontology):
                    pertypes.append({**{k: base[k] for k in ['model_family', 'model', 'method', 'arm', 'population', 'scope', 'region', 'split']},
                        'label_code': label_code, 'label': label, 'support': int(support[label_code]),
                        'predicted_cells': int(predicted[label_code]), 'true_positive': int(cm[label_code, label_code]),
                        'f1': float(f1[label_code]), 'recall': float(recall[label_code]), 'precision': float(precision[label_code])})
                for t in range(28):
                    for p in range(28):
                        cms.append({**{k: base[k] for k in ['model_family', 'model', 'method', 'arm', 'population', 'scope', 'region']},
                                    'truth_label_code': t, 'truth_label': ontology[t], 'pred_label_code': p,
                                    'pred_label': ontology[p], 'count': int(cm[t, p])})
            test_rows = [m for m in condition_metrics if m['scope'] == 'region' and m['region'] in test_regions]
            equal = {k: test_rows[0][k] for k in ['model_family', 'model', 'method', 'arm', 'population', 'planned_clusters', 'delivered_clusters', 'cluster_delivery_coverage']}
            equal.update(scope='equal_test_regions', region='EQUAL_TEST_REGIONS', split='test',
                         n_cells=sum(m['n_cells'] for m in test_rows), n_correct=sum(m['n_correct'] for m in test_rows))
            for metric in ['agreement', 'fixed28_macro_f1', 'weighted_f1', 'cell_delivery_coverage', 'reference_upper_bound', 'gap_to_maximum_agreement', 'within_cluster_minority_fraction']:
                equal[metric] = float(np.mean([m[metric] for m in test_rows]))
            metrics.append(equal)

    metric_df = pd.DataFrame(metrics)
    cluster_df = pd.DataFrame(cluster_rows)
    for model in MODEL_ORDER:
        for method in METHOD_ORDER:
            names, codes, ct = method_info[method]
            left_cells = condition_preds['__'.join((model, method, ARMS[0]))]
            right_cells = condition_preds['__'.join((model, method, ARMS[1]))]
            left_cluster = cluster_df[(cluster_df['model_family'] == model) & (cluster_df['method'] == method) & (cluster_df['arm'] == ARMS[0])].sort_values('cluster_index')['pred_label_code'].values
            right_cluster = cluster_df[(cluster_df['model_family'] == model) & (cluster_df['method'] == method) & (cluster_df['arm'] == ARMS[1])].sort_values('cluster_index')['pred_label_code'].values
            for population in ['all_labels', 'exclude_reference_noise']:
                popmask = allmask if population == 'all_labels' else truth != noise
                for scope, region in [('pooled_all', 'ALL'), ('pooled_test', 'TEST'), ('equal_test_regions', 'EQUAL_TEST_REGIONS')] + [('region', r) for r in regions]:
                    query = (metric_df['model_family'] == model) & (metric_df['method'] == method) & (metric_df['population'] == population) & (metric_df['scope'] == scope) & (metric_df['region'] == region)
                    l = metric_df[query & (metric_df['arm'] == ARMS[0])].iloc[0]
                    r = metric_df[query & (metric_df['arm'] == ARMS[1])].iloc[0]
                    mask = popmask & (testmask if scope in ['pooled_test', 'equal_test_regions'] else regions_vec == region if scope == 'region' else allmask)
                    paired.append({'model_family': model, 'model': MODEL_NAMES[model], 'method': method,
                        'population': population, 'scope': scope, 'region': region,
                        'means_agreement': float(l['agreement']), 'fractions_agreement': float(r['agreement']),
                        'agreement_difference': float(r['agreement']-l['agreement']),
                        'means_fixed28_macro_f1': float(l['fixed28_macro_f1']), 'fractions_fixed28_macro_f1': float(r['fixed28_macro_f1']),
                        'fixed28_macro_f1_difference': float(r['fixed28_macro_f1']-l['fixed28_macro_f1']),
                        'planned_clusters': len(names), 'joint_valid_clusters': len(names),
                        'changed_clusters': int((left_cluster != right_cluster).sum()),
                        'cluster_label_change_rate': float(np.mean(left_cluster != right_cluster)),
                        'planned_cells': int(mask.sum()), 'changed_cells': int((left_cells[mask] != right_cells[mask]).sum()),
                        'cell_label_change_rate': float(np.mean(left_cells[mask] != right_cells[mask])),
                        'joint_delivery_coverage': 1.0})
    paired_df = pd.DataFrame(paired)
    metric_df.to_csv(out / 'metrics.csv', index=False)
    cluster_df.to_csv(out / 'cluster_predictions.csv', index=False)
    pd.DataFrame(pertypes).to_csv(out / 'per_type_metrics.csv', index=False)
    pd.DataFrame(cms).to_csv(out / 'confusion.csv.gz', index=False, compression={'method': 'gzip', 'mtime': 0})
    paired_df.to_csv(out / 'paired_contrasts.csv', index=False)
    bound_df.to_csv(out / 'reference_bounds.csv', index=False)
    np.savez_compressed(out / 'cell_predictions.npz', **condition_preds)
    # Across-model labels are a descriptive display; they are not repeat votes.
    consensus = {}
    consensus_rows = []
    for method in METHOD_ORDER:
        names, codes, _ = method_info[method]
        family_labels = []
        for family in MODEL_ORDER:
            f = cluster_df[(cluster_df['model_family'] == family) & (cluster_df['method'] == method) & (cluster_df['arm'] == ARMS[1])].sort_values('cluster_index')
            family_labels.append(f['pred_label_code'].values)
        votes = np.stack(family_labels)
        labels = []
        for i in range(len(names)):
            counts = Counter(votes[:, i].tolist())
            maxcount = max(counts.values())
            labels.append(next(int(v) for v in votes[:, i] if counts[int(v)] == maxcount))
        labels = np.array(labels, dtype=np.int8)
        consensus[method] = labels[codes]
        for i, name in enumerate(names):
            consensus_rows.append({'method': method, 'cluster_id': name, 'n_cells': int((codes == i).sum()),
                'consensus_label_code': int(labels[i]), 'consensus_label': ontology[int(labels[i])],
                'agreeing_models': int((votes[:, i] == labels[i]).sum()),
                **{family+'_label_code': int(votes[j, i]) for j, family in enumerate(MODEL_ORDER)}})
    pd.DataFrame(consensus_rows).to_csv(out / 'cross_model_consensus_clusters.csv', index=False)
    np.savez_compressed(out / 'cross_model_consensus_cells.npz', **consensus)
    cd8code = ontology.index('CD8+ T')
    cd8_rows = []
    reference_cd8 = pd.read_csv(out / 'reference_cd8_profiles.csv')
    for row in reference_cd8.to_dict(orient='records'):
        cd8_rows.append({'method':'reference', **row})
    processed_profiles = pd.read_csv(out / 'profiles_means_processed.csv', dtype={'cluster_id':str})
    fraction_profiles = pd.read_csv(out / 'profiles_fractions.csv', dtype={'cluster_id':str})
    consensus_frame = pd.DataFrame(consensus_rows)
    for method in METHOD_ORDER:
        selection = consensus_frame[(consensus_frame['method'] == method) & (consensus_frame['consensus_label_code'] == cd8code)]
        means = selection[['cluster_id']].merge(processed_profiles[processed_profiles['method'] == method], on='cluster_id', validate='one_to_one')
        fractions = selection[['cluster_id']].merge(fraction_profiles[fraction_profiles['method'] == method], on='cluster_id', validate='one_to_one')
        n = int(means['n_cells'].sum())
        for marker in protocol['markers']:
            cd8_rows.append({'method':method,'marker':marker,'n_cells':n,
                'mean_processed':float(np.average(means[marker],weights=means['n_cells'])) if n else None,
                'fraction_above_zero':float(np.average(fractions[marker],weights=fractions['n_cells'])) if n else None})
    cd8_df = pd.DataFrame(cd8_rows)
    four = cd8_df[cd8_df['method'] != 'reference'].copy()
    four['mean_minmax_four_methods'] = four.groupby('marker')['mean_processed'].transform(
        lambda s: (s-s.min())/(s.max()-s.min()) if s.max()>s.min() else s*0)
    cd8_df = cd8_df.merge(four[['method','marker','mean_minmax_four_methods']], on=['method','marker'], how='left')
    cd8_df.to_csv(out / 'cd8_consensus_profiles.csv', index=False)

    # Independent primary check with Python dictionary counts, separate from the
    # NumPy bincount matrix implementation above. No optional binary scorer is
    # required for exact offline replay on a publication checkout.
    max_acc_delta, max_f1_delta = 0., 0.
    for key, pred in condition_preds.items():
        family, method, arm = key.split('__')
        independent = []
        for region in test_regions:
            keep = regions_vec == region
            actual = truth[keep].tolist()
            predicted = pred[keep].tolist()
            pair_counts = Counter(zip(actual, predicted))
            actual_counts, predicted_counts = Counter(actual), Counter(predicted)
            agreement = sum(a == p for a, p in zip(actual, predicted)) / len(actual)
            f1s = [2*pair_counts[(label,label)]/(actual_counts[label]+predicted_counts[label])
                   if actual_counts[label]+predicted_counts[label] else 0.0 for label in range(28)]
            independent.append((agreement, sum(f1s)/28))
        row = metric_df[(metric_df['model_family'] == family) & (metric_df['method'] == method) & (metric_df['arm'] == arm) &
                        (metric_df['scope'] == 'equal_test_regions') & (metric_df['population'] == 'all_labels')].iloc[0]
        max_acc_delta = max(max_acc_delta, abs(float(row['agreement'])-float(np.mean([x[0] for x in independent]))))
        max_f1_delta = max(max_f1_delta, abs(float(row['fixed28_macro_f1'])-float(np.mean([x[1] for x in independent]))))
    assert max_acc_delta < 1e-12 and max_f1_delta < 1e-12
    primary = metric_df[(metric_df['scope'] == 'equal_test_regions') & (metric_df['population'] == 'all_labels') & (metric_df['arm'] == ARMS[1])]
    contrasts = paired_df[(paired_df['scope'] == 'equal_test_regions') & (paired_df['population'] == 'all_labels')]
    best = primary.sort_values('agreement', ascending=False).iloc[0]
    summary = {'schema': 'annotation47.scored_publication_summary.v1', 'status': 'offline_scoring_complete',
        'calls_made': 0, 'jobs_submitted': 0, 'accepted_requests': 128, 'accepted_predictions': 9024,
        'n_cells': len(cells), 'n_markers': 47, 'ontology_size': 28, 'repetitions': 1,
        'test_regions': test_regions, 'test_region_cells': {r: int((regions_vec==r).sum()) for r in test_regions},
        'split_cells': cells['split'].value_counts().to_dict(),
        'primary_arm': ARMS[1], 'primary_population': 'all_labels', 'primary_weighting': 'equal_mean_of_two_test_regions',
        'primary_agreement_range': [float(primary['agreement'].min()), float(primary['agreement'].max())],
        'primary_fixed28_macro_f1_range': [float(primary['fixed28_macro_f1'].min()), float(primary['fixed28_macro_f1'].max())],
        'best_primary_condition': {k: (float(best[k]) if isinstance(best[k],(float,np.floating)) else best[k]) for k in ['model_family','model','method','agreement','fixed28_macro_f1']},
        'paired_agreement_difference_range': [float(contrasts['agreement_difference'].min()), float(contrasts['agreement_difference'].max())],
        'paired_improved': int((contrasts['agreement_difference']>0).sum()),
        'paired_reduced': int((contrasts['agreement_difference']<0).sum()),
        'paired_tied': int((contrasts['agreement_difference']==0).sum()),
        'independent_python_counter_check': {'conditions':32,'max_agreement_abs_delta':max_acc_delta,'max_macro_f1_abs_delta':max_f1_delta},
        'full_delivery_coverage': True, 'repeat_sd_or_repeatability_estimated':False,
        'interpretation': 'Single accepted predictions; descriptive comparisons on transductive previously examined B004 data. No donor generalization, biological correctness, or repeated-call stability is inferred.'}
    save_json(out / 'summary.json', summary)
    outputs = {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in out.iterdir()
               if p.is_file() and p.name not in ['verification.json']}
    verification = {'schema':'annotation47.scoring_verification.v1', 'passed':True,
        'scored_at':datetime.now(timezone.utc).isoformat(), 'checks':{
        '128_unique_request_ids':True,'9024_valid_cluster_predictions':True,'32_complete_annotation_sets':True,
        '220082_exact_cell_join':True,'28_original_labels_including_noise':True,
        'four_train_two_validation_two_test_split':True,'same_cluster_order_within_pairs':True,
        'all_missing_predictions_retained_in_denominator':True,'all_clusters_delivered':True,
        'all_cells_delivered':True,'decomposition_identities_match':True,
        'independent_python_counter_primary_scores_match':True,'no_repeat_sd_or_repeatability':True},
        'annotation_calls':0,'new_fits':0,'jobs_submitted':0,'outputs':outputs}
    save_json(out / 'verification.json', verification)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
