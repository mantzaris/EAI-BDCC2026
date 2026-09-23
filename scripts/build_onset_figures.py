"""Render saved CUDA outputs and transcribe tables; no host research numerics."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

ROOT=Path('results/onset_graph/study01')


def read(path):return json.loads(path.read_text())


def save(fig,name):
    folder=ROOT/'main/figures';folder.mkdir(exist_ok=True)
    for ext in ('pdf','svg','png'):
        path=folder/(name+'.'+ext);fig.savefig(path,bbox_inches='tight',dpi=180)
        if ext=='svg':path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines())+'\n')
    plt.close(fig)


def main():
    raw=read(ROOT/'main/validation_raw_metrics.json');cal=read(ROOT/'main/validation_calibrated_metrics.json')
    topology=read(ROOT/'main/topology_metrics.json');metadata=read(ROOT/'main/models_with_nulls.json')
    G,X=metadata['strong_aggregate'],metadata['expanded'];pairs=[('C',G),('D','C'),(X,'D'),(X,G)]
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    colors=['#156b8a','#cd6936','#38916b','#9055a2','#4d6475','#bb8d24']
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,endpoint in zip(axes,['onset','all_time']):
        for i,(a,b) in enumerate(pairs):
            r=raw['paired'][a+'_minus_'+b+'_'+endpoint];interval=r['3']
            if 'bonferroni_family4' in interval:ax.hlines(i,*interval['bonferroni_family4'],color='#bdc4ca',lw=7,label='Family-adjusted interval' if i==0 else None)
            ax.hlines(i,*interval['pointwise_95'],color=colors[0],lw=2,label='Pointwise 95%' if i==0 else None);ax.plot(r['difference'],i,'o',color=colors[0])
        ax.axvline(0,color='#555555',lw=1);ax.set(yticks=range(4),yticklabels=[a+' − '+b for a,b in pairs],
            xlabel='Brier difference; negative favors first model',title='Onset: exploratory primary' if endpoint=='onset' else 'All-time: required secondary')
        ax.invert_yaxis();ax.ticklabel_format(axis='x',style='sci',scilimits=(-3,3));ax.grid(axis='x',alpha=.2)
    axes[0].legend(fontsize=8,loc='best');fig.suptitle('Stronger controls do not sustain the earlier local/graph advantage')
    fig.text(.02,.005,'2,000 paired three-day resamples; mean seed losses, not an ensemble. All 36 validation days were previously exposed.',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.94));save(fig,'endpoint_effects')

    families=['A_G','R_union','B','C','D','E'];fig,axes=plt.subplots(1,3,figsize=(14,4.3))
    for i,name in enumerate(families):
        f=raw['families'][name]['onset'];q=cal['families'][name]['onset']
        axes[0].plot([f['brier'],q['brier']],[i,i],color=colors[i]);axes[0].plot(f['brier'],i,'o',color=colors[i]);axes[0].plot(q['brier'],i,'s',color=colors[i])
        keys=[name] if name in metadata['controls'] else [r['key'] for r in metadata['families'][name]['replicates']]
        for key in keys:
            m=raw['models'][key]['onset'];axes[1].plot(m['fpr'],m['recall'],'o',color=colors[i],alpha=.75)
        key=keys[0];bins=cal['models'][key]['onset']['reliability']
        axes[2].plot([b['predicted'] for b in bins],[b['observed'] for b in bins],'-o',ms=3,color=colors[i],label=name)
    axes[0].set(yticks=range(len(families)),yticklabels=families,title='Onset score: circle raw, square calibrated',xlabel='Brier');axes[0].invert_yaxis()
    axes[1].axvline(.05,color='#555555',ls='--');axes[1].set(xlabel='Achieved false-alarm rate',ylabel='Recall',title='Frozen alarms: every seed')
    axes[2].plot([0,1],[0,1],ls='--',color='#999999');axes[2].set(xlabel='Mean predicted probability',ylabel='Observed frequency',title='Calibrated reliability: first fixed seed');axes[2].legend(fontsize=8)
    fig.text(.02,.005,'Calibration fit on Apr 2–9 training data (30 onset positives in five groups); alarms exclude cutoff ties. Reliability bins have unequal support.',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1));save(fig,'alarm_calibration')

    fig,axes=plt.subplots(1,2,figsize=(12,5));mechanisms=[('D','C'),('D','D_rewire_20261004'),('D','D_rewire_20261005'),('E','E_self'),('E','E_rewire_20261004'),('E','E_rewire_20261005'),('E','E_internal')]
    for ax,endpoint in zip(axes,['onset','all_time']):
        for i,(a,b) in enumerate(mechanisms):
            r=topology['paired'][a+'_minus_'+b+'_'+endpoint];ax.hlines(i,*r['3']['pointwise_95'],color=colors[0],lw=2);ax.plot(r['difference'],i,'o',color=colors[0])
        ax.axvline(0,color='#555555',lw=1);ax.set(yticks=range(len(mechanisms)),yticklabels=[a+' − '+b.replace('_202610',' seed').replace('_rewire',' null') for a,b in mechanisms],
            title=endpoint.replace('_',' ').title(),xlabel='Paired Brier difference');ax.invert_yaxis();ax.ticklabel_format(axis='x',style='sci',scilimits=(-3,3))
    fig.suptitle('Matched trained topology controls: neither graph consistently beats both nulls')
    fig.text(.02,.005,'Pointwise three-day 95% intervals; diagnostic contrasts outside the primary multiplicity family. E was selected using training data only.',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.94));save(fig,'topology_controls')

    blocks=read(ROOT/'main/validation_blocks.json');fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for i,(a,b) in enumerate(pairs):
        for j,block in enumerate(blocks.values()):
            r=block['raw']['paired'][a+'_minus_'+b+'_onset'];pos=j+(i-1.5)*.14
            axes[0].vlines(pos,*r['3']['pointwise_95'],color=colors[i],lw=1.5);axes[0].plot(pos,r['difference'],'o',color=colors[i],label=a+' − '+b if j==0 else None)
    axes[0].axhline(0,color='#555555',lw=1);axes[0].set(xticks=range(3),xticklabels=['Apr20–May1','May2–13','May14–25'],ylabel='Onset Brier difference',title='Fixed validation calendar blocks');axes[0].legend(fontsize=8)
    for i,name in enumerate(['A_G','R_union','B','C','D','E']):
        values=[read(ROOT/f/'gate_raw_metrics.json')['families'][name]['onset']['brier'] for f in ['rolling1','rolling2','main']]
        axes[1].plot(range(3),values,'-o',label=name,color=colors[i])
    axes[1].set(xticks=range(3),xticklabels=['Mar13–16','Mar25–Apr1','Apr10–19'],ylabel='Onset Brier',title='Chronological training-period evaluations');axes[1].legend(fontsize=8,ncol=2)
    fig.text(.02,.005,'Weak support: 7, 9 and 9 onset groups in rolling/gate periods. Pipelines overlap development data; these are not independent studies.',fontsize=8)
    fig.tight_layout(rect=(0,.055,1,1));save(fig,'temporal_robustness')

    illustration=read(ROOT/'main/illustration.json');fig,axes=plt.subplots(2,1,figsize=(9,5.5),sharex=True)
    axes[0].plot(range(12),illustration['regional_mean_scaled'],label='Region 0 mean',lw=2)
    streams=illustration['regional_summary_hops']
    for i,h in enumerate([1,2,4]):axes[0].plot(range(12),[row[3+i] for row in streams],label='Deviation summary, hop '+str(h))
    axes[0].set(ylabel='Scaled transformed state',title='Fixed window: 2017-04-20 08:00, first region');axes[0].legend(fontsize=8,ncol=2)
    im=axes[1].imshow(illustration['local_severity_categories'],aspect='auto',vmin=-1,vmax=3,cmap=ListedColormap(['#999999','#2274a5','#82b6d9','#ebb35e','#bc463f']))
    axes[1].set(yticks=range(4),yticklabels=['Column '+str(i) for i in illustration['sensor_column_indices']],xticks=[0,3,6,9,11],xticklabels=['−55','−40','−25','−10','0'],xlabel='Minutes before forecast origin')
    fig.colorbar(im,ax=axes[1],ticks=[-1,0,1,2,3],label='Local severity category; −1 missing')
    fig.text(.02,.005,'Outcome-blind timestamp/identity rule. Categorical local values are noninvertible; this window is a mechanism illustration, not population evidence.',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1));save(fig,'illustrative_window')

    # Exact transcriptions of existing GPU output values; no CPU scoring.
    populations=[('outer',raw,cal)]+[(f,read(ROOT/f/'gate_raw_metrics.json'),read(ROOT/f/'gate_calibrated_metrics.json')) for f in ['rolling1','rolling2','main']]
    with (ROOT/'metrics.csv').open('w',newline='') as stream:
        w=csv.writer(stream,lineterminator="\n");fields=['n','positives','brier','event_contribution','nonevent_contribution','mean_probability','recall','fpr','tp','fp','cutoff','zero_count','cutoff_ties']
        w.writerow(['population','calibration','model','endpoint']+fields)
        for population,r,c in populations:
            for label,d in [('raw',r),('calibrated',c)]:
                for model,subsets in d['models'].items():
                    for endpoint,m in subsets.items():w.writerow([population,label,model,endpoint]+[m[k] for k in fields])
    with (ROOT/'paired_metrics.csv').open('w',newline='') as stream:
        w=csv.writer(stream,lineterminator="\n");w.writerow(['population','calibration','comparison','difference','relative_reduction','block_days','low95','high95','family4_low','family4_high','primary'])
        for population,r,c in populations+[('topology',topology,{'paired':{}})]:
            for label,d in [('raw',r),('calibrated',c)]:
                for name,m in d['paired'].items():
                    for block in ('3','1'):w.writerow([population,label,name,m['difference'],m['relative_reduction'],block]+m[block]['pointwise_95']+m[block].get('bonferroni_family4',['',''])+[m['primary']])
    print('Rendered five figures and transcribed GPU metric tables; no CPU experiment.')


if __name__=='__main__':main()
