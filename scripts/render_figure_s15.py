#!/usr/bin/env python3
"""Render manuscript Figure S15 from the verified B004 Leiden Astra scores."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, to_rgba
from matplotlib.lines import Line2D
from matplotlib.text import Text

ROOT = Path(__file__).resolve().parents[1]
SCORES = ROOT / "data/frozen/b004_astra_noise_20261120"
DEFAULT_OUTPUT = ROOT / "outputs/figure_s15/Figure_S15.png"
SCOPE = "heldout_equal_regions"
REFERENCE_POLICIES = ("all_reference", "non_noise_reference")
PREDICTION_POLICIES = ("noise_allowed", "noise_excluded")
WIDTH_MM = 165.1
HEIGHT_MM = 48.26
DPI = 600
TEXT_PT = 5
REFERENCE_LABELS = ("Counted", "Excluded")
MARK_STYLES = (("o", "#2864a5"), ("s", "#b55224"))


def read_scope(name):
    with (SCORES / name).open(newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["scope"] == SCOPE]


def read_results():
    manifest = json.loads((SCORES / "manifest.json").read_text())
    annotation = manifest["annotation"]
    verification = manifest["independent_verification"]
    if (
        annotation["model"] != "gpt-6.2-astra"
        or annotation["reasoning_effort"] != "max"
        or annotation["request_count"] != 4
        or verification["status"] != "pass"
        or verification["responses_verified"] != 4
    ):
        raise ValueError("Figure S15 requires four verified GPT-6.2 Astra max-reasoning calls")
    for name in ("cluster_predictions.csv", "metrics.csv", "paired_contrasts.csv"):
        digest = hashlib.sha256((SCORES / name).read_bytes()).hexdigest()
        if digest != manifest["files"][name]["sha256"]:
            raise ValueError(f"Frozen Figure S15 input changed: {name}")

    selected = read_scope("metrics.csv")
    metrics = {(row["arm"], row["reference_policy"]): row for row in selected}
    expected = {(arm, view) for arm in PREDICTION_POLICIES for view in REFERENCE_POLICIES}
    if set(metrics) != expected or len(selected) != 4 or any(
        row["designated_condition"] != "True" for row in selected
    ):
        raise ValueError("Figure S15 requires one designated score for each of four conditions")

    contrasts = read_scope("paired_contrasts.csv")
    paired = {(row["assigned_reference_policy"], row["reference_policy"]): row for row in contrasts}
    expected_pairs = {(assigned, view) for assigned in REFERENCE_POLICIES for view in REFERENCE_POLICIES}
    if len(contrasts) != 4 or set(paired) != expected_pairs:
        raise ValueError("Figure S15 requires both scoring rules for each of the two call pairs")
    return metrics, paired


def axes_at(figure, x, y, width, height):
    return figure.add_axes([
        x / WIDTH_MM, 1 - (y + height) / HEIGHT_MM, width / WIDTH_MM, height / HEIGHT_MM,
    ])


def panel_letter(figure, letter, x):
    figure.text(x / WIDTH_MM, 1 - 2 / HEIGHT_MM, letter, weight="bold", va="top")


def draw_scores(figure, metrics):
    panel_letter(figure, "A", 2)
    for column, (metric, title) in enumerate((
        ("accuracy", "Reference agreement (%)"), ("macro_f1", "Macro-F1 (%)"),
    )):
        ax = axes_at(figure, 21 + column * 31, 7, 27, 22)
        values = [
            [100 * float(metrics[arm, view][metric]) for view in REFERENCE_POLICIES]
            for arm in PREDICTION_POLICIES
        ]
        cells = ax.pcolormesh(
            (-0.5, 0.5, 1.5), (-0.5, 0.5, 1.5), values,
            cmap="RdYlGn", norm=Normalize(0, 100), edgecolors="white", linewidth=0.25,
        )
        ax.set(xlim=(-0.5, 1.5), ylim=(1.5, -0.5), title=title)
        ax.set_xticks((0, 1), REFERENCE_LABELS)
        ax.set_yticks((0, 1), ("Allowed", "Excluded") if column == 0 else ("", ""))
        ax.tick_params(length=0, pad=2)
        for spine in ax.spines.values():
            spine.set_visible(False)
        if column == 0:
            ax.set_ylabel("Noise prediction")
        for row, row_values in enumerate(values):
            for index, score in enumerate(row_values):
                ax.text(index, row, f"{score:.2f}", ha="center", va="center")

    figure.text(50 / WIDTH_MM, 1 - 35.2 / HEIGHT_MM, "Reference Noise", ha="center")
    color_axis = axes_at(figure, 34, 39.1, 32, 1.4)
    colorbar = figure.colorbar(cells, cax=color_axis, orientation="horizontal", ticks=(0, 50, 100))
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(length=1.2, width=0.4, pad=1)


def draw_pairs(figure, paired):
    panel_letter(figure, "B", 88)
    ax = axes_at(figure, 99, 8.5, 62, 29)
    ax.set(xlim=(-2.8, 8), ylim=(1.62, -0.62), xlabel="Change in reference agreement (percentage points)")
    ax.set_xticks((-2, 0, 2, 4, 6, 8))
    ax.set_yticks((0, 1), ("Pair 1", "Pair 2"))
    ax.axvline(0, color="black", linewidth=0.45, linestyle=(0, (2, 2)), zorder=1)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=2.5)

    for row, assigned in enumerate(REFERENCE_POLICIES):
        y_positions = (row - 0.12, row + 0.12)
        changes = [float(paired[assigned, view]["accuracy_delta_pp"]) for view in REFERENCE_POLICIES]
        ax.plot(changes, y_positions, color="#aaaaaa", linewidth=0.45, zorder=2)
        for delta, y, (marker, color) in zip(changes, y_positions, MARK_STYLES, strict=True):
            ax.plot(delta, y, marker=marker, color=color, markersize=3.2, linestyle="none", zorder=3)
            outside_right = delta == max(changes)
            align = "left" if outside_right else "right"
            offset = 3.5 if outside_right else -3.5
            label = f"{delta:+.2f}".replace("-", "−")
            ax.annotate(label, (delta, y), xytext=(offset, 0), textcoords="offset points",
                        ha=align, va="center", annotation_clip=False)

    handles = [
        Line2D([], [], marker=marker, color=color, linestyle="none", markersize=3.2, label=label)
        for (marker, color), label in zip(MARK_STYLES, REFERENCE_LABELS, strict=True)
    ]
    ax.legend(handles=handles, title="Reference Noise", ncol=2, loc="lower left",
              bbox_to_anchor=(0, 1.01), borderaxespad=0, borderpad=0,
              handlelength=0.7, handletextpad=0.4, columnspacing=0.9, labelspacing=0.25)


def verify_typography(figure):
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    black = to_rgba("black")
    for artist in figure.findobj(Text):
        if not artist.get_visible() or not artist.get_text():
            continue
        if artist.get_fontsize() != TEXT_PT or to_rgba(artist.get_color()) != black:
            raise ValueError(f"Figure typography diverges from 5 pt black: {artist.get_text()!r}")
        bbox = artist.get_window_extent(renderer)
        if not (figure.bbox.contains(bbox.x0, bbox.y0) and figure.bbox.contains(bbox.x1, bbox.y1)):
            raise ValueError(f"Figure text falls outside the canvas: {artist.get_text()!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output path for the 600 dpi PNG.")
    args = parser.parse_args()
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": TEXT_PT, "axes.titlesize": TEXT_PT, "axes.labelsize": TEXT_PT,
        "xtick.labelsize": TEXT_PT, "ytick.labelsize": TEXT_PT,
        "legend.fontsize": TEXT_PT, "legend.title_fontsize": TEXT_PT,
        "text.color": "black", "axes.labelcolor": "black", "axes.titlecolor": "black",
        "xtick.color": "black", "ytick.color": "black", "legend.labelcolor": "black",
        "axes.linewidth": 0.5, "axes.labelpad": 2.5, "axes.titlepad": 3,
        "xtick.major.width": 0.5, "xtick.major.size": 1.6, "xtick.major.pad": 1.8,
        "legend.frameon": False, "pdf.fonttype": 42,
    })
    figure = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4), facecolor="white")
    metrics, pairs = read_results()
    draw_scores(figure, metrics)
    draw_pairs(figure, pairs)
    verify_typography(figure)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=DPI, facecolor="white")
    plt.close(figure)


if __name__ == "__main__":
    main()
