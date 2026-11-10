"""Offline scientific, leakage and request-pack contract tests."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from llm_spatial_omics_clustering.revision.annotation47_prepare import (
    ARMS, FAMILIES, MARKERS, METHODS, N_CELLS, OCCUPIED, SYSTEM,
    batch_envelopes, canonical_bytes, compute_profiles, evidence_pair,
    join_memberships, make_records, payload, prepare, read_json,
    validate_body, validate_evidence, validate_protocol, validate_records,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'configs/primary_annotation47_1repeat_opus55_v1.json'


def mock_profiles():
    result = {}
    for method in METHODS:
        n = OCCUPIED[method]
        counts = np.ones(n, dtype=np.int64)
        counts[0] += N_CELLS - n
        result[method] = {'cluster_names': np.asarray([str(i) for i in range(n)]),
                          'counts': counts, 'means_z': np.zeros((n, 47)),
                          'fractions': np.full((n, 47), .5)}
    return result


class AnnotationPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = read_json(PROTOCOL)
        cls.records, cls.bodies, cls.maps = make_records(cls.protocol, mock_profiles())

    def test_exact_one_repeat_scientific_contract_and_disabled_execution(self):
        validate_protocol(self.protocol)
        self.assertEqual(len(self.records), 128)
        self.assertEqual(sum(record['n_cases'] for record in self.records), 9024)
        self.assertEqual(len(self.maps), 1128)
        self.assertEqual(sum(record['transport'] == 'batch' for record in self.records), 96)
        self.assertEqual(sum(record['transport'] == 'standard' for record in self.records), 32)

    def test_non_one_repeat_and_45_markers_and_launch_are_rejected(self):
        for change in ['repeats', 'marker', 'launch', 'scope']:
            protocol = deepcopy(self.protocol)
            if change == 'repeats':
                protocol['repeats'] = 3
            elif change == 'marker':
                protocol['markers'] = protocol['markers'][:45]
            elif change == 'launch':
                protocol['execution']['enabled'] = True
            else:
                protocol['experiment_ids'] = [7, 9, 14]
            with self.assertRaises(ValueError):
                validate_protocol(protocol)

    def test_model_provider_seed_and_sampling_fields(self):
        for record in self.records:
            body = self.bodies[record['request_id']]
            family = record['model_family']
            self.assertEqual(body['messages'][0]['content'], SYSTEM)
            self.assertEqual(body['reasoning'], {'effort': 'high'})
            self.assertEqual(body['max_tokens'], 32768)
            self.assertNotIn('temperature', body)
            self.assertNotIn('top_p', body)
            self.assertNotIn('tools', body)
            if family in ['openai', 'google']:
                self.assertEqual(body['seed'], 42)
            else:
                self.assertNotIn('seed', body)
            if record['transport'] == 'batch':
                self.assertNotIn('provider', body)
            else:
                self.assertEqual(body['provider'], {'only': ['deepseek'],
                    'allow_fallbacks': False, 'require_parameters': True})

    def test_pair_has_identical_mean_encoding_and_only_adds_fractions(self):
        pair = evidence_pair(self.protocol, np.full((2, 47), .1235), np.full((2, 47), .999))
        right = deepcopy(pair[ARMS[1]])
        self.assertEqual(right.pop('fraction_above_processed_zero'), [[999] * 47] * 2)
        self.assertEqual(right, pair[ARMS[0]])
        self.assertEqual(pair[ARMS[0]]['mean_asinh_expression_z_thousandths'], [[124] * 47] * 2)

    def test_recursive_positive_allowlist_blocks_nested_or_top_level_leakage(self):
        pair = evidence_pair(self.protocol, np.zeros((2, 47)), np.zeros((2, 47)))
        mutations = []
        e = deepcopy(pair[ARMS[0]]); e['truth_labels'] = [0, 1]; mutations.append(e)
        e = deepcopy(pair[ARMS[0]]); e['response_contract']['method'] = 'leiden'; mutations.append(e)
        e = deepcopy(pair[ARMS[0]]); e['label_dictionary']['28'] = 'ground_truth'; mutations.append(e)
        e = deepcopy(pair[ARMS[0]]); e['query_case_ids'] = ['leiden_0', 'leiden_1']; mutations.append(e)
        e = deepcopy(pair[ARMS[0]]); e['mean_asinh_expression_z_thousandths'][0][0] = {'truth': 'B'}; mutations.append(e)
        e = deepcopy(pair[ARMS[0]]); e['task'] += ' Use Leiden.'; mutations.append(e)
        for evidence in mutations:
            with self.assertRaises(ValueError):
                validate_evidence(self.protocol, evidence, ARMS[0])

    def test_mean_fraction_shapes_types_ranges_and_anonymous_ids(self):
        pair = evidence_pair(self.protocol, np.zeros((2, 47)), np.zeros((2, 47)))
        for mode in ['markers', 'fraction', 'bool', 'ids', 'rows']:
            evidence = deepcopy(pair[ARMS[1]])
            if mode == 'markers': evidence['marker_order'] = MARKERS[:-1]
            elif mode == 'fraction': evidence['fraction_above_processed_zero'][0][0] = 1001
            elif mode == 'bool': evidence['mean_asinh_expression_z_thousandths'][0][0] = True
            elif mode == 'ids': evidence['query_case_ids'] = [0, 0]
            else: evidence['mean_asinh_expression_z_thousandths'].pop()
            with self.assertRaises(ValueError):
                validate_evidence(self.protocol, evidence, ARMS[1])
        with self.assertRaises(ValueError):
            evidence_pair(self.protocol, np.zeros((2, 45)), np.zeros((2, 45)))

    def test_exact_cartesian_coverage_duplicate_request_and_observation_rejected(self):
        validate_records(self.protocol, self.records, self.bodies)
        with self.assertRaises(ValueError):
            validate_records(self.protocol, self.records[:-1], self.bodies)
        for records in [self.records + [self.records[0]],
                        [*self.records[:-1], {**self.records[-1], 'request_id': self.records[0]['request_id']}]]:
            with self.assertRaises(ValueError):
                validate_records(self.protocol, records, self.bodies)

    def test_body_parameter_drift_is_rejected(self):
        record = self.records[0]
        for field, value in [('tools', []), ('temperature', 0), ('max_tokens', 4000),
                             ('provider', {'allow_fallbacks': True}), ('model', 'wrong/model')]:
            body = deepcopy(self.bodies[record['request_id']])
            body[field] = value
            with self.assertRaises(ValueError):
                validate_body(self.protocol, record, body)

    def test_batch_top_level_fields_come_before_requests_and_routes_are_pinned(self):
        envelopes = batch_envelopes(self.protocol, self.records, self.bodies)
        self.assertEqual(set(envelopes), set(FAMILIES[:3]))
        for family, envelope in envelopes.items():
            self.assertEqual(list(envelope)[-1], 'requests')
            self.assertEqual(len(envelope['requests']), 32)
            self.assertEqual(envelope['provider'], {'only': [self.protocol['model_bindings'][family]['provider_route']],
                                                    'allow_fallbacks': False})
            self.assertFalse(envelope['model'].endswith(':batch'))
            self.assertEqual(envelope['endpoint'], '/v1/chat/completions')
            self.assertEqual(envelope['completion_window'], '24h')
            for item in envelope['requests']:
                self.assertEqual(item['body'], self.bodies[item['custom_id']])

    def test_source_join_requires_exact_unique_keys_but_reorders_memberships(self):
        keys = pd.DataFrame({'File_ID': ['a', 'a', 'b'], 'ID': ['1', '2', '1']})
        values = pd.DataFrame({'File_ID': ['b', 'a', 'a'], 'ID': ['1', '1', '2'], 'cluster': ['x', 'y', 'x']})
        np.testing.assert_array_equal(join_memberships(keys, values, 'cluster', 2), ['y', 'x', 'x'])
        for invalid in [values.iloc[:-1], pd.concat([values.iloc[:2], values.iloc[:1]]),
                        values.assign(ID=['99', '1', '2'])]:
            with self.assertRaises(ValueError):
                join_memberships(keys, invalid, 'cluster', 2)

    def test_train_only_population_scaling_asinh_order_and_raw_zero_fractions(self):
        raw = np.zeros((5, 47), dtype=np.float64)
        raw[:, 0] = [-10, 0, 5, 1000, -5]
        raw[:, 1] = [2, 2, 2, 9, 12]  # exactly constant within training only
        train = np.array([True, True, True, False, False])
        memberships = {'m': ['b', 'a', 'b', 'a', 'a']}
        scaler, profiles = compute_profiles(raw, train, memberships)
        transformed = np.arcsinh(raw / 5)
        np.testing.assert_allclose(scaler['center'], transformed[:3].mean(0), rtol=0, atol=0)
        self.assertEqual(scaler['scale'][1], 1)
        profile = profiles['m']
        self.assertEqual(profile['cluster_names'].tolist(), ['a', 'b'])
        np.testing.assert_array_equal(profile['counts'], [3, 2])
        np.testing.assert_allclose(profile['means_asinh'][0], transformed[[1, 3, 4]].mean(0), rtol=0, atol=0)
        self.assertEqual(profile['fractions'][0, 0], 1 / 3)
        self.assertNotEqual(profile['means_asinh'][0, 0], np.arcsinh(raw[[1, 3, 4], 0].mean() / 5))
        modified = raw.copy(); modified[~train] *= 10
        altered_scaler, _ = compute_profiles(modified, train, memberships)
        np.testing.assert_array_equal(scaler['center'], altered_scaler['center'])
        np.testing.assert_array_equal(scaler['scale'], altered_scaler['scale'])

    def test_existing_output_is_never_overwritten_before_source_reads(self):
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            prepare(PROTOCOL, ROOT, Path('/does/not/exist'), ROOT / 'tests')


if __name__ == '__main__':
    unittest.main()
