#!/usr/bin/env python3
"""Render the current manuscript figures using the shared publication style.

All numerical inputs are frozen. Run selected figures with --figures, or omit
it to render the full set. No API calls, model runs, clustering or fitting are
performed by this renderer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, ConnectionPatch
from matplotlib.text import Text
from matplotlib.ticker import PercentFormatter, MaxNLocator, FuncFormatter

from publication_figure_design import (
    ROOT, METHODS, METHOD_KEYS, METHOD_COLORS, MODELS, MODEL_KEYS, MODEL_COLORS,
    figure, axes, text, panel, grid, heatmap, colorbar, flow, finish, sha,
)

from biorender_workflows import add_workflow
from comparison_order import rank_labels
from original_compensation_workflow import add_original_compensation_workflow

sys.path.insert(0, str(ROOT / 'src'))
from llm_spatial_omics_clustering.clustering_publication import override_path

DATA = ROOT / "data/frozen/publication_design"
SEG = ["Mesmer", "CellposeCyto3", "CellposeSAM", "CellSAM", "InstanSeg", "MicroSAM"]
COMPONENT_NAMES = ["Reference agreement", "Gap to maximum agreement",
                   "Within-cluster minority-label fraction"]
COMPONENT_COLORS = ["#2A6F5B", "#D9852B", "#D9D9D9"]


def current_path(name):
    if name == "figureS4_marker_summaries.csv":
        folder=ROOT/"data/frozen/reference47_profiles_20261110"
        manifest=json.loads((folder/"manifest.json").read_text())
        entry=manifest["files"][name]
        path=folder/name
        if sha(path) != entry["sha256"]:
            raise ValueError("Frozen47-marker reference profiles changed")
        return path
    return override_path(name, root=ROOT)


def csv(name, **kw):
    current = current_path(name)
    if current is not None:
        return pd.read_csv(current, **kw)
    manifest = json.loads((DATA / "manifest.json").read_text())
    expected = manifest["files"][name]["sha256"]
    if sha(DATA / name) != expected:
        raise ValueError(f"Frozen publication input changed: {name}")
    return pd.read_csv(DATA/name, **kw)


def inputs(*names):
    paths = [current_path(n) or DATA/n for n in names]
    return {str(path.relative_to(ROOT)):sha(path) for path in paths}


def cell_colors():
    d=pd.read_csv(ROOT/"configs/cell_type_colors.csv")
    return dict(zip(d.cell_type_update,d.color_hex))


def spatial(a,d,label="cell_type_update",size=.3,normalize=False):
    colors=cell_colors()
    if normalize:
        import yaml
        norm=yaml.safe_load((ROOT/"configs/figure_02.yaml").read_text())["four_llm_consensus"]["truth_normalization_map"]
        colors={norm.get(k,k):v for k,v in colors.items()}
        # Match the recovered harmonized palette, rather than last-alias wins.
        for raw in ["Epithelial","Stromal","CD36 high Endothelial","CD4+ T","PDPN+ Stromal","Goblet","M2 Macrophage","Cycling TA","Neuroendocrine","CD66+ Epithelial","MUC1+ Epithelial","NK"]:
            colors[norm.get(raw,raw)]=cell_colors()[raw]
    a.scatter(d.x,d.y,c=d[label].map(colors).fillna("#d0d0d0"),s=size,linewidths=0,alpha=.8,rasterized=True)
    a.set_aspect("equal");a.set_xticks([]);a.set_yticks([])
    for s in a.spines.values():s.set_visible(False)


def count_heatmap(f,values,rows,cols,x,y,w,h,counts,limits=(0,100),label="Reference agreement (%)",rotation=55):
    a=axes(f,x,y,w,h);artist=heatmap(a,values,rows,cols,*limits)
    plt.setp(a.get_xticklabels(),rotation=rotation,ha="right",rotation_mode="anchor")
    c=axes(f,x+w+2,y,6,h)
    c.barh(range(len(rows)),[counts.get(r,0) for r in rows],height=.8,color="#64748b")
    c.set(ylim=(len(rows)-.5,-.5),yticks=[],xlim=(0,35000),xticks=[0,25000],xticklabels=["0","25k"])
    c.spines["left"].set_visible(False);c.set_xlabel("Cells",fontsize=5.5)
    colorbar(f,artist,(x,y-7,w,1.6),None,ticks=np.linspace(limits[0],limits[1],3))
    return artist


def figure_2(out):
    import yaml
    cfg=yaml.safe_load((ROOT/"configs/figure_02.yaml").read_text())
    ref=csv("reference_plot_cells.csv.gz");u=csv("umap_coordinates.csv.gz")
    d=ref.merge(u,on=["File_ID","ID"],validate="one_to_one")
    # Current manuscript Figure2 ends atH. Historical annotation profiles were
    # moved toS11A and the reference-selected spatial examples were removed.
    f=figure(224)
    panel(f,"A",3,2)
    workflow_inputs=add_workflow(f,"2A")
    panel(f,"B",3,39)
    a=axes(f,15,45,96,9)
    counts=ref.cell_type_update.value_counts().drop("Noise").sort_values(ascending=False)
    a.bar(range(27),counts,color=[cell_colors()[s] for s in counts.index],width=.88)
    a.set(xticks=range(27),xticklabels=counts.index,yticks=[0,15000,30000],yticklabels=["0","15k","30k"],ylabel="Cell count",xlim=(-.6,26.6))
    plt.setp(a.get_xticklabels(),rotation=90)
    panel(f,"C",115,39)
    a=axes(f,126,45,30,30);r=ref[ref.File_ID.eq("8da8f27977d946b8c912d42c8827b55c")].copy()
    spatial(a,r,size=.2)
    panel(f,"D",3,82)
    zoom=cfg["panel_d"]["style"]["zoom"]
    for i,(key,title) in enumerate([("cell_type_update","Reference\nannotations")]+list(zip(["leiden","flowsom","spatialsort","pixie"],METHODS))):
        x=11+i*31
        text(f,x+11.5,82,title,size=5.5,ha="center")
        if key=="cell_type_update":labels=d.cell_type_update
        else:
            mapping=d.groupby(key,sort=True).cell_type_update.agg(lambda s:s.value_counts().sort_index().idxmax())
            labels=d[key].map(mapping)
        colors=labels.map(cell_colors()).fillna("#d0d0d0")
        big=axes(f,x,99,23,13);big.scatter(d.UMAP1,d.UMAP2,c=colors,s=.09,alpha=.6,linewidths=0,rasterized=True)
        big.set_aspect("equal");big.set_xticks([]);big.set_yticks([])
        big.set_xlabel("UMAP 1",fontsize=5.5);big.set_ylabel("UMAP 2",fontsize=5.5,labelpad=1)
        small=axes(f,x+6,88,9,8);small.scatter(d.UMAP1,d.UMAP2,c=colors,s=.09,alpha=.6,linewidths=0,rasterized=True)
        x0,y0,s=zoom["x0"],zoom["y0"],zoom["size"]
        small.set(xlim=(x0,x0+s),ylim=(y0,y0+s),xticks=[],yticks=[]);small.set_aspect("equal")
        for edge in small.spines.values():edge.set_visible(True);edge.set_color("#888888");edge.set_linewidth(.35)
        big.add_patch(Rectangle((x0,y0),s,s,fill=False,ec="#555555",lw=.35))
        f.add_artist(ConnectionPatch((x0,y0+s),(x0,y0),coordsA=big.transData,coordsB=small.transData,color="#777777",lw=.35))
    region=csv("figure2_regional_metrics.csv")
    method_order = rank_labels(METHODS, region.groupby("method").weighted_f1.mean().reindex(METHODS))
    rcfg=json.loads((ROOT/"configs/figure_04_historical_claude.json").read_text())["regions"]
    for i,(letter,key,title,ylab) in enumerate([("E","weighted_f1",None,"Weighted F1"),("G","cluster_purity",None,"Cluster purity")]):
        x=3+i*83;panel(f,letter,x,121,title)
        a=axes(f,x+12,129,63,14)
        values=[region[region.method.eq(m)].sort_values("region")[key].to_numpy() for m in method_order]
        a.boxplot(values,positions=range(4),widths=.48,showfliers=False,patch_artist=True,
                  boxprops={"facecolor":"#e5e7eb","linewidth":.5},medianprops={"color":"black","linewidth":.6},whiskerprops={"linewidth":.5},capprops={"linewidth":.5})
        for j,m in enumerate(method_order):
            z=region[region.method.eq(m)].sort_values("region")
            a.scatter(j+np.linspace(-.08,.08,8),z[key],s=7,c=z.region.map({k:v["color"] for k,v in rcfg.items()}),zorder=3)
        a.set(xticks=range(4),xticklabels=method_order,ylim=(.3,.9),yticks=[.3,.5,.7,.9],ylabel=ylab);grid(a)
    norm=cfg['panel_e']['evaluation']['harmonization_map']
    nref=ref.loc[ref.cell_type_update.ne('Noise'),'cell_type_update'].replace(norm).value_counts().to_dict()
    f1=csv("figure2_f1.csv").set_index("cell_type")
    rows=rank_labels(f1.index, f1[METHODS].mean(axis=1))
    for i,(letter,filename,title,scale) in enumerate([("F","figure2_f1.csv","F1",1),("H","figure2_recall.csv","Recall (%)",100)]):
        x=3+i*83;panel(f,letter,x,150,title)
        matrix=csv(filename).set_index("cell_type").reindex(rows)[method_order].to_numpy()*scale
        count_heatmap(f,matrix,rows,method_order,x+27,163,38,39,nref,limits=(0,scale),rotation=55)
    # This dense figure has a small placement margin when fitted to one page.
    for t in f.findobj(Text):
        if t.get_fontsize()<6.6:t.set_fontsize(6.6)
        if t.get_text() in list("ABCDEFGH") and t.get_weight()=="bold":t.set_fontsize(10.3)
    names=["reference_plot_cells.csv.gz","umap_coordinates.csv.gz","figure2_regional_metrics.csv","figure2_f1.csv","figure2_recall.csv"]
    return finish(f,"Figure_2",out,{**inputs(*names),**workflow_inputs},notes=["Current A–H manuscript arrangement. E–H share descending mean regional weighted-F1 method order. F/H share descending across-method mean F1 cell-type order. Archived shared UMAP coordinates retained and recolored from the frozen primary partitions. Annotation-dependent results require the 47-marker annotation outputs. Suggested manuscript width: 128.27 mm (5.05 in)."])


def figure_s4(out):
    import yaml
    cfg=yaml.safe_load((ROOT/"configs/figure_s03.yaml").read_text())
    ref=csv("reference_plot_cells.csv.gz");d=csv("figureS4_marker_summaries.csv")
    f=figure(239)
    panel(f,"A",3,2)
    labs=cfg["panel_a"]["cell_type_order"];markers=cfg["panel_a"]["marker_order"]
    assert len(markers)==47 and len(set(markers))==47 and {"CD123","CDX2"}.issubset(markers)
    assert len(d)==27*47 and set(d.marker)==set(markers) and set(d.cell_type)==set(labs)
    assert d.groupby("cell_type").marker.nunique().eq(47).all()
    a=axes(f,29,12,40,58)
    for i,lab in enumerate(labs):
        z=d[d.cell_type.eq(lab)].set_index("marker").reindex(markers)
        dots=a.scatter(range(len(markers)),[i]*len(markers),s=.02+3*z.fraction_cells_pct/100,c=z.scaled_mean_expression,cmap="RdYlGn",vmin=0,vmax=1,linewidths=.1,edgecolors="#8c8c8c")
    a.set(yticks=range(27),yticklabels=labs,xticks=list(range(0,len(markers)-2,3))+[len(markers)-1],xticklabels=[markers[j] for j in list(range(0,len(markers)-2,3))+[len(markers)-1]],xlim=(-1,len(markers)),ylim=(26.5,-.5))
    plt.setp(a.get_xticklabels(),rotation=90)
    a.tick_params(length=0)
    for edge in a.spines.values():edge.set_visible(False)
    colorbar(f,dots,(73,17,1.7,25),"Mean marker expression\nScaled per marker",ticks=[0,1],orientation="vertical")
    leg=axes(f,71,53,10,15);leg.set_axis_off();leg.set(xlim=(0,1),ylim=(0,1))
    for y,v in zip([.8,.5,.2],[25,50,75]):leg.scatter([.25],[y],s=.02+3*v/100,color="#aaaaaa");leg.text(.55,y,str(v),fontsize=5.5,va="center")
    text(f,72,72,"Cells with stored\nmarker value > 0 (%)",size=5.5)
    panel(f,"B",87,2)
    regions=cfg["panel_b"]["file_id_order"]
    names=json.loads((ROOT/"configs/figure_04_historical_claude.json").read_text())["regions"]
    for i,fid in enumerate(regions):
        x=86+(i%4)*19.5;y=16+(i//4)*31
        text(f,x+9.5,y-4,names[fid]["name"].replace(" ","\n",1),size=5.5,ha="center")
        a=axes(f,x,y,19,24);spatial(a,ref[ref.File_ID.eq(fid)],size=.13)
    panel(f,"C",3,88)
    comp=csv("figureS4_compositions.csv.gz");colors=cell_colors()
    for i,(m,title) in enumerate(zip(["leiden","flowsom","spatialsort","pixie"],METHODS)):
        x=3+(i%2)*83;y=99+(i//2)*27
        text(f,x+44,y-5,title,size=6.5,weight="bold",ha="center")
        a=axes(f,x+10,y,65,17)
        z=comp[comp.method.eq(m)];tot=z.groupby("cluster").n_cells.sum().sort_values(ascending=False,kind="stable")
        top=tot.head(cfg["panel_c"]["displayed_cluster_limit"].get(m,50)).index
        mat=z.pivot(index="cluster",columns="cell_type",values="n_cells").fillna(0).reindex(index=top,columns=cfg["panel_c"]["cell_type_order"],fill_value=0)
        bottom=np.zeros(len(top))
        for lab in mat.columns:
            vals=mat[lab].to_numpy();a.bar(range(len(top)),vals,bottom=bottom,color=colors[lab],width=.92,edgecolor="white",linewidth=.1);bottom+=vals
        a.set(xticks=[],xlabel="Cluster",ylabel="Cell count",xlim=(-1,len(top)))
        a.yaxis.set_major_locator(MaxNLocator(2, integer=True))
        a.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1000:g}k" if v >= 1000 else f"{v:g}"))
    panel(f,"D",3,155)
    raw=csv("figureS5_fixed_metrics.csv");raw=raw[raw.noise_policy.eq("exclude")&raw.region.ne("ALL")]
    cm=csv("figureS4_cluster_metrics.csv");ct=csv("figureS4_celltype_metrics.csv")
    specs=[("ari","ARI",raw,"#222222"),
           ("ami","AMI",raw,"#222222"),
           ("shannon_index","Shannon index",cm,None),
           ("f1","F1 score",ct,None),("recall","Recall",ct,None),
           ("purity_percent","Cluster purity (%)",cm,None)]
    for i,(metric,title,frame,color) in enumerate(specs):
        x=15+(i%3)*53;y=174+(i//3)*38
        text(f,x+19,y-8,title,size=5.5,ha="center")
        a=axes(f,x,y,38,16)
        keys=["leiden","flowsom","spatialsort","pixie"]
        method_order=rank_labels(keys, frame.groupby("method")[metric].median().reindex(keys),
                                 ascending=metric == "shannon_index")
        method_names=[METHODS[keys.index(m)] for m in method_order]
        vals=[frame[frame.method.eq(m)][metric].to_numpy() for m in method_order]
        a.boxplot(vals,positions=range(4),widths=.6,showfliers=False,patch_artist=True,
                  boxprops={"facecolor":"white","linewidth":.5},medianprops={"color":"black","linewidth":.6},whiskerprops={"linewidth":.5},capprops={"linewidth":.5})
        rng=np.random.default_rng(42)
        for j,m in enumerate(method_order):
            z=frame[frame.method.eq(m)];cs=color if color else z["cell_type" if "cell_type" in z else "majority_label"].map(colors)
            a.scatter(j+rng.uniform(-.12,.12,len(z)),z[metric],c=cs,s=3,alpha=.6,zorder=3,linewidths=0)
        a.set(xticks=range(4),xticklabels=method_names,xlim=(-.5,3.5))
        plt.setp(a.get_xticklabels(),rotation=50,ha="right",rotation_mode="anchor")
    names=["reference_plot_cells.csv.gz","figureS4_marker_summaries.csv","figureS4_compositions.csv.gz","figureS4_cluster_metrics.csv","figureS4_celltype_metrics.csv","figureS5_fixed_metrics.csv"]
    return finish(f,"Figure_S4",out,{**inputs(*names),"configs/figure_s03.yaml":sha(ROOT/"configs/figure_s03.yaml"),"data/frozen/reference47_profiles_20261110/manifest.json":sha(ROOT/"data/frozen/reference47_profiles_20261110/manifest.json")},notes=["Primary clustering diagnostics. Panel A displays all 47 stored marker channels; marker tick labels are thinned for legibility. Panels B–D preserve the same frozen reference/primary-clustering data. D ranks each metric by its median, descending except ascending Shannon index. Suggested manuscript width: 152.4 mm (6 in)."])




def figure_1(out):
    names=["figureS1_archived_metrics.csv","figure1_pooled_f1_changes.csv"]
    m=csv(names[0]);c=csv(names[1]);p=ROOT/"data/frozen/figure_01_descriptive/regional_f1_changes.csv";reg=pd.read_csv(p)
    seg_order=rank_labels(SEG, c.groupby("method").delta_f1.mean().reindex(SEG))
    f=figure(216)
    panel(f,"A",3,2)
    workflow_inputs=add_original_compensation_workflow(f)
    panel(f,"B",3,31)
    a=axes(f,16,42,63,27)
    vals=[]
    for method in seg_order:
        z=m[m.method.eq(method)].pivot(index="region",columns="condition",values="silhouette")
        vals.append((z.after-z.before).to_numpy())
    colors_by_method=dict(zip(SEG,["#90aecb","#efbd86","#a8c59e","#e8a3a3","#c8aac4","#97bfbd"]))
    colors=[colors_by_method[m] for m in seg_order]
    boxes=a.boxplot(vals,positions=range(6),widths=.58,showfliers=False,patch_artist=True,
                    medianprops={"color":"black","linewidth":.6},boxprops={"linewidth":.5},
                    whiskerprops={"linewidth":.5},capprops={"linewidth":.5})
    for i,(v,color) in enumerate(zip(vals,colors)):
        boxes["boxes"][i].set_facecolor(color)
        a.scatter(i+np.linspace(-.07,.07,len(v)),v,s=5,color="#333333",zorder=3)
        a.scatter(i,v.mean(),s=13,marker="D",color=color,edgecolors="black",linewidths=.35,zorder=4)
    a.axhline(0,lw=.5,color="#777777")
    a.set(xticks=range(6),xticklabels=seg_order,ylim=(-.07,.07),yticks=[-.06,-.03,0,.03,.06],ylabel="Δ silhouette score")
    plt.setp(a.get_xticklabels(),rotation=25,ha="right",rotation_mode="anchor")
    panel(f,"C",85,31)
    a=axes(f,99,42,62,27)
    vals=[c[c.method.eq(method)].delta_f1.to_numpy() for method in seg_order]
    a.boxplot(vals,positions=range(6),widths=.58,showfliers=False,patch_artist=True,
              boxprops={"facecolor":"white","edgecolor":"#777777","linewidth":.5},
              medianprops={"color":"black","linewidth":.6},whiskerprops={"linewidth":.5},capprops={"linewidth":.5})
    rng=np.random.default_rng(42);palette=cell_colors()
    for i,method in enumerate(seg_order):
        z=c[c.method.eq(method)]
        a.scatter(i+rng.uniform(-.16,.16,len(z)),z.delta_f1,s=6,c=z.cell_type.map(palette),edgecolors="white",linewidths=.15,zorder=3)
    a.axhline(0,color="#777777",ls="--",lw=.5)
    a.set(xticks=range(6),xticklabels=seg_order,ylim=(-.7,.7),yticks=[-.6,-.3,0,.3,.6],ylabel="ΔF1")
    plt.setp(a.get_xticklabels(),rotation=25,ha="right",rotation_mode="anchor")
    handles=[Line2D([],[],marker="o",color=co,linestyle="",markersize=2.5,label=lab) for lab,co in palette.items()]
    f.legend(handles=handles,loc="upper left",bbox_to_anchor=(.015,.615),ncol=4,fontsize=5.5,
             handlelength=.6,handletextpad=.4,columnspacing=1.8,labelspacing=.3)
    labels=sorted(reg.cell_type.unique())
    displayed=reg[reg.method.isin(["Mesmer","CellposeSAM","CellposeCyto3"])]
    labels=rank_labels(labels, displayed.groupby("cell_type").delta_pp.mean().reindex(labels))
    for i,(method,x,w) in enumerate([("Mesmer",39,36),("CellposeSAM",83,36),("CellposeCyto3",127,34)]):
        panel(f,chr(68+i),3 if i==0 else x-3,109,method,title_x=x+9)
        a=axes(f,x,117,w,76)
        for j,lab in enumerate(labels):
            if j%2==0:a.axhspan(j-.5,j+.5,color="#f4f4f4",zorder=0)
            values=reg[reg.method.eq(method)&reg.cell_type.eq(lab)].delta_pp.to_numpy()
            a.plot([values.min(),values.max()],[j,j],color="#888888",lw=.6,zorder=2)
            a.scatter(values,j+np.linspace(-.1,.1,len(values)),s=6,c="#c4c4c4",edgecolors="#888888",linewidths=.2,zorder=3)
            a.scatter(values.mean(),j,marker="D",s=12,color="black",zorder=4)
            a.text(1.025,j,str(len(values)),transform=a.get_yaxis_transform(),ha="left",va="center",fontsize=5.5)
        a.text(1.025,1.02,"n",transform=a.transAxes,fontsize=5.5,ha="left")
        a.axvline(0,color="#555555",lw=.5);a.set(xlim=(-100,100),ylim=(27.5,-.5),yticks=range(28),yticklabels=labels if i==0 else [""]*28,xticks=[-100,-50,0,50,100],xlabel="F1 change (percentage points)")
        a.spines["left"].set_visible(False);a.tick_params(axis="y",length=0)
    f.legend(handles=[Line2D([],[],marker="o",linestyle="",markersize=3,color="#bbbbbb",label="Individual tissue region"),
                      Line2D([],[],marker="D",linestyle="",markersize=3,color="black",label="Mean regional change"),
                      Line2D([],[],color="#888888",lw=.7,label="Observed regional range")],
             loc="upper center",bbox_to_anchor=(.58,1-202/216),ncol=3,fontsize=5.5,columnspacing=1.1,handlelength=1.1)
    return finish(f,"Figure_1",out,{**workflow_inputs,**inputs(*names),str(p.relative_to(ROOT)):sha(p)},notes=["Panel A retains the original illustrations and arrows. Only declared raster text rectangles are cleared, with larger editable Arial labels placed over them.","Panel B retains the precision archived in the executed notebook. B/C share descending mean pooled cell-type F1-change method order. D–F share descending mean regional F1-change cell-type order across the three displayed methods."])


def figure_s2(out):
    name="figureS2_spatial_cells.csv.gz";d=csv(name);ref=csv("reference_cells.csv.gz")
    r=ref[ref.File_ID.eq("63d000170e475af142f6e8673de5eb0f")].copy()
    # These archived coordinates already match the segmentation orientation.
    f=figure(168)
    lo=np.minimum(d[["x","y"]].min(),r[["x","y"]].min());hi=np.maximum(d[["x","y"]].max(),r[["x","y"]].max())
    def draw(a,z,target,col):
        a.scatter(z.x,z.y,s=.15,color="#d0d0d0",alpha=.35,linewidths=0,rasterized=True)
        v=z[z[col].eq(target)];a.scatter(v.x,v.y,s=.8,color="#1f5269",linewidths=0,rasterized=True)
        a.set(xlim=(lo.x,hi.x),ylim=(hi.y,lo.y));a.set_aspect("equal");a.set_axis_off()
    for i,target in enumerate(["DC","CD8+ T"]):
        y=2+i*83;panel(f,chr(65+i),3,y,"Dendritic cells" if target == "DC" else "CD8+ T cells")
        text(f,21,y+14,"HuBMAP reference\nannotations",size=5.5,ha="center")
        a=axes(f,3,y+23,37,53);draw(a,r,target,"cell_type_update")
        text(f,49,y+33,"Before compensation",size=5.5,rotation=90,ha="center",va="center")
        text(f,49,y+65,"After compensation",size=5.5,rotation=90,ha="center",va="center")
        for j,m in enumerate(["Mesmer","CellposeSAM","CellposeCyto3"]):
            x=56+j*36;text(f,x+15,y+8,m,size=6,weight="bold",ha="center")
            for k,cond in enumerate(["before","after"]):
                a=axes(f,x,y+15+k*32,30,29)
                draw(a,d[d.method.eq(m)&d.condition.eq(cond)],target,"predicted_label")
    return finish(f,"Figure_S2",out,inputs(name,"reference_cells.csv.gz"))




def figure_s3c(out):
    config=json.loads((ROOT/"configs/figure_s05.json").read_text())
    source=ROOT/config["data"]
    assert sha(source)==config["data_sha256"]
    df=pd.read_csv(source)
    f=figure(140)
    panel(f,"C",3,2)
    labels=config["cell_types"]
    labels=rank_labels(labels, df.groupby("cell_type").mean_difference.mean().reindex(labels))
    method_order=rank_labels(SEG, df.groupby("method").mean_difference.mean().reindex(SEG))
    for i,backend in enumerate(config["backends"]):
        x=43+i*59
        text(f,x+25,10,backend,size=6.5,weight="bold",ha="center")
        a=axes(f,x,15,51,84)
        mat=df[df.clustering.eq(backend)].pivot(index="cell_type",columns="method",values="mean_difference").reindex(index=labels,columns=method_order).to_numpy()*100
        assert mat.shape==(28,6) and np.isfinite(mat).all()
        h=heatmap(a,mat,labels if i==0 else [""]*28,method_order,
                  *config["color_limits"],annotate=True,fmt=".0f",size=5.5)
        plt.setp(a.get_xticklabels(),rotation=45,ha="right",rotation_mode="anchor")
    colorbar(f,h,(43,113,110,2.3),config["colorbar_label"],ticks=config["colorbar_ticks"])
    return finish(f,"Figure_S3C",out,{str(source.relative_to(ROOT)):sha(source)},notes=["Both backends share cell-type and method orders ranked by descending mean displayed F1 change."])












def figure_s1(out):
    name="figureS1_archived_metrics.csv";d=csv(name)
    f=figure(139)
    f.legend(handles=[Patch(color="#888780",label="Before REDSEA"),Patch(color="#378ADD",label="After REDSEA")],
             loc="upper center",bbox_to_anchor=(.5,.995),ncol=2,fontsize=6,handlelength=1.1)
    for i,(metric,title) in enumerate([("silhouette","Silhouette score"),
                                       ("davies_bouldin","Davies-Bouldin index"),
                                       ("calinski_harabasz","Calinski-Harabasz index")]):
        y=11+i*41;panel(f,chr(65+i),3,y)
        a=axes(f,17,y+8,144,25)
        after=d[d.condition.eq("after")].groupby("method")[metric].mean().reindex(SEG)
        method_order=rank_labels(SEG, after, ascending=metric == "davies_bouldin")
        for j,m in enumerate(method_order):
            z=d[d.method.eq(m)].pivot(index="region",columns="condition",values=metric).sort_index()
            assert len(z)==8
            a.bar(j-.17,z.before.mean(),width=.32,color="#888780",zorder=2)
            a.bar(j+.17,z.after.mean(),width=.32,color="#378ADD",zorder=2)
            for b,c in zip(z.before,z.after):
                a.plot([j-.17,j+.17],[b,c],lw=.35,color="#aaa9a4",zorder=3)
                a.scatter([j-.17,j+.17],[b,c],color="#222222",s=4,zorder=4)
        a.set(xticks=range(6),xticklabels=method_order,xlim=(-.5,5.5),ylabel=title)
        grid(a)
    return finish(f,"Figure_S1",out,inputs(name),notes=["Metrics retain the four-decimal precision archived in the executed notebook stdout. Method groups are ordered by after-compensation means, descending except ascending Davies–Bouldin index. Before/after pairs remain together."])


def figure_s3a(out):
    name="figureS3_population.csv";d=csv(name);f=figure(84)
    panel(f,"A",3,2)
    a=axes(f,17,12,144,47)
    variants=["directed_5","directed_10","directed_15","mutual_10"]
    colors=["#0072B2","#009E73","#E69F00","#CC79A7"]
    method_order=rank_labels(SEG, d.groupby("method").paired_coverage_of_shared_ids.mean().reindex(SEG))
    for vi,(v,c) in enumerate(zip(variants,colors)):
        for mi,m in enumerate(method_order):
            z=d[d.method.eq(m)&d.variant.eq(v)].sort_values("region")
            vals=z.paired_coverage_of_shared_ids.to_numpy()*100
            assert len(vals)==8
            x=mi+np.linspace(-.28,.28,4)[vi]
            a.scatter(x+np.linspace(-.035,.035,8),vals,s=7,color=c,alpha=.65,zorder=3)
            a.scatter(x,vals.mean(),s=14,marker="D",color=c,edgecolors="black",linewidths=.35,zorder=4)
    a.set(xticks=range(6),xticklabels=method_order,xlim=(-.5,5.5),ylim=(0,103),
          ylabel="Shared objects retained (%)")
    grid(a)
    handles=[Line2D([],[],color=c,marker="o",linestyle="",markersize=3,label=v.replace("_"," ")) for v,c in zip(variants,colors)]
    handles.append(Line2D([],[],color="black",marker="D",markersize=3,linestyle="",label="Regional mean"))
    f.legend(handles=handles,loc="upper center",bbox_to_anchor=(.53,.18),ncol=5,fontsize=5.5,handletextpad=.4,columnspacing=1)
    return finish(f,"Figure_S3A",out,inputs(name),notes=["Segmentation methods ordered by descending mean retention across the displayed population variants."])


def figure_s3b(out):
    names=["figureS3_regional_changes.csv","figureS3_intervals.csv"]
    d=csv(names[0]);intervals=csv(names[1]);f=figure(88)
    method_order=rank_labels(SEG, d.groupby("method").mean_celltype_delta.mean().reindex(SEG))
    panel(f,"B",3,2)
    for i,(backend,c) in enumerate([("Leiden","#0072B2"),("FlowSOM","#D55E00")]):
        x=3+82*i;text(f,x+45,15,backend,size=6.5,weight="bold",ha="center")
        a=axes(f,x+15,24,63,36)
        for j,m in enumerate(method_order):
            z=d[d.method.eq(m)&d.clustering.eq(backend)].sort_values("region")
            vals=z.mean_celltype_delta.to_numpy()*100
            ci=intervals[intervals.method.eq(m)&intervals.clustering.eq(backend)].iloc[0]
            assert len(vals)==8
            a.scatter(j+np.linspace(-.1,.1,8),vals,s=8,color=c,alpha=.72,zorder=3)
            a.plot([j,j],[ci.ci_low*100,ci.ci_high*100],color="black",lw=.6)
            a.scatter(j,vals.mean(),marker="D",color="black",s=12,zorder=4)
        a.axhline(0,color="#888888",lw=.5)
        a.set(xticks=range(6),xticklabels=method_order,xlim=(-.5,5.5),ylim=(-10,10),yticks=[-10,-5,0,5,10])
        plt.setp(a.get_xticklabels(),rotation=35,ha="right",rotation_mode="anchor")
        if i==0:a.set_ylabel("Mean cell-type ΔF1 within region\n(percentage points)")
        grid(a)
    return finish(f,"Figure_S3B",out,inputs(*names),notes=["Both clustering backends share descending mean regional cell-type F1-change method order."])


def figure_s5(out):
    name="figureS5_fixed_metrics.csv"
    fixed=csv(name);f=figure(78)
    panel(f,"A",3,2)
    a=axes(f,23,13,126,43)
    keys=["pixie" if m=="pixie_tiff" else m for m in METHOD_KEYS]
    pooled=fixed[fixed.noise_policy.eq("include") & fixed.region.eq("ALL")].set_index("method")
    method_order=rank_labels(keys, pooled.reindex(keys).purity)
    method_names=[METHODS[keys.index(m)] for m in method_order]
    for i,key in enumerate(method_order):
        c=METHOD_COLORS[keys.index(key)]
        z=fixed[fixed.method.eq(key)&fixed.noise_policy.eq("include")]
        val=z[z.region.eq("ALL")].purity.iloc[0]
        reg=z[~z.region.eq("ALL")].sort_values("region").purity
        assert len(reg)==8
        a.bar(i,val,width=.7,color=c,alpha=.65,zorder=2)
        a.scatter(i+np.linspace(-.16,.16,8),reg,s=10,color="#333333",edgecolors="white",linewidths=.25,zorder=3)
        a.text(i,.035,f"{val:.3f}",ha="center",va="bottom",fontsize=6)
    a.set(xticks=range(4),xticklabels=method_names,ylim=(0,1.1),yticks=[0,.2,.4,.6,.8,1],ylabel="Cluster-majority upper bound\non reference agreement")
    grid(a)
    a.legend(handles=[Patch(color="#8ba0b1",label="Pooled"),Line2D([],[],color="#333333",marker="o",linestyle="",markersize=3,label="Regional")],loc="upper left",fontsize=5.5)
    return finish(f,"Figure_S5",out,inputs(name),notes=["Single-panel primary fixed-partition reference upper bounds sorted by descending pooled value. Original 28 labels including Noise. No shared-marker or cluster-count refitting."])




def figure_slot(out, key):
    """Create a plain pending-result slot; never read annotation tables."""
    out.mkdir(parents=True,exist_ok=True)
    f=figure(48)
    text(f,82.55,10,"Figure "+key,size=11,weight="bold",ha="center")
    text(f,82.55,25,"[[annotation results pending]]",size=12,ha="center")
    text(f,82.55,38,"47-marker primary clustering · annotation outputs required",size=8,ha="center")
    name="Figure_"+key
    paths=[]
    for ext in ("png","svg","pdf"):
        path=out/(name+"."+ext)
        metadata={"CreationDate":None,"ModDate":None} if ext=="pdf" else {"Date":None} if ext=="svg" else {}
        f.savefig(path,dpi=600,facecolor="white",metadata=metadata)
        paths.append(path)
    receipt={"figure":name,"artifact_type":"figure_slot_placeholder","scientific_output":False,
             "status":"annotation_results_pending","annotation_calls":0,"width_mm":165.1,"height_mm":48,
             "minimum_font_pt":8,"minimum_placement_width_mm":103.188,"raster_size_pixels":[3900,1133],
             "inputs":{},"files":{p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in paths},
             "notes":["Plain manuscript figure slot. No annotation results, plots or scientific validation are represented."]}
    from PIL import Image
    with Image.open(out/(name+".png")) as im:receipt["raster_size_pixels"]=list(im.size)
    (out/(name+"_verification.json")).write_text(json.dumps(receipt,indent=2)+"\n")
    plt.close(f)
    return receipt


RENDERERS={"1":figure_1,"2":figure_2,"S1":figure_s1,"S2":figure_s2,"S4":figure_s4,
           "S3A":figure_s3a,"S3B":figure_s3b,"S3C":figure_s3c,"S5":figure_s5}
from render_annotation47_figures import RENDERERS as ANNOTATION47_RENDERERS
RENDERERS.update(ANNOTATION47_RENDERERS)
from render_reviewer47_figures import RENDERERS as REVIEWER47_RENDERERS
RENDERERS.update(REVIEWER47_RENDERERS)



def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"figures/publication")
    p.add_argument("--figures",nargs="+",choices=list(RENDERERS),default=list(RENDERERS))
    args=p.parse_args();receipts=[]
    for name in args.figures:receipts.append(RENDERERS[name](args.output))
    receipts=[json.loads(p.read_text()) for p in sorted(args.output.glob("Figure_*_verification.json"))]
    (args.output/"render_receipts.json").write_text(json.dumps(receipts,indent=2)+"\n")


if __name__=="__main__":main()
