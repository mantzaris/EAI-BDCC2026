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
    fig,axes=plt.subplots(2,2,figsize=(7.0,5.5));layouts=[]
    positions={"O1":(.5,2.5),"O2":(.5,.75),"F1":(2.8,2.5),"F2":(2.8,.75),"C2":(5.1,2.5),"C1":(5.1,.75)}
    for row,source in enumerate(("wesad","ppg_dalia")):
        selected=read_json(DATA/f"representative_cores/{source}_median.json")
        for col,stage in enumerate(("before","after")):
            ax=axes[row,col];ax.set(xlim=(-.6,6.2),ylim=(.05,3.28));ax.axis("off")
            g=selected[stage];short={};ps={};features=sorted([n for n in g["nodes"] if n["type"]=="feature"],key=lambda n:n["interval"][0])
            for i,n in enumerate(features,1):
                label=f"F{i}";short[n["id"]]=label
                text=f"{label} EDA v{n['version']}\n{n['value']:.4f} µS\n{n['interval'][0]:g}–{n['interval'][1]:g}s"
                ps[label]=box(ax,positions[label],text,width=1.95,height=.9,color="#f8decf" if col and i==2 else "#dcecf6",fontsize=10.5)
                prov=g["sidecars"]["observation_provenance"][n["id"]][0];o=prov["record"];olabel=f"O{i}";short[o["record_id"]]=olabel
                ps[olabel]=box(ax,positions[olabel],f"{olabel} EDA\n{o['event_start_seconds']:g}–{o['event_end_seconds']:g}s\n{o['metadata']['rate_hz']:g} Hz",width=1.95,height=.9,color="#e7edf2",fontsize=10.5)
                arrow(ax,label,olabel,ps,positions,color="#77848d")
            for n in [n for n in g["nodes"] if n["type"]=="claim"]:
                is_comparison=n["claim"]["claim_type"] in {"comparison","trend"};label="C2" if is_comparison else "C1";short[n["id"]]=label
                labeltext="ΔEDA" if is_comparison else "median"
                ps[label]=box(ax,positions[label],f"{label} {labeltext}\n{n['value']:.4f} µS\n{'displayed' if n['displayed_member'] else 'withdrawn'}",width=1.95,height=.9,
                    color="#e3f0e8" if n["displayed_member"] else "#f8decf",fontsize=10.5)
            for e in g["edges"]:
                a,b=short[e["source"]],short[e["target"]]
                parent=e["semantics"]=="declared_prerequisite";derived=not e["directly_stored"]
                arrow(ax,a,b,ps,positions,color="#D55E00" if derived else "#666666" if parent else "#0072B2",
                    style=":" if derived else "--" if parent else "-",rad=-.2 if parent else 0)
            time=int(g["knowledge_time"])
            ax.set_title(f"{NAMES[source]} · {stage} · t = {time} s",fontsize=10,loc="left",pad=8)
            layouts.append({"source":source,"stage":stage,"case_id":g["case_id"],"scope":g["scope"],"knowledge_time":g["knowledge_time"],
                "short_label_to_source_ids":{label:[rid for rid,l in short.items() if l==label] for label in positions},"positions":positions,
                "edges":g["edges"],"selection":selected["selection_rule"],"seed":selected["layout_seed"]})
    handles=[Line2D([0],[0],color="#0072B2",label="stored citation"),Line2D([0],[0],color="#666666",linestyle="--",label="declared parent"),
        Line2D([0],[0],color="#D55E00",linestyle=":",label="derived current-version path"),Line2D([0],[0],color="#77848d",label="stored extraction provenance")]
    fig.legend(handles=handles,loc="lower center",ncol=2,frameon=False,bbox_to_anchor=(.5,-.01),fontsize=8.5)
    fig.subplots_adjust(wspace=.10,hspace=.28,bottom=.14);save(fig,"actual_revision_graphs");write_json(OUT/"actual_revision_graphs_layout.json",layouts)

def topology():
    full=read_json(DATA/"storage_by_scope.json");cores=read_json(DATA/"degree_depth_witness_distributions.json")
    parent=read_json(DATA/"parent_structure_summary.json");active=read_json(DATA/"active_graph_by_snapshot.json")
    fig,axes=plt.subplots(2,3,figsize=(6.4,4.8));sources=list(NAMES)
    categories=[("FOR_SUBJECT","membership","#bdbdbd"),("DERIVED_FROM","extraction","#7cabbf"),("DEPENDS_ON","dependencies","#0072B2"),
        ("SUPPORTS","accepted mirror","#009E73"),("ASSESS_OTHER","other / assessment","#e2be82")]
    ax=axes[0,0];bottom=np.zeros(3)
    totals=[sum(r["edges"] for r in full if r["dataset"]==s) for s in sources]
    for key,label,color in categories:
        values=[]
        for s,total in zip(sources,totals):
            group=[r for r in full if r["dataset"]==s]
            count=sum(r["edges_"+key] for r in group) if key!="ASSESS_OTHER" else total-sum(sum(r["edges_"+k] for r in group) for k,_,_ in categories[:-1])
            values.append(count/total)
        ax.bar(range(3),values,bottom=bottom,color=color,label=label,width=.65);bottom+=values
    ax.set(xticks=range(3),xticklabels=["Syn.","WES","PPG"],ylim=(0,1),ylabel="Stored edge fraction");ax.set_title("a  Stored relations",loc="left",fontsize=10)
    handles,labels=ax.get_legend_handles_labels()
    fig.legend(handles,labels,frameon=False,fontsize=9.5,loc="lower center",bbox_to_anchor=(.5,-.01),ncol=3)
    ax=axes[0,1];matrix=np.zeros((3,3));labels=["C→C","C→F","F→O"]
    for i,s in enumerate(sources):
        g=[r for r in cores if r["dataset"]==s];parent_count=sum(sum(r["claim_parent_degrees"]) for r in g);citations=sum(sum(r["direct_evidence_counts"]) for r in g)
        matrix[i]=[parent_count,citations,0]
        if matrix[i].sum():matrix[i]/=matrix[i].sum()
    ax.imshow(matrix,cmap="Blues",vmin=0,vmax=1,aspect="auto")
    for i in range(3):
        for j in range(3):ax.text(j,i,f"{100*matrix[i,j]:.1f}",ha="center",va="center",fontsize=9.5,color="white" if matrix[i,j]>.6 else "black")
    ax.set(xticks=range(3),xticklabels=labels,yticks=range(3),yticklabels=["Syn.","WESAD","PPG"]);ax.tick_params(axis="x",labelsize=9.5);ax.set_title("b  Core types (%)",loc="left",fontsize=10)
    ax=axes[0,2]
    for i,s in enumerate(sources):
        for j,stage in enumerate(("proposal","displayed")):
            r=next(r for r in parent if r["dataset"]==s and r["method"]=="M1" and r["stage"]==stage)
            val=r["parentless"];mean=100*val["mean"];ci=100*np.array(val["ci95"])
            ax.errorbar(j+(i-1)*.07,mean,yerr=[[mean-ci[0]],[ci[1]-mean]],fmt="os^"[i],color=COLORS[s],capsize=2,markersize=4,label=NAMES[s] if j==0 else None)
    ax.set(xticks=[0,1],xticklabels=["Raw","Display"],ylim=(0,105),ylabel="Parentless (%)");ax.set_title("c  No-parent mass",loc="left",fontsize=10);ax.legend(frameon=False,fontsize=9.5,loc="lower right")
    ax=axes[1,0]
    for s in sources:
        values=[v for r in active if r["dataset"]==s for v in r["in_degrees"]]
        xs=np.arange(0,max(values)+1);ys=[np.mean(np.asarray(values)>=x) for x in xs]
        ax.step(xs,ys,where="post",color=COLORS[s],label=NAMES[s])
    ax.set(xlabel="Dependency in-degree",ylabel="Empirical CCDF",ylim=(-.02,1.02));ax.set_title("d  Active degree",loc="left",fontsize=10)
    for ax,key,title,xlabels in [(axes[1,1],"claim_depths","e  Parent depth",["0","1","≥2"]),
                                (axes[1,2],"admissible_witness_counts","f  Evidence witnesses",["0","1","≥2"])]:
        for i,s in enumerate(sources):
            values=[v for r in cores if r["dataset"]==s for v in r[key]];counts=[sum(v==0 for v in values),sum(v==1 for v in values),sum(v>=2 for v in values)]
            ax.bar(np.arange(3)+(i-1)*.23,np.array(counts)/len(values),width=.22,color=COLORS[s],label=NAMES[s])
        ax.set(xticks=range(3),xticklabels=xlabels,ylim=(0,1.05),ylabel="Claim fraction");ax.set_title(title,loc="left",fontsize=10)
    fig.subplots_adjust(wspace=.68,hspace=.6,bottom=.20);save(fig,"semantic_topology")

def fidelity():
    fresh=read_json(DATA/"semantic_summary.json");temporal=read_json(DATA/"temporal_summary_all_variants.json")
    fig,axes=plt.subplots(2,3,figsize=(6.4,4.55),sharey=True)
    for col,source in enumerate(NAMES):
        for row,phases,data,key in ((0,["proposal","final_proposal","displayed"],fresh,"stage"),(1,["before","arrival","maintained"],temporal,"position")):
            ax=axes[row,col]
            for metric,color,marker in (("precision","#0072B2","o"),("recall","#009E73","s")):
                group=[next(r for r in data if r["dataset"]==source and r["method"]=="M1" and r[key]==p)[metric] for p in phases]
                means=np.array([r["mean"] for r in group])*100;cis=np.array([r["ci95"] for r in group])*100
                ax.errorbar(np.arange(3)+(-.035 if metric=="precision" else .035),means,yerr=[means-cis[:,0],cis[:,1]-means],fmt=marker+"-",color=color,capsize=2,markersize=4,linewidth=1.3,label="Grounding P" if metric=="precision" else "Required R")
            ax.set(xticks=range(3),xticklabels=["Raw","Final","Shown"] if row==0 else ["Before","Arrival","After"],ylim=(0,104));ax.tick_params(axis="x",labelsize=9.5)
            if row==0:ax.set_title(NAMES[source],fontsize=11)
            if col==0:ax.set_ylabel("Fresh answer (%)" if row==0 else "Prior answer (%)")
            ax.grid(axis="y",alpha=.18)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,frameon=False,fontsize=10,loc="lower center",ncol=2)
    fig.subplots_adjust(wspace=.35,hspace=.55,bottom=.2);save(fig,"semantic_fidelity")

def structural():
    path=DATA/"structural_summary.json"
    if not path.exists():return False
    data=read_json(path);rows=read_json(DATA/"structural_replay_metrics.json")
    fig,axes=plt.subplots(2,2,figsize=(6.4,5.3))
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
        ax.set(xlim=(-.045,1.02),ylim=(-.045,1.02),xlabel="Realized transitive exposure ξ",ylabel="Full − direct correction fraction")
        ax.set_title("a  Exact programs" if col==0 else "b  GPU-generated programs",loc="left",fontsize=11)
    axes[0,0].legend(frameon=False,fontsize=9.5,loc="upper left")
    depth_handles=[Line2D([0],[0],marker="o",linestyle="none",color=plt.cm.viridis(d/4),label=f"depth {d}") for d in range(1,5)]
    route_handles=[Line2D([0],[0],marker="o",linestyle="none",color="black",label="one route"),
        Line2D([0],[0],marker="s",linestyle="none",color="black",markerfacecolor="none",label="two routes")]
    fig.legend(handles=depth_handles+route_handles,ncol=3,frameon=False,fontsize=9.5,loc="lower center",bbox_to_anchor=(.5,-.015))
    ax=axes[1,0];matrix=np.zeros((4,5))
    for r in data["generated_cases"]:
        depth=r["realized_depth"];j=0 if depth is None else min(depth,4);matrix[r["intended_depth"]-1,j]+=1
    ax.imshow(matrix,cmap="Blues",aspect="auto")
    for i in range(4):
        for j in range(5):ax.text(j,i,str(int(matrix[i,j])),ha="center",va="center",fontsize=10,color="white" if matrix[i,j]>matrix.max()*.6 else "black")
    ax.set(xticks=range(5),xticklabels=["None","1","2","3","≥4"],yticks=range(4),yticklabels=[1,2,3,4],xlabel="Realized evidence-to-answer depth",ylabel="Requested depth")
    ax.set_title("c  Realized depth (all 240)",loc="left",fontsize=11)
    ax=axes[1,1]
    for i,origin in enumerate(("fixture","generated")):
        for j,regime in enumerate(("single","alternative")):
            group=[r for r in rows if r["origin"]==origin and r["method"]=="M1" and r["condition"]=="route_loss" and r["regime"]==regime and r["root_count"]]
            value=100*np.mean([r["root_preserved"] for r in group]) if group else 0
            ax.bar(j+(i-.5)*.28,value,width=.27,color="#0072B2" if i==0 else "#CC79A7",label="Exact" if i==0 and j==0 else "Generated" if i==1 and j==0 else None)
    for j,regime in enumerate(("single","alternative")):
        denominators=[sum(r["origin"]==origin and r["method"]=="M1" and r["condition"]=="route_loss" and r["regime"]==regime and bool(r["root_count"]) for r in rows) for origin in ("fixture","generated")]
        ax.text(j,6 if j==0 else 105,f"n={denominators[0]}/{denominators[1]}",ha="center",fontsize=9.5)
    ax.set(xticks=[0,1],xticklabels=["One route","Two routes"],ylim=(0,116),ylabel="Answer retained (%)")
    ax.set_title("d  Primary-route loss",loc="left",fontsize=11);ax.legend(frameon=False,fontsize=9.5,loc="upper left")
    fig.subplots_adjust(wspace=.45,hspace=.6,bottom=.20);save(fig,"structural_theory_test");return True

def run():
    ontology();actual_graphs();topology();fidelity();complete=structural()
    write_json(OUT/"manifest.json",{"complete_main_set":complete,"script_sha256":digest_file(__file__),
        "inputs":{str(p):digest_file(p) for p in sorted(DATA.glob("*.json"))},
        "figures":["ontology_construction","actual_revision_graphs","semantic_topology","semantic_fidelity"]+(["structural_theory_test"] if complete else []),
        "layout":"fixed typed layout; actual graph source IDs and derived path witnesses exported separately"})

if __name__=="__main__":run()
