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

DATA = ROOT / "data/frozen/publication_design"
SEG = ["Mesmer", "CellposeCyto3", "CellposeSAM", "CellSAM", "InstanSeg", "MicroSAM"]
COMPONENT_NAMES = ["Reference agreement", "Gap to maximum agreement",
                   "Within-cluster minority-label fraction"]
COMPONENT_COLORS = ["#2A6F5B", "#D9852B", "#D9D9D9"]


def csv(name, **kw):
    manifest = json.loads((DATA / "manifest.json").read_text())
    expected = manifest["files"][name]["sha256"]
    if sha(DATA / name) != expected:
        raise ValueError(f"Frozen publication input changed: {name}")
    return pd.read_csv(DATA/name, **kw)


def inputs(*names):
    return {str((DATA/n).relative_to(ROOT)):sha(DATA/n) for n in names}


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
    f=figure(290)
    panel(f,"A",3,2)
    workflow_inputs=add_workflow(f,"2A")
    panel(f,"B",3,39)
    a=axes(f,15,45,96,9)
    counts=ref.cell_type_update.value_counts().drop("Noise").sort_values(ascending=False)
    a.bar(range(27),counts,color=[cell_colors()[s] for s in counts.index],width=.88)
    a.set(xticks=range(27),xticklabels=counts.index,yticks=[0,15000,30000],yticklabels=["0","15k","30k"],ylabel="Cell count",xlim=(-.6,26.6))
    plt.setp(a.get_xticklabels(),rotation=90)
    panel(f,"C",115,39,"Reference\nannotations")
    a=axes(f,126,45,30,30);r=ref[ref.File_ID.eq("8da8f27977d946b8c912d42c8827b55c")].copy()
    spatial(a,r,size=.2)
    panel(f,"D",3,82)
    zoom=cfg["panel_d"]["style"]["zoom"]
    for i,(key,title) in enumerate([("cell_type_update","Reference\nannotations")]+list(zip(["leiden","flowsom","spatialsort","pixie"],METHODS))):
        x=11+i*31
        text(f,x+11.5,82,title,size=5.5,ha="center")
        if key=="cell_type_update":labels=d.cell_type_update
        else:
            mapping=d.groupby(key,sort=True).cell_type_update.agg(lambda s:s.value_counts(sort=True).index[0])
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
    rcfg=json.loads((ROOT/"configs/figure_04_historical_claude.json").read_text())["regions"]
    for i,(letter,key,title,ylab) in enumerate([("E","weighted_f1","Regional weighted F1","Weighted F1"),("G","cluster_purity","Regional cell-count-weighted cluster purity","Cluster purity")]):
        x=3+i*83;panel(f,letter,x,121,title)
        a=axes(f,x+12,129,63,14)
        values=[region[region.method.eq(m)].sort_values("region")[key].to_numpy() for m in METHODS]
        a.boxplot(values,positions=range(4),widths=.48,showfliers=False,patch_artist=True,
                  boxprops={"facecolor":"#e5e7eb","linewidth":.5},medianprops={"color":"black","linewidth":.6},whiskerprops={"linewidth":.5},capprops={"linewidth":.5})
        for j,m in enumerate(METHODS):
            z=region[region.method.eq(m)].sort_values("region")
            a.scatter(j+np.linspace(-.08,.08,8),z[key],s=7,c=z.region.map({k:v["color"] for k,v in rcfg.items()}),zorder=3)
        a.set(xticks=range(4),xticklabels=METHODS,ylim=(.3,.9),yticks=[.3,.5,.7,.9],ylabel=ylab);grid(a)
    norm=cfg["four_llm_consensus"]["truth_normalization_map"]
    nref=ref.cell_type_update.replace(norm).value_counts().to_dict()
    rows=csv("figure2_f1.csv").cell_type.tolist()
    for i,(letter,filename,title,scale) in enumerate([("F","figure2_f1.csv","Cell-type F1",1),("H","figure2_recall.csv","Cell-type recall (%)",100)]):
        x=3+i*83;panel(f,letter,x,150,title)
        matrix=csv(filename).set_index("cell_type").reindex(rows)[METHODS].to_numpy()*scale
        count_heatmap(f,matrix,rows,METHODS,x+27,163,38,39,nref,limits=(0,scale),rotation=55)
    panel(f,"I",3,218,"CD8+ T groups from four-model modal annotations")
    d=csv("figure2_marker_summaries.csv");markers=cfg["panel_i"]["marker_order"]
    a=axes(f,27,231,134,8)
    for i,m in enumerate(METHODS):
        z=d[d.method.eq(m)].set_index("marker").reindex(markers)
        dots=a.scatter(np.arange(45),np.repeat(i,45),s=.03+8*z.fraction_cells_pct/100,c=z.scaled_mean_expression,cmap="Reds",vmin=0,vmax=1,edgecolors="black",linewidths=.2)
    a.set(xticks=range(45),xticklabels=markers,yticks=range(4),yticklabels=[f"{m} (n={int(d[d.method.eq(m)].n_selected_cells.iloc[0]):,})" for m in METHODS],xlim=(-.7,44.7),ylim=(3.5,-.5))
    plt.setp(a.get_xticklabels(),rotation=45,ha="right",rotation_mode="anchor")
    for edge in a.spines.values():edge.set_visible(True);edge.set_linewidth(.4)
    a.tick_params(length=0)
    text(f,28,224,"Stored marker value > 0 (%)",size=5.5)
    leg=axes(f,73,223,29,3);leg.set_axis_off()
    for x,v in zip([.1,.45,.8],[0,50,100]):
        leg.scatter([x],[.6],s=.03+8*v/100,color="#999999",edgecolors="black",linewidths=.2)
        leg.text(x,.05,str(v),fontsize=5.5,ha="center",va="top",transform=leg.transAxes)
    leg.set(xlim=(0,1),ylim=(0,1))
    text(f,117,220,"Mean stored marker expression\nMin-max scaled per marker",size=5.5)
    colorbar(f,dots,(121,225,34,1.3),None,ticks=[0,1])
    panel(f,"J",3,254,"Post-hoc selected spatial examples")
    examples=csv("figure2_spatial_examples.csv");windows=csv("figure2_spatial_windows.csv")
    titles=["Tissue region","Reference\nannotations"]+METHODS
    for j,title in enumerate(titles):text(f,19+j*25,259,title,size=5.5,ha="center")
    for row,example in enumerate(["Low reference agreement","High reference agreement"]):
        z=examples[examples.example.eq(example)];w=windows[windows.example.eq(example)].iloc[0]
        text(f,4.2,271+row*12,f"{'Low' if row==0 else 'High'}\nn = {len(z):,}",size=5.5,ha="center",va="center",rotation=90)
        for j,label in enumerate([None,"truth_label"]+METHODS):
            a=axes(f,9+j*25,266+row*12,21,10.5)
            if j==0:
                whole=ref[ref.File_ID.eq(w.file_id)].copy();whole["truth_label"]=whole.cell_type_update.replace(norm)
                spatial(a,whole,label="truth_label",size=.09,normalize=True)
                a.add_patch(Rectangle((w.x0,w.y0),w.x1-w.x0,w.y1-w.y0,fill=False,ec="black",lw=.4))
            else:
                spatial(a,z,label=label,size=.4,normalize=True);a.set(xlim=(w.x0,w.x1),ylim=(w.y0,w.y1))
            a.invert_yaxis()
            for edge in a.spines.values():edge.set_visible(True);edge.set_color("#9ca3af");edge.set_linewidth(.35)
    # This dense figure has a small placement margin when fitted to one page.
    for t in f.findobj(Text):
        if t.get_fontsize()<6.6:t.set_fontsize(6.6)
        if t.get_text() in list("ABCDEFGHIJ") and t.get_weight()=="bold":t.set_fontsize(10.3)
    names=["reference_plot_cells.csv.gz","umap_coordinates.csv.gz","figure2_regional_metrics.csv","figure2_f1.csv","figure2_recall.csv","figure2_marker_summaries.csv","figure2_spatial_examples.csv","figure2_spatial_windows.csv"]
    return finish(f,"Figure_2",out,{**inputs(*names),**workflow_inputs},notes=["Original BioRender workflow restored with editable text. Place at least 125.076 mm wide. Suggested manuscript width: 128.27 mm (5.05 in)."])


def figure_s4(out):
    import yaml
    cfg=yaml.safe_load((ROOT/"configs/figure_s03.yaml").read_text())
    ref=csv("reference_plot_cells.csv.gz");d=csv("figureS4_marker_summaries.csv")
    f=figure(239)
    panel(f,"A",3,2,"Protein expression by reference cell type")
    labs=cfg["panel_a"]["cell_type_order"];markers=cfg["panel_a"]["marker_order"]
    a=axes(f,29,12,40,58)
    for i,lab in enumerate(labs):
        z=d[d.cell_type.eq(lab)].set_index("marker").reindex(markers)
        dots=a.scatter(range(45),[i]*45,s=.02+3*z.fraction_cells_pct/100,c=z.scaled_mean_expression,cmap="Reds",vmin=0,vmax=1,linewidths=.1,edgecolors="#8c8c8c")
    a.set(yticks=range(27),yticklabels=labs,xticks=range(0,45,3),xticklabels=markers[::3],xlim=(-1,45),ylim=(26.5,-.5))
    plt.setp(a.get_xticklabels(),rotation=90)
    a.tick_params(length=0)
    for edge in a.spines.values():edge.set_visible(False)
    colorbar(f,dots,(73,17,1.7,25),"Mean marker expression\nScaled per marker",ticks=[0,1],orientation="vertical")
    leg=axes(f,71,53,10,15);leg.set_axis_off();leg.set(xlim=(0,1),ylim=(0,1))
    for y,v in zip([.8,.5,.2],[25,50,75]):leg.scatter([.25],[y],s=.02+3*v/100,color="#aaaaaa");leg.text(.55,y,str(v),fontsize=5.5,va="center")
    text(f,72,72,"Cells with stored\nmarker value > 0 (%)",size=5.5)
    panel(f,"B",87,2,"Reference annotations across tissue regions")
    regions=cfg["panel_b"]["file_id_order"]
    names=json.loads((ROOT/"configs/figure_04_historical_claude.json").read_text())["regions"]
    for i,fid in enumerate(regions):
        x=86+(i%4)*19.5;y=16+(i//4)*31
        text(f,x+9.5,y-4,names[fid]["name"].replace(" ","\n",1),size=5.5,ha="center")
        a=axes(f,x,y,19,24);spatial(a,ref[ref.File_ID.eq(fid)],size=.13)
    panel(f,"C",3,88,"Cluster composition by method")
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
    panel(f,"D",3,155,"FlowSOM cluster-count sweep")
    a=axes(f,14,168,32,44)
    p=ROOT/"data/frozen/figure_s03/flowsom_k_sweep_purity.csv";s=pd.read_csv(p)
    # The pinned historical table carries the original exploratory sweep.
    a.plot(s.iloc[:,0],s.iloc[:,2]*100,"o-",color="black",ms=2.5,lw=.7)
    a.set(xlabel="FlowSOM cluster count",ylabel="Purity (%)",xticks=[0,100,200,300]);grid(a)
    panel(f,"E",53,155,"Clustering metric distributions")
    text(f,61,160,"ARI / AMI: imaged tissue region (n = 8)",size=5.5)
    raw=csv("figureS5_fixed_metrics.csv");raw=raw[raw.noise_policy.eq("exclude")&raw.region.ne("ALL")]
    cm=csv("figureS4_cluster_metrics.csv");ct=csv("figureS4_celltype_metrics.csv")
    specs=[("ari","Adjusted Rand\nindex (ARI)",raw,"#222222"),
           ("ami","Adjusted mutual\ninformation (AMI)",raw,"#222222"),
           ("shannon_index","Within-cluster reference diversity\nShannon index",cm,None),
           ("f1","F1 score",ct,None),("recall","Recall",ct,None),
           ("purity_percent","Cluster purity (%)\nCells sharing majority reference type",cm,None)]
    for i,(metric,title,frame,color) in enumerate(specs):
        x=63+(i%3)*36;y=174+(i//3)*38
        text(f,x+12.5,y-8,title,size=5.5,ha="center")
        a=axes(f,x,y,25,16)
        vals=[frame[frame.method.eq(m)][metric].to_numpy() for m in ["leiden","flowsom","spatialsort","pixie"]]
        a.boxplot(vals,positions=range(4),widths=.6,showfliers=False,patch_artist=True,
                  boxprops={"facecolor":"white","linewidth":.5},medianprops={"color":"black","linewidth":.6},whiskerprops={"linewidth":.5},capprops={"linewidth":.5})
        rng=np.random.default_rng(42)
        for j,m in enumerate(["leiden","flowsom","spatialsort","pixie"]):
            z=frame[frame.method.eq(m)];cs=color if color else z["cell_type" if "cell_type" in z else "majority_label"].map(colors)
            a.scatter(j+rng.uniform(-.12,.12,len(z)),z[metric],c=cs,s=3,alpha=.6,zorder=3,linewidths=0)
        a.set(xticks=range(4),xticklabels=METHODS,xlim=(-.5,3.5))
        plt.setp(a.get_xticklabels(),rotation=50,ha="right",rotation_mode="anchor")
    names=["reference_plot_cells.csv.gz","figureS4_marker_summaries.csv","figureS4_compositions.csv.gz","figureS4_cluster_metrics.csv","figureS4_celltype_metrics.csv","figureS5_fixed_metrics.csv"]
    return finish(f,"Figure_S4",out,{**inputs(*names),str(p.relative_to(ROOT)):sha(p)},notes=["Suggested manuscript width: 152.4 mm (6 in), preserving a minimum of 5.077 pt."])


def figure_3(out):
    d=csv("figure3_agreement.csv");ct=csv("figure3_celltype_agreement.csv")
    selected=csv("figure3_celltype_selected.csv").query("truth_label!='Noise'")
    ref=csv("reference_plot_cells.csv.gz")
    f=figure(244)
    panel(f,"A",3,2)
    workflow_inputs=add_workflow(f,"3A")
    # Figure 3A follows the updated live-document version, not the earlier
    # branch diagram that distinguished original prompts from later exports.
    for i,(letter,value,title,limits) in enumerate([
        ("B","agreement_percent","Cell-level reference\nagreement (%)",(20,65)),
        ("C","percent_of_upper_bound","Reference agreement\n% of cluster-majority\nupper bound",(40,100))]):
        px=3+i*54;panel(f,letter,px,41,title)
        a=axes(f,px+13,57,29,31)
        mat=d.pivot(index="model",columns="method",values=value).reindex(index=MODEL_KEYS,columns=METHOD_KEYS).to_numpy()
        h=heatmap(a,mat,MODELS,METHODS,*limits,annotate=True,fmt=".1f",size=6)
        plt.setp(a.get_xticklabels(),rotation=55,ha="right",rotation_mode="anchor")
        colorbar(f,h,(px+44,57,1.7,31),None,ticks=[limits[0],sum(limits)/2,limits[1]],orientation="vertical")
    panel(f,"D",112,41,"Cell-type reference\nagreement (%)")
    matrix=ct.pivot(index="cell_type",columns="model",values="agreement_percent").reindex(columns=MODEL_KEYS)
    rows=matrix.mean(axis=1).sort_values(ascending=False,kind="stable").index.tolist()
    nref=ct.groupby("cell_type").reference_cells.first().to_dict()
    count_heatmap(f,matrix.reindex(rows).to_numpy(),rows,MODELS,137,58,20,37,nref,rotation=65)
    panel(f,"E",3,116,"Reference-informed selection\nafter prediction")
    emat=selected.pivot(index="truth_label",columns="llm",values="exact_cell_accuracy").reindex(columns=MODEL_KEYS)*100
    erows=emat.mean(axis=1).sort_values(ascending=False,kind="stable").index.tolist()
    text(f,30,124,"Cell-type reference agreement (%)",size=5.5)
    count_heatmap(f,emat.reindex(erows).to_numpy(),erows,MODELS,30,135,23,37,nref,rotation=65)
    for i,(letter,name,value,y,subtitle) in enumerate([
        ("F","figure3_cell_weighted_selection.csv","exact_cell_accuracy",116,"Cells weighted equally"),
        ("G","figure3_cluster_weighted_selection.csv","cluster_balanced_exact_cell_accuracy",160,"Clusters weighted equally")]):
        panel(f,letter,68,y,"Reference-informed selection after prediction\n"+subtitle)
        a=axes(f,82,y+17,79,18);z=csv(name)
        for j,(model,color,label) in enumerate(zip(MODEL_KEYS,MODEL_COLORS,MODELS)):
            vals=z[z.llm.eq(model)].set_index("clustering_method").reindex(METHOD_KEYS)[value]*100
            a.bar(np.arange(4)+(j-1.5)*.18,vals,width=.18,color=color,edgecolor="black",linewidth=.35,label=label)
        a.set(xticks=range(4),xticklabels=METHODS,ylim=(0,90),yticks=[0,40,80],ylabel="Reference agreement (%)")
        grid(a)
    f.legend(handles=[Patch(color=c,label=l) for c,l in zip(MODEL_COLORS,MODELS)],loc="upper center",bbox_to_anchor=(.72,1-124/244),ncol=4,fontsize=5.5,handlelength=.9,columnspacing=1)
    panel(f,"H",3,203,"Spatial cell-type maps")
    examples=csv("figure3_spatial_examples.csv.gz");windows=csv("figure3_spatial_windows.csv")
    con=pd.read_csv(ROOT/"data/frozen/v3_k300_assignments/panel_i_j_four_llm_consensus.csv.gz")
    examples=examples.merge(con[["File_ID","ID","leiden_consensus"]],on=["File_ID","ID"],validate="one_to_one")
    titles=["Tissue region","Reference\nannotations"]+MODELS+["Most frequent\npredicted cell-type\nlabel"]
    for j,title in enumerate(titles):text(f,20+j*22,208,title,size=5.5,ha="center")
    normal={"Epithelial":"Enterocyte","CD66+ Epithelial":"CD66+ Enterocyte","MUC1+ Epithelial":"MUC1+ Enterocyte","CD57+ Epithelial":"Enterocyte","ITLN+ Epithelial":"Goblet","TA":"Cycling TA","CD4+ T":"CD4+ T cell","Stromal":"Stroma","PDPN+ Stromal":"Lymphatic","CD36 high Endothelial":"Endothelial","CD36 low Endothelial":"Endothelial","CD49a+ Smooth muscle":"Smooth muscle","Paneth":"Neuroendocrine","M1 Macrophage":"M2 Macrophage","NK":"CD7+ Immune"}
    for row,example in enumerate(["low_agreement","high_agreement"]):
        z=examples[examples.example.eq(example)];w=windows[windows.region.eq(example)].iloc[0]
        text(f,3,220+row*13.5,"Low reference\nagreement" if row==0 else "High reference\nagreement",size=5.5,ha="center",va="center",rotation=90)
        for j,label in enumerate([None,"truth_normalized"]+["leiden__"+m for m in MODEL_KEYS]+["leiden_consensus"]):
            a=axes(f,10+j*22,216+row*13.5,20,11.5)
            if j==0:
                whole=ref[ref.File_ID.eq(w.file_id)].copy();whole["truth_normalized"]=whole.cell_type_update.replace(normal)
                spatial(a,whole,label="truth_normalized",size=.09,normalize=True)
                a.add_patch(Rectangle((w.window_x_min,w.window_y_min),w.window_x_max-w.window_x_min,w.window_y_max-w.window_y_min,fill=False,ec="black",lw=.4))
            else:
                spatial(a,z,label=label,size=.4,normalize=True)
                a.set(xlim=(w.window_x_min,w.window_x_max),ylim=(w.window_y_min,w.window_y_max))
            a.invert_yaxis()
            for edge in a.spines.values():edge.set_visible(True);edge.set_color("#9ca3af");edge.set_linewidth(.35)
    names=["figure3_agreement.csv","figure3_celltype_agreement.csv","figure3_celltype_selected.csv","figure3_cell_weighted_selection.csv","figure3_cluster_weighted_selection.csv","figure3_spatial_examples.csv.gz","figure3_spatial_windows.csv","reference_plot_cells.csv.gz"]
    return finish(f,"Figure_3",out,{**inputs(*names),**workflow_inputs},notes=["Figure 3A follows the live-document update exported on 2026-10-31.","Figure 3E heading corrected with author approval to describe its existing reference-selected values.","Suggested manuscript width: 152.4 mm (6 in), preserving a minimum of 5.077 pt."])


def figure_1(out):
    names=["figureS1_archived_metrics.csv","figure1_pooled_f1_changes.csv"]
    m=csv(names[0]);c=csv(names[1]);p=ROOT/"data/frozen/figure_01_descriptive/regional_f1_changes.csv";reg=pd.read_csv(p)
    f=figure(216)
    panel(f,"A",3,2)
    flow(f,["Multiplexed tissue images\nTIF mask files\nMarker channel list", "REDSEA\ncompensation",
            "Merge regions\nBefore / after REDSEA", "Data\npreprocessing", "Leiden clustering\nResolution 1.5",
            "Paired clustered\nH5AD files"],8,17,gap=2,size=5.5)
    panel(f,"B",3,31,"Change in silhouette score\nafter compensation")
    a=axes(f,16,42,63,27)
    vals=[]
    for method in SEG:
        z=m[m.method.eq(method)].pivot(index="region",columns="condition",values="silhouette")
        vals.append((z.after-z.before).to_numpy())
    colors=["#90aecb","#efbd86","#a8c59e","#e8a3a3","#c8aac4","#97bfbd"]
    boxes=a.boxplot(vals,positions=range(6),widths=.58,showfliers=False,patch_artist=True,
                    medianprops={"color":"black","linewidth":.6},boxprops={"linewidth":.5},
                    whiskerprops={"linewidth":.5},capprops={"linewidth":.5})
    for i,(v,color) in enumerate(zip(vals,colors)):
        boxes["boxes"][i].set_facecolor(color)
        a.scatter(i+np.linspace(-.07,.07,len(v)),v,s=5,color="#333333",zorder=3)
        a.scatter(i,v.mean(),s=13,marker="D",color=color,edgecolors="black",linewidths=.35,zorder=4)
    a.axhline(0,lw=.5,color="#777777")
    a.set(xticks=range(6),xticklabels=SEG,ylim=(-.07,.07),yticks=[-.06,-.03,0,.03,.06],ylabel="Δ silhouette score")
    plt.setp(a.get_xticklabels(),rotation=25,ha="right",rotation_mode="anchor")
    panel(f,"C",85,31,"Change in cell-type F1 score\nafter compensation")
    a=axes(f,99,42,62,27)
    vals=[c[c.method.eq(method)].delta_f1.to_numpy() for method in SEG]
    a.boxplot(vals,positions=range(6),widths=.58,showfliers=False,patch_artist=True,
              boxprops={"facecolor":"white","edgecolor":"#777777","linewidth":.5},
              medianprops={"color":"black","linewidth":.6},whiskerprops={"linewidth":.5},capprops={"linewidth":.5})
    rng=np.random.default_rng(42);palette=cell_colors()
    for i,method in enumerate(SEG):
        z=c[c.method.eq(method)]
        a.scatter(i+rng.uniform(-.16,.16,len(z)),z.delta_f1,s=6,c=z.cell_type.map(palette),edgecolors="white",linewidths=.15,zorder=3)
    a.axhline(0,color="#777777",ls="--",lw=.5)
    a.set(xticks=range(6),xticklabels=SEG,ylim=(-.7,.7),yticks=[-.6,-.3,0,.3,.6],ylabel="ΔF1 (after minus before)")
    plt.setp(a.get_xticklabels(),rotation=25,ha="right",rotation_mode="anchor")
    handles=[Line2D([],[],marker="o",color=co,linestyle="",markersize=2.5,label=lab) for lab,co in palette.items()]
    f.legend(handles=handles,loc="upper left",bbox_to_anchor=(.015,.615),ncol=4,fontsize=5.5,
             handlelength=.6,handletextpad=.4,columnspacing=1.8,labelspacing=.3)
    labels=sorted(reg.cell_type.unique())
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
    text(f,3,212,"After minus before compensation. B004 tissue regions are subsamples of one donor.",size=5.5)
    return finish(f,"Figure_1",out,{**inputs(*names),str(p.relative_to(ROOT)):sha(p)},notes=["Panel B retains the precision archived in the executed notebook."])


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
        y=2+i*83;panel(f,chr(65+i),3,y,f"{target}: B004-A-004")
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


def figure_s6(out):
    name="figure4_confusion.csv";counts=csv(name,index_col=0)
    path=ROOT/"data/frozen/leiden_claude_diagnostic_identity/cluster_counts.csv";d=pd.read_csv(path)
    f=figure(223)
    panel(f,"A",3,2)
    for i,title in enumerate(["Counts","Row-normalized fraction"]):
        x=3+i*80;text(f,x+44,8,title,size=6.5,weight="bold",ha="center")
        a=axes(f,x+24,15,45,45)
        mat=counts.to_numpy().astype(float)
        if i:mat=mat/mat.sum(axis=1,keepdims=True)
        h=heatmap(a,mat,counts.index,counts.columns,0,float(mat.max()) if i==0 else 1)
        plt.setp(a.get_xticklabels(),rotation=90)
        a.set_xlabel("Predicted (Claude on Leiden clusters)")
        a.set_ylabel("Reference cell type")
        colorbar(f,h,(x+71,15,2,45),"Cells" if i==0 else "Fraction",orientation="vertical")
    panel(f,"B",3,89,"Cluster-majority diagnostic")
    f.legend(handles=[Patch(color=c,label=l) for c,l in zip(COMPONENT_COLORS,COMPONENT_NAMES)],loc="upper center",bbox_to_anchor=(.5,1-97/223),ncol=3,fontsize=5.5,columnspacing=1.3,handlelength=.8)
    text(f,3,104,"Maximum agreement assigns each fixed cluster its majority reference label.",size=5.5)
    d["bound_fraction"]=d.historical_21_bound_cells/d.n_cells
    d=d.sort_values("bound_fraction",ascending=False,kind="stable").reset_index(drop=True)
    assert len(d)==300
    for i in range(4):
        z=d.iloc[i*75:(i+1)*75];a=axes(f,22+i*41,113,16,99)
        vals=np.stack([z.historical_21_direct_matches,z.historical_21_bound_cells-z.historical_21_direct_matches,z.n_cells-z.historical_21_bound_cells],axis=1)/z.n_cells.to_numpy()[:,None]
        left=np.zeros(75)
        for k,c in enumerate(COMPONENT_COLORS):
            a.barh(range(75),vals[:,k],left=left,color=c,height=.86,linewidth=0);left+=vals[:,k]
        ticks=sorted(set(list(range(0,75,7))+[74]))
        if i==0:
            # Preserve the annotated pure-cluster example in the manuscript.
            ticks=[int(np.flatnonzero(z.cluster.eq("49::0"))[0]) if j==7 else j for j in ticks]
        labels=[f"Cluster {z.iloc[j].cluster.replace('::','-')}\n- {z.iloc[j].historical_21_majority_label}" for j in ticks]
        a.set(yticks=ticks,yticklabels=labels,ylim=(75.5,-1.5),xlim=(0,1),xticks=[0,.5,1],xlabel="Fraction")
        a.tick_params(axis="y",length=0,pad=1.5)
        a.spines["left"].set_visible(False);a.xaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    return finish(f,"Figure_S6",out,{**inputs(name),str(path.relative_to(ROOT)):sha(path)})


def figure_s3c(out):
    config=json.loads((ROOT/"configs/figure_s05.json").read_text())
    source=ROOT/config["data"]
    assert sha(source)==config["data_sha256"]
    df=pd.read_csv(source)
    f=figure(140)
    panel(f,"C",3,2,"Cell-type compensation changes on shared objects")
    labels=config["cell_types"]
    for i,backend in enumerate(config["backends"]):
        x=43+i*59
        text(f,x+25,10,backend,size=6.5,weight="bold",ha="center")
        a=axes(f,x,15,51,84)
        mat=df[df.clustering.eq(backend)].pivot(index="cell_type",columns="method",values="mean_difference").reindex(index=labels,columns=SEG).to_numpy()*100
        assert mat.shape==(28,6) and np.isfinite(mat).all()
        h=heatmap(a,mat,labels if i==0 else [""]*28,SEG,
                  *config["color_limits"],annotate=True,fmt=".0f",size=5.5)
        plt.setp(a.get_xticklabels(),rotation=45,ha="right",rotation_mode="anchor")
    colorbar(f,h,(43,113,110,2.3),config["colorbar_label"],ticks=config["colorbar_ticks"])
    for i,note in enumerate(config["footnotes"]):
        text(f,3,127+i*4,note,size=5.5)
    return finish(f,"Figure_S3C",out,{str(source.relative_to(ROOT)):sha(source)})


def figure_s7(out):
    p=ROOT/"data/frozen/leiden_claude_diagnostic_identity/cluster_counts.csv"
    d=pd.read_csv(p);n=d.n_cells.sum();assert n==220082
    f=figure(67)
    a=axes(f,61,5,100,34)
    labels=["21-label benchmark\n(harmonized reference)","Original 28-label reference\n(vocabulary mismatch diagnostic)"]
    for i,vocab in enumerate(["historical_21","original_28"]):
        direct=d[vocab+"_direct_matches"].sum()
        bound=d[vocab+"_bound_cells"].sum()
        counts=[direct,n-bound,bound-direct]
        left=0.
        for count,color in zip(counts,[COMPONENT_COLORS[j] for j in [0,2,1]]):
            v=count/n
            a.barh(i,v,left=left,height=.52,color=color,edgecolor="white",linewidth=.6)
            a.text(left+v/2,i,f"{v:.2%}",ha="center",va="center",fontsize=6,
                   color="white" if color==COMPONENT_COLORS[0] else "black")
            left+=v
    a.set(yticks=[0,1],yticklabels=labels,xlim=(0,1),ylim=(1.65,-.65),
          xlabel="Fraction of 220,082 cells, including Noise")
    a.set_xticks(np.arange(0,1.01,.2))
    f.legend(handles=[Patch(color=COMPONENT_COLORS[j],label=COMPONENT_NAMES[j]) for j in [0,2,1]],
             loc="upper center",bbox_to_anchor=(.5,.28),ncol=3,fontsize=5.5,
             handlelength=1,handletextpad=.5,columnspacing=1.4)
    text(f,3,55,"Maximum agreement assigns each fixed cluster its majority reference label.",size=5.5)
    text(f,3,60,"The raw 28-label row is a vocabulary mismatch diagnostic. Minority-label matches are retained.",size=5.5)
    text(f,3,64,"Archived responses identify Claude Opus 5.",size=5.5)
    return finish(f,"Figure_S7",out,{str(p.relative_to(ROOT)):sha(p)})


def figure_s8(out):
    cfg=json.loads((ROOT/"configs/figure_s07.json").read_text());p=ROOT/cfg["data"]
    assert sha(p)==cfg["data_sha256"]
    d=pd.read_csv(p);f=figure(90)
    for i,(arm,title,subtitle) in enumerate(zip(cfg["arms"],cfg["condition_labels"],cfg["condition_subtitles"])):
        x=3+i*81
        panel(f,chr(65+i),x,2,title)
        text(f,x+8,7.5,subtitle,size=5.5)
        a=axes(f,x+19,15,56,50)
        mat=d[d.arm.eq(arm)].pivot(index="method",columns="model",values="agreement").reindex(index=METHOD_KEYS,columns=MODEL_KEYS).to_numpy()*100
        assert mat.shape==(4,4)
        h=heatmap(a,mat,METHODS,MODELS,annotate=True,fmt=".1f",size=7)
    colorbar(f,h,(38,75,90,2.5),"Reference agreement (%)",ticks=[0,20,40,60,80,100])
    text(f,3,86,"Mean across the same two B004 test regions. Missing predictions remain errors.",size=5.5)
    return finish(f,"Figure_S8",out,{str(p.relative_to(ROOT)):sha(p)})


def figure_s9(out):
    names=["figureS9_calibration_metrics.csv","figureS9_reliability.csv",
           "figureS9_selective_risk.csv","figureS9_spatial_differences.csv"]
    m=csv(names[0]);pool=m[m.region.eq("POOLED")]
    wide=pool.pivot(index=["method","model","arm"],columns="probability",values="brier")
    assert len(wide)==32
    f=figure(127)
    panel(f,"A",3,2,"Probability assessment\nacross 32 conditions")
    a=axes(f,14,14,64,39)
    for k,c,label in zip(METHOD_KEYS,METHOD_COLORS,METHODS):
        z=wide.loc[k];a.scatter(z.raw_vote,z.recalibrated,s=9,color=c,label=label,alpha=.85)
    a.plot([0,1],[0,1],ls="--",color="#888888",lw=.5)
    a.set(xlim=(0,1),ylim=(0,1),xlabel="Raw vote Brier score",ylabel="Recalibrated Brier score")
    a.legend(loc="upper left",markerscale=.8)
    grid(a,axis="both")
    panel(f,"B",87,2,"GPT and Leiden\nmarker-only reliability")
    a=axes(f,100,14,61,39)
    r=csv(names[1]).query("method=='leiden' and model=='gpt' and arm=='marker_only' and probability=='raw_vote'")
    a.plot([0,1],[0,1],ls="--",color="#888888",lw=.5)
    a.scatter(r.mean_probability,r.observed_reference_agreement,
              s=8+40*r.n_cells/r.n_cells.max(),color="#2166ac")
    a.set(xlim=(0,1.02),ylim=(0,1.02),xlabel="Raw modal vote fraction",ylabel="Observed reference agreement")
    a.set_xticks(np.arange(0,1.01,.2));a.set_yticks(np.arange(0,1.01,.2))
    grid(a,axis="both")
    panel(f,"C",3,67,"GPT and Leiden selective risk")
    a=axes(f,14,78,64,39);r=csv(names[2])
    for arm,c,label in [("marker_only","#2166ac","Markers"),("retrieval","#b35806","Reference-assisted")]:
        z=r[r.method.eq("leiden")&r.model.eq("gpt")&r.arm.eq(arm)].sort_values("threshold")
        a.plot(z.coverage*100,z.selective_reference_error*100,"o-",ms=2.5,lw=.7,color=c,label=label)
    a.set(xlim=(0,100),ylim=(0,100),xlabel="Retained cell coverage (%)",ylabel="Reference disagreement (%)")
    a.legend(loc="upper left");grid(a,axis="both")
    panel(f,"D",87,67,"Paired neighborhood-input\ncomparison")
    a=axes(f,100,78,61,39);d=csv(names[3]).query("split=='test'")
    regions=sorted(d.region.unique());assert len(d)==6
    for i,reg in enumerate(regions):
        z=d[d.region.eq(reg)].sort_values("repeat")
        a.scatter(np.arange(3)*.1-.1+i,z.agreement_delta_pp,s=14,color="#2166ac",zorder=3)
    delta=d.groupby("region").agreement_delta_pp.mean().mean()
    a.scatter([2],[delta],marker="D",s=22,color="#b35806",zorder=3)
    a.text(2,delta-.45,f"{delta:+.2f}",ha="center",va="top",fontsize=5.5)
    a.axhline(0,ls="--",lw=.5,color="#888888")
    a.set(xticks=[0,1,2],xticklabels=["Test region 1","Test region 2","Mean"],
          ylabel="Neighborhood minus markers\n(percentage points)",xlim=(-.3,2.3))
    grid(a)
    return finish(f,"Figure_S9",out,inputs(*names))


def figure_s10(out):
    name="figureS10_paired_summary.csv";d=csv(name);assert len(d)==16
    full=["GPT-5.6-Sol","Claude Opus 5","Gemini 3.1 Pro Preview","DeepSeek V4 Pro"]
    f=figure(124);handles=None
    for i,(model,title) in enumerate(zip(MODEL_KEYS,full)):
        x=3+(i%2)*82;y=13+(i//2)*48
        panel(f,chr(65+i),x,y,title)
        a=axes(f,x+19,y+8,59,30)
        z=d[d.model.eq(model)].set_index("method").reindex(METHOD_KEYS)
        p=z.means_agreement_mean.to_numpy()*100;q=z.fractions_agreement_mean.to_numpy()*100
        for j in range(4):a.plot([p[j],q[j]],[j,j],color="#c9d2da",lw=.7,zorder=1)
        h0=a.errorbar(p,np.arange(4)-.06,xerr=z.means_agreement_sd.to_numpy()*100,
                      fmt="o",color="#2864a5",capsize=1.5,markersize=2.6,lw=.7)
        h1=a.errorbar(q,np.arange(4)+.06,xerr=z.fractions_agreement_sd.to_numpy()*100,
                      fmt="s",color="#b55224",capsize=1.5,markersize=2.6,lw=.7)
        if handles is None:handles=[h0,h1]
        a.set(yticks=np.arange(4),yticklabels=METHODS,ylim=(3.5,-.5),xlim=(0,50),xticks=[0,20,40])
        a.set_xlabel("Reference agreement (%)")
        grid(a,axis="x")
    f.legend(handles,["All-marker means","Means plus fractions"],loc="upper center",bbox_to_anchor=(.5,.995),
             ncol=2,fontsize=6,handlelength=1.5)
    text(f,3,114,"Mean ± run SD, 3 repeats and 2 B004 test regions.",size=5.5)
    text(f,3,119,"28 labels. Missing predictions remain errors.",size=5.5)
    return finish(f,"Figure_S10",out,inputs(name))


def figure_5(out):
    name="figure5_donor_transfer.csv";d=csv(name)
    f=figure(166)
    lim=max(10,float(d[d.donor.isin(["B005","B006"])].retrieval_minus_marker_pp.abs().max()))
    method_labels=["Leiden","FlowSOM†","SpatialSort","PIXIE‡"]
    # Preserve the symmetric change scale of the current four-panel figure.
    for i,donor in enumerate(["B005","B006"]):
        x=3+81*i
        panel(f,chr(65+i),x,2,f"{donor}: change after adding\nlabeled reference profiles\nPercentage points")
        a=axes(f,x+18,17,53,43)
        mat=d[d.donor.eq(donor)].pivot(index="method",columns="model",values="retrieval_minus_marker_pp").reindex(index=METHOD_KEYS,columns=MODEL_KEYS)
        h=heatmap(a,mat,method_labels,MODELS,-lim,lim,annotate=True,fmt="+.1f",size=7)
    colorbar(f,h,(51,67,64,2.5),"Change in reference agreement (percentage points)",ticks=[-lim,0,lim])
    for i,(metric,title) in enumerate([("retrieval_agreement","Mean reference agreement\nacross B005 and B006 (%)"),("retrieval_macro_f1","Mean 23-class macro-F1\nacross B005 and B006 (%)")]):
        x=3+81*i;panel(f,chr(67+i),x,82,title)
        text(f,x+8,92,"Equal donor weights, with labeled reference profiles",size=5.5)
        a=axes(f,x+18,99,53,43)
        mat=d[d.donor.eq("Equal-donor mean")].pivot(index="method",columns="model",values=metric).reindex(index=METHOD_KEYS,columns=MODEL_KEYS).to_numpy()*100
        assert mat.shape==(4,4) and np.isfinite(mat).all()
        h=heatmap(a,mat,method_labels,MODELS,0,100,annotate=True,size=7)
    colorbar(f,h,(51,149,64,2.5),"Equal-donor mean (%)",ticks=[0,20,40,60,80,100])
    text(f,3,161,"† FlowSOM implementation is described in Methods.  ‡ PIXIE used partial correspondence to public masks.",size=5.5)
    return finish(f,"Figure_5",out,inputs(name))


def figure_s1(out):
    name="figureS1_archived_metrics.csv";d=csv(name)
    f=figure(139)
    f.legend(handles=[Patch(color="#888780",label="Before REDSEA"),Patch(color="#378ADD",label="After REDSEA")],
             loc="upper center",bbox_to_anchor=(.5,.995),ncol=2,fontsize=6,handlelength=1.1)
    for i,(metric,title) in enumerate([("silhouette","Silhouette score"),
                                       ("davies_bouldin","Davies-Bouldin index"),
                                       ("calinski_harabasz","Calinski-Harabasz index")]):
        y=11+i*41;panel(f,chr(65+i),3,y,title)
        a=axes(f,17,y+8,144,25)
        for j,m in enumerate(SEG):
            z=d[d.method.eq(m)].pivot(index="region",columns="condition",values=metric).sort_index()
            assert len(z)==8
            a.bar(j-.17,z.before.mean(),width=.32,color="#888780",zorder=2)
            a.bar(j+.17,z.after.mean(),width=.32,color="#378ADD",zorder=2)
            for b,c in zip(z.before,z.after):
                a.plot([j-.17,j+.17],[b,c],lw=.35,color="#aaa9a4",zorder=3)
                a.scatter([j-.17,j+.17],[b,c],color="#222222",s=4,zorder=4)
        a.set(xticks=range(6),xticklabels=SEG,xlim=(-.5,5.5),ylabel=title)
        grid(a)
    text(f,3,135,"Paired tissue-region observations (n = 8), retained from the historical notebook.",size=5.5)
    return finish(f,"Figure_S1",out,inputs(name),notes=["Metrics retain the four-decimal precision archived in the executed notebook stdout."])


def figure_s3a(out):
    name="figureS3_population.csv";d=csv(name);f=figure(84)
    panel(f,"A",3,2,"Matching sensitivity across segmentation methods")
    a=axes(f,17,12,144,47)
    variants=["directed_5","directed_10","directed_15","mutual_10"]
    colors=["#0072B2","#009E73","#E69F00","#CC79A7"]
    for vi,(v,c) in enumerate(zip(variants,colors)):
        for mi,m in enumerate(SEG):
            z=d[d.method.eq(m)&d.variant.eq(v)].sort_values("region")
            vals=z.paired_coverage_of_shared_ids.to_numpy()*100
            assert len(vals)==8
            x=mi+np.linspace(-.28,.28,4)[vi]
            a.scatter(x+np.linspace(-.035,.035,8),vals,s=7,color=c,alpha=.65,zorder=3)
            a.scatter(x,vals.mean(),s=14,marker="D",color=c,edgecolors="black",linewidths=.35,zorder=4)
    a.set(xticks=range(6),xticklabels=SEG,xlim=(-.5,5.5),ylim=(0,103),
          ylabel="Shared objects retained (%)\n(in both conditions)")
    grid(a)
    handles=[Line2D([],[],color=c,marker="o",linestyle="",markersize=3,label=v.replace("_"," ")) for v,c in zip(variants,colors)]
    handles.append(Line2D([],[],color="black",marker="D",markersize=3,linestyle="",label="Regional mean"))
    f.legend(handles=handles,loc="upper center",bbox_to_anchor=(.53,.18),ncol=5,fontsize=5.5,handletextpad=.4,columnspacing=1)
    text(f,3,75,"Each point represents one tissue region. Distances use source centroid-coordinate units.",size=5.5)
    text(f,3,80,"Mutual matching requires one-to-one links. Upstream segmentation geometries were not independently validated.",size=5.5)
    return finish(f,"Figure_S3A",out,inputs(name))


def figure_s3b(out):
    names=["figureS3_regional_changes.csv","figureS3_intervals.csv"]
    d=csv(names[0]);intervals=csv(names[1]);f=figure(88)
    panel(f,"B",3,2,"Compensation changes on shared objects")
    text(f,11,7,"Directed matching at 10 source centroid-coordinate units",size=5.5)
    for i,(backend,c) in enumerate([("Leiden","#0072B2"),("FlowSOM","#D55E00")]):
        x=3+82*i;text(f,x+45,15,f"{backend} downstream clustering",size=6.5,weight="bold",ha="center")
        a=axes(f,x+15,24,63,36)
        for j,m in enumerate(SEG):
            z=d[d.method.eq(m)&d.clustering.eq(backend)].sort_values("region")
            vals=z.mean_celltype_delta.to_numpy()*100
            ci=intervals[intervals.method.eq(m)&intervals.clustering.eq(backend)].iloc[0]
            assert len(vals)==8
            a.scatter(j+np.linspace(-.1,.1,8),vals,s=8,color=c,alpha=.72,zorder=3)
            a.plot([j,j],[ci.ci_low*100,ci.ci_high*100],color="black",lw=.6)
            a.scatter(j,vals.mean(),marker="D",color="black",s=12,zorder=4)
        a.axhline(0,color="#888888",lw=.5)
        a.set(xticks=range(6),xticklabels=SEG,xlim=(-.5,5.5),ylim=(-10,10),yticks=[-10,-5,0,5,10])
        plt.setp(a.get_xticklabels(),rotation=35,ha="right",rotation_mode="anchor")
        if i==0:a.set_ylabel("Mean cell-type ΔF1 within region\n(percentage points)")
        grid(a)
    text(f,3,78,"Points: all regions. Diamonds: regional mean. Bars: descriptive 95% regional-bootstrap interval.",size=5.5)
    text(f,3,83,"One donor. Fitted mappings were held fixed.",size=5.5)
    return finish(f,"Figure_S3B",out,inputs(*names))


def figure_s5(out):
    names=["figureS5_fixed_metrics.csv","figureS5_controlled_metrics.csv"]
    fixed=csv(names[0]);controlled=csv(names[1]);f=figure(87)
    panel(f,"A",3,2,"Fixed clustering assignments")
    a=axes(f,17,13,61,43)
    for i,(m,c) in enumerate(zip(["leiden","flowsom","spatialsort","pixie"],METHOD_COLORS)):
        z=fixed[fixed.method.eq(m)&fixed.noise_policy.eq("include")]
        val=z[z.region.eq("ALL")].purity.iloc[0]
        reg=z[~z.region.eq("ALL")].sort_values("region").purity
        assert len(reg)==8
        a.bar(i,val,width=.7,color=c,alpha=.65,zorder=2)
        a.scatter(i+np.linspace(-.16,.16,8),reg,s=10,color="#333333",edgecolors="white",linewidths=.25,zorder=3)
        a.text(i,.035,f"{val:.3f}",ha="center",va="bottom",fontsize=6)
    a.set(xticks=range(4),xticklabels=METHODS,ylim=(0,1.1),yticks=[0,.2,.4,.6,.8,1],ylabel="Cluster-majority upper bound\non reference agreement")
    grid(a)
    a.legend(handles=[Patch(color="#8ba0b1",label="Labels from pooled regions"),Line2D([],[],color="#333333",marker="o",linestyle="",markersize=3,label="Labels assigned within each region")],loc="upper left",fontsize=5.5)
    panel(f,"B",86,2,"Common 45 markers, all cells")
    a=axes(f,101,13,60,43)
    z=controlled[controlled.region.eq("ALL")&controlled.noise_policy.eq("include")]
    for m,c,label in zip(["leiden","flowsom","spatialsort","pixie"],METHOD_COLORS,METHODS):
        vals=[z[z.method.eq(f"{m}_k{k}")].purity.iloc[0] for k in [100,200,300]]
        a.plot([100,200,300],vals,"o-",lw=.8,ms=3,color=c,label=label)
    a.set(xlim=(90,310),ylim=(0,1.1),xticks=[100,200,300],yticks=[0,.2,.4,.6,.8,1],xlabel="Requested cluster count K",ylabel="Cluster-majority upper bound\non reference agreement")
    a.legend(ncol=2,loc="upper left",fontsize=5.5,columnspacing=.7,handlelength=1.4);grid(a)
    notes=["Original 28 reference labels. Noise included. One donor.",
           "(A) Original marker sets. Cluster labels assigned using pooled regions or separately within each region.",
           "(B) Pooled estimates with seed 42 and method-specific preprocessing.",
           "PIXIE: eight cells without measurable marker signal were retained in a separate group."]
    for i,note in enumerate(notes):text(f,3,69+i*4,note,size=5.5)
    return finish(f,"Figure_S5",out,inputs(*names))


def figure_4(out):
    cn="figure4_confusion.csv";fn="figure4_f1.csv"
    counts=csv(cn,index_col=0);d=csv(fn)
    assert counts.shape==(21,21)
    n=counts.sum(axis=1).to_numpy();mat=np.divide(counts.to_numpy(),n[:,None],where=n[:,None]>0)
    cfg=json.loads((ROOT/"configs/figure_04_historical_claude.json").read_text())
    cp=ROOT/cfg["frozen_inputs"]["cluster_counts"]["path"];clusters=pd.read_csv(cp).set_index("cluster")
    f=figure(169)
    panel(f,"A",3,2)
    workflow_inputs=add_workflow(f,"4A")
    panel(f,"B",3,33)
    a=axes(f,29,39,45,45)
    h=heatmap(a,mat,counts.index,counts.columns,0,1)
    plt.setp(a.get_xticklabels(),rotation=90)
    a.set_xlabel("Predicted cell type");a.set_ylabel("Reference cell type")
    colorbar(f,h,(77,39,2,45),"Fraction",ticks=[0,.2,.4,.6,.8,1],orientation="vertical")
    panel(f,"C",89,33)
    pooled=d[d.File_ID.eq("pooled")].set_index("label").sort_values("f1",ascending=False)
    labs=pooled.index.tolist();a=axes(f,117,52,44,42)
    a.barh(np.arange(21),pooled.f1,color="#e7e8ec",edgecolor="#9ca3af",linewidth=.4,label="Pooled F1")
    handles=[Patch(facecolor="#e7e8ec",edgecolor="#9ca3af",label="Pooled F1")]
    for fid,v in cfg["regions"].items():
        vals=d[d.File_ID.eq(fid)].set_index("label").reindex(labs).f1
        sc=a.scatter(vals,np.arange(21),s=7,color=v["color"],edgecolors="white",linewidths=.15,zorder=3,label=v["name"])
        handles.append(sc)
    a.set(yticks=np.arange(21),yticklabels=labs,ylim=(20.7,-.7),xlim=(0,1.02),xlabel="F1 score")
    a.set_xticks([0,.2,.4,.6,.8,1]);grid(a,axis="x")
    f.legend(handles=handles,loc="upper right",bbox_to_anchor=(.99,1-40/169),
             ncol=3,fontsize=5.5,columnspacing=.6,handletextpad=.3,handlelength=.8)
    panel(f,"D",3,117,"Cluster-majority diagnostic")
    a=axes(f,43,127,39,20);left=np.zeros(3)
    ex=clusters.loc[cfg["example_clusters"]]
    values=np.stack([ex.historical_21_direct_matches,
                     ex.historical_21_bound_cells-ex.historical_21_direct_matches,
                     ex.n_cells-ex.historical_21_bound_cells],axis=1)/ex.n_cells.to_numpy()[:,None]
    for k,c in enumerate(COMPONENT_COLORS):
        a.barh(range(3),values[:,k],left=left,color=c,height=.6,edgecolor="white",linewidth=.35)
        for j,v in enumerate(values[:,k]):
            if v>.08:a.text(left[j]+v/2,j,f"{v:.0%}",fontsize=5.5,va="center",ha="center",color="white" if k==0 else "black")
        left+=values[:,k]
    labs=[f"Example {i+1}\nMajority: {r.historical_21_majority_label}\nPredicted: {r.predicted_label}" for i,(_,r) in enumerate(ex.iterrows())]
    a.set(yticks=range(3),yticklabels=labs,ylim=(2.5,-.5),xlim=(0,1),xlabel="Fraction of cells in cluster")
    a.xaxis.set_major_formatter(PercentFormatter(1,decimals=0));a.set_xticks([0,.5,1])
    panel(f,"E",89,117,"Cluster-majority diagnostic")
    a=axes(f,116,130,45,12)
    n=clusters.n_cells.sum();direct=clusters.historical_21_direct_matches.sum();bound=clusters.historical_21_bound_cells.sum()
    left=0
    for k,(v,c) in enumerate(zip(np.array([direct,bound-direct,n-bound])/n,COMPONENT_COLORS)):
        a.barh([0],[v],left=[left],color=c,edgecolor="white",linewidth=.5,height=.5)
        a.text(left+v/2,0,f"{v:.0%}",ha="center",va="center",fontsize=5.5,color="white" if k==0 else "black");left+=v
    a.set(yticks=[0],yticklabels=["Leiden and Claude"],xlim=(0,1),ylim=(-.5,.5),xlabel="Fraction of cells")
    a.xaxis.set_major_formatter(PercentFormatter(1,decimals=0));a.set_xticks([0,.5,1])
    f.legend(handles=[Patch(color=c,label=l) for c,l in zip(COMPONENT_COLORS,COMPONENT_NAMES)],
             loc="lower center",bbox_to_anchor=(.5,.035),ncol=3,fontsize=5.5,handlelength=.8,columnspacing=1.5)
    text(f,3,165.5,"Maximum agreement assigns each fixed cluster its majority reference label.",size=5.5)
    return finish(f,"Figure_4",out,{**workflow_inputs,**inputs(cn,fn),str(cp.relative_to(ROOT)):sha(cp)})


RENDERERS={"1":figure_1,"2":figure_2,"3":figure_3,"4":figure_4,"5":figure_5,"S1":figure_s1,"S2":figure_s2,"S4":figure_s4,"S6":figure_s6,
           "S3A":figure_s3a,"S3B":figure_s3b,"S3C":figure_s3c,"S5":figure_s5,
           "S7":figure_s7,"S8":figure_s8,"S9":figure_s9,"S10":figure_s10}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"figures/publication")
    p.add_argument("--figures",nargs="+",choices=list(RENDERERS),default=list(RENDERERS))
    args=p.parse_args();receipts=[]
    for name in args.figures:receipts.append(RENDERERS[name](args.output))
    receipts=[json.loads(p.read_text()) for p in sorted(args.output.glob("Figure_*_verification.json"))]
    (args.output/"render_receipts.json").write_text(json.dumps(receipts,indent=2)+"\n")


if __name__=="__main__":main()
