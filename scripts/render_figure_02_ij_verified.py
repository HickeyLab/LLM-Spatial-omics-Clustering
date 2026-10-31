#!/usr/bin/env python3
"""Refresh only publication Figure 2I/J from independently verified source tables."""
from pathlib import Path
import argparse,json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle,ConnectionPatch
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import numpy as np
import pandas as pd
from PIL import Image

REPO=Path(__file__).resolve().parents[1]

def render(workspace,out,input_dir=None,source=None):
    out.mkdir(parents=True,exist_ok=True)
    input_dir=Path(input_dir) if input_dir else REPO/'data/frozen/manuscript_replay/figure_02'
    source=Path(source) if source else REPO/'figures/manuscript/Figure_2.png'
    original=Image.open(source).convert('RGB');assert original.size==(1792,2048)
    composite=original.copy()
    font=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
    if font.exists():font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({'font.family':('Arial' if font.exists() else 'DejaVu Sans'),'font.size':5,'text.color':'black','axes.labelcolor':'black','xtick.color':'black','ytick.color':'black'})
    methods=['Leiden','FlowSOM','SpatialSort','PIXIE']
    rects={'I':(850,1325,1792,1690),'J':(842,1690,1792,2048)}
    summaries=pd.read_csv(input_dir/'panel_I_marker_summaries.csv')
    counts=pd.read_csv(input_dir/'panel_I_selected_groups.csv').set_index('method').n_selected_cells
    markers=summaries.marker.drop_duplicates().tolist();assert len(markers)==45 and len(summaries)==180
    x0,y0,x1,y1=rects['I'];width,height=x1-x0,y1-y0
    fig=plt.figure(figsize=(width/250,height/250),dpi=250)
    fig.text(.008,.99,'I',va='top',fontsize=10)
    fig.text(.57,.99,'CD8+ T groups from four-model modal annotations',ha='center',va='top',fontsize=5.3)
    ax=fig.add_axes([.19,.43,.80,.22]);order={(m,k):(i,j) for i,m in enumerate(methods) for j,k in enumerate(markers)}
    for m in methods:
        v=summaries.loc[summaries.method.eq(m)].set_index('marker').loc[markers]
        # Preserve the source Scanpy dot-size exponent (1.5), with 0–100% limits.
        ax.scatter(np.arange(45),np.full(45,3-methods.index(m)),s=(v.fraction_cells_pct.to_numpy()/100)**1.5*12,c=v.scaled_mean_expression,cmap='Reds',vmin=0,vmax=1,edgecolors='black',linewidths=.16)
    ax.set_xlim(-.8,44.8);ax.set_ylim(-.6,3.6)
    ax.set_xticks(range(45));ax.set_xticklabels(markers,rotation=90,fontsize=4.8)
    ax.set_yticks([3,2,1,0]);ax.set_yticklabels([f'{m} (n={counts.loc[m]:,})' for m in methods],fontsize=4.6)
    ax.tick_params(axis='both',length=1.5,width=.4,pad=1)
    ax.set_ylabel('')
    for spine in ax.spines.values():spine.set_linewidth(.55)
    fig.text(.59,.015,'Protein marker',ha='center',va='bottom',fontsize=4.8)
    legend=fig.add_axes([.21,.73,.34,.15]);legend.set_xlim(-.3,2.3);legend.set_ylim(-.8,1.5);legend.axis('off')
    fractions=np.array([0,50,100]);legend.scatter(range(3),[0]*3,s=(fractions/100)**1.5*12,color='#888888',edgecolors='black',linewidths=.16)
    for i,f in enumerate(fractions):legend.text(i,-.28,str(f),ha='center',va='top',fontsize=4.5)
    legend.text(1,1.22,'Cells with stored marker value > 0 (%)',ha='center',va='center',fontsize=4.7)
    cax=fig.add_axes([.68,.78,.28,.025]);cb=fig.colorbar(ScalarMappable(norm=Normalize(0,1),cmap='Reds'),cax=cax,orientation='horizontal');cb.set_ticks([0,1]);cb.ax.tick_params(length=1.5,width=.4,labelsize=4.5,pad=1);cb.outline.set_linewidth(.5)
    fig.text(.82,.93,'Mean stored marker expression\nMin–max scaled per marker',ha='center',va='top',fontsize=4.7)
    fig.savefig(out/'Figure_2I_verified.png',dpi=250,facecolor='white');plt.close(fig)
    tile=Image.open(out/'Figure_2I_verified.png').convert('RGB');assert tile.size==(width,height);composite.paste(tile,(x0,y0))
    # Reuse fixed source-output windows. No search, retuning or annotation calls.
    cells=pd.read_csv(input_dir/'panel_J_all_cells.csv.gz',dtype={'File_ID':str,'ID':str})
    windows=pd.read_csv(input_dir/'panel_J_window_agreement.csv',dtype={'file_id':str})
    raw=pd.read_csv(REPO/'configs/cell_type_colors.csv');colors=dict(zip(raw.cell_type_update,raw.color_hex))
    reps={'CD4+ T cell':'CD4+ T','CD66+ Enterocyte':'CD66+ Epithelial','CD7+ Immune':'NK','Endothelial':'CD36 high Endothelial','Enterocyte':'Epithelial','Lymphatic':'PDPN+ Stromal','MUC1+ Enterocyte':'MUC1+ Epithelial','Stroma':'Stromal'}
    color_map={label:colors[reps.get(label,label)] for label in set(cells.truth_label).union(*[set(cells[m]) for m in methods])}
    x0,y0,x1,y1=rects['J'];width,height=x1-x0,y1-y0
    fig=plt.figure(figsize=(width/250,height/250),dpi=250)
    fig.text(.008,.99,'J',va='top',fontsize=10)
    fig.text(.57,.99,'Post-hoc selected spatial examples',ha='center',va='top',fontsize=5.3)
    grid=fig.add_gridspec(2,6,left=.10,right=.998,top=.76,bottom=.02,wspace=.06,hspace=.11)
    headers=['Tissue region','Reference\nannotations',*methods]
    plotted=[]
    for ri,name in enumerate(['Low reference agreement','High reference agreement']):
        record=windows.loc[windows.example.eq(name)].iloc[0]
        whole=cells.loc[cells.File_ID.eq(record.file_id)]
        zoom=whole.loc[whole.x.between(record.x0,record.x1)&whole.y.between(record.y0,record.y1)&whole.truth_label.ne('Noise')]
        assert len(zoom)==record.n_cells
        axes=[]
        for ci,column in enumerate(['truth_label','truth_label',*methods]):
            axis=fig.add_subplot(grid[ri,ci]);axes.append(axis)
            frame=whole if ci==0 else zoom
            for label,g in frame.groupby(column,sort=True):axis.scatter(g.x,g.y,s=.16 if ci==0 else .7,color=color_map[label],alpha=.72 if ci==0 else .85,edgecolors='none')
            axis.invert_yaxis();axis.set_xticks([]);axis.set_yticks([])
            for spine in axis.spines.values():spine.set_linewidth(.35);spine.set_edgecolor('#9CA3AF')
            if ri==0:axis.set_title(headers[ci],fontsize=4.8,pad=2)
        axes[0].add_patch(Rectangle((record.x0,record.y0),record.x1-record.x0,record.y1-record.y0,fill=False,edgecolor='black',linewidth=.55))
        for corner,target in [((record.x1,record.y0),(0,1)),((record.x1,record.y1),(0,0))]:fig.add_artist(ConnectionPatch(xyA=corner,coordsA=axes[0].transData,xyB=target,coordsB=axes[1].transAxes,color='black',linewidth=.3,clip_on=False))
        row_label=name.replace(' reference agreement',' reference\nagreement')
        fig.text(.034,.59 if ri==0 else .20,row_label+f'\nn = {len(zoom):,}',rotation=90,ha='center',va='center',fontsize=4.6)
        plotted.append({'example':name,'n_zoom_cells':len(zoom),'n_locator_cells':len(whole),'columns':headers})
    fig.savefig(out/'Figure_2J_verified.png',dpi=250,facecolor='white');plt.close(fig)
    tile=Image.open(out/'Figure_2J_verified.png').convert('RGB');assert tile.size==(width,height);composite.paste(tile,(x0,y0))
    dest=out/'Figure_2_verified_IJ.png';composite.save(dest)
    final=out/'Figure_2_verified_IJ.pdf';composite.save(final,resolution=300)
    a=np.array(original);b=np.array(composite);mask=np.zeros(a.shape[:2],dtype=bool)
    for x0,y0,x1,y1 in rects.values():mask[y0:y1,x0:x1]=True
    assert not np.any(a[~mask]!=b[~mask])
    receipt={'source_figure_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_figure_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'rectangles':rects,'pixels_changed_outside_I_J':0,'I_method_order':methods,'I_marker_order':markers,'I_source_size_exponent':1.5,'I_color_range':[0,1],'I_fraction_range':[0,100],'J_windows':plotted,'final_pdf':str(final)}
    (out/'artwork_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Rendered verified I/J and preserved all other panel pixels.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=REPO,help='Compatibility argument; no files are written here')
    p.add_argument('--source-figure',type=Path,default=REPO/'figures/manuscript/Figure_2.png')
    p.add_argument('--input-dir',type=Path,default=REPO/'data/frozen/manuscript_replay/figure_02')
    p.add_argument('--output-dir',type=Path,default=REPO/'outputs/manuscript_replay/figure_02_ij')
    a=p.parse_args();render(a.workspace,a.output_dir,a.input_dir,a.source_figure)
