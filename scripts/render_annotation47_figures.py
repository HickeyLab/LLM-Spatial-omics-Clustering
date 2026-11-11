"""Render the completed, one-annotation 47-marker study from scored tables.

The input directory is a checksum-pinned offline result export. There is no
inference, fitting, clustering or endpoint access in this module.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

from publication_figure_design import (
    ROOT, METHODS, METHOD_KEYS, METHOD_COLORS, MODEL_COLORS,
    figure, axes, text, panel, grid, heatmap, colorbar, flow, finish, sha,
)
from biorender_workflows import add_workflow

DATA = ROOT / "data/frozen/annotation47_results_20261110"
MODEL_KEYS = ["openai", "anthropic", "google", "deepseek"]
MODELS = ["Astra", "Opus 5.5", "Argon", "DeepSeek"]
FULL_MODELS = ["GPT-6 Astra", "Claude Opus 5.5", "Gemini 4 Argon", "DeepSeek V4.1 Flash 1017"]
ARM = "all_means_fractions"
COMPONENT_NAMES = ["Reference agreement", "Gap to maximum agreement",
                   "Within-cluster minority-label fraction"]
COMPONENT_COLORS = ["#2A6F5B", "#D9852B", "#D9D9D9"]
FIXED_REGION = "8da8f27977d946b8c912d42c8827b55c"


def checked_path(name):
    path = DATA / name
    manifest = json.loads((DATA / "manifest.json").read_text())
    spec = manifest["files"][name]
    expected = spec["sha256"] if isinstance(spec, dict) else spec
    if sha(path) != expected:
        raise ValueError(f"Scored figure input changed: {name}")
    return path


def table(name, **kwargs):
    return pd.read_csv(checked_path(name), **kwargs)


def policy():
    d=json.loads(checked_path("protocol.json").read_text())
    return {"labels":d["ontology"],"markers":d["markers"]}


def input_hashes(*names):
    return {str((DATA / n).relative_to(ROOT)): sha(DATA / n) for n in names}


def metric_rows(scope="equal_test_regions", arm=ARM, population="all_labels"):
    d = table("metrics.csv")
    return d[d.arm.eq(arm) & d.scope.eq(scope) & d.population.eq(population)].copy()


def metric_matrix(metric, scope="equal_test_regions", arm=ARM):
    d = metric_rows(scope=scope, arm=arm)
    mat = d.pivot(index="model_family", columns="method", values=metric).reindex(index=MODEL_KEYS, columns=METHOD_KEYS)
    if mat.shape != (4, 4) or not np.isfinite(mat.to_numpy()).all():
        raise ValueError(f"Incomplete annotation metric: {metric}/{scope}/{arm}")
    return mat.to_numpy()


def palette():
    d = pd.read_csv(ROOT / "configs/cell_type_colors.csv")
    return dict(zip(d.cell_type_update, d.color_hex))


def draw_spatial(ax, cells, labels, size=.16):
    colors = pd.Series(labels, index=cells.index).map(palette()).fillna("#d0d0d0")
    ax.scatter(cells.x, cells.y, c=colors, s=size, linewidths=0, alpha=.8, rasterized=True)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True); s.set_color("#b0b0b0"); s.set_linewidth(.35)


def matrix_panel(f, x, y, metric, title, limits=(0, 100), fmt=".1f"):
    text(f, x+39, y, title, size=6.5, ha="center", weight="bold")
    a = axes(f, x+19, y+10, 48, 37)
    h = heatmap(a, metric_matrix(metric)*100, MODELS, METHODS, *limits,
                annotate=True, fmt=fmt, size=6.3)
    plt.setp(a.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    colorbar(f, h, (x+70, y+10, 2, 37), None, ticks=[limits[0], (limits[0]+limits[1])/2, limits[1]], orientation="vertical")
    return a


def focal_clusters(model_family="anthropic"):
    d = table("cluster_predictions.csv", dtype={"cluster_id": str})
    d = d[d.model_family.eq(model_family) & d.method.eq("leiden") & d.arm.eq(ARM)].copy()
    if len(d) != 300 or d.n_cells.sum() != 220082:
        raise ValueError("Focal cluster denominator changed")
    return d


def cluster_components(d):
    v = np.stack([d.n_correct, d.majority_count-d.n_correct, d.n_cells-d.majority_count], axis=1) / d.n_cells.to_numpy()[:, None]
    if (v < -1e-12).any() or not np.allclose(v.sum(axis=1), 1):
        raise ValueError("Invalid cluster-bound decomposition")
    return v


def legend_components(f, y, ncol=3):
    f.legend(handles=[Patch(color=c, label=l) for c,l in zip(COMPONENT_COLORS, COMPONENT_NAMES)],
             loc="upper center", bbox_to_anchor=(.5, 1-y/f._physical_mm[1]),
             ncol=ncol, fontsize=5.5, handlelength=.85, columnspacing=1)


def confusion_matrix(scope="pooled_test", model_family="anthropic"):
    d = table("confusion.csv.gz")
    d = d[d.model_family.eq(model_family) & d.method.eq("leiden") & d.arm.eq(ARM)
          & d.scope.eq(scope) & d.population.eq("all_labels")]
    cfg = policy()
    labels = cfg["labels"]
    counts = d.pivot(index="truth_label", columns="pred_label", values="count").reindex(index=labels, columns=labels, fill_value=0).fillna(0)
    if counts.shape != (28, 28):
        raise ValueError("Confusion vocabulary changed")
    row = np.divide(counts.to_numpy(), counts.sum(axis=1).to_numpy()[:, None],
                    out=np.zeros((28,28)), where=counts.sum(axis=1).to_numpy()[:, None] > 0)
    return counts, row


def figure_3(out):
    f = figure(205)
    panel(f, "A", 3, 2)
    flow(f, ["Frozen cell partitions\n47 markers · 1,128 clusters",
             "Anonymous cluster evidence\nMeans / means + fractions · 28 labels",
             "Four models · one annotation\nReference-label evaluation"], 10, height=17, x=11,
         widths=[47,47,47], gap=3, size=6)
    panel(f, "B", 3, 36)
    matrix_panel(f, 3, 36, "agreement", "Reference agreement (%)")
    panel(f, "C", 85, 36)
    matrix_panel(f, 85, 36, "fixed28_macro_f1", "Fixed-28-label macro-F1 (%)")
    panel(f, "D", 3, 106, "Leiden cell-type agreement")
    d = table("per_type_metrics.csv")
    d = d[d.method.eq("leiden") & d.arm.eq(ARM) & d.scope.eq("pooled_test") & d.population.eq("all_labels")]
    vals = d.pivot(index="label", columns="model_family", values="recall").reindex(columns=MODEL_KEYS)
    # Fixed ontology order avoids selecting or sorting cell types by outcomes.
    labels = policy()["labels"]
    vals = vals.reindex(labels)
    a = axes(f, 32, 118, 38, 70)
    h = heatmap(a, vals.to_numpy()*100, labels, MODELS, 0, 100)
    plt.setp(a.get_xticklabels(), rotation=50, ha="right", rotation_mode="anchor")
    colorbar(f, h, (73,118,2,70), "Recall (%)", ticks=[0,50,100], orientation="vertical")
    panel(f, "E", 85, 106, "Fixed spatial view")
    cells = table("reference_cells.csv.gz")
    z = cells[cells.File_ID.eq(FIXED_REGION)].copy()
    predictions=np.load(checked_path("cell_predictions.npz"))
    for model in MODEL_KEYS:
        values=predictions[f"{model}__leiden__{ARM}"]
        z["leiden__"+model]=np.asarray(policy()["labels"],dtype=object)[values[z.index]]
    if not len(z): raise ValueError("Fixed spatial region missing")
    titles = ["Reference"] + MODELS
    cols = ["truth_label"] + ["leiden__"+m for m in MODEL_KEYS]
    for i,(title,col) in enumerate(zip(titles, cols)):
        x = 87 + (i%3)*25.1; y = 123 + (i//3)*32
        text(f, x+11.5, y-5, title, size=6, ha="center")
        a = axes(f, x, y, 23, 26)
        draw_spatial(a, z, z[col])
    text(f, 88, 190, "B004 mid-jejunum · fixed spatial view", size=5.5)
    return finish(f, "Figure_3", out, input_hashes("metrics.csv", "per_type_metrics.csv", "reference_cells.csv.gz", "cell_predictions.npz", "protocol.json"),
                  notes=["One accepted annotation per model/method/arm; no repeated-generation SD.",
                         "B/C: equal-weighted two test regions, all original28 labels including Noise. D: pooled test cells. E: fixed Figure2C region."])


def figure_4(out):
    f = figure(191)
    panel(f, "A", 3, 2)
    workflow_inputs = add_workflow(f, "4A", annotation_model="Astra")
    panel(f, "B", 3, 35, "Test-cell confusion")
    counts, mat = confusion_matrix(model_family="openai")
    a = axes(f, 29, 54, 56, 56)
    h = heatmap(a, mat, counts.index, counts.columns, 0, 1, cmap="RdYlGn")
    plt.setp(a.get_xticklabels(), rotation=90)
    a.set_xlabel("Predicted cell type"); a.set_ylabel("Reference cell type")
    colorbar(f, h, (29,43,56,1.7), None, ticks=[0,.5,1])
    panel(f, "C", 87, 35, "Cell-type F1")
    d = table("per_type_metrics.csv")
    d = d[d.model_family.eq("openai") & d.method.eq("leiden") & d.arm.eq(ARM) & d.population.eq("all_labels")]
    labels = counts.index.tolist()
    pooled = d[d.scope.eq("pooled_test")].set_index("label").reindex(labels)
    a = axes(f, 119, 47, 42, 73)
    a.barh(range(28), pooled.f1, color="#e7e8ec", edgecolor="#9ca3af", linewidth=.35, height=.7)
    regions = d[d.scope.eq("region") & d.split.eq("test")].region.drop_duplicates().tolist()
    colors = ["#2864a5", "#bc6535"]
    names = json.loads((ROOT / "configs/figure_04_historical_claude.json").read_text())["regions"]
    handles = [Patch(color="#e7e8ec", label="Pooled test")]
    for region,c in zip(regions,colors):
        v = d[d.scope.eq("region") & d.region.eq(region)].set_index("label").reindex(labels).f1
        a.scatter(v, range(28), s=6, color=c, edgecolors="white", linewidths=.15, zorder=3)
        handles.append(Line2D([],[],marker="o",ls="",color=c,markersize=2.5,label=names[region]["name"]))
    a.set(yticks=range(28), yticklabels=labels, ylim=(27.7,-.7), xlim=(0,1), xticks=[0,.5,1], xlabel="F1 score")
    grid(a,"x")
    f.legend(handles=handles, loc="upper center", bbox_to_anchor=(.77,1-123/191), ncol=1, fontsize=5.5)
    d = focal_clusters(model_family="openai")
    ex = d.sort_values(["n_cells", "cluster_id"], ascending=[False, True], kind="stable").head(3)
    panel(f, "D", 3, 145, "Three largest Leiden clusters")
    a = axes(f, 47, 154, 36, 22); left=np.zeros(3)
    for k,c in enumerate(COMPONENT_COLORS):
        vals=cluster_components(ex)[:,k]
        a.barh(range(3), vals, left=left, color=c, height=.62, edgecolor="white", linewidth=.3)
        for j,v in enumerate(vals):
            if v>.1: a.text(left[j]+v/2,j,f"{v:.0%}",ha="center",va="center",fontsize=5.5,color="white" if k==0 else "black")
        left += vals
    labs=[f"Cluster {r.cluster_id} (n={r.n_cells:,})\nMajority: {r.majority_truth}\nPredicted: {r.pred_label}" for r in ex.itertuples()]
    a.set(yticks=range(3),yticklabels=labs,ylim=(2.5,-.5),xlim=(0,1),xticks=[0,.5,1],xlabel="Fraction of cluster cells")
    a.xaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    panel(f,"E",88,145,"All B004 cells")
    a=axes(f,109,157,52,13)
    vals=np.array([d.n_correct.sum(),(d.majority_count-d.n_correct).sum(),(d.n_cells-d.majority_count).sum()])/d.n_cells.sum()
    left=0
    for k,(v,c) in enumerate(zip(vals,COMPONENT_COLORS)):
        a.barh([0],[v],left=[left],height=.6,color=c,edgecolor="white",linewidth=.4)
        if v>.07:a.text(left+v/2,0,f"{v:.1%}",ha="center",va="center",fontsize=5.5,color="white" if k==0 else "black")
        left += v
    a.set(yticks=[0],yticklabels=["Leiden–\nAstra"],xlim=(0,1),ylim=(-.6,.6),xticks=[0,.5,1],xlabel="Fraction of all cells")
    a.xaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    legend_components(f,181)
    return finish(f,"Figure_4",out,{**input_hashes("confusion.csv.gz","per_type_metrics.csv","cluster_predictions.csv","protocol.json"),**workflow_inputs},
                  notes=["Leiden–Astra means-plus-fractions pipeline selected from the B004 benchmark results. B/C use test cells. D/E use all220082 cells and original28 labels.","Examples chosen by descending cell count, then clusterID; no reference-agreement selection."])


def figure_s6(out):
    f=figure(251)
    counts,row=confusion_matrix()
    panel(f,"A",3,2)
    for i,(mat,title,lim) in enumerate([(counts.to_numpy(),"Counts",float(counts.to_numpy().max())),(row,"Row fraction",1)]):
        x=3+i*81
        text(f,x+43,7,title,size=6.5,ha="center",weight="bold")
        a=axes(f,x+22,25,56,56)
        h=heatmap(a,mat,counts.index,counts.columns,0,lim,cmap="RdYlGn")
        plt.setp(a.get_xticklabels(),rotation=90)
        a.set_xlabel("Predicted cell type");a.set_ylabel("Reference cell type")
        colorbar(f,h,(x+22,14,56,1.7),None,ticks=[0,lim])
    panel(f,"B",3,113,"All 300 Leiden clusters")
    legend_components(f,123)
    d=focal_clusters();d["bound_fraction"]=d.majority_count/d.n_cells
    d=d.sort_values(["bound_fraction","cluster_id"],ascending=[False,True],kind="stable")
    for i in range(4):
        z=d.iloc[i*75:(i+1)*75];a=axes(f,20+i*40,138,20,99);left=np.zeros(75)
        for k,c in enumerate(COMPONENT_COLORS):
            vals=cluster_components(z)[:,k];a.barh(range(75),vals,left=left,color=c,height=.86,linewidth=0);left+=vals
        ticks=list(range(0,75,10))+[74]
        a.set(yticks=ticks,yticklabels=z.iloc[ticks].cluster_id,ylim=(75,-1),xlim=(0,1),xticks=[0,.5,1],xlabel="Fraction")
        a.tick_params(axis="y",length=0,pad=1.5);a.spines["left"].set_visible(False)
        a.xaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    return finish(f,"Figure_S6",out,input_hashes("confusion.csv.gz","cluster_predictions.csv","protocol.json"),notes=["A: held-out test-cell confusion. B: all220082cells across300Leidenclusters; sorted by decreasing majority-reference fraction, then clusterID."])


def figure_s7(out):
    f=figure(133)
    d=metric_rows()
    a=axes(f,35,10,126,96)
    labels=[]
    for i,method in enumerate(METHOD_KEYS):
        for j,model in enumerate(MODEL_KEYS):
            r=d[d.method.eq(method)&d.model_family.eq(model)].iloc[0]
            vals=[r.agreement,r.reference_upper_bound-r.agreement,1-r.reference_upper_bound]
            if min(vals)<-1e-12:raise ValueError("Invalid test decomposition")
            left=0;idx=i*4+j
            for k,(v,c) in enumerate(zip(vals,COMPONENT_COLORS)):
                a.barh(idx,v,left=left,height=.75,color=c,edgecolor="white",linewidth=.25)
                if v>.08:a.text(left+v/2,idx,f"{100*v:.1f}",ha="center",va="center",fontsize=5.5,color="white" if k==0 else "black")
                left+=v
            labels.append(f"{METHODS[i]} · {MODELS[j]}")
        if i<3:a.axhline(i*4+3.5,color="#b5b5b5",lw=.45)
    a.set(yticks=range(16),yticklabels=labels,ylim=(15.6,-.6),xlim=(0,1),xticks=np.arange(0,1.01,.2),xlabel="Equal-weighted test-region fraction")
    a.xaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    a.spines["left"].set_visible(False);a.tick_params(axis="y",length=0)
    legend_components(f,119)
    return finish(f,"Figure_S7",out,input_hashes("metrics.csv"),notes=["All16means-plus-fractions conditions. Components computed within each test region before equal weighting. The arithmetic components are not causal or independent biological error classes."])


def figure_s10(out):
    f=figure(126)
    for i,(model,title) in enumerate(zip(MODEL_KEYS,FULL_MODELS)):
        x=3+(i%2)*82;y=14+(i//2)*50
        panel(f,chr(65+i),x,y,title)
        a=axes(f,x+20,y+10,57,29)
        d=metric_rows(arm="all_means");e=metric_rows(arm=ARM)
        p=d[d.model_family.eq(model)].set_index("method").reindex(METHOD_KEYS).agreement.to_numpy()*100
        q=e[e.model_family.eq(model)].set_index("method").reindex(METHOD_KEYS).agreement.to_numpy()*100
        for j in range(4):a.plot([p[j],q[j]],[j,j],color="#c9d2da",lw=.8,zorder=1)
        a.scatter(p,np.arange(4)-.06,s=12,marker="o",color="#2864a5",zorder=2)
        a.scatter(q,np.arange(4)+.06,s=12,marker="s",color="#b55224",zorder=2)
        a.set(yticks=range(4),yticklabels=METHODS,ylim=(3.5,-.5),xlim=(0,100),xticks=[0,25,50,75,100],xlabel="Reference agreement (%)")
        grid(a,"x")
    f.legend(handles=[Line2D([],[],marker="o",ls="",color="#2864a5",markersize=3,label="All-marker means"),Line2D([],[],marker="s",ls="",color="#b55224",markersize=3,label="Means plus fractions")],loc="upper center",bbox_to_anchor=(.5,.995),ncol=2,fontsize=6)
    return finish(f,"Figure_S10",out,input_hashes("metrics.csv","paired_contrasts.csv"),notes=["Single-annotation descriptive input comparisons; equal-weighted test-region agreement. No repeated-generation SD, confidence intervals, majority votes or repeatability claims."])


def figure_s11(out):
    d=table("cd8_consensus_profiles.csv")
    f=figure(55)
    panel(f,"A",3,2,"CD8+ T")
    markers=policy()["markers"]
    a=axes(f,30,17,131,12)
    row_labels=[]
    for i,m in enumerate(METHOD_KEYS):
        z=d[d.method.eq(m)].set_index("marker").reindex(markers)
        dots=a.scatter(range(47),[i]*47,s=.08+10*z.fraction_above_zero,c=z.mean_minmax_four_methods,cmap="Reds",vmin=0,vmax=1,linewidths=.2,edgecolors="#777777")
        n=int(z.n_cells.iloc[0])
        row_labels.append(f"{METHODS[i]} (n={n:,})")
    a.set(yticks=range(4),yticklabels=row_labels,xticks=range(47),xticklabels=markers,xlim=(-.7,46.7),ylim=(3.5,-.5))
    plt.setp(a.get_xticklabels(),rotation=48,ha="right",rotation_mode="anchor")
    a.tick_params(length=0)
    for edge in a.spines.values():edge.set_visible(True);edge.set_linewidth(.5)
    colorbar(f,dots,(121,10,39,1.7),None,ticks=[0,1])
    text(f,121,2,"Mean stored expression\nScaled 0–1",size=5.5)
    leg=axes(f,53,7,51,7);leg.set_axis_off();leg.set(xlim=(0,1),ylim=(0,1))
    for x,v in zip([.1,.46,.82],[0,.5,1]):
        leg.scatter([x],[.6],s=.08+10*v,color="#aaaaaa",edgecolors="#777777",linewidths=.2)
        leg.text(x,.13,f"{100*v:g}",fontsize=5.5,va="top",ha="center")
    text(f,31,8,"Stored value > 0 (%)",size=5.5,ha="right")
    return finish(f,"Figure_S11",out,input_hashes("cd8_consensus_profiles.csv","protocol.json"),notes=["Cells selected using one accepted label per model and fixed four-model modal ties, not repeated-call votes. Color uses stored processed expression without another transform, min-max scaled by marker across the four displayed methods. Size encodes the numerical fraction >0, not validated biological positivity."])


RENDERERS={"3":figure_3,"4":figure_4,"S6":figure_s6,"S7":figure_s7,"S10":figure_s10,"S11":figure_s11}
