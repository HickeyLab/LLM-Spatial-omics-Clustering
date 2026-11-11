"""Offline reconstruction of the preserved Opus Figure 4; not active artwork."""
from pathlib import Path
import hashlib,importlib.util,json,sys
ARCHIVE=Path(__file__).resolve().parent
ROOT=ARCHIVE.parents[1]
manifest=json.loads((ARCHIVE/"index.json").read_text())
for entry in manifest["files"]:
    path=ROOT/entry["archive_path"]
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry["sha256"]:
        raise ValueError("Archived source changed: "+entry["archive_path"])
sys.path.insert(0,str(ARCHIVE/"scripts"))
import publication_figure_design as design
design.ROOT=ROOT
import biorender_workflows
biorender_workflows.ROOT=ROOT
biorender_workflows.CONFIG=ARCHIVE/"configs/biorender_workflows.json"
import render_annotation47_figures as renderer
renderer.ROOT=ROOT
renderer.DATA=ROOT/"data/frozen/annotation47_results_20261110"
renderer.figure_4(ROOT/"outputs/archival_figure4_opus_replay")
