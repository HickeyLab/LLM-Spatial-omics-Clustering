"""Offline means-only presentation of the frozen paired experiment."""
from pathlib import Path
import argparse
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/frozen/manuscript_replay/paired'
OUT = ROOT / 'outputs/manuscript_replay/means_only'
MODELS = ['gpt', 'claude', 'gemini', 'deepseek']
METHODS = ['leiden', 'flowsom', 'spatialsort', 'pixie_tiff']
NAMES = {'gpt': 'GPT-5.6-Sol', 'claude': 'Claude Opus 5', 'gemini': 'Gemini 3.1 Pro Preview', 'deepseek': 'DeepSeek V4 Pro',
         'leiden': 'Leiden', 'flowsom': 'FlowSOM', 'spatialsort': 'SpatialSort', 'pixie_tiff': 'PIXIE'}
COLORS = ['#2864a5', '#b55224', '#337a58', '#77559a']
MARKERS = ['o', 's', '^', 'D']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    global SOURCE,OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=SOURCE)
    parser.add_argument('--output-dir',type=Path,default=OUT)
    args=parser.parse_args();SOURCE=args.input_dir;OUT=args.output_dir
    if OUT.resolve()==SOURCE.resolve():raise ValueError('Output must differ from frozen input directory')
    receipt = json.loads((SOURCE / 'scoring_receipt.json').read_text())
    source = SOURCE / 'paired_summary.csv'
    assert sha(source) == receipt['metric_sha256'][source.name]
    repeats = pd.read_csv(SOURCE / 'paired_repeat_metrics.csv')
    assert sha(SOURCE / 'paired_repeat_metrics.csv') == receipt['metric_sha256']['paired_repeat_metrics.csv']
    data = pd.read_csv(source)
    assert len(data) == 16 and data.n_repeats.eq(3).all()
    rows = []
    for method in METHODS:
        for model in MODELS:
            r = data[(data.method == method) & (data.model == model)].iloc[0]
            individual = repeats[(repeats.method == method) & (repeats.model == model)]
            values = {'clustering': NAMES[method], 'model': NAMES[model], 'repeats': 3}
            for metric, title, scale in [('agreement', 'reference_agreement_percent', 100), ('macro_f1', 'macro_f1', 1), ('coverage', 'coverage_percent', 100)]:
                mean, sd = individual[f'means_{metric}'].mean(), individual[f'means_{metric}'].std(ddof=1)
                np.testing.assert_allclose([mean, sd], [r[f'means_{metric}_mean'], r[f'means_{metric}_sd']], atol=1e-12, rtol=0)
                values[title] = mean * scale
                values[title + '_run_sd'] = sd * scale
            rows.append(values)
    OUT.mkdir(parents=True,exist_ok=True)
    table = pd.DataFrame(rows)
    table.to_csv(OUT / 'means_only_results.csv', index=False)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.8), gridspec_kw={'width_ratios': [1.15, 1.15, 1]})
    x = np.arange(4)
    offsets = [-.21, -.07, .07, .21]
    specs = [
        ('agreement', 100, 'A  Reference agreement', 'Reference agreement (%)', (0, 50)),
        ('macro_f1', 1, 'B  Macro-F1', 'Macro-F1 (fixed 28 labels)', (0, .43)),
        ('coverage', 100, 'C  Prediction coverage', 'Cells with a valid predicted label (%)', (0, 110)),
    ]
    handles = []
    for ax, (metric, scale, title, ylabel, limits) in zip(axes, specs):
        for i, model in enumerate(MODELS):
            group = [data[(data.method == method) & (data.model == model)].iloc[0] for method in METHODS]
            means = np.array([r[f'means_{metric}_mean'] for r in group]) * scale
            sd = np.array([r[f'means_{metric}_sd'] for r in group]) * scale
            artist = ax.errorbar(x + offsets[i], means, yerr=sd, fmt=MARKERS[i], color=COLORS[i], markersize=5, capsize=3, linewidth=1.2, label=NAMES[model])
            if metric == 'agreement':
                handles.append(artist)
        ax.set_xticks(x, [NAMES[m] for m in METHODS], rotation=22, ha='right')
        ax.set_title(title, loc='left', fontweight='bold', pad=12)
        ax.set_ylabel(ylabel)
        ax.set_ylim(*limits)
        ax.set_xlim(-.5, 3.5)
        ax.grid(axis='y', alpha=.18)
        ax.set_axisbelow(True)
    axes[2].set_yticks([0, 25, 50, 75, 100])
    fig.suptitle('Mean-expression profiles: annotation results', x=.035, y=.98, ha='left', fontsize=17, fontweight='bold')
    fig.text(.035, .91, 'Four LLMs, four frozen clustering partitions, original 28 reference labels', fontsize=11)
    fig.legend(handles, [NAMES[m] for m in MODELS], loc='lower center', bbox_to_anchor=(.5, .145), ncol=4, frameon=False, fontsize=10)
    fig.text(.035, .035, 'Points show mean ± sample SD across 3 runs, after equally averaging the same 2 B004 test regions. Missing outputs remain errors in agreement and F1.\nPreviously examined single donor. Repeated model calls are not biological replication.', fontsize=9, color='#4b5963')
    fig.tight_layout(rect=[.01, .23, .99, .88], w_pad=2)
    fig.savefig(OUT / 'means_only_results.png', dpi=220, facecolor='white')
    fig.savefig(OUT / 'means_only_results.pdf', facecolor='white')
    plt.close(fig)
    caption = ('Means-only annotation results for four LLMs across the frozen Leiden, FlowSOM, SpatialSort and PIXIE partitions. '
        '(A) Cell-level reference agreement, (B) fixed-28-label macro-F1 and (C) prediction coverage. '
        'Points show the mean and error bars the sample standard deviation across three separately requested runs. '
        'Each run averages the same two B004 test regions equally. All 45 marker mean profiles use the frozen training-region standardization and integer-thousandths encoding. '
        'Missing or invalid outputs remain in the full denominators for agreement and F1. '
        'The partitions/profiles were fitted using full-cohort unlabeled data and B004 was previously examined, so this is a conditional within-donor comparison. '
        'Repeated calls do not provide independent biological replication. The means-only presentation was chosen after the paired ablation and is not a prespecified model-selection result.')
    (OUT / 'figure_caption.txt').write_text(caption + '\n')
    outputs = ['means_only_results.csv', 'means_only_results.png', 'means_only_results.pdf', 'figure_caption.txt']
    audit = {'status': 'pass', 'source_summary_sha256': sha(source), 'source_repeat_metrics_sha256': sha(SOURCE / 'paired_repeat_metrics.csv'),
        'all_16_means_and_standard_deviations_recomputed': True, 'repeats': 3, 'selected_arm': 'all_means',
        'source_experiment_changed': False, 'new_model_calls': 0, 'additional_api_spend_usd': 0, 'network_access': False,
        'script_sha256': sha(__file__), 'artifacts': {name: sha(OUT / name) for name in outputs}}
    assert sha(source) == receipt['metric_sha256'][source.name]
    (OUT / 'presentation_receipt.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(table.to_string(index=False))


if __name__ == '__main__':
    main()
