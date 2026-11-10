"""Adversarial output, serving identity, accounting and denominator checks."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from llm_spatial_omics_clustering.revision.annotation47_results import (
    collect_results, delivery_coverage, new_ledger, normalize_response,
    paired_label_changes, paired_region_contrast, parse_labels,
    persist_submission_event, score_regions, strict_json, transition_submission,
)

ROOT = Path(__file__).resolve().parents[1]


def request(request_id='q0', family='openai'):
    identities = {
        'openai': ('openai/gpt-6-astra', 'openai/gpt-6-astra-20260903', 'openai'),
        'google': ('google/gemini-4-argon', 'google/gemini-4-argon-20261013', 'google-vertex/global'),
    }
    model, canonical, provider = identities[family]
    return dict(request_id=request_id, model_id=model, canonical_slug_expected=canonical,
                provider_route=provider, expected_n=2)


def response(req=None, **overrides):
    req = req or request()
    value = {'id': 'gen_' + req['request_id'], 'model': req['canonical_slug_expected'],
             'provider_route': req['provider_route'],
             'choices': [{'finish_reason': 'stop', 'message': {
                 'role': 'assistant', 'content': '{"a":[{"i":1,"l":21},{"i":0,"l":7}]}'}}],
             'usage': {'prompt_tokens': 100, 'completion_tokens': 200, 'total_tokens': 300,
                       'cost': 0.25}}
    value.update(overrides)
    return value


def wrapped(req=None, **overrides):
    req = req or request()
    return {'custom_id': req['request_id'], 'response': {
        'status_code': 200, 'request_id': 'up_' + req['request_id'],
        'body': response(req, **overrides)}, 'error': None}


class StrictAnnotation47ResponseTests(unittest.TestCase):
    def test_exact_reordered_valid_integer_codes(self):
        self.assertEqual(parse_labels('{"a":[{"i":1,"l":21},{"i":0,"l":7}]}', 2), [7, 21])

    def test_extra_missing_duplicate_wrong_types_out_of_range(self):
        invalid = [
            '{"a":[]}', '{"a":[{"i":0,"l":7}]}',
            '{"a":[{"i":0,"l":7},{"i":0,"l":8}]}',
            '{"a":[{"i":0,"l":7},{"i":2,"l":8}]}',
            '{"a":[{"i":0,"l":7},{"i":1,"l":28}]}',
            '{"a":[{"i":0,"l":7},{"i":1,"l":-1}]}',
            '{"a":[{"i":0,"l":7},{"i":1,"l":"8"}]}',
            '{"a":[{"i":0,"l":7},{"i":1,"l":8.0}]}',
            '{"a":[{"i":0,"l":7},{"i":true,"l":8}]}',
            '{"a":[{"i":0,"l":7},{"i":1,"l":false}]}',
            '{"a":[{"i":0,"l":7,"note":"good"},{"i":1,"l":8}]}',
            '{"a":[{"i":0,"l":7},{"i":1,"l":8}],"explanation":"x"}',
            '```json\n{"a":[{"i":0,"l":7},{"i":1,"l":8}]}\n```',
        ]
        for content in invalid:
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_labels(content, 2)

    def test_duplicate_json_keys_and_nonfinite_constants(self):
        for content in ['{"a":[],"a":[]}', '{"a":[{"i":0,"i":1,"l":7}]}',
                        '{"a":NaN}', '{"a":Infinity}']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                strict_json(content)

    def test_valid_chat_and_batch_wrappers_preserve_hash_and_charge(self):
        for raw in [response(), wrapped()]:
            result = normalize_response(json.dumps(raw), request())
            self.assertEqual(result['status'], 'completed_valid')
            self.assertEqual(result['labels'], [7, 21])
            self.assertEqual(result['cost_usd'], '0.25')
            self.assertEqual(result['raw_sha256'], hashlib.sha256(json.dumps(raw).encode()).hexdigest())

    def test_atomic_no_partial_salvage_but_charge_retained(self):
        raw = response()
        raw['choices'][0]['message']['content'] = '{"a":[{"i":0,"l":7}]}'
        result = normalize_response(raw, request())
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(result['labels'], [None, None])
        self.assertEqual(result['cost_usd'], '0.25')

    def test_empty_choices_refusal_truncation_nonterminal_errors_all_rejected(self):
        cases = [response(choices=[]), response(status='in_progress'), response(error={'message': 'x'})]
        for finish in ['length', 'content_filter', 'refusal', None]:
            raw = response()
            raw['choices'][0]['finish_reason'] = finish
            cases.append(raw)
        for refusal in ['refused', {'category': 'policy'}]:
            raw = response()
            raw['choices'][0]['message']['refusal'] = refusal
            cases.append(raw)
        raw = wrapped()
        raw['response']['status_code'] = 429
        cases.append(raw)
        for raw in cases:
            with self.subTest(raw=raw):
                result = normalize_response(raw, request())
                self.assertEqual(result['status'], 'invalid')
                self.assertEqual(result['labels'], [None, None])

    def test_base_model_needs_bound_canonical_receipt(self):
        req = request()
        raw = response(model=req['model_id'])
        self.assertEqual(normalize_response(raw, req)['status'], 'identity_unverified')
        receipt = dict(request_id='q0', model_id=req['model_id'],
                       canonical_slug=req['canonical_slug_expected'], provider_route='openai')
        self.assertEqual(normalize_response(raw, req, receipt)['status'], 'completed_valid')
        receipt['request_id'] = 'wrong-request'
        self.assertEqual(normalize_response(raw, req, receipt)['status'], 'identity_unverified')

    def test_google_display_name_is_not_exact_vertex_global_route(self):
        req = request(family='google')
        raw = response(req)
        raw.pop('provider_route')
        raw['provider'] = 'Google'
        self.assertEqual(normalize_response(raw, req)['status'], 'identity_unverified')
        receipt = dict(request_ids=['q0'], provider_route='google-vertex/global',
                       canonical_slug=req['canonical_slug_expected'], model_id=req['model_id'])
        self.assertEqual(normalize_response(raw, req, receipt)['status'], 'completed_valid')
        receipt['provider_route'] = 'google-ai-studio'
        self.assertEqual(normalize_response(raw, req, receipt)['status'], 'identity_mismatch')

    def test_wrong_model_provider_or_receipt_identity_rejected(self):
        req = request()
        for raw in [response(model='openai/gpt-6.1-sol'), response(provider_route='anthropic'),
                    response(provider='Anthropic')]:
            self.assertEqual(normalize_response(raw, req)['status'], 'identity_mismatch')
        receipt = dict(request_id='q0', canonical_slug='openai/gpt-6-astra-OTHER', provider_route='openai')
        self.assertEqual(normalize_response(response(), req, receipt)['status'], 'identity_mismatch')

    def test_saved_request_identity_mismatch_and_malformed_raw_hash_retained(self):
        self.assertEqual(normalize_response(wrapped(request('other')), request())['status'], 'identity_mismatch')
        raw = b'{"not complete"'
        result = normalize_response(raw, request())
        self.assertEqual(result['status'], 'invalid')
        self.assertEqual(result['raw_sha256'], hashlib.sha256(raw).hexdigest())

    def test_absent_and_invalid_usage_not_zero_cost(self):
        self.assertIsNone(normalize_response(response(usage=None), request())['cost_usd'])
        for usage in [{'cost': -1}, {'cost': 'NaN'}, {'cost': True}, {'completion_tokens': True}]:
            result = normalize_response(response(usage=usage), request())
            self.assertEqual(result['status'], 'invalid')
            self.assertIsNone(result['cost_usd'])

    def test_duplicate_rows_invalidate_predictions_but_charge_same_call_once(self):
        req = request()
        result = collect_results([req], [wrapped(req), wrapped(req)])
        self.assertEqual(result['outcomes'][0]['status'], 'duplicate')
        self.assertEqual(result['outcomes'][0]['labels'], [None, None])
        self.assertEqual(result['accounting']['known_cost_usd'], '0.25')
        self.assertEqual(len(result['accounting']['physical_calls']), 1)

    def test_two_distinct_generations_same_logical_id_count_each_charge_once(self):
        first, second = wrapped(), wrapped()
        second['response']['body']['id'] = 'second-generation'
        result = collect_results([request()], [first, second])
        self.assertEqual(result['outcomes'][0]['status'], 'duplicate')
        self.assertEqual(result['accounting']['known_cost_usd'], '0.50')

    def test_missing_results_remain_missing_and_unknown_total_cost(self):
        result = collect_results([request()], [])
        self.assertEqual(result['outcomes'][0]['status'], 'missing')
        self.assertFalse(result['collection_complete'])
        self.assertIsNone(result['accounting']['total_cost_usd'])

    def test_unexpected_malformed_and_reused_physical_ids_block_certificate(self):
        a, b = request('q0'), request('q1')
        raw_a, raw_b = wrapped(a), wrapped(b)
        raw_b['response']['body']['id'] = raw_a['response']['body']['id']
        result = collect_results([a, b], [raw_a, raw_b, wrapped(request('extra')), b'not-json'])
        self.assertFalse(result['collection_complete'])
        self.assertEqual(len(result['unexpected_ids']), 1)
        self.assertEqual(len(result['malformed_items']), 1)
        self.assertEqual(len(result['accounting']['conflicts']), 1)
        self.assertIsNone(result['accounting']['total_cost_usd'])

    def test_results_join_by_saved_ids_not_output_order(self):
        a, b = request('q0'), request('q1')
        raw_a, raw_b = wrapped(a), wrapped(b)
        raw_b['response']['body']['choices'][0]['message']['content'] = '{"a":[{"i":0,"l":1},{"i":1,"l":2}]}'
        result = collect_results([a, b], [raw_b, raw_a])
        self.assertEqual([o['request_id'] for o in result['outcomes']], ['q0', 'q1'])
        self.assertEqual([o['labels'] for o in result['outcomes']], [[7, 21], [1, 2]])


class Annotation47ScoringTests(unittest.TestCase):
    def test_equal_region_weighting_and_missing_as_error_not_noise(self):
        # Region b is three times larger. Its one missing Noise cell is an
        # error, not an imputed correct technical-quality prediction.
        score = score_regions([0, 21, 21, 21], [0, 21, None, 21], ['a', 'b', 'b', 'b'], ['a', 'b'])
        self.assertAlmostEqual(score['equal_region_agreement'], (1 + 2 / 3) / 2)
        self.assertNotEqual(score['equal_region_agreement'], 3 / 4)
        self.assertEqual(score['regions'][1]['planned_cells'], 3)
        self.assertEqual(score['regions'][1]['delivered_cells'], 2)
        self.assertAlmostEqual(score['regions'][1]['fixed28_macro_f1'], 0.8 / 28)
        self.assertEqual(score['repetitions'], 1)
        self.assertFalse(score['repeatability_estimable'])
        self.assertNotIn('sd', score)

    def test_absent_classes_stay_zero_and_missing_adds_false_negative(self):
        score = score_regions([0, 0, 1], [0, None, 1], ['a', 'a', 'b'], ['a', 'b'])
        self.assertAlmostEqual(score['regions'][0]['fixed28_macro_f1'], (2 / 3) / 28)
        self.assertAlmostEqual(score['regions'][1]['fixed28_macro_f1'], 1 / 28)
        self.assertEqual(score['regions'][0]['agreement_upper_bound'], 1)

    def test_cluster_and_cell_coverage_use_different_fixed_denominators(self):
        coverage = delivery_coverage([21, None], [1, 9])
        self.assertEqual(coverage['cluster_delivery_coverage'], 0.5)
        self.assertEqual(coverage['cell_delivery_coverage'], 0.1)

    def test_joint_valid_pair_changes_do_not_count_missing_as_label(self):
        pair = paired_label_changes([0, 1, None, 21], [1, None, 1, 21])
        self.assertEqual(pair['joint_valid_cases'], 2)
        self.assertEqual(pair['label_change_rate_on_joint_valid'], 0.5)
        self.assertEqual(pair['label_change_bounds_all_planned'], [0.25, 0.75])
        self.assertIsNone(paired_label_changes([None], [None])['label_change_rate_on_joint_valid'])

    def test_fraction_minus_means_contrast_preserves_region_pairing(self):
        a = score_regions([0, 1], [0, None], ['a', 'b'], ['a', 'b'])
        b = score_regions([0, 1], [0, 1], ['a', 'b'], ['a', 'b'])
        contrast = paired_region_contrast(a, b)
        self.assertEqual(contrast['equal_region_agreement_difference'], 0.5)
        self.assertEqual(contrast['agreement_difference_bounds'], [0.0, 0.5])
        reversed_regions = score_regions([0, 1], [0, 1], ['a', 'b'], ['b', 'a'])
        with self.assertRaises(ValueError):
            paired_region_contrast(a, reversed_regions)

    def test_invalid_labels_populations_and_empty_regions_rejected(self):
        for args in [([0], [None, None], ['a'], ['a', 'b']),
                     ([0, 1], [0, True], ['a', 'b'], ['a', 'b']),
                     ([0], [0], ['a'], ['a', 'b'])]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                score_regions(*args)


class Annotation47LedgerTests(unittest.TestCase):
    def setUp(self):
        self.entry = new_ledger([request()])['entries']['q0']

    def test_ambiguous_submission_never_automatically_resubmits(self):
        entry = transition_submission(self.entry, 'submit_started')
        entry = transition_submission(entry, 'submission_ambiguous')
        with self.assertRaises(ValueError):
            transition_submission(entry, 'submit_started')
        with self.assertRaises(ValueError):
            transition_submission(entry, 'no_generation_confirmed', {'no_generation_confirmed': True})
        accepted = transition_submission(entry, 'reconciled_accepted', {'batch_id': 'batch-1'})
        self.assertEqual(accepted['state'], 'accepted')

    def test_at_most_two_documented_pre_generation_retries(self):
        entry = self.entry
        proof = dict(no_generation_confirmed=True, provider_accepted=False, billed=False,
                     source='recorded transport proof')
        for attempt in range(3):
            entry = transition_submission(entry, 'submit_started')
            self.assertEqual(entry['attempts'], attempt + 1)
            entry = transition_submission(entry, 'no_generation_confirmed', proof)
        self.assertEqual(entry['state'], 'pre_generation_failed')
        with self.assertRaises(ValueError):
            transition_submission(entry, 'submit_started')

    def test_generated_invalid_missing_or_valid_results_never_regenerated(self):
        for event in ['result_valid', 'result_invalid', 'result_missing']:
            entry = transition_submission(self.entry, 'submit_started')
            entry = transition_submission(entry, 'submission_accepted', {'generation_id': 'gen-1'})
            entry = transition_submission(entry, event)
            with self.subTest(event=event), self.assertRaises(ValueError):
                transition_submission(entry, 'submit_started')

    def test_receipts_fsync_and_reload_before_next_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            path.write_text(json.dumps(new_ledger([request()])))
            persist_submission_event(path, 'q0', 'submit_started')
            persisted = strict_json(path.read_text())
            self.assertEqual(persisted['entries']['q0']['state'], 'submitting')
            self.assertFalse(persisted['execution_enabled'])
            persist_submission_event(path, 'q0', 'submission_accepted', {'batch_id': 'batch-1'})
            self.assertEqual(strict_json(path.read_text())['entries']['q0']['acceptance_receipt']['batch_id'], 'batch-1')

    def test_offline_cli_verifies_bundle_and_preserves_raw_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            bundle = base / 'bundle'
            bundle.mkdir()
            (bundle / 'requests.jsonl').write_text(json.dumps(request()) + '\n')
            (bundle / 'protocol.json').write_text('{"status":"planned_not_executed"}\n')
            metadata = {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                                'bytes': p.stat().st_size} for p in bundle.iterdir()}
            (bundle / 'manifest.json').write_text(json.dumps({'files': metadata}))
            raw = base / 'result.jsonl'
            raw.write_text(json.dumps(wrapped()) + '\n')
            output = base / 'collected'
            command = [sys.executable, str(ROOT / 'scripts/collect_annotation47.py'),
                       '--manifest', str(bundle / 'manifest.json'), '--results', str(raw),
                       '--output', str(output)]
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads((output / 'collection.json').read_text())
            self.assertTrue(report['collection_complete'])
            self.assertEqual(report['network_calls'], 0)
            self.assertEqual(report['source_files'][0]['sha256'], hashlib.sha256(raw.read_bytes()).hexdigest())
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
            (bundle / 'requests.jsonl').write_text('{}\n')
            command[-1] = str(base / 'other-output')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)


if __name__ == '__main__':
    unittest.main()
