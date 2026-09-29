"""Bounded positive semantic programs for structure_study_v1.

Model edges are only the model's explicit witness tokens. Exact fixtures are a
separate compiler output. No missing model parent or alternative is inserted.
"""
from copy import deepcopy
from itertools import product
from pathlib import Path
import re
from pydantic import BaseModel, ConfigDict, Field
from temporal_evidence.io import read_json, write_json, digest_file, utc_now

class ProgramClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    proposition: str
    value: bool
    witnesses: list[list[str]] = Field(min_length=1, max_length=4)
    sentence: str

class ProgramAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ProgramClaim] = Field(max_length=16)
    explanation: str


def natural(x): return tuple(int(t) if t.isdigit() else t for t in re.split(r"(\d+)", x))


def minimal(clauses):
    sets = {frozenset(c) for c in clauses}
    return sorted([sorted(s) for s in sets if not any(t < s for t in sets)], key=lambda s:(len(s),s))


def formula_and(parts):
    return minimal([set().union(*[set(p) for p in group]) for group in product(*parts)])


def expand(claims, atoms):
    formulas, errors = {}, {}
    for c in claims:
        cid=c["claim_id"]; problems=[]; clauses=[]
        if cid in formulas or cid in atoms: problems.append("duplicate_id")
        for witness in c["witnesses"]:
            terms=[]
            if not witness: problems.append("empty_witness")
            for token in witness:
                if token in atoms: terms.append([[token]])
                elif token in formulas: terms.append(formulas[token])
                else: problems.append("unknown_or_forward_reference")
            if len(terms)==len(witness) and terms: clauses += formula_and(terms)
        formulas[cid]=minimal(clauses); errors[cid]=problems
    return formulas,errors


def validate(candidate, case):
    claims=(candidate or {}).get("claims",[]); formulas,errors=expand(claims,case["tests"])
    accepted=[]; decisions=[]; accepted_ids=set()
    for c in claims:
        cid=c["claim_id"]; reasons=list(errors[cid]); gold=case["propositions"].get(c["proposition"])
        if gold is None: reasons.append("unknown_proposition")
        if not c["value"]: reasons.append("initial_value_false")
        if not formulas[cid]: reasons.append("no_witness")
        if gold is not None and any(not any(set(g)<=set(w) for g in gold) for w in formulas[cid]): reasons.append("witness_does_not_entail_proposition")
        parents=[token for w in c["witnesses"] for token in w if token not in case["tests"]]
        if any(p not in accepted_ids for p in parents): reasons.append("unaccepted_parent")
        if not reasons: accepted.append(c); accepted_ids.add(cid)
        decisions.append({"claim_id":cid,"accepted":not reasons,"reasons":sorted(set(reasons)),
            "expanded_witnesses":formulas[cid],"complete_witness_family":gold is not None and minimal(gold)==formulas[cid]})
    return accepted,decisions


def fixture(case):
    claims=[]; depth=case["intended_depth"]
    for route in case["routes"]:
        parent=None
        prefixes={1:[],2:[4],3:[2,4],4:[1,2,4]}[depth]
        consumed=0
        for count in prefixes:
            cid=f"{route}_{count}"; prop=f"{route}_first_{count}"
            witnesses=[[parent] if parent else []]
            witnesses[0] += [f"{route}{i}" for i in range(consumed+1,count+1)]
            claims.append({"claim_id":cid,"proposition":prop,"value":True,"witnesses":witnesses,
                "sentence":f"Window {route} satisfies its first {count} specified numerical tests."})
            parent=cid; consumed=count
    root=[[f"{r}_4"] for r in case["routes"]] if depth>1 else [[f"{r}{i}" for i in range(1,5)] for r in case["routes"]]
    claims.append({"claim_id":"answer","proposition":"answer","value":True,"witnesses":root,
        "sentence":"At least one eligible window satisfies all four specified numerical tests."})
    return {"claims":claims,"explanation":" ".join(c["sentence"] for c in claims),"origin":"exact_compiler_fixture"}


def build_case(episode, depth, regime):
    t=episode["end"]+1
    # Independently select a clean visible version; no runtime flags.
    latest={}
    for e in episode["variants"]["clean"]["events"]:
        if e["ingested_at_seconds"]<=t and (e["logical_id"] not in latest or e["version"]>latest[e["logical_id"]]["version"]): latest[e["logical_id"]]=e
    quantities=("eda_median","eda_iqr","acceleration_magnitude_sd","eda_missing_fraction")
    bounds={"A":(episode["start"],episode["end"]),"B":(episode["start"]-120,episode["start"])}
    chosen={}
    for route,window in bounds.items():
        for i,q in enumerate(quantities,1):
            es=[e for e in latest.values() if e["record_type"]=="feature" and e["quantity"]==q and
                (e["event_start_seconds"],e["event_end_seconds"])==window]
            assert len(es)==1 and es[0]["value"] is not None and es[0]["evidence_state"]=="available"
            chosen[f"{route}{i}"]=es[0]
    tests={}; routes=["A"] if regime=="single" else ["A","B"]
    for i,q in enumerate(quantities,1):
        values=[chosen[f"{r}{i}"]["value"] for r in ("A","B")]
        margin=max(1e-5,.1*abs(min(values))) if i<4 else .05
        threshold=min(values)-margin if i<4 else max(values)+margin
        for r in routes:
            e=chosen[f"{r}{i}"]
            tests[f"{r}{i}"]={"source_id":e["record_id"],"logical_id":e["logical_id"],"quantity":q,
                "unit":e["unit"],"operator":"ge" if i<4 else "le","threshold":threshold,"margin":margin,
                "initial_value":e["value"],"interval":list(bounds[r]),"observation_ids":list(e["source_ids"])}
    propositions={f"{r}_first_{n}":[[f"{r}{i}" for i in range(1,n+1)]] for r in routes for n in (1,2,4)}
    propositions["answer"]=[[f"{r}{i}" for i in range(1,5)] for r in routes]
    irrelevant=next(e for e in latest.values() if e["record_type"]=="feature" and e["quantity"]=="cardiac_missing_fraction" and (e["event_start_seconds"],e["event_end_seconds"])==bounds["A"])
    required={test["source_id"] for test in tests.values()}|{irrelevant["record_id"]}
    byid={e["record_id"]:e for e in latest.values()}
    agenda=list(required)
    while agenda:
        for sid in byid[agenda.pop()]["source_ids"]:
            if sid not in required and sid in byid: required.add(sid); agenda.append(sid)
    events=[deepcopy(byid[r]) for r in sorted(required)]
    if regime=="alternative":
        assert set(s for k,v in tests.items() if k[0]=="A" for s in v["observation_ids"]).isdisjoint(s for k,v in tests.items() if k[0]=="B" for s in v["observation_ids"])
        assert bounds["B"][1]<=bounds["A"][0]
    return {"case_id":f"{episode['episode_id']}-d{depth}-{regime}","episode_id":episode["episode_id"],
        "dataset":episode["dataset"],"subject":episode["subject"],"intended_depth":depth,"regime":regime,
        "routes":routes,"tests":tests,"propositions":propositions,"events":events,"knowledge_time":t,
        "irrelevant_id":irrelevant["record_id"],"source_episode_sha256":digest_file(f"artifacts/prepared/{episode['episode_id']}.json")}


def updates(case, condition):
    byid={e["record_id"]:e for e in case["events"]}; edits=[]
    tokens=["A1"]
    if condition=="necessary": tokens=[f"{r}1" for r in case["routes"]]
    if condition=="irrelevant": tokens=[None]
    for index,token in enumerate(tokens):
        test=case["tests"].get(token); old=byid[test["source_id"] if test else case["irrelevant_id"]]
        new=deepcopy(old); new.update(record_id=old["logical_id"]+f"/structure-{condition}-v2",version=2,
            supersedes_id=old["record_id"],ingested_at_seconds=case["knowledge_time"]+30)
        new["value"]=(old["value"]+test["margin"]*.01 if condition=="benign" else test["threshold"]-test["margin"]) if test else old["value"]+.01
        new["metadata"]={**old["metadata"],"structure_study_condition":condition,"controlled_numeric_revision":True}
        edits.append(new)
    return edits


def runtime_support(claims, case, records):
    """Declared witness semantics; consumes records, never prior assessment flags."""
    latest={}
    for r in records.values():
        key=r.logical_id
        if key not in latest or (r.version,r.ingested_at_seconds)>(latest[key].version,latest[key].ingested_at_seconds): latest[key]=r
    atoms={}
    for token,test in case["tests"].items():
        r=latest.get(test["logical_id"])
        valid=r is not None and r.evidence_state=="available" and r.value is not None and r.subject_id==case["subject"] and r.dataset_id==case["dataset"] and r.unit==test["unit"]
        valid=valid and r.quantity==test["quantity"] and [r.event_start_seconds,r.event_end_seconds]==test["interval"] and r.session_id=="session_1"
        atoms[token]=bool(valid and (r.value>=test["threshold"] if test["operator"]=="ge" else r.value<=test["threshold"]))
    values={}
    for c in claims:
        values[c["claim_id"]]=any(bool(w) and all(atoms.get(token,values.get(token,False)) for token in w) for w in c["witnesses"])
    return values


def select():
    episodes=[read_json(p) for p in sorted(Path("artifacts/prepared").glob("*.json"))]
    output=Path("artifacts/runs/structure_study_v1"); output.mkdir(parents=True,exist_ok=True)
    selected=[]; pilot=[]
    for source in ("synthetic","wesad","ppg_dalia"):
        eligible=[e for e in episodes if e["dataset"]==source and e["split"]=="test"]
        subjects=sorted({e["subject"] for e in eligible},key=natural)[:5]
        base=sorted([e for e in eligible if e["subject"] in subjects],key=lambda e:natural(e["episode_id"]))
        assert len(base)==10
        for e in base:
            for d in (1,2,3,4):
                for regime in ("single","alternative"): selected.append(build_case(e,d,regime))
        dev=sorted([e for e in episodes if e["dataset"]==source and e["split"]=="development"],key=lambda e:natural(e["episode_id"]))[0]
        for d in (1,4):
            for regime in ("single","alternative"): pilot.append(build_case(dev,d,regime))
    for name, cases in (("cases",selected),("pilot_cases",pilot)):
        path=output/f"{name}.json"
        if path.exists(): assert read_json(path)==cases, "prospective selection is immutable"
        else: write_json(path,cases)
    manifest={"created_at":utc_now(),"rule":"first five naturally sorted existing held-out subjects, both episodes per source",
        "core_cases":len(selected),"pilot_cases":len(pilot),"maximum_core_calls":480,"maximum_pilot_calls":24,
        "cases_sha256":digest_file(output/"cases.json"),"pilot_sha256":digest_file(output/"pilot_cases.json"),
        "protocol_sha256":digest_file("docs/semantic_analysis_protocol.md"),"cohort":"reused existing participants"}
    if not (output/"selection.json").exists(): write_json(output/"selection.json",manifest)
    return manifest


if __name__ == "__main__": print(select())
