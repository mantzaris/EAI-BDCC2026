"""Matched database replay of common admitted programs, without new generation."""
import argparse
from dataclasses import replace
from collections import defaultdict
from pathlib import Path
import time
from temporal_evidence.io import read_json,write_json,utc_now,digest_object
from temporal_evidence.schema import Record
from temporal_evidence.storage.graph import GraphStore
from temporal_evidence.storage.relational import RelationalStore
from temporal_evidence.structure.program import fixture,updates,runtime_support,validate
from temporal_evidence.structure.oracle import reference

ROOT=Path("artifacts/runs/structure_study_v1")
METHODS=("B0","B1","B2","M1","B3")
CONDITIONS=("necessary","route_loss","benign","irrelevant")


def claim_records(case,claims,origin):
    out=[]; mapping={c["claim_id"]:case["case_id"]+"/claim/"+c["claim_id"] for c in claims}
    for c in claims:
        sources=tuple(sorted({case["tests"][token]["source_id"] if token in case["tests"] else mapping[token]
            for witness in c["witnesses"] for token in witness}))
        rid=mapping[c["claim_id"]]
        out.append(Record(record_id=rid,logical_id=rid,record_type="claim",dataset_id=case["dataset"],subject_id=case["subject"],
            session_id="session_1",event_start_seconds=min(t["interval"][0] for t in case["tests"].values()),
            event_end_seconds=max(t["interval"][1] for t in case["tests"].values()),ingested_at_seconds=case["knowledge_time"]+.001,
            quantity=c["proposition"],value=float(c["value"]),unit="boolean",source_ids=sources,operator="positive_witness_program",
            metadata={"semantic_program":c,"origin":origin,"accepted":True,"test_reference_map":{k:v["source_id"] for k,v in case["tests"].items()}}))
    return out,mapping


def structure(claims,case):
    depths={}; parents={}; redundant=[]
    for c in claims:
        cid=c["claim_id"]; tokens={t for w in c["witnesses"] for t in w}
        ps=tokens-set(case["tests"]); parents[cid]=sorted(ps)
        depths[cid]=max([1 if t in case["tests"] else 1+depths[t] for t in tokens],default=0)
        redundant.append(len(c["witnesses"]))
    roots=[c["claim_id"] for c in claims if c["proposition"]=="answer"]
    return {"claims":len(claims),"root_count":len(roots),"realized_depth":max((depths[c] for c in roots),default=None),
        "max_depth":max(depths.values(),default=0),"depths":depths,"parents":parents,
        "parentless":sum(not p for p in parents.values()),"declared_witness_counts":redundant}


def replay_case(case,claims,origin,method,condition,driver=None,path=None,scope_prefix="structure_study_v1"):
    scope=f"{scope_prefix}/{case['case_id']}/{origin}/{condition}/{method}"
    store=GraphStore(scope=scope,driver=driver) if method in {"B2","M1"} else RelationalStore(path or ":memory:",scope=scope)
    start=time.perf_counter()
    try:
        generated,mapping=claim_records(case,claims,origin)
        before_display={"claims":claims,"explanation":" ".join(c["sentence"] for c in claims)}
        explanation=Record(record_id=case["case_id"]+"/explanation/v1",logical_id=case["case_id"]+"/explanation",
            record_type="explanation",dataset_id=case["dataset"],subject_id=case["subject"],session_id="session_1",
            event_start_seconds=min(t["interval"][0] for t in case["tests"].values()),event_end_seconds=max(t["interval"][1] for t in case["tests"].values()),
            ingested_at_seconds=case["knowledge_time"]+.002,source_ids=tuple(mapping.values()),metadata={"display":before_display,"origin":origin})
        store.put_many([Record.from_dict(e) for e in case["events"]]+generated+[explanation])
        before=reference(case,case["events"],case["knowledge_time"])
        revisions=updates(case,condition); change_time=revisions[0]["ingested_at_seconds"]
        tick=time.perf_counter(); store.put_many([Record.from_dict(e) for e in revisions]); insertion=time.perf_counter()-tick
        tick=time.perf_counter(); snapshot=store.snapshot(change_time); lookup=time.perf_counter()-tick
        changed_logicals={e["logical_id"] for e in revisions}
        predecessors=[r.record_id for r in snapshot.values() if r.logical_id in changed_logicals and r.version<2]
        tick=time.perf_counter()
        direct=set(store.dependents_many(predecessors,change_time,False))
        reached=set(store.dependents_many(predecessors,change_time,True))
        traversal=time.perf_counter()-tick
        scheduled=(reached if method in {"M1","B3"} else direct) if method!="B0" else set()
        tick=time.perf_counter(); reevaluated=runtime_support(claims,case,snapshot); evaluation=time.perf_counter()-tick
        states={c["claim_id"]:(reevaluated[c["claim_id"]] if mapping[c["claim_id"]] in scheduled else True) for c in claims}
        assessments={mapping[cid]:{"state":"supported" if states[cid] else "contradicted","value":float(states[cid])}
            for cid in states if mapping[cid] in scheduled}
        tick=time.perf_counter(); store.assess_many(assessments,change_time,revisions[0]["record_id"]); assessment_write=time.perf_counter()-tick
        after=reference(case,case["events"]+revisions,change_time)
        required={c["claim_id"] for c in claims if before[c["proposition"]] and not after[c["proposition"]]}
        D={cid for cid,rid in mapping.items() if rid in direct}
        missed={cid for cid in required if states[cid]}
        collateral={c["claim_id"] for c in claims if after[c["proposition"]] and not states[c["claim_id"]]}
        roots=[c for c in claims if c["proposition"]=="answer"]
        retained=[c for c in claims if states[c["claim_id"]]]
        after_display={"claims":retained,"explanation":" ".join(c["sentence"] for c in retained)}
        if len(retained)!=len(claims):
            store.put(replace(explanation,record_id=case["case_id"]+"/explanation/v2",version=2,supersedes_id=explanation.record_id,
                ingested_at_seconds=change_time+.001,source_ids=tuple(mapping[c["claim_id"]] for c in retained),
                metadata={"display":after_display,"origin":origin,"maintenance":"retain supported common-candidate claims"}))
        return {"case_id":case["case_id"],"episode_id":case["episode_id"],"dataset":case["dataset"],"subject":case["subject"],
            "intended_depth":case["intended_depth"],"regime":case["regime"],"origin":origin,"method":method,"condition":condition,"scope":scope,
            **structure(claims,case),"knowledge_time":change_time,"revisions":revisions,"required_change_ids":sorted(required),"direct_scheduled_ids":sorted(D),
            "scheduled_ids":sorted(cid for cid,rid in mapping.items() if rid in scheduled),"potential_affected_records":len(reached),
            "xi":len(required-D)/len(required) if required else None,"required_changes":len(required),"missed_changes":len(missed),
            "missed_ids":sorted(missed),"collateral_ids":sorted(collateral),"collateral":len(collateral),"states":states,
            "corrected":len(required-missed),"root_truth_after":after["answer"],"root_preserved":any(states[c["claim_id"]] for c in roots),
            "predicate_truth_after":after,"logical_hash":digest_object(states),
            "before_display":before_display,"after_display":after_display,"unresolved_claims":len(claims)-len(retained),
            "adequate_root_after":after["answer"] and any(states[c["claim_id"]] for c in roots),
            "replacement_generation":"not scheduled in this structural maintenance experiment",
            "theory_direct_prediction_agrees":missed==required-D if method in {"B1","B2"} else None,
            "timing_seconds":{"insertion":insertion,"snapshot":lookup,"both_reach_queries":traversal,"whole_program_evaluation":evaluation,"assessment_write":assessment_write,"cell":time.perf_counter()-start},
            "timing_note":"both direct and full queries measured for instrumentation; not production-only update latency"}
    finally: store.close()


def run(pilot=False,fixtures_only=False,pilot_version="pilot_v2"):
    from neo4j import GraphDatabase
    cases=read_json(ROOT/("pilot_cases.json" if pilot else "cases.json")); label=pilot_version+"_replay" if pilot else "replay"
    out=ROOT/label; out.mkdir(parents=True,exist_ok=True)
    with GraphDatabase.driver("bolt://127.0.0.1:7687",auth=None) as driver:
        for index,case in enumerate(cases):
            origins=[("fixture",fixture(case)["claims"])]
            candidate_path=ROOT/(pilot_version if pilot else "core")/"candidates"/(case["case_id"]+".json")
            if not fixtures_only:
                candidate=read_json(candidate_path); origins.append(("generated",candidate["accepted"]))
            for origin,claims in origins:
                path=out/(case["case_id"]+"-"+origin+".json")
                if path.exists(): continue
                prefix="structure_study_v1/"+pilot_version if pilot else "structure_study_v1"
                rows=[replay_case(case,claims,origin,m,c,driver,str(ROOT/"replay.sqlite"),prefix) for c in CONDITIONS for m in METHODS]
                for condition in CONDITIONS:
                    matched={r["method"]:r for r in rows if r["condition"]==condition}
                    assert matched["M1"]["logical_hash"]==matched["B3"]["logical_hash"]
                    assert matched["B1"]["logical_hash"]==matched["B2"]["logical_hash"]
                    assert matched["B1"]["theory_direct_prediction_agrees"] and matched["B2"]["theory_direct_prediction_agrees"]
                write_json(path,rows)
            print(f"Replay {index+1}/{len(cases)}",flush=True)
    write_json(out/"completion.json",{"cases":len(cases),"origins":1 if fixtures_only else 2,"cells":len(cases)*20*(1 if fixtures_only else 2),"finished_at":utc_now()})


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--pilot",action="store_true");p.add_argument("--fixtures-only",action="store_true");p.add_argument("--pilot-version",default="pilot_v2");a=p.parse_args();run(a.pilot,a.fixtures_only,a.pilot_version)
