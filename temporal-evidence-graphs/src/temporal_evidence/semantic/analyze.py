"""Re-score saved answers, measure actual graph structure and revision exposure."""
from collections import Counter,defaultdict
from pathlib import Path
import json
import numpy as np
from temporal_evidence.io import read_json,write_json,digest_file
from temporal_evidence.semantic.scoring import score,proposition,snapshot
from temporal_evidence.semantic.export import read_export,write_gzip
from temporal_evidence.semantic.projection import core,records,latest,dependency_statistics
from temporal_evidence.semantic.ontology import TYPES,RELATIONS
from temporal_evidence.semantic.statistics import cluster_ratio,cluster_mean,csv_rows

ROOT=Path("artifacts/analysis/semantic_analysis_v1")
SOURCES=("synthetic","wesad","ppg_dalia")
METHODS=("B0","B1","B2","M1","B3")

def brief(result): return {k:v for k,v in result.items() if k not in {"claims","requirements"}}

def aggregate(rows,keys):
    groups=defaultdict(list)
    for r in rows: groups[tuple(r[k] for k in keys)].append(r)
    out=[]
    for key,group in sorted(groups.items()):
        entry=dict(zip(keys,key)); entry.update(cases=len(group),empty=sum(r["empty"] for r in group),
            **{k:sum(r[k] for r in group) for k in ("emitted","grounded","answerable","matched","witness_valid","prose_flagged")})
        entry["precision"]=cluster_ratio(group,"grounded","emitted")
        entry["recall"]=cluster_ratio(group,"matched","answerable")
        entry["witness_fidelity"]=cluster_ratio(group,"witness_valid","emitted")
        entry["harmonic_case_mean"]=cluster_mean(group,"harmonic")
        out.append(entry)
    return out

def semantic_scores(outputs,episodes):
    rows=[]; details=[]; crosswalk=[]; trajectories=[]
    bycase={o["case"]["case_id"]:o for o in outputs}
    for output in outputs:
        case=output["case"]; cid=case["case_id"]; events=episodes[case["episode_id"]]["variants"][case["variant"]]["events"]
        raw=(output.get("raw_candidate") or {}).get("claims",[])
        final=(output.get("final_candidate") or {}).get("claims",[])
        accepted_ids={d["claim_id"] for d in output["validation"] if d["state"]=="supported"}
        stages={"proposal":raw,"final_proposal":final,"displayed":(output.get("display") or {}).get("claims",[])}
        if case["method"]!="B0": stages["accepted"]=[c for c in final if c["claim_id"] in accepted_ids]
        results={}
        for stage,claims in stages.items():
            result=score(claims,events,output["query"]); results[stage]=result
            rows.append({**case,"stage":stage,**brief(result)})
        details.append({"case_id":cid,"query":output["query"],"stages":results})
        frozen=read_json(Path("artifacts/evaluation/minimum_v1/cases")/(cid+".json"))
        for claim,new,old in zip(stages["displayed"],results["displayed"]["claims"],frozen["claims"]):
            crosswalk.append({**case,"claim_id":claim["claim_id"],"contract_valid":old["valid"],"grounded":new["grounded"],
                "witness_valid":new["witness_valid"],"background":new["background"],"contract_reasons":"|".join(old["reasons"]),
                "semantic_reasons":"|".join(new["reasons"]),"prose_audit":"|".join(new["prose_audit"]),"sentence":claim["sentence"]})
        if case["checkpoint"]==0: continue
        prior_id=cid.replace(f"-c{case['checkpoint']}-",f"-c{case['checkpoint']-1}-"); previous=bycase[prior_id]
        old_claims=(previous.get("display") or {}).get("claims",[])
        persistent=[item for rid,item in output["persistent_before"].items() if rid.startswith(prior_id+"/claim/")]
        retained=[item["claim"] for item in persistent if item["state"] in {"supported","unverified","pending"}]
        for position,claims,q in (("before",old_claims,previous["query"]),("arrival",old_claims,output["query"]),("maintained",retained,output["query"])):
            result=score(claims,events,q,remap_citations=True)
            trajectories.append({**case,"position":position,"from_case_id":prior_id,"original_claims":len(old_claims),
                "withdrawn":len(old_claims)-len(claims),"contradicted_or_ungrounded":result["emitted"]-result["grounded"],**brief(result)})
    write_gzip(ROOT/"proposition_scores.json.gz",details)
    write_json(ROOT/"semantic_metrics.json",rows);csv_rows(ROOT/"semantic_metrics.csv",rows)
    write_json(ROOT/"semantic_summary.json",aggregate(rows,("dataset","method","stage")))
    csv_rows(ROOT/"contract_crosswalk.csv",crosswalk)
    write_json(ROOT/"contract_crosswalk_summary.json",[{"dataset":s,"method":m,"claims":len(g),
        "contract_invalid":sum(not r["contract_valid"] for r in g),"contract_invalid_but_grounded":sum(not r["contract_valid"] and r["grounded"] for r in g),
        "contract_invalid_grounded_background":sum(not r["contract_valid"] and r["grounded"] and r["background"] for r in g),
        "contract_valid_but_ungrounded":sum(r["contract_valid"] and not r["grounded"] for r in g)}
        for s in SOURCES for m in METHODS for g in [[r for r in crosswalk if r["dataset"]==s and r["method"]==m]]])
    write_json(ROOT/"temporal_checkpoints.json",trajectories);csv_rows(ROOT/"temporal_checkpoints.csv",trajectories)
    write_json(ROOT/"temporal_summary.json",aggregate(trajectories,("dataset","method","variant","position")))
    write_json(ROOT/"temporal_summary_all_variants.json",aggregate(trajectories,("dataset","method","position")))
    return rows

def reverse_reach(adjacency,roots):
    result=set(); agenda=list(roots)
    while agenda:
        for node in adjacency.get(agenda.pop(),()):
            if node not in result: result.add(node);agenda.append(node)
    return result

def graph_analysis(outputs,episodes):
    graphs={}; full=[]; cores=[]; distributions=[]; mixing=Counter(); origins=Counter(); revision_rows=[]; eligible=defaultdict(list); competency=Counter()
    metadata=read_json(ROOT/"exports/manifest.json")
    for item in metadata["scopes"]:
        if not item["scope"].endswith("/M1"): continue
        graph=read_export(ROOT/"exports"/item["file"]); _,eid,variant,method=item["scope"].split("/")
        episode=episodes[eid]; info={"dataset":episode["dataset"],"subject":episode["subject"],"episode_id":eid,"variant":variant,"method":method,"scope":item["scope"]}
        graphs[item["scope"]]=graph; nodes={n["id"]:n for n in graph["nodes"]}
        full.append({**info,"nodes":len(nodes),"edges":len(graph["edges"]),**{f"nodes_{k}":item["node_types"].get(k,0) for k in TYPES},**{f"edges_{k}":item["edge_types"].get(k,0) for k in RELATIONS}})
        for e in graph["edges"]:
            mixing[(episode["dataset"],"stored",e["type"],nodes[e["source"]]["semantic_type"],nodes[e["target"]]["semantic_type"])]+=1
            origins[(episode["dataset"],"edge",e["construction_origin"])]+=1
        for n in nodes.values(): origins[(episode["dataset"],"node",n["construction_origin"])]+=1
    for output in outputs:
        c=output["case"]
        if c["method"]!="M1": continue
        scope=f"minimum_v1/{c['episode_id']}/{c['variant']}/M1"; graph=graphs[scope]; t=c["knowledge_time"]+.01
        projected=core(graph,c["case_id"],t); stats=dependency_statistics(projected)
        rs=records(graph,t); current=latest(rs); visible_assessments=[n for n in graph["nodes"] if n["semantic_type"]=="assessment" and n["properties"]["known_at"]<=t]
        latest_exps=[r for r in current.values() if r["record_type"]=="explanation"]
        active_claims={rid for r in latest_exps for rid in r["source_ids"]}
        todo=list(active_claims)
        while todo:
            for sid in rs[todo.pop()]["source_ids"]:
                if sid in rs and rs[sid]["record_type"]=="claim" and sid not in active_claims:active_claims.add(sid);todo.append(sid)
        active={r["record_id"] for r in current.values() if r["record_type"] in {"feature","observation"}}|active_claims
        active_db={n["id"] for n in graph["nodes"] if n["properties"].get("id") in active and n["semantic_type"]!="assessment"}
        active_edges=[e for e in graph["edges"] if e["source"] in active_db and e["target"] in active_db and e["type"] in {"DEPENDS_ON","DERIVED_FROM","SUPPORTS"}]
        cores.append({**c,"core_nodes":len(projected["nodes"]),"core_edges":len(projected["edges"]),"full_visible_nodes":len(rs)+len(visible_assessments),
            "core_full_ratio":len(projected["nodes"])/(len(rs)+len(visible_assessments)),"active_nodes":len(active),"active_stored_edges":len(active_edges),
            **{k:v for k,v in stats.items() if not isinstance(v,list)}})
        distributions.append({**c,**stats})
        pnodes={n["id"]:n for n in projected["nodes"]}
        for e in projected["edges"]:mixing[(c["dataset"],"core",e["type"],pnodes[e["source"]]["type"],pnodes[e["target"]]["type"])]+=1
        events=episodes[c["episode_id"]]["variants"][c["variant"]]["events"]
        event_byid={e["record_id"]:e for e in events}
        _,oracle_latest=snapshot(events,c["knowledge_time"])
        witness_counts=[]
        for n in projected["nodes"]:
            if n["type"]=="feature" and n["logical_id"] in oracle_latest:
                competency[(c["dataset"],"known_version","total")]+=1
                competency[(c["dataset"],"known_version","correct")]+=n["id"]==oracle_latest[n["logical_id"]]["record_id"]
                for p in projected["sidecars"]["observation_provenance"].get(n["id"],[]):
                    r=p["record"]; competency[(c["dataset"],"source_window","total")]+=1
                    competency[(c["dataset"],"source_window","correct")]+=r==event_byid.get(r["record_id"])
            if n["type"]=="claim":
                oracle=proposition(n["claim"],events,output["query"])
                witness_counts.append(len(oracle["witnesses"]))
                if n["claim"]["claim_type"] in {"comparison","trend"}:
                    competency[(c["dataset"],"comparison_witness","total")]+=1
                    competency[(c["dataset"],"comparison_witness","correct")]+=oracle["witness_valid"]
        distributions[-1]["admissible_witness_counts"]=witness_counts
        if c["checkpoint"]==0 and c["variant"]=="correction" and c["dataset"] in {"wesad","ppg_dalia"}:
            after=core(graph,c["case_id"],c["knowledge_time"]+30+.01,include_withdrawn=True)
            changed=[]
            for n in projected["nodes"]:
                if n["type"]=="claim" and proposition(n["claim"],events,output["query"])["grounded"] and not proposition(n["claim"],events,{**output["query"],"knowledge_time":c["knowledge_time"]+30})["grounded"]:changed.append(n["id"])
            if changed:eligible[c["dataset"]].append({"case_id":c["case_id"],"size":len(projected["nodes"]),"changed":changed,"before":projected,"after":after})
    # Each revision time is a batch: simultaneous feature/observation versions are
    # one delta, preventing duplicate counting of the same semantic transition.
    for scope,graph in graphs.items():
        _,eid,variant,_=scope.split("/");episode=episodes[eid];events=episode["variants"][variant]["events"]
        allrs=records(graph); times=sorted({r["ingested_at_seconds"] for r in allrs.values() if r["record_type"] in {"observation","feature"} and r["version"]>1})
        for t in times:
            rs=records(graph,t); changed=[r for r in rs.values() if r["ingested_at_seconds"]==t and r["version"]>1 and r["record_type"] in {"observation","feature"}]
            logicals={r["logical_id"] for r in changed}; roots={r["record_id"] for r in rs.values() if r["logical_id"] in logicals and r["ingested_at_seconds"]<t}
            reverse=defaultdict(set)
            for r in rs.values():
                for sid in r["source_ids"]:
                    if sid in rs: reverse[sid].add(r["record_id"])
            direct=set().union(*(reverse[r] for r in roots)) if roots else set();reach=reverse_reach(reverse,roots)
            claims=[r for r in rs.values() if r["record_type"]=="claim" and r["ingested_at_seconds"]<t]
            A=set(); changed_support=set()
            for r in claims:
                claim=r["metadata"]["claim"];q=r["metadata"]["query"]
                before=proposition(claim,events,{**q,"knowledge_time":t-1e-5})["grounded"]
                after=proposition(claim,events,{**q,"knowledge_time":t})["grounded"]
                if before!=after:changed_support.add(r["record_id"])
                if before and not after:A.add(r["record_id"])
            revision_rows.append({"dataset":episode["dataset"],"subject":episode["subject"],"episode_id":eid,"variant":variant,"scope":scope,"knowledge_time":t,
                "roots":len(roots),"potential_records":len(reach),"potential_claims":sum(r["record_id"] in reach for r in claims),
                "actual_support_changes":len(changed_support),"required_changes":len(A),"direct_claims":sum(r["record_id"] in direct for r in claims),
                "excluded_required":len(A-direct),"xi":len(A-direct)/len(A) if A else None,
                "locality_holds":changed_support<=reach,"required_ids":sorted(A),"direct_ids":sorted(direct),"affected_ids":sorted(reach)})
    selections=[]
    (ROOT/"representative_cores").mkdir(exist_ok=True)
    for source,items in sorted(eligible.items()):
        ordered=sorted(items,key=lambda r:(r["size"],r["case_id"]))
        selected={"median":ordered[(len(ordered)-1)//2],"high_impact":sorted(items,key=lambda r:(-len(r["changed"]),r["case_id"]))[0]}
        for rule,item in selected.items():
            item={**item,"dataset":source,"selection_rule":rule,"eligible":len(items),"layout_seed":20260929}
            write_json(ROOT/"representative_cores"/f"{source}_{rule}.json",item)
            selections.append({k:v for k,v in item.items() if k not in {"before","after"}})
    write_json(ROOT/"representative_selection.json",selections)
    write_json(ROOT/"storage_by_scope.json",full);csv_rows(ROOT/"storage_by_scope.csv",full)
    write_json(ROOT/"core_by_snapshot.json",cores);csv_rows(ROOT/"core_by_snapshot.csv",cores)
    write_json(ROOT/"degree_depth_witness_distributions.json",distributions)
    write_json(ROOT/"revision_exposure.json",revision_rows)
    csv_rows(ROOT/"revision_exposure.csv",[{k:v for k,v in r.items() if not isinstance(v,list)} for r in revision_rows])
    write_json(ROOT/"construction_origins.json",[{"dataset":k[0],"object":k[1],"origin":k[2],"count":v} for k,v in sorted(origins.items())])
    # Common alphabet including meaningful zeros, regardless of observed source.
    mixing_rows=[{"dataset":s,"projection":p,"relation":r,"source_type":a,"target_type":b,"count":mixing[(s,p,r,a,b)]}
        for s in SOURCES for p in ("stored","core") for r in (*RELATIONS,"CURRENT_CITATION_PATH") for a in TYPES for b in TYPES]
    csv_rows(ROOT/"relation_type_mixing.csv",mixing_rows)
    write_json(ROOT/"competency_queries.json",[{"dataset":s,"question":q,"correct":competency[(s,q,"correct")],"total":competency[(s,q,"total")]}
        for s in SOURCES for q in ("source_window","known_version","comparison_witness")])
    summaries=[]
    for source in SOURCES:
        cs=[r for r in cores if r["dataset"]==source];rev=[r for r in revision_rows if r["dataset"]==source]
        summaries.append({"dataset":source,"core_nodes":cluster_mean(cs,"core_nodes"),"core_ratio":cluster_mean(cs,"core_full_ratio"),
            "parentless":cluster_ratio(cs,"parentless","claims"),"revision_batches":len(rev),"with_required_change":sum(r["required_changes"]>0 for r in rev),
            "with_nonzero_exposure":sum(r["xi"] is not None and r["xi"]>0 for r in rev),"locality_violations":sum(not r["locality_holds"] for r in rev),
            "potential_records":cluster_mean(rev,"potential_records"),"actual_support_changes":cluster_mean(rev,"actual_support_changes")})
    write_json(ROOT/"structure_summary.json",summaries)

def run():
    outputs=[read_json(p) for p in sorted(Path("artifacts/runs/minimum_v1/cases").glob("*.json"))]
    episodes={eid:read_json(f"artifacts/prepared/{eid}.json") for eid in {o["case"]["episode_id"] for o in outputs}}
    semantic_scores(outputs,episodes);graph_analysis(outputs,episodes)
    from temporal_evidence.semantic.additional_statistics import run as additional
    additional(outputs)
    write_json(ROOT/"analysis_manifest.json",{"namespace":"semantic_analysis_v1","original_run":"minimum_v1","cases":len(outputs),
        "oracle_inputs":"immutable prepared events and fixed task specification, never database support flags",
        "source_hashes":{str(p):digest_file(p) for p in sorted(Path("src/temporal_evidence/semantic").glob("*.py"))},
        "original_protocol_hash":read_json("artifacts/manifests/minimum_run.json")["protocol_hash"],
        "export_manifest_sha256":digest_file(ROOT/"exports/manifest.json")})
    print("Semantic scoring, temporal checkpoints, actual graph statistics and exposure complete.")

if __name__=="__main__": run()
