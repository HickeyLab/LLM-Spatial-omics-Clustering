"""Verify current replay integrity and scientific definitions independently."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from llm_spatial_omics_clustering import manuscript

ROOT = Path(__file__).resolve().parents[1]


class ManuscriptAlignmentTests(unittest.TestCase):
    def test_independent_frozen_cell_recalculation(self):
        spec = importlib.util.spec_from_file_location('verify_replay', ROOT / 'scripts/verify_manuscript_replay.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        receipt = module.verify()
        self.assertEqual(receipt['status'], 'pass')
        self.assertEqual(receipt['figure_2_regional_values'], 64)
        self.assertEqual(receipt['figure_2_celltype_values'], 160)
        self.assertEqual(receipt['figure_3_method_model_maps'], 16)
        self.assertEqual(receipt['approved_images'], 15)

    def test_corrupted_input_is_rejected_before_plotting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'inputs'
            data.mkdir()
            (data / 'table.csv').write_text('value\n9\n')
            (data / 'manifest.json').write_text(json.dumps({'files': [{
                'path': 'inputs/table.csv', 'sha256': hashlib.sha256(b'value\n1\n').hexdigest()}]}))
            with patch.object(manuscript, 'ROOT', root), patch.object(manuscript, 'INPUTS', data):
                with self.assertRaisesRegex(ValueError, 'Frozen table changed'):
                    manuscript.read_table('table.csv')

    def test_current_panel_arrangement_and_notebook_python(self):
        inventory = manuscript.inventory()['figures']
        self.assertEqual(inventory['2']['panels'], list('ABCDEFGH'))
        self.assertEqual(inventory['S11']['panels'], ['A'])
        self.assertEqual(inventory['3']['panels'], list('ABCDE'))
        self.assertEqual(len(inventory), 13)
        self.assertEqual(sum(len(r['images']) for r in inventory.values()), 15)
        self.assertNotIn('5', inventory)
        self.assertNotIn('S8', inventory)
        self.assertNotIn('S9', inventory)
        self.assertEqual(inventory['S5']['panels'], ['A'])
        for key in ['3','4','S6','S7','S10','S11']:
            self.assertEqual(inventory[key]['scientific_status'], 'annotation47_scored_single_run')
            self.assertNotIn('pending', inventory[key]['caption'])
            self.assertNotIn('historical', inventory[key]['caption'].lower())
        self.assertEqual(inventory['4']['panels'], list('ABCDE'))
        self.assertEqual(inventory['S4']['panels'], list('ABCD'))
        for record in inventory.values():
            notebook = json.loads((ROOT / record['notebook']).read_text())
            for cell in notebook['cells']:
                if cell['cell_type'] == 'code':
                    ast.parse(''.join(cell['source']))

    def test_spatial_replots_preserve_each_figures_windows_and_geometry(self):
        import matplotlib.pyplot as plt
        for figure_id, counts in [(2,[1086,915]),(3,[1003,1000])]:
            figure = manuscript.spatial_panel(figure_id)
            try:
                columns = len(figure.axes)//2
                self.assertEqual([len(figure.axes[row*columns+1].collections[0].get_offsets())
                                  for row in range(2)],counts)
                self.assertTrue(all(float(axis.get_aspect()) == 1 for axis in figure.axes))
            finally:
                plt.close(figure)

    def test_reference_display_contains_all47_actual_marker_profiles(self):
        import csv
        import yaml
        cfg=yaml.safe_load((ROOT/'configs/figure_s03.yaml').read_text())['panel_a']
        archived=yaml.safe_load((ROOT/'data/historical/reference47_display_before_20261110/figure_s03.yaml').read_text())['panel_a']
        self.assertEqual(cfg['marker_order'][:45], archived['marker_order'])
        self.assertEqual(cfg['marker_order'][-2:], ['CD123','CDX2'])
        folder=ROOT/'data/frozen/reference47_profiles_20261110'
        manifest=json.loads((folder/'manifest.json').read_text())
        source=folder/'figureS4_marker_summaries.csv'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), manifest['files'][source.name]['sha256'])
        with source.open() as handle:
            rows=list(csv.DictReader(handle))
        self.assertEqual(len(rows),27*47)
        self.assertEqual({row['marker'] for row in rows}, set(cfg['marker_order']))
        self.assertEqual({row['cell_type'] for row in rows}, set(cfg['cell_type_order']))
        counts={}
        for label in cfg['cell_type_order']:
            group=[row for row in rows if row['cell_type']==label]
            self.assertEqual(len(group),47)
            self.assertEqual(len({row['marker'] for row in group}),47)
            self.assertEqual(len({row['n_cells'] for row in group}),1)
            counts[label]=int(group[0]['n_cells'])
        self.assertEqual(sum(counts.values()),209587)
        self.assertTrue(all(0<=float(row['fraction_cells_pct'])<=100 for row in rows))
        self.assertTrue(all(0<=float(row['scaled_mean_expression'])<=1 for row in rows))

    def test_companion_bytes_and_current_labels_are_unique(self):
        crosswalk = json.loads((ROOT / 'configs/supplementary_table_crosswalk.json').read_text())['tables']
        self.assertEqual(len({e['path'] for e in crosswalk}), len(crosswalk))
        labels = {e['filename']: e['current_label'] for e in crosswalk}
        self.assertEqual(set(labels.values()), {'S2B','S6a','S6b','S6c','S6d','S7'})
        for part in 'abcd':
            self.assertEqual(labels['Table_S6'+part+'.csv'], 'S6'+part)
        self.assertEqual(labels['conditional_comparisons.csv'], 'S7')
        self.assertEqual(labels['paired_regional_observations.csv'], 'S7')
        self.assertNotIn('S3a_regional_metrics.csv', labels)
        self.assertNotIn('Table_S4h_calibration.csv', labels)
        self.assertNotIn('Table_S7b.csv', labels)
        for entry in crosswalk:
            self.assertEqual(hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest(), entry['sha256'])

    def test_primary_clustering_table_cells_match_display_sources(self):
        current={x['label']:x for x in json.loads(manuscript.override_path('tables/current_tables.json', 'replay_table_overrides', root=ROOT).read_text())['tables']}
        rows={row[0]:row for row in current['S2A']['rows'][1:]}
        self.assertEqual(rows['Inputs'][2:4], ['47 markers', '47 markers'])
        self.assertEqual(rows['Configured and occupied clusters'][2:4], ['300 requested and 299 occupied', '300 requested. 229 occupied in the primary chain and 231 in the sensitivity chain'])
        self.assertEqual(rows['Iterations'][2:4], ['3 whole-cohort passes, giving 660,246 updates', '100 actual sweeps per chain with dmh_iter=5'])
        self.assertEqual(rows['Seed'][3], 'Sampling seed 42 primary and 43 sensitivity')
        membership={row[0]:row for row in current['S2B']['rows'][1:]}
        self.assertEqual(membership['CD123'][2:4], ['Included','Included'])
        self.assertEqual(membership['CDX2'][2:4], ['Included','Included'])
        self.assertEqual(membership['Total selected inputs'][2:4], ['47','47'])
        sources=json.loads((ROOT/'configs/supplementary_table_crosswalk.json').read_text())['native_table_sources']
        self.assertEqual({v['current_label'] for v in sources}, {'S1','S2A','S2B'})
        for source in sources:
            tables=json.loads((ROOT/source['path']).read_text())['tables']
            self.assertIn(source['table_label_selector'], {v['label'] for v in tables})


if __name__ == '__main__':
    unittest.main()
