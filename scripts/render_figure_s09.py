#!/usr/bin/env python3
"""Replot current Figure S9 calibration and neighborhood-input panels."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from llm_spatial_omics_clustering.manuscript import figure_s9, verify_inputs

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/manuscript_replay/figure_s09')
    args=parser.parse_args()
    verify_inputs()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    figure=figure_s9()
    path=args.output_dir/'Figure_S9_replot.png'
    figure.savefig(path,dpi=180,bbox_inches='tight')
    print(path)

if __name__=='__main__': main()
