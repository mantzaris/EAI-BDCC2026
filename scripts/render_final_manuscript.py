"""Render already-computed CUDA statistics. No fitting, metrics or resampling on CPU."""
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'manuscript/generated';FIG=ROOT/'manuscript/figures'
OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
TRACE=[]

def read(path):
    p=ROOT/path;TRACE.append(dict(path=path,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    return json.loads(p.read_text())

raw=read('results/final_test/evaluate/raw_metrics.json');cal=read('results/final_test/evaluate/calibrated_metrics.json')
val=read('results/onset_graph/study01/main/validation_raw_metrics.json');vcal=read('results/onset_graph/study01/main/validation_calibrated_metrics.json')
null=read('results/onset_graph/study01/main/topology_metrics.json')
cost=read('results/final_test/evaluate/historical_cost_summary.json');usage=read('manifests/final_test/compute_summary.json')
roster=list(raw['families']);principal=['A_G','R_union','A_mono','B','K','C','D','M','S','E','F']
names={'A_G':r'$A_G$','R_union':r'$R_{\rm union}$','A_mono':r'$A_{\rm mono}$'}
texname=lambda k:names.get(k,k.replace('_rewire_202610',' rew. ').replace('_',r'\_'))
macro=[];claims=[]

def add(name,value,fmt,source,pointer):
    shown=format(value,fmt).replace('%',r'\%');macro.append('\\newcommand{\\'+name+'}{'+shown+'}')
    claims.append(dict(macro=name,value=value,rendered=shown,artifact=source,pointer=pointer))

for split,variants,srcs in [('Test',[raw,cal],['results/final_test/evaluate/raw_metrics.json','results/final_test/evaluate/calibrated_metrics.json']),
                          ('Val',[val,vcal],['results/onset_graph/study01/main/validation_raw_metrics.json','results/onset_graph/study01/main/validation_calibrated_metrics.json'])]:
    for model in principal:
        mn={'A_G':'AG','R_union':'RUnion','A_mono':'AMono'}.get(model,model)
        for ci,data in enumerate(variants):
            for ep,en in [('onset','On'),('all_time','All')]:
                add(split+('Cal' if ci else '')+en+mn,data['families'][model][ep]['brier'],'.5f',srcs[ci],'/families/'+model+'/'+ep+'/brier')
        for key,kn in [('mean_recall','Recall'),('mean_fpr','Fpr')]:
            add(split+kn+mn,variants[0]['families'][model]['onset'][key],'.2%',srcs[0],'/families/'+model+'/onset/'+key)
for name,valx,fmt,pointer in [('TestOnsetN',raw['support']['onset']['n'],',d','/support/onset/n'),('TestPos',raw['support']['onset']['positives'],',d','/support/onset/positives'),('TestEligible',raw['support']['eligible'],',d','/support/eligible'),('TestPrevalence',raw['diagnostics']['B']['onset']['prevalence'],'.2%','/diagnostics/B/onset/prevalence')]:
    add(name,valx,fmt,'results/final_test/evaluate/raw_metrics.json',pointer)
add('NewGPU',usage['new_gpu_job_seconds'],'.2f','manifests/final_test/compute_summary.json','/new_gpu_job_seconds')
add('CumulativeGPU',usage['cumulative_gpu_job_seconds'],'.2f','manifests/final_test/compute_summary.json','/cumulative_gpu_job_seconds')
(OUT/'numbers.tex').write_text('\n'.join(macro)+'\n')

# Every family and seed is retained in machine-readable tables; no averages computed here.
rows=[]
for mode,data in [('raw',raw),('calibrated',cal)]:
    for k,f in data['families'].items():
        for endpoint,m in f.items():
            rows.append(dict(model=k,calibration=mode,endpoint=endpoint,**{key:v for key,v in m.items() if key!='seed_briers'},seed_briers=json.dumps(m['seed_briers'])))
with (ROOT/'results/final_test/metrics.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
pairs=[]
for mode,data in [('raw',raw),('calibrated',cal)]:
    for kind in ['paired','secondary_paired']:
        for key,r in data[kind].items():pairs.append(dict(calibration=mode,kind=kind,key=key,**r))
(ROOT/'results/final_test/paired_metrics.json').write_text(json.dumps(pairs,indent=2)+'\n')
lines=[]
for k in principal:
    r=raw['families'][k];cc=cal['families'][k]
    lines.append(texname(k)+' & '+' & '.join([f"{val['families'][k]['onset']['brier']:.5f}",f"{r['onset']['brier']:.5f}",f"{r['all_time']['brier']:.5f}",f"{cc['onset']['brier']:.5f}",f"{r['onset']['mean_recall']:.1%}".replace('%',r'\%'),f"{r['onset']['mean_fpr']:.2%}".replace('%',r'\%')])+r' \\')
(OUT/'scores.tex').write_text('\n'.join(lines)+'\n')
lines=[]
for k in principal:
    if k in ['A_G','R_union','A_mono']:
        fit=read('results/onset_graph/study01/main/anchor_fits.json');fittime=f"{fit['anchor' if k!='R_union' else 'refresh']['wall_seconds']:.3f}" if k!='A_mono' else 'n/a'
    else:
        records=read('results/onset_graph/study01/main/'+k+'_attempts.json')
        selected=[r for r in records if 'replicate' in r]
        fittime='/'.join(f"{r['fit_wall_seconds']:.3f}" for r in selected)
    r=cost['families'][k]
    lines.append(texname(k)+f" & {fittime} & {r['complete_seconds']:.4f} & "+'/'.join(f'{x:.4f}' for x in r['repeats'])+r' \\')
(OUT/'costs.tex').write_text('\n'.join(lines)+'\n')
lines=[]
for k in roster:
    r=raw['families'][k]
    lines.append(texname(k)+' & '+' & '.join(f'{x:.6f}' for x in r['onset']['seed_briers'])+(' & -- & --' if len(r['onset']['seed_briers'])==1 else '')+f" & {r['onset']['seed_std']:.6f}"+r' \\')
(OUT/'seeds.tex').write_text('\n'.join(lines)+'\n')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
COL=['#2166ac','#b2182b'];MARK=['o','s']
def export(fig,name):
    fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight');fig.savefig(FIG/(name+'.svg'),bbox_inches='tight');fig.savefig(FIG/(name+'.png'),dpi=180,bbox_inches='tight');plt.close(fig)
    svg=FIG/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')

fig,axes=plt.subplots(1,2,figsize=(7.1,3.15));contrasts=['C_minus_B','D_minus_C','E_minus_D','E_minus_B']
for ax,ep,title in zip(axes,['onset','all_time'],['Onset (primary)','All-time (secondary)']):
    for j,data in enumerate([val,raw]):
        for i,key in enumerate(contrasts):
            r=data['paired'][key+'_'+ep];lo,hi=r['3']['pointwise_95'];y=i+(-.11 if j==0 else .11)
            ax.plot([lo,hi],[y,y],color=COL[j],lw=1.2)
            if ep=='onset':
                lo,hi=r['3']['bonferroni_family4'];ax.plot([lo,hi],[y,y],color=COL[j],lw=3,alpha=.28)
            ax.plot(r['difference'],y,MARK[j],color=COL[j],ms=5,label=['Validation (exposed)','Test (frozen)'][j] if i==0 else None)
    ax.axvline(0,color='#555555',lw=.8);ax.set_yticks(range(4));ax.set_yticklabels(['C - B','D - C','E - D','E - B']);ax.invert_yaxis();ax.set_title(title);ax.set_xlabel('Brier difference (units of 0.0001)');ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x*10000:g}'))
axes[0].legend(fontsize=8,loc='lower left');fig.tight_layout();export(fig,'effects')

fig,axes=plt.subplots(1,2,figsize=(7.1,3.15));models=['R_union','B','C','D','E','F']
for i,k in enumerate(models):
    r=raw['families'][k]['onset'];diag=raw['diagnostics'][k]['onset'];x,y=r['mean_fpr'],r['mean_recall']
    lo,hi=diag['fpr_95'];axes[0].plot([lo,hi],[y,y],color='#999999',lw=.7)
    lo,hi=diag['recall_95'];axes[0].plot([x,x],[lo,hi],color='#999999',lw=.7)
    axes[0].plot(x,y,'o',ms=5);axes[0].annotate(k.replace('_union',''),(x,y),xytext={'R_union':(-5,7),'B':(-20,2),'C':(-4,17),'D':(3,-12),'E':(7,3),'F':(-5,-22)}[k],textcoords='offset points',fontsize=9)
axes[0].axvline(.05,color='#555555',ls='--',lw=.8);axes[0].set(xlabel='Frozen-cutoff false-alarm rate',ylabel='Recall',title='Test onset alarms',ylim=(.82,1.005))
for j,data in enumerate([raw,cal]):
    for k,color in [('R_union','#1b7837'),('B','#2166ac'),('E','#b2182b')]:
        bins=data['diagnostics'][k]['onset']['reliability'];axes[1].plot([b['predicted'] for b in bins],[b['observed'] for b in bins],['-','--'][j],color=color,marker=['o','s'][j],ms=3,label=k.replace('_union','')+[' raw',' calibrated'][j])
axes[1].plot([0,1],[0,1],color='#777777',lw=.6);axes[1].set(xlabel='Mean predicted risk in fixed bin',ylabel='Observed fraction',title='Test reliability');axes[1].legend(fontsize=7,ncol=2)
fig.tight_layout();export(fig,'alarms')

fig,ax=plt.subplots(figsize=(6.8,3.5));keys=[('D','C'),('D','D_rewire_20261004'),('D','D_rewire_20261005'),('E','E_self'),('E','E_internal'),('E','E_rewire_20261004'),('E','E_rewire_20261005')]
for j,data in enumerate([null['paired'],raw['secondary_paired']]):
    for i,(a,b) in enumerate(keys):
        key=a+'_minus_'+b+'_onset'
        r=(raw['paired'] if j==1 and b=='C' else data)[key];lo,hi=r['3']['pointwise_95'];y=i+(-.12 if j==0 else .12)
        ax.plot([lo,hi],[y,y],color=COL[j]);ax.plot(r['difference'],y,MARK[j],color=COL[j],ms=5,label=['Validation (exposed)','Test (frozen)'][j] if i==0 else None)
ax.set_yticks(range(len(keys)));ax.set_yticklabels([a+' - '+b.replace('202610','').replace('_',' ') for a,b in keys]);ax.invert_yaxis();ax.axvline(0,color='#555555',lw=.8);ax.set_xlabel('Onset Brier difference (units of 0.0001)');ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x*10000:g}'));ax.legend(fontsize=8);fig.tight_layout();export(fig,'topology')

# Conceptual flowchart uses no raw measurements or generated imagery.
fig,ax=plt.subplots(figsize=(7.0,3.0));ax.set(xlim=(0,10),ylim=(0,5));ax.axis('off')
boxes=[(.1,3.5,2.5,1,'60-minute sensor histories\n325 sensors + masks'),(3.2,3.5,2.8,1,'16 fixed regional summaries\nmeans, counts, heterogeneity'),(6.7,3.5,3.1,1,'Frozen aggregate anchor\nA_G or refit R_union'),(.1,1.5,2.5,1,'C: local temporal\nD/F: sensor messages'),(3.2,1.5,2.8,1,'M: regional messages\nS: coarse + deviations'),(6.7,1.5,3.1,1,'E: within/cross messages\nB/K: aggregate correction'),(3.2,0,3.7,.85,'Frozen additive correction + clipping\n30-minute sustained-event risk')]
for x,y,w,h,label in boxes:
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.06',fc='#f4f4f4',ec='#555555',lw=.8));ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=9)
for xy,xytext in [((3.2,4),(2.65,4)),((6.7,4),(6.05,4)),((1.35,2.55),(1.35,3.45)),((4.6,2.55),(4.6,3.45)),((8.25,2.55),(8.25,3.45)),((3.2,.6),(1.35,1.45)),((5.05,.9),(4.6,1.45)),((6.95,.6),(8.25,1.45))]:ax.annotate('',xy=xy,xytext=xytext,arrowprops=dict(arrowstyle='->',color='#555555',lw=.8))
export(fig,'overview')

(OUT/'claim_traceability.json').write_text(json.dumps(dict(numeric_macros=claims,artifact_sources=TRACE,
    generated_tables=dict(scores='raw/calibrated families plus validation families',costs='saved measured repeats and selected fit records',seeds='all saved raw onset seed scores'),
    scientific_computation='All inputs are saved GPU statistics. CPU only formats tables, text and geometric plotting coordinates.'),indent=2)+'\n')
print('Rendered four figures, tables and traceable numerical macros')
