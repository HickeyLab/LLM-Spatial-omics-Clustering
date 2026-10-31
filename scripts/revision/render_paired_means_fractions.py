#!/usr/bin/env python3
"""Replot current Figure S10 from the frozen three-run paired results."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from llm_spatial_omics_clustering.manuscript import figure_s10, verify_inputs

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/manuscript_replay/figure_s10')
    args=parser.parse_args()
    verify_inputs()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    figure=figure_s10()
    path=args.output_dir/'Figure_S10_replot.png'
    figure.savefig(path,dpi=180,bbox_inches='tight')
    print(path)

if __name__=='__main__': main()
