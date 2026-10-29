#!/usr/bin/env python3
"""Replay historical Figure 4 from frozen Leiden assignments and Claude labels.

This module has no model client, network operation, clustering or fitting path.
The 300 Claude labels are taken from the checksum-pinned, previously audited
cluster-count table. The reference H5AD is read only for cell keys and labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = "configs/figure_04_historical_claude.json"
COMPONENTS = ("Direct reference agreement", "Net annotation gap", "Within-cluster bound gap")
COLORS = ("#2A6F5B", "#D9852B", "#D9D9D9")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked(path: Path, digest: str) -> Path:
    if not path.is_file():
        raise ValueError(f"Required frozen input is missing: {path}")
    if getattr(path.stat(), "st_flags", 0) & 0x40000000:
        raise ValueError(f"Download this cloud placeholder locally before replay: {path}")
    if sha256(path) != digest:
        raise ValueError(f"Frozen input SHA-256 differs: {path}")
    return path


def _column(obs, name):
    """Read an H5AD obs array, including categorical arrays, without loading X."""
    import h5py
    import numpy as np

    node = obs[name]
    if isinstance(node, h5py.Group):
        codes = node["codes"][:]
        if (codes < 0).any():
            raise ValueError(f"Missing H5AD observation: {name}")
        values = node["categories"].asstr()[:][codes]
    elif h5py.check_string_dtype(node.dtype):
        values = node.asstr()[:]
    else:
        values = node[:]
    return np.asarray(values)


def verify_clusters(rows, expected, cells=None):
    """Check both vocabulary identities and, when supplied, every keyed cell."""
    if len(rows) != 300 or len({r["cluster"] for r in rows}) != 300:
        raise ValueError("Expected exactly 300 unique frozen Leiden clusters")
    summaries = []
    for vocab in ("historical_21", "original_28"):
        n = bound = direct = minority = mismatches = 0
        groups = defaultdict(Counter)
        if cells is not None:
            for cell in cells:
                groups[cell["cluster"]][cell[vocab]] += 1
            if set(groups) != {r["cluster"] for r in rows}:
                raise ValueError("Cell-source cluster coverage differs")
        for row in rows:
            size = int(row["n_cells"])
            upper = int(row[vocab + "_bound_cells"])
            matches = int(row[vocab + "_direct_matches"])
            recovered = int(row[vocab + "_minority_matches"])
            disagreed = int(row[vocab + "_majority_mismatches"])
            if not 0 <= matches <= upper <= size or upper - matches != disagreed - recovered:
                raise ValueError(f"Invalid identity for cluster {row['cluster']}/{vocab}")
            if cells is not None:
                counts = groups[row["cluster"]]
                majority = min(k for k, v in counts.items() if v == max(counts.values()))
                actual_direct = counts[row["predicted_label"]]
                actual_minority = actual_direct if row["predicted_label"] != majority else 0
                actual_mismatch = max(counts.values()) if row["predicted_label"] != majority else 0
                actual = (sum(counts.values()), max(counts.values()), actual_direct,
                          actual_minority, actual_mismatch, majority)
                saved = (size, upper, matches, recovered, disagreed, row[vocab + "_majority_label"])
                if actual != saved:
                    raise ValueError(f"Cell-source counts differ for {row['cluster']}/{vocab}")
            n += size
            bound += upper
            direct += matches
            minority += recovered
            mismatches += disagreed
        observed = dict(reference_vocabulary=vocab, n_cells=n, direct_matches=direct,
                        cluster_majority_bound_cells=bound, within_cluster_bound_gap_cells=n-bound,
                        net_annotation_gap_cells=bound-direct, minority_matches=minority,
                        majority_mismatches=mismatches)
        saved = next(s for s in expected if s["reference_vocabulary"] == vocab)
        if any(observed[k] != saved[k] for k in observed):
            raise ValueError(f"Historical aggregate contract differs: {vocab}")
        if direct + (n - bound) + (bound - direct) != n:
            raise ValueError("Aggregate components do not sum to N")
        summaries.append(observed)
    return summaries


def load_replay(root=ROOT, h5ad_path=None):
    root = Path(root).resolve()
    config_path = root / CONFIG
    config = json.loads(config_path.read_text())
    specs = config["frozen_inputs"]
    for spec in specs.values():
        checked(root / spec["path"], spec["sha256"])
    audit = json.loads((root / specs["count_audit"]["path"]).read_text())
    with (root / specs["cluster_counts"]["path"]).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assignment_bytes = gzip.decompress((root / specs["assignments"]["path"]).read_bytes())
    if hashlib.sha256(assignment_bytes).hexdigest() != config["assignment_csv_sha256"]:
        raise ValueError("Decompressed Leiden assignment SHA-256 differs")
    assignments = list(csv.DictReader(io.StringIO(assignment_bytes.decode())))
    keys = [(r["File_ID"], int(r["ID"])) for r in assignments]
    if len(keys) != 220082 or len(set(keys)) != len(keys) or len({k[0] for k in keys}) != 8:
        raise ValueError("Expected 220,082 unique assignment keys from eight B004 regions")
    labels = {r["cluster"]: r["predicted_label"] for r in rows}
    cluster_sizes = Counter(r["cluster"] for r in assignments)
    if cluster_sizes != {r["cluster"]: int(r["n_cells"]) for r in rows}:
        raise ValueError("Frozen assignment sizes do not match the Claude count audit")
    h5ad = checked(Path(h5ad_path or root / config["reference_h5ad"]["path"]),
                   config["reference_h5ad"]["sha256"])
    import h5py

    with h5py.File(h5ad, "r") as handle:
        files = _column(handle["obs"], "File_ID")
        ids = _column(handle["obs"], "ID")
        reference = _column(handle["obs"], "cell_type_update")
    reference_by_key = {}
    for file_id, cell_id, truth in zip(files, ids, reference):
        key = (str(file_id), int(cell_id))
        if key in reference_by_key:
            raise ValueError("Duplicate H5AD cell key")
        reference_by_key[key] = str(truth)
    if set(keys) != set(reference_by_key):
        raise ValueError("H5AD and Leiden assignments must cover exactly the same cell keys")
    cells = []
    for key, assignment in zip(keys, assignments):
        original = reference_by_key[key]
        cluster = assignment["cluster"]
        cells.append(dict(File_ID=key[0], ID=key[1], cluster=cluster,
                          original_28=original, historical_21=audit["historical_harmonization"].get(original, original),
                          predicted_label=labels[cluster]))
    summaries = verify_clusters(rows, audit["summary"], cells)
    receipt = dict(schema_version="figure04.frozen_historical_claude_replay.v1",
                   focal_pair=config["focal_pair"], n_cells=len(cells), n_clusters=len(rows),
                   exact_key_join=True, every_cluster_recomputed=True, minority_matches_retained=True,
                   inference_calls=0, classifier_fits=0, clustering_fits=0,
                   reference_h5ad_sha256=sha256(h5ad),
                   frozen_inputs=specs, config_sha256=sha256(config_path),
                   replay_source_sha256=sha256(Path(__file__)), summary=summaries,
                   historical_source_inputs=audit["source_inputs"],
                   source_scope="Cluster labels and archived counts are checksum-verified. All cell counts are recomputed from the pinned reference H5AD and exact frozen assignments. Archived raw API responses are not re-parsed by this replay.",
                   interpretation=config["interpretation"])
    return dict(root=root, config=config, audit=audit, rows=rows, cells=cells, receipt=receipt)


def confusion(cells, labels):
    import numpy as np

    lookup = {label: i for i, label in enumerate(labels)}
    counts = np.zeros((len(labels), len(labels)), dtype=int)
    for cell in cells:
        counts[lookup[cell["historical_21"]], lookup[cell["predicted_label"]]] += 1
    return counts


def f1(counts):
    import numpy as np

    denominator = counts.sum(axis=0) + counts.sum(axis=1)
    return np.divide(2 * counts.diagonal(), denominator,
                     out=np.zeros(len(denominator), dtype=float), where=denominator != 0)


def render_panels(replay):
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch
    import numpy as np

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    panels = {}
    figure, ax = plt.subplots(figsize=(12, 2.0))
    ax.set(xlim=(0, 12), ylim=(0, 2))
    ax.axis("off")
    for i, text in enumerate(("Frozen Leiden partition\n300 clusters", "Archived Claude labels\nleiden__claude", "Exact cell-key join\n220,082 cells", "Historical reference\nagreement diagnostics")):
        x = i * 3 + .12
        ax.add_patch(FancyBboxPatch((x, .4), 2.65, .9, boxstyle="round,pad=.06",
                                    facecolor="#edf2f5", edgecolor="#445566"))
        ax.text(x + 1.325, .85, text, ha="center", va="center")
        if i < 3:
            ax.add_patch(FancyArrowPatch((x + 2.72, .85), (x + 2.95, .85), arrowstyle="->", mutation_scale=14))
    ax.set_title("A  Historical Leiden–Claude workflow", loc="left")
    figure.tight_layout()
    panels["A"] = figure

    cells = replay["cells"]
    labels = sorted({c["historical_21"] for c in cells} | {c["predicted_label"] for c in cells})
    if len(labels) != 21:
        raise ValueError("Expected the historical 21-label vocabulary, including Noise")
    matrix = confusion(cells, labels)
    normalized = np.divide(matrix, matrix.sum(axis=1, keepdims=True),
                           out=np.zeros(matrix.shape, dtype=float), where=matrix.sum(axis=1, keepdims=True) != 0)
    figure, ax = plt.subplots(figsize=(8.6, 7.6))
    image = ax.imshow(normalized, cmap="RdYlGn", vmin=0, vmax=1)
    ax.set(xticks=range(len(labels)), yticks=range(len(labels)), xticklabels=labels,
           yticklabels=labels, xlabel="Claude prediction on frozen Leiden clusters", ylabel="Historical reference label",
           title="B  Leiden–Claude row-normalized reference agreement")
    plt.setp(ax.get_xticklabels(), rotation=90, fontsize=8)
    plt.setp(ax.get_yticklabels(), fontsize=8)
    figure.colorbar(image, ax=ax, label="Fraction", shrink=.8)
    figure.tight_layout()
    panels["B"] = figure

    figure, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(range(len(labels)), f1(matrix), color="#E5E7EB", edgecolor="#9CA3AF", label="Pooled cells")
    regions = replay["config"]["regions"]
    for file_id, region in regions.items():
        subset = [c for c in cells if c["File_ID"] == file_id]
        if not subset:
            raise ValueError(f"Missing region: {file_id}")
        ax.scatter(np.arange(len(labels)), f1(confusion(subset, labels)), s=18,
                   color=region["color"], edgecolors="black", linewidths=.25, label=region["name"], zorder=3)
    ax.set(xticks=range(len(labels)), xticklabels=labels, ylim=(0, 1.04), ylabel="F1 against historical reference",
           title="C  Historical Leiden–Claude F1 by cell type and tissue region")
    plt.setp(ax.get_xticklabels(), rotation=60, ha="right", fontsize=8)
    ax.legend(fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(.5, 1.0))
    figure.tight_layout()
    panels["C"] = figure

    by_cluster = {r["cluster"]: r for r in replay["rows"]}
    examples = replay["config"]["example_clusters"]
    figure, ax = plt.subplots(figsize=(10, 3.9))
    left = np.zeros(len(examples))
    for index, (label, color) in enumerate(zip(COMPONENTS, COLORS)):
        values = []
        for cluster in examples:
            r = by_cluster[cluster]
            n, upper, direct = int(r["n_cells"]), int(r["historical_21_bound_cells"]), int(r["historical_21_direct_matches"])
            values.append((direct, upper-direct, n-upper)[index] / n)
        ax.barh(range(len(examples)), values, left=left, color=color, label=label)
        left += values
    names = [f"{c}   Majority: {by_cluster[c]['historical_21_majority_label']}\nClaude: {by_cluster[c]['predicted_label']}" for c in examples]
    ax.set(yticks=range(len(examples)), yticklabels=names, xlim=(0, 1), xlabel="Fraction of cells in cluster",
           title="D  Historical majority-based diagnostic")
    ax.invert_yaxis()
    ax.legend(handles=[Patch(color=c, label=l) for l, c in zip(COMPONENTS, COLORS)],
              loc="upper center", bbox_to_anchor=(.5, -.23), ncol=3, fontsize=8)
    figure.tight_layout()
    panels["D"] = figure

    summary = replay["receipt"]["summary"][0]
    counts = (summary["direct_matches"], summary["net_annotation_gap_cells"], summary["within_cluster_bound_gap_cells"])
    figure, ax = plt.subplots(figsize=(10, 2.8))
    left = 0
    for count, label, color in zip(counts, COMPONENTS, COLORS):
        value = count / summary["n_cells"]
        ax.barh([0], [value], left=[left], color=color, label=label)
        ax.text(left + value / 2, 0, f"{value:.3%}\n{count:,} cells", ha="center", va="center", fontsize=9)
        left += value
    ax.set(yticks=[], xlim=(0, 1), xlabel="Cell-count-weighted fraction",
           title="E  Historical majority-based diagnostic for Leiden–Claude")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.32), ncol=3, fontsize=8)
    figure.tight_layout()
    panels["E"] = figure
    return panels


def export(replay, panels, output_root):
    """Write a numerical replay and panels, without overwriting publication art."""
    from matplotlib.backends.backend_pdf import PdfPages

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for panel, figure in panels.items():
        path = output_root / f"Figure_04_{panel}_historical_claude.png"
        figure.savefig(path, dpi=200, bbox_inches="tight")
        outputs[path.name] = sha256(path)
    path = output_root / "Figure_04_historical_claude_replay.pdf"
    with PdfPages(path) as pdf:
        for figure in panels.values():
            pdf.savefig(figure, bbox_inches="tight")
    outputs[path.name] = sha256(path)
    path = output_root / "frozen_claude_cluster_map.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("cluster", "predicted_label"))
        writer.writerows((r["cluster"], r["predicted_label"]) for r in replay["rows"])
    outputs[path.name] = sha256(path)
    cells = replay["cells"]
    labels = sorted({c["historical_21"] for c in cells} | {c["predicted_label"] for c in cells})
    matrix = confusion(cells, labels)
    path = output_root / "panel_B_confusion_counts.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("reference_label", *labels))
        writer.writerows((label, *counts) for label, counts in zip(labels, matrix))
    outputs[path.name] = sha256(path)
    path = output_root / "panel_C_pooled_and_regional_f1.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("File_ID", "region", "label", "reference_cells", "predicted_cells", "true_positives", "f1"))
        groups = [("pooled", "Pooled cells", cells)]
        groups.extend((file_id, region["name"], [c for c in cells if c["File_ID"] == file_id])
                      for file_id, region in replay["config"]["regions"].items())
        for file_id, region, subset in groups:
            counts = confusion(subset, labels)
            for i, value in enumerate(f1(counts)):
                writer.writerow((file_id, region, labels[i], counts.sum(axis=1)[i],
                                 counts.sum(axis=0)[i], counts[i, i], value))
    outputs[path.name] = sha256(path)
    receipt = dict(replay["receipt"], outputs=outputs,
                   artwork_scope="Numerical panels A-E are redrawn from frozen data. The exact publication layout remains the separately versioned preview, which is never read as a numerical input.")
    path = output_root / "replay_receipt.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--h5ad", type=Path)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    replay = load_replay(args.root, args.h5ad)
    output = args.output_root or args.root / "outputs/source_rebuilt/figure_04_historical_claude"
    receipt = export(replay, render_panels(replay), output)
    print(f"Verified 220,082 keyed cells, 300 frozen Claude labels and both reference vocabularies.\n{receipt}")


if __name__ == "__main__":
    main()
