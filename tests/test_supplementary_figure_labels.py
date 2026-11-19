"""Guard manuscript display numbering and stable native replay paths."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SupplementaryFigureLabelTests(unittest.TestCase):
    def test_native_inventory_has_the_expected_supplementary_notebooks(self):
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
        index = json.loads((ROOT / 'configs/manuscript_display_crosswalk.json').read_text())
        records = index['figures']
        expected_ids = {str(i) for i in range(1, 6)} | {f'S{i}' for i in range(1, 15)}
        self.assertEqual(set(records), expected_ids)
        caption_path = ROOT / 'figures/current_manuscript/Figure_captions.txt'
        artwork_manifest = json.loads((ROOT / index['current_artwork_manifest']).read_text())
        self.assertEqual(hashlib.sha256(caption_path.read_bytes()).hexdigest(),
                         artwork_manifest['captions_sha256'])
        self.assertEqual(caption_path.read_text().strip().split('\n\n'),
                         [record['caption'] for record in records.values()])
        for name in ['docs/figure_map.md', 'notebooks/final_figures/README.md']:
            text = (ROOT / name).read_text()
            for figure_id, record in records.items():
                self.assertIn(f'| {figure_id}. ', text)
                self.assertTrue(record['caption'].startswith(f'Figure {figure_id}. '))
                if 'native_notebook' in record:
                    self.assertIn(Path(record['native_notebook']).name, text)
                for entry in record['images']:
                    image = ROOT / entry['path']
                    self.assertIn(image.name, text)
                    self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), entry['sha256'])
        self.assertEqual(sum(len(r['images']) for r in records.values()), 21)
        self.assertEqual(len(records['S5']['images']), 3)


if __name__ == '__main__':
    unittest.main()
