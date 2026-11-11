"""Build IEEE-style native-table fragments from frozen B004 reviewer results.

This is an offline presentation exporter. It never runs inference or fits an
analysis. Pending conditions remain visibly pending in all public formats.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/revision"))
import render_ieee_tables as style
from render_reviewer47_figures import checked_path, complete_sets, FAMILIES, MODELS, ARMS

PRIMARY = ROOT / "data/frozen/annotation47_results_20261111"
OUTPUT = ROOT / "docs/tables/ieee_reviewer47_20261111"
METHODS = ["leiden", "flowsom", "spatialsort", "pixie_tiff"]
METHOD_LABELS = dict(zip(METHODS, ["Leiden", "FlowSOM", "SpatialSort", "PIXIE"]))
ARM_LABELS = dict(zip(ARMS, ["Selected names", "Selected means", "All means", "Means + fractions"]))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def primary_path(name):
    manifest = json.loads((PRIMARY / "manifest.json").read_text())
    spec = manifest["files"][name]
    expected = spec["sha256"] if isinstance(spec, dict) else spec
    path = PRIMARY / name
    if sha(path) != expected:
        raise ValueError("Primary table source changed: " + name)
    return path


def number(value, *, scale=1, digits=4, signed=False):
    if pd.isna(value):
        return "Pending"
    return f"{value * scale:+.{digits}f}" if signed else f"{value * scale:.{digits}f}"


def table_specs():
    tables = {}

    def add(key, title, rows, weights, numeric, sources, note):
        if any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("Inconsistent table width: " + key)
        tables[key] = {"caption_old": f"Table {key}. {title}.", "rows": rows,
                       "weights": weights, "numeric": numeric, "note": note,
                       "sources": {str(p.relative_to(ROOT)): sha(p) for p in sources}}

    metric_source = primary_path("metrics.csv")
    pair_source = primary_path("paired_contrasts.csv")
    metrics = pd.read_csv(metric_source)
    metrics = metrics[metrics.population.eq("all_labels") & metrics.scope.eq("equal_test_regions")]
    pairs = pd.read_csv(pair_source)
    pairs = pairs[pairs.population.eq("all_labels") & pairs.scope.eq("equal_test_regions")]
    if len(metrics) != 32 or len(pairs) != 16 or not metrics.cell_delivery_coverage.eq(1).all():
        raise ValueError("Full-arm table denominator or delivery differs")
    rows_a = [["Clustering", "Model", "Means (%)", "Means + fractions (%)", "Paired change (pp)"]]
    rows_b = [["Clustering", "Model", "Means macro-F1", "Means + fractions macro-F1", "Means coverage (%)", "Means + fractions coverage (%)"]]
    rows_c = [["Clustering", "Model", "Valid-label term (pp)", "Delivery term (pp)", "Total change (pp)"]]
    for family, model in zip(FAMILIES, MODELS):
        for method in METHODS:
            pair = pairs[pairs.method.eq(method) & pairs.model_family.eq(family)].iloc[0]
            arm_rows = metrics[metrics.method.eq(method) & metrics.model_family.eq(family)].set_index("arm")
            means, fractions = arm_rows.loc["all_means"], arm_rows.loc["all_means_fractions"]
            rows_a.append([METHOD_LABELS[method], model, number(means.agreement, scale=100, digits=2),
                           number(fractions.agreement, scale=100, digits=2), number(pair.agreement_difference, scale=100, digits=2, signed=True)])
            rows_b.append([METHOD_LABELS[method], model, number(means.fixed28_macro_f1), number(fractions.fixed28_macro_f1),
                           number(means.cell_delivery_coverage, scale=100, digits=2), number(fractions.cell_delivery_coverage, scale=100, digits=2)])
            # Both complete arms deliver every planned prediction, so the
            # delivery term is exactly zero and the valid-label term is delta.
            rows_c.append([METHOD_LABELS[method], model, number(pair.agreement_difference, scale=100, digits=2, signed=True),
                           "0.00", number(pair.agreement_difference, scale=100, digits=2, signed=True)])
    titles = {"S6a": "Paired reference agreement", "S6b": "Macro-F1 and prediction coverage", "S6c": "Decomposition of paired agreement changes"}
    for key, rows in [("S6a", rows_a), ("S6b", rows_b), ("S6c", rows_c)]:
        add(key, titles[key], rows, style.WEIGHTS[key], style.NUMERIC[key], [metric_source, pair_source],
            "Completed full-arm bank; equal weighting of two test regions; fixed 28-label vocabulary including Noise. One accepted annotation per cluster and condition; no repeated-call SD.")

    setting_source = checked_path("model_settings.json")
    settings = json.loads(setting_source.read_text())["requests"]
    rows = [["Model", "Requested model ID", "Transport", "Reasoning", "Decoding fields sent"]]
    for family, model in zip(FAMILIES, MODELS):
        accepted = [r for r in settings if r["family"] == family and r["status"] == "accepted"]
        logical = [r["logical_template_settings"] for r in accepted]
        efforts = {r["reasoning"]["effort"] for r in logical}
        ceilings = {r["max_tokens"] for r in logical}
        seeds = {r.get("seed") for r in logical}
        if efforts != {"high"} or len(ceilings) != 1 or len(seeds) != 1:
            raise ValueError("Accepted model settings differ within family")
        model_ids = {r["model"] for r in logical}
        model_ids.update(r["actual_wire_settings"]["model"] for r in accepted if r.get("actual_wire_settings"))
        seed = next(iter(seeds))
        transport = "Batch" if family in ["openai", "anthropic"] else "Standard streaming"
        decoding = f"Combined output ceiling {next(iter(ceilings)):,}; " + (f"seed {seed}" if seed is not None else "seed omitted") + "; temperature/top-p omitted"
        rows.append([model, "; ".join(sorted(model_ids)), transport, "high", decoding])
    add("S6d", "Model identities and inference settings", rows, style.WEIGHTS["S6d"], style.NUMERIC["S6d"], [setting_source],
        "Actual accepted settings are preserved per request with served model/provider, transport/recovery provenance and literal-body hashes. Exact accepted prior answers are reused once; interrupted or rejected attempts are separate physical records. One selected-means request and the separate eight-item Astra extension remain pending.")

    sets = complete_sets()
    for family, model, suffix in zip(FAMILIES, MODELS, "abcd"):
        rows = [["Clustering", "Input", "Agreement (%)", "Macro-F1", "Clusters delivered"]]
        for method in METHODS:
            for arm in ARMS:
                selected = sets[sets.family.eq(family) & sets.method.eq(method) & sets.arm.eq(arm)]
                if len(selected) != 1:
                    raise ValueError("Representation table coverage differs")
                r = selected.iloc[0]
                rows.append([METHOD_LABELS[method], ARM_LABELS[arm], number(r.agreement, scale=100, digits=2),
                             number(r.fixed28_macro_f1), f"{int(r.delivered_clusters)}/{int(r.planned_clusters)}"])
        add("S8" + suffix, model + " marker-representation comparison", rows, [16, 27, 19, 16, 22], [2, 3, 4],
            [checked_path("set_metrics.csv")],
            "Agreement and fixed-28-label macro-F1 average the two B004 test regions equally. Missing requests remain in planned coverage. A partial condition is Pending and has no public accuracy or F1.")

    contrasts = pd.read_csv(checked_path("control_contrasts.csv"))
    rows = [["Clustering", "Control", "Blinded (%)", "Control (%)", "Change (pp)", "Changed clusters"]]
    for method in METHODS:
        r = contrasts[contrasts.method.eq(method) & contrasts.control_arm.eq("method_named")].iloc[0]
        rows.append([METHOD_LABELS[method], "Method name", number(r.baseline_agreement, scale=100, digits=2),
                     number(r.control_agreement, scale=100, digits=2), number(r.agreement_difference, scale=100, digits=2, signed=True),
                     str(int(r.cluster_label_changes))])
    r = contrasts[contrasts.method.eq("leiden") & contrasts.control_arm.eq("neighborhood")].iloc[0]
    rows.append(["Leiden", "Neighborhood", number(r.baseline_agreement, scale=100, digits=2),
                 number(r.control_agreement, scale=100, digits=2), number(r.agreement_difference, scale=100, digits=2, signed=True),
                 str(int(r.cluster_label_changes))])
    add("S9", "Opus 5.5 matched prompt controls", rows, [15, 21, 16, 16, 16, 16], [2, 3, 4, 5],
        [checked_path("control_contrasts.csv")],
        "Each comparison reuses its blinded means-plus-fractions baseline. Agreement averages two test regions equally. Changed-cluster counts retain all planned clusters. The separately submitted Astra extension is pending.")

    path = checked_path("baselines/classifier_equal_test_region_metrics.csv")
    data = pd.read_csv(path)
    rows = [["Clustering", "Classifier", "Input", "Agreement (%)", "Macro-F1"]]
    for method in METHODS:
        for classifier, label in [("nearest_centroid", "Nearest centroid"), ("logistic_regression", "Logistic regression")]:
            for arm in ["all_means", "all_means_fractions"]:
                r = data[data.method.eq(method) & data.classifier.eq(classifier) & data.arm.eq(arm)].iloc[0]
                rows.append([METHOD_LABELS[method], label, ARM_LABELS[arm], number(r.reference_agreement, scale=100, digits=2), number(r.macro_f1)])
    add("S10", "Conventional B004 annotation classifiers", rows, [15, 25, 24, 20, 16], [3, 4], [path],
        "Classifiers used B004 training-region cell labels, richer supervision than the LLM prompts. Hyperparameters were chosen in validation regions. Metrics average the two test regions equally; fixed 28-label macro-F1 includes absent classes as zero.")

    path = checked_path("granularity/equal_test_region_metrics.csv")
    data = pd.read_csv(path)
    rows = [["Clustering", "Occupied clusters", "Purity", "ARI", "NMI"]]
    for method in METHODS:
        selected = data[data.method.eq(method)].sort_values("k")
        if len(selected) != 3:
            raise ValueError("Granularity table expects K100/K200/primary")
        for r in selected.itertuples():
            rows.append([METHOD_LABELS[method], str(int(r.k)), number(r.purity), number(r.ari), number(r.nmi)])
    add("S11", "B004 partition granularity sensitivity", rows, [24, 25, 17, 17, 17], [1, 2, 3, 4], [path],
        "K100 and K200 are cell-count-weighted Ward coarsenings of frozen full-precision cluster profiles, sealed before reference scoring. They are not native-K refits or LLM ranking-stability experiments. Metrics average the two test regions equally.")

    path = checked_path("calibration/calibration_equal_test_region_metrics.csv")
    data = pd.read_csv(path)
    variant_labels = [("raw_agreement", "Raw agreement"), ("recalibrated", "Logistic recalibration"), ("development_constant", "Development constant")]
    for family, model, suffix in zip(FAMILIES, MODELS, "abcd"):
        rows = [["Clustering", "Score", "Brier", "Log loss", "ECE"]]
        for method in METHODS:
            for variant, label in variant_labels:
                r = data[data.method.eq(method) & data.model_family.eq(family) & data.variant.eq(variant)].iloc[0]
                rows.append([METHOD_LABELS[method], label, number(r.brier), number(r.log_loss), number(r.ece)])
        add("S12" + suffix, model + " cross-model agreement calibration", rows, [20, 31, 16, 17, 16], [2, 3, 4], [path],
            "Lower scores are better. These are equal-test-region metrics on hash-held-out evaluation clusters, not the full benchmark population. Development uses disjoint clusters and regions. Agreement support has denominator four. This is retrospective within-donor reference-agreement calibration, not repeatability, native model confidence or biological certainty.")
    return tables


def render(output=OUTPUT):
    output.mkdir(parents=True, exist_ok=True)
    specifications = table_specs()
    manifest = {"schema": "reviewer47.ieee_tables.v1", "new_scientific_calls_or_fits": 0,
                "stable_supplementary_ids_preserved": True, "tables": {}}
    sources = {"schema": "reviewer47.ieee_table_cells.v1", "tables": {}}
    all_html = []
    for key, spec in specifications.items():
        rows = spec["rows"]
        style.WEIGHTS[key], style.NUMERIC[key] = spec["weights"], spec["numeric"]
        label, title = style.caption(key, spec["caption_old"])
        fragment = style.table_html(key, rows)
        title_html = '<p style="font-family:Times New Roman,Times,serif;font-size:10pt;font-weight:normal;text-align:center;color:#000;">' + html.escape(label) + '<br>' + html.escape(title) + '</p>'
        note_html = '<p style="font-family:Times New Roman,Times,serif;font-size:10pt;font-weight:normal;color:#000;">' + html.escape(spec["note"]) + '</p>'
        (output / (key + ".html")).write_text('<html><body>' + title_html + fragment + note_html + '</body></html>\n')
        (output / (key + ".standalone.html")).write_text('<!doctype html><meta charset="utf-8"><body style="margin:24px;background:white;">' + title_html + fragment + note_html + '</body>\n')
        with (output / (key + ".tsv")).open('w', newline='') as f:
            csv.writer(f, delimiter='\t', lineterminator='\n').writerows(rows)
        with (output / ("Table_" + key + ".csv")).open('w', newline='') as f:
            csv.writer(f, lineterminator='\n').writerows(rows)
        (output / (key + ".tex")).write_text(style.table_tex(key, rows, label, title))
        preview = style.render_preview(output / key, key, rows, label, title, note=spec["note"])
        cell_sha = hashlib.sha256(style.canonical_rows(rows)).hexdigest()
        sources["tables"][key] = {"rows": rows, "caption": spec["caption_old"], "note": spec["note"], "cell_order_sha256": cell_sha, "sources": spec["sources"]}
        manifest["tables"][key] = {"caption_label": label, "caption_title": title, "caption": spec["caption_old"],
                                   "note": spec["note"], "rows_including_header": len(rows), "columns": len(rows[0]),
                                   "cell_order_sha256": cell_sha, "numeric_columns_zero_based": spec["numeric"],
                                   "render": preview, "sources": spec["sources"],
                                   "files": {suffix: {"sha256": sha(output / (key + suffix)), "bytes": (output / (key + suffix)).stat().st_size}
                                             for suffix in [".html", ".standalone.html", ".tsv", ".tex", ".pdf", ".png"]}}
        manifest["tables"][key]["csv_companion"] = {"path": "Table_" + key + ".csv", "sha256": sha(output / ("Table_" + key + ".csv"))}
        if not key.startswith("S6"):
            all_html.append(title_html + fragment + note_html)
    (output / "all_new_tables.html").write_text('<html><body>' + '\n'.join(all_html) + '</body></html>\n')
    (output / "source_tables.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False) + '\n')
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({"output": str(output), "table_count": len(specifications), "new_tables": len(all_html), "new_calls": 0}))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    render(parser.parse_args().output)
