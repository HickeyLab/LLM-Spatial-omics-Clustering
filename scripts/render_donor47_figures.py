"""Cross-donor evaluation figures from checksum-bound offline scores.

Figure5 contains donor reference agreement and frozen-baseline comparisons.
S12 describes the frozen donor partitions; S13 is an evaluation-only ontology
sensitivity on the same eligible cells. Existing B004 artwork is never written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import publication_figure_design as design

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/frozen/donor47_deepseek_completion_20261116'
METHODS=['leiden','flowsom','spatialsort','pixie_tiff']
METHOD_LABELS=['Leiden','FlowSOM','SpatialSort','PIXIE']
FAMILIES=['openai','anthropic','google','deepseek']
MODEL_LABELS=['Astra','Opus 5.5','Argon','DeepSeek']
FULL_MODEL_LABELS=['GPT-6 Astra','Claude Opus 5.5','Gemini 4 Argon','DeepSeek V4.1 Flash 1017']
CLASSIFIERS=['nearest_centroid','logistic_regression']
DONORS=['B005','B006']
PRIMARY='native28_all'
ELIGIBLE_NATIVE='native28_eligible23'
SHARED23='shared23'
ARM='all_means_fractions'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_key(path):
    path=Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


class Scores:
    def __init__(self,directory,*,scope='annotation'):
        self.directory=Path(directory).resolve();self.inputs={}
        path=self.directory/'manifest.json'
        if not path.exists():raise ValueError('Scored-data manifest is required')
        self.manifest=json.loads(path.read_text())
        if scope=='clustering':
            if self.manifest.get('clustering_ready') is not True:
                raise ValueError('Clustering publication requires an admitted clustering score bank')
        elif scope=='annotation':
            if (self.manifest.get('publication_ready') is not True
                    or self.manifest.get('annotation_requests_terminal') is not True):
                raise ValueError('Annotation publication requires terminal requests and an admitted final score bank')
        else:raise ValueError('Unknown publication scope')
        self.scope=scope
        self.inputs[source_key(path)]=sha(path)
    def path(self,name):
        if self.scope=='clustering' and name not in {'clustering_donor_metrics.csv','clustering_pooled_metrics.csv','spatialsort_seed_sensitivity.csv'}:
            raise ValueError('Annotation source cannot use clustering-only admission')
        spec=self.manifest['files'][name];wanted=spec['sha256'] if isinstance(spec,dict) else spec
        path=(self.directory/name).resolve()
        if not path.is_relative_to(self.directory) or sha(path)!=wanted:raise ValueError('Scored figure source changed: '+name)
        self.inputs[source_key(path)]=wanted;return path
    def table(self,name):return pd.read_csv(self.path(name))
    def has(self,name):return name in self.manifest['files']


def evaluation(rows,name):
    if 'evaluation' not in rows:raise ValueError('An explicit evaluation population is required')
    selected=rows[rows.evaluation.eq(name)].copy()
    if selected.empty:raise ValueError('Missing evaluation population: '+name)
    if 'arm' in selected and not selected.arm.eq(ARM).all():
        raise ValueError('Donor annotation figures admit only the frozen means-plus-fractions arm')
    if 'aggregation' in selected and not selected.aggregation.isin(['equal_region','equal_donor']).all():
        raise ValueError('A pooled descriptive score cannot enter the primary equal-region figure')
    return selected


def metric_matrix(rows,metric,*,index=METHODS,columns=FAMILIES,column='family'):
    if rows[['method',column]].duplicated().any():raise ValueError('Duplicate plotted condition')
    expected={(m,c) for m in index for c in columns}
    if set(zip(rows.method,rows[column]))!=expected:raise ValueError('Incomplete or unexpected plotted Cartesian grid')
    values=rows.pivot(index='method',columns=column,values=metric).reindex(index=index,columns=columns).to_numpy(float)
    if not np.isfinite(values).all() or (values<0).any() or (values>1).any():raise ValueError('Metric must be a finite fraction in [0,1]')
    return values


def validate_coverage(rows):
    for name in ['agreement','macro_f1','cell_delivery_coverage','cluster_delivery_coverage']:
        if name not in rows:raise ValueError('Missing planned-denominator metric: '+name)
        values=rows[name].to_numpy(float)
        if not np.isfinite(values).all() or (values<0).any() or (values>1).any():raise ValueError('Invalid metric: '+name)
    if (rows.agreement>rows.cell_delivery_coverage+1e-12).any():
        raise ValueError('Reference agreement cannot exceed delivered-cell coverage')
    if 'n_cells' in rows and (rows.n_cells<=0).any():raise ValueError('Empty evaluation denominator')


def validate_paired_population(native,coarse):
    keys=['donor','method','family']
    for rows in [native,coarse]:
        if rows[keys].duplicated().any():raise ValueError('Duplicate ontology comparison condition')
    joined=native.merge(coarse,on=keys,suffixes=('_native','_coarse'),how='outer',validate='one_to_one',indicator=True)
    if not joined['_merge'].eq('both').all() or not joined.n_cells_native.eq(joined.n_cells_coarse).all():
        raise ValueError('Ontology comparison changed the same-eligible-cell denominator')
    if not np.allclose(joined.cell_delivery_coverage_native,joined.cell_delivery_coverage_coarse,rtol=0,atol=1e-12):
        raise ValueError('Ontology comparison changed native output delivery')


def annotate_heatmap(ax,values,rowlabels,collabels,*,coverage=None,display_scale=100,fmt='.1f'):
    artist=design.heatmap(ax,values*100,rowlabels,collabels,0,100,cmap='RdYlGn')
    ax.set_aspect('auto')
    for (i,j),value in np.ndenumerate(values):
        rgb=np.asarray(artist.cmap(artist.norm(value*100))[:3])
        lin=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        lum=float(lin@[.2126,.7152,.0722]);color='black' if (lum+.05)/.05>=1.05/(lum+.05) else 'white'
        suffix='†' if coverage is not None and coverage[i,j]<1-1e-12 else ''
        ax.text(j,i,format(display_scale*value,fmt)+suffix,ha='center',va='center',fontsize=6.1,color=color)
    return artist


def matrix_panel(fig,letter,x,y,values,columns,condition,*,coverage=None):
    design.panel(fig,letter,x,y)
    design.text(fig,x+44,y+.2,condition,size=6.5,ha='center')
    ax=design.axes(fig,x+17,y+11,54,35)
    artist=annotate_heatmap(ax,values,METHOD_LABELS,columns,coverage=coverage)
    design.colorbar(fig,artist,(x+74,y+11,1.5,35),ticks=[0,50,100],orientation='vertical')
    return ax


def baseline_join(scores,metric):
    llm=evaluation(scores.table('annotation_equal_donor_metrics.csv'),PRIMARY)
    validate_coverage(llm);llm=llm.assign(annotator=llm.family)
    base=scores.table('baselines_donor_metrics.csv')
    base=evaluation(base[base.arm.eq(ARM)],PRIMARY)
    if base[['donor','method','classifier']].duplicated().any():raise ValueError('Duplicate donor baseline')
    expected={(d,m,c) for d in DONORS for m in METHODS for c in CLASSIFIERS}
    if set(zip(base.donor,base.method,base.classifier))!=expected:raise ValueError('Baseline donor grid differs')
    base=base.groupby(['method','classifier'],sort=False,as_index=False)[[metric,'cell_delivery_coverage']].mean()
    base=base.rename(columns={'classifier':'annotator'})
    combined=pd.concat([llm[['method','annotator',metric,'cell_delivery_coverage']],base],ignore_index=True)
    columns=FAMILIES+CLASSIFIERS
    return (metric_matrix(combined,metric,column='annotator',columns=columns),
            metric_matrix(combined,'cell_delivery_coverage',column='annotator',columns=columns))


def seed_comparison(scores):
    seed=scores.table('spatialsort_seed_sensitivity.csv')
    seed=seed[seed.evaluation.eq(PRIMARY)&seed.aggregation.eq('pooled_descriptive')].copy()
    if len(seed)!=2 or set(seed.donor)!=set(DONORS) or seed.donor.duplicated().any():
        raise ValueError('Global common-cell seed comparison donor grid differs')
    return seed


def figure5(scores,output):
    if scores.scope!='annotation':raise ValueError('Annotation figure cannot use clustering-only admission')
    rows=evaluation(scores.table('annotation_donor_metrics.csv'),PRIMARY);validate_coverage(rows)
    if set(rows.donor)!=set(DONORS) or len(rows)!=32:raise ValueError('Exactly32 donor-specific annotation sets are required')
    f=design.figure(125)
    for i,donor in enumerate(DONORS):
        selected=rows[rows.donor.eq(donor)]
        matrix_panel(f,chr(65+i),3+80*i,3,metric_matrix(selected,'agreement'),MODEL_LABELS,
            donor,coverage=metric_matrix(selected,'cell_delivery_coverage'))
    for i,(metric,label) in enumerate([('agreement','Agreement (%)'),('macro_f1','Macro-F1 (%)')]):
        values,coverage=baseline_join(scores,metric)
        x,y=3+80*i,65
        design.panel(f,chr(67+i),x,y)
        design.text(f,x+44,y+.2,label,size=6.5,ha='center')
        llm_ax=design.axes(f,x+17,y+11,34,35)
        annotate_heatmap(llm_ax,values[:,:4],METHOD_LABELS,MODEL_LABELS,coverage=coverage[:,:4])
        llm_ax.text(1.5,-.68,'LLMs',ha='center',va='bottom',fontsize=5.5,clip_on=False)
        classifier_ax=design.axes(f,x+54,y+11,17,35)
        artist=annotate_heatmap(classifier_ax,values[:,4:],METHOD_LABELS,
            ['Nearest\ncentroid','Logistic\nregression'],coverage=coverage[:,4:])
        classifier_ax.tick_params(axis='y',left=False,labelleft=False)
        classifier_ax.text(.5,-.68,'B004-supervised\nclassifiers',ha='center',va='bottom',
                fontsize=5.5,linespacing=1.05,clip_on=False)
        design.colorbar(f,artist,(x+74,y+11,1.5,35),ticks=[0,50,100],orientation='vertical')
    return design.finish(f,'Figure_5',output,dict(scores.inputs),notes=[
        'A,B: native 28-label evaluation including Noise; each donor averages its eight region scores equally.',
        'C,D: equal donor weights after equal region weights; frozen B004 classifiers use the same 94 decoded query features.',
        'The completed score bank has 100% cell and cluster prediction delivery. For archival inputs, † marks incomplete delivery.',
        'One planned annotation per cluster/condition; accepted outputs are scored where available. No repeat SD, confidence interval or repeatability claim.',
        'Baselines use training-cell reference labels, richer supervision than supplied to the LLMs; no donor fitting/tuning.',
    ])


def figure_s12(scores,output):
    rows=scores.table('clustering_donor_metrics.csv')
    if 'evaluation' in rows:rows=evaluation(rows,PRIMARY)
    if rows[['donor','method']].duplicated().any() or set(zip(rows.donor,rows.method))!={(d,m) for d in DONORS for m in METHODS}:
        raise ValueError('Donor clustering grid differs')
    has_seed=scores.has('spatialsort_seed_sensitivity.csv')
    f=design.figure(104 if has_seed else 58)
    for i,(metric,label) in enumerate([('purity','Purity (%)'),('ari','ARI')]):
        x=3+80*i;design.panel(f,chr(65+i),x,3);design.text(f,x+46,3,label,size=6.5,ha='center')
        values=rows.pivot(index='donor',columns='method',values=metric).reindex(index=DONORS,columns=METHODS).to_numpy(float)
        if not np.isfinite(values).all() or (values<0).any() or (values>1).any():raise ValueError('Invalid clustering metric')
        ax=design.axes(f,x+17,15,54,22)
        artist=annotate_heatmap(ax,values,DONORS,METHOD_LABELS,display_scale=1 if metric=='ari' else 100,fmt='.3f' if metric=='ari' else '.1f')
        bar=design.colorbar(f,artist,(x+74,15,1.5,22),ticks=[0,50,100],orientation='vertical')
        if metric=='ari':bar.set_ticklabels(['0','0.5','1'])
    if has_seed:
        seed=seed_comparison(scores)
        values=seed.set_index('donor').partition_ari.reindex(DONORS).to_numpy(float)
        if not np.isfinite(values).all() or (values<0).any() or (values>1).any():raise ValueError('Invalid seed partition ARI')
        design.panel(f,'C',3,60);design.text(f,86,60,'Seed 42 / seed 43',size=6.5,ha='center')
        ax=design.axes(f,25,71,126,18)
        ax.scatter(values,np.arange(2),s=16,color='#315f4b',zorder=3)
        for i,v in enumerate(values):ax.text(v+.018,i,f'{v:.3f}',va='center',fontsize=6)
        ax.set(yticks=[0,1],yticklabels=DONORS,ylim=(1.5,-.5),xlim=(0,1),xticks=[0,.25,.5,.75,1],xlabel='Partition ARI')
        design.grid(ax,'x')
    return design.finish(f,'Figure_S12',output,dict(scores.inputs),notes=[
        'Frozen method-specific donor partitions, evaluated against native 28-label references; annotation profiles contain all 47 proteins and SpatialSort seed 42 is primary.',
        'A,B average eight regions equally within each donor; C is a global common-cell membership comparison.',
        'No reference-guided partition selection or donor retuning.',
        'C, if present: global common-cell partition ARI between seeds 42 and 43; clustering stability only, with no seed-43 annotation calls.',
    ])


def figure_s13(scores,output):
    if scores.scope!='annotation':raise ValueError('Annotation figure cannot use clustering-only admission')
    rows=scores.table('annotation_donor_metrics.csv')
    original = evaluation(rows, ELIGIBLE_NATIVE)
    projected = evaluation(rows, SHARED23)
    validate_coverage(original)
    validate_coverage(projected)
    validate_paired_population(original, projected)

    f = design.figure(125)
    vocabularies = (
        (original, 'Original 28-label vocabulary'),
        (projected, 'Projected 23-label vocabulary'),
    )
    for i, donor in enumerate(DONORS):
        for j, (selected, vocabulary) in enumerate(vocabularies):
            data = selected[selected.donor.eq(donor)]
            matrix_panel(
                f, chr(65 + i * 2 + j), 3 + 80 * j, 3 + 62 * i,
                metric_matrix(data, 'agreement'), MODEL_LABELS,
                f'{donor} / {vocabulary}',
                coverage=metric_matrix(data, 'cell_delivery_coverage'),
            )
    return design.finish(f, 'Figure_S13', output, dict(scores.inputs), notes=[
        'Both vocabularies score the same predictions on the same reference-eligible cells within each donor.',
        'Predictions outside the projected 23-label vocabulary remain errors.',
        'The evaluation excludes cells with Noise, ITLN+ Epithelial and PDPN+ Stromal reference labels.',
        'The completed bank has 100% prediction delivery. Table S15 reports projected-vocabulary coverage. For archival inputs, † marks incomplete prediction delivery.',
    ])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=DATA)
    p.add_argument('--output',type=Path,default=ROOT/'figures/publication');p.add_argument('--figures',nargs='+',default=['5','S12','S13'])
    a=p.parse_args();scores=Scores(a.data,scope='clustering' if set(a.figures)=={'S12'} else 'annotation');a.output.mkdir(parents=True,exist_ok=True)
    renderers={'5':figure5,'S12':figure_s12,'S13':figure_s13}
    # Isolate each receipt's consumed inputs rather than accumulating sources
    # from previously rendered figures in a multi-figure command.
    receipts={name:renderers[name](Scores(a.data,scope='clustering' if name=='S12' else 'annotation'),a.output)
              for name in a.figures}
    manifest={'schema':'donor47.publication_figures.v1','new_calls_or_fits':0,'source_manifest':source_key(a.data/'manifest.json'),
        'scope':scores.scope,'planned_annotation_sets':32,'planned_initial_request_items':128,'planned_cluster_predictions':9468,'annotation_arm':ARM,
        'source_manifest_sha256':sha(a.data/'manifest.json'),'renderer_sha256':sha(__file__),
        'shared_style_sha256':sha(ROOT/'scripts/publication_figure_design.py'),'figures':receipts}
    (a.output/'donor47_figure_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
