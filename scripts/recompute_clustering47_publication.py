#!/usr/bin/env python3
"""Recompute the frozen November 8 clustering publication tables, offline.

Usage: python scripts/recompute_clustering47_publication.py --output-dir PATH
Inputs are repository-pinned. Outputs must go to a new, empty directory.
No clustering fit, annotation call, embedding fit or publication is performed.
The 20-class publication map and historical 21-label diagnostic map stay separate.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, gzip, hashlib, itertools, json, os, platform, sys

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

REPO=Path(__file__).resolve().parents[1]
OUT=None
DATA=REPO/'data/frozen/publication_design'
REPLAY=REPO/'data/frozen/manuscript_replay'
CONFIG='configs/clustering47_publication.json'
KEYS=['File_ID','ID']
METHODS={'leiden':'Leiden','flowsom':'FlowSOM','spatialsort':'SpatialSort','pixie':'PIXIE'}
BASE_COLUMNS=['File_ID','ID','x','y','cell_type_update','leiden','flowsom','spatialsort','pixie']
SOURCE_HASHES={}
GENERATED_OUTPUTS=set()
# These retained baseline/config files are not members of the new primary manifest.
# Their hashes are the original generator's verified source hashes.
AUXILIARY_INPUT_SHA256={'configs/figure_02.yaml': 'a052df01c012f01707e6d43ee38919b1e486b2e1eefacafd90dd22fb25bb30bc', 'data/frozen/publication_design/reference_plot_cells.csv.gz': 'f47805fdce441c199cb3cef25bfc0b8a51fa6f0c39ea61ddff196fc2d0a2b66a', 'data/frozen/publication_design/figure2_regional_metrics.csv': 'cacde7e3d53b5227ecb7178517231060acacf92d6d8cafdec1fdf1b4a8b46168', 'data/frozen/manuscript_replay/figure_02/panel_F_values.csv': '2ef0920234a3bfc0c9ffef3e5741d34a14fbb96661e2c7ef1720f2d0ec239476', 'data/frozen/manuscript_replay/figure_02/panel_H_values.csv': '50f090dfadd242f2cd0c7ffe95cad48370c2576138b06e01ac4121ccfbeec5b8', 'data/frozen/publication_design/figureS5_fixed_metrics.csv': '33be582395354543969e9d1f26a0d2742ca02a9a63dc76a8076f54cef9e8e9ef', 'data/frozen/manuscript_replay/tables/companions/conditional_comparisons.csv': 'aeed35a2da36ab65eddfd3a6ccbf5c9033d3be942d91a8ce7a91e22f39130e1c', 'data/frozen/manuscript_replay/tables/companions/paired_regional_observations.csv': '2ebc29a41d56c769afdfa3915ddfae0b0269f7795539958b7a14c9cf786f1200'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_path(relative,root=REPO):
    """Resolve a contract path without allowing absolute paths or traversal."""
    root=Path(root).resolve()
    if Path(relative).is_absolute():
        raise ValueError(f'Input path must be repository-relative: {relative}')
    path=(root/relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Input path escapes the repository: {relative}')
    return path


def check_hash(relative,expected,root=REPO):
    path=repo_path(relative,root)
    if sha(path)!=expected:
        raise ValueError(f'Input checksum differs: {relative}')
    return path


def load_pinned_inputs(root=REPO):
    """Verify the binding, every manifest member and all retained baselines."""
    root=Path(root).resolve()
    config_path=repo_path(CONFIG,root)
    config=json.loads(config_path.read_text())
    if config.get('schema')!='clustering.publication.bindings.v1' or config.get('annotation_execution_disabled') is not True:
        raise ValueError('Unsupported or execution-enabled publication binding')
    manifest_path=check_hash(config['manifest'],config['manifest_sha256'],root)
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('schema')!='clustering.publication.primary47.v1':
        raise ValueError('Unsupported publication manifest')
    if (manifest.get('primary_spatialsort_seed'),manifest.get('spatialsort_sensitivity_seed'))!=(42,43):
        raise ValueError('Frozen SpatialSort primary/sensitivity seeds changed')
    if manifest['cohort']['cells']!=220082 or manifest['cohort']['key_columns']!=KEYS:
        raise ValueError('Frozen cell population or join keys changed')
    hashes={CONFIG:sha(config_path),config['manifest']:config['manifest_sha256']}
    for relative,entry in manifest['files'].items():
        path=check_hash(relative,entry['sha256'],root)
        if path.stat().st_size!=entry['bytes']:
            raise ValueError(f'Input byte count differs: {relative}')
        hashes[relative]=entry['sha256']
    for relative,expected in AUXILIARY_INPUT_SHA256.items():
        check_hash(relative,expected,root)
        hashes[relative]=expected
    for spec in [*manifest['methods'].values(),*manifest['sensitivity'].values()]:
        if spec['path'] not in hashes or spec.get('gzip_sha256',hashes[spec['path']])!=hashes[spec['path']]:
            raise ValueError('Assignment specification does not match the file manifest')
    markers=json.loads(repo_path(manifest['marker_order_path'],root).read_text())
    if len(markers)!=47 or len(set(markers))!=47:
        raise ValueError('Expected exactly 47 distinct frozen protein markers')
    return config,manifest,hashes


def prepare_output_directory(output,root=REPO):
    """Refuse frozen/source locations and existing nonempty output directories."""
    root=Path(root).resolve();output=Path(output).expanduser().resolve()
    if root.is_relative_to(output):
        raise ValueError('Output cannot be the repository or an ancestor')
    for name in ['data','configs','scripts','src','tests','docs','figures','notebooks']:
        if output.is_relative_to(root/name):
            raise ValueError('Output must be outside frozen inputs and repository source directories')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Output directory must be new or empty')
    output.mkdir(parents=True,exist_ok=True)
    return output


def source(path):
    relative=str(path.resolve().relative_to(REPO))
    if relative not in VERIFIED_INPUTS:
        raise ValueError(f'Unpinned source dependency: {relative}')
    check_hash(relative,VERIFIED_INPUTS[relative])
    SOURCE_HASHES[relative]=VERIFIED_INPUTS[relative]
    return path


def write_json(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    GENERATED_OUTPUTS.add(name)


def save(frame,name):
    path=OUT/name
    if path.suffix=='.gz':
        with path.open('wb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as stream:
                stream.write(frame.to_csv(index=False).encode())
    else:
        frame.to_csv(path,index=False)
    GENERATED_OUTPUTS.add(name)


def join_assignments(frame,method,assignments,column,expected_rows,expected_clusters):
    if len(assignments)!=expected_rows or assignments.duplicated(KEYS).any():
        raise ValueError(f'{method}: incorrect row count or duplicate cell keys')
    joined=frame.drop(columns=method).merge(assignments[KEYS+[column]],on=KEYS,how='outer',validate='one_to_one',sort=False,indicator=True)
    if not joined._merge.eq('both').all() or len(joined)!=expected_rows:
        raise ValueError(f'{method}: cell-key sets differ')
    joined=joined.drop(columns='_merge').rename(columns={column:method})
    joined=frame[KEYS].merge(joined,on=KEYS,how='left',validate='one_to_one',sort=False)
    if not joined[KEYS].equals(frame[KEYS]) or joined[method].isna().any() or joined[method].nunique()!=expected_clusters:
        raise ValueError(f'{method}: order, missing assignments or occupied cluster count differs')
    return joined[BASE_COLUMNS]


def compare_published_outputs(manifest,primary):
    """Validate all generated tables also present in the publication contract."""
    checks=[]
    for name in sorted(GENERATED_OUTPUTS):
        expected=primary/name
        relative=str(expected.relative_to(REPO))
        if relative not in manifest['files']:
            continue
        if name.endswith('.csv') or name.endswith('.csv.gz'):
            pd.testing.assert_frame_equal(pd.read_csv(OUT/name),pd.read_csv(expected),
                check_dtype=False,check_exact=False,rtol=0,atol=2e-12)
        elif name.endswith('.json'):
            if json.loads((OUT/name).read_text())!=json.loads(expected.read_text()):
                raise ValueError(f'Published JSON differs: {name}')
        checks.append({'file':name,'values_match':True,'byte_identical':sha(OUT/name)==sha(expected)})
    if len(checks)<25:
        raise ValueError('Expected at least 25 independently regenerated publication outputs')
    return checks


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

def main(config,manifest):
    primary=repo_path(config['manifest']).parent
    config_path=source(REPO/'configs/figure_02.yaml');cfg=yaml.safe_load(config_path.read_text())
    mapping=cfg['panel_e']['evaluation']['harmonization_map'];assert mapping['Paneth']=='Goblet'
    write_json('publication_scoring_policy.json',{'map':mapping,'excluded_label':'Noise','classes':20,'n_cells':209587,'tie_rule':'alphabetical','regional_mapping':'per region','celltype_mapping':'global'})
    original_path=source(DATA/'reference_plot_cells.csv.gz')
    original=pd.read_csv(original_path,dtype={k:str for k in KEYS+list(METHODS)})
    assert len(original)==220082 and list(original.columns)==BASE_COLUMNS and not original.duplicated(KEYS).any()
    assert original.cell_type_update.eq('Noise').sum()==10495
    baseline=publication_metrics(original,mapping)[0]
    frozen_baseline=pd.read_csv(source(DATA/'figure2_regional_metrics.csv'))
    check=baseline.merge(frozen_baseline,on=['method','region'],validate='one_to_one',suffixes=('_new','_old'))
    np.testing.assert_allclose(check[['weighted_f1_new','cluster_purity_new']],check[['weighted_f1_old','cluster_purity_old']],atol=1e-12,rtol=0)
    save(baseline,'baseline_regional_metrics.csv')
    completion=json.loads(source(primary/'spatialsort_completion_receipt.json').read_text());assert completion['verified']
    flow_manifest=json.loads(source(primary/'flowsom_manifest.json').read_text())
    frame=original.copy();import_receipts={}
    for method,spec in manifest['methods'].items():
        path=source(repo_path(spec['path']));column=spec['assignment_column']
        expected=manifest['files'][spec['path']]['sha256'];nclusters=spec['observed_clusters']
        if method=='flowsom':
            assert expected==flow_manifest['files']['assignments.csv.gz']
        if method=='spatialsort':
            assert expected==completion['completion_outputs']['chains']['42']['assignment_sha256']
        assignments=pd.read_csv(path,dtype={k:str for k in KEYS+[column]})
        frame=join_assignments(frame,method,assignments,column,220082,nclusters)
        if method in ['flowsom','spatialsort']:
            import_receipts[method]={'path':spec['path'],'sha256':expected,'assignment_column':column,'rows':220082,'occupied_clusters':nclusters,'exact_keys':True}
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
    s43_spec=manifest['sensitivity']['spatialsort_seed43']
    s43_path=source(repo_path(s43_spec['path']))
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
    hist_map=cfg['four_llm_consensus']['truth_normalization_map'];assert len(hist_map)==15 and hist_map['Paneth']=='Neuroendocrine'
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
    published_checks=compare_published_outputs(manifest,primary)
    receipt={'schema':'clustering.publication.recomputation.v1','status':'complete','created_utc':datetime.now(timezone.utc).isoformat(),'repo_base':'aa632f695a97f48b72ee6c048464881872488870',
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
        'source_hashes':SOURCE_HASHES,'verified_input_files':len(VERIFIED_INPUTS),'verified_manifest_sha256':config['manifest_sha256'],'script_sha256':sha(Path(__file__).resolve()),'output_directory':str(OUT),'published_output_checks':published_checks,'source_policy_difference':'Do not substitute historical21/Noise or raw28 metrics into publication20/nonNoise panels. Paneth mapping also differs.',
        'limits':['Descriptive single-donor reference-informed diagnostics.','Regional sign-exchangeability is unestablished.','No annotation inference or convergence claim.'],
        'outputs':{name:{'sha256':sha(OUT/name),'bytes':(OUT/name).stat().st_size} for name in sorted(GENERATED_OUTPUTS)}}
    write_json('metrics_receipt.json',receipt)
    print(summary.to_string(index=False),flush=True)
    print(json.dumps({'status':'complete','cluster_counts':receipt['cluster_counts'],'holm_below_0_05':receipt['holm_below_0_05'],'seed_ARI':partition[0]['partition_ari']},indent=2),flush=True)

def cli():
    global OUT,VERIFIED_INPUTS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path,help='New or empty directory outside frozen inputs and repository source directories')
    parser.add_argument('--verify-inputs-only',action='store_true',help='Verify hashes and policies without recomputing tables')
    args=parser.parse_args()
    if sys.flags.optimize:
        parser.error('Do not use Python -O: this scientific replay retains invariant assertions')
    config,manifest,VERIFIED_INPUTS=load_pinned_inputs()
    OUT=prepare_output_directory(args.output_dir)
    if args.verify_inputs_only:
        write_json('input_verification_receipt.json',{'schema':'clustering.publication.input_verification.v1','status':'verified','created_utc':datetime.now(timezone.utc).isoformat(),'verified_input_files':len(VERIFIED_INPUTS),'source_hashes':VERIFIED_INPUTS,'manifest_sha256':config['manifest_sha256'],'new_fits':0,'new_annotations':0,'tables_recomputed':False})
        print(json.dumps({'status':'verified','verified_input_files':len(VERIFIED_INPUTS),'tables_recomputed':False}))
    else:
        main(config,manifest)


if __name__=='__main__':
    cli()
