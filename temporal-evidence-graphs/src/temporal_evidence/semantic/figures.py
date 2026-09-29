"""Vector publication figures from actual exports and measured semantic scores."""
from collections import Counter,defaultdict
from pathlib import Path
import os
os.environ.setdefault("MPLCONFIGDIR",".local/matplotlib")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from matplotlib.lines import Line2D
from temporal_evidence.io import read_json,write_json,digest_file

DATA=Path("artifacts/analysis/semantic_analysis_v1")
OUT=Path("artifacts/figures/semantic_analysis_v1")
NAMES={"synthetic":"Synthetic","wesad":"WESAD","ppg_dalia":"PPG-DaLiA"}
COLORS={"synthetic":"#0072B2","wesad":"#009E73","ppg_dalia":"#CC79A7"}
plt.rcParams.update({"font.size":10,"axes.titlesize":11,"axes.labelsize":10,"legend.fontsize":8.5,
    "pdf.fonttype":42,"svg.fonttype":"none","svg.hashsalt":"semantic_analysis_v1_20260929",
    "font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False})

def save(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    for ext in ("pdf","svg","png"):fig.savefig(OUT/f"{name}.{ext}",bbox_inches="tight",dpi=210)
    svg=OUT/f"{name}.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    plt.close(fig)

def box(ax,xy,text,width=1.65,height=.68,color="#e4eff5",fontsize=9.5,edge="#3d5967"):
    x,y=xy;p=FancyBboxPatch((x-width/2,y-height/2),width,height,boxstyle="round,pad=.035",facecolor=color,edgecolor=edge,linewidth=.9,zorder=3)
    ax.add_patch(p);ax.text(x,y,text,ha="center",va="center",fontsize=fontsize,zorder=4);return p

def arrow(ax,a,b,patches,positions,color="#426578",style="-",rad=0,label=None,fontsize=8):
    pa,pb=positions[a],positions[b]
    ax.add_patch(FancyArrowPatch(pa,pb,patchA=patches[a],patchB=patches[b],arrowstyle="-|>",mutation_scale=11,
        shrinkA=2,shrinkB=2,color=color,linestyle=style,linewidth=1.05,connectionstyle=f"arc3,rad={rad}",zorder=2))
    if label:ax.text((pa[0]+pb[0])/2,(pa[1]+pb[1])/2+.06,label,ha="center",va="bottom",fontsize=fontsize,color=color,zorder=5,
        bbox={"facecolor":"white","edgecolor":"none","pad":.25})

def ontology():
    selected=read_json(DATA/"representative_cores/wesad_median.json");example=selected["before"]
    target=max((n for n in example["nodes"] if n["type"]=="feature"),key=lambda n:n["interval"][0])
    claim=next(n for n in example["nodes"] if n["type"]=="claim" and n["claim"]["claim_type"]=="numeric_observation")
    obs=example["sidecars"]["observation_provenance"][target["id"]][0]["record"]
    revised=max((n for n in selected["after"]["nodes"] if n["type"]=="feature"),key=lambda n:n["interval"][0])
    fig,axes=plt.subplots(1,2,figsize=(6.8,4.1),gridspec_kw={"width_ratios":[1.1,1]})
    ax=axes[0];ax.set(xlim=(-.95,4.3),ylim=(-.65,4.05));ax.axis("off");ax.set_title("a  Fixed types and typed relations",loc="left")
    pos={"O":(0,2.25),"F":(2,2.25),"C":(2,.75),"X":(0,.75),"A":(3.25,-.15),"I":(1,3.55)}
    patches={key:box(ax,xy,label,width=w,height=h,color=col,fontsize=10) for key,xy,label,w,h,col in [
        ("I",pos["I"],"Subject / Sensor",2.55,.5,"#eeeeee"),("O",pos["O"],"Observation\nwindow",1.65,.65,"#e7edf2"),
        ("F",pos["F"],"Feature\nversion",1.95,.65,"#dcecf6"),("C",pos["C"],"Claim\nversion",1.85,.65,"#e3f0e8"),
        ("X",pos["X"],"Explanation\nVersion",1.65,.7,"#eeeeee"),("A",pos["A"],"Support\nassessment",1.85,.65,"#f5e4cf") ]}
    arrow(ax,"F","O",patches,pos)
    ax.text(1,2.78,"DERIVED_FROM",ha="center",fontsize=9)
    arrow(ax,"C","F",patches,pos,rad=.18)
    ax.text(.92,1.48,"depends on",ha="center",fontsize=9,color="#426578")
    arrow(ax,"F","C",patches,pos,color="#009E73",rad=.2)
    ax.text(3.15,1.5,"supports*",fontsize=9,color="#007e5c",ha="center")
    arrow(ax,"X","C",patches,pos)
    ax.text(1,1.16,"contains",ha="center",fontsize=9)
    arrow(ax,"C","A",patches,pos,color="#af711f")
    arrow(ax,"O","I",patches,pos,color="#8a8a8a",style=":")
    ax.text(.5,-.30,"Review events and\nversion history",ha="center",fontsize=9.5)
    ax.text(1,3.05,"* accepted at insertion",ha="center",fontsize=9,color="#007e5c")
    ax=axes[1];ax.set(xlim=(-.45,4.2),ylim=(-.65,4.05));ax.axis("off");ax.set_title("b  Saved WESAD S11 construction",loc="left")
    samples=obs["metadata"]["sample_stop"]-obs["metadata"]["sample_start"]
    items=[("O",(1.8,3.45),f"EDA window: {obs['event_start_seconds']:g}–{obs['event_end_seconds']:g} s\n{samples} samples at {obs['metadata']['rate_hz']:g} Hz", "#e7edf2"),
        ("F",(1.8,2.2),f"Median: {target['value']:.5f} µS\nv1, known at {target['ingested']:g} s","#dcecf6"),
        ("C",(1.8,.9),f"C1 proposes {claim['value']:.6g} uS\nChecker accepts\nscope, value and unit","#e3f0e8")]
    ps={};po={}
    for key,xy,label,col in items:po[key]=xy;ps[key]=box(ax,xy,label,width=3.95,height=.8 if key!="C" else .92,color=col,fontsize=10.3)
    arrow(ax,"F","O",ps,po)
    ax.text(2.12,2.82,"extraction",ha="left",fontsize=9,color="#426578")
    arrow(ax,"C","F",ps,po)
    ax.text(2.12,1.63,"citation",ha="left",fontsize=9,color="#426578")
    ax.text(1.8,-.12,f"At {int(selected['after']['knowledge_time'])} s: v2 = {revised['value']:.5f} uS.\nRe-evaluate the old statement;\nretain its original citation.",ha="center",va="center",fontsize=10)
    fig.subplots_adjust(wspace=.23);save(fig,"ontology_construction")
    write_json(OUT/"ontology_example.json",{"scope":example["scope"],"knowledge_time":example["knowledge_time"],"observation_id":obs["record_id"],"feature_id":target["id"],"claim_id":claim["id"],"source_sha256":obs["metadata"]["file_sha256"]})

def actual_graphs():
    from temporal_evidence.semantic.network_examples import run
    run()


def fidelity():
    temporal=read_json(DATA/"temporal_summary_all_variants.json")
    fig,axes=plt.subplots(1,2,figsize=(6.4,2.75),sharey=True)
    phases=["before","arrival","maintained"]
    for ax,metric,title in zip(axes,("precision","recall"),("Grounding precision","Required-fact recall")):
        for i,source in enumerate(NAMES):
            group=[next(r for r in temporal if r["dataset"]==source and r["method"]=="M1" and r["position"]==phase)[metric] for phase in phases]
            means=np.array([r["mean"] for r in group])*100;cis=np.array([r["ci95"] for r in group])*100
            ax.errorbar(np.arange(3)+(i-1)*.07,means,yerr=[means-cis[:,0],cis[:,1]-means],fmt="os^"[i]+"-",color=COLORS[source],capsize=3,markersize=5,linewidth=1.3,label=NAMES[source])
        ax.set(xticks=range(3),xticklabels=["Before","Arrival","After"],ylim=(0,106));ax.tick_params(labelsize=12)
        ax.set_title(title,fontsize=13);ax.grid(axis="y",alpha=.18)
    axes[0].set_ylabel("Percent",fontsize=12)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,frameon=False,fontsize=12,loc="lower center",ncol=3)
    fig.subplots_adjust(wspace=.20,bottom=.26,top=.84);save(fig,"semantic_fidelity")


def structural():
    path=DATA/"structural_summary.json"
    if not path.exists():return False
    data=read_json(path);rows=read_json(DATA/"structural_replay_metrics.json")
    fig,axs=plt.subplots(1,2,figsize=(6.4,3.3));axes=np.array([axs])
    for col,origin in enumerate(("fixture","generated")):
        ax=axes[0,col];groups=defaultdict(list)
        for r in rows:
            if r["origin"]==origin and r["method"]=="B2" and r["xi"] is not None:
                groups[(r["xi"],r["regime"],r["realized_depth"])].append(r)
        ax.plot([0,1],[0,1],color="#777777",linestyle=":",label="predicted: gap = ξ")
        for (xi,regime,depth),rs in sorted(groups.items(),key=lambda x:str(x[0])):
            ys=[r["missed_changes"]/r["required_changes"] for r in rs]
            ax.scatter([xi],[np.mean(ys)],s=22+9*np.sqrt(len(rs)),marker="o" if regime=="single" else "s",
                facecolors=plt.cm.viridis((depth or 1)/4) if regime=="single" else "none",edgecolors=plt.cm.viridis((depth or 1)/4),linewidths=1.3,alpha=.8)
        ax.set(xlim=(-.045,1.02),ylim=(-.045,1.02),xlabel="Transitive exposure ξ",ylabel="Full − direct fraction")
        ax.set_title("Exact programs" if col==0 else "Generated programs",loc="left",fontsize=13)
        ax.tick_params(labelsize=12);ax.xaxis.label.set_size(12);ax.yaxis.label.set_size(12)
    axes[0,0].legend(frameon=False,fontsize=11.5,loc="upper left")
    depth_handles=[Line2D([0],[0],marker="o",linestyle="none",color=plt.cm.viridis(d/4),label=f"depth {d}") for d in range(1,5)]
    route_handles=[Line2D([0],[0],marker="o",linestyle="none",color="black",label="one route"),
        Line2D([0],[0],marker="s",linestyle="none",color="black",markerfacecolor="none",label="two routes")]
    fig.legend(handles=depth_handles+route_handles,ncol=3,frameon=False,fontsize=11.5,loc="lower center",bbox_to_anchor=(.5,-.015))
    fig.subplots_adjust(wspace=.45,bottom=.35,top=.87);save(fig,"structural_theory_test");return True

def manifest():
    names=['ontology_construction','real_revision_network','structural_witness_network',
           'ontology_instance_network','semantic_fidelity','structural_theory_test']
    complete=all((OUT/(name+'.'+ext)).exists() for name in names for ext in ('pdf','svg','png'))
    write_json(OUT/"manifest.json",{"complete_main_set":complete,"script_sha256":digest_file(__file__),
        "inputs":{str(p):digest_file(p) for p in sorted(DATA.glob("*.json"))} |
                 {'artifacts/analysis/classic_network_v1/manifest.json':digest_file('artifacts/analysis/classic_network_v1/manifest.json')},
        "figures":names,
        "layout":"Graphviz dot and seeded spring union layouts; stored/derived mappings in per-network manifests; dashboard uses identical typed views"})

def run():
    from temporal_evidence.semantic.classic_example import run as classic
    ontology();actual_graphs();classic();fidelity();structural();manifest()

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--manifest-only',action='store_true')
    args=parser.parse_args()
    manifest() if args.manifest_only else run()
