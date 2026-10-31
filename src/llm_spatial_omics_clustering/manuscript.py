"""Offline manuscript artwork replay and numerical panel replotting.

Artwork replay preserves the approved publication layout. Numerical replotting
uses separate checksum-pinned tables and does not claim pixel-identical fonts.
Neither path makes model calls, fits models, or modifies manuscript files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / 'data/frozen/manuscript_replay'
MODELS = ['gemini', 'gpt', 'claude', 'deepseek']
METHODS = ['FlowSOM', 'Leiden', 'SpatialSort', 'PIXIE']
NAMES = {'gpt': 'GPT', 'claude': 'Claude', 'gemini': 'Gemini', 'deepseek': 'DeepSeek'}


def inventory():
    return json.loads((ROOT / 'configs/manuscript_inventory.json').read_text())


def verify_inputs():
    manifest = json.loads((INPUTS / 'manifest.json').read_text())
    for entry in manifest['files']:
        path = ROOT / entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f"Frozen manuscript input changed: {entry['path']}")
    return len(manifest['files'])


def read_table(name):
    manifest = json.loads((INPUTS / 'manifest.json').read_text())
    path = INPUTS / name
    entry = next(e for e in manifest['files'] if e['path'] == str(path.relative_to(ROOT)))
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
        raise ValueError(f'Frozen table changed: {name}')
    return pd.read_csv(path)


def artwork(figure_id, output_dir=None):
    """Return exact approved images, with optional lossless PNG export."""
    record = inventory()['figures'][str(figure_id)]
    images = []
    for entry in record['images']:
        path = ROOT / entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Approved artwork checksum differs: {path.name}')
        image = Image.open(path).convert('RGB')
        if output_dir is not None:
            target = Path(output_dir)
            target.mkdir(parents=True, exist_ok=True)
            image.save(target / path.name)
        images.append(image)
    return images


def _heatmap(frame, title, *, vmax=100, percent=False, counts=None):
    if counts is None:
        fig, ax = plt.subplots(figsize=(7.8, max(4.5, .27 * len(frame))))
    else:
        fig, (ax, side) = plt.subplots(1, 2, figsize=(11, max(5.8, .3 * len(frame))),
                                      gridspec_kw={'width_ratios': [4, 1.25]})
    im = ax.imshow(frame.to_numpy(), aspect='auto', cmap='RdYlGn', vmin=0, vmax=vmax)
    ax.set_xticks(range(len(frame.columns)), frame.columns)
    ax.set_yticks(range(len(frame)), frame.index)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label='Reference agreement (%)' if percent else title)
    if len(frame) <= 4:
        for i in range(len(frame)):
            for j in range(len(frame.columns)):
                ax.text(j, i, f'{frame.iloc[i,j]:.1f}' + ('%' if percent else ''), ha='center', va='center')
    if counts is not None:
        side.barh(np.arange(len(frame)), counts.reindex(frame.index), color='#64748b')
        side.set_ylim(len(frame)-.5, -.5)
        side.set_yticks([])
        side.set_xlabel('Reference cells')
    fig.tight_layout()
    return fig


def figure_2_panel(panel):
    """Replot the current E/G, F/H, I and J metrics from frozen evidence."""
    panel = panel.upper()
    if panel in ['E', 'G']:
        data = read_table('figure_02/regional_metrics.csv')
        value = 'weighted_f1' if panel == 'E' else 'cluster_purity'
        title = 'Regional weighted F1' if panel == 'E' else 'Regional cell-count-weighted cluster purity'
        fig, ax = plt.subplots(figsize=(7.4, 4.4))
        groups = [data.loc[data.method.eq(m)].sort_values('region') for m in METHODS]
        ax.boxplot([g[value] for g in groups], positions=range(4), showfliers=False)
        palette = plt.get_cmap('tab10')
        for i, group in enumerate(groups):
            jitter = np.random.default_rng(7).uniform(-.15,.15,len(group))
            ax.scatter(i+jitter, group[value], c=[palette(j) for j in range(len(group))], s=30)
        ax.set_xticks(range(4), METHODS)
        ax.set(title=title, ylabel='Weighted F1' if panel=='E' else 'Cluster purity', ylim=(.3,.9))
        fig.tight_layout()
        return fig
    if panel in ['F', 'H']:
        values = read_table('figure_02/celltype_metrics.csv')
        order = read_table(f'figure_02/panel_{panel}_values.csv').iloc[:,0].tolist()
        field = 'f1' if panel == 'F' else 'recall'
        matrix = values.pivot(index='cell_type',columns='method',values=field).reindex(index=order,columns=METHODS)
        counts = values.groupby('cell_type').n_cells.first()
        return _heatmap(matrix * (1 if panel=='F' else 100), 'Cell-type F1' if panel=='F' else 'Cell-type recall (%)', vmax=1 if panel=='F' else 100, counts=counts)
    if panel == 'I':
        data = read_table('figure_02/panel_I_marker_summaries.csv')
        markers = data.marker.drop_duplicates().tolist()
        fig, ax = plt.subplots(figsize=(14,4.3))
        for i, method in enumerate(['Leiden','FlowSOM','SpatialSort','PIXIE']):
            rows=data.loc[data.method.eq(method)].set_index('marker').reindex(markers)
            ax.scatter(range(45),np.full(45,i),s=rows.fraction_cells_pct/100*180,c=rows.scaled_mean_expression,cmap='Reds',vmin=0,vmax=1)
        ax.set_xticks(range(45),markers,rotation=90)
        groups = data.groupby('method').n_selected_cells.first()
        ax.set_yticks(range(4),[f'{m} (n={groups[m]:,})' for m in ['Leiden','FlowSOM','SpatialSort','PIXIE']])
        ax.invert_yaxis()
        ax.set_title('CD8+ T groups from four-model modal annotations')
        colorbar = fig.colorbar(plt.cm.ScalarMappable(cmap='Reds',norm=plt.Normalize(0,1)),ax=ax)
        colorbar.set_label('Mean stored expression\n(min-max scaled per marker)', fontsize=9)
        ax.set_xlabel('Marker. Dot area encodes the fraction of processed values above zero.')
        fig.tight_layout()
        return fig
    if panel == 'J':
        return spatial_panel(2)
    raise ValueError(f'Figure 2{panel} is retained approved artwork, not a numerical replot.')


def figure_3_panel(panel):
    """Replot B-G with the manuscript's exact metric definitions and vocabulary."""
    panel=panel.upper()
    data=read_table('figure_03/metrics.csv')
    if panel in ['B','C']:
        field='agreement' if panel=='B' else 'percent_upper_bound'
        frame=data.pivot(index='model',columns='method',values=field).reindex(index=MODELS,columns=METHODS)
        frame.index=[NAMES[m] for m in frame.index]
        return _heatmap(frame*(100 if panel=='B' else 1), 'Cell-level reference agreement (%)' if panel=='B' else 'Reference agreement as % of cluster-majority upper bound',percent=panel=='B')
    if panel in ['D','E']:
        types=read_table('figure_03/celltype_metrics.csv')
        types=types.loc[types.method.eq('Leiden')]
        field='agreement' if panel=='D' else 'percent_upper_bound'
        frame=types.pivot(index='cell_type',columns='model',values=field).reindex(columns=MODELS)
        frame=frame.loc[frame.mean(axis=1).sort_values(ascending=False,kind='stable').index]
        frame.columns=[NAMES[m] for m in frame.columns]
        return _heatmap(frame*(100 if panel=='D' else 1),'Cell-type reference agreement (%)' if panel=='D' else 'Cell-type agreement as % of cluster-majority upper bound',counts=types.groupby('cell_type').cells.first())
    if panel in ['F','G']:
        field='selected_cell_agreement' if panel=='F' else 'selected_cluster_agreement'
        order=['Leiden','FlowSOM','SpatialSort','PIXIE']
        fig,ax=plt.subplots(figsize=(10,4.5))
        for i, model in enumerate(MODELS):
            values=data.loc[data.model.eq(model)].set_index('method').reindex(order)[field]*100
            ax.bar(np.arange(4)+(i-1.5)*.18,values,width=.18,label=NAMES[model])
        ax.set_xticks(range(4),order)
        ax.set(ylim=(0,100),ylabel='Reference agreement (%)',title='Reference-informed selection after prediction\n'+('Cells weighted equally' if panel=='F' else 'Clusters weighted equally'))
        ax.legend(ncols=4,frameon=False)
        fig.tight_layout()
        return fig
    if panel=='H':return spatial_panel(3)
    raise ValueError(f'Figure 3{panel} is retained approved workflow artwork.')


def spatial_panel(figure_id):
    cells=read_table('figure_02/panel_J_zoom_cells.csv')
    columns=['truth_label','Leiden','FlowSOM','SpatialSort','PIXIE']
    if figure_id==3:
        raw=read_table('figure_03/annotations.csv.gz')
        # Explicit string keys avoid dtype-dependent cell joins.
        for frame in [cells,raw]:
            frame['File_ID']=frame.File_ID.astype(str);frame['ID']=frame.ID.astype(str)
        cells=cells.merge(raw,on=['File_ID','ID'],validate='one_to_one')
        columns=['truth_label']+['leiden__'+m for m in ['gpt','gemini','claude','deepseek']]
        votes=cells[['leiden__'+m for m in ['gpt','claude','gemini','deepseek']]]
        cells['Modal label']=[next(v for v in row if list(row).count(v)==max(list(row).count(x) for x in row)) for row in votes.itertuples(index=False,name=None)]
        columns.append('Modal label')
    color_data=pd.read_csv(ROOT/'configs/cell_type_colors.csv').set_index('cell_type_update').color_hex.to_dict()
    aliases={'CD4+ T cell':'CD4+ T','CD66+ Enterocyte':'CD66+ Epithelial','CD7+ Immune':'NK','Endothelial':'CD36 high Endothelial','Enterocyte':'Epithelial','Lymphatic':'PDPN+ Stromal','MUC1+ Enterocyte':'MUC1+ Epithelial','Stroma':'Stromal'}
    locators=read_table('figure_02/panel_J_all_cells.csv.gz')
    windows=read_table('figure_02/panel_J_window_agreement.csv')
    fig,axes=plt.subplots(2,len(columns)+1,figsize=(3*(len(columns)+1),6),squeeze=False)
    for i,example in enumerate(['Low reference agreement','High reference agreement']):
        group=cells.loc[cells.example.eq(example)]
        window=windows.loc[windows.example.eq(example)].iloc[0]
        whole=locators.loc[locators.File_ID.eq(window.file_id)]
        axes[i,0].scatter(whole.x,whole.y,c=[color_data.get(aliases.get(v,v),'#999999') for v in whole.truth_label],s=.3,linewidths=0)
        from matplotlib.patches import Rectangle
        axes[i,0].add_patch(Rectangle((window.x0,window.y0),window.x1-window.x0,window.y1-window.y0,fill=False,color='black',lw=.7))
        axes[i,0].invert_yaxis();axes[i,0].set_xticks([]);axes[i,0].set_yticks([])
        if i==0:axes[i,0].set_title('Tissue region')
        for ax,column in zip(axes[i,1:],columns):
            colors=[color_data.get(aliases.get(v,v),'#999999') for v in group[column]]
            ax.scatter(group.x,group.y,c=colors,s=3,linewidths=0)
            ax.invert_yaxis();ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
            if i==0:ax.set_title('Reference annotations' if column=='truth_label' else NAMES.get(column.removeprefix('leiden__'),column))
        axes[i,0].set_ylabel(example+f' (n={len(group):,})')
    fig.tight_layout()
    return fig


def figure_5():
    data=read_table('figure_05/All_four_LLMs_B005_B006.csv')
    equal=read_table('figure_05/equal_external_donor_metrics.csv')
    methods=['leiden','flowsom','spatialsort','pixie_tiff'];models=['gpt','claude','gemini','deepseek']
    donors=['B005','B006']
    matrices=[]
    for donor in donors:
        group=data.loc[data.donor.eq(donor)]
        matrices.append(group.pivot(index='method',columns='model',values='retrieval_minus_marker_pp').reindex(index=methods,columns=models))
    eq=equal.loc[equal.population.eq('external_common5px')&equal.arm.eq('retrieval')]
    for field in ['agreement','macro_f1']:
        matrices.append(eq.pivot(index='method',columns='model',values=field).reindex(index=methods,columns=models)*100)
    limit=max(abs(m.to_numpy()).max() for m in matrices[:2])
    fig,axes=plt.subplots(2,2,figsize=(12,9),constrained_layout=True)
    titles=['B005: change after adding labeled reference profiles\nPercentage points','B006: change after adding labeled reference profiles\nPercentage points','Mean reference agreement across B005 and B006 (%)\nEqual donor weights, with labeled reference profiles','Mean 23-class macro-F1 across B005 and B006 (%)\nEqual donor weights, with labeled reference profiles']
    for i,(ax,matrix,title) in enumerate(zip(axes.flat,matrices,titles)):
        values=matrix.to_numpy();im=ax.imshow(values,cmap='RdYlGn',vmin=-limit if i<2 else 0,vmax=limit if i<2 else 100)
        ax.set_xticks(range(4),[NAMES[m] for m in models],rotation=35,ha='right')
        ax.set_yticks(range(4),['Leiden','FlowSOM','SpatialSort','PIXIE']);ax.set_title(title,fontsize=10)
        for r in range(4):
            for c in range(4):
                rgb=np.asarray(im.cmap(im.norm(values[r,c]))[:3]);linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);lum=linear@[.2126,.7152,.0722]
                color='black' if (lum+.05)/.05>=1.05/(lum+.05) else 'white'
                ax.text(c,r,format(values[r,c],'+.1f' if i<2 else '.1f'),ha='center',va='center',color=color)
    return fig


def figure_s10():
    data=read_table('paired/paired_summary.csv')
    methods=['leiden','flowsom','spatialsort','pixie_tiff']
    fig,axes=plt.subplots(2,2,figsize=(11,9),sharex=True,sharey=True,constrained_layout=True)
    for ax,model in zip(axes.flat,['gpt','claude','gemini','deepseek']):
        rows=data.loc[data.model.eq(model)].set_index('method').reindex(methods)
        y=np.arange(4)
        ax.hlines(y,rows.means_agreement_mean*100,rows.fractions_agreement_mean*100,color='#cbd5df')
        for arm,offset,color,marker,title in [('means',-.06,'#2864a5','o','All-marker means'),('fractions',.06,'#b55224','s','Means plus fractions')]:
            ax.errorbar(rows[f'{arm}_agreement_mean']*100,y+offset,xerr=rows[f'{arm}_agreement_sd']*100,fmt=marker,color=color,capsize=3,label=title)
        ax.set_yticks(y,['Leiden','FlowSOM','SpatialSort','PIXIE']);ax.set_title(NAMES[model]);ax.set_xlim(0,50);ax.set_xlabel('Reference agreement (%)')
    axes[0,0].invert_yaxis();axes[0,0].legend(frameon=False)
    return fig


def figure_s9():
    metrics=read_table('figure_s09/calibration_metrics.csv')
    pooled=metrics.loc[metrics.region.eq('POOLED')]
    wide=pooled.pivot(index=['method','model','arm'],columns='probability',values='brier')
    reliability=read_table('figure_s09/calibration_reliability.csv')
    risk=read_table('figure_s09/selective_risk.csv')
    paired=read_table('figure_s09/spatial_paired_differences.csv').query("split=='test'")
    fig,axes=plt.subplots(2,2,figsize=(11,8.5),constrained_layout=True)
    ax=axes[0,0];ax.scatter(wide.raw_vote,wide.recalibrated);ax.plot([0,1],[0,1],'--',color='gray');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Raw vote Brier score',ylabel='Recalibrated Brier score',title='A  Probability assessment across 32 conditions')
    r=reliability.query("method=='leiden' and model=='gpt' and arm=='marker_only' and probability=='raw_vote'")
    ax=axes[0,1];ax.scatter(r.mean_probability,r.observed_reference_agreement,s=25+150*r.n_cells/r.n_cells.max());ax.plot([0,1],[0,1],'--',color='gray');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Raw modal vote fraction',ylabel='Observed reference agreement',title='B  GPT and Leiden marker-only reliability')
    ax=axes[1,0]
    for arm,title in [('marker_only','Markers'),('retrieval','Reference-assisted')]:
        r=risk.loc[risk.method.eq('leiden')&risk.model.eq('gpt')&risk.arm.eq(arm)].sort_values('threshold')
        ax.plot(r.coverage*100,r.selective_reference_error*100,'o-',label=title)
    ax.set(xlim=(0,100),ylim=(0,100),xlabel='Retained cell coverage (%)',ylabel='Reference disagreement (%)',title='C  GPT and Leiden selective risk');ax.legend(frameon=False)
    ax=axes[1,1]
    for i,(_,r) in enumerate(paired.groupby('region')):ax.scatter(i+np.linspace(-.1,.1,len(r)),r.agreement_delta_pp)
    ax.scatter([2],[paired.agreement_delta_pp.mean()],marker='D');ax.axhline(0,color='gray',ls='--');ax.set_xticks([0,1,2],['Test region 1','Test region 2','Mean']);ax.set(ylabel='Neighborhood minus markers (percentage points)',title='D  Paired neighborhood-input comparison')
    return fig


def save_replots(figure_id, output_dir):
    """Export numerical panels only. The approved composite remains untouched."""
    target=Path(output_dir);target.mkdir(parents=True,exist_ok=True)
    panels={'2':'EFGHIJ','3':'BCDEFGH'}
    for panel in panels[str(figure_id)]:
        fig=(figure_2_panel if str(figure_id)=='2' else figure_3_panel)(panel)
        fig.savefig(target/f'Figure_{figure_id}{panel}_replot.png',dpi=150)
        plt.close(fig)
