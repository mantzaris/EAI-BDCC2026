"""Episode-first, subject-cluster descriptive uncertainty and table exports."""
from collections import defaultdict
import csv
from pathlib import Path
import numpy as np

def csv_rows(path, rows):
    rows=list(rows)
    if not rows: return
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,"w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n"); writer.writeheader();writer.writerows(rows)

def cluster_ratio(rows,numerator,denominator,seed=20260929):
    episodes=defaultdict(lambda:[0.,0.]); subjects=defaultdict(list)
    for r in rows:
        # Participant labels are scoped to a dataset (WESAD S2 is not PPG S2).
        identity=(r.get("dataset",""),r["subject"])
        episodes[(identity,r["episode_id"])][0]+=r[numerator]
        episodes[(identity,r["episode_id"])][1]+=r[denominator]
    for (subject,_),(n,d) in episodes.items():
        if d: subjects[subject].append(n/d)
    values=np.array([np.mean(v) for _,v in sorted(subjects.items())])
    if not len(values): return {"mean":None,"ci95":None,"subjects":0,"episodes":0}
    draws=np.random.default_rng(seed).choice(values,size=(2000,len(values)),replace=True).mean(axis=1)
    return {"mean":float(values.mean()),"ci95":[float(x) for x in np.quantile(draws,[.025,.975])],
        "subjects":len(values),"episodes":sum(len(v) for v in subjects.values())}

def cluster_mean(rows,value):
    return cluster_ratio([{**r,"__n":r[value],"__d":1} for r in rows if r[value] is not None],"__n","__d")
