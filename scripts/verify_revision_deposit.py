#!/usr/bin/env python3
"""Verify downloaded revision assets and replay frozen results without inference."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, importlib.util, itertools, json, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode=True

def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def check_files(root,manifest):
    for r in manifest['files']:
        p=root/r['path']
        assert p.is_file() and not p.is_symlink(),r['path']
        assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],r['path']
    return len(manifest['files'])

def paired(root,parser):
    import numpy as np
    import pandas as pd
    out=root/'outputs/revision_20261028/paired_means_fractions'
    protocol=read(out/'active_protocol.json')
    requests=[json.loads(x) for x in (out/'requests_active.jsonl').read_text().splitlines() if x.strip()]
    receipts=read(out/'run/receipts.json')
    replay={};generation_ids=[]
    for r in requests:
        key=(r['method'],r['model'],r['condition'],int(r['repeat']))
        if key not in replay:
            with np.load(out/f"cases/B004_{r['method']}.npz",allow_pickle=False) as a:n=len(a['cluster_names'])
            replay[key]=np.full(n,-1,int)
        entry=receipts[r['request_id']]
        attempt=entry['attempts'][-1]
        raw=read(out/attempt['raw_file'])['raw_response']
        b=protocol['model_bindings'][r['model']]
        good=raw.get('model') in [b['model_id'],b['canonical_slug']] and raw.get('provider')==b['expected_provider']
        labels=parser.decode(raw,r['n_cases'])['labels'] if good else [-1]*r['n_cases']
        replay[key][r['case_start']:r['case_stop']]=labels
        if raw.get('id'):generation_ids.append(raw['id'])
    maps=0
    for p in (out/'predictions/paired').glob('*.npz'):
        donor,method,model,arm,repeat=p.stem.split('__')
        with np.load(p,allow_pickle=False) as a:
            np.testing.assert_array_equal(a['cluster_labels'],replay[method,model,arm,int(repeat[1:])])
        maps+=1
    keys=pd.read_csv(out/'cases/B004_cell_keys.csv.gz',dtype={'File_ID':str})
    ref=pd.read_csv(root/'outputs/revision_20261021/annotation_bound/cells.csv.gz',dtype={'File_ID':str})
    ref=keys[['File_ID','ID']].merge(ref[['File_ID','ID','truth_label']],on=['File_ID','ID'],sort=False,validate='one_to_one')
    truth=ref.truth_label.map({v:i for i,v in enumerate(protocol['ontology'])}).to_numpy(int)
    regions=keys.File_ID.to_numpy()
    testregions=[r for r,s in protocol['split'].items() if s=='test']
    table=pd.read_csv(out/'paired_repeat_metrics.csv');summary=pd.read_csv(out/'paired_summary.csv')
    all_values={}
    for row in table.itertuples():
        with np.load(out/f'cases/B004_{row.method}.npz',allow_pickle=False) as a:codes=a['codes']
        values=[]
        for arm in protocol['arms']:
            pred=replay[row.method,row.model,arm,int(row.repeat)][codes]
            values.append(float(np.mean([np.mean(pred[regions==r]==truth[regions==r]) for r in testregions])))
        np.testing.assert_allclose(values+[values[1]-values[0]],[row.means_agreement,row.fractions_agreement,row.delta_agreement],rtol=0,atol=1e-12)
        all_values.setdefault((row.method,row.model),[]).append(values+[values[1]-values[0]])
    for row in summary.itertuples():
        values=np.array(all_values[row.method,row.model])
        for i,arm in enumerate(['means','fractions','delta']):
            np.testing.assert_allclose([values[:,i].mean(),values[:,i].std(ddof=1)],[getattr(row,arm+'_agreement_mean'),getattr(row,arm+'_agreement_sd')],rtol=0,atol=1e-12)
    assert len(requests)==384 and sum(r['n_cases'] for r in requests)==27504 and maps==96 and len(set(generation_ids))==384
    return {'raw_requests':len(requests),'prediction_maps':maps,'paired_repeat_rows':len(table),'method_model_summaries':len(summary)}

def calibration(root,parser):
    import numpy as np
    import pandas as pd
    out=root/'outputs/revision_20261028/uncertainty_spatial_v1'
    records=pd.read_csv(out/'calibration_cluster_records.csv')
    metrics=pd.read_csv(out/'calibration_metrics.csv')
    fits=pd.read_csv(out/'calibration_fits.csv')
    for row in metrics.itertuples():
        x=records[(records.method==row.method)&(records.model==row.model)&(records.arm==row.arm)&(records.cluster_partition=='evaluation')&(records.region_split=='test')]
        if row.region!='POOLED':x=x[x.region==row.region]
        x=x[x.modal_label>=0]
        n=x.n_cells.to_numpy();c=x.n_reference_matches.to_numpy()
        if row.probability=='development_constant':
            fit=fits[(fits.method==row.method)&(fits.model==row.model)&(fits.arm==row.arm)]
            p=np.full(len(x),fit.constant_probability.iloc[0])
        else:p=x['vote_fraction' if row.probability=='raw_vote' else 'calibrated_probability'].to_numpy()
        assert n.sum()==row.n_delivered
        brier=np.sum(c*(1-p)**2+(n-c)*p**2)/n.sum()
        bins=np.minimum((p*5).astype(int),4)
        ece=sum(abs(np.dot(p[bins==b],n[bins==b])-c[bins==b].sum()) for b in range(5))/n.sum()
        np.testing.assert_allclose([brier,ece,c.sum()/n.sum()],[row.brier,row.ece_5_bins,row.reference_agreement],rtol=0,atol=1e-12)
    requests=[json.loads(x) for x in (out/'requests.jsonl').read_text().splitlines() if x.strip()]
    for repeat in range(3):
        for start in range(0,300,75):
            arms={r['condition']:r for r in requests if r['repeat']==repeat and r['case_start']==start}
            a=json.loads(json.dumps(arms['marker_only']['payload']));b=json.loads(json.dumps(arms['marker_plus_neighborhood']['payload']))
            evidence=json.loads(b['messages'][1]['content']);assert len(evidence.pop('neighbor_profiles_z'))==75;evidence.pop('neighborhood_definition')
            a['messages'][1]['content']=json.loads(a['messages'][1]['content']);b['messages'][1]['content']=evidence
            assert a==b
    frozen=read(out/'prediction_freeze.json');ids=[];decoded={}
    binding=read(out/'model_binding.json')
    for name in frozen['raw_sha256']:
        wrapper=read(out/name);raw=wrapper['raw_response'];labels=parser.decode(raw,75)['labels']
        assert raw.get('model') in [binding['model_id'],binding['canonical_slug']] and raw.get('provider')==binding['expected_provider']
        assert len(labels)==75 and all(0<=int(x)<28 for x in labels)
        ids.append(raw['id']);assert wrapper['request_id'] not in decoded;decoded[wrapper['request_id']]=np.array(labels)
    assert len(ids)==24 and len(set(ids))==24
    with np.load(out/'predictions.npz',allow_pickle=False) as a:
        predictions={k:a[k] for k in a.files}
    for r in requests:
        key=r['condition']+'__r'+str(r['repeat'])
        np.testing.assert_array_equal(predictions[key][r['case_start']:r['case_stop']],decoded[r['request_id']])
    from sklearn.metrics import f1_score
    keys=pd.read_csv(root/'controlled_annotation/cases/B004_cell_keys.csv.gz',dtype={'File_ID':str})
    reference=pd.read_csv(root/'outputs/revision_20261021/annotation_bound/cells.csv.gz',dtype={'File_ID':str})
    joined=keys[['File_ID','ID']].merge(reference[['File_ID','ID','truth_label']],on=['File_ID','ID'],sort=False,validate='one_to_one')
    ontology=read(root/'controlled_annotation/protocol.json')['ontology']
    truth=joined.truth_label.map({v:i for i,v in enumerate(ontology)}).to_numpy(int)
    with np.load(out/'spatial_inputs.npz',allow_pickle=False) as a:codes=a['codes']
    regional=pd.read_csv(out/'spatial_regional_metrics.csv')
    for r in regional.itertuples():
        mask=keys.File_ID.eq(r.region).to_numpy();p=predictions[r.arm+'__r'+str(r.repeat)][codes[mask]];y=truth[mask]
        assert len(y)==r.n_cells and int((p==y).sum())==r.n_correct and int((p<0).sum())==r.n_missing
        np.testing.assert_allclose([np.mean(p==y),f1_score(y,p,labels=list(range(28)),average='macro',zero_division=0),np.mean(p>=0)],[r.agreement,r.macro_f1,r.coverage],rtol=0,atol=1e-12)
    return {'calibration_metric_rows':len(metrics),'paired_spatial_payloads':12,'spatial_raw_responses':24,'spatial_prediction_maps':len(predictions),'spatial_regional_metric_rows':len(regional)}

def conditional_comparisons(root):
    import numpy as np
    import pandas as pd
    out=root/'outputs/revision_20261028/hybrid_comparative_statistics_v1'
    table=pd.read_csv(out/'conditional_comparisons.csv')
    observations=pd.read_csv(out/'paired_regional_observations.csv')
    key=['family','metric','comparison','condition_a','condition_b']
    computed=[]
    for _,row in table.iterrows():
        x=observations
        for k in key:x=x[x[k]==row[k]]
        assert len(x)==8 and x.region.nunique()==8
        a=x.value_a.to_numpy();b=x.value_b.to_numpy();d=(a-b)*100
        np.testing.assert_allclose(d,x.difference_pp.to_numpy(),rtol=0,atol=1e-10)
        np.testing.assert_allclose([a.mean()*100,b.mean()*100,d.mean(),np.median(d)],[row.mean_a_percent,row.mean_b_percent,row.mean_difference_pp,row.median_difference_pp],rtol=0,atol=1e-10)
        signs=np.array(list(itertools.product([-1,1],repeat=8)))
        p=float(np.mean(np.abs((signs*d).mean(axis=1))>=abs(d.mean())-1e-12))
        np.testing.assert_allclose(p,row.raw_p,rtol=0,atol=1e-12)
        computed.append(p)
    for family,part in table.groupby('family',sort=False):
        ix=part.index.to_numpy();p=np.array(computed)[ix];order=np.argsort(p,kind='stable')
        adjusted=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
        expected=np.empty(len(p));expected[order]=adjusted
        np.testing.assert_allclose(expected,part.holm_adjusted_p.to_numpy(),rtol=0,atol=1e-12)
    assert len(table)==60 and len(observations)==480
    return {'comparisons':len(table),'paired_regional_rows':len(observations),'holm_families':table.groupby('family').size().to_dict()}

def historical_raw_responses(root):
    import csv
    import numpy as np
    import pandas as pd
    out=root/'outputs/revision_20261021/historical_annotations'
    rows=list(csv.DictReader((out/'complete_target_label_maps.csv').open()))
    details={r['call_id']:r for r in read(out/'historical_prompt_details.json')}
    grouped={}
    for r in rows:grouped.setdefault(r['source_call_id'],[]).append(r)
    parsed={};native=transformed=0
    def artifact(digest):
        assert len(digest)==64
        return read(out/'source_artifacts'/(digest+'.json'))
    for call,targets in grouped.items():
        r=targets[0];status=r['repair_status']
        if r['source_response_file_sha256']:
            saved=artifact(r['source_response_file_sha256']);raw=saved['raw_response'];native+=1
        else:
            column=next(k for k in ['source_repair_file_sha256','source_schema_normalization_file_sha256','source_ontology_alias_sidecar_file_sha256'] if r[k])
            saved=artifact(r[column]);raw=artifact(r['source_failure_file_sha256'])['response_failure_evidence']['raw_response'];transformed+=1
        content=raw['choices'][0]['message']['content'].strip()
        if status=='deterministically_repaired_trailing_unmatched_closing_brace':
            labels,end=json.JSONDecoder().raw_decode(content)
            assert content[end:].strip()=='}'
        elif status=='deterministically_repaired_one_brace_json_boundary':
            mode=saved['extraction']['repair_mode']
            if mode=='append_exactly_one_terminal_closing_brace':labels=json.loads(content+'}')
            elif mode=='prepend_exactly_one_opening_brace':labels=json.loads('{'+content)
            else:raise AssertionError('Unrecognized recorded structural transformation: '+mode)
        else:labels=json.loads(content)
        if status=='deterministically_schema_normalized_exact_targets_array':
            assert set(labels)=={'targets'} and all(set(x)=={'id','label'} for x in labels['targets'])
            pairs=labels['targets'];labels={x['id']:x['label'] for x in pairs};assert len(labels)==len(pairs)
        if status=='deterministically_canonicalized_exact_closed_ontology_alias':
            rule=saved['alias_rule']
            affected=[k for k,v in labels.items() if v==rule['raw_label_exact']]
            assert set(affected)==set(rule['alias_target_ids']) and len(affected)==rule['expected_alias_count']
            for k in affected:labels[k]=rule['canonical_closed_ontology_label_exact']
        assert labels==saved['annotations'],call
        assert all(v in details[call]['ontology'] for v in labels.values()),call
        parsed[call]=labels
    mapping={}
    for r in rows:
        label=parsed[r['source_call_id']][r['target_id']];assert label==r['label']
        k=r['clustering_method'],r['llm'],r['cluster_id'];assert k not in mapping;mapping[k]=label
    base=root/'outputs/revision_20261021'
    assignments=pd.read_csv(base/'annotation_bound/assignments.csv.gz',dtype=str)
    maps=pd.read_csv(base/'historical_annotation_metrics/historical_16_maps_key_aligned.csv.gz',dtype=str)
    joined=maps.merge(assignments,on=['File_ID','ID'],sort=False,validate='one_to_one')
    assert len(joined)==len(assignments)==len(maps)==220082
    conditions=sorted({(r['clustering_method'],r['llm']) for r in rows})
    for method,model in conditions:
        lookup={cluster:v for (m,llm,cluster),v in mapping.items() if m==method and llm==model}
        expanded=joined[method].map(lookup)
        assert expanded.notna().all()
        np.testing.assert_array_equal(expanded.to_numpy(),joined[method+'__'+model].to_numpy())
    assert len(rows)==4584 and len(conditions)==16 and len(grouped)==179 and native==173 and transformed==6
    assert int((maps['leiden__claude']==maps.truth_normalized).sum())==123099
    return {'contributing_responses':179,'native_responses':native,'documented_transformations':transformed,'cluster_labels_replayed':len(rows),'cell_prediction_maps':len(conditions),'cells_per_map':len(maps),'leiden_claude_reference_matches':123099}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path.cwd())
    ap.add_argument('--hashes-only',action='store_true')
    ap.add_argument('--receipt',type=Path,default=Path('public_replay_receipt.json'))
    args=ap.parse_args();root=args.root.resolve()
    manifest=read(root/'PUBLIC_MANIFEST.json')
    result={'status':'pass','verified_files':check_files(root,manifest),'network_access':False,'new_model_calls':0,'new_fits':0}
    if not args.hashes_only:
        parser=module('registered_public_parser',root/'controlled_annotation/registered_parser.py')
        # This registered verifier checks every final raw-response prediction map,
        # cell expansion, regional metric and prompt-control change in the study.
        with tempfile.TemporaryDirectory(prefix='cell-masks-controlled-replay-') as temp:
            cached=Path(temp)/'controlled_annotation'
            shutil.copytree(root/'controlled_annotation',cached)
            subprocess.run([sys.executable,str(cached/'verify_cached.py')],cwd=cached,check=True)
            result['controlled_annotation']=read(cached/'offline_replay_receipt.json')
        result['paired_representations']=paired(root,parser)
        result['calibration_and_spatial']=calibration(root,parser)
        result['conditional_comparisons']=conditional_comparisons(root)
        result['historical_raw_responses']=historical_raw_responses(root)
        with tempfile.TemporaryDirectory(prefix='cell-masks-historical-replay-') as temp:
            temporary=Path(temp)
            relative=Path('outputs/revision_20261029/historical_label_mapping_sensitivity')
            shutil.copytree(root/relative,temporary/relative)
            (temporary/'outputs/revision_20261021').symlink_to(root/'outputs/revision_20261021',target_is_directory=True)
            subprocess.run([sys.executable,str(temporary/relative/'verify.py')],cwd=temporary,check=True)
            result['historical_mapping']=read(temporary/relative/'independent_verification.json')
    args.receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
