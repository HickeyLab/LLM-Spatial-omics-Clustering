#!/usr/bin/env python3
"""Replot current Figure 5 from frozen donor results. No inference or fitting."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from llm_spatial_omics_clustering.manuscript import figure_5, verify_inputs

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/manuscript_replay/figure_05')
    args=parser.parse_args()
    verify_inputs()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    figure=figure_5()
    path=args.output_dir/'Figure_5_replot.png'
    figure.savefig(path,dpi=180,bbox_inches='tight')
    print(path)

if __name__=='__main__': main()
