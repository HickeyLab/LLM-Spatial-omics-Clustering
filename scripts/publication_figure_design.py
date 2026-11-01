"""Shared physical-size typography and exports for the manuscript artwork.

Coordinates in the layout helpers are millimetres, measured from the top left.
The plotting inputs are frozen tables. This module has no inference or fitting
path. SVG text remains text, PDF uses embedded TrueType fonts, and raster
exports are drawn directly from the native figure at 600 dpi.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.text import Text
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STYLE = json.loads((ROOT / "configs/publication_figure_style.json").read_text())
MM = 1 / 25.4
METHODS = ["Leiden", "FlowSOM", "SpatialSort", "PIXIE"]
METHOD_KEYS = ["leiden", "flowsom", "spatialsort", "pixie_tiff"]
METHOD_COLORS = ["#2f6fab", "#cf7d30", "#a35a93", "#4d8e73"]
MODELS = ["GPT", "Claude", "Gemini", "DeepSeek"]
MODEL_KEYS = ["gpt", "claude", "gemini", "deepseek"]
MODEL_COLORS = ["#E39835", "#53A055", "#4D7DA7", "#AC77A2"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configure():
    for suffix in ("", " Bold", " Italic", " Bold Italic"):
        path = Path("/System/Library/Fonts/Supplemental") / ("Arial" + suffix + ".ttf")
        if path.exists():
            font_manager.fontManager.addfont(str(path))
    # Other systems can use an installed Arial or the metrically similar font.
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 6, "axes.labelsize": 6, "axes.titlesize": 6.5,
        "xtick.labelsize": 5.5, "ytick.labelsize": 5.5, "legend.fontsize": 5.5,
        "figure.titlesize": 6.5, "axes.linewidth": .5,
        "xtick.major.width": .5, "ytick.major.width": .5,
        "xtick.major.size": 2, "ytick.major.size": 2,
        "xtick.major.pad": 2, "ytick.major.pad": 2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.labelpad": 2.5, "legend.frameon": False,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "svg.hashsalt": "cell-masks-publication-20261031",
        "savefig.facecolor": "white", "figure.facecolor": "white",
        "text.color": "black", "axes.labelcolor": "black",
        "xtick.color": "black", "ytick.color": "black",
        "axes.unicode_minus": False,
    })


def figure(height_mm, width_mm=165.1):
    configure()
    f = plt.figure(figsize=(width_mm * MM, height_mm * MM))
    f._physical_mm = (width_mm, height_mm)
    return f


def axes(f, x, y, w, h):
    fw, fh = f._physical_mm
    return f.add_axes([x / fw, 1 - (y + h) / fh, w / fw, h / fh])


def text(f, x, y, value, size=6, **kw):
    fw, fh = f._physical_mm
    return f.text(x / fw, 1 - y / fh, value, fontsize=size,
                  va=kw.pop("va", "top"), **kw)


def panel(f, letter, x, y, title=None, title_x=None):
    text(f, x, y, letter, size=8, weight="bold")
    if title:
        text(f, title_x if title_x is not None else x + 8, y + .35,
             title, size=6.5, weight="bold")


def grid(ax, axis="y"):
    ax.grid(axis=axis, color="#d9d9d9", lw=.35, zorder=0)
    ax.set_axisbelow(True)


def heatmap(ax, data, rows, cols, vmin=0, vmax=100, cmap="RdYlGn",
            annotate=False, fmt=".1f", size=6):
    a = np.asarray(data, float)
    p = ax.pcolormesh(np.arange(a.shape[1]+1)-.5, np.arange(a.shape[0]+1)-.5,
                      a, cmap=cmap, vmin=vmin, vmax=vmax, shading="flat",
                      linewidth=0, rasterized=False)
    ax.set_xlim(-.5, a.shape[1]-.5)
    ax.set_ylim(a.shape[0]-.5, -.5)
    if a.shape[0] == a.shape[1]:
        ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(range(len(cols)), cols)
    ax.set_yticks(range(len(rows)), rows)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_linewidth(.5)
    if annotate:
        for (i,j),v in np.ndenumerate(a):
            rgb = np.asarray(p.cmap(p.norm(v))[:3])
            lin = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
            lum = float(lin @ [.2126,.7152,.0722])
            color = "black" if (lum+.05)/.05 >= 1.05/(lum+.05) else "white"
            label=format(v,fmt)
            if label in ("-0","-0.0","-0.00"):label=format(0,fmt)
            ax.text(j,i,label,ha="center",va="center",fontsize=size,color=color)
    return p


def colorbar(f, artist, rect, label=None, ticks=None, orientation="horizontal"):
    ax = axes(f, *rect)
    cb = f.colorbar(artist,cax=ax,orientation=orientation,ticks=ticks)
    cb.outline.set_linewidth(.5)
    cb.ax.tick_params(labelsize=5.5,length=2,width=.5,pad=1.5)
    if label:
        cb.set_label(label,fontsize=5.5,labelpad=2)
    return cb


def flow(f, boxes, y, height=16, gap=3, x=3, widths=None, size=5.5):
    fw,_ = f._physical_mm
    if widths is None:
        widths=[(fw-2*x-gap*(len(boxes)-1))/len(boxes)]*len(boxes)
    for i,(value,w) in enumerate(zip(boxes,widths)):
        a=axes(f,x,y,w,height)
        a.add_patch(Rectangle((0,0),1,1,transform=a.transAxes,
                             ec="#7a858e",fc="#f6f8fa",lw=.5))
        a.text(.5,.5,value,ha="center",va="center",fontsize=size,
               transform=a.transAxes,linespacing=1.3)
        a.set_axis_off()
        if i<len(boxes)-1:
            line=axes(f,x+w,y+height/2-1,gap,2)
            line.add_patch(FancyArrowPatch((.05,.5),(.95,.5),arrowstyle="-|>",
                           mutation_scale=5,linewidth=.5,color="black"))
            line.set_axis_off()
        x+=w+gap


def finish(f, name, output, inputs=None, notes=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    f.canvas.draw()
    visible=[t for t in f.findobj(Text) if t.get_visible() and t.get_text().strip()]
    min_size=min(t.get_fontsize() for t in visible)
    if min_size < STYLE["minimum_font_pt"]-1e-5:
        bad=[(t.get_text(),t.get_fontsize()) for t in visible if t.get_fontsize()<5.5-1e-5]
        raise ValueError(f"Subminimum text in {name}: {bad}")
    # Check text against the physical page, independently of tight cropping.
    renderer=f.canvas.get_renderer(); page=f.bbox
    outside=[]
    for t in visible:
        b=t.get_window_extent(renderer)
        if b.x0 < -1 or b.y0 < -1 or b.x1 > page.x1+1 or b.y1 > page.y1+1:
            outside.append(t.get_text())
    if outside:
        raise ValueError(f"Text outside {name} page: {outside}")
    paths=[]
    for ext in ("svg","pdf","png"):
        p=output/(name+"."+ext)
        metadata = {"CreationDate":None,"ModDate":None} if ext=="pdf" else {"Date":None} if ext=="svg" else {}
        f.savefig(p,dpi=610 if ext in ("svg","pdf") else 600,metadata=metadata,
                  transparent=bool(getattr(f,"_biorender_overlays",None)))
        paths.append(p)
    if getattr(f,"_biorender_overlays",None):
        from biorender_workflows import compose
        compose(f,output,name)
    p=output/(name+".tiff")
    # Lossless container conversion, with no resizing or interpolation.
    with Image.open(output/(name+".png")) as im:
        im.convert("RGB").save(p,dpi=(600,600),compression="tiff_lzw")
        pixel_size=list(im.size)
    paths.append(p)
    preview=output/(name+"_preview.png")
    if not getattr(f,"_biorender_overlays",None):
        f.savefig(preview,dpi=160)
    fw,fh=f._physical_mm
    receipt={"figure":name,"width_mm":fw,"height_mm":fh,
             "minimum_font_pt":min_size,"font_family":"Arial",
             "minimum_placement_width_mm":round(fw*5/min_size,3),
             "raster_dpi":600,"raster_size_pixels":pixel_size,
             "vector_text_editable":True,"panel_letter_format":"A",
             "biorender_workflow":getattr(f,"_biorender_overlays",None),
             "dense_point_layers_native_dpi":610 if any(getattr(a,"get_rasterized",lambda:False)() for a in f.findobj()) else None,
             "inputs":inputs or {},"notes":notes or [],
             "files":{p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in paths}}
    if hasattr(f,"_original_raster_workflow"):
        receipt["original_raster_workflow"] = f._original_raster_workflow
        receipt["minimum_font_scope"] = "Native text only; original Figure 1A raster labels are preserved."
    (output/(name+"_verification.json")).write_text(json.dumps(receipt,indent=2)+"\n")
    plt.close(f)
    print(name, pixel_size, "minimum font", min_size, "pt",flush=True)
    return receipt
