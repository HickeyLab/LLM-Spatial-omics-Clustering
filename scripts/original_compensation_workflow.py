"""Place the checksum-pinned original Figure 1A artwork without redrawing it."""
from __future__ import annotations

import hashlib
import json

from PIL import Image

from publication_figure_design import ROOT, axes, sha

CONFIG = ROOT / "configs/figure_01_original_workflow.json"


def add_original_compensation_workflow(figure):
    spec = json.loads(CONFIG.read_text())
    source = ROOT / spec["source_file"]
    if sha(source) != spec["source_sha256"]:
        raise ValueError("Original Figure 1A source checksum differs")
    with Image.open(source) as image:
        crop = image.convert("RGB").crop(spec["crop_pixels"])
    if hashlib.sha256(crop.tobytes()).hexdigest() != spec["crop_rgb_sha256"]:
        raise ValueError("Original Figure 1A crop checksum differs")
    x, y, width, height = spec["rect_mm"]
    if abs(width / height - crop.width / crop.height) > 1e-9:
        raise ValueError("Original Figure 1A aspect ratio differs")
    axis = axes(figure, x, y, width, height)
    # PDF and SVG embed the original pixels. PNG/TIFF rasterize the complete
    # figure at the configured output resolution without claiming new detail.
    axis.imshow(crop, interpolation="none")
    axis.set_axis_off()
    figure._original_raster_workflow = {
        **spec,
        "native_size_pixels": list(crop.size),
        "effective_source_dpi": crop.width / (width / 25.4),
    }
    return {spec["source_file"]: spec["source_sha256"],
            str(CONFIG.relative_to(ROOT)): sha(CONFIG)}
