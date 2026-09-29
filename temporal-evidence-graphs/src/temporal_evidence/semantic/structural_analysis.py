"""Independent semantic-program audit and analysis of completed common replays."""
from collections import Counter,defaultdict
from itertools import product
from pathlib import Path
import re
import numpy as np
from temporal_evidence.io import read_json,write_json,digest_file
from temporal_evidence.semantic.statistics import cluster_ratio,csv_rows
from temporal_evidence.structure.oracle import reference
from temporal_evidence.semantic.aliases import canonical_case

RUN=Path("artifacts/runs/structure_study_v1")
OUT=Path("artifacts/analysis/semantic_analysis_v1")

def audit_program(claims,case):
    """Truth-table oracle, independent of the runtime's DNF expansion/checker.

    All 2^4 or 2^8 assignments are enumerated. Equivalent proof syntax is accepted;
    no unique gold graph is imposed. Actual proposition truth comes from records.
    """
    case=canonical_case(case)
    actual=reference(case,case["events"],case["knowledge_time"])
    atoms=sorted(case["tests"]);known=set(atoms);syntax={};results=[]
    for c in claims:
        cid=c["claim_id"];tokens=[t for w in c["witnesses"] for t in w]
        ok=cid not in known and bool(c["witnesses"]) and all(w for w in c["witnesses"])
        ok=ok and all(t in known and syntax.get(t,True) for t in tokens)
        ok=ok and c["proposition"] in actual and c["value"]==actual.get(c["proposition"])
        syntax[cid]=bool(ok);known.add(cid)
        results.append({"claim_id":cid,"proposition":c["proposition"],"grounded":c["proposition"] in actual and c["value"]==actual[c["proposition"]],
            "sound_witnesses":[bool(ok and c["proposition"] in actual) for w in c["witnesses"]],"complete_family":bool(ok and c["proposition"] in actual),
            "sentence":c["sentence"]})
    for assignment in product((False,True),repeat=len(atoms)):
        assignment_values=dict(zip(atoms,assignment));values=dict(assignment_values)
        for c,result in zip(claims,results):
            ws=[bool(w) and all(values.get(t,False) for t in w) for w in c["witnesses"]]
            actual_formula=any(all(assignment_values.get(t,False) for t in clause) for clause in case["propositions"].get(c["proposition"],[]))
            for i,wtrue in enumerate(ws):
                if wtrue and not actual_formula:result["sound_witnesses"][i]=False
            if any(ws)!=actual_formula:result["complete_family"]=False
            values[c["claim_id"]]=any(ws)
    for c,r in zip(claims,results):
        allowed=[1.,2.,3.,4.]
        test_names={t for clause in case["propositions"].get(c["proposition"],[]) for t in clause}
        for token in test_names:
            t=case["tests"][token];allowed += [t["initial_value"],t["threshold"],*t["interval"]]
            if t["unit"]=="fraction" and re.search(r"%|percent",c["sentence"],re.I):allowed += [100*t["initial_value"],100*t["threshold"]]
        # A native unit such as 1/64g is not an extra numerical assertion.
        prose=re.sub(r"1\s*/\s*64\s*g\b"," ",c["sentence"],flags=re.I)
        numbers=[float(x) for x in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?",prose)]
        unmatched=[n for n in numbers if not any(abs(n-v)<=max(1e-6,.01*abs(v)) for v in allowed)]
        r["prose_audit"]={"unmatched_numbers":unmatched,"interpretation_term":bool(re.search(r"\b(?:diagnos\w*|stress|disease|caus\w*)\b",c["sentence"],re.I)),
            "scope":"limited literal audit; additional prose interpretations are not certified"}
    return results

def analyze():
    complete=read_json(RUN/"completed.json");assert complete["core"]["cases"]==240 and complete["replay"]["cells"]==9600
    frozen=read_json(RUN/"core/frozen.json")
    for path,expected in frozen["sources"].items():assert digest_file(path)==expected,(path,"extension source changed after freeze")
    cases=read_json(RUN/"cases.json");byid={c["case_id"]:c for c in cases}
    assert digest_file(RUN/"cases.json")==frozen["cases_sha256"]
    replay=[];full_rows=[]
    for path in sorted((RUN/"replay").glob("*.json")):
        if path.name=="completion.json":continue
        full_rows+=read_json(path)
    assert len(full_rows)==9600
    for row in full_rows:
        replay.append({k:v for k,v in row.items() if k not in {"before_display","after_display","revisions","predicate_truth_after","states"}})
    generated=[];stage_rows=[];audits=[];proposed_topology=[];rejection_reasons=Counter()
    for case in cases:
        output=read_json(RUN/"core/candidates"/(case["case_id"]+".json"))
        for d in output["decisions"]:rejection_reasons.update(d["reasons"])
        for stage,claims in (("proposal",(output.get("raw_candidate") or {}).get("claims",[])),
                ("final_proposal",(output.get("final_candidate") or {}).get("claims",[])),("accepted_displayed",output["accepted"])):
            scores=audit_program(claims,case); roots=[r for r in scores if r["proposition"]=="answer"]
            # Report raw topology even when a proposal fails admission. Unknown
            # references/cycles are undefined depth, never silently repaired.
            depths={};bad=set();atoms=set(case["tests"])
            for c in claims:
                tokens={t for w in c["witnesses"] for t in w}
                if c["claim_id"] in depths or c["claim_id"] in atoms or any(t not in atoms and (t not in depths or depths[t] is None) for t in tokens):
                    depths[c["claim_id"]]=None;bad.add(c["claim_id"])
                else:depths[c["claim_id"]]=max((1 if t in atoms else 1+depths[t] for t in tokens),default=0)
            ds=[depths[c["claim_id"]] for c in claims if c["proposition"]=="answer"]
            proposed_topology.append({"case_id":case["case_id"],"dataset":case["dataset"],"stage":stage,"intended_depth":case["intended_depth"],
                "realized_root_depth":max(ds) if ds and all(d is not None for d in ds) else None,"undefined_references_or_ids":sorted(bad)})
            valid_root=any(r["grounded"] and r["sound_witnesses"] and all(r["sound_witnesses"]) for r in roots)
            if stage=="accepted_displayed":
                assert all(r["grounded"] and all(r["sound_witnesses"]) for r in scores),case["case_id"]
                assert valid_root==output["adequate_answer"]
            audits.append({"case_id":case["case_id"],"stage":stage,"claims":scores})
            stage_rows.append({"case_id":case["case_id"],"dataset":case["dataset"],"subject":case["subject"],"episode_id":case["episode_id"],
                "intended_depth":case["intended_depth"],"regime":case["regime"],"stage":stage,"claims":len(claims),
                "grounded":sum(r["grounded"] for r in scores),"witnesses":sum(len(r["sound_witnesses"]) for r in scores),
                "sound_witnesses":sum(sum(r["sound_witnesses"]) for r in scores),"complete_families":sum(r["complete_family"] for r in scores),
                "required":1,"root_grounded":int(any(r["grounded"] for r in roots)),"root_with_admissible_witness":int(valid_root),
                "prose_flagged":sum(bool(r["prose_audit"]["unmatched_numbers"]) or r["prose_audit"]["interpretation_term"] for r in scores)})
        r=next(r for r in replay if r["case_id"]==case["case_id"] and r["origin"]=="generated" and r["method"]=="M1" and r["condition"]=="necessary")
        generated.append({k:r[k] for k in ("case_id","dataset","subject","episode_id","intended_depth","regime","claims","root_count","realized_depth","max_depth","parentless","declared_witness_counts")})
    grouped=defaultdict(list)
    for r in replay:grouped[(r["origin"],r["method"],r["condition"],r["intended_depth"],r["regime"])].append(r)
    summaries=[]
    for key,rs in sorted(grouped.items()):
        summaries.append({**dict(zip(("origin","method","condition","intended_depth","regime"),key)),"cases":len(rs),
            "required_changes":sum(r["required_changes"] for r in rs),"missed_changes":sum(r["missed_changes"] for r in rs),
            "collateral":sum(r["collateral"] for r in rs),"nonzero_exposure":sum(r["xi"] is not None and r["xi"]>0 for r in rs),
            "eligible_exposure":sum(r["xi"] is not None for r in rs),"correction":cluster_ratio(rs,"corrected","required_changes")})
    stages=defaultdict(list)
    for r in stage_rows:stages[(r["dataset"],r["stage"])].append(r)
    stage_summary=[{"dataset":s,"stage":stage,"cases":len(rs),"claims":sum(r["claims"] for r in rs),
        "grounding":cluster_ratio(rs,"grounded","claims"),"witness_precision":cluster_ratio(rs,"sound_witnesses","witnesses"),
        "complete_family":cluster_ratio(rs,"complete_families","claims"),"root_recall":cluster_ratio(rs,"root_grounded","required"),
        "traceable_root_recall":cluster_ratio(rs,"root_with_admissible_witness","required"),"prose_flagged":sum(r["prose_flagged"] for r in rs)} for (s,stage),rs in sorted(stages.items())]
    index={(r["case_id"],r["origin"],r["method"],r["condition"]):r for r in replay}
    parity=0;direct_agreement=0;eligible=0;same_size_different_gap=0;different_gap_pairs=0
    for case in cases:
        for origin in ("fixture","generated"):
            for condition in ("necessary","route_loss","benign","irrelevant"):
                m1=index[(case["case_id"],origin,"M1",condition)];b3=index[(case["case_id"],origin,"B3",condition)]
                b1=index[(case["case_id"],origin,"B1",condition)];b2=index[(case["case_id"],origin,"B2",condition)]
                assert m1["logical_hash"]==b3["logical_hash"] and b1["logical_hash"]==b2["logical_hash"]
                parity+=1
                if b2["xi"] is not None:
                    eligible+=1;direct_agreement+=int(b2["missed_changes"]==len(set(b2["required_change_ids"])-set(b2["direct_scheduled_ids"])))
        for condition in ("necessary","route_loss"):
            f=index[(case["case_id"],"fixture","B2",condition)];g=index[(case["case_id"],"generated","B2",condition)]
            if f["xi"] is not None and g["xi"] is not None and f["xi"]!=g["xi"]:
                different_gap_pairs+=1
                if f["claims"]==g["claims"]:same_size_different_gap+=1
    result={"completed":complete,"generated_cases":generated,"stratified_replay":summaries,"semantic_stages":stage_summary,
        "database_parity_groups":parity,"eligible_direct_prediction_groups":eligible,"direct_prediction_agreement":direct_agreement,
        "paired_different_exposure":different_gap_pairs,"same_record_count_different_exposure":same_size_different_gap,
        "realized_root_depth_counts":dict(Counter(str(r["realized_depth"]) for r in generated)),
        "raw_root_depth_counts":dict(Counter(str(r["realized_root_depth"]) for r in proposed_topology if r["stage"]=="proposal")),
        "admission_rejection_reasons":dict(rejection_reasons),
        "semantic_normalization":"Primitive names explicitly defined in tests are grounded independently even when omitted from the frozen runtime proposition table.",
        "fixture_compiler_note":"known programs separate from generated graph; model links never inserted",
        "size_comparison":"same base events, same admitted claim count, and one initial explanation imply equal baseline stored Record count; dependency edges may differ"}
    write_json(OUT/"structural_summary.json",result);write_json(OUT/"structural_replay_metrics.json",replay)
    csv_rows(OUT/"structural_replay_metrics.csv",[{k:v for k,v in r.items() if not isinstance(v,(list,dict))} for r in replay])
    write_json(OUT/"structural_semantic_metrics.json",stage_rows);csv_rows(OUT/"structural_semantic_metrics.csv",stage_rows)
    write_json(OUT/"structural_program_audit.json",audits)
    write_json(OUT/"structural_proposed_topology.json",proposed_topology)
    print({k:v for k,v in result.items() if k not in {"generated_cases","stratified_replay","semantic_stages"}})

if __name__=="__main__":analyze()
