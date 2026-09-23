"""Rebuild two Stage 2 scientific figures using committed numerical outputs only."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def save(fig, name):
    directory = Path('results/stage2/figures'); directory.mkdir(parents=True, exist_ok=True)
    for extension in ('pdf', 'svg', 'png'):
        path = directory/(name+'.'+extension)
        fig.savefig(path, bbox_inches='tight', dpi=180)
        if extension == 'svg': path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines())+'\n')
    plt.close(fig)


def main():
    root = Path('results/stage2')
    plt.rcParams.update({'font.size':10, 'pdf.fonttype':42, 'svg.fonttype':'none',
                         'axes.spines.top':False, 'axes.spines.right':False})
    metrics = pd.read_csv(root/'predictive_metrics.csv')
    pairs = json.loads((root/'matched_pairs.json').read_text())
    sims = json.loads((root/'simulator_pairs.json').read_text())
    names = ['A', 'B', 'C', 'simulator_original', 'simulator_location_repair']
    labels = ['A: aggregate + heterogeneity', 'B: A + 15% locals', 'C: A + all locals',
              'Original simulator (full)', 'Repaired simulator (full)']
    blue, orange, gray = '#2371a5', '#da7927', '#777777'
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={'width_ratios':[1.3, 1.]})
    for kind, color, offset, label in [('probability',blue,-.13,'Raw'),('calibrated_probability',orange,.13,'Training-calibrated')]:
        take = metrics[(metrics.probability_kind == kind)&(metrics.subset == 'all_time')].set_index('model').loc[names]
        x = take.brier.to_numpy()
        axes[0].errorbar(x, np.arange(5)+offset, xerr=np.stack((x-take.brier_low.to_numpy(), take.brier_high.to_numpy()-x)),
                         fmt='o', color=color, markersize=4, capsize=3, label=label)
    axes[0].set(yticks=np.arange(5), yticklabels=labels, xlabel='Brier score (lower is better)')
    axes[0].set_ylim(5.1, -.5); axes[0].legend(fontsize=9, loc='lower right')
    comparison = [pairs['B_minus_A_probability_all_time_block1'], pairs['C_minus_A_probability_all_time_block1'],
                  sims['location_repair_probability_versus_A_block1']]
    for i, result in enumerate(comparison):
        delta = result['difference_b_minus_a']; lo, hi = result['difference_95']
        axes[1].errorbar(delta, i, xerr=[[delta-lo],[hi-delta]], fmt='o', color=blue, capsize=4)
    baseline = metrics[(metrics.model == 'A')&(metrics.probability_kind == 'probability')&(metrics.subset == 'all_time')].brier.iloc[0]
    axes[1].axvline(0, color=gray, linewidth=1)
    axes[1].axvline(-.05*baseline, color=orange, linestyle='--', label='5% improvement over A')
    axes[1].set(yticks=np.arange(3), yticklabels=['B minus A', 'C minus A', 'Repaired simulator minus A'],
                xlabel='Paired Brier difference (negative favors added model)')
    axes[1].set_ylim(2.8, -.3); axes[1].legend(fontsize=8, loc='lower right')
    fig.suptitle('Stage 2: matched local information and one simulator repair', fontsize=13)
    fig.text(.01,-.015,'Exploratory PEMS-BAY validation: 127 eligible origins, 20 positives on 17 days. Intervals: 2,000 paired day bootstraps. Simulator N=256.',fontsize=8)
    fig.tight_layout(rect=(0,.015,1,.92), w_pad=2.8); save(fig,'paired_predictions')

    old = pd.read_csv(root/'enclosure_widths.csv').groupby('retention').mean()
    new = pd.read_csv(root/'tightening_widths.csv').groupby('retention').mean()
    cost = json.loads((root/'enclosure_summary.json').read_text())
    tight = json.loads((root/'tightening_summary.json').read_text())
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.3))
    x = np.arange(3)
    axes[0].bar(x-.17, old.mean_radius.to_numpy(), .34, color=blue, label='Original radius')
    axes[0].bar(x+.17, new.mean_radius.to_numpy(), .34, color=orange, label='Tightened radius')
    axes[0].plot(x, old.mean_center_threshold_distance.to_numpy(), 'k--o', markersize=4, label='Center distance to threshold')
    axes[0].plot(x, old.mean_fine_error.to_numpy(), color=gray, marker='s', linestyle=':', label='Actual fine/coarse error')
    axes[0].set(xticks=x, xticklabels=['0%', '15%', '100%'], xlabel='Retained local sensors', ylabel='Mean log-odds magnitude')
    axes[0].legend(fontsize=8)
    for j, record in enumerate((cost['repeat_timing'], tight['repeat_timings'])):
        ratios = np.array([1-row['relative_saving'] for row in record])
        axes[1].bar(j, ratios.mean(), .48, color=[blue,orange][j], alpha=.6)
        axes[1].scatter(j+np.linspace(-.1,.1,len(ratios)), ratios, color='black', s=20, zorder=3)
    axes[1].axhline(1, color=gray, label='Fine computation')
    axes[1].axhline(.9, color=orange, linestyle='--', label='Required 10% saving')
    axes[1].set(xticks=[0,1], xticklabels=['Original selective','Tightened selective'],
                ylabel='Complete time / paired fine time', ylim=(0,1.48))
    axes[1].legend(fontsize=8, loc='lower right')
    fig.suptitle('Stage 2: tighter enclosures still do not resolve events or save time', fontsize=13)
    fig.text(.01,-.015,'16 prespecified origins; 256 coupled scenarios. Both bounds unresolved on 100% of scenarios. Dots: five paired CPU repetitions at 15%.',fontsize=8)
    fig.tight_layout(rect=(0,.015,1,.92), w_pad=2.5); save(fig,'enclosure_width_cost')
    (root/'figures/ALT_TEXT.md').write_text('''# Stage 2 figure descriptions

paired_predictions: Exploratory real validation Brier scores for matched aggregate,
15% local and full local classifiers, plus original and repaired full-retention
simulators. Raw and training-calibrated scores are separate. Paired differences
favor the aggregate baseline in point estimates, with broad day-level intervals.

enclosure_width_cost: Mean empirical radius drops substantially under a justified
tightening, but remains larger than typical center-to-threshold distances. Every
scenario remains ambiguous. Original and tightened selective CPU paths both take
more time than their paired fine references in five repetitions. No test outcomes,
synthetic observations, or claimed floating-point certificates appear in the plots.
''')


if __name__ == '__main__': main()
