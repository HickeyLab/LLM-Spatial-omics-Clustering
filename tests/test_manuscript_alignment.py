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
        self.assertEqual(receipt['approved_images'], 17)

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
        self.assertEqual(inventory['3']['panels'], list('ABCDEFGH'))
        self.assertEqual(inventory['4']['panels'], list('ABCDE'))
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

    def test_companion_bytes_and_current_labels_are_unique(self):
        crosswalk = json.loads((ROOT / 'configs/supplementary_table_crosswalk.json').read_text())['tables']
        self.assertEqual(len({e['path'] for e in crosswalk}), len(crosswalk))
        labels = {e['filename']: e['current_label'] for e in crosswalk}
        self.assertEqual(labels['S3a_regional_metrics.csv'], 'S4a')
        self.assertEqual(labels['Table_S4h_calibration.csv'], 'S5h')
        self.assertEqual(labels['Table_S7b.csv'], 'S8b')
        self.assertEqual(labels['conditional_comparisons.csv'], 'S7')
        for entry in crosswalk:
            self.assertEqual(hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest(), entry['sha256'])

    def test_current_table_cells_match_display_sources(self):
        native = {x['label']: x for x in json.loads((manuscript.INPUTS / 'tables/current_tables.json').read_text())['tables']}
        clustering = json.loads((ROOT / 'data/frozen/table_s01/manuscript_table.json').read_text())
        self.assertEqual([clustering['headers'], *clustering['rows']], native['S2A']['rows'])
        marker = json.loads((ROOT / 'data/frozen/table_s02/manuscript_tables.json').read_text())
        for part in marker['panels']:
            label = 'S3' + part['letter']
            self.assertEqual([part['headers'], *part['rows']], native[label]['rows'])


if __name__ == '__main__':
    unittest.main()
