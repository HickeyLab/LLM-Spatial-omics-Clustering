"""Retain the original Figure 1A illustrations with larger native text labels."""
from __future__ import annotations

import hashlib
import json

from PIL import Image

from publication_figure_design import ROOT, axes, sha, text

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
    left, top, _, _ = spec["crop_pixels"]
    for region in spec["erase_regions"]:
        x0,y0,x1,y1 = region["rect_pixels"]
        crop.paste(tuple(region["fill_rgb"]),(x0-left,y0-top,x1-left,y1-top))
    if hashlib.sha256(crop.tobytes()).hexdigest() != spec["cleaned_crop_rgb_sha256"]:
        raise ValueError("Figure 1A text-only cleanup checksum differs")
    x, y, width, height = spec["rect_mm"]
    if abs(width / height - crop.width / crop.height) > 1e-9:
        raise ValueError("Original Figure 1A aspect ratio differs")
    axis = axes(figure, x, y, width, height)
    # PDF and SVG embed the original pixels. PNG/TIFF rasterize the complete
    # figure at the configured output resolution without claiming new detail.
    axis.imshow(crop, interpolation="none")
    axis.set_axis_off()
    for label in spec["labels"]:
        text(figure,*label["position_mm"],label["text"],size=label["font_pt"],
             ha="center",va=label.get("va","top"),linespacing=1.05)
    figure._original_raster_workflow = {
        **spec,
        "native_size_pixels": list(crop.size),
        "effective_source_dpi": crop.width / (width / 25.4),
    }
    return {spec["source_file"]: spec["source_sha256"],
            str(CONFIG.relative_to(ROOT)): sha(CONFIG)}
