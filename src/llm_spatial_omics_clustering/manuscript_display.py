"""Current manuscript display numbers over stable native figure inputs."""
import json
import hashlib
from PIL import Image
from pathlib import Path
from . import manuscript
ROOT = Path(__file__).resolve().parents[2]

def inventory():
    value = json.loads((ROOT / "configs/manuscript_display_crosswalk.json").read_text())
    native = manuscript.inventory()["figures"]
    records = value["figures"]
    if len(records) != 18 or len({r["source_figure_id"] for r in records.values()}) != 18:
        raise ValueError("Manuscript display map must cover 18 distinct source figures")
    if {r["source_figure_id"] for r in records.values()} != set(native):
        raise ValueError("Manuscript display map differs from native inventory")
    for display_id, record in records.items():
        if not record["caption"].startswith("Figure " + display_id + ". "):
            raise ValueError("Caption and manuscript display label differ")
        if not (ROOT / record["notebook"]).is_file():
            raise ValueError("Current manuscript notebook is missing")
    return value

def artwork(figure_id, output_dir=None):
    record = inventory()["figures"][str(figure_id)]
    images = []
    for entry in record["images"]:
        path = ROOT / entry["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Current manuscript image checksum differs")
        images.append(Image.open(path).copy())
        if output_dir is not None:
            target = Path(output_dir)
            target.mkdir(parents=True, exist_ok=True)
            (target / path.name).write_bytes(path.read_bytes())
    return images

def __getattr__(name):
    return getattr(manuscript, name)
