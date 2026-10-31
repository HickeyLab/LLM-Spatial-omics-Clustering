"""Render the offline decomposition. No inference or network operations."""
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
SOURCE = ROOT / 'data/frozen/manuscript_replay/paired/failure_decomposition'
OUT = ROOT / 'outputs/manuscript_replay/paired_decomposition'
MODELS = ['gpt', 'claude', 'gemini', 'deepseek']
METHODS = ['leiden', 'flowsom', 'spatialsort', 'pixie_tiff']
NAMES = {'gpt': 'GPT-5.6-Sol', 'claude': 'Claude Opus 5', 'gemini': 'Gemini 3.1 Pro Preview', 'deepseek': 'DeepSeek V4 Pro',
         'leiden': 'Leiden', 'flowsom': 'FlowSOM', 'spatialsort': 'SpatialSort', 'pixie_tiff': 'PIXIE'}


def main():
    global SOURCE,OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=SOURCE)
    parser.add_argument('--output-dir',type=Path,default=OUT)
    args=parser.parse_args();SOURCE=args.input_dir;OUT=args.output_dir
    if OUT.resolve()==SOURCE.resolve():raise ValueError('Output must differ from frozen input directory')
    OUT.mkdir(parents=True,exist_ok=True)
    receipt = json.loads((SOURCE / 'audit_receipt.json').read_text())
    for name, digest in receipt['output_sha256'].items():
        path=SOURCE/name
        if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    data = pd.read_csv(SOURCE / 'comparison_decomposition.csv')
    ordered = pd.DataFrame([data[(data.model == model) & (data.method == method)].iloc[0] for model in MODELS for method in METHODS])
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(12, 9))
    y = np.arange(16)
    ax.barh(y - .14, ordered.label_contribution_pp, height=.24, color='#2864a5', label='Label changes where both arms delivered')
    ax.barh(y + .14, ordered.delivery_contribution_pp, height=.24, color='#b55224', label='Net contribution of one-arm delivery')
    ax.scatter(ordered.total_change_pp, y, color='#263442', marker='D', s=24, label='Total observed change', zorder=3)
    for i, value in enumerate(ordered.total_change_pp):
        ax.annotate(f'{value:+.2f}', (value, i), xytext=(-7 if value < -15 else 7, 1), textcoords='offset points', ha='right' if value < -15 else 'left', va='center', fontsize=8, bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': .95, 'pad': .5})
    ax.axvline(0, color='#687783', lw=1)
    ax.set_yticks(y, [f'{NAMES[m]} / {NAMES[c]}' for m in MODELS for c in METHODS])
    ax.invert_yaxis()
    ax.set_xlabel('Contribution to fractions-minus-means reference agreement (percentage points)')
    ax.set_xlim(-34, 4)
    ax.grid(axis='x', alpha=.18)
    ax.set_axisbelow(True)
    for divider in [3.5, 7.5, 11.5]:
        ax.axhline(divider, color='#dce1e5', lw=.8)
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.01), frameon=False, fontsize=9)
    fig.suptitle('Label changes account for most of the observed decline', x=.035, ha='left', fontsize=16, fontweight='bold')
    fig.text(.035, .93, 'Average decline: 9.72 pp overall, comprising 7.67 pp from valid-pair label changes and 2.05 pp from delivery differences.', fontsize=10)
    fig.text(.035, .025, 'Each comparison averages the same two B004 test regions and three repeats. Both components use the full original denominators.\nDelivery differences count correct labels gained or lost when only one arm delivered. Missing predictions have unknown counterfactual labels.', fontsize=9, color='#4b5963')
    fig.tight_layout(rect=[0, .07, 1, .90])
    fig.savefig(OUT / 'decomposition.png', dpi=200, facecolor='white')
    plt.close(fig)
    summary = pd.read_csv(SOURCE / 'model_decomposition.csv')
    failures = pd.read_csv(SOURCE / 'failure_summary.csv')
    noise = pd.read_csv(SOURCE / 'repeat_disagreement_summary.csv')
    label_share = abs(receipt['overall_equal_comparison_mean']['label_contribution_pp'] / receipt['overall_equal_comparison_mean']['total_change_pp'])
    lines = [
        'Offline decomposition of the paired representation experiment', '',
        'Across 16 equally weighted model-partition comparisons, mean reference agreement changed by -9.72 percentage points. The exact accounting is -7.67 points from changes on cells where both arms returned valid labels and -2.05 points from net differences in delivery. The label term accounts for approximately ' + f'{label_share:.1%}' + ' of that net average decline. This is an accounting share, not an estimate of what repairing missing responses would recover.', '',
        'The original metric is preserved: equal means over two test regions, followed by three runs. It is not a pooled-cell decomposition. The label and delivery terms reconcile for every region, run and comparison.', '',
        'Per model, averaged equally over the four clustering partitions:',
    ]
    for row in summary.itertuples():
        lines.append(f'{NAMES[row.model]}: total {row.total_change_pp:+.2f} pp, valid-pair labels {row.label_contribution_pp:+.2f} pp, delivery {row.delivery_contribution_pp:+.2f} pp.')
    lines += ['', 'Claude/Leiden: -29.20 pp = -10.58 pp from valid-pair labels and -18.62 pp from delivery. Claude/FlowSOM: -22.63 pp is almost entirely valid-pair label regression, with approximately zero net delivery contribution.', '',
        'GPT delivered every requested annotation in both arms. Its average -4.05 pp change is entirely due to different valid labels. Gemini and DeepSeek have positive net delivery contributions: better delivery partly offsets worse reference agreement on valid pairs.', '',
        'Raw failure diagnosis: Claude means-plus-fractions has 12 malformed-JSON batches, losing all 75 scheduled cluster annotations in each. Its other missing outputs are invalid label codes, missing IDs and a duplicate ID. No response was flagged with a non-stop finish reason: all 384 have finish_reason=stop. Therefore the saved metadata do not support a claim of reported output-token-limit truncation.', '',
        'Mean prompt-token counts grew by approximately 66% to 86% depending on model. A longer and numerically different input is an observed change, but attention overload, semantic confusion and over-weighting of fractions remain hypotheses, not established mechanisms.', '',
        'On the same cells with all six labels available, cross-representation disagreement exceeds within-representation disagreement in all 16 comparisons. This supports a representation-associated shift beyond ordinary repeat disagreement in this sample, but three repeats do not establish a general causal mechanism.', '',
        'Fraction values are processed X>0 numerical summaries. They are not validated biological marker-positive fractions. The saved outputs do not establish whether models misread their scale, over-weighted them, or applied different biological heuristics.', '',
        'Conditional both-valid agreement is reported on the same paired cells, but that is a selected delivered subset. Delivery accounting does not reveal the predictions that would have appeared in failed responses. Agreement is with the existing reference, not independently validated biological correctness. The study uses one previously examined donor.', '',
        'No new inference, retries, fitting or network access was used. Original experiment files remain unchanged.',
    ]
    assert np.all(noise.between_arm_disagreement_all_nine_pairs > noise[['means_within_arm_disagreement', 'fractions_within_arm_disagreement']].max(axis=1))
    (OUT / 'interpretation.txt').write_text('\n'.join(lines) + '\n')
    (OUT / 'presentation_receipt.json').write_text(json.dumps({'source_audit_sha256': hashlib.sha256((SOURCE / 'audit_receipt.json').read_bytes()).hexdigest(),
        'artifacts': {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in ['decomposition.png', 'interpretation.txt']},
        'new_model_calls': 0, 'new_fits': 0, 'network_access': False}, indent=2) + '\n')


if __name__ == '__main__':
    main()
