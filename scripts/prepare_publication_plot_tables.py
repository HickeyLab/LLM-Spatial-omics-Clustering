#!/usr/bin/env python3
"""Freeze compact plotting tables from archived, already scored figure inputs.

This optional preparation step reads a local source archive. The publication
renderer itself only needs the resulting tracked tables. It performs no model
calls, fitting, clustering, tuning, new matching or new hypothesis tests.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import yaml

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data/frozen/publication_design"
KEYS=["File_ID","ID"]
SEG=["Mesmer","CellposeCyto3","CellposeSAM","CellSAM","InstanSeg","MicroSAM"]
METHODS=["leiden","flowsom","spatialsort","pixie"]
MODELS=["gpt","claude","gemini","deepseek"]


def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()


def write(df,name):
    p=DATA/name
    if name.endswith(".gz"):
        df.to_csv(p,index=False,compression={"method":"gzip","mtime":0})
    else:df.to_csv(p,index=False)
    return sha(p)


def column(g,name):
    n=g[name]
    if isinstance(n,h5py.Group):return n["categories"].asstr()[:][n["codes"][:]]
    if h5py.check_string_dtype(n.dtype):return n.asstr()[:]
    return n[:]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sources",type=Path,required=True,help="Archive cache with extracted/ and local_sources/")
    p.add_argument("--coordinate-h5ad",type=Path,required=True)
    args=p.parse_args();arc=args.sources/"extracted";local=args.sources/"local_sources"
    receipt={"inference_calls":0,"fits":0,"new_matching":0,"sources":{},"checks":{}}
    cfg=yaml.safe_load((ROOT/"configs/figure_02.yaml").read_text())
    normal=cfg["four_llm_consensus"]["truth_normalization_map"]
    ref=pd.read_csv(DATA/"reference_cells.csv.gz")
    # Verify every reference label against the archived historical input.
    truth_path=arc/"outputs/revision_20261021/historical_figure4_sources/truth.csv"
    truth=pd.read_csv(truth_path)
    chk=ref.merge(truth,on=KEYS,validate="one_to_one",suffixes=("","_archived"))
    assert len(chk)==220082
    assert chk.cell_type_update.eq(chk.cell_type_update_archived).all()
    receipt["checks"]["all_220082_reference_labels_match_archived_truth"]=True
    assignment_manifest=json.loads((ROOT/"data/frozen/v3_k300_assignments/manifest.json").read_text())
    for m in METHODS:
        spec=assignment_manifest["methods"][m]
        path=ROOT/"data/frozen/v3_k300_assignments"/spec["path"]
        b=gzip.decompress(path.read_bytes());assert hashlib.sha256(b).hexdigest()==spec["source_csv_sha256"]
        d=pd.read_csv(path);ref=ref.merge(d[KEYS+[spec["assignment_column"]]],on=KEYS,validate="one_to_one")
        ref=ref.rename(columns={spec["assignment_column"]:m})
    assert len(ref)==220082
    receipt["sources"]["reference_h5ad_sha256"]=sha(args.coordinate_h5ad)
    receipt["sources"]["reference_h5ad_filename"]=args.coordinate_h5ad.name
    receipt["checks"]["coordinate_scope"]="Native archived coordinates retained to match the current manuscript's spatial artwork. The public Duke H5AD coordinate convention differs by an axis swap. No coordinates or embedding values are fitted or changed."
    # The original shared embedding is reused byte-for-byte, with no UMAP fit.
    up=local/"umap_flowsom_coords.csv";ub=up.read_bytes()
    assert hashlib.sha256(ub).hexdigest()==cfg["panel_d"]["shared_umap"]["source_coordinates_sha256"]
    (DATA/"umap_coordinates.csv.gz").write_bytes(gzip.compress(ub,mtime=0))
    receipt["checks"]["original_umap_coordinate_sha256"]=hashlib.sha256(ub).hexdigest()
    write(ref,"reference_plot_cells.csv.gz")
    # Restore the existing compensation scores and maps from cached matches.
    cp=[];spatial=[];source_hashes={}
    for m in SEG:
        scores={}
        for condition in ["before","after"]:
            path=(local/f"{m}_before.csv.gz") if condition=="before" else (arc/f"outputs/revision/segmentation/matching/{m}_after.csv.gz")
            source_hashes[f"{m}_{condition}"]=sha(path)
            d=pd.read_csv(path,dtype={"cluster":str})
            accepted=d[d.accepted].copy()
            counts=accepted.groupby(["cluster","reference_label"]).size().rename("n").reset_index()
            mapping=counts.sort_values(["cluster","n","reference_label"],ascending=[True,False,True],kind="stable").drop_duplicates("cluster").set_index("cluster").reference_label
            accepted["predicted"]=accepted.cluster.map(mapping)
            labels=sorted(set(accepted.reference_label)|set(accepted.predicted))
            rows=[]
            for lab in labels:
                nt=int(accepted.reference_label.eq(lab).sum());npred=int(accepted.predicted.eq(lab).sum())
                tp=int((accepted.reference_label.eq(lab)&accepted.predicted.eq(lab)).sum())
                rows.append({"cell_type":lab,"true_cells":nt,"predicted_cells":npred,"true_positives":tp,
                             "f1":2*tp/(nt+npred) if nt+npred else 0})
            scores[condition]=pd.DataFrame(rows).set_index("cell_type")
            if m in ["Mesmer","CellposeSAM","CellposeCyto3"]:
                z=d[d.region.eq("B004-A-004")][["x","y","cluster"]].copy()
                z["predicted_label"]=z.cluster.map(mapping).fillna("Unmapped")
                z["method"]=m;z["condition"]=condition;spatial.append(z.drop(columns="cluster"))
        d=scores["before"].join(scores["after"],lsuffix="_before",rsuffix="_after").reset_index()
        d["delta_f1"]=d.f1_after-d.f1_before;d["method"]=m;cp.append(d)
    write(pd.concat(cp,ignore_index=True),"figure1_pooled_f1_changes.csv")
    write(pd.concat(spatial,ignore_index=True),"figureS2_spatial_cells.csv.gz")
    receipt["sources"]["archived_segmentation_matches"]=source_hashes
    # Native X is verified against all 180 already audited Figure 2I summaries.
    with h5py.File(args.coordinate_h5ad,"r") as h:
        file_ids=column(h["obs"],"File_ID");idx=np.flatnonzero(np.isin(file_ids,ref.File_ID.unique()))
        obs=pd.DataFrame({"File_ID":file_ids[idx],"ID":column(h["obs"],"ID")[idx],"source_index":idx})
        aligned=ref[KEYS].merge(obs,on=KEYS,validate="one_to_one")
        blocks=[h["X"][int(c[0]):int(c[-1])+1,:] for c in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1)]
        # Match the archived master-matrix / Scanpy float32 representation.
        x=np.asarray(np.concatenate(blocks)[pd.Index(idx).get_indexer(aligned.source_index)],dtype=np.float32)
        markers=column(h["var"],"_index").tolist()
    consensus=pd.read_csv(ROOT/"data/frozen/v3_k300_assignments/panel_i_j_four_llm_consensus.csv.gz")
    cons=ref[KEYS].merge(consensus,on=KEYS,validate="one_to_one")
    checked=pd.read_csv(DATA/"figure2_marker_summaries.csv")
    for m,label,col in [("leiden","Leiden","leiden_consensus"),("flowsom","FlowSOM","flowsom_consensus"),("spatialsort","SpatialSort","spatialsort_consensus"),("pixie","PIXIE","pixie_tiff_consensus")]:
        a=x[cons[col].eq("CD8+ T")]
        means=a.mean(axis=0,dtype=np.float64);fracs=np.count_nonzero(a>0,axis=0)/len(a)*100
        q=checked[checked.method.eq(label)].set_index("marker").reindex(markers)
        np.testing.assert_allclose(means,q.mean_expression,atol=1e-11,rtol=1e-11)
        np.testing.assert_allclose(fracs,q.fraction_cells_pct,atol=1e-11,rtol=0)
    receipt["checks"]["all_180_marker_means_and_fractions_match_audited_figure2I"]=True
    rows=[]
    for lab in sorted(set(ref.cell_type_update)-{"Noise"}):
        a=x[ref.cell_type_update.eq(lab)]
        means=a.mean(axis=0,dtype=np.float64);fracs=np.count_nonzero(a>0,axis=0)/len(a)*100
        rows.extend({"cell_type":lab,"marker":marker,"mean_expression":means[j],"fraction_cells_pct":fracs[j]} for j,marker in enumerate(markers))
    d=pd.DataFrame(rows);g=d.groupby("marker").mean_expression;lo=g.transform("min");hi=g.transform("max")
    d["scaled_mean_expression"]=np.divide(d.mean_expression-lo,hi-lo,out=np.zeros(len(d)),where=hi>lo)
    write(d,"figureS4_marker_summaries.csv")
    # Retain the existing raw-label cluster compositions and diagnostic grains.
    comp=[];metrics=[];f1rows=[]
    for m in METHODS:
        d=ref.groupby([m,"cell_type_update"]).size().rename("n_cells").reset_index().rename(columns={m:"cluster","cell_type_update":"cell_type"});d["method"]=m;comp.append(d)
        d=ref[ref.cell_type_update.ne("Noise")].copy()
        counts=d.groupby([m,"cell_type_update"]).size().rename("n").reset_index()
        mapping=counts.sort_values([m,"n","cell_type_update"],ascending=[True,False,True],kind="stable").drop_duplicates(m).set_index(m).cell_type_update
        for cluster,g in counts.groupby(m,sort=True):
            ps=g.n.to_numpy()/g.n.sum()
            metrics.append({"method":m,"cluster":cluster,"majority_label":mapping[cluster],"n_cells":g.n.sum(),"shannon_index":float(-(ps*np.log(ps)).sum()),"purity_percent":float(ps.max()*100)})
        pred=d[m].map(mapping)
        for lab in sorted(set(d.cell_type_update)):
            nt=int(d.cell_type_update.eq(lab).sum());npred=int(pred.eq(lab).sum());tp=int((d.cell_type_update.eq(lab)&pred.eq(lab)).sum())
            f1rows.append({"method":m,"cell_type":lab,"f1":2*tp/(nt+npred) if nt+npred else 0,"recall":tp/nt})
    write(pd.concat(comp,ignore_index=True),"figureS4_compositions.csv.gz")
    write(pd.DataFrame(metrics),"figureS4_cluster_metrics.csv")
    write(pd.DataFrame(f1rows),"figureS4_celltype_metrics.csv")
    # Exact historical reference-agreement values for Figure 3B/C.
    hist=pd.read_csv(DATA/"historical_annotation_maps.csv.gz")
    d=ref.merge(hist,on=KEYS,validate="one_to_one")
    assert d.cell_type_update.replace(normal).eq(d.truth_normalized).all()
    rows=[];types=[]
    for m in METHODS:
        mk="pixie_tiff" if m=="pixie" else m
        counts=d.groupby([m,"truth_normalized"]).size().rename("n").reset_index()
        bound=counts.groupby(m).n.max().sum()/len(d)
        for model in MODELS:
            correct=d[f"{mk}__{model}"].eq(d.truth_normalized)
            direct=float(correct.mean())
            rows.append({"method":mk,"model":model,"agreement_percent":100*direct,"upper_bound_percent":100*bound,"percent_of_upper_bound":100*direct/bound})
            if m=="leiden":
                for lab,g in d[d.truth_normalized.ne("Noise")].groupby("truth_normalized"):
                    types.append({"cell_type":lab,"model":model,"reference_cells":len(g),"agreement_percent":100*g[f"{mk}__{model}"].eq(g.truth_normalized).mean()})
    write(pd.DataFrame(rows),"figure3_agreement.csv")
    write(pd.DataFrame(types),"figure3_celltype_agreement.csv")
    # These formatted values are those shown in the controlling manuscript.
    check=pd.DataFrame(rows).pivot(index="model",columns="method",values="agreement_percent").reindex(index=["gemini","gpt","claude","deepseek"],columns=["flowsom","leiden","spatialsort","pixie_tiff"])
    np.testing.assert_allclose(np.round(check.to_numpy(),1),[[45.6,54.2,33.0,51.8],[44.5,51.1,33.1,52.3],[50.5,55.9,31.3,52.3],[43.1,48.7,32.7,49.9]],atol=1e-10)
    receipt["checks"]["all_16_Figure3B_displayed_values_preserved"]=True
    receipt["output_sha256"]={p.name:sha(p) for p in DATA.iterdir() if p.is_file() and p.suffix in [".csv",".gz"]}
    (DATA/"preparation_verification.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt["checks"],indent=2))


if __name__=="__main__":main()
