from collections import defaultdict
from pathlib import Path
import csv
import math
import numpy as np
from temporal_evidence.io import read_json,write_json,digest_file

METHODS=("B0","B1","B2","M1","B3")
SOURCES=("synthetic","wesad","ppg_dalia")
RATIOS={"claim_error":("claim_errors","claim_count"),"reference_validity":("valid_reference_count","reference_count"),
        "fact_recall":("supplied_slots","answerable_slots"),"useful_coverage":("useful_complete","useful_eligible"),
        "correction_completeness":("corrected","correction_required"),
        "correction_by_deadline":("corrected_by_5s","correction_required"),
        "residual_incorrect":("residual_incorrect","correction_required"),
        "collateral_revision":("collateral_withdrawn","unaffected")}
MEANS=("case_error","abstained","partial","failed","initial_parse_failure","initial_truncation","repair_calls")


def aggregate(rows):
    report={"cases":len(rows)}
    for name,(numerator,denominator) in RATIOS.items():
        n=sum(row[numerator] for row in rows);d=sum(row[denominator] for row in rows)
        report[name]={"value":n/d if d else None,"numerator":n,"denominator":d}
    for key in MEANS:
        report[key]={"value":sum(row[key] for row in rows)/len(rows) if rows else None,
                     "numerator":sum(row[key] for row in rows),"denominator":len(rows)}
    for key in ("generation_seconds","database_update_seconds","retrieval_seconds","end_to_end_seconds"):
        values=[row[key] for row in rows if row.get(key) is not None]
        report[key]={"p50":float(np.quantile(values,.5)) if values else None,
                     "p95":float(np.quantile(values,.95)) if values else None}
    report["tokens"]={key:sum(row[key] for row in rows) for key in ("input_tokens","output_tokens")}
    report["abstention_by_answerability"]={str(answerable):aggregate_abstentions([row for row in rows if row["answerable_slots"]==answerable])
                                          for answerable in (0,1,2)}
    return report


def aggregate_abstentions(rows):
    return {"cases":len(rows),"abstained":sum(row["abstained"] for row in rows),"partial":sum(row["partial"] for row in rows)}


def subject_values(rows,metric):
    subjects=defaultdict(list)
    for row in rows:
        subjects[row["subject"]].append(row)
    result={}
    for subject,items in subjects.items():
        if metric in RATIOS:
            numerator,denominator=RATIOS[metric]
            total=sum(row[denominator] for row in items)
            result[subject]=sum(row[numerator] for row in items)/total if total else None
        else:
            # Balanced episode/checkpoint counts make this equal to first averaging
            # within each base episode, then within participant.
            result[subject]=float(np.mean([row[metric] for row in items]))
    return result


def paired_interval(rows,left,right,metric,resamples=2000):
    a=subject_values([r for r in rows if r["method"]==left],metric)
    b=subject_values([r for r in rows if r["method"]==right],metric)
    subjects=sorted(a.keys()&b.keys())
    eligible=[subject for subject in subjects if a[subject] is not None and b[subject] is not None]
    differences=np.array([a[subject]-b[subject] for subject in eligible])
    if not len(differences):
        return {"left":left,"right":right,"metric":metric,"subjects":0,"difference":None,"ci95":None}
    rng=np.random.Generator(np.random.PCG64(20260928))
    samples=differences[rng.integers(0,len(differences),size=(resamples,len(differences)))].mean(axis=1)
    return {"left":left,"right":right,"metric":metric,"subjects":len(eligible),"excluded_subjects":len(subjects)-len(eligible),
            "difference":float(differences.mean()),"ci95":np.quantile(samples,[.025,.975]).tolist(),
            "resamples":resamples,"estimand":"equal-subject mean of within-subject paired differences"}


def export_csv(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
        writer.writeheader();writer.writerows(rows)


def analyze(run_id="minimum_v1"):
    path=f"artifacts/evaluation/{run_id}/metrics.json"
    rows=read_json(path)
    if run_id=="minimum_v1":
        manifest=read_json("artifacts/manifests/minimum_run.json")
        assert {row["case_id"] for row in rows}=={case["case_id"] for case in manifest["cases"]}
    summary=[]
    contrasts=[]
    for source in SOURCES:
        source_rows=[row for row in rows if row["dataset"]==source]
        for method in METHODS:
            items=[row for row in source_rows if row["method"]==method]
            summary.append({"dataset":source,"method":method,**aggregate(items)})
        for left,right,metric in [("M1","B2","correction_completeness"),("M1","B1","case_error"),("M1","B1","fact_recall")]:
            contrasts.append({"dataset":source,"principal":True,**paired_interval(source_rows,left,right,metric)})
        for metric in ("case_error","fact_recall","correction_completeness"):
            contrasts.append({"dataset":source,"principal":False,**paired_interval(source_rows,"M1","B3",metric)})
    strata=[]
    for source in SOURCES:
        for method in METHODS:
            for variant in ("clean","channel_fault","delayed","correction"):
                for checkpoint in (0,1,2):
                    selected=[r for r in rows if (r["dataset"],r["method"],r["variant"],r["checkpoint"])==(source,method,variant,checkpoint)]
                    strata.append({"dataset":source,"method":method,"variant":variant,"checkpoint":checkpoint,**aggregate(selected)})
    report={"run_id":run_id,"input_sha256":digest_file(path),"cases":len(rows),"summary":summary,"strata":strata,
            "contrasts":contrasts,"intervals":"Pointwise 95% paired subject-cluster bootstrap; no hypothesis-test p-values",
            "limitations":["10 independent held-out subjects per source","Exact lexical prose checks do not replace the separate fidelity audit",
                           "Faithfulness to ingested evidence is distinct from physiological accuracy",
                           "Replay flag/withdrawal service times exclude offered-load queues; streaming results measure queues separately"]}
    directory=Path(f"artifacts/analysis/{run_id}")
    write_json(directory/"summary.json",report)
    export_csv(directory/"case_metrics.csv",rows)
    import pandas as pd
    pd.DataFrame(rows).to_parquet(directory/"case_metrics.parquet",index=False)
    export_csv(directory/"contrasts.csv",[{**row,"ci95":str(row["ci95"])} for row in contrasts])
    figure_tables(report,directory)
    return report


def figure_tables(report,directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":10,"pdf.fonttype":42,"svg.fonttype":"none"})
    figures=Path("artifacts/figures");figures.mkdir(parents=True,exist_ok=True)
    colors=["#747474","#e69f00","#56b4e9","#0072b2","#009e73"]
    for names,title in [(("case_error","fact_recall"),"reliability"),
                        (("correction_completeness","collateral_revision"),"correction")]:
        fig,axes=plt.subplots(2,3,figsize=(10.5,5.2),sharey="row")
        for col,source in enumerate(SOURCES):
            group=[row for row in report["summary"] if row["dataset"]==source]
            for ri,metric in enumerate(names):
                values=[row[metric]["value"] for row in group]
                ax=axes[ri,col]
                ax.bar(METHODS,[v if v is not None else 0 for v in values],color=colors,width=.65)
                for x,value in enumerate(values):
                    if value is None:
                        ax.text(x,.025,"n/a",ha="center")
                ax.set_ylim(0,1.05);ax.spines[["top","right"]].set_visible(False)
                if ri==0:ax.set_title(source.replace("_","-"))
                if col==0:ax.set_ylabel(metric.replace("_"," "))
        fig.tight_layout()
        for suffix in ("pdf","svg","png"):
            fig.savefig(figures/f"{report['run_id']}_{title}.{suffix}",dpi=180,bbox_inches="tight")
        plt.close(fig)
    def percent(value):
        return "--" if value is None else f"{100*value:.1f}"
    lines=[r"\begin{tabular}{llrrrr}",r"\toprule",r"Source & Method & Case error (\%) & Fact recall (\%) & Coverage (\%) & Claims \\",r"\midrule"]
    for row in report["summary"]:
        lines.append(f"{row['dataset'].replace('_', '-')} & {row['method']} & {percent(row['case_error']['value'])} & {percent(row['fact_recall']['value'])} & {percent(row['useful_coverage']['value'])} & {row['claim_error']['denominator']} \\\\")
    lines += [r"\bottomrule",r"\end{tabular}"]
    (directory/"reliability_table.tex").write_text("\n".join(lines)+"\n")
    write_json(figures/f"{report['run_id']}_manifest.json",{"input":str(directory/"summary.json"),
        "sha256":digest_file(directory/"summary.json"),"script":"src/temporal_evidence/analysis/summarize.py"})
