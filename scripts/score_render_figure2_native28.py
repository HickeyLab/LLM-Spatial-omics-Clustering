#!/usr/bin/env python3
"""Score and render Figure 2 with the original 28 reference labels.

Use the frozen B004 partitions and the packed, pre-update manuscript artwork.
The reference estimands, plotted scores, and conditional tests use the same cells.
No model inference or clustering is performed.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
from itertools import product
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import permutation_test

BASE_COMMIT = "ae0005e834f2c55f8d944973ce44b6da2008661a"
BASE_PATH = "figures/current_manuscript/PNG/Figure_2.png"
BASE_SHA = "cd25f997441b88fc06ea06d23f05b349f552144d116cb1ee91324fc3c78c55fd"
FROZEN = Path("data/frozen/clustering47_primary_20261108")
METHODS = {"leiden": "Leiden", "flowsom": "FlowSOM", "pixie": "PIXIE", "spatialsort": "SpatialSort"}
COHORT = 220_082
REGIONS = 8
NOISE = 10_495


def checked_sha(data, expected, description):
    actual = sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(f"Unexpected {description} SHA-256: {actual}")
    return actual


def class_scores(cells, method, labels):
    counts = pd.crosstab(cells[method], cells.cell_type_update).reindex(columns=labels, fill_value=0)
    majority = counts.idxmax(axis=1)  # labels are in lexical order for ties
    match = pd.crosstab(cells.cell_type_update, cells[method].map(majority)).reindex(
        index=labels, columns=labels, fill_value=0
    )
    tp = pd.Series(np.diag(match), index=labels, dtype=float)
    denominators = match.sum(axis=1)
    predicted = match.sum(axis=0)
    f1_denominator = denominators + predicted
    precision = (tp / predicted.replace(0, np.nan)).fillna(0)
    f1 = (2 * tp / f1_denominator.replace(0, np.nan)).fillna(0)
    recall = (tp / denominators.replace(0, np.nan)).fillna(0)
    return precision, f1, recall, float(f1.dot(denominators) / len(cells)), float(tp.sum() / len(cells))


def score(cells, expected):
    keys = ["File_ID", "ID"]
    labels = sorted(cells.cell_type_update.unique())
    if (len(cells) != COHORT or cells[keys].duplicated().any() or len(labels) != 28
            or cells.cell_type_update.eq("Noise").sum() != NOISE or cells.File_ID.nunique() != REGIONS):
        raise ValueError("Frozen B004 cell identity or label universe changed")
    f1, recall = pd.DataFrame(index=labels), pd.DataFrame(index=labels)
    counts = cells.cell_type_update.value_counts().sort_index().sort_values(ascending=False, kind="stable")
    rows, class_rows = [], []
    for method, display in METHODS.items():
        precision, f1[display], recall[display], _, _ = class_scores(cells, method, labels)
        class_rows.extend({"cell_type": label, "precision": precision[label],
                           "recall": recall.at[label, display], "f1": f1.at[label, display],
                           "n_cells": counts[label], "method": display} for label in labels)
        for region, subset in cells.groupby("File_ID"):
            _, _, _, weighted_f1, purity = class_scores(subset, method, labels)
            rows.append({"method": display, "method_key": method, "region": region,
                         "n_cells": len(subset), "weighted_f1": weighted_f1,
                         "cluster_purity": purity, "n_clusters": subset[method].nunique()})
    regional = pd.DataFrame(rows)
    baseline = expected.query("noise_policy == 'include' and region != 'ALL'").rename(columns={
        "method": "method_key", "majority_weighted_f1": "weighted_f1", "purity": "cluster_purity"
    })
    stats = ["n_cells", "weighted_f1", "cluster_purity", "n_clusters"]
    np.testing.assert_allclose(regional.set_index(["method_key", "region"]).sort_index()[stats],
                              baseline.set_index(["method_key", "region"]).sort_index()[stats],
                              atol=1e-13, rtol=0)
    ordered_labels = f1.mean(axis=1).sort_values(ascending=False, kind="stable").index
    return counts, regional, f1.loc[ordered_labels], recall.loc[ordered_labels], pd.DataFrame(class_rows)


def sign_p(differences):
    signs = np.array(list(product([-1, 1], repeat=len(differences))))
    null = np.abs((signs * differences).mean(axis=1))
    return float(np.mean(null >= abs(differences.mean()) - 1e-12))


def bootstrap_bounds(differences):
    draws = np.random.default_rng(42).integers(0, len(differences), (10_000, len(differences)))
    return np.quantile(differences[draws].mean(axis=1), [0.025, 0.975])


def holm_adjust(raw):
    order = np.argsort(raw, kind="stable")
    adjusted = np.empty(len(raw))
    adjusted[order] = np.minimum(1, np.maximum.accumulate(raw[order] * np.arange(len(raw), 0, -1)))
    return adjusted


def conditional_comparisons(regional, legacy, legacy_observations):
    lookup = regional.set_index(["method_key", "region"])
    table = legacy.copy()
    observations = legacy_observations.copy()
    for i, row in observations.iterrows():
        a = lookup.at[(row.condition_a, row.region), row.metric]
        b = lookup.at[(row.condition_b, row.region), row.metric]
        observations.loc[i, ["value_a", "value_b", "difference_pp"]] = a, b, 100 * (a - b)

    for i, row in table.iterrows():
        def matching(frame):
            return frame[
                (frame.metric == row.metric) & (frame.condition_a == row.condition_a)
                & (frame.condition_b == row.condition_b)
            ].sort_values("region")

        # Verify the historical bootstrap convention against the frozen table
        # before carrying it over to the same 12 contrasts on the new vocabulary.
        historical = matching(legacy_observations)
        baseline = (historical.value_a - historical.value_b).to_numpy() * 100
        np.testing.assert_allclose(bootstrap_bounds(baseline),
                                   [row.region_interval_low_pp, row.region_interval_high_pp],
                                   rtol=0, atol=1e-12)
        current = matching(observations)
        deltas = current.difference_pp.to_numpy()
        if len(deltas) != REGIONS:
            raise ValueError("Each contrast requires eight paired regions")
        p = sign_p(deltas)
        scipy_p = permutation_test(
            (100 * current.value_a.to_numpy(), 100 * current.value_b.to_numpy()),
            lambda a, b: np.mean(a - b), permutation_type="samples", n_resamples=np.inf,
            alternative="two-sided", vectorized=False,
        ).pvalue
        np.testing.assert_allclose(p, scipy_p, rtol=0, atol=1e-14)
        lower, upper = bootstrap_bounds(deltas)
        fields = ["mean_a_percent", "mean_b_percent", "mean_difference_pp",
                  "median_difference_pp", "region_interval_low_pp", "region_interval_high_pp",
                  "raw_p", "scipy_p"]
        table.loc[i, fields] = [
            100 * current.value_a.mean(), 100 * current.value_b.mean(), deltas.mean(),
            np.median(deltas), lower, upper, p, scipy_p,
        ]
    table["holm_adjusted_p"] = holm_adjust(table.raw_p.to_numpy())
    table["holm_below_0_05"] = table.holm_adjusted_p.lt(.05)
    return table, observations


def render(base_bytes, output, counts, regional, f1, recall, palette, region_colors):
    original = Image.open(BytesIO(base_bytes))
    canvas = original.convert("RGB")
    width, height = canvas.size
    if (width, height) != (1455, 1800):
        raise ValueError("Unexpected packed Figure 2 canvas")
    dpi = float(original.info["dpi"][0])
    matplotlib.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 5, "axes.labelsize": 5, "xtick.labelsize": 5, "ytick.labelsize": 5,
        "axes.linewidth": .48, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.major.width": .45, "ytick.major.width": .45,
    })
    font_manager.findfont("Arial")
    # An exact integer-size Agg canvas keeps untouched panels pixel-identical.
    figure = plt.figure(figsize=(width / 200, height / 200), dpi=200, facecolor="white")
    point_conversion = dpi / 200

    def axes(x, y, w, h):
        return figure.add_axes((x / width, 1 - (y + h) / height, w / width, h / height))

    def letters(letter, x, y):
        figure.text(x / width, 1 - y / height, letter, fontsize=5.4 * point_conversion,
                    weight="bold", va="top")

    def text_size(axis, size=5):
        axis.tick_params(labelsize=size * point_conversion)

    # B. Keep the two equal-height ranked columns and the native reference palette.
    split_counts = [counts.iloc[:14], counts.iloc[14:]]
    for (left, block) in zip((260, 752), split_counts):
        axis = axes(left, 358, 184, 300)
        rows = np.arange(len(block))
        axis.barh(rows, block, color=[palette[label] for label in block.index],
                  height=.57, zorder=2)
        axis.set(yticks=rows, yticklabels=block.index, ylim=(13.5, -.5),
                 xticks=(0, 15_000, 30_000), xticklabels=("0", "15k", "30k"), xlim=(0, 33_000))
        axis.tick_params(axis="y", length=0, pad=1.7)
        axis.tick_params(axis="x", length=1.8, pad=1.2)
        text_size(axis)
        axis.spines["left"].set_visible(False)
        axis.spines["bottom"].set_color("#8c929a")
        axis.grid(axis="x", color="#d9d9d9", linewidth=.35, zorder=0)
        for row, count in enumerate(block):
            axis.text(1.33, row, f"{count:,}", transform=axis.get_yaxis_transform(),
                      fontsize=5 * point_conversion, ha="right", va="center")

    # E/G. The same method order and common metric axis are used in both panels.
    method_order = regional.groupby("method").weighted_f1.mean().sort_values(ascending=False).index
    for x, letter, key, title in [(144, "E", "weighted_f1", "Weighted F1"),
                                  (868, "G", "cluster_purity", "Cluster purity")]:
        letters(letter, x - 126, 1022)
        axis = axes(x, 1027, 548, 173)
        values = [regional[regional.method.eq(method)].sort_values("region")[key] for method in method_order]
        axis.boxplot(values, positions=range(4), widths=.48, showfliers=False, patch_artist=True,
                     boxprops={"facecolor": "#e5e7eb", "linewidth": .55},
                     medianprops={"color": "black", "linewidth": .65},
                     whiskerprops={"linewidth": .55}, capprops={"linewidth": .55})
        for position, method in enumerate(method_order):
            subset = regional[regional.method.eq(method)].sort_values("region")
            axis.scatter(position + np.linspace(-.08, .08, REGIONS), subset[key],
                         c=subset.region.map(region_colors), s=8 * point_conversion**2,
                         linewidths=0, zorder=3)
        axis.set(xticks=range(4), xticklabels=method_order, ylim=(.3, .9), yticks=[.3, .5, .7, .9])
        axis.set_ylabel(title, fontsize=5 * point_conversion, labelpad=3)
        axis.tick_params(length=2, pad=1.7)
        text_size(axis)
        axis.grid(axis="y", color="#d9d9d9", linewidth=.35)
        axis.set_axisbelow(True)

    # F/H. The space saved on the boxplots accommodates eight additional rows.
    for x, letter, matrix, scale, title in [(261, "F", f1, 1, "F1"),
                                             (985, "H", recall, 100, "Recall (%)")]:
        letters(letter, x - 244, 1248)
        plot_width, plot_y, plot_height = 365, 1314, 411
        axis = axes(x, plot_y, plot_width, plot_height)
        values = matrix[method_order].to_numpy() * scale
        n = len(matrix)
        artist = axis.pcolormesh(np.arange(5) - .5, np.arange(n + 1) - .5,
                                 values, cmap="RdYlGn", vmin=0, vmax=scale,
                                 edgecolors="white", linewidth=.2)
        axis.set(xlim=(-.5, 3.5), ylim=(n - .5, -.5), xticks=range(4),
                 xticklabels=method_order, yticks=range(n), yticklabels=matrix.index)
        axis.tick_params(length=0, pad=1.5)
        text_size(axis, 4.85)
        plt.setp(axis.get_xticklabels(), rotation=46, ha="right", rotation_mode="anchor")
        for spine in axis.spines.values():
            spine.set_visible(False)
        legend = axes(x, 1272, plot_width, 12)
        colorbar = figure.colorbar(artist, cax=legend, orientation="horizontal", ticks=[0, scale / 2, scale])
        colorbar.outline.set_visible(False)
        legend.tick_params(length=0, pad=1.0)
        text_size(legend)
        legend.set_title(title, fontsize=5 * point_conversion, pad=2.2)

        count_axis = axes(x + plot_width + 19, plot_y, 59, plot_height)
        count_axis.barh(range(n), counts.reindex(matrix.index), color="#64748b", height=.8)
        count_axis.set(ylim=(n - .5, -.5), yticks=[], xlim=(0, 35_000),
                       xticks=[0, 25_000], xticklabels=["0", "25k"])
        count_axis.set_xlabel("Cells", fontsize=5 * point_conversion, labelpad=3)
        count_axis.tick_params(length=1.4, pad=1.7)
        text_size(count_axis)
        count_axis.spines["left"].set_visible(False)

    figure.canvas.draw()
    rendered = Image.fromarray(np.asarray(figure.canvas.buffer_rgba()).copy()).convert("RGB")
    plt.close(figure)
    if rendered.size != canvas.size:
        raise ValueError(f"Unexpected renderer size: {rendered.size}")
    # Replace only B's plot and the lower E-H block. Retain the native panel
    # A/C/D artwork, the B/C panel letters and their surrounding white space.
    rectangles = [(45, 352, 1023, 686), (0, 1014, width, height)]
    for box in rectangles:
        canvas.paste(rendered.crop(box), box)
    canvas.save(output, dpi=original.info["dpi"])
    changed = np.any(np.asarray(canvas) != np.asarray(original.convert("RGB")), axis=2)
    for x0, y0, x1, y1 in rectangles:
        changed[y0:y1, x0:x1] = False
    if changed.any():
        raise ValueError("Pixels changed outside panels B and E-H")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--flat-inputs", type=Path, help="Optional directory of repository inputs by basename")
    p.add_argument("--base-figure", type=Path, help="The packed Figure 2 at the pinned revision")
    args = p.parse_args()
    root = args.root.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    def source(path):
        return args.flat_inputs / Path(path).name if args.flat_inputs else root / path

    if args.base_figure:
        base_bytes = args.base_figure.read_bytes()
    else:
        result = subprocess.run(["git", "show", f"{BASE_COMMIT}:{BASE_PATH}"], cwd=root,
                                capture_output=True, check=False)
        if result.returncode:
            p.error(f"Git history does not contain the packed Figure 2 at {BASE_COMMIT}. "
                    "Use a checkout with that commit or pass the checksum-pinned PNG via --base-figure.")
        base_bytes = result.stdout
    checked_sha(base_bytes, BASE_SHA, "packed Figure 2")

    manifest = json.loads(source(FROZEN / "manifest.json").read_text())
    reference = source(FROZEN / "reference_plot_cells.csv.gz")
    source_hash = checked_sha(reference.read_bytes(), manifest["files"][str(FROZEN / reference.name)]["sha256"], "frozen cells")
    expected = pd.read_csv(source(FROZEN / "fixed_raw_metrics.csv"))
    counts, regional, f1, recall, celltypes = score(pd.read_csv(reference), expected)
    table, observations = conditional_comparisons(
        regional, pd.read_csv(source(FROZEN / "conditional_comparisons.csv")),
        pd.read_csv(source(FROZEN / "paired_regional_observations.csv")),
    )
    outputs = {
        "reference_counts.csv": counts.rename_axis("cell_type").rename("n_cells").reset_index(),
        "regional_metrics.csv": regional,
        "panel_F_values.csv": f1.rename_axis("cell_type").reset_index(),
        "panel_H_values.csv": recall.rename_axis("cell_type").reset_index(),
        "celltype_metrics.csv": celltypes,
        "conditional_comparisons.csv": table,
        "paired_regional_observations.csv": observations,
    }
    for name, frame in outputs.items():
        frame.to_csv(out / name, index=False)
    colors = pd.read_csv(source(Path("configs/cell_type_colors.csv")))
    palette = colors.set_index("cell_type_update").color_hex.to_dict()
    region_cfg = json.loads(source(Path("configs/figure_04_historical_claude.json")).read_text())
    region_colors = {region: entry["color"] for region, entry in region_cfg["regions"].items()}
    render(base_bytes, out / "Figure_2.png", counts, regional, f1, recall, palette, region_colors)
    files = {name: {"sha256": sha256((out / name).read_bytes()).hexdigest(),
                    "bytes": (out / name).stat().st_size} for name in [*outputs, "Figure_2.png"]}
    metadata = {
        "base_commit": BASE_COMMIT,
        "base_image_sha256": BASE_SHA,
        "reference_cells_sha256": source_hash,
        "n_cells": COHORT, "n_reference_labels": 28, "n_noise": NOISE,
        "reference_vocabulary": "native labels including Noise",
        "majority_map": {"E": "within region", "F": "global", "G": "within region", "H": "global"},
        "tie_break": "alphabetical",
        "unchanged_raster_panels": ["A", "C", "D"],
        "files": files,
    }
    (out / "scoring_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(regional.groupby("method")[["weighted_f1", "cluster_purity"]].mean().mul(100).to_string())
    print(f"Minimum Holm-adjusted p: {table.holm_adjusted_p.min():.5f}")
    print((out / "Figure_2.png").resolve())


if __name__ == "__main__":
    main()
