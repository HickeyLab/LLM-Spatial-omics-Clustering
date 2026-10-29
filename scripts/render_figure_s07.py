#!/usr/bin/env python3
"""Render Figure S7 from frozen results without scoring, fitting or model calls."""
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
from matplotlib.colors import Normalize
import numpy as np
from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_inputs():
    config = json.loads((ROOT / "configs/figure_s07.json").read_text())
    data = ROOT / config["data"]
    if hashlib.sha256(data.read_bytes()).hexdigest() != config["data_sha256"]:
        raise ValueError("Frozen S7 input checksum differs")
    with data.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    keys = [(r["arm"], r["method"], r["model"]) for r in rows]
    expected = {(a, m, l) for a in config["arms"] for m in config["methods"] for l in config["models"]}
    if len(rows) != 32 or len(set(keys)) != 32 or set(keys) != expected:
        raise ValueError("S7 must contain exactly 32 condition/method/model cells")
    for row in rows:
        if (row["donor"], row["population"], float(row["repeat"])) != ("B004", "B004_test", 0.0):
            raise ValueError("Unexpected S7 cohort or repeat")
        if not 0 <= float(row["agreement"]) <= 1:
            raise ValueError("Invalid agreement fraction")
    reference = yaml.safe_load((ROOT / "configs/figure_02.yaml").read_text())["panel_h"]["style"]
    if (config["color_map"] != reference["cmap"]
            or config["color_limits"] != reference["color_limits"]):
        raise ValueError("S7 palette and limits must match Figure 2H")
    return config, {(r["arm"], r["method"], r["model"]): float(r["agreement"]) for r in rows}


def text_color(rgba):
    rgb = np.asarray(rgba[:3])
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    luminance = float(linear @ [0.2126, 0.7152, 0.0722])
    return "black" if luminance > 0.179 else "white"


def build_figure(config, values):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 14})
    figure = plt.figure(figsize=(12.8, 5.03125), facecolor="white")
    figure.text(0.5, 0.97, config["title"], ha="center", va="top", fontsize=18)
    norm = Normalize(*config["color_limits"])
    cmap = plt.get_cmap(config["color_map"])
    for column, arm in enumerate(config["arms"]):
        left = 0.085 if column == 0 else 0.565
        axis = figure.add_axes([left, 0.15, 0.31, 0.60])
        matrix = np.array([[100 * values[arm, method, model] for model in config["models"]]
                           for method in config["methods"]])
        image = axis.imshow(matrix, norm=norm, cmap=cmap, aspect="auto", interpolation="nearest")
        axis.set(xticks=range(4), xticklabels=config["model_labels"],
                 yticks=range(4), yticklabels=config["method_labels"])
        axis.tick_params(axis="both", labelsize=12)
        plt.setp(axis.get_xticklabels(), rotation=30, ha="right")
        center = left + 0.155
        figure.text(center, 0.855, config["condition_labels"][column],
                    ha="center", va="center", fontsize=16)
        figure.text(center, 0.795, config["condition_subtitles"][column],
                    ha="center", va="center", fontsize=11)
        for row in range(4):
            for col in range(4):
                value = matrix[row, col]
                axis.text(col, row, f"{value:.1f}", ha="center", va="center",
                          color=text_color(cmap(norm(value))), fontsize=14)
    color_axis = figure.add_axes([0.922, 0.15, 0.016, 0.60])
    colorbar = figure.colorbar(image, cax=color_axis, ticks=config["colorbar_ticks"])
    colorbar.set_label(config["colorbar_label"], fontsize=13, labelpad=8)
    colorbar.ax.tick_params(labelsize=11)
    return figure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, help="PNG output path, defaulting to the committed preview")
    parser.add_argument("--pdf", type=Path, help="Optional vector PDF export")
    args = parser.parse_args()
    config, values = load_inputs()
    figure = build_figure(config, values)
    output = args.output or ROOT / config["preview"]
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=160, facecolor="white")
    rendered = Image.open(buffer).convert("RGB")
    if rendered.size != (2048, 805):
        raise ValueError(f"Unexpected S7 footprint: {rendered.size}")
    if args.check:
        actual = Image.open(output).convert("RGB")
        if actual.size != rendered.size or actual.tobytes() != rendered.tobytes():
            raise ValueError("S7 preview differs from its frozen-data renderer")
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
