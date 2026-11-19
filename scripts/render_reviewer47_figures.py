"""Render B004 reviewer controls from checksum-bound offline results.

There is no inference, fitting, scheduler or network path. Missing scientific
conditions are masked before plotting; partial accuracy is never displayed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

from publication_figure_design import (
    ROOT, METHODS, METHOD_KEYS, figure, axes, text, panel, grid, heatmap,
    colorbar, finish, sha,
)

from render_annotation47_figures import benchmark_orders, input_hashes as annotation_inputs

DATA = ROOT / "data/frozen/reviewer47_results_20261111"
COMPLETED_DATA = ROOT / "data/frozen/astra_prompt_controls_results_20261115"
FAMILIES = ["openai", "anthropic", "google", "deepseek"]
MODELS = ["GPT-6 Astra", "Claude Opus 5.5", "Gemini 4 Argon", "DeepSeek V4.1 Flash 1017"]
ARMS = ["selected_names", "selected_means", "all_means", "all_means_fractions"]
ARM_LABELS = ["Selected\nnames", "Selected\nmeans", "All\nmeans", "Means +\nfractions"]


def checked_path(name, directory=DATA):
    manifest = json.loads((directory / "manifest.json").read_text())
    spec = manifest["files"][name]
    expected = spec["sha256"] if isinstance(spec, dict) else spec
    path = directory / name
    if sha(path) != expected:
        raise ValueError("Frozen reviewer result changed: " + name)
    return path


def table(name, **kwargs):
    return pd.read_csv(checked_path(name), **kwargs)


def inputs(*names, directory=DATA):
    paths = [checked_path(name, directory) for name in names]
    return {str(path.relative_to(ROOT)): sha(path) for path in paths}


def complete_sets(directory=DATA):
    rows = (table("set_metrics.csv") if directory == DATA
            else pd.read_csv(checked_path("set_metrics.csv", directory)))
    required = {"family", "method", "arm", "status", "agreement", "fixed28_macro_f1"}
    if not required.issubset(rows.columns):
        raise ValueError("Reviewer set-metric schema differs")
    if rows[["family", "method", "arm"]].duplicated().any():
        raise ValueError("Duplicate reviewer condition")
    # An incomplete condition keeps its planned denominator in source tables,
    # but must not contribute a public accuracy/F1 point.
    incomplete = rows.status.ne("complete")
    if rows.loc[incomplete, ["agreement", "fixed28_macro_f1"]].notna().any().any():
        raise ValueError("Incomplete condition exposes partial accuracy")
    if directory == COMPLETED_DATA and (len(rows) != 71 or incomplete.any()):
        raise ValueError("Completed reviewer bank must contain all 71 completed conditions")
    return rows


def representation_matrix(rows, family):
    selected = rows[rows.family.eq(family) & rows.arm.isin(ARMS)]
    if len(selected) != 16:
        raise ValueError("Representation Cartesian coverage differs")
    return selected.pivot(index="method", columns="arm", values="agreement").reindex(
        index=benchmark_orders()[1], columns=ARMS).to_numpy(dtype=float) * 100


def figure_s8(out, *, completed=False):
    directory = COMPLETED_DATA if completed else DATA
    rows = complete_sets(directory)
    f = figure(137)
    for i, family in enumerate(FAMILIES):
        x = 3 + (i % 2) * 82
        y = 3 + (i // 2) * 66
        panel(f, chr(65 + i), x, y)
        text(f, x + 42, y, MODELS[i], size=6.5, ha="center")
        a = axes(f, x + 22, y + 11, 48, 35)
        matrix = representation_matrix(rows, family)
        if completed and not np.isfinite(matrix).all():
            raise ValueError("Completed representation matrix contains a missing value")
        method_names = [METHODS[METHOD_KEYS.index(m)] for m in benchmark_orders()[1]]
        artist = heatmap(a, matrix, method_names, ARM_LABELS, 0, 100,
                         cmap="RdYlGn", annotate=False)
        for (r, c), value in np.ndenumerate(matrix):
            if np.isfinite(value):
                rgb = np.asarray(artist.cmap(artist.norm(value))[:3])
                color = "black" if rgb.mean() > .5 else "white"
                a.text(c, r, f"{value:.1f}", ha="center", va="center", fontsize=6.1, color=color)
            else:
                a.add_patch(Rectangle((c - .5, r - .5), 1, 1, facecolor="#eeeeee",
                                      edgecolor="#b5b5b5", hatch="///", lw=.3))
                a.text(c, r, "Pending", ha="center", va="center", fontsize=5.5, color="#333333")
        a.tick_params(axis="x", pad=3)
        colorbar(f, artist, (x + 73, y + 11, 1.5, 35), None,
                 ticks=[0, 50, 100], orientation="vertical")
    name = "Figure_S10" if completed else "Figure_S8"
    coverage = ("All 64 representation conditions are complete." if completed
                else "Partial conditions are masked as Pending, not scored.")
    source_hashes = inputs("set_metrics.csv", directory=directory)
    if completed:
        source_hashes.update(annotation_inputs("metrics.csv"))
    return finish(f, name, out, source_hashes, notes=[
        "Equal-weighted agreement across the two B004 test regions; fixed 28-label vocabulary including Noise.",
        "Four frozen partitions and one generation per condition. " + coverage,
        "Selected names and selected means use at most six label-blind selected markers; full arms use all47 markers.",
        "Method rows share the primary benchmark ranking by descending mean four-model fixed-28-label macro-F1 for means plus fractions. Columns retain the planned information progression.",
    ])


def control_rows():
    rows = complete_sets()
    return rows[rows.family.eq("anthropic")].copy()


def values_for(rows, arm):
    selected = rows[rows.arm.eq(arm)]
    if not selected.status.eq("complete").all():
        raise ValueError("A plotted Opus control is incomplete")
    return selected.set_index("method").agreement.reindex(benchmark_orders()[1]).to_numpy(dtype=float) * 100


def _legacy_prompt_panels(f):
    rows = control_rows()
    panel(f, "A", 3, 3)
    a = axes(f, 27, 15, 51, 38)
    blind = values_for(rows, "all_means_fractions")
    named = values_for(rows, "method_named")
    if not np.isfinite(np.concatenate([blind, named])).all():
        raise ValueError("Method-name control has missing values")
    for i in range(4):
        a.plot([blind[i], named[i]], [i, i], color="#b9c2cc", lw=.9, zorder=1)
    a.scatter(blind, np.arange(4) - .055, s=15, color="#2864a5", marker="o", zorder=3)
    a.scatter(named, np.arange(4) + .055, s=15, color="#b55224", marker="s", zorder=3)
    method_names = [METHODS[METHOD_KEYS.index(m)] for m in benchmark_orders()[1]]
    a.set(yticks=range(4), yticklabels=method_names, ylim=(3.5, -.5), xlim=(0, 100),
          xticks=[0, 25, 50, 75, 100], xlabel="Reference agreement (%)")
    grid(a, "x")
    a.legend(handles=[Line2D([], [], marker="o", ls="", color="#2864a5", label="Blinded"),
                      Line2D([], [], marker="s", ls="", color="#b55224", label="Named")],
             loc="upper left", bbox_to_anchor=(-.1, 1.32), ncol=2, fontsize=5.5, markerscale=.5)

    panel(f, "B", 85, 3)
    a = axes(f, 111, 15, 50, 38)
    selected = rows[rows.method.eq("leiden")].set_index("arm")
    if any(selected.loc[arm, "status"] != "complete" for arm in ["all_means_fractions", "neighborhood"]):
        raise ValueError("Neighborhood control is incomplete")
    vals = selected.loc[["all_means_fractions", "neighborhood"], "agreement"].to_numpy(dtype=float) * 100
    a.barh([0, 1], vals, color=["#2864a5", "#b55224"], height=.55, zorder=2)
    for i, v in enumerate(vals):
        a.text(v + 1.2, i, f"{v:.1f}", va="center", fontsize=6)
    a.set(yticks=[0, 1], yticklabels=["Markers", "Markers +\nneighborhood"], ylim=(1.7, -.7),
          xlim=(0, 100), xticks=[0, 25, 50, 75, 100], xlabel="Reference agreement (%)")
    grid(a, "x")

def _completed_prompt_panels(f):
    rows = complete_sets(COMPLETED_DATA)

    def agreement(family, method, arm):
        selected = rows[rows.family.eq(family) & rows.method.eq(method) & rows.arm.eq(arm)]
        if len(selected) != 1 or selected.iloc[0].status != "complete":
            raise ValueError("A plotted prompt-control condition is incomplete or duplicated")
        value = float(selected.iloc[0].agreement) * 100
        if not np.isfinite(value):
            raise ValueError("A plotted prompt-control condition has no agreement")
        return value

    panel(f, "A", 3, 3)
    a = axes(f, 30, 15, 48, 38)
    methods = benchmark_orders()[1]
    conditions = [("anthropic", method) for method in methods] + [("openai", "leiden")]
    blind = np.asarray([agreement(family, method, "all_means_fractions")
                        for family, method in conditions])
    named = np.asarray([agreement(family, method, "method_named")
                        for family, method in conditions])
    positions = np.asarray([0, 1, 2, 3, 4.35])
    for y, left, right in zip(positions, blind, named):
        a.plot([left, right], [y, y], color="#b9c2cc", lw=.9, zorder=1)
    a.scatter(blind, positions - .055, s=15, color="#2864a5", marker="o", zorder=3)
    a.scatter(named, positions + .055, s=15, color="#b55224", marker="s", zorder=3)
    labels = ["Opus–" + METHODS[METHOD_KEYS.index(method)] for method in methods] + ["Astra–Leiden"]
    a.set(yticks=positions, yticklabels=labels, ylim=(4.95, -.55), xlim=(0, 100),
          xticks=[0, 25, 50, 75, 100], xlabel="Reference agreement (%)")
    a.axhline(3.7, color="#d1d5db", lw=.5, zorder=1)
    grid(a, "x")
    a.legend(handles=[Line2D([], [], marker="o", ls="", color="#2864a5", label="Blinded"),
                      Line2D([], [], marker="s", ls="", color="#b55224", label="Named")],
             loc="upper left", bbox_to_anchor=(-.1, 1.32), ncol=2, fontsize=5.5, markerscale=.5)

    panel(f, "B", 85, 3)
    a = axes(f, 112, 15, 49, 38)
    conditions = [("anthropic", "all_means_fractions"), ("anthropic", "neighborhood"),
                  ("openai", "all_means_fractions"), ("openai", "neighborhood")]
    vals = np.asarray([agreement(family, "leiden", arm) for family, arm in conditions])
    positions = np.asarray([0, 1, 2.5, 3.5])
    a.barh(positions, vals, color=["#2864a5", "#b55224"] * 2, height=.55, zorder=2)
    for y, value in zip(positions, vals):
        a.text(value + 1.2, y, f"{value:.1f}", va="center", fontsize=6)
    a.set(yticks=positions,
          yticklabels=["Opus\nmarkers", "Opus\n+ neighborhood", "Astra\nmarkers", "Astra\n+ neighborhood"],
          ylim=(4.2, -.7), xlim=(0, 100), xticks=[0, 25, 50, 75, 100],
          xlabel="Reference agreement (%)")
    a.axhline(1.75, color="#d1d5db", lw=.5, zorder=1)
    grid(a, "x")

def figure_s9(out, *, completed=False):
    f = figure(171)
    if completed:
        _completed_prompt_panels(f)
    else:
        _legacy_prompt_panels(f)

    panel(f, "C", 3, 79)
    a = axes(f, 20, 90, 58, 49)
    name = "calibration/calibration_equal_test_region_metrics.csv"
    cal = table(name)
    variants = ["raw_agreement", "recalibrated", "development_constant"]
    pairs = cal.pivot(index=["method", "model_family"], columns="variant", values="brier").reindex(columns=variants)
    if pairs.shape != (16, 3) or not np.isfinite(pairs.to_numpy()).all():
        raise ValueError("Calibration Brier coverage differs")
    for values in pairs.to_numpy():
        a.plot(range(3), values, color="#d1d5db", lw=.55, zorder=1)
    for i, variant in enumerate(variants):
        vals = pairs[variant].to_numpy()
        a.scatter(np.full(16, i) + np.linspace(-.07, .07, 16), vals, s=8, color="#616d7a", zorder=2)
        a.scatter([i], [vals.mean()], s=28, marker="D", color="#152b42", edgecolors="white", lw=.4, zorder=3)
    a.set(xticks=range(3), xticklabels=["Raw\nagreement", "Logistic\nrecalibration", "Development\nconstant"],
          xlim=(-.4, 2.4), ylim=(0, .5), yticks=[0, .1, .2, .3, .4, .5], ylabel="Brier score")
    grid(a)

    panel(f, "D", 85, 79)
    a = axes(f, 107, 90, 54, 49)
    risk_name = "calibration/calibration_risk_coverage.csv"
    risk = table(risk_name)
    risk = risk[risk.method.eq("leiden") & risk.model_family.eq("openai")
                & risk.variant.isin(["raw_agreement", "recalibrated"]) & risk.region.ne("pooled")]
    regions = sorted(risk.region.unique())
    if len(regions) != 2:
        raise ValueError("Risk display requires both test regions")
    region_config = "configs/figure_04_historical_claude.json"
    names = json.loads((ROOT / region_config).read_text())["regions"]
    handles = []
    for region, color in zip(regions, ["#2864a5", "#b55224"]):
        handles.append(Line2D([], [], color=color, lw=1, label=names[region]["name"]))
        for variant, linestyle, marker in [("raw_agreement", "-", "o"), ("recalibrated", "--", "s")]:
            selected = risk[risk.region.eq(region) & risk.variant.eq(variant)].copy()
            # Undefined selective risk at zero retained cells never becomes 0.
            selected = selected[selected.retained_cells.gt(0) & selected.risk.notna()].sort_values("coverage")
            a.plot(selected.coverage * 100, selected.risk * 100, color=color, ls=linestyle,
                   marker=marker, markersize=2.5, lw=.85)
    a.set(xlim=(0, 100), ylim=(0, 100), xticks=[0, 25, 50, 75, 100], yticks=[0, 25, 50, 75, 100],
          xlabel="Coverage (%)", ylabel="Selective reference error (%)")
    grid(a)
    handles.extend([Line2D([], [], color="#444444", ls="-", marker="o", markersize=2.5, label="Raw agreement"),
                    Line2D([], [], color="#444444", ls="--", marker="s", markersize=2.5, label="Recalibrated")])
    f.legend(handles=handles, loc="upper center", bbox_to_anchor=(.76, 1 - 150 / 171), ncol=2,
             fontsize=5.5, columnspacing=.8, handlelength=1.7)
    if completed:
        source_hashes = {
            **inputs("set_metrics.csv", directory=COMPLETED_DATA),
            **inputs(name, risk_name),
            **annotation_inputs("metrics.csv"),
            region_config: sha(ROOT / region_config),
        }
        return finish(f, "Figure_S2", out, source_hashes, notes=[
            "A/B: four Opus and one Astra method-name contrast, and a neighborhood contrast for each model.",
            "The Astra controls used native OpenAI Batch and reused the accepted OpenRouter Batch baseline.",
            "C/D: exploratory calibration uses disjoint clusters and regions.",
        ])
    return finish(f, "Figure_S9", out, inputs("set_metrics.csv", name, risk_name), notes=[
        "A/B: Opus5.5 single-generation controls; matched means-plus-fractions baseline; equal-weighted two test-region agreement.",
        "A: method rows share the primary benchmark descending mean four-model macro-F1 ranking. B/C retain their evidence/calibration progression, and D keeps ascending numeric coverage.",
        "C: each line/dot is one of16method/model conditions; diamonds are arithmetic means of equal-region Brier scores. Lower is better.",
        "D: illustrative Astra-Leiden selective-risk curves by test region, on hash-held-out evaluation clusters. All tied scores are retained together; undefined zero-retention risk is omitted.",
        "Calibration development/evaluation use disjoint clusters and disjoint regions. It estimates within-donor reference agreement, not native confidence, repeatability or biological correctness.",
        "Eight separately submitted Astra named/neighborhood requests remain pending and do not supply plotted results.",
    ])


RENDERERS = {"S8": figure_s8, "S9": figure_s9}


def main():
    parser = argparse.ArgumentParser(description="Render completed manuscript Figures S2 and S10 offline.")
    parser.add_argument("--output", type=Path, required=True, help="New directory for the figure files")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    figure_s9(args.output, completed=True)
    figure_s8(args.output, completed=True)


if __name__ == "__main__":
    main()
