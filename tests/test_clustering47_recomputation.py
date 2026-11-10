"""Offline admission tests for the fixed-partition publication replay."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'clustering47_recompute', ROOT / 'scripts/recompute_clustering47_publication.py')
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


class FrozenRecomputationTests(unittest.TestCase):
    def fixture(self, root):
        """A tiny hash contract tests admission without copying the real cohort."""
        (root / 'configs').mkdir()
        (root / 'data').mkdir()
        inputs = {'data/assignments.csv': b'File_ID,ID,cluster\nr,1,a\n',
                  'data/markers.json': json.dumps([f'marker_{i}' for i in range(47)]).encode()}
        for relative, content in inputs.items():
            (root / relative).write_bytes(content)
        manifest = {
            'schema': 'clustering.publication.primary47.v1',
            'cohort': {'cells': 220082, 'key_columns': ['File_ID', 'ID']},
            'primary_spatialsort_seed': 42, 'spatialsort_sensitivity_seed': 43,
            'marker_order_path': 'data/markers.json',
            'methods': {method: {'path': 'data/assignments.csv'} for method in REPLAY.METHODS},
            'sensitivity': {'spatialsort_seed43': {'path': 'data/assignments.csv'}},
            'files': {relative: {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
                      for relative, content in inputs.items()},
        }
        manifest_path = root / 'data/manifest.json'
        manifest_path.write_text(json.dumps(manifest))
        config = {'schema': 'clustering.publication.bindings.v1',
                  'annotation_execution_disabled': True,
                  'manifest': 'data/manifest.json',
                  'manifest_sha256': REPLAY.sha(manifest_path)}
        (root / REPLAY.CONFIG).write_text(json.dumps(config))
        return config, manifest

    def test_hash_contract_rejects_input_and_manifest_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with patch.object(REPLAY, 'AUXILIARY_INPUT_SHA256', {}):
                _, _, hashes = REPLAY.load_pinned_inputs(root)
                self.assertEqual(len(hashes), 4)
                path = root / 'data/assignments.csv'
                content = path.read_bytes()
                path.write_bytes(content + b'changed\n')
                with self.assertRaisesRegex(ValueError, 'checksum differs'):
                    REPLAY.load_pinned_inputs(root)
                path.write_bytes(content)
                manifest = root / 'data/manifest.json'
                manifest.write_bytes(manifest.read_bytes() + b' ')
                with self.assertRaisesRegex(ValueError, 'checksum differs'):
                    REPLAY.load_pinned_inputs(root)

    def test_paths_and_output_directory_protect_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ['../outside.csv', '/absolute/input.csv']:
                with self.assertRaises(ValueError):
                    REPLAY.repo_path(relative, root)
            with self.assertRaises(ValueError):
                REPLAY.prepare_output_directory(root / 'data/frozen/output', root)
            output = REPLAY.prepare_output_directory(root / 'outputs/replay', root)
            (output / 'existing.txt').write_text('preserve')
            with self.assertRaisesRegex(ValueError, 'new or empty'):
                REPLAY.prepare_output_directory(output, root)
            self.assertEqual((output / 'existing.txt').read_text(), 'preserve')

    def test_exact_cell_join_restores_order_and_rejects_missing_or_duplicate_keys(self):
        frame = pd.DataFrame({column: ['1', '2'] for column in REPLAY.BASE_COLUMNS})
        frame['File_ID'] = ['region', 'region']
        assignments = pd.DataFrame({'File_ID': ['region', 'region'], 'ID': ['2', '1'],
                                    'cluster': ['b', 'a']})
        joined = REPLAY.join_assignments(frame, 'flowsom', assignments, 'cluster', 2, 2)
        self.assertEqual(joined.flowsom.tolist(), ['a', 'b'])
        pd.testing.assert_frame_equal(joined.drop(columns='flowsom'), frame.drop(columns='flowsom'))
        for invalid in [assignments.assign(ID=['2', '3']), assignments.assign(ID=['2', '2'])]:
            with self.assertRaises(ValueError):
                REPLAY.join_assignments(frame, 'flowsom', invalid, 'cluster', 2, 2)

    def test_alphabetical_majority_tie_and_zero_prediction_class(self):
        labels = pd.Series(['Z', 'A'])
        _, mapping, predictions, ties = REPLAY.majority(labels, pd.Series(['c', 'c']))
        self.assertEqual(mapping['c'], 'A')
        self.assertEqual(ties, 1)
        metrics = REPLAY.class_metrics(labels, predictions).set_index('cell_type')
        self.assertEqual(metrics.loc['Z', 'f1'], 0)
        self.assertEqual(metrics.loc['Z', 'n_cells'], 1)

    def test_original_generator_is_preserved_byte_for_byte(self):
        archive = ROOT / 'scripts/archive/recompute_publication_metrics_20261108_original.py'
        self.assertEqual(REPLAY.sha(archive),
                         'cd235843e16c77723a13ac2c3b3b2570f611c6d267a5e414fe051557dd592e62')


if __name__ == '__main__':
    unittest.main()
