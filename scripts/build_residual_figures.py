"""Render saved CUDA statistics only; no fitting, scoring or CPU resampling."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


ROOT=Path('results/residual_pilot/pilot01')


def save(fig,name):
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    for ext in ('pdf','svg','png'):
        path=out/(name+'.'+ext);fig.savefig(path,bbox_inches='tight',dpi=180)
        if ext=='svg':path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines())+'\n')
    plt.close(fig)


def main():
    primary=json.loads((ROOT/'primary_metrics.json').read_text())
    historical=json.loads((ROOT/'historical_panel_metrics.json').read_text())
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'svg.fonttype':'none',
                         'axes.spines.top':False,'axes.spines.right':False})
    blue,orange,green='#256a9b','#bc6524','#277865'
    fig,axes=plt.subplots(1,2,figsize=(11.8,4.8),gridspec_kw={'width_ratios':[1.3,1]})
    pairs=['B_minus_A_T','C_minus_A_T','D_minus_A_T','C_minus_B','D_minus_B','D_minus_C']
    labels=['Aggregate correction B − A_T','Local correction C − A_T','Graph correction D − A_T','Local C − aggregate B','Graph D − aggregate B','Graph D − local C']
    for i,key in enumerate(pairs):
        r=primary['paired'][key+'_all_time'];lo,hi=r['3']['difference_95']
        axes[0].hlines(i,lo,hi,color=blue,lw=2);axes[0].plot(r['difference'],i,'o',color=blue)
    axes[0].set(yticks=range(len(labels)),yticklabels=labels,title='Primary: 10,309 eligible origins',xlabel='Paired Brier difference')
    axes[0].invert_yaxis()
    for i,f in enumerate(('B','C','D')):
        r=historical['paired'][f+'_minus_A_H_all_time'];lo,hi=r['3']['difference_95']
        axes[1].hlines(i,lo,hi,color=orange,lw=2);axes[1].plot(r['difference'],i,'o',color=orange)
    axes[1].set(yticks=range(3),yticklabels=['Transferred B − A_H','Transferred C − A_H','Transferred D − A_H'],
                title='Historical panel: 127 eligible origins',xlabel='Paired Brier difference')
    axes[1].invert_yaxis()
    for ax in axes:
        ax.axvline(0,color='#666666',lw=1);ax.grid(axis='x',alpha=.2)
        ax.xaxis.set_major_locator(MaxNLocator(4))
    fig.suptitle('Exploratory residual pilot: matched comparisons, distinct baselines',fontsize=13)
    fig.text(.02,.005,'Intervals: 2,000 paired three-day-block resamples; mean seed loss, not an ensemble. Negative favors correction.\nA_T is the temporal GPU baseline. A_H is the saved original baseline; transfer changes the corrector’s baseline input.',fontsize=8)
    fig.tight_layout(rect=(0,.085,1,.94),w_pad=3);save(fig,'predictive_comparison')

    fig,axes=plt.subplots(1,2,figsize=(10.8,4.5))
    for ax,metrics,title in zip(axes,(primary,historical),('Complete validation versus A_T','Historical transfer versus A_H')):
        for i,f in enumerate(('B','C','D')):
            r=metrics['alignment'][f+'_seed_mean']
            ax.bar(i-.22,r['twice_alignment'],width=.22,color=blue,label='2 × error alignment' if i==0 else None)
            ax.bar(i,-r['squared_magnitude'],width=.22,color=orange,label='− correction magnitude²' if i==0 else None)
            ax.bar(i+.22,r['improvement'],width=.22,color=green,label='Net Brier improvement' if i==0 else None)
        ax.axhline(0,color='#666666',lw=1);ax.set(xticks=range(3),xticklabels=['B aggregate','C local','D graph'],title=title,ylabel='Contribution to mean Brier improvement')
        ax.grid(axis='y',alpha=.2)
    axes[0].legend(fontsize=8,loc='upper left')
    fig.suptitle('Correction alignment after clipping: established squared-loss identity',fontsize=12)
    fig.text(.02,.005,'GPU-computed seed means. Greater alignment can be offset by larger corrections. This decomposition is descriptive, not a generalization guarantee.',fontsize=8)
    fig.tight_layout(rect=(0,.035,1,.94));save(fig,'correction_alignment')

    # Lossless transcriptions of existing GPU outputs, including all seeds/subsets.
    with (ROOT/'metrics.csv').open('w',newline='') as out:
        w=csv.writer(out,lineterminator='\n');fields=['n','positives','brier','event_contribution','nonevent_contribution','mean_probability','threshold','tp','fp','recall','false_alarm_rate']
        w.writerow(['population','model','subset']+fields)
        for population,metrics in [('primary_A_T',primary),('historical_transfer_A_H',historical)]:
            for model,subsets in metrics['per_model'].items():
                for subset,r in subsets.items():w.writerow([population,model,subset]+[r[k] for k in fields])
    with (ROOT/'paired_metrics.csv').open('w',newline='') as out:
        w=csv.writer(out,lineterminator='\n');w.writerow(['population','comparison','a_brier','b_brier','difference','relative_reduction','block_days','difference_low','difference_high'])
        for population,metrics in [('primary_A_T',primary),('historical_transfer_A_H',historical)]:
            for pair,r in metrics['paired'].items():
                for block in ('1','3'):w.writerow([population,pair]+[r[k] for k in ('a_brier','b_brier','difference','relative_reduction')]+[block]+r[block]['difference_95'])


if __name__=='__main__':main()
