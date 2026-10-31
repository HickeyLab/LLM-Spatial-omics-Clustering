"""Guard current supplementary numbering while preserving compatible imports."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SupplementaryFigureLabelTests(unittest.TestCase):
    def test_inventory_has_all_ten_current_supplementary_figures(self):
        records = json.loads((ROOT / 'configs/manuscript_inventory.json').read_text())['figures']
        paths = []
        for number in range(1, 11):
            record = records[f'S{number}']
            path = ROOT / record['notebook']
            self.assertTrue(path.is_file(), path)
            paths.append(path)
            source = '\n'.join(''.join(c['source']) for c in json.loads(path.read_text())['cells'])
            self.assertTrue(f'Figure S{number}' in source or f'Figure S{number:02}' in source, path)
        self.assertEqual(len(set(paths)), 10)

    def test_renumbered_compatibility_notebooks_point_to_current_owners(self):
        aliases = {
            'figure_s03_clustering_inputs_and_diagnostics.ipynb': 'figure_s04_reference_and_clustering_diagnostics.ipynb',
            'figure_s04_annotation_diagnostics.ipynb': 'figure_s06_annotation_diagnostics.ipynb',
        }
        for old, current in aliases.items():
            text = (ROOT / 'notebooks/final_figures' / old).read_text()
            self.assertIn(current, text)

    def test_supporting_s4_runner_preserves_legacy_import_compatibility(self):
        path = ROOT / 'notebooks/supplementary/figure_s04_reference_and_clustering_diagnostics.ipynb'
        notebook = json.loads(path.read_text())
        self.assertEqual(notebook['metadata']['figure_id'], 'figure_s04')
        self.assertEqual(notebook['metadata']['canonical_notebook'],
                         'notebooks/final_figures/figure_s04_reference_and_clustering_diagnostics.ipynb')
        source = '\n'.join(''.join(c['source']) for c in notebook['cells'])
        self.assertIn('llm_spatial_omics_clustering.figure_s03', source)
        for panel in 'ABCDE':
            self.assertIn(f'Supplementary Figure S4{panel}', source)
        self.assertNotIn('/Users/', source)

    def test_navigation_lists_every_current_supplement(self):
        records = json.loads((ROOT / 'configs/manuscript_inventory.json').read_text())['figures']
        for name in ['README.md', 'docs/figure_map.md', 'notebooks/final_figures/README.md']:
            text = (ROOT / name).read_text()
            for number in range(1, 11):
                self.assertIn(Path(records[f'S{number}']['notebook']).name, text)


if __name__ == '__main__':
    unittest.main()
