"""Frozen primary clustering replay stays separate from historical annotations."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from llm_spatial_omics_clustering import clustering_publication as current
from llm_spatial_omics_clustering import manuscript

ROOT=Path(__file__).resolve().parents[1]


class CurrentClusteringContractTests(unittest.TestCase):
    def test_frozen_partitions_join_the_entire_cohort(self):
        config,manifest=current.contract(ROOT)
        self.assertTrue(config['annotation_execution_disabled'])
        self.assertGreaterEqual(current.verify_current_inputs(ROOT),40)
        markers=json.loads((ROOT/manifest['marker_order_path']).read_text())
        self.assertEqual(len(markers),47)
        self.assertEqual(len(set(markers)),47)
        self.assertTrue({'CD123','CDX2'}.issubset(markers))
        truth=pd.read_csv(manuscript.INPUTS/'figure_02/truth.csv.gz',dtype={'File_ID':str,'ID':str})
        keys=['File_ID','ID']
        for method,spec in current.clustering_assignment_specs(ROOT).items():
            frame=pd.read_csv(spec['assignment_path'],dtype=str)
            self.assertFalse(frame.duplicated(keys).any())
            self.assertEqual(len(frame),220082)
            self.assertEqual(len(truth.merge(frame,on=keys,validate='one_to_one')),220082)
            self.assertEqual(frame[spec['assignment_column']].nunique(),spec['observed_clusters'])
        self.assertEqual(manifest['methods']['flowsom']['observed_clusters'],299)
        self.assertEqual(manifest['methods']['spatialsort']['observed_clusters'],229)
        self.assertEqual(manifest['sensitivity']['spatialsort_seed43']['observed_clusters'],231)

    def test_current_and_annotation_scopes_are_distinct(self):
        path=current.override_path('reference_plot_cells.csv.gz',root=ROOT)
        new=pd.read_csv(path,dtype={'File_ID':str,'ID':str})
        old=pd.read_csv(ROOT/'data/frozen/publication_design/reference_plot_cells.csv.gz',dtype={'File_ID':str,'ID':str})
        for name in old.columns:
            if name not in ['flowsom','spatialsort']:
                pd.testing.assert_series_equal(old[name],new[name])
        self.assertIsNone(current.override_path('figure3_agreement.csv',root=ROOT))
        self.assertIsNone(current.override_path('figure_03/metrics.csv','replay_table_overrides',root=ROOT))
        with self.assertRaisesRegex(ValueError,'historical'):
            manuscript.figure_2_panel('I')

    def test_s4_and_s5_keep_their_declared_ontologies(self):
        raw=pd.read_csv(current.override_path('figureS5_fixed_metrics.csv',root=ROOT))
        regional=raw.loc[raw.noise_policy.eq('exclude')&raw.region.ne('ALL')]
        self.assertEqual(len(regional),32)
        self.assertTrue(regional.groupby('method').size().eq(8).all())
        self.assertTrue(regional.n_reference_labels.le(27).all())
        global_=raw.loc[raw.noise_policy.eq('include')&raw.region.eq('ALL')]
        self.assertTrue(global_.n_reference_labels.eq(28).all())
        conditional=pd.read_csv(current.override_path('conditional_comparisons.csv','companion_table_overrides',root=ROOT))
        original=pd.read_csv(ROOT/'data/frozen/manuscript_replay/tables/companions/conditional_comparisons.csv')
        self.assertEqual(len(conditional),12)
        self.assertTrue(conditional.family.eq('Figure2_EG_12').all())
        observations=pd.read_csv(current.override_path('paired_regional_observations.csv','companion_table_overrides',root=ROOT))
        self.assertEqual(len(observations),96)
        self.assertTrue(observations.family.eq('Figure2_EG_12').all())
        archival=pd.read_csv(ROOT/'data/frozen/clustering47_primary_20261108/conditional_comparisons_all_families.csv')
        other=original.loc[original.family.ne('Figure2_EG_12')].reset_index(drop=True)
        pd.testing.assert_frame_equal(other,archival.loc[archival.family.ne('Figure2_EG_12')].reset_index(drop=True))

    def test_s4_reference_display_uses_all_47_channels(self):
        import yaml
        cfg=yaml.safe_load((ROOT/'configs/figure_s03.yaml').read_text())
        markers=cfg['panel_a']['marker_order']
        self.assertEqual(len(markers),47)
        self.assertEqual(len(set(markers)),47)
        self.assertEqual(markers[-2:],['CD123','CDX2'])
        folder=ROOT/'data/frozen/reference47_profiles_20261110'
        manifest=json.loads((folder/'manifest.json').read_text())
        for name,entry in manifest['files'].items():
            self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(),entry['sha256'])
        data=pd.read_csv(folder/'figureS4_marker_summaries.csv')
        receipt=json.loads((ROOT/'figures/publication/Figure_S4_verification.json').read_text())
        source='data/frozen/reference47_profiles_20261110/figureS4_marker_summaries.csv'
        self.assertEqual(receipt['inputs'][source],manifest['files']['figureS4_marker_summaries.csv']['sha256'])
        self.assertEqual(len(data),27*47)
        self.assertEqual(set(data.marker),set(markers))
        self.assertEqual(data.cell_type.nunique(),27)
        self.assertFalse(data.duplicated(['cell_type','marker']).any())
        self.assertEqual(int(data.groupby('cell_type').n_cells.first().sum()),209587)
        self.assertNotIn('Noise',set(data.cell_type))

    def test_bad_manifest_or_primary_seed_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'configs').mkdir()
            m={'schema':'clustering.publication.primary47.v1','primary_spatialsort_seed':43,'spatialsort_sensitivity_seed':42}
            p=root/'manifest.json';p.write_text(json.dumps(m))
            config={'manifest':'manifest.json','manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            (root/current.CONFIG).write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError,'selection changed'):current.contract(root)
            p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'checksum'):current.contract(root)


if __name__=='__main__':unittest.main()
