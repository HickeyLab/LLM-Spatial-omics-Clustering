"""Guard the B004-only presentation amendment without new inference."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_annotation47_figures import focal_clusters,confusion_matrix,table

class AstraFigure4PresentationTests(unittest.TestCase):
    def test_main_and_supplementary_model_binding(self):
        inventory=json.loads((ROOT/'configs/manuscript_inventory.json').read_text())['figures']
        self.assertEqual(inventory['4']['presentation_model_family'],'openai')
        self.assertEqual(inventory['4']['selection'],'descriptive_selection_from_b004_benchmark')
        self.assertEqual(inventory['S6']['presentation_model_family'],'anthropic')
        self.assertIn('selected from the B004 benchmark',inventory['4']['caption'])
        self.assertNotIn('Prespecified',inventory['4']['caption'])
        self.assertIn('supplementary comparison',inventory['S6']['caption'])
        self.assertEqual(focal_clusters('openai').n_correct.sum(),118584)
        self.assertEqual(focal_clusters().n_correct.sum(),106242)

    def test_confusion_and_focal_examples_keep_fixed_denominators(self):
        counts,row=confusion_matrix(model_family='openai')
        original,_=confusion_matrix()
        self.assertEqual(counts.to_numpy().sum(),69576)
        self.assertEqual(original.to_numpy().sum(),69576)
        self.assertEqual(np.trace(counts.to_numpy()),40655)
        self.assertEqual(np.trace(original.to_numpy()),35158)
        self.assertFalse(np.array_equal(counts.to_numpy(),original.to_numpy()))
        a=focal_clusters('openai');o=focal_clusters()
        self.assertEqual(a.n_cells.sum(),220082)
        self.assertEqual(a.majority_count.sum(),151164)
        largest=lambda x:x.sort_values(['n_cells','cluster_id'],ascending=[False,True],kind='stable').head(3).cluster_id.tolist()
        self.assertEqual(largest(a),['0::6','1::6','2::6'])
        self.assertEqual(largest(a),largest(o))
        m=table('metrics.csv');s=m[m.model_family.eq('openai')&m.method.eq('leiden')&m.arm.eq('all_means_fractions')&m.scope.eq('equal_test_regions')&m.population.eq('all_labels')].iloc[0]
        self.assertAlmostEqual(s.agreement,.5812001783991381,places=14)
        self.assertAlmostEqual(a.n_correct.sum()/a.n_cells.sum(),.5388173498968566,places=14)

    def test_archived_figure_and_source_integrity(self):
        archive=ROOT/'archive/figure4_opus_20261111'
        index=json.loads((archive/'index.json').read_text())
        for entry in index['files']:
            p=ROOT/entry['archive_path']
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),entry['sha256'])
        old=archive/'figures/manuscript/Figure_4.png'
        self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(),'7b9617fbf63f2576c7efc9b710e964cbb7068609b6d3f10a8f404d19ab13163d')
        self.assertEqual(hashlib.sha256((ROOT/'configs/primary_annotation47_1repeat_opus55_v1.json').read_bytes()).hexdigest(),'c8de5b481ee48253015f54d6e30f47ba9cefc3ab00ec2ba465df0395b5580052')
        self.assertEqual(hashlib.sha256((ROOT/'figures/manuscript/Figure_S6.png').read_bytes()).hexdigest(),'19ce2668b0182057ce609c78957348905d32c55e2b5cb64d0f81c14a9ecd6c2d')

    def test_exported_workflow_is_astra_and_red_green(self):
        svg=ROOT/'figures/publication/Figure_4.svg'
        text=' '.join(ET.parse(svg).getroot().itertext())
        self.assertIn('Astra annotation',text)
        self.assertIn('Astra',text)
        self.assertNotIn('Opus',text)
        receipt=json.loads((ROOT/'figures/publication/Figure_4_verification.json').read_text())
        self.assertEqual(set(receipt['files']),{'Figure_4.png','Figure_4.pdf','Figure_4.svg','Figure_4.tiff'})
        self.assertGreaterEqual(receipt['minimum_font_pt'],5.5)
        for name,entry in receipt['files'].items():
            p=ROOT/'figures/publication'/name
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),entry['sha256'])
        self.assertIn('cmap="RdYlGn"',(ROOT/'scripts/render_annotation47_figures.py').read_text())

if __name__=='__main__':unittest.main()
