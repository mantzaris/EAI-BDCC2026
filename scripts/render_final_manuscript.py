"""Render already-computed CUDA statistics. No fitting, metrics or resampling on CPU."""
import hashlib
import io
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

# Scientific result exports are frozen. This renderer only writes manuscript assets.
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
# Retain the historical detailed cost export; the paper uses saved means only.
assert (OUT/'costs.tex').read_text()=='\n'.join(lines)+'\n','Historical detailed cost export changed'
compact=[]
for left,right in zip(['A_G','R_union','A_mono','B','K',None],['C','D','M','S','E','F']):
    cells=[]
    for k in (left,right):
        cells.extend(['',''] if k is None else [texname(k),f"{cost['families'][k]['complete_seconds']:.4f}"])
    compact.append(' & '.join(cells)+r' \\')
(OUT/'cost_summary.tex').write_text('\n'.join(compact)+'\n')
lines=[]
for k in roster:
    r=raw['families'][k]
    lines.append(texname(k)+' & '+' & '.join(f'{x:.6f}' for x in r['onset']['seed_briers'])+(' & -- & --' if len(r['onset']['seed_briers'])==1 else '')+f" & {r['onset']['seed_std']:.6f}"+r' \\')
(OUT/'seeds.tex').write_text('\n'.join(lines)+'\n')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
COL=['#2166ac','#b2182b'];MARK=['o','s']
def export(fig,name):
    # Avoid timestamp-only changes to vector exports when the rendered plot is unchanged.
    preview=io.BytesIO();fig.savefig(preview,format='png',dpi=180,bbox_inches='tight')
    if all((FIG/(name+suffix)).exists() for suffix in ('.pdf','.svg','.png')) and (FIG/(name+'.png')).read_bytes()==preview.getvalue():
        plt.close(fig);return
    fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight');fig.savefig(FIG/(name+'.svg'),bbox_inches='tight');fig.savefig(FIG/(name+'.png'),dpi=180,bbox_inches='tight');plt.close(fig)
    svg=FIG/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')

fig,axes=plt.subplots(1,2,figsize=(7.1,3.45));contrasts=['C_minus_B','D_minus_C','E_minus_D','E_minus_B']
for ax,ep,title in zip(axes,['onset','all_time'],['Onset (primary)','All-time (secondary)']):
    for j,data in enumerate([val,raw]):
        for i,key in enumerate(contrasts):
            r=data['paired'][key+'_'+ep];lo,hi=r['3']['pointwise_95'];y=i+(-.11 if j==0 else .11)
            ax.plot([lo,hi],[y,y],color=COL[j],lw=1.2)
            if ep=='onset':
                lo,hi=r['3']['bonferroni_family4'];ax.plot([lo,hi],[y,y],color=COL[j],lw=3,alpha=.28)
            ax.plot(r['difference'],y,MARK[j],color=COL[j],ms=5,label=['Validation (exposed)','Test (frozen)'][j] if i==0 else None)
    ax.axvline(0,color='#555555',lw=.8);ax.set_yticks(range(4));ax.set_yticklabels(['C - B','D - C','E - D','E - B']);ax.invert_yaxis();ax.set_title(title);ax.set_xlabel('Brier difference (units of 0.0001)');ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x*10000:g}'))
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,fontsize=10,loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,0))
fig.tight_layout(rect=(0,.13,1,1))
fig.canvas.draw()
legend_bounds=fig.legends[0].get_window_extent(fig.canvas.get_renderer())
assert all(not legend_bounds.overlaps(ax.bbox) for ax in axes),'Effects legend covers data'
export(fig,'effects')

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

# Conceptual interface: one alternative correction per prediction, never an ensemble.
# Input paths checked against onset_graph/models.py and graphs.py. No raw data read.
fig,ax=plt.subplots(figsize=(6.8,4.25))
fig.subplots_adjust(left=.015,right=.985,bottom=.015,top=.985)
ax.set(xlim=(0,16),ylim=(0,9.4));ax.axis('off')
label_boxes=[]
def box(x,y,w,h,label,color='#f4f4f4',size=11):
    patch=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=.10',
                        fc=color,ec='#555555',lw=.8)
    ax.add_patch(patch)
    txt=ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=size,linespacing=1.25)
    label_boxes.append((patch,txt))

def arrow(start,end):
    ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='-|>',
                color='#555555',lw=.9,shrinkA=3,shrinkB=3,mutation_scale=10))

box(.25,7.9,4.75,1.2,'60-minute histories\n325 sensors + masks')
box(5.65,7.9,4.8,1.2,'16 regional summaries\n+ calendar features')
box(11.1,7.9,4.65,1.2,'Aggregate refit\n'+r'$R_{\rm union}$',color='#eef3f8')
arrow((5,8.5),(5.65,8.5));arrow((10.45,8.5),(11.1,8.5))

box(.25,5.45,4.75,1.8,'Local histories supply\nC / D / E / F and\nbuild summaries for S')
box(5.65,5.45,4.8,1.8,'Shared correction inputs\nAggregates + '+r'$p_{A_G}$'+'\n(anchor '+r'$A_G$'+' frozen)',color='#edf4ee')
box(11.1,5.85,4.65,1.15,'Separate prediction\n'+r'$p_{R_{\rm union}}$',color='#eef3f8')
arrow((2.625,7.9),(2.625,7.25));arrow((8.05,7.9),(8.05,7.25))
arrow((13.425,7.9),(13.425,7))

panel=FancyBboxPatch((.25,1.95),15.5,3.05,boxstyle='round,pad=0,rounding_size=.1',
                    fc='white',ec='#555555',lw=.8)
ax.add_patch(panel)
ax.text(8,4.57,'Alternative correction models: evaluate one arm at a time',
        ha='center',va='center',fontsize=11,fontweight='bold')
arrow((2.625,5.45),(2.625,5));arrow((8.05,5.45),(8.05,5))
box(.55,2.65,3.4,1.35,'B / K\nAggregate\ncorrection',size=11)
box(4.35,2.65,3.4,1.35,'M\nRegional\ngraph',size=11)
box(8.15,2.65,3.4,1.35,'S\nCoarse/deviation\nsummaries',size=10.5)
box(11.95,2.65,3.4,1.35,'C / D / E / F\nLocal histories\n+ graph (D/E/F)',size=10.5)
ax.text(8,2.24,'All arms receive shared inputs; graph arms use their fixed operators.',
        ha='center',va='center',fontsize=10)
box(2.4,.15,11.2,1.4,'Each arm separately: '+r'$p=\operatorname{clip}(p_{A_G}+\alpha r,0,1)$'+'\n30-minute sustained-event probability',color='#edf4ee',size=11)
arrow((8,1.95),(8,1.55))

# Check actual rendered extents, including padding, before every export.
fig.canvas.draw();renderer=fig.canvas.get_renderer()
for patch,txt in label_boxes:
    outer=patch.get_window_extent(renderer);inner=txt.get_window_extent(renderer)
    assert outer.x0+4 <= inner.x0 and inner.x1 <= outer.x1-4,txt.get_text()
    assert outer.y0+4 <= inner.y0 and inner.y1 <= outer.y1-4,txt.get_text()
    assert ax.bbox.contains(outer.x0,outer.y0) and ax.bbox.contains(outer.x1,outer.y1)
export(fig,'overview')

(OUT/'claim_traceability.json').write_text(json.dumps(dict(numeric_macros=claims,artifact_sources=TRACE,
    generated_tables=dict(scores='raw/calibrated families plus validation families',costs='saved measured repeats and selected fit records; historical export retained unchanged',cost_summary='saved complete_seconds means, first seed, three repeats, no recomputation',seeds='all saved raw onset seed scores'),
    scientific_computation='All inputs are saved GPU statistics. CPU only formats tables, text and geometric plotting coordinates.'),indent=2)+'\n')
print('Rendered four figures, tables and traceable numerical macros')
