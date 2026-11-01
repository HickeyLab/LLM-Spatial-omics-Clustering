#!/usr/bin/env python3
"""Render S5C from frozen effects, without fitting, rescoring or model calls."""
from __future__ import annotations

import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
from PIL import Image
import yaml

from render_figure_s07 import text_color

ROOT = Path(__file__).resolve().parents[1]


def load_inputs():
    config = json.loads((ROOT / "configs/figure_s05.json").read_text())
    source = ROOT / config["data"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != config["data_sha256"]:
        raise ValueError("Frozen S5C input checksum differs")
    with source.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    keys = [(r["clustering"], r["cell_type"], r["method"]) for r in rows]
    expected = {(b, t, m) for b in config["backends"]
                for t in config["cell_types"] for m in config["methods"]}
    if len(rows) != 336 or len(set(keys)) != 336 or set(keys) != expected:
        raise ValueError("S5C must contain exactly 336 backend/type/method cells")
    for row in rows:
        if (row["variant"], row["population"]) != ("directed_10", "shared_fixed_objects"):
            raise ValueError("Unexpected S5C analysis population")
        if not 1 <= int(row["n_regions"]) <= 8:
            raise ValueError("Unexpected contributing tissue-region count")
        if not np.isfinite(float(row["mean_difference"])):
            raise ValueError("Missing S5C effect")
    values = {k: 100 * float(r["mean_difference"]) for k, r in zip(keys, rows)}
    maximum = max(5.0, max(abs(v) for v in values.values()))
    if config["color_limits"] != [-maximum, maximum] or config["color_center"] != 0:
        raise ValueError("S5C must retain its original symmetric limits and zero center")
    reference = yaml.safe_load((ROOT / "configs/figure_02.yaml").read_text())["panel_h"]["style"]
    if config["color_map"] != reference["cmap"]:
        raise ValueError("S5C must use the manuscript heatmap palette")
    return config, values


def build_figure(config, values):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13,
                         "pdf.fonttype": 42, "ps.fonttype": 42})
    figure = plt.figure(figsize=(12.76875, 12.8), facecolor="white")
    # Current S3C: the title and explanatory notes belong in its caption.
    figure.text(0.009, 0.994, "C", ha="left", va="top", fontsize=17, weight="bold")
    norm = TwoSlopeNorm(vmin=config["color_limits"][0],
                        vcenter=config["color_center"], vmax=config["color_limits"][1])
    cmap = plt.get_cmap(config["color_map"])
    for column, backend in enumerate(config["backends"]):
        axis = figure.add_axes([0.235 + column * 0.353, 0.157, 0.307, 0.79])
        matrix = np.array([[values[backend, label, method] for method in config["methods"]]
                           for label in config["cell_types"]])
        image = axis.imshow(matrix, norm=norm, cmap=cmap, aspect="auto", interpolation="nearest")
        axis.set(xticks=range(6), xticklabels=config["methods"],
                 yticks=range(28), yticklabels=config["cell_types"] if column == 0 else [])
        axis.tick_params(axis="both", labelsize=12.5, length=3)
        plt.setp(axis.get_xticklabels(), rotation=40, ha="right")
        axis.set_title(backend, fontsize=16, pad=8)
        for row in range(28):
            for col in range(6):
                value = matrix[row, col]
                axis.text(col, row, str(round(value)), ha="center", va="center",
                          fontsize=13, color=text_color(cmap(norm(value))))
    color_axis = figure.add_axes([0.915, 0.208, 0.015, 0.60])
    colorbar = figure.colorbar(image, cax=color_axis, ticks=config["colorbar_ticks"])
    colorbar.set_label(config["colorbar_label"], fontsize=12.5, labelpad=8)
    colorbar.ax.tick_params(labelsize=12)
    return figure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pdf", type=Path)
    args = parser.parse_args()
    config, values = load_inputs()
    figure = build_figure(config, values)
    output = args.output or ROOT / config["preview"]
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=160, facecolor="white")
    rendered = Image.open(buffer).convert("RGB")
    if rendered.size != (2043, 2048):
        raise ValueError(f"Unexpected S5C footprint: {rendered.size}")
    if args.check:
        actual = Image.open(output).convert("RGB")
        if actual.size != rendered.size or actual.tobytes() != rendered.tobytes():
            raise ValueError("S5C preview differs from its frozen-data renderer")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        rendered.save(output, compress_level=9)
    if args.pdf:
        args.pdf.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(args.pdf, facecolor="white")
    plt.close(figure)
    print(f"{'Verified' if args.check else 'Rendered'} {output}")


if __name__ == "__main__":
    main()
