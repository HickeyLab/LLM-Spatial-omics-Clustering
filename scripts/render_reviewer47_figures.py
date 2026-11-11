"""Render B004 reviewer controls from checksum-bound completed offline results.

There is no inference, fitting, scheduler or network path. Missing scientific
conditions are masked before plotting; partial accuracy is never displayed.
"""
from __future__ import annotations

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

DATA = ROOT / "data/frozen/reviewer47_results_20261111"
FAMILIES = ["openai", "anthropic", "google", "deepseek"]
MODELS = ["GPT-6 Astra", "Claude Opus 5.5", "Gemini 4 Argon", "DeepSeek V4.1 Flash 1017"]
ARMS = ["selected_names", "selected_means", "all_means", "all_means_fractions"]
ARM_LABELS = ["Selected\nnames", "Selected\nmeans", "All\nmeans", "Means +\nfractions"]


def checked_path(name):
    manifest = json.loads((DATA / "manifest.json").read_text())
    spec = manifest["files"][name]
    expected = spec["sha256"] if isinstance(spec, dict) else spec
    path = DATA / name
    if sha(path) != expected:
        raise ValueError("Frozen reviewer result changed: " + name)
    return path


def table(name, **kwargs):
    return pd.read_csv(checked_path(name), **kwargs)


def inputs(*names):
    return {str((DATA / n).relative_to(ROOT)): sha(checked_path(n)) for n in names}


def complete_sets():
    rows = table("set_metrics.csv")
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
    return rows


def representation_matrix(rows, family):
    selected = rows[rows.family.eq(family) & rows.arm.isin(ARMS)]
    if len(selected) != 16:
        raise ValueError("Representation Cartesian coverage differs")
    return selected.pivot(index="method", columns="arm", values="agreement").reindex(
        index=METHOD_KEYS, columns=ARMS).to_numpy(dtype=float) * 100


def figure_s8(out):
    rows = complete_sets()
    f = figure(137)
    for i, family in enumerate(FAMILIES):
        x = 3 + (i % 2) * 82
        y = 3 + (i // 2) * 66
        panel(f, chr(65 + i), x, y)
        text(f, x + 42, y, MODELS[i], size=6.5, ha="center", weight="bold")
        a = axes(f, x + 22, y + 11, 48, 35)
        matrix = representation_matrix(rows, family)
        artist = heatmap(a, matrix, METHODS, ARM_LABELS, 0, 100,
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
    return finish(f, "Figure_S8", out, inputs("set_metrics.csv"), notes=[
        "Equal-weighted agreement across the two B004 test regions; fixed 28-label vocabulary including Noise.",
        "Four frozen partitions and one generation per condition. Partial conditions are masked as Pending, not scored.",
        "Selected names and selected means use at most six label-blind selected markers; full arms use all47 markers.",
    ])


def control_rows():
    rows = complete_sets()
    return rows[rows.family.eq("anthropic")].copy()


def values_for(rows, arm):
    selected = rows[rows.arm.eq(arm)]
    if not selected.status.eq("complete").all():
        raise ValueError("A plotted Opus control is incomplete")
    return selected.set_index("method").agreement.reindex(METHOD_KEYS).to_numpy(dtype=float) * 100


def figure_s9(out):
    rows = control_rows()
    f = figure(171)
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
    a.set(yticks=range(4), yticklabels=METHODS, ylim=(3.5, -.5), xlim=(0, 100),
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
    names = json.loads((ROOT / "configs/figure_04_historical_claude.json").read_text())["regions"]
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
    return finish(f, "Figure_S9", out, inputs("set_metrics.csv", name, risk_name), notes=[
        "A/B: Opus5.5 single-generation controls; matched means-plus-fractions baseline; equal-weighted two test-region agreement.",
        "C: each line/dot is one of16method/model conditions; diamonds are arithmetic means of equal-region Brier scores. Lower is better.",
        "D: illustrative Astra-Leiden selective-risk curves by test region, on hash-held-out evaluation clusters. All tied scores are retained together; undefined zero-retention risk is omitted.",
        "Calibration development/evaluation use disjoint clusters and disjoint regions. It estimates within-donor reference agreement, not native confidence, repeatability or biological correctness.",
        "Eight separately submitted Astra named/neighborhood requests remain pending and do not supply plotted results.",
    ])


RENDERERS = {"S8": figure_s8, "S9": figure_s9}
