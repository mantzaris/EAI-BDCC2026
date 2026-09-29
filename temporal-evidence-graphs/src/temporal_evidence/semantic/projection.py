"""Time-specific query cores with explicit mappings and derived-path witnesses."""
import json
from collections import defaultdict


def records(graph, time=float("inf")):
    return {n["properties"]["id"]: json.loads(n["properties"]["payload"])
        for n in graph["nodes"] if n["properties"].get("payload") and n["properties"].get("ingested",float("inf"))<=time}


def latest(rs):
    out={}
    for r in rs.values():
        old=out.get(r["logical_id"])
        order=lambda x:(x["version"],x["ingested_at_seconds"],x["record_id"])
        if old is None or order(r)>order(old): out[r["logical_id"]]=r
    return out


def assessment_sidecar(graph, time):
    groups=defaultdict(list)
    for n in graph["nodes"]:
        if n["semantic_type"]!="assessment": continue
        a=n["properties"]
        if a["known_at"]<=time:groups[a["id"]].append({**a,"database_element_id":n["id"]})
    answer={}
    for rid,rows in groups.items():
        known_at=max(a["known_at"] for a in rows)
        tied=sorted((a for a in rows if a["known_at"]==known_at),key=lambda a:(a["trigger_id"],a["database_element_id"]))
        states={a["state"] for a in tied}
        if len(states)>1:
            answer[rid]={"id":rid,"known_at":known_at,"state":"ambiguous_same_time","outcomes":tied,
                "note":"Trigger order is not encoded by knowledge time; no final state is inferred from element IDs."}
        else:
            answer[rid]={**tied[0],"outcomes":tied}
    return answer


def core(graph, case_id, knowledge_time, include_withdrawn=False):
    rs=records(graph,knowledge_time); current=latest(rs)
    candidates=[r for r in current.values() if r["record_type"]=="explanation" and r["metadata"].get("case_id")==case_id]
    if not candidates:
        return {"scope":graph["scope"],"case_id":case_id,"knowledge_time":knowledge_time,"nodes":[],"edges":[],"sidecars":{},"counts":{"nodes":0,"edges":0}}
    explanation=max(candidates,key=lambda r:r["version"])
    root_ids=list(explanation["source_ids"])
    if include_withdrawn:
        root_ids=sorted(r["record_id"] for r in rs.values() if r["record_type"]=="claim" and r["record_id"].startswith(case_id+"/claim/"))
    dbnodes={n["properties"].get("id"):n for n in graph["nodes"] if n["semantic_type"]!="assessment"}
    dbedges={(e["source"],e["type"],e["target"]):e for e in graph["edges"]}
    states=assessment_sidecar(graph,knowledge_time)
    chosen={}; edges=[]; agenda=list(root_ids); visited=set()
    while agenda:
        rid=agenda.pop()
        if rid in visited or rid not in rs: continue
        visited.add(rid); r=rs[rid]
        if r["record_type"] not in {"feature","claim"}: continue
        chosen[rid]=r
        if r["record_type"]!="claim": continue
        proposition=r["metadata"].get("claim",{})
        resolve_at=knowledge_time
        if proposition.get("temporal_mode")=="historical":
            resolve_at=proposition.get("as_of_knowledge_time",knowledge_time)
            if resolve_at>knowledge_time:raise ValueError("future historical scope in semantic projection")
        resolved_versions=current if resolve_at==knowledge_time else latest(records(graph,resolve_at))
        for source_id in r["source_ids"]:
            if source_id not in rs: continue
            original=rs[source_id]
            resolved=resolved_versions.get(original["logical_id"]) if original["record_type"]=="feature" else original
            if resolved is None:continue
            target=resolved["record_id"]
            if resolved["record_type"] not in {"feature","claim"}: continue
            witness=[dbedges[(dbnodes[rid]["id"],"DEPENDS_ON",dbnodes[source_id]["id"])]["id"]]
            version_ids=[source_id]
            cursor=resolved
            while cursor["record_id"]!=source_id and cursor.get("supersedes_id") in rs:
                prior=cursor["supersedes_id"]
                e=dbedges.get((dbnodes[cursor["record_id"]]["id"],"SUPERSEDES",dbnodes[prior]["id"]))
                if e: witness.append(e["id"])
                version_ids.append(cursor["record_id"]); cursor=rs[prior]
            edges.append({"source":rid,"target":target,"type":"DEPENDS_ON" if target==source_id else "CURRENT_CITATION_PATH",
                "directly_stored":target==source_id,"witness_edge_ids":witness,"witness_record_ids":version_ids,
                "declared_source_id":source_id,"semantics":"declared_prerequisite" if resolved["record_type"]=="claim" else "evidence_citation",
                "resolved_knowledge_time":resolve_at,
                "origin":"model_parent" if resolved["record_type"]=="claim" else "model_citation"})
            agenda.append(target)
    nodes=[]; provenance={}
    for rid,r in sorted(chosen.items()):
        claim=r["metadata"].get("claim")
        nodes.append({"id":rid,"database_element_id":dbnodes[rid]["id"],"type":r["record_type"],
            "logical_id":r["logical_id"],"version":r["version"],"quantity":r["quantity"],"unit":r["unit"],"value":r["value"],
            "interval":[(claim or r)["event_start_seconds"],(claim or r)["event_end_seconds"]],"ingested":r["ingested_at_seconds"],
            "evidence_state":r["evidence_state"],"claim":claim,"displayed_member":rid in explanation["source_ids"],
            "assessment":states.get(rid),"accepted_at_creation":r["metadata"].get("accepted")})
        if r["record_type"]=="feature":
            provenance[rid]=[]
            for source in r["source_ids"]:
                if source in rs:
                    edge=dbedges.get((dbnodes[rid]["id"],"DERIVED_FROM",dbnodes[source]["id"]))
                    provenance[rid].append({"record":rs[source],"database_element_id":dbnodes[source]["id"],"edge_id":edge["id"] if edge else None})
    return {"scope":graph["scope"],"case_id":case_id,"knowledge_time":knowledge_time,
        "projection":"latest explanation members + declared claim ancestors + cited features resolved at the proposition knowledge time; no SUPPORTS mirror",
        "nodes":nodes,"edges":edges,"counts":{"nodes":len(nodes),"edges":len(edges)},
        "sidecars":{"explanation":explanation,"observation_provenance":provenance,
            "omitted_types":["subject","sensor","observation","explanation","assessment","review"],
            "include_withdrawn_for_revision_drawing":include_withdrawn}}


def dependency_statistics(projected):
    nodes={n["id"]:n for n in projected["nodes"]}; parents=defaultdict(set); cited=defaultdict(set)
    indegree={n:0 for n in nodes}; outdegree={n:0 for n in nodes}
    for e in projected["edges"]:
        outdegree[e["source"]]+=1; indegree[e["target"]]+=1
        (parents if nodes[e["target"]]["type"]=="claim" else cited)[e["source"]].add(e["target"])
    memo={}
    def depth(n,active=None):
        if n in memo: return memo[n]
        active=set() if active is None else active
        if n in active: raise ValueError("cycle in stored dependency core")
        memo[n]=max((1+depth(p,active|{n}) for p in parents[n]),default=0)
        return memo[n]
    claims=[n for n in nodes if nodes[n]["type"]=="claim"]
    return {"claims":len(claims),"features":len(nodes)-len(claims),"parentless":sum(not parents[n] for n in claims),
        "claim_parent_degrees":[len(parents[n]) for n in claims],"claim_depths":[depth(n) for n in claims],
        "direct_evidence_counts":[len(cited[n]) for n in claims],"in_degrees":list(indegree.values()),"out_degrees":list(outdegree.values())}


def active_graph(graph, knowledge_time):
    """Latest evidence plus current display members; provenance witnesses retained.

    DEPENDS_ON alone supplies dependency degree. DERIVED_FROM is a typed provenance
    mirror, retained for inspection but never counted twice in that degree.
    """
    rs=records(graph,knowledge_time); current=latest(rs)
    selected={r["record_id"]:r for r in current.values() if r["record_type"] in {"feature","observation"}}
    edges={}; sidecars={}
    for r in current.values():
        if r["record_type"]!="explanation" or not r["metadata"].get("case_id"): continue
        c=core(graph,r["metadata"]["case_id"],knowledge_time)
        for n in c["nodes"]: selected[n["id"]]=rs[n["id"]]
        for e in c["edges"]: edges[(e["source"],e["type"],e["target"])]=e
        sidecars[r["record_id"]]=c["sidecars"]
    # Preserve actual feature provenance, including an older observation version
    # if that is the input from which this feature was extracted.
    for r in list(selected.values()):
        if r["record_type"]=="feature":
            for source in r["source_ids"]:
                if source in rs: selected[source]=rs[source]
    db={n["id"]:n["properties"].get("id") for n in graph["nodes"] if n["semantic_type"]!="assessment"}
    for e in graph["edges"]:
        a,b=db.get(e["source"]),db.get(e["target"])
        if a in selected and b in selected and selected[a]["record_type"]=="feature" and e["type"] in {"DEPENDS_ON","DERIVED_FROM"}:
            edges[(a,e["type"],b)]={"source":a,"target":b,"type":e["type"],"directly_stored":True,"witness_edge_ids":[e["id"]]}
    return {"scope":graph["scope"],"knowledge_time":knowledge_time,"nodes":[{"id":k,"type":r["record_type"],"record":r} for k,r in sorted(selected.items())],
        "edges":list(edges.values()),"sidecars":sidecars,"definition":"latest visible evidence + latest displayed claims and ancestors, with actual observation provenance; SUPPORTS mirror omitted"}
