"""Portable offline donor scoring. No fitting, network, credentials or inference.

Usage: python score_core.py --bundle public_bundle --output results [--offline-only]
All scientific paths are relative to the hash-bound public bundle.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import shutil
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score,normalized_mutual_info_score

METHODS=('leiden','flowsom','spatialsort','pixie_tiff')
FAMILIES=('openai','anthropic','google','deepseek')
EVALUATIONS=('native28_all','native28_eligible23','shared23')
KEYS=['File_ID','ID']

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(8*1024*1024),b''):h.update(part)
    return h.hexdigest()
def write_json(path,value):Path(path).write_bytes(canonical(value)+b'\n')
def key_frame(path):
    frame=pd.read_csv(path,dtype={'File_ID':str,'ID':str},keep_default_na=False)
    if any(k not in frame for k in KEYS):raise ValueError('Missing cell keys')
    ids=pd.to_numeric(frame.ID,errors='raise').to_numpy()
    if not np.isfinite(ids).all() or not (ids==np.floor(ids)).all():raise ValueError('Noninteger cell ID')
    frame.ID=ids.astype(np.int64).astype(str)
    if frame[KEYS].duplicated().any() or (frame.File_ID=='').any():raise ValueError('Duplicate/empty cell keys')
    return frame
def joined(reference,path,column):
    frame=key_frame(path)
    if len(frame)!=len(reference) or column not in frame:raise ValueError('Membership population/column mismatch')
    result=reference[KEYS].merge(frame[KEYS+[column]],on=KEYS,how='left',validate='one_to_one',sort=False)
    if result[column].isna().any() or (result[column].astype(str)=='').any():raise ValueError('Incorrect/foreign cell join')
    return result[column].astype(str).to_numpy()
def classifier_predict(directory,method,arm,classifier,query):
    if not np.isfinite(query).all():raise ValueError('Nonfinite classifier query')
    file=f'{arm}_centroids.npz' if classifier=='nearest_centroid' else f'{method}_{arm}_logistic.npz'
    with np.load(directory/file,allow_pickle=False) as z:
        classes=z['classes']
        if classifier=='nearest_centroid':
            distances=((query[:,None,:]-z['centroids'][None,:,:])**2).sum(2)
            return classes[np.argmin(distances,axis=1)]
        logits=query@z['coefficient'].T+z['intercept']
        return classes[(logits[:,0]>0).astype(int)] if len(classes)==2 else classes[np.argmax(logits,axis=1)]

def prediction_codes(values):
    # CSV can represent an internally validated integer column with blanks as
    # integral decimals. This is storage decoding, never model-output repair.
    numeric=pd.to_numeric(pd.Series(values).replace('',np.nan),errors='raise').to_numpy(dtype=float)
    if np.isinf(numeric).any():raise ValueError('Infinite stored prediction')
    present=np.isfinite(numeric)
    if np.any(present&((numeric!=np.floor(numeric))|(numeric<0)|(numeric>=28))):raise ValueError('Noninteger/out-of-range stored prediction')
    return np.where(present,numeric,-1).astype(int)

def classification_metrics(truth,prediction,nlabels,delivered):
    truth=np.asarray(truth,dtype=int);prediction=np.asarray(prediction,dtype=int);delivered=np.asarray(delivered,dtype=bool)
    if not len(truth) or len(truth)!=len(prediction) or len(delivered)!=len(truth):raise ValueError('Invalid planned denominator')
    if np.any((truth<0)|(truth>=nlabels)) or np.any((prediction<-1)|(prediction>=nlabels)):raise ValueError('Invalid vocabulary')
    counts=np.bincount(truth*(nlabels+1)+(prediction+1),minlength=nlabels*(nlabels+1)).reshape(nlabels,nlabels+1)
    support=counts.sum(1);pred_support=counts[:,1:].sum(0);tp=np.diag(counts[:,1:])
    denom=support+pred_support;f1=np.divide(2*tp,denom,out=np.zeros(nlabels,float),where=denom!=0)
    correct=int(tp.sum());n=len(truth)
    return {'n_cells':n,'delivered_cells':int(delivered.sum()),'correct_cells':correct,
        'agreement':correct/n,'macro_f1':float(f1.mean()),'cell_delivery_coverage':float(delivered.mean()),
        'in_vocabulary_prediction_coverage':float((prediction>=0).mean()),
        'agreement_upper_bound_if_missing_correct':float((correct+(~delivered).sum())/n)},counts

def partition_metrics(truth,clusters):
    truth=np.asarray(truth,dtype=int);codes,unique=pd.factorize(clusters,sort=True)
    counts=np.bincount(codes*28+truth,minlength=len(unique)*28).reshape(len(unique),28)
    return {'n_cells':len(truth),'occupied_clusters':len(unique),'majority_cells':int(counts.max(1).sum()),
        'purity':float(counts.max(1).sum()/len(truth)),
        'ari':float(adjusted_rand_score(truth,codes)),
        'nmi':float(normalized_mutual_info_score(truth,codes,average_method='arithmetic'))}

def load_scientific(bundle):
    protocol=json.loads((bundle/'protocol.json').read_text());manifest=json.loads((bundle/'manifest.json').read_text())
    for name,record in manifest['files'].items():
        p=(bundle/name).resolve()
        if not p.is_relative_to(bundle.resolve()) or sha(p)!=record['sha256']:raise ValueError('Bundle file changed')
    ontology=protocol['ontology'];projection=protocol['projection23'];shared=protocol['shared23_ontology']
    if len(ontology)!=28 or ontology[21]!='Noise' or len(shared)!=23:raise ValueError('Wrong frozen ontologies')
    projection_codes=np.array([shared.index(projection[x]) if projection[x] in shared else -1 for x in ontology],int)
    donors={}
    for donor,spec in protocol['donors'].items():
        ref=key_frame(bundle/spec['reference'])
        if len(ref)!=spec['n_cells'] or ref.File_ID.nunique()!=8:raise ValueError('Wrong donor denominator/regions')
        truth=pd.to_numeric(ref.reference_label_code,errors='raise').to_numpy(dtype=int)
        if not np.array_equal(np.asarray(ontology)[truth],ref.reference_label.to_numpy()):raise ValueError('Reference names/code order mismatch')
        ref['truth']=truth;ref['shared23']=projection_codes[truth];ref['eligible23']=ref.shared23>=0
        memberships={};profiles={}
        for method,entry in spec['methods'].items():
            memberships[method]=joined(ref,bundle/entry['membership'],entry['column'])
            with np.load(bundle/entry['profiles'],allow_pickle=False) as z:profile={k:z[k].copy() for k in z.files}
            names=profile['cluster_names'].astype(str);counts=pd.Series(memberships[method]).value_counts().sort_index()
            if names.tolist()!=sorted(names.tolist()) or names.tolist()!=counts.index.tolist():raise ValueError('Occupied cluster order differs')
            if not np.array_equal(profile['cell_counts'],counts.to_numpy()) or int(profile['cell_counts'].sum())!=len(ref):raise ValueError('Profile cell counts differ')
            if profile['marker_order'].tolist()!=protocol['markers'] or len(protocol['markers'])!=47:raise ValueError('Marker order differs')
            for key in ['means_asinh','means_z','fractions']:
                if profile[key].dtype!=np.float64 or not np.isfinite(profile[key]).all():raise ValueError('Original float64 evidence required')
            if not np.array_equal(np.rint(profile['means_z']*1000).astype(np.int64),profile['means_z_thousandths']):raise ValueError('Mean encoding differs')
            if not np.array_equal(np.rint(profile['fractions']*1000).astype(np.int64),profile['fractions_thousandths']):raise ValueError('Fraction encoding differs')
            profiles[method]=profile
        donors[donor]={'reference':ref,'memberships':memberships,'profiles':profiles}
    return protocol,manifest,donors,projection_codes

def evaluation_view(truth,pred,projection,evaluation):
    eligible=projection[truth]>=0
    if evaluation=='native28_all':return np.ones(len(truth),bool),truth,pred,28
    if evaluation=='native28_eligible23':return eligible,truth[eligible],pred[eligible],28
    projected=np.full(len(pred),-1,int);valid=pred>=0;projected[valid]=projection[pred[valid]]
    return eligible,projection[truth[eligible]],projected[eligible],23

def summarize(rows,groups):
    frame=pd.DataFrame(rows);result=[]
    if frame.empty:return result
    for values,part in frame.groupby(groups,sort=True,dropna=False):
        values=values if isinstance(values,tuple) else (values,)
        row=dict(zip(groups,values));row.update(aggregation='equal_region',n_regions=len(part),n_cells=int(part.n_cells.sum()))
        for name in ['agreement','macro_f1','cell_delivery_coverage','cluster_delivery_coverage','in_vocabulary_prediction_coverage','agreement_upper_bound_if_missing_correct']:
            if name in part:row[name]=float(part[name].mean())
        result.append(row)
    return result

def score(bundle,output,offline_only=False,provisional=False,include_archive=False):
    bundle=Path(bundle).resolve();output=Path(output);output.mkdir(parents=True,exist_ok=False)
    protocol,manifest,donors,projection=load_scientific(bundle)
    region_rows=[];pooled_rows=[];clustering=[];clustering_pool=[];baseline_rows=[];baseline_pool=[];baseline_predictions=[];seed_rows=[];coarse=[];confusions={}
    annotations=None
    if not offline_only:
        if not protocol['annotation_requests_terminal'] and not provisional:raise ValueError('Cannot publish annotation scores from active requests')
        annotations=pd.read_csv(bundle/'prediction_grid.csv',dtype={'cluster_id':str,'request_id':str},keep_default_na=False)
        if len(annotations)!=9468 or annotations.duplicated(['donor','method','family','cluster_id']).any():raise ValueError('Prediction grid differs')
        registry=json.loads((bundle/'request_registry.json').read_text())
        if ({r['arm'] for r in registry}!={'all_means_fractions'} or {r['repeat'] for r in registry}!={0}
                or len(registry)!=128 or len({(r['donor'],r['method'],r['family']) for r in registry})!=32):
            raise ValueError('Only32 one-repetition MF donor sets are authorized')
    for donor,data in donors.items():
        ref=data['reference'];truth=ref.truth.to_numpy();regions=ref.File_ID.to_numpy();region_names=sorted(ref.File_ID.unique())
        for method in METHODS:
            cluster=data['memberships'][method];profile=data['profiles'][method];names=profile['cluster_names'].astype(str)
            name_index={x:i for i,x in enumerate(names)};cell_indices=np.array([name_index[x] for x in cluster],int)
            for evaluation in EVALUATIONS:
                mask,y,_,_=evaluation_view(truth,np.full(len(truth),-1),projection,evaluation)
                for region in region_names:
                    take=regions[mask]==region
                    metrics=partition_metrics(y[take],cluster[mask][take])
                    clustering.append({'donor':donor,'method':method,'evaluation':evaluation,'File_ID':region,**metrics})
                clustering_pool.append({'donor':donor,'method':method,'evaluation':evaluation,'aggregation':'pooled_descriptive',**partition_metrics(y,cluster[mask])})
            queries={'all_means':profile['means_z_thousandths']/1000.,'all_means_fractions':np.column_stack([profile['means_z_thousandths']/1000.,profile['fractions_thousandths']/1000.])}
            conditions=[]
            for arm,query in queries.items():
                for classifier in ('nearest_centroid','logistic_regression'):
                    pred=classifier_predict(bundle/'baselines',method,arm,classifier,query).astype(int)
                    baseline_predictions.extend({'donor':donor,'method':method,'arm':arm,'classifier':classifier,'cluster_id':name,'label_code':int(label)} for name,label in zip(names,pred))
                    conditions.append(('baseline',classifier,arm,pred,np.ones(len(pred),bool)))
            if annotations is not None:
                for family in FAMILIES:
                    part=annotations[(annotations.donor==donor)&(annotations.method==method)&(annotations.family==family)].set_index('cluster_id')
                    if set(part.index)!=set(names):raise ValueError('Model cluster coverage differs')
                    part=part.reindex(names);pred=prediction_codes(part.label_code)
                    delivered=part.delivered.to_numpy(dtype=int)==1
                    if not np.array_equal(delivered,pred>=0):raise ValueError('Missing output cannot become Noise')
                    conditions.append(('annotation',family,'all_means_fractions',pred,delivered))
            for kind,family,arm,pred_cluster,delivered_cluster in conditions:
                pred=pred_cluster[cell_indices];delivered=delivered_cluster[cell_indices]
                for evaluation in EVALUATIONS:
                    mask,y,p,nlabels=evaluation_view(truth,pred,projection,evaluation);delivery=delivered[mask]
                    identity={'donor':donor,'method':method,'evaluation':evaluation}
                    identity.update({'family':family} if kind=='annotation' else {'classifier':family,'arm':arm})
                    pooled,counts=classification_metrics(y,p,nlabels,delivery)
                    pooled.update(identity,aggregation='pooled_descriptive',cluster_delivery_coverage=float(delivered_cluster.mean()))
                    (pooled_rows if kind=='annotation' else baseline_pool).append(pooled)
                    if kind=='annotation':confusions['__'.join([donor,method,family,evaluation])]=counts
                    for region in region_names:
                        take=regions[mask]==region;metrics,_=classification_metrics(y[take],p[take],nlabels,delivery[take])
                        present=np.unique(cell_indices[mask][take])
                        metrics.update(identity,File_ID=region,cluster_delivery_coverage=float(delivered_cluster[present].mean()))
                        (region_rows if kind=='annotation' else baseline_rows).append(metrics)
            seed_spec=protocol['donors'][donor].get('spatialsort_seed43')
            if method=='spatialsort' and seed_spec:
                seed43=joined(ref,bundle/seed_spec['membership'],seed_spec['column'])
                for evaluation in EVALUATIONS:
                    mask,y,_,_=evaluation_view(truth,np.full(len(truth),-1),projection,evaluation)
                    for region in [*region_names,'ALL']:
                        take=np.ones(mask.sum(),bool) if region=='ALL' else regions[mask]==region
                        a=cluster[mask][take];b=seed43[mask][take]
                        seed_rows.append({'donor':donor,'evaluation':evaluation,'File_ID':region,
                            'aggregation':'pooled_descriptive' if region=='ALL' else 'region',
                            'n_cells':int(take.sum()),'seed42_seed43_ari':float(adjusted_rand_score(a,b)),
                            'partition_ari':float(adjusted_rand_score(a,b)),
                            'seed42_clusters':int(len(np.unique(a))),'seed43_clusters':int(len(np.unique(b))),
                            'seed42_seed43_nmi':float(normalized_mutual_info_score(a,b,average_method='arithmetic')),
                            **{'seed43_'+k:v for k,v in partition_metrics(y[take],b).items() if k!='n_cells'}})
    ann_donor=summarize(region_rows,['donor','method','family','evaluation']) if region_rows else []
    base_donor=summarize(baseline_rows,['donor','method','classifier','arm','evaluation'])
    for row in ann_donor:
        part=annotations[(annotations.donor==row['donor'])&(annotations.method==row['method'])&(annotations.family==row['family'])]
        row['planned_clusters']=len(part);row['delivered_clusters']=int(part.delivered.sum())
        row['cluster_delivery_coverage']=row['delivered_clusters']/row['planned_clusters']
    baseline_equal=[]
    for values,part in pd.DataFrame(base_donor).groupby(['method','classifier','arm','evaluation'],sort=True):
        if len(part)!=2:raise ValueError('Equal-donor baseline requires both donors')
        row=dict(zip(['method','classifier','arm','evaluation'],values));row.update(aggregation='equal_donor',n_donors=2,n_cells=int(part.n_cells.sum()))
        for col in ['agreement','macro_f1','cell_delivery_coverage','cluster_delivery_coverage','in_vocabulary_prediction_coverage']:
            row[col]=float(part[col].mean())
        baseline_equal.append(row)
    equal_donor=[]
    if ann_donor:
        f=pd.DataFrame(ann_donor)
        for values,part in f.groupby(['method','family','evaluation'],sort=True):
            if len(part)!=2:raise ValueError('Equal-donor endpoint needs both donors')
            row=dict(zip(['method','family','evaluation'],values));row.update(aggregation='equal_donor',n_donors=2,n_cells=int(part.n_cells.sum()))
            for col in ['agreement','macro_f1','cell_delivery_coverage','cluster_delivery_coverage','in_vocabulary_prediction_coverage']:
                row[col]=float(part[col].mean())
            equal_donor.append(row)
        for values,part in f.groupby(['donor','method','family'],sort=True):
            row=dict(zip(['donor','method','family'],values));lookup=part.set_index('evaluation')
            for ev in EVALUATIONS:
                for col in ['n_cells','agreement','macro_f1','cell_delivery_coverage']:
                    row[ev+'__'+col]=float(lookup.loc[ev,col]) if col!='n_cells' else int(lookup.loc[ev,col])
            row['eligible23_fraction']=row['shared23__n_cells']/row['native28_all__n_cells'];coarse.append(row)
    cluster_donor=[]
    for values,part in pd.DataFrame(clustering).groupby(['donor','method','evaluation'],sort=True):
        row=dict(zip(['donor','method','evaluation'],values));row.update(aggregation='equal_region',n_regions=len(part),n_cells=int(part.n_cells.sum()))
        row['occupied_clusters']=len(donors[row['donor']]['profiles'][row['method']]['cluster_names'])
        row['n_clusters']=row['occupied_clusters']
        for col in ['purity','ari','nmi']:row[col]=float(part[col].mean())
        cluster_donor.append(row)
    tables={'clustering_region_metrics.csv':clustering,'clustering_donor_metrics.csv':cluster_donor,
        'clustering_pooled_metrics.csv':clustering_pool,'baselines_region_metrics.csv':baseline_rows,
        'baselines_donor_metrics.csv':base_donor,'baselines_pooled_metrics.csv':baseline_pool,
        'baselines_equal_donor_metrics.csv':baseline_equal,
        'baseline_cluster_predictions.csv':baseline_predictions,'spatialsort_seed_sensitivity.csv':seed_rows}
    if annotations is not None:
        tables.update({'annotation_region_metrics.csv':region_rows,'annotation_donor_metrics.csv':ann_donor,
            'annotation_equal_donor_metrics.csv':equal_donor,'annotation_pooled_metrics.csv':pooled_rows,'coarse23_comparison.csv':coarse})
        shutil.copyfile(bundle/'prediction_grid.csv',output/'prediction_grid.csv')
        np.savez_compressed(output/'confusion_matrices.npz',**confusions)
    matched=protocol.get('matched45_B005') if include_archive else None
    if include_archive and (bundle/'archive/protocol.json').is_file():
        matched=json.loads((bundle/'archive/protocol.json').read_text()).get('matched45_B005')
    if matched:
        data=donors['B005'];ref=data['reference'];truth=ref.truth.to_numpy();clusters45=joined(ref,bundle/matched['membership'],matched['column']);clusters47=data['memberships']['flowsom'];rows=[]
        for ev in EVALUATIONS:
            mask,y,_,_=evaluation_view(truth,np.full(len(truth),-1),projection,ev)
            a=partition_metrics(y,clusters47[mask]);b=partition_metrics(y,clusters45[mask])
            rows.append({'donor':'B005','method':'flowsom','evaluation':ev,'n_cells':len(y),
                **{'marker47_'+k:v for k,v in a.items() if k!='n_cells'},**{'marker45_'+k:v for k,v in b.items() if k!='n_cells'},
                'purity_47_minus45_pp':100*(a['purity']-b['purity']),'new_fits':0,'new_annotation_calls':0})
        tables['archive/matched45_sensitivity.csv']=rows
    for name,rows in tables.items():
        (output/name).parent.mkdir(parents=True,exist_ok=True)
        pd.DataFrame(rows).to_csv(output/name,index=False,float_format='%.15g')
    ready=not offline_only and protocol['annotation_requests_terminal']
    summary={'schema':'donor47.portable_scoring_results.v1','publication_ready':ready,
        'clustering_ready':True,'annotation_ready':ready,'provisional_annotation_scores':not offline_only and not ready,
        'annotation_requests_terminal':bool(protocol['annotation_requests_terminal']),'offline_only':True,'new_fits':0,'new_annotation_calls':0,
        'cells':sum(len(d['reference']) for d in donors.values()),'regions':16,'primary_labels':28,'Noise_code':21,
        'planned_sets':32,'planned_request_items':128,'planned_cluster_predictions':9468,
        'aggregation':'Equal-weighted regions within donor, then equal-weighted donors; pooled descriptive tables separate.',
        'missing_predictions':'Kept as errors in every planned denominator; never imputed as Noise.',
        'secondary23':'Reference-eligible mask only; native28 also scored on exactly that mask; predictions outside23 remain errors.',
        'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__},
        'source_bundle_manifest_sha256':sha(bundle/'manifest.json'),
        'files':{str(p.relative_to(output)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(output.rglob('*')) if p.is_file()}}
    if annotations is not None:summary.update(accepted_request_items=int(annotations.groupby('request_id').delivered.min().sum()),delivered_cluster_predictions=int(annotations.delivered.sum()))
    write_json(output/'manifest.json',summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--offline-only',action='store_true');p.add_argument('--provisional',action='store_true');p.add_argument('--include-archive',action='store_true');a=p.parse_args()
    print(json.dumps(score(a.bundle,a.output,a.offline_only,a.provisional,a.include_archive),sort_keys=True))
