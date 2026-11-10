#!/usr/bin/env python3
"""Build or verify the one-repeat annotation pack. No network or paid execution."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from llm_spatial_omics_clustering.revision.annotation47_prepare import main

if __name__ == '__main__':
    main()
