"""Build IEEE-style native-table fragments from frozen B004 reviewer results.

This offline exporter reproduces the current non-donor supplementary tables.
It reads checksum-bound results and formats them without inference or fitting.
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
sys.path.insert(0, str(ROOT / "scripts/revision"))
import render_ieee_tables as style

PRIMARY = ROOT / "data/frozen/annotation47_results_20261111"
CLUSTERING = ROOT / "data/frozen/clustering47_primary_20261108"
REVIEWER = ROOT / "data/frozen/reviewer47_results_20261111"
DEEPSEEK = ROOT / "data/frozen/reviewer47_deepseek_completion_20261115"
COMPLETED = ROOT / "data/frozen/astra_prompt_controls_results_20261115"
OUTPUT = ROOT / "docs/tables/ieee_reviewer47_20261119"
METHODS = ["leiden", "flowsom", "spatialsort", "pixie_tiff"]
METHOD_LABELS = dict(zip(METHODS, ["Leiden", "FlowSOM", "SpatialSort", "PIXIE"]))
MODEL_LABELS = {
    "openai": "GPT-6 Astra",
    "anthropic": "Claude Opus 5.5",
    "google": "Gemini 4 Argon",
    "deepseek": "DeepSeek V4.1 Flash 1017",
}
ARM_LABELS = {
    "selected_names": "Selected marker names",
    "selected_means": "Selected marker means",
    "all_means": "All-marker means",
    "all_means_fractions": "All-marker means plus fractions",
}


TABLE_NOTES = {
    "S1": (
        "Counts are pooled across the eight B004 regions. Processed counts refer to segmentation objects "
        "retained in the processed H5ADs. Matched counts include objects accepted by directed "
        "nearest-neighbor matching within 10 source-coordinate units after swapping the reference x and y "
        "coordinates. Multiple segmentation objects could match the same reference cell. Shared objects "
        "had the same CellID within a region and unchanged coordinates. Before-only and after-only counts "
        "were based on CellID, not saved row indices. Paired F1 evaluation also required an accepted "
        "match to the same reference cell and label in both conditions, so the shared-ID column is not "
        "its final scoring denominator. These counts describe retention and matching, not "
        "segmentation-boundary accuracy."
    ),
    "S2A": (
        "Leiden, FlowSOM and SpatialSort used 47 protein markers. PIXIE selected 47 protein channels and "
        "Hoechst1 DNA signal from the 59 available image channels, then converted pixel-cluster "
        "assignments into vectors of pixel-metacluster fractions. Pixel-level and cell-level "
        "configurations are reported separately for PIXIE."
    ),
    "S6a": (
        "Means are the transformed and standardized cluster-level marker-expression means defined in "
        "Section 2.4. Positive fractions are the per-marker proportions of cells with positive processed "
        "expression. Values are single-run outcomes averaged equally across the two B004 test regions. "
        "Paired changes subtract agreement using all-marker means from agreement using all-marker means "
        "plus fractions, in percentage points (pp). Missing or invalid predictions remain errors in the "
        "full planned denominator. All planned predictions were delivered; paired changes therefore "
        "reflect changes between valid labels."
    ),
    "S6d": (
        "Requests used supported high-reasoning settings, no tools or retrieval, at most 75 clusters per "
        "item, and no automatic model or provider fallback. Table S6d reports requested model identities, "
        "transport, supported seeds and combined output ceilings. Execution records preserve native "
        "OpenAI and OpenRouter bindings, routes, attempt status, usage and confirmed charges for each "
        "physical generation. Requests and recoveries are linked to prompt, parser and source hashes. "
        "Requested output ceilings are distinct from observed token use, and recoveries do not provide "
        "independent repetitions."
    ),
    "S8": (
        "Means are the transformed and standardized cluster-level marker-expression means defined in "
        "Section 2.4. Positive fractions are the per-marker proportions of cells with positive processed "
        "expression. Reference agreement and macro-F1 calculated using the original 28-label vocabulary "
        "average the two B004 test regions equally. All planned cluster predictions were delivered. Each "
        "condition has one accepted annotation per cluster."
    ),
    "S9": (
        "Each comparison reuses its blinded baseline containing all-marker means plus fractions. "
        "Reference agreement averages the two B004 test regions equally. Changed-cluster counts use all "
        "planned clusters. Astra macro-F1 calculated using the original 28-label vocabulary was 0.4490 "
        "for the baseline, 0.4458 with the method name and 0.4531 with neighborhood-expression summaries. "
        "Astra controls used native OpenAI Batch and reused the OpenRouter Batch baseline. These "
        "single-generation comparisons do not establish repeatability or a general prompt effect. Opus "
        "5.5 is Claude Opus 5.5, and Astra is GPT-6 Astra."
    ),
    "S10": (
        "Means are the transformed and standardized cluster-level marker-expression means defined in "
        "Section 2.4. Positive fractions are the per-marker proportions of cells with positive processed "
        "expression. Classifiers used cell-level reference labels from the B004 training regions, "
        "providing richer supervision than the LLM prompts. Hyperparameters were selected in the "
        "validation regions. Metrics average the two test regions equally. Macro-F1 calculated using the "
        "original 28-label vocabulary assigns zero F1 to absent classes."
    ),
    "S11": (
        "K100 and K200 were formed by cell-count-weighted Ward merging of frozen, full-precision cluster "
        "profiles, with merge mappings fixed before reference scoring. They do not represent clustering "
        "rerun at those target counts or tests of whether LLM rankings remain stable. Metrics average the "
        "two test regions equally."
    ),
    "S12": (
        "ECE is expected calibration error. Lower scores are better. Metrics give equal weight to the two "
        "test regions and use only evaluation clusters held out by the cluster-hash split, rather than "
        "the full benchmark population. Development and evaluation use nonoverlapping clusters and "
        "regions. Cross-model support has a denominator of four. This retrospective within-donor "
        "calibration measures reference agreement, not repeatability, an individual model’s confidence or "
        "biological certainty."
    ),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_path(bank, name):
    path = bank / name
    files = json.loads((bank / "manifest.json").read_text())["files"]
    spec = files.get(name) or files[str(path.relative_to(ROOT))]
    expected = spec["sha256"] if isinstance(spec, dict) else spec
    if sha(path) != expected:
        raise ValueError(f"Frozen table source changed: {path.relative_to(ROOT)}")
    return path


def number(value, *, scale=1, digits=4, signed=False):
    if pd.isna(value):
        raise ValueError("A current table metric is missing")
    return f"{value * scale:+.{digits}f}" if signed else f"{value * scale:.{digits}f}"


def table_specs():
    tables = {}

    def add(key, title, rows, weights, numeric, sources, note):
        if any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("Inconsistent table width: " + key)
        tables[key] = {"caption": f"Table {key}. {title}.", "rows": rows,
                       "weights": weights, "numeric": numeric, "note": note,
                       "sources": {str(p.relative_to(ROOT)): sha(p) for p in sources}}

    prior_ieee = ROOT / "docs/tables/ieee"
    source = prior_ieee / "source_tables.json"
    if sha(source) != json.loads((prior_ieee / "manifest.json").read_text())["source_tables_sha256"]:
        raise ValueError("Frozen S1 source changed")
    rows = json.loads(source.read_text())["tables"]["S1"]["rows"]
    add("S1", "REDSEA matching and cell retention audit", rows, style.WEIGHTS["S1"],
        style.NUMERIC["S1"], [source], TABLE_NOTES["S1"])

    source = checked_path(CLUSTERING, "current_tables.json")
    rows = next(table["rows"] for table in json.loads(source.read_text())["tables"] if table["label"] == "S2A")
    # The current display spells out the frozen inputs and uses the revised section reference.
    rows[1] = [
        "Clustering inputs", "47 marker-expression features", "47 marker-expression features",
        "47 marker-expression features, cell coordinates and a within-region 24-neighbor graph",
        "48 image channels and cell masks",
    ]
    rows[3][2] = rows[3][3] = "RobustScaler on all B004 cells"
    rows[4] = [
        "Configured and nonempty clusters", "300 and 300", "300 requested and 299 nonempty",
        "300 requested. 229 nonempty in the primary chain and 231 in the seed-43 comparison chain",
        "300 and 300",
    ]
    rows[6][1] = rows[7][1] = "See Leiden procedure in Section 2.3"
    rows[8][3] = "Sampling seeds 42 (primary) and 43 (comparison)"
    add("S2A", "Clustering configurations and hyperparameters", rows, style.WEIGHTS["S2A"],
        style.NUMERIC["S2A"], [source], TABLE_NOTES["S2A"])

    metric_source = checked_path(PRIMARY, "metrics.csv")
    pair_source = checked_path(PRIMARY, "paired_contrasts.csv")
    metrics = pd.read_csv(metric_source)
    metrics = metrics[metrics.population.eq("all_labels") & metrics.scope.eq("equal_test_regions")]
    pairs = pd.read_csv(pair_source)
    pairs = pairs[pairs.population.eq("all_labels") & pairs.scope.eq("equal_test_regions")]
    if len(metrics) != 32 or len(pairs) != 16 or not metrics.cell_delivery_coverage.eq(1).all():
        raise ValueError("Full-arm table denominator or delivery differs")
    rows = [["Clustering method", "Model", "All-marker means (%)",
             "All-marker means plus fractions (%)", "Paired change (pp)"]]
    for family, model in MODEL_LABELS.items():
        for method in METHODS:
            pair = pairs[pairs.method.eq(method) & pairs.model_family.eq(family)].iloc[0]
            arm_rows = metrics[metrics.method.eq(method) & metrics.model_family.eq(family)].set_index("arm")
            means, fractions = arm_rows.loc["all_means"], arm_rows.loc["all_means_fractions"]
            rows.append([METHOD_LABELS[method], model, number(means.agreement, scale=100, digits=2),
                         number(fractions.agreement, scale=100, digits=2),
                         number(pair.agreement_difference, scale=100, digits=2, signed=True)])
    add("S6a", "Paired reference agreement", rows, style.WEIGHTS["S6a"], style.NUMERIC["S6a"],
        [metric_source, pair_source], TABLE_NOTES["S6a"])

    setting_source = checked_path(DEEPSEEK, "model_settings.json")
    astra_source = checked_path(COMPLETED, "provider_batch.json")
    settings = json.loads(setting_source.read_text())["requests"]
    rows = [["Model", "Requested model ID", "Transport", "Reasoning", "Decoding fields sent"]]
    for family, model in MODEL_LABELS.items():
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
        transport = {
            "openai": "Batch", "anthropic": "Batch", "google": "Standard streaming",
            "deepseek": "Standard streaming and Batch",
        }[family]
        decoding = (f"Combined output ceiling {next(iter(ceilings)):,}, "
                    + (f"seed {seed}" if seed is not None else "seed omitted")
                    + ", temperature/top-p omitted")
        rows.append([model, ", ".join(sorted(model_ids)), transport, "high", decoding])
    add("S6d", "Model identities and inference settings", rows, style.WEIGHTS["S6d"],
        style.NUMERIC["S6d"], [setting_source, astra_source], TABLE_NOTES["S6d"])

    source = checked_path(COMPLETED, "set_metrics.csv")
    sets = pd.read_csv(source)
    representation = sets[sets.arm.isin(ARM_LABELS)]
    if (len(representation) != 64 or not representation.status.eq("complete").all()
            or not representation.accepted_requests.eq(representation.planned_requests).all()
            or not representation.delivered_clusters.eq(representation.planned_clusters).all()):
        raise ValueError("Incomplete marker-representation evidence")
    for (family, model), suffix in zip(MODEL_LABELS.items(), "abcd"):
        rows = [["Clustering method", "Input", "Agreement (%)", "Macro-F1"]]
        for method in METHODS:
            for arm in ARM_LABELS:
                selected = representation[representation.family.eq(family)
                                          & representation.method.eq(method)
                                          & representation.arm.eq(arm)]
                if len(selected) != 1:
                    raise ValueError("Representation table coverage differs")
                r = selected.iloc[0]
                rows.append([METHOD_LABELS[method], ARM_LABELS[arm], number(r.agreement, scale=100, digits=2),
                             number(r.fixed28_macro_f1)])
        add("S8" + suffix, model + " marker-representation comparison", rows, [22, 42, 20, 16],
            [2, 3], [source], TABLE_NOTES["S8"])

    source = checked_path(COMPLETED, "control_contrasts.csv")
    contrasts = pd.read_csv(source)
    if len(contrasts) != 7 or not contrasts.status.eq("complete").all():
        raise ValueError("Incomplete prompt-control contrasts")
    rows = [["Clustering method–LLM", "Control", "Blinded (%)", "Control (%)",
             "Change (pp)", "Changed clusters"]]
    comparisons = [("anthropic", method, "method_named") for method in METHODS]
    comparisons.extend([("anthropic", "leiden", "neighborhood"),
                        ("openai", "leiden", "method_named"),
                        ("openai", "leiden", "neighborhood")])
    for family, method, arm in comparisons:
        selected = contrasts[contrasts.family.eq(family) & contrasts.method.eq(method)
                             & contrasts.control_arm.eq(arm)]
        if len(selected) != 1:
            raise ValueError("Prompt-control table coverage differs")
        r = selected.iloc[0]
        model = "Astra" if family == "openai" else "Opus 5.5"
        label = "Method name" if arm == "method_named" else "Neighborhood"
        rows.append([METHOD_LABELS[method] + "–" + model, label,
                     number(r.baseline_agreement, scale=100, digits=2),
                     number(r.control_agreement, scale=100, digits=2),
                     number(r.agreement_difference, scale=100, digits=2, signed=True),
                     str(int(r.cluster_label_changes))])
    add("S9", "LLM matched-evidence prompt controls", rows, [25, 17, 14, 14, 14, 16],
        [2, 3, 4, 5], [source], TABLE_NOTES["S9"])

    path = checked_path(REVIEWER, "baselines/classifier_equal_test_region_metrics.csv")
    data = pd.read_csv(path)
    rows = [["Clustering method", "Classifier", "Input", "Agreement (%)", "Macro-F1"]]
    for method in METHODS:
        for classifier, label in [("nearest_centroid", "Nearest centroid"), ("logistic_regression", "Logistic regression")]:
            for arm in ["all_means", "all_means_fractions"]:
                r = data[data.method.eq(method) & data.classifier.eq(classifier) & data.arm.eq(arm)].iloc[0]
                rows.append([METHOD_LABELS[method], label, ARM_LABELS[arm], number(r.reference_agreement, scale=100, digits=2), number(r.macro_f1)])
    add("S10", "Conventional B004 annotation classifiers", rows, [18, 22, 27, 18, 15],
        [3, 4], [path], TABLE_NOTES["S10"])

    path = checked_path(REVIEWER, "granularity/equal_test_region_metrics.csv")
    data = pd.read_csv(path)
    rows = [["Clustering method", "Nonempty clusters", "Purity", "ARI", "NMI"]]
    for method in METHODS:
        selected = data[data.method.eq(method)].sort_values("k")
        if len(selected) != 3:
            raise ValueError("Granularity table expects K100/K200/primary")
        for r in selected.itertuples():
            rows.append([METHOD_LABELS[method], str(int(r.k)), number(r.purity), number(r.ari), number(r.nmi)])
    add("S11", "Effect of merging existing B004 clusters", rows, [24, 25, 17, 17, 17],
        [1, 2, 3, 4], [path], TABLE_NOTES["S11"])

    path = checked_path(REVIEWER, "calibration/calibration_equal_test_region_metrics.csv")
    data = pd.read_csv(path)
    variant_labels = [("raw_agreement", "Raw cross-model support"), ("recalibrated", "Logistic recalibration"), ("development_constant", "Development constant")]
    for (family, model), suffix in zip(MODEL_LABELS.items(), "abcd"):
        rows = [["Clustering method", "Score", "Brier", "Log loss", "ECE"]]
        for method in METHODS:
            for variant, label in variant_labels:
                r = data[data.method.eq(method) & data.model_family.eq(family) & data.variant.eq(variant)].iloc[0]
                rows.append([METHOD_LABELS[method], label, number(r.brier), number(r.log_loss), number(r.ece)])
        add("S12" + suffix, model + " cross-model support calibration", rows, [21, 30, 16, 17, 16],
            [2, 3, 4], [path], TABLE_NOTES["S12"])
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
        label, title = style.caption(key, spec["caption"])
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
        sources["tables"][key] = {"rows": rows, "caption": spec["caption"], "note": spec["note"], "cell_order_sha256": cell_sha, "sources": spec["sources"]}
        manifest["tables"][key] = {"caption_label": label, "caption_title": title, "caption": spec["caption"],
                                   "note": spec["note"], "rows_including_header": len(rows), "columns": len(rows[0]),
                                   "cell_order_sha256": cell_sha, "numeric_columns_zero_based": spec["numeric"],
                                   "render": preview, "sources": spec["sources"],
                                   "files": {suffix: {"sha256": sha(output / (key + suffix)), "bytes": (output / (key + suffix)).stat().st_size}
                                             for suffix in [".html", ".standalone.html", ".tsv", ".tex", ".pdf", ".png"]}}
        manifest["tables"][key]["csv_companion"] = {"path": "Table_" + key + ".csv", "sha256": sha(output / ("Table_" + key + ".csv"))}
        all_html.append(title_html + fragment + note_html)
    (output / "all_tables.html").write_text('<html><body>' + '\n'.join(all_html) + '</body></html>\n')
    (output / "source_tables.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False) + '\n')
    manifest["combined_files"] = {
        name: {"sha256": sha(output / name), "bytes": (output / name).stat().st_size}
        for name in ("all_tables.html", "source_tables.json")
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({"output": str(output), "table_count": len(specifications), "new_calls": 0}))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    render(parser.parse_args().output)
