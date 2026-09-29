"""Proposed versus accepted topology and the intermediate active projection."""
from collections import Counter,defaultdict
from pathlib import Path
from temporal_evidence.io import write_json,read_json
from temporal_evidence.semantic.export import read_export
from temporal_evidence.semantic.projection import active_graph
from temporal_evidence.semantic.statistics import csv_rows,cluster_ratio,cluster_mean

ROOT=Path("artifacts/analysis/semantic_analysis_v1")

def stages(outputs):
    rows=[]
    for o in outputs:
        c=o["case"];accepted={d["claim_id"] for d in o["validation"] if d["state"]=="supported"}
        options={"proposal":(o.get("raw_candidate") or {}).get("claims",[]),"displayed":(o.get("display") or {}).get("claims",[])}
        if c["method"]!="B0":options["accepted"]=[p for p in (o.get("final_candidate") or {}).get("claims",[]) if p["claim_id"] in accepted]
        for stage,claims in options.items():
            byid={p["claim_id"]:p for p in claims}; memo={}
            def depth(cid,seen=None):
                if cid in memo:return memo[cid]
                seen=set() if seen is None else seen
                if cid in seen or cid not in byid:return None
                ds=[depth(p,seen|{cid}) for p in byid[cid]["depends_on_claim_ids"]]
                memo[cid]=None if any(d is None for d in ds) else max((1+d for d in ds),default=0)
                return memo[cid]
            rows.append({**c,"stage":stage,"claims":len(claims),"parentless":sum(not p["depends_on_claim_ids"] for p in claims),
                "parent_edges":sum(len(set(p["depends_on_claim_ids"])) for p in claims),"citation_edges":sum(len(set(p["evidence_ids"])) for p in claims),
                "claim_depths":[depth(p["claim_id"]) for p in claims],"parent_degrees":[len(set(p["depends_on_claim_ids"])) for p in claims],
                "evidence_counts":[len(set(p["evidence_ids"])) for p in claims],"status":"model proposed" if stage=="proposal" or c["method"]=="B0" else "accepted at insertion"})
    write_json(ROOT/"proposed_accepted_displayed_structure.json",rows)
    groups=defaultdict(list)
    for r in rows:groups[(r["dataset"],r["method"],r["stage"])].append(r)
    write_json(ROOT/"parent_structure_summary.json",[{"dataset":s,"method":m,"stage":stage,
        "parentless":cluster_ratio(group,"parentless","claims"),"claims":sum(r["claims"] for r in group),
        "parent_edges":sum(r["parent_edges"] for r in group),"citation_edges":sum(r["citation_edges"] for r in group),
        "unresolved_or_cyclic_depths":sum(v is None for r in group for v in r["claim_depths"])} for (s,m,stage),group in sorted(groups.items())])

def active(outputs):
    groups=defaultdict(list)
    for o in outputs:
        c=o["case"]
        if c["method"]=="M1": groups[f"minimum_v1__{c['episode_id']}__{c['variant']}__M1.json.gz"].append(c)
    rows=[];mixing=Counter();origin_scopes=[]
    for filename,cases in groups.items():
        graph=read_export(ROOT/"exports"/filename)
        origin_scopes.append({**{k:cases[0][k] for k in ("dataset","subject","episode_id","variant")},
            "scope":graph["scope"],"node":Counter(n["construction_origin"] for n in graph["nodes"]),
            "edge":Counter(e["construction_origin"] for e in graph["edges"])})
        for c in cases:
            a=active_graph(graph,c["knowledge_time"]+.01); nodes={n["id"]:n for n in a["nodes"]}
            indegree=Counter();outdegree=Counter()
            for e in a["edges"]:
                mixing[(c["dataset"],e["type"],nodes[e["source"]]["type"],nodes[e["target"]]["type"])]+=1
                if e["type"]!="DERIVED_FROM":indegree[e["target"]]+=1;outdegree[e["source"]]+=1
            rows.append({**c,"nodes":len(nodes),"edges":len(a["edges"]),"node_types":dict(Counter(n["type"] for n in a["nodes"])),
                "edge_types":dict(Counter(e["type"] for e in a["edges"])),"in_degrees":[indegree[n] for n in nodes],"out_degrees":[outdegree[n] for n in nodes],
                "derived_current_paths":sum(not e["directly_stored"] for e in a["edges"])})
    write_json(ROOT/"active_graph_by_snapshot.json",rows)
    origin_rows=[]
    for kind in ("node","edge"):
        alphabet=sorted({o for r in origin_scopes for o in r[kind]})
        for r in origin_scopes:
            for origin in alphabet:origin_rows.append({**{k:v for k,v in r.items() if k not in {"node","edge"}},
                "object":kind,"origin":origin,"count":r[kind].get(origin,0)})
    csv_rows(ROOT/"construction_origins_by_scope.csv",origin_rows)
    grouped=defaultdict(list)
    for r in origin_rows:grouped[(r["dataset"],r["object"],r["origin"])].append(r)
    write_json(ROOT/"construction_origin_uncertainty.json",[{"dataset":s,"object":k,"origin":o,"count":cluster_mean(rs,"count")}
        for (s,k,o),rs in sorted(grouped.items())])
    csv_rows(ROOT/"active_relation_mixing.csv",[{"dataset":s,"relation":r,"source_type":a,"target_type":b,"count":mixing[(s,r,a,b)]}
        for s in ("synthetic","wesad","ppg_dalia") for r in ("DEPENDS_ON","DERIVED_FROM","CURRENT_CITATION_PATH")
        for a in ("observation","feature","claim") for b in ("observation","feature","claim")])

def run(outputs=None):
    if outputs is None: outputs=[read_json(p) for p in sorted(Path("artifacts/runs/minimum_v1/cases").glob("*.json"))]
    stages(outputs);active(outputs)
    audit=[]
    for entry in read_json(ROOT/"exports/manifest.json")["scopes"]:
        graph=read_export(ROOT/"exports"/entry["file"]);groups=defaultdict(list)
        for node in graph["nodes"]:
            if node["semantic_type"]=="assessment":
                a=node["properties"];groups[(a["id"],a["known_at"])].append(a)
        for (rid,time),group in groups.items():
            if len(group)>1:audit.append({"scope":entry["scope"],"record_id":rid,"known_at":time,
                "assessments":len(group),"states":sorted({a["state"] for a in group}),
                "trigger_ids":sorted(a["trigger_id"] for a in group),"conflicting_states":len({a["state"] for a in group})>1})
    write_json(ROOT/"assessment_temporal_audit.json",{"same_time_groups":len(audit),"conflicting_state_groups":sum(r["conflicting_states"] for r in audit),
        "scope":"All 480 original exported scopes; states are provenance outcomes, never reference truth.",
        "resolution":"Preserve all tied latest outcomes; mark conflicting sidecars ambiguous_same_time. No within-time ordering is invented.",
        "groups":audit})

if __name__=="__main__":run()
