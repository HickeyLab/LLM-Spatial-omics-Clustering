#!/usr/bin/env python3
"""Validate the dormant protocol offline; no inference or launch command exists."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from llm_spatial_omics_clustering.revision.combined_annotation47 import load_protocol, validate_protocol

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=ROOT / 'configs/combined_annotation47_7_9_14_v1.json')
    args = parser.parse_args()
    print(json.dumps(validate_protocol(load_protocol(args.protocol)), indent=2))
