#!/usr/bin/env python3
"""Render descriptive Figure 1D–F from the frozen regional effect rows.

The full publication composite preserves the original A and archived B/C.
This standalone view reproduces D–F values without significance-based encodings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
def figure():
    frozen = ROOT / 'data/frozen/figure_01_descriptive'
    for name, digest in json.loads((frozen / 'checksums.json').read_text()).items():
        if hashlib.sha256((frozen / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Frozen descriptive effect data changed: {name}')
    df = pd.read_csv(ROOT / "data/frozen/figure_01_descriptive/regional_f1_changes.csv")
    methods = ["Mesmer", "CellposeSAM", "CellposeCyto3"]
    labels = sorted(df.cell_type.unique())
    assert len(df) == 663 and len(labels) == 28
    assert set(df.method) == set(methods)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15})
    fig = plt.figure(figsize=(16, 10.8), facecolor="white")
    # All 28 classes are retained without significance-based selection or sorting.
    for i,(method,letter) in enumerate(zip(methods,'DEF')):
     ax=fig.add_axes([.235+i*.249,.17,.224,.735])
     ax.set_title(method,fontsize=19,pad=12)
     ax.text(-.08,1.045,letter,transform=ax.transAxes,fontsize=25,fontweight='bold')
     for y,label in enumerate(labels):
      vals=df[(df.method==method)&(df.cell_type==label)].sort_values('region').delta_pp.to_numpy()
      if not len(vals):continue
      ax.hlines(y,float(vals.min()),float(vals.max()),color='#8b8b8b',linewidth=1.4,zorder=1)
      # Vertical offsets separate regional points without altering effect values.
      offsets=np.linspace(-.18,.18,len(vals))
      ax.scatter(vals,y+offsets,s=19,facecolors='#b0b0b0',edgecolors='#666666',linewidths=.35,zorder=2)
      ax.scatter([float(vals.mean())],[y],marker='D',s=26,color='#111111',zorder=3)
      ax.text(104,y,str(len(vals)),va='center',ha='center',fontsize=12,color='#444444')
     ax.text(104,-1.2,'n',ha='center',fontsize=13,color='#444444')
     ax.set_xlim(-103,111);ax.set_xticks([-100,-50,0,50,100]);ax.set_ylim(len(labels)-.4,-1)
     ax.axvline(0,color='#555555',linewidth=.8,zorder=0)
     ax.set_yticks(range(len(labels)))
     ax.set_yticklabels(labels if i==0 else [],fontsize=14)
     ax.tick_params(axis='y',length=0,pad=8);ax.tick_params(axis='x',labelsize=13)
     for j in range(len(labels)):
      if j%2==0:ax.axhspan(j-.5,j+.5,color='#f4f4f4',zorder=-1)
     ax.spines[['top','right','left']].set_visible(False)
     ax.spines['bottom'].set_bounds(-100,100)
     ax.set_xlabel('F1 change (percentage points)',fontsize=14,labelpad=8)
    handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor='#b0b0b0',markeredgecolor='#666666',markersize=6,label='Individual tissue region'),Line2D([0],[0],marker='D',color='none',markerfacecolor='#111111',markeredgecolor='#111111',markersize=6,label='Mean regional change'),Line2D([0],[0],color='#8b8b8b',linewidth=1.4,label='Observed regional range')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.60,.035),ncol=3,frameon=False,fontsize=13)
    fig.text(.235,.005,'After minus before compensation. B004 tissue regions are subsamples of one donor.',fontsize=12,color='#444444')
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Output path stem, without extension")
    args = parser.parse_args()
    fig = figure()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output.with_suffix(".png"), dpi=250, facecolor="white")
    fig.savefig(args.output.with_suffix(".pdf"), facecolor="white")
    plt.close(fig)
    print(args.output)


if __name__ == '__main__':
    main()
