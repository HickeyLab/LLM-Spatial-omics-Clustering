"""Protect grids, denominators and scope of the new donor figures."""
import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import render_donor47_figures as r


class FigureContractTests(unittest.TestCase):
    def test_repository_source_reference_is_portable(self):
        self.assertEqual(r.source_key(r.DATA/'manifest.json'),'data/frozen/donor47_results_20261114/manifest.json')
    def data(self):
        return pd.DataFrame([{'method':m,'family':f,'agreement':.4,'macro_f1':.3,
            'cell_delivery_coverage':1.,'cluster_delivery_coverage':1.} for m in r.METHODS for f in r.FAMILIES])
    def test_grid_preserves_fixed_logical_order(self):
        d=self.data();d.loc[0,'agreement']=.7
        matrix=r.metric_matrix(d.iloc[::-1],'agreement')
        self.assertEqual(matrix.shape,(4,4));self.assertEqual(matrix[0,0],.7)
    def test_missing_or_duplicate_conditions_are_rejected(self):
        d=self.data()
        for bad in [d.iloc[:-1],pd.concat([d,d.iloc[:1]])]:
            with self.assertRaises(ValueError):r.metric_matrix(bad,'agreement')
    def test_incomplete_delivery_scores_remain_valid_with_planned_denominator(self):
        d=self.data();d.loc[0,['agreement','cell_delivery_coverage','cluster_delivery_coverage']]=[.3,.7,.75]
        r.validate_coverage(d);self.assertEqual(r.metric_matrix(d,'agreement')[0,0],.3)
        d.loc[0,'agreement']=.8
        with self.assertRaises(ValueError):r.validate_coverage(d)
    def test_pooled_metrics_cannot_enter_primary_panels(self):
        d=self.data().assign(evaluation=r.PRIMARY,aggregation='pooled_descriptive')
        with self.assertRaises(ValueError):r.evaluation(d,r.PRIMARY)
    def test_nonfinite_or_out_of_range_values_are_rejected(self):
        for value in [np.nan,-.1,1.1]:
            d=self.data();d.loc[0,'agreement']=value
            with self.assertRaises(ValueError):r.metric_matrix(d,'agreement')
    def test_seed_panel_uses_global_common_cell_population(self):
        rows=pd.DataFrame([{'donor':d,'evaluation':e,'aggregation':a,'partition_ari':v}
            for d in r.DONORS for e in [r.PRIMARY,r.SHARED23]
            for a,v in [('region',.1),('pooled_descriptive',.7)]])
        class Source:
            def table(self,name):return rows.copy()
        selected=r.seed_comparison(Source())
        self.assertEqual(len(selected),2)
        self.assertTrue(selected.partition_ari.eq(.7).all())
        self.assertTrue(selected.evaluation.eq(r.PRIMARY).all())
    def test_clustering_readiness_never_admits_annotation_figures_or_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            (directory/'manifest.json').write_text(json.dumps({'clustering_ready':True,'publication_ready':False,
                'annotation_requests_terminal':False,'files':{}}))
            scores=r.Scores(directory,scope='clustering')
            with self.assertRaises(ValueError):r.Scores(directory)
            with self.assertRaises(ValueError):scores.path('annotation_donor_metrics.csv')
            with self.assertRaises(ValueError):r.figure5(scores,directory)
            with self.assertRaises(ValueError):r.figure_s13(scores,directory)
    def test_ontology_panels_reject_changed_eligible_population(self):
        native=self.data().assign(donor='B005',n_cells=100)
        coarse=native.copy();r.validate_paired_population(native,coarse)
        coarse.loc[0,'n_cells']=99
        with self.assertRaises(ValueError):r.validate_paired_population(native,coarse)


if __name__=='__main__':unittest.main()
