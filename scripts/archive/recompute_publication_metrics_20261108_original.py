#!/usr/bin/env python3
"""Read-only, fixed-partition publication diagnostics for the November8 refresh.

Writes only to this metrics directory. Does not fit, select, annotate or publish.
The publication20-class map is deliberately distinct from the historical21
annotation diagnostic map: Paneth→Goblet versus Paneth→Neuroendocrine.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip, hashlib, itertools, json, os, platform, sys

for var in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[var] = '2'
import numpy as np
import pandas as pd
import scipy
from scipy.stats import permutation_test
import sklearn
from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score
from sklearn.metrics import precision_recall_fscore_support, f1_score
import yaml

OUT=Path(__file__).resolve().parent
REPO=OUT.parent/'repo'
DATA=REPO/'data/frozen/publication_design'
REPLAY=REPO/'data/frozen/manuscript_replay'
FLOW=Path('/Users/zacharydeutsch/Desktop/cell_masks/revision_20261021/data/frozen/flowsom47_primary_20261102')
SPAT=Path('/Users/zacharydeutsch/.codex/analysis_artifacts/spatialsort47_results_20261108/inputs')
SPAT_RECEIPT=Path('/Users/zacharydeutsch/.codex/analysis_artifacts/spatialsort47_hubmap_20261102/completion_receipt.json')
HIST=Path('/Users/zacharydeutsch/.codex/analysis_artifacts/cell_masks_marker47_20261101/scoring_policy.json')
KEYS=['File_ID','ID']
METHODS={'leiden':'Leiden','flowsom':'FlowSOM','spatialsort':'SpatialSort','pixie':'PIXIE'}
BASE_COLUMNS=['File_ID','ID','x','y','cell_type_update','leiden','flowsom','spatialsort','pixie']
SOURCE_HASHES={}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source(path):
    SOURCE_HASHES[str(path)]=sha(path)
    return path

def save(frame,name):
    path=OUT/name
    if path.suffix=='.gz':
        with path.open('wb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as stream:
                stream.write(frame.to_csv(index=False).encode())
    else:frame.to_csv(path,index=False)

def majority(labels,clusters):
    counts=pd.crosstab(clusters,labels).sort_index(axis=1)
    mapping=counts.idxmax(axis=1)
    pred=clusters.map(mapping)
    ties=int((counts.eq(counts.max(axis=1),axis=0).sum(axis=1)>1).sum())
    return counts,mapping,pred,ties

def class_metrics(labels,predicted):
    vocabulary=sorted(labels.unique())
    precision,recall,f1,support=precision_recall_fscore_support(labels,predicted,labels=vocabulary,zero_division=0)
    # Independent count formula, including zero-prediction classes.
    ct=pd.crosstab(labels,predicted).reindex(index=vocabulary,columns=vocabulary,fill_value=0)
    true=ct.sum(axis=1).to_numpy();pred=ct.sum(axis=0).to_numpy();tp=np.diag(ct)
    independent=np.divide(2*tp,true+pred,out=np.zeros(len(tp),float),where=(true+pred)>0)
    np.testing.assert_allclose(f1,independent,rtol=0,atol=1e-14)
    np.testing.assert_array_equal(support,true)
    return pd.DataFrame({'cell_type':vocabulary,'precision':precision,'recall':recall,'f1':f1,'n_cells':support})

def independent_ari(labels,clusters):
    table=Counter(zip(labels,clusters));a=Counter(labels);b=Counter(clusters)
    pairs=lambda vals:sum(int(x)*(int(x)-1)//2 for x in vals)
    total=len(labels)*(len(labels)-1)//2
    x,aa,bb=pairs(table.values()),pairs(a.values()),pairs(b.values())
    denominator=(aa+bb)*total-2*aa*bb
    return 2*(x*total-aa*bb)/denominator if denominator else 1.

def subset_metrics(labels,clusters):
    ct,mapping,pred,ties=majority(labels,clusters)
    cm=class_metrics(labels,pred)
    sizes=ct.sum(axis=1)
    purity=float(ct.max(axis=1).sum()/len(labels))
    direct=defaultdict(Counter)
    for c,t in zip(clusters,labels):direct[c][t]+=1
    assert sum(max(x.values()) for x in direct.values())==ct.max(axis=1).sum()
    ari=float(adjusted_rand_score(labels,clusters))
    assert abs(ari-independent_ari(labels,clusters))<2e-13
    weighted=float(np.average(cm.f1,weights=cm.n_cells))
    assert abs(weighted-f1_score(labels,pred,average='weighted',zero_division=0))<1e-13
    return {'n_cells':len(labels),'n_reference_labels':labels.nunique(),'n_clusters':len(ct),
        'purity':purity,'ari':ari,'ami':float(adjusted_mutual_info_score(labels,clusters)),
        'majority_macro_f1':float(cm.f1.mean()),'majority_weighted_f1':weighted,
        'min_cluster_cells':int(sizes.min()),'median_cluster_cells':float(sizes.median()),
        'max_cluster_cells':int(sizes.max()),'tied_majority_clusters':ties}

def publication_metrics(frame,mapping):
    nn=frame.loc[frame.cell_type_update.ne('Noise')].copy()
    nn['label']=nn.cell_type_update.replace(mapping)
    assert len(nn)==209587 and nn.label.nunique()==20
    regional,types,global_maps,region_maps,pooled,ties=[],[],[],[],[],[]
    for key,title in METHODS.items():
        ct,mp,pred,t=majority(nn.label,nn[key])
        cm=class_metrics(nn.label,pred);cm['method']=title;types.append(cm)
        global_maps.extend({'method':title,'cluster':c,'majority_label':label} for c,label in mp.items())
        pooled.append({'method':title,'method_key':key,**subset_metrics(nn.label,nn[key])})
        ties.append({'method':title,'scope':'global','region':'ALL','tied_majority_clusters':t})
        for region,part in nn.groupby('File_ID',sort=True):
            ct,mp,pred,t=majority(part.label,part[key]);cm=class_metrics(part.label,pred)
            regional.append({'method':title,'method_key':key,'region':region,'n_cells':len(part),
                'weighted_f1':float(np.average(cm.f1,weights=cm.n_cells)),
                'cluster_purity':float(ct.max(axis=1).sum()/len(part)),'n_clusters':len(ct)})
            region_maps.extend({'method':title,'region':region,'cluster':c,'majority_label':label} for c,label in mp.items())
            ties.append({'method':title,'scope':'regional','region':region,'tied_majority_clusters':t})
    return pd.DataFrame(regional),pd.concat(types,ignore_index=True),pd.DataFrame(global_maps),pd.DataFrame(region_maps),pd.DataFrame(pooled),pd.DataFrame(ties)

def raw_metrics(frame,method_keys=METHODS):
    compositions,cluster_rows,type_rows,scores=[],[],[],[]
    for key in method_keys:
        comp=frame.groupby([key,'cell_type_update'],sort=True).size().rename('n_cells').reset_index().rename(columns={key:'cluster','cell_type_update':'cell_type'})
        comp['method']=key;compositions.append(comp[['method','cluster','cell_type','n_cells']])
        nn=frame.loc[frame.cell_type_update.ne('Noise')]
        ct,mp,pred,t=majority(nn.cell_type_update,nn[key])
        for cluster,row in ct.iterrows():
            probs=row[row>0].to_numpy()/row.sum()
            cluster_rows.append({'method':key,'cluster':cluster,'majority_label':mp[cluster],
                'n_cells':int(row.sum()),'shannon_index':float(-(probs*np.log(probs)).sum()),
                'purity_percent':float(probs.max()*100)})
        cm=class_metrics(nn.cell_type_update,pred);cm['method']=key
        type_rows.append(cm[['method','cell_type','f1','recall']])
        for noise in ['include','exclude']:
            used=frame if noise=='include' else nn
            for region in ['ALL',*sorted(used.File_ID.unique())]:
                part=used if region=='ALL' else used.loc[used.File_ID.eq(region)]
                values=subset_metrics(part.cell_type_update,part[key]);values.pop('tied_majority_clusters')
                scores.append({'method':key,'region':region,'noise_policy':noise,'ontology':'original_reference_labels',
                    **values,'majority_mapping':'same_evaluation_subset_lexical_ties',
                    'interpretation':'descriptive reference agreement; oracle majority labels; not predictive validation'})
    return pd.concat(compositions,ignore_index=True),pd.DataFrame(cluster_rows),pd.concat(type_rows,ignore_index=True),pd.DataFrame(scores)

def conditional_tests(regional):
    all_tests=pd.read_csv(source(REPLAY/'tables/companions/conditional_comparisons.csv'))
    all_obs=pd.read_csv(source(REPLAY/'tables/companions/paired_regional_observations.csv'))
    tests=all_tests.loc[all_tests.family.eq('Figure2_EG_12')].copy()
    observations=all_obs.loc[all_obs.family.eq('Figure2_EG_12')].copy()
    assert len(tests)==12 and len(observations)==96
    signs=np.array(list(itertools.product([-1,1],repeat=8)))
    for index,row in tests.iterrows():
        a=regional.loc[regional.method_key.eq(row.condition_a)].set_index('region')[row.metric]
        b=regional.loc[regional.method_key.eq(row.condition_b)].set_index('region')[row.metric]
        a,b=a.align(b);assert len(a)==8 and a.notna().all() and b.notna().all()
        delta=(a-b).to_numpy()*100
        permutations=signs@delta/8
        p=float(np.mean(np.abs(permutations)>=abs(delta.mean())-1e-12))
        independent=sum(abs(sum(s*x for s,x in zip(sign,d))/8)>=abs(delta.mean())-1e-12 for sign in itertools.product([-1,1],repeat=8) for d in [delta])/256
        assert independent==p
        sp=permutation_test((a.to_numpy(),b.to_numpy()),lambda x,y,axis:np.mean(x-y,axis=axis),
            permutation_type='samples',n_resamples=np.inf,alternative='two-sided',vectorized=True).pvalue
        assert abs(sp-p)<1e-14,(row.metric,row.condition_a,row.condition_b,sp,p)
        rng=np.random.default_rng(42);boot=delta[rng.integers(0,8,size=(10000,8))].mean(axis=1)
        lo,hi=np.quantile(boot,[.025,.975])
        tests.loc[index,['mean_a_percent','mean_b_percent','mean_difference_pp','median_difference_pp','region_interval_low_pp','region_interval_high_pp','raw_p','scipy_p']]=[a.mean()*100,b.mean()*100,delta.mean(),np.median(delta),lo,hi,p,sp]
        mask=observations.metric.eq(row.metric)&observations.condition_a.eq(row.condition_a)&observations.condition_b.eq(row.condition_b)
        assert mask.sum()==8
        for region in a.index:
            select=mask&observations.region.eq(region)
            observations.loc[select,['value_a','value_b','difference_pp']]=[a[region],b[region],100*(a[region]-b[region])]
    order=np.argsort(tests.raw_p.to_numpy(),kind='stable')
    adjusted=np.minimum(1,np.maximum.accumulate(tests.raw_p.to_numpy()[order]*np.arange(12,0,-1)))
    tests.loc[tests.index[order],'holm_adjusted_p']=adjusted
    tests['holm_below_0_05']=tests.holm_adjusted_p.lt(.05)
    # Preserve the other48 test rows and their observation rows exactly as values.
    combined_tests=all_tests.copy();combined_obs=all_obs.copy()
    for idx in tests.index:
        for col in tests.columns:combined_tests.at[idx,col]=tests.at[idx,col]
    for idx in observations.index:
        for col in observations.columns:combined_obs.at[idx,col]=observations.at[idx,col]
    pd.testing.assert_frame_equal(combined_tests.loc[~all_tests.family.eq('Figure2_EG_12')],all_tests.loc[~all_tests.family.eq('Figure2_EG_12')])
    pd.testing.assert_frame_equal(combined_obs.loc[~all_obs.family.eq('Figure2_EG_12')],all_obs.loc[~all_obs.family.eq('Figure2_EG_12')])
    return tests,observations,combined_tests,combined_obs

def main():
    config_path=source(REPO/'configs/figure_02.yaml');cfg=yaml.safe_load(config_path.read_text())
    mapping=cfg['panel_e']['evaluation']['harmonization_map'];assert mapping['Paneth']=='Goblet'
    (OUT/'publication_scoring_policy.json').write_text(json.dumps({'map':mapping,'excluded_label':'Noise','classes':20,'n_cells':209587,'tie_rule':'alphabetical','regional_mapping':'per region','celltype_mapping':'global'},indent=2)+'\n')
    original_path=source(DATA/'reference_plot_cells.csv.gz')
    original=pd.read_csv(original_path,dtype={k:str for k in KEYS+list(METHODS)})
    assert len(original)==220082 and list(original.columns)==BASE_COLUMNS and not original.duplicated(KEYS).any()
    assert original.cell_type_update.eq('Noise').sum()==10495
    baseline=publication_metrics(original,mapping)[0]
    frozen_baseline=pd.read_csv(source(DATA/'figure2_regional_metrics.csv'))
    check=baseline.merge(frozen_baseline,on=['method','region'],validate='one_to_one',suffixes=('_new','_old'))
    np.testing.assert_allclose(check[['weighted_f1_new','cluster_purity_new']],check[['weighted_f1_old','cluster_purity_old']],atol=1e-12,rtol=0)
    save(baseline,'baseline_regional_metrics.csv')
    completion=json.loads(source(SPAT_RECEIPT).read_text());assert completion['verified']
    flow_manifest=json.loads(source(FLOW/'manifest.json').read_text())
    frame=original.copy();import_receipts={}
    source_specs={'flowsom':(FLOW/'assignments.csv.gz','flowsom_cluster',flow_manifest['files']['assignments.csv.gz'],299),
        'spatialsort':(SPAT/'spatialsort_seed42_sweep100.csv.gz','spatialsort_cluster',completion['completion_outputs']['chains']['42']['assignment_sha256'],229)}
    for method,(path,column,expected,nclusters) in source_specs.items():
        source(path);assert sha(path)==expected
        assignments=pd.read_csv(path,dtype={k:str for k in KEYS+[column]})
        assert len(assignments)==220082 and not assignments.duplicated(KEYS).any()
        joined=frame.drop(columns=method).merge(assignments[KEYS+[column]],on=KEYS,how='outer',validate='one_to_one',sort=False,indicator=True)
        assert joined._merge.eq('both').all() and len(joined)==220082
        joined=joined.drop(columns='_merge').rename(columns={column:method})
        # Restore canonical order explicitly rather than assuming an outer join's order.
        joined=frame[KEYS].merge(joined,on=KEYS,how='left',validate='one_to_one',sort=False)
        assert joined[KEYS].equals(frame[KEYS]) and joined[method].notna().all() and joined[method].nunique()==nclusters
        frame=joined[BASE_COLUMNS]
        import_receipts[method]={'path':str(path),'sha256':expected,'assignment_column':column,'rows':220082,'occupied_clusters':nclusters,'exact_keys':True}
    assert frame[KEYS+['x','y','cell_type_update','leiden','pixie']].equals(original[KEYS+['x','y','cell_type_update','leiden','pixie']])
    save(frame,'reference_plot_cells.csv.gz')
    regional,celltype,gm,rm,pooled,ties=publication_metrics(frame,mapping)
    for name,value in [('regional_metrics.csv',regional),('celltype_metrics.csv',celltype),('global_majority_maps.csv',gm),('regional_majority_maps.csv',rm),('publication_pooled_metrics.csv',pooled),('majority_ties.csv',ties)]:save(value,name)
    for letter,field in [('F','f1'),('H','recall')]:
        template=pd.read_csv(source(REPLAY/f'figure_02/panel_{letter}_values.csv'))
        table=celltype.pivot(index='cell_type',columns='method',values=field).reindex(index=template.iloc[:,0],columns=template.columns[1:]).reset_index()
        save(table,f'panel_{letter}_values.csv')
    comp,clusters,types,raw=raw_metrics(frame)
    for name,value in [('figureS4_compositions.csv.gz',comp),('figureS4_cluster_metrics.csv',clusters),('figureS4_celltype_metrics.csv',types),('fixed_raw_metrics.csv',raw)]:save(value,name)
    # Retained methods' raw diagnostics also match the archived active values.
    oldraw=pd.read_csv(source(DATA/'figureS5_fixed_metrics.csv'))
    rawcheck=raw.loc[raw.method.isin(['leiden','pixie'])].merge(oldraw,on=['method','region','noise_policy'],validate='one_to_one',suffixes=('_new','_old'))
    for col in ['purity','ari','ami','majority_macro_f1','majority_weighted_f1']:
        np.testing.assert_allclose(rawcheck[col+'_new'],rawcheck[col+'_old'],atol=1e-10,rtol=0)
    tests,obs,alltests,allobs=conditional_tests(regional)
    for name,value in [('conditional_comparisons.csv',tests),('paired_regional_observations.csv',obs),('conditional_comparisons_all_families.csv',alltests),('paired_regional_observations_all_families.csv',allobs)]:save(value,name)
    # The other completed SpatialSort chain remains a prespecified sensitivity.
    s43_path=source(SPAT/'spatialsort_seed43_sweep100.csv.gz')
    assert sha(s43_path)==completion['completion_outputs']['chains']['43']['assignment_sha256']
    s43=pd.read_csv(s43_path,dtype={k:str for k in KEYS+['spatialsort_cluster']})
    assert len(s43)==220082 and not s43.duplicated(KEYS).any()
    sensitivity=frame.drop(columns='spatialsort').merge(s43,on=KEYS,how='left',validate='one_to_one',sort=False).rename(columns={'spatialsort_cluster':'spatialsort'})
    assert sensitivity[KEYS].equals(frame[KEYS]) and sensitivity.spatialsort.nunique()==231
    sr,sc,sg,srm,sp,st=publication_metrics(sensitivity,mapping)
    save(sr.loc[sr.method_key.eq('spatialsort')],'spatialsort_seed43_regional_metrics.csv')
    save(sc.loc[sc.method.eq('SpatialSort')],'spatialsort_seed43_celltype_metrics.csv')
    save(sp.loc[sp.method_key.eq('spatialsort')],'spatialsort_seed43_publication_pooled_metrics.csv')
    _,_,_,sraw=raw_metrics(sensitivity,method_keys=['spatialsort']);save(sraw,'spatialsort_seed43_fixed_raw_metrics.csv')
    partition=[]
    for region in ['ALL',*sorted(frame.File_ID.unique())]:
        keep=np.ones(len(frame),dtype=bool) if region=='ALL' else frame.File_ID.eq(region).to_numpy()
        a,b=frame.loc[keep,'spatialsort'],sensitivity.loc[keep,'spatialsort']
        ari=float(adjusted_rand_score(a,b));assert abs(ari-independent_ari(a,b))<1e-13
        partition.append({'region':region,'n_cells':int(keep.sum()),'primary_seed':42,'sensitivity_seed':43,'partition_ari':ari})
    save(pd.DataFrame(partition),'spatialsort_seed_sensitivity.csv')
    hist_map=json.loads(source(HIST).read_text())['mapping'];assert hist_map['Paneth']=='Neuroendocrine'
    policy_rows=[]
    for method in METHODS:
        for policy,used,truth in [('publication20_nonNoise',frame.loc[frame.cell_type_update.ne('Noise')],None),('historical21_includingNoise',frame,None),('raw28_includingNoise',frame,None)]:
            truth=used.cell_type_update.replace(mapping if policy.startswith('publication') else hist_map) if not policy.startswith('raw28') else used.cell_type_update
            policy_rows.append({'method':method,'label_policy':policy,**subset_metrics(truth,used[method])})
    save(pd.DataFrame(policy_rows),'scoring_policy_comparison.csv')
    summary=regional.groupby(['method','method_key'],sort=False)[['weighted_f1','cluster_purity']].agg(['mean','min','max'])
    summary.columns=['_'.join(x) for x in summary.columns];summary=summary.reset_index();save(summary,'publication_regional_summary.csv')
    baseline_summary=baseline.groupby('method')[['weighted_f1','cluster_purity']].mean()
    changes=summary[['method','weighted_f1_mean','cluster_purity_mean']].merge(baseline_summary,on='method',validate='one_to_one')
    changes['weighted_f1_delta_pp']=100*(changes.weighted_f1_mean-changes.weighted_f1)
    changes['cluster_purity_delta_pp']=100*(changes.cluster_purity_mean-changes.cluster_purity)
    save(changes,'publication_baseline_changes.csv')
    receipt={'status':'complete','created_utc':datetime.now(timezone.utc).isoformat(),'repo_base':'aa632f695a97f48b72ee6c048464881872488870',
        'input_rows':220082,'evaluation_rows':209587,'excluded_reference_noise':10495,'regions':8,'donors':1,'publication_classes':20,
        'publication_mapping':mapping,'majority_tie_break':'alphabetical','regional_mapping':'within each region','celltype_mapping':'globally over all eight regions',
        'updated_methods':import_receipts,'unchanged_methods':['leiden','pixie'],'all_unchanged_columns_preserved':True,
        'baseline_regional_values_reproduced':True,'unchanged_method_raw_values_reproduced':True,
        'independent_checks':['weightedF1 versus independent confusion counts','purity versus dictionary majorities','ARI versus integer pair counts','exact sign flip versus independent enumeration and scipy paired-samples exact permutation'],
        'conditional_tests':len(tests),'paired_region_rows':len(obs),'holm_family':'Figure2_EG_12','holm_below_0_05':int(tests.holm_below_0_05.sum()),
        'other_test_rows_preserved':len(alltests)-len(tests),'other_paired_rows_preserved':len(allobs)-len(obs),
        'cluster_counts':{k:int(frame[k].nunique()) for k in METHODS},'primary_spatialsort_seed':42,'spatialsort_sensitivity_seed':43,
        'spatialsort_sensitivity_clusters':231,'spatialsort_seed_partition_ari':partition[0]['partition_ari'],
        'regional_summary':summary.to_dict(orient='records'),'pooled_metrics':pooled.to_dict(orient='records'),
        'publication_baseline_changes':changes.to_dict(orient='records'),
        'new_fits':0,'new_annotations':0,'Ward_sweep':False,'shared_archived_UMAP':'unchanged, to be used by figure integrator',
        'versions':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'scikit-learn':sklearn.__version__},
        'source_hashes':SOURCE_HASHES,'source_policy_difference':'Do not substitute historical21/Noise or raw28 metrics into publication20/nonNoise panels. Paneth mapping also differs.',
        'limits':['Descriptive single-donor reference-informed diagnostics.','Regional sign-exchangeability is unestablished.','No annotation inference or convergence claim.'],
        'outputs':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p.name not in ['metrics_receipt.json','run.log']}}
    (OUT/'metrics_receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(summary.to_string(index=False),flush=True)
    print(json.dumps({'status':'complete','cluster_counts':receipt['cluster_counts'],'holm_below_0_05':receipt['holm_below_0_05'],'seed_ARI':partition[0]['partition_ari']},indent=2),flush=True)

if __name__=='__main__':main()
