"""Reject scientific input mismatches and accidental activation without calls."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from llm_spatial_omics_clustering.revision.combined_annotation47 import (
    validate_protocol, validate_cell_join, validate_paired_evidence, validate_request_ids,
)

ROOT = Path(__file__).resolve().parents[1]


class CombinedAnnotationTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / 'configs/combined_annotation47_7_9_14_v1.json').read_text())
        self.left = {'markers': self.protocol['markers'], 'ontology': self.protocol['ontology'],
                     'cluster_ids': ['c0', 'c1'], 'mean_expression_z_thousandths': [[0] * 47, [-2] * 47]}
        self.right = deepcopy(self.left)
        self.right['fraction_above_processed_zero_thousandths'] = [[500] * 47, [0] * 47]

    def test_valid_design_is_160_sets_and_still_disabled(self):
        receipt = validate_protocol(self.protocol)
        self.assertEqual(receipt['annotation_sets'], 160)
        self.assertFalse(receipt['execution_enabled'])
        self.assertEqual(receipt['annotation_calls'], 0)

    def test_activation_is_rejected(self):
        self.protocol['execution']['enabled'] = True
        with self.assertRaisesRegex(ValueError, 'disabled'):
            validate_protocol(self.protocol)

    def test_45_marker_contract_is_rejected(self):
        self.protocol['markers'] = self.protocol['markers'][:45]
        with self.assertRaisesRegex(ValueError, '47'):
            validate_protocol(self.protocol)

    def test_identical_means_and_only_added_fractions_are_admitted(self):
        validate_paired_evidence(self.protocol, self.left, self.right)

    def test_missing_marker_and_mean_changes_are_rejected(self):
        for key, value in [('markers', self.protocol['markers'][:-1]),
                           ('mean_expression_z_thousandths', [[1] * 47, [-2] * 47])]:
            right = deepcopy(self.right)
            right[key] = value
            with self.assertRaisesRegex(ValueError, 'differs'):
                validate_paired_evidence(self.protocol, self.left, right)

    def test_duplicate_cluster_and_out_of_bounds_fraction_are_rejected(self):
        left, right = deepcopy(self.left), deepcopy(self.right)
        left['cluster_ids'] = right['cluster_ids'] = ['c0', 'c0']
        with self.assertRaisesRegex(ValueError, 'unique'):
            validate_paired_evidence(self.protocol, left, right)
        self.right['fraction_above_processed_zero_thousandths'][0][0] = 1001
        with self.assertRaisesRegex(ValueError, 'bounded'):
            validate_paired_evidence(self.protocol, self.left, self.right)

    def test_cell_join_requires_exact_unique_key_set(self):
        keys = [('r0', '01'), ('r1', '02')]
        validate_cell_join(keys, list(reversed(keys)), expected_n=2)
        for assigned in [keys[:1], [keys[0], keys[0]], [('r0', '01'), ('r1', '03')]]:
            with self.assertRaisesRegex(ValueError, 'Membership join'):
                validate_cell_join(keys, assigned, expected_n=2)

    def test_duplicate_request_ids_and_observations_are_rejected(self):
        a = dict(request_id='r0', method='flowsom', model_family='openai', arm='all_means', repeat=0, batch=0)
        b = {**a, 'request_id': 'r1', 'repeat': 1}
        validate_request_ids([a, b])
        for duplicate in [{**b, 'request_id': 'r0'}, {**a, 'request_id': 'r2'}]:
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                validate_request_ids([a, duplicate])


if __name__ == '__main__':
    unittest.main()
