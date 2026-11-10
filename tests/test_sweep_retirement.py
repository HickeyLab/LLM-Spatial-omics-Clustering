"""Historical evidence stays intact while the active publication loses the sweep."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'data/historical/flowsom_cluster_count_sweep_20261103'


class SweepRetirementTests(unittest.TestCase):
    def test_all_archived_files_keep_their_original_hashes(self):
        manifest = json.loads((ARCHIVE / 'manifest.json').read_text())
        self.assertEqual(manifest['experiment_id'], 4)
        self.assertEqual(manifest['status'], 'archived')
        for entry in manifest['files']:
            self.assertEqual(hashlib.sha256((ROOT / entry['archive_path']).read_bytes()).hexdigest(), entry['sha256'])
        original = ROOT / 'data/frozen/figure_s03/flowsom_k_sweep_purity.csv'
        self.assertEqual(original.read_bytes(), (ARCHIVE / 'data/frozen/figure_s03/flowsom_k_sweep_purity.csv').read_bytes())

    def test_active_s4_has_four_panels_and_no_sweep_dependency(self):
        record = json.loads((ROOT / 'configs/manuscript_inventory.json').read_text())['figures']['S4']
        self.assertEqual(record['panels'], list('ABCD'))
        self.assertNotIn('cluster-count sweep', record['caption'])
        self.assertRegex(record['caption'], r'\(D\) (?:Regional )?[Aa]djusted Rand index')
        receipt = json.loads((ROOT / 'figures/publication/Figure_S4_verification.json').read_text())
        self.assertFalse(any('flowsom_k_sweep' in name for name in receipt['inputs']))
        svg = (ROOT / 'figures/publication/Figure_S4.svg').read_text()
        self.assertNotIn('FlowSOM cluster count', svg)

    def test_stable_ids_and_current_annotation_selection(self):
        registry = json.loads((ROOT / 'configs/experiment_registry.json').read_text())
        self.assertEqual([e['id'] for e in registry['experiments']], list(range(1, 15)))
        self.assertNotIn(4, registry['active_reported_ids'])
        for e in registry['experiments']:
            self.assertFalse(e['new_execution'])
            if e['id'] in [7, 14]:
                self.assertEqual(e['status'], 'reported_completed')
                self.assertFalse(e['prior_results_remain_reported'])
            if e['id'] == 9:
                self.assertEqual(e['status'], 'archived')
                self.assertNotIn(9, registry['active_reported_ids'])


if __name__ == '__main__':
    unittest.main()
