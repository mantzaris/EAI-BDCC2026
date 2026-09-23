"""Scientific figures from saved real validation results; no generated graphics."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def save(fig,name):
    directory=Path('results/figures');directory.mkdir(parents=True,exist_ok=True)
    for extension in ('pdf','svg','png'):
        output=directory/(name+'.'+extension)
        fig.savefig(output,bbox_inches='tight',dpi=170)
        if extension == 'svg':
            output.write_text('\n'.join(line.rstrip() for line in output.read_text().splitlines())+'\n')
    plt.close(fig)


def main():
    plt.rcParams.update({'font.size':11,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    metrics=pd.read_csv('results/tables/pilot_metrics.csv')
    reconstruction=pd.read_csv('results/tables/pilot_reconstruction.csv')
    baseline=json.loads(Path('results/tables/baseline_metrics.json').read_text())
    costs=pd.read_csv('results/tables/pilot_costs.csv')
    enc=pd.read_csv('results/tables/pilot_enclosures.csv')
    blue,orange,gray='#2371a5','#da7927','#777777'
    fig,axes=plt.subplots(1,2,figsize=(10.6,4.0))
    for N,color in [(256,blue),(1024,orange)]:
        g=metrics[(metrics.method == 'fine_mc')&(metrics.N == N)].sort_values('retention')
        axes[0].plot((g.retention*100).to_numpy(),g.brier.to_numpy(),'o-',label=f'Fine MC, N={N:,}',color=color)
        axes[0].fill_between((g.retention*100).to_numpy(),g.brier_low.to_numpy(),g.brier_high.to_numpy(),color=color,alpha=.13)
    axes[0].axhline(baseline['heterogeneity']['brier'],color=gray,linestyle='--',label='Aggregate + heterogeneity')
    axes[0].set(xlabel='Retained local sensors (%)',ylabel='Validation Brier score',xticks=[0,15,100])
    axes[0].legend(fontsize=9,loc='best')
    g=reconstruction[reconstruction.retention < 1]
    axes[1].plot((g.retention*100).to_numpy(),g.mean_rmse.to_numpy(),'o-',color=blue)
    axes[1].set(xlabel='Retained local sensors (%)',ylabel='Hidden-history RMSE (log odds)',xticks=[0,15,100],xlim=(-4,105))
    axes[1].text(98,.97,'100%: no hidden values',transform=axes[1].get_xaxis_transform(),ha='right',va='top',fontsize=9,color=gray)
    fig.suptitle('PEMS-BAY development pilot: information and reconstruction',fontsize=13)
    fig.text(.01,-.04,'128 time-selected validation origins; 127 scorable. Shading: paired-day bootstrap 95% intervals for each score. No test outcomes.',fontsize=9)
    fig.tight_layout(rect=(0,0,1,.92));save(fig,'information_prediction')

    fig,axes=plt.subplots(1,2,figsize=(10.6,4.0))
    g=enc[enc.N == 1024].sort_values('retention')
    width=.28; positions=np.arange(len(g))
    axes[0].bar(positions-width/2,g.actual_mean_error,width,color=blue,label='Actual fine/coarse error')
    axes[0].bar(positions+width/2,g.mean_radius,width,color=orange,label='Empirical radius')
    axes[0].set(xticks=positions,xticklabels=[f'{int(x*100)}%' for x in g.retention],xlabel='Retained local sensors',ylabel='Mean absolute state / radius (log odds)')
    axes[0].legend(fontsize=9)
    selected=costs[(costs.retention == .15)&(costs.N == 1024)]
    cases=[('cpu','fine_mc','CPU fine'),('cuda','fine_mc','Hybrid GPU fine'),('cuda','empirical_selective','Empirical selective'),('cuda','certified_fallback','Conservative fallback')]
    values=[]; tails=[]
    for device,method,label in cases:
        row=selected[(selected.device == device)&(selected.method == method)].iloc[0]
        values.append(row.mean_seconds*1000);tails.append(row.p95_seconds*1000)
    cpu_file=Path('results/cpu_reference.json')
    if cpu_file.exists():
        cpu=json.loads(cpu_file.read_text())['results']
        best=min(cpu,key=lambda name:cpu[name]['mean_seconds'])
        values[0]=cpu[best]['mean_seconds']*1000;tails[0]=cpu[best]['p95_seconds']*1000
        cases[0]=('cpu','fine_mc','CPU '+best.upper()+' fine')
    axes[1].barh(np.arange(4),values,color=[gray,blue,orange,'#a4a4a4'])
    axes[1].plot(tails,np.arange(4),'k|',markersize=11,label='p95')
    axes[1].set(yticks=np.arange(4),yticklabels=[c[2] for c in cases],xlabel='Forecast computation time (ms)')
    axes[1].invert_yaxis();axes[1].legend(fontsize=9)
    fig.suptitle('PEMS-BAY development pilot: enclosure and complete computation cost',fontsize=13)
    fig.text(.01,-.045,'N=1,024. Conditioning, reconstruction, forcing, reductions, compaction, and transfers included. Bounds are empirical; fallback refines all.',fontsize=9)
    fig.tight_layout(rect=(0,0,1,.92));save(fig,'enclosure_cost')
    Path('results/figures/ALT_TEXT.md').write_text('''# Pilot figure descriptions

information_prediction: Real PEMS-BAY validation Brier scores at 0%, 15%, and
100% retained sensors for 256 and 1,024 Monte Carlo scenarios, with whole-day
bootstrap intervals and an aggregate-plus-heterogeneity baseline. The companion
panel shows hidden-history reconstruction RMSE; at 100% no hidden values remain.

enclosure_cost: Real PEMS-BAY mean coarse/fine errors compared with empirical
radius widths, alongside complete forecast computation times at 15% retention
and 1,024 scenarios. The conservative method evaluates all scenarios because
floating-point certification is unavailable. Black marks show p95 latency.
These are validation development figures, not test-set findings.
''')


if __name__ == '__main__': main()
