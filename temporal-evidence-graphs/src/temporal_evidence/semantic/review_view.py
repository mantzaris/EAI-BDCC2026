"""A bounded, auditable review graph shared by the dashboard and paper.

Stored citations are never redirected. Version resolution is a separate path
sidecar. Layout, highlighting and human labels cannot change support semantics.
"""
from collections import deque
import json

from temporal_evidence.io import digest_object
from temporal_evidence.semantic.projection import records, latest, assessment_sidecar

HIDDEN = {
    "FOR_SUBJECT": "identity hubs", "OBSERVED_BY": "sensor identities",
    "SUPPORTS": "admission-time mirror, not current support",
    "CONTAINS": "display membership retained as node attributes",
    "ASSESSED_AS": "time-filtered assessments retained in the detail panel",
    "CONTRADICTS": "assessment outcomes retained with their knowledge time",
    "REVIEWED_BY_EVENT": "review events retained in the workspace history",
    "feature DEPENDS_ON": "duplicate of displayed DERIVED_FROM provenance",
}
MEANINGS = {
    "DEPENDS_ON": "Dependent → immutable cited input or declared prerequisite; not a causal arrow.",
    "DERIVED_FROM": "Feature → observation/input used for its extraction.",
    "SUPERSEDES": "New version → earlier immutable version; does not make historical data false.",
    "CURRENT_CITATION_PATH": "Derived resolution through an original citation and reverse supersession traversal.",
}


def graph_from_store(store):
    """Read actual stored rows/relations, including the relational control.

SQLite row keys are explicit local identities, not fabricated Neo4j element IDs.
The shared view format uses the same immutable Record IDs in either backend.
"""
    if hasattr(store, "driver"):
        from temporal_evidence.semantic.export import NODE_QUERY, EDGE_QUERY
        from temporal_evidence.semantic.ontology import kind
        with store.driver.session() as session:
            nodes = [dict(r) for r in session.run(NODE_QUERY, prefix=store.scope)
                     if r["properties"]["scope"] == store.scope]
            edges = [dict(r) for r in session.run(EDGE_QUERY, prefix=store.scope) if r["scope"] == store.scope]
        for n in nodes:
            n["semantic_type"] = kind(n)
        return {"scope": store.scope, "instance": "live Neo4j review workspace", "nodes": nodes, "edges": edges}
    nodes, edges = [], []
    con = store.connection
    for rid, payload, ingested in con.execute("SELECT id,payload,ingested FROM records WHERE scope=?", (store.scope,)):
        r = json.loads(payload)
        nodes.append({"id": rid, "semantic_type": r["record_type"],
                      "properties": {"id": rid, "payload": payload, "ingested": ingested, "scope": store.scope}})
    for a, b, rel in con.execute("SELECT dependent,required,relation FROM dependencies WHERE scope=?", (store.scope,)):
        edges.append({"id": "sqlite-edge/"+digest_object([store.scope,a,rel,b]), "source": a, "target": b, "type": rel})
    for rid, time, state, value, trigger in con.execute("SELECT id,known_at,state,value,trigger_id FROM assessments WHERE scope=?", (store.scope,)):
        aid = "sqlite-assessment/"+digest_object([store.scope,rid,time,trigger])
        nodes.append({"id": aid, "semantic_type": "assessment", "properties": {
            "id": rid, "scope": store.scope, "known_at": time, "state": state, "value": value, "trigger_id": trigger}})
    return {"scope": store.scope, "instance": "actual SQLite review rows", "nodes": nodes, "edges": edges}


def build_view(graph, case_id, knowledge_time, focus_ids, *, budget=18,
               expand_provenance=True, program_case=None, baseline_time=None,
               source=None, support_overrides=None):
    """Close prerequisites, preserve version history, then apply a visible budget.

The budget counts stored record nodes. Complete witness closures are preferred;
if the closure does not fit, missing inputs/groups are explicitly enumerated.
Assessments, raw records and original path IDs remain available in sidecars.
"""
    if budget < 1:
        raise ValueError("The stored-node budget must be positive")
    rs = records(graph, knowledge_time)
    current = latest(rs)
    focus_ids = list(dict.fromkeys(focus_ids))
    if any(rid not in rs for rid in focus_ids):
        raise ValueError("A focus record is absent at the selected knowledge time")
    dbnodes = {n["properties"].get("id"): n for n in graph["nodes"] if n["properties"].get("payload")}
    dbids = {n["id"]: rid for rid,n in dbnodes.items()}
    stored = {(dbids.get(e["source"]),e["type"],dbids.get(e["target"])):e for e in graph["edges"]}
    assessments = assessment_sidecar(graph, knowledge_time)
    focus_logicals={rs[i]["logical_id"] for i in focus_ids}
    histories={r["logical_id"] for r in rs.values() if r["record_type"]=="explanation" and
               any(i in rs and rs[i]["logical_id"] in focus_logicals for i in r["source_ids"])}
    exps = [r for r in current.values() if r["record_type"] == "explanation" and (
        r["metadata"].get("case_id") == case_id or r["logical_id"] == case_id+"/explanation" or
        r["logical_id"] in histories)]
    displayed = {i for r in exps for i in r["source_ids"]}
    # The explanation's original member set distinguishes withdrawn from merely
    # never-displayed records; it is not a semantic correctness oracle.
    exp_logicals = {r["logical_id"] for r in exps}
    previously_displayed = {i for r in rs.values() if r["record_type"] == "explanation" and
                            r["logical_id"] in exp_logicals for i in r["source_ids"]}
    selected, order, agenda = set(), [], deque(focus_ids)
    while agenda:
        rid = agenda.popleft()
        if rid in selected or rid not in rs:
            continue
        r = rs[rid]
        if r["record_type"] not in {"claim","feature","observation"}:
            continue
        selected.add(rid); order.append(rid)
        if r["record_type"] == "claim" or expand_provenance:
            agenda.extend(sorted(r["source_ids"]))
        if r["record_type"] in {"feature","observation"}:
            agenda.extend(x["record_id"] for x in sorted(rs.values(),key=lambda x:x["record_id"])
                          if x["logical_id"] == r["logical_id"] and x["record_id"] not in selected)
    complete_selection = set(selected)
    selected = set(focus_ids[:budget])
    def witness_closure(inputs):
        closure=set();pending=list(inputs)
        while pending:
            i=pending.pop()
            if i in closure or i not in complete_selection:continue
            closure.add(i);r=rs[i]
            if r["record_type"]=="claim" or expand_provenance:pending.extend(r["source_ids"])
            if r["record_type"] in {"feature","observation"}:
                pending.extend(x for x in complete_selection if rs[x]["logical_id"]==r["logical_id"])
        return closure
    # Prefer an entire alternative over partial fragments of several routes.
    for rid in focus_ids:
        p=rs[rid]["metadata"].get("semantic_program")
        if p:
            mapping=rs[rid]["metadata"]["test_reference_map"]
            families=[[mapping.get(t,case_id+"/claim/"+t) for t in w] for w in p["witnesses"]]
        else:families=[rs[rid]["source_ids"]]
        for inputs in families:
            closure=witness_closure(inputs)
            if len(selected|closure)<=budget:selected|=closure
    for rid in order:
        if len(selected)>=budget:break
        selected.add(rid)
    omitted = sorted(complete_selection-selected)
    test_map = (program_case or {}).get("tests", {})
    logical_tokens = {t["logical_id"]:token for token,t in test_map.items()}
    features = sorted({rs[i]["logical_id"] for i in complete_selection if rs[i]["record_type"] == "feature"},
                      key=lambda k:(current[k]["event_start_seconds"],k))
    observations = sorted(i for i in complete_selection if rs[i]["record_type"] == "observation")
    groups = []
    for rid in order:
        r = rs[rid]; p = r["metadata"].get("semantic_program")
        if r["record_type"] != "claim":
            continue
        if p:
            mapping = r["metadata"]["test_reference_map"]
            families = [[mapping.get(t,case_id+"/claim/"+t) for t in w] for w in p["witnesses"]]
        else:
            families = [list(r["source_ids"])] if r["support_mode"] == "AND" else [[i] for i in r["source_ids"]]
        for j, inputs in enumerate(families,1):
            if rid not in selected:
                continue
            gids = [stored[(rid,"DEPENDS_ON",i)]["id"] for i in inputs if (rid,"DEPENDS_ON",i) in stored]
            temporal=r["metadata"].get("claim",{})
            resolve_time=temporal.get("as_of_knowledge_time",knowledge_time) if temporal.get("temporal_mode")=="historical" else knowledge_time
            if resolve_time>knowledge_time:raise ValueError("Future historical scope")
            resolution=latest(records(graph,resolve_time))
            resolved=[resolution[rs[i]["logical_id"]]["record_id"] for i in inputs if i in rs and rs[i]["record_type"]=="feature" and rs[i]["logical_id"] in resolution]
            groups.append({"id":rid+f"/w{j}", "owner":rid,"index":j,"inputs":inputs,"within":"AND","between":"OR",
                           "complete":all(i in selected for i in inputs),"omitted_inputs":[i for i in inputs if i not in selected],
                           "resolved_input_ids":resolved,"resolution_complete":all(i in selected for i in resolved),
                           "stored_edge_ids":gids,"metadata_path":"metadata.semantic_program.witnesses" if p else "Record.source_ids / support_mode",
                           "rendering_construct":True,"note":"Witness grouping is metadata, not a stored Neo4j node or relation."})
    nodes=[]
    for rid in sorted(selected):
        r=rs[rid];kind=r["record_type"];a=assessments.get(rid)
        state=a["state"] if a else "supported_at_admission" if r["metadata"].get("accepted") else "unassessed"
        if support_overrides and rid in support_overrides:
            state=support_overrides[rid]
        display="displayed" if rid in displayed else "withdrawn" if rid in previously_displayed else "not a display member"
        if kind=="feature": short=logical_tokens.get(r["logical_id"],"F"+str(features.index(r["logical_id"])+1))
        elif kind=="observation":short="O"+str(observations.index(rid)+1)
        else:short=rid.rsplit("/",1)[-1]
        changed=r["ingested_at_seconds"]>baseline_time if baseline_time is not None else False
        affected=bool(a and baseline_time is not None and a["known_at"]>baseline_time)
        proposition=r["metadata"].get("claim")
        program=r["metadata"].get("semantic_program")
        if proposition:
            intervals=[[proposition["event_start_seconds"],proposition["event_end_seconds"]]]
        elif program and program_case:
            tokens={t for w in program_case["propositions"].get(program["proposition"],[]) for t in w}
            intervals=[list(t) for t in sorted({tuple(test_map[t]["interval"]) for t in tokens if t in test_map})]
        else:intervals=[[r["event_start_seconds"],r["event_end_seconds"]]]
        nodes.append({"id":rid,"database_element_id":dbnodes[rid]["id"],"short_id":short,"type":kind,"record":r,
            "asserted_intervals":intervals,
            "proposition_witnesses":(program_case or {}).get("propositions",{}).get(program["proposition"]) if program else None,
            "assessment":a,"support_state":state,"support_origin":"current review evaluation" if support_overrides and rid in support_overrides else
            "recorded assessment" if a else "admission metadata" if r["metadata"].get("accepted") else "not evaluated",
            "display_state":display,"availability":r["evidence_state"],"version_status":"current" if current[r["logical_id"]]["record_id"]==rid else "historical version",
            "changed":changed,"affected":affected,"test":test_map.get(logical_tokens.get(r["logical_id"])),
            "witness_groups":[w["id"] for w in groups if w["owner"]==rid]})
    edges=[];paths=[]
    for (a,rel,b), e in sorted(stored.items(),key=lambda x:str(x[0])):
        if a not in selected or b not in selected:
            continue
        if not (rel=="SUPERSEDES" or rel=="DERIVED_FROM" and rs[a]["record_type"]=="feature" or
                rel=="DEPENDS_ON" and rs[a]["record_type"]=="claim"):
            continue
        memberships=[w["id"] for w in groups if w["owner"]==a and b in w["inputs"]]
        edges.append({"id":e["id"],"source":a,"target":b,"type":rel,"directly_stored":True,
                      "meaning":MEANINGS[rel],"witness_groups":memberships,"witness_edge_ids":[e["id"]]})
    # Recover current-resolution paths without replacing the stored citation.
    for e in edges:
        if e["type"]!="DEPENDS_ON" or rs[e["target"]]["record_type"]!="feature":continue
        r=rs[e["source"]];p=r["metadata"].get("claim",{})
        resolved_time=p.get("as_of_knowledge_time",knowledge_time) if p.get("temporal_mode")=="historical" else knowledge_time
        if resolved_time>knowledge_time:raise ValueError("Future historical scope")
        versions=latest(records(graph,resolved_time));old=rs[e["target"]];new=versions.get(old["logical_id"],old)
        chain=[];cursor=new;seen=set()
        while cursor["record_id"]!=old["record_id"] and cursor.get("supersedes_id") in rs and cursor["record_id"] not in seen:
            seen.add(cursor["record_id"]);prior=cursor["supersedes_id"]
            edge=stored.get((cursor["record_id"],"SUPERSEDES",prior))
            if not edge:break
            chain.append({"edge_id":edge["id"],"direction":"reverse"});cursor=rs[prior]
        if chain and cursor["record_id"]==old["record_id"]:
            paths.append({"id":"derived/"+e["id"],"source":e["source"],"target":new["record_id"],"type":"CURRENT_CITATION_PATH",
                          "directly_stored":False,"visible_edge":False,"resolved_at":resolved_time,
                          "path":[{"edge_id":e["id"],"direction":"forward"}]+list(reversed(chain)),
                          "witness_edge_ids":[e["id"]]+[c["edge_id"] for c in chain],"original_citation_id":e["target"]})
    return {"format":"review_graph_v1","scope":graph["scope"],"instance":graph.get("instance"),"case_id":case_id,
        "knowledge_time":knowledge_time,"baseline_time":baseline_time,"focus_ids":focus_ids,"nodes":nodes,"edges":edges,
        "witness_groups":groups,"derived_paths":paths,"source":source or {},
        "budget":{"limit":budget,"required_nodes":len(complete_selection),"shown_nodes":len(nodes),"partial":bool(omitted),"omitted_ids":omitted,
                  "incomplete_witness_groups":[w["id"] for w in groups if not w["complete"] or not w["resolution_complete"]]},
        "context":{"observation_provenance_expanded":expand_provenance,"hidden_relations":HIDDEN,
                   "omitted_provenance_ids":sorted({s for rid in complete_selection if rs[rid]["record_type"]=="feature" for s in rs[rid]["source_ids"] if s not in selected}),
                   "explanations":exps,"assessment_ties":"All tied outcomes retained; conflicting states are ambiguous."}}


def validate_view(view, graph):
    """Check identity, direction, visibility, grouping and path provenance."""
    ids={n["id"] for n in view["nodes"]};dbnodes={n["id"]:n for n in graph["nodes"]};dbedges={e["id"]:e for e in graph["edges"]}
    mapping={n["id"]:n["database_element_id"] for n in view["nodes"]}
    for n in view["nodes"]:
        assert n["database_element_id"] in dbnodes
        assert n["record"]["record_id"]==n["id"] and n["record"]["ingested_at_seconds"]<=view["knowledge_time"]
        if n["assessment"]:assert n["assessment"]["known_at"]<=view["knowledge_time"]
    for e in view["edges"]:
        assert e["directly_stored"] and e["id"] in dbedges
        actual=dbedges[e["id"]]
        assert (mapping[e["source"]],e["type"],mapping[e["target"]])==(actual["source"],actual["type"],actual["target"])
    for w in view["witness_groups"]:
        assert w["complete"]==all(i in ids for i in w["inputs"])
        assert set(w["omitted_inputs"])==set(w["inputs"])-ids
    for p in view["derived_paths"]:
        assert not p["directly_stored"] and not p["visible_edge"]
        assert all(i in dbedges for i in p["witness_edge_ids"])
        record_nodes={n["properties"].get("id"):n for n in graph["nodes"] if n["properties"].get("payload")}
        cursor=record_nodes[p["source"]]["id"]
        for step in p["path"]:
            edge=dbedges[step["edge_id"]]
            start,end=(edge["source"],edge["target"]) if step["direction"]=="forward" else (edge["target"],edge["source"])
            assert cursor==start
            assert dbnodes[end]["properties"]["ingested"]<=view["knowledge_time"]
            cursor=end
        assert cursor==record_nodes[p["target"]]["id"]
    assert view["budget"]["partial"]==bool(view["budget"]["omitted_ids"])
    return True
