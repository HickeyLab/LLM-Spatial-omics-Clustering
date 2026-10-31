#!/usr/bin/env python3
"""Offline Figure 3 replay and numerical replot, using current manuscript panels."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from llm_spatial_omics_clustering.manuscript import artwork, save_replots, verify_inputs
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=ROOT/'outputs/manuscript_replay/figure_03')
    a=p.parse_args();verify_inputs();save_replots('3',a.output_dir);artwork('3',a.output_dir)
if __name__=='__main__':main()
