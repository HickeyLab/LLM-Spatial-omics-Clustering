#!/usr/bin/env python3
"""Render only verified Figure 2F/H, preserving every other panel pixel."""
from pathlib import Path
import argparse
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from PIL import Image
import yaml

REPO=Path(__file__).resolve().parents[1]

def render(source,out,input_dir=None):
    out.mkdir(parents=True,exist_ok=True)
    input_dir=Path(input_dir) if input_dir else REPO/'data/frozen/manuscript_replay/figure_02'
    config=yaml.safe_load((REPO/'configs/figure_02.yaml').read_text())
    values=pd.read_csv(input_dir/'celltype_metrics.csv')
    legacy_values=pd.read_csv(input_dir/'legacy_celltype_metrics.csv')
    original=Image.open(source).convert('RGB');assert original.size==(1792,2048)
    if source.resolve()!=(out/'Figure_2_before.png').resolve():original.save(out/'Figure_2_before.png')
    family='DejaVu Sans'
    arial=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
    if arial.exists():font_manager.fontManager.addfont(str(arial));family='Arial'
    plt.rcParams.update({'font.family':family,'font.size':5,'text.color':'black','axes.labelcolor':'black','xtick.color':'black','ytick.color':'black'})
    methods=['FlowSOM','Leiden','SpatialSort','PIXIE']
    rectangles={'F':(1170,700,1792,1320),'H':(0,1325,640,1960)}
    combined=original.copy()
    plot_records={}
    for letter,rect in rectangles.items():
        is_f=letter=='F';metric='f1' if is_f else 'recall'
        labels=legacy_values.groupby('cell_type')[metric].mean().sort_values(ascending=False,kind='stable').index.tolist()
        matrix=values.pivot(index='cell_type',columns='method',values=metric).reindex(index=labels,columns=methods)
        assert matrix.shape==(20,4) and matrix.notna().all().all()
        counts=values.groupby('cell_type').n_cells.agg(['min','max']).reindex(labels)
        assert counts['min'].equals(counts['max']) and counts['min'].sum()==209587
        scale=1 if is_f else 100
        x0,y0,x1,y1=rect;width,height=x1-x0,y1-y0
        fig=plt.figure(figsize=(width/250,height/250),dpi=250,facecolor='white')
        ax=fig.add_axes([.32,.22,.49,.59]);bars=fig.add_axes([.838,.22,.142,.59])
        cmap='RdYlGn';image=ax.imshow(matrix.to_numpy()*scale,aspect='auto',interpolation='nearest',cmap=cmap,vmin=0,vmax=scale)
        ax.set_yticks(np.arange(20));ax.set_yticklabels(labels,fontsize=5)
        ax.set_xticks(np.arange(4));ax.set_xticklabels(methods,rotation=90,fontsize=5)
        ax.tick_params(length=0,pad=2)
        fig.text(.565,.02,'Clustering method',ha='center',va='bottom',fontsize=4.7)
        for spine in ax.spines.values():spine.set_linewidth(.5)
        bars.barh(np.arange(20),counts['min'],height=.76,color='#64748B')
        bars.set_ylim(19.5,-.5);bars.set_xlim(0,33000);bars.set_xticks([0,25000]);bars.set_yticks([])
        bars.xaxis.set_major_formatter(FuncFormatter(lambda x,p:'0' if x==0 else f'{x/1000:g}k'))
        bars.tick_params(axis='x',labelsize=4.5,length=2,width=.4,pad=2)
        bars.spines[['top','right','left']].set_visible(False);bars.spines['bottom'].set_linewidth(.5)
        bars.set_xlabel('Reference\ncells',fontsize=4.7,labelpad=3)
        color_axis=fig.add_axes([.32,.88,.49,.027])
        cb=fig.colorbar(image,cax=color_axis,orientation='horizontal',ticks=np.linspace(0,scale,6))
        cb.ax.xaxis.set_ticks_position('top');cb.ax.tick_params(labelsize=4.6,length=2,width=.4,pad=1)
        cb.outline.set_linewidth(.5)
        title='Cell-type F1' if is_f else 'Cell-type recall (%)'
        fig.text(.565,.98,title,ha='center',va='top',fontsize=5.3)
        fig.text(.012,.985,letter,ha='left',va='top',fontsize=10)
        png=out/f'Figure_2{letter}_verified.png';pdf=out/f'Figure_2{letter}_verified.pdf'
        fig.savefig(png,dpi=250,facecolor='white');fig.savefig(pdf,facecolor='white');plt.close(fig)
        tile=Image.open(png).convert('RGB');assert tile.size==(width,height)
        combined.paste(tile,(x0,y0))
        plot_records[letter]={'metric':metric,'matrix_row_order':labels,'matrix_column_order':methods,'matrix':matrix.to_numpy().tolist(),'display_multiplier':scale,'reference_cell_counts':counts['min'].astype(int).tolist()}
    png=out/'Figure_2_verified_F1_recall.png';combined.save(png)
    combined.save(out/'Figure_2_verified_F1_recall.pdf',resolution=300)
    a=np.array(original);b=np.array(combined);mask=np.zeros(a.shape[:2],bool)
    for x0,y0,x1,y1 in rectangles.values():mask[y0:y1,x0:x1]=True
    assert not np.any(a[~mask]!=b[~mask])
    receipt={'source_path':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'rectangles':rectangles,'pixels_changed_outside_F_H':0,'font':family,'plotted_values':plot_records}
    (out/'artwork_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Rendered 80 F1 entries and 80 recall entries with verified reference counts. Other panel pixels unchanged.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-figure',type=Path,default=REPO/'figures/manuscript/Figure_2.png')
    p.add_argument('--input-dir',type=Path,default=REPO/'data/frozen/manuscript_replay/figure_02')
    p.add_argument('--output-dir',type=Path,default=REPO/'outputs/manuscript_replay/figure_02_fh')
    a=p.parse_args();render(a.source_figure,a.output_dir,a.input_dir)
