#!/usr/bin/env python3
"""Independently verify current figure values from frozen cell-level evidence.

No network, LLM inference, clustering, fitting, or manuscript edits are used.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_recall_fscore_support
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from llm_spatial_omics_clustering.manuscript import INPUTS, artwork, inventory, verify_inputs

KEYS=['File_ID','ID']
METHODS={'leiden':'Leiden','flowsom':'FlowSOM','spatialsort':'SpatialSort','pixie':'PIXIE'}
MODELS=['gpt','claude','gemini','deepseek']


def verify():
    files=verify_inputs()
    truth=pd.read_csv(INPUTS/'figure_02/truth.csv.gz',dtype={k:str for k in KEYS})
    annotations=pd.read_csv(INPUTS/'figure_03/annotations.csv.gz',dtype={k:str for k in KEYS})
    assert len(truth)==len(annotations)==220082
    assert not truth.duplicated(KEYS).any() and not annotations.duplicated(KEYS).any()
    assert truth.cell_type_update.eq('Noise').sum()==10495
    config=yaml.safe_load((ROOT/'configs/figure_02.yaml').read_text())
    truth['label20']=truth.cell_type_update.replace(config['panel_e']['evaluation']['harmonization_map'])
    manifest=json.loads((ROOT/'data/frozen/v3_k300_assignments/manifest.json').read_text())
    regional=pd.read_csv(INPUTS/'figure_02/regional_metrics.csv')
    celltype=pd.read_csv(INPUTS/'figure_02/celltype_metrics.csv')
    score3=pd.read_csv(INPUTS/'figure_03/metrics.csv')
    celltype3=pd.read_csv(INPUTS/'figure_03/celltype_metrics.csv')
    selected=pd.read_csv(ROOT/'data/frozen/figure_02_publication_metrics/regional_selected_agreement.csv')
    regional_checks=0;pertype_checks=0;annotation_checks=0
    for method,title in METHODS.items():
        spec=manifest['methods'][method]
        path=ROOT/'data/frozen/v3_k300_assignments'/spec['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==spec['gzip_sha256']
        partition=pd.read_csv(path,dtype=str)[KEYS+[spec['assignment_column']]].rename(columns={spec['assignment_column']:'cluster'})
        frame=truth.merge(partition,on=KEYS,validate='one_to_one')
        assert len(frame)==220082 and frame.cluster.nunique()==spec['observed_clusters']
        frame=frame.loc[frame.cell_type_update.ne('Noise')]
        assert len(frame)==209587
        for region,part in frame.groupby('File_ID'):
            c=pd.crosstab(part.cluster,part.label20);majority=c.idxmax(axis=1)
            prediction=part.cluster.map(majority)
            row=regional.loc[regional.method.eq(title)&regional.region.eq(region)].iloc[0]
            np.testing.assert_allclose(row.weighted_f1,f1_score(part.label20,prediction,average='weighted',zero_division=0),rtol=0,atol=1e-12)
            np.testing.assert_allclose(row.cluster_purity,c.max(axis=1).sum()/len(part),rtol=0,atol=1e-12)
            regional_checks+=2
        c=pd.crosstab(frame.cluster,frame.label20)
        prediction=frame.cluster.map(c.idxmax(axis=1))
        labels=sorted(frame.label20.unique())
        _,recall,f1,support=precision_recall_fscore_support(frame.label20,prediction,labels=labels,zero_division=0)
        rows=celltype.loc[celltype.method.eq(title)].set_index('cell_type').reindex(labels)
        np.testing.assert_allclose(rows.f1,f1,rtol=0,atol=1e-12)
        np.testing.assert_allclose(rows.recall,recall,rtol=0,atol=1e-12)
        np.testing.assert_array_equal(rows.n_cells,support)
        pertype_checks+=len(labels)*2
        raw=annotations.merge(partition,on=KEYS,validate='one_to_one')
        ct=pd.crosstab(raw.cluster,raw.truth_normalized)
        bound=ct.max(axis=1).sum()
        nn=raw.loc[raw.truth_normalized.ne('Noise')].copy()
        nn['majority']=nn.cluster.map(pd.crosstab(nn.cluster,nn.truth_normalized).idxmax(axis=1))
        prefix='pixie_tiff' if method=='pixie' else method
        for model in MODELS:
            prediction=raw[prefix+'__'+model]
            row=score3.loc[score3.method.eq(title)&score3.model.eq(model)].iloc[0]
            matching=prediction.eq(raw.truth_normalized)
            selected_cells=matching|raw.phase7_prediction.eq(raw.truth_normalized)
            cluster_counts=pd.crosstab(raw.cluster,selected_cells).reindex(columns=[False,True],fill_value=0)
            np.testing.assert_allclose([row.agreement,row.percent_upper_bound,row.selected_cell_agreement,row.selected_cluster_agreement],
                [matching.sum()/len(raw),100*matching.sum()/bound,selected_cells.sum()/len(raw),(cluster_counts[True]/cluster_counts.sum(axis=1)).mean()],rtol=0,atol=1e-12)
            old=selected.loc[selected.clustering_method.eq(prefix)&selected.llm.eq(model)]
            np.testing.assert_allclose(row.selected_cell_agreement,old.correct_cells.sum()/old.n_cells.sum(),rtol=0,atol=1e-12)
            for label,group in nn.groupby('truth_normalized'):
                target=celltype3.loc[celltype3.method.eq(title)&celltype3.model.eq(model)&celltype3.cell_type.eq(label)].iloc[0]
                correct=group[prefix+'__'+model].eq(label).sum();upper=group.majority.eq(label).sum()
                np.testing.assert_allclose(target.agreement,correct/len(group),rtol=0,atol=1e-12)
                if upper:np.testing.assert_allclose(target.percent_upper_bound,100*correct/upper,rtol=0,atol=1e-10)
            annotation_checks+=1
    markers=pd.read_csv(INPUTS/'figure_02/panel_I_marker_summaries.csv')
    assert len(markers)==180 and markers.marker.nunique()==45
    np.testing.assert_allclose(markers.fraction_cells_pct,100*markers.n_above_zero/markers.n_selected_cells,rtol=0,atol=1e-12)
    for marker,group in markers.groupby('marker'):
        lo,hi=group.mean_expression.min(),group.mean_expression.max()
        expected=(group.mean_expression-lo)/(hi-lo) if hi!=lo else np.zeros(len(group))
        np.testing.assert_allclose(group.scaled_mean_expression,expected,rtol=0,atol=1e-12)
    zoom=pd.read_csv(INPUTS/'figure_02/panel_J_zoom_cells.csv',dtype={k:str for k in KEYS})
    assert sorted(zoom.groupby('example').size())==[915,1086]
    merged=zoom.merge(annotations,on=KEYS,validate='one_to_one')
    for method,title in METHODS.items():
        prefix='pixie_tiff' if method=='pixie' else method
        votes=merged[[prefix+'__'+m for m in MODELS]]
        modal=[next(v for v in row if list(row).count(v)==max(list(row).count(x) for x in row)) for row in votes.itertuples(index=False,name=None)]
        assert np.array_equal(modal,merged[title])
    paired=pd.read_csv(INPUTS/'paired/paired_summary.csv')
    repeats=pd.read_csv(INPUTS/'paired/paired_repeat_metrics.csv')
    assert len(paired)==16 and (paired.delta_agreement_mean<0).sum()==15
    for row in paired.itertuples():
        group=repeats.loc[repeats.model.eq(row.model)&repeats.method.eq(row.method)]
        assert len(group)==3
        for arm in ['means','fractions']:
            np.testing.assert_allclose([getattr(row,arm+'_agreement_mean'),getattr(row,arm+'_agreement_sd')],
                [group[arm+'_agreement'].mean(),group[arm+'_agreement'].std(ddof=1)],rtol=0,atol=1e-12)
    image_count=sum(len(artwork(key)) for key in inventory()['figures'])
    return {'status':'pass','frozen_input_files':files,'approved_images':image_count,
            'figure_2_regional_values':regional_checks,'figure_2_celltype_values':pertype_checks,
            'figure_3_method_model_maps':annotation_checks,'spatial_window_cells':[1086,915],
            'paired_representation_comparisons':16,'new_model_calls':0,'new_fits':0,'network_access':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',type=Path)
    args=parser.parse_args();result=verify()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True,exist_ok=True);args.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
