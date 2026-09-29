"""Independent event-log evaluator. Does not import runtime validation/replay.

Exact scores concern source faithfulness, not physiological truth. Lexical prose
checks are incomplete; the separately pinned neural audit is reported separately.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from copy import deepcopy
from pathlib import Path
import math
import re
from temporal_evidence.io import read_json,write_json


def visible_versions(events,query):
    visible={}
    newest={}
    for event in events:
        if event["ingested_at_seconds"]>query["knowledge_time"]:
            continue
        identifier=event["record_id"]
        if identifier in visible and visible[identifier]!=event:
            raise ValueError("Conflicting immutable event in evaluator input")
        visible[identifier]=event
        previous=newest.get(event["logical_id"])
        order=lambda item:(item["version"],item["ingested_at_seconds"],item["record_id"])
        if previous is None or order(event)>order(previous):
            newest[event["logical_id"]]=event
    return visible,newest


def agrees(actual,expected):
    if actual is None or expected is None:
        return False
    return math.isfinite(actual) and math.isfinite(expected) and abs(actual-expected)<=max(.000001,abs(expected)/100)


def in_scope(event,query):
    return all(event[key]==query[key] for key in ("dataset_id","subject_id","session_id"))


def interval(event):
    return event["event_start_seconds"],event["event_end_seconds"]


def source_value(event):
    return event.get("value") if event.get("evidence_state")=="available" else None


def score_claims(claims,events,query,remap_versions=False,check_prose=True):
    visible,newest=visible_versions(events,query)
    counts=Counter(claim["claim_id"] for claim in claims)
    by_id={claim["claim_id"]:claim for claim in claims}
    memo={}
    active=set()
    def evaluate(identifier):
        if identifier in memo:
            return memo[identifier]
        if identifier in active or identifier not in by_id:
            return {"valid":False,"reasons":["dependency"],"reference_count":0,"valid_reference_count":0}
        active.add(identifier)
        claim=by_id[identifier]
        reasons=[]
        references=[]
        reference_errors=[]
        if counts[identifier]!=1:
            reasons.append("duplicate_id")
        if claim["subject_id"]!=query["subject_id"]:
            reasons.append("wrong_subject")
        if interval(claim)!=interval(query):
            reasons.append("wrong_time")
        for reference in claim["evidence_ids"]:
            event=visible.get(reference)
            faults=[]
            if event is None:
                faults.append("reference_absent")
            else:
                latest=newest[event["logical_id"]]
                if remap_versions:
                    event=latest
                elif latest["record_id"]!=reference:
                    faults.append("superseded_reference")
                if not in_scope(event,query):
                    faults.append("reference_scope")
                if event["record_type"]!="feature":
                    faults.append("reference_kind")
                if (event["quantity"],event["unit"])!=(claim["quantity"],claim["unit"]):
                    faults.append("quantity_or_unit")
                references.append(event)
            reference_errors.append(faults)
            reasons.extend(faults)
        if any(not evaluate(parent)["valid"] for parent in claim["depends_on_claim_ids"]):
            reasons.append("dependency")
        kind=claim["claim_type"]
        op=claim["operator"]
        value=claim["value"]
        target=[e for e in references if interval(e)==interval(query) and source_value(e) is not None]
        prior=[e for e in references if interval(e)==(query["event_start_seconds"]-120,query["event_start_seconds"])
               and source_value(e) is not None]
        allowed={"numeric_observation":("approximately_equal",),"revision_effect":("revised","remains_supported"),
                 "trend":("difference","greater_than","less_than"),"comparison":("difference","greater_than","less_than"),
                 "missing_evidence":("missing",),"evidence_conflict":("disagrees",)}
        if op not in allowed.get(kind,()):
            reasons.append("operator")
        if op in ("greater_than","less_than") and (value is None or (value<=0 if op=="greater_than" else value>=0)):
            reasons.append("direction")
        if kind=="missing_evidence":
            available=[e for e in newest.values() if e["record_type"]=="feature" and in_scope(e,query)
                       and interval(e)==interval(query) and e["quantity"]==claim["quantity"] and source_value(e) is not None]
            if available or value is not None:
                reasons.append("false_missing")
        elif kind in ("numeric_observation","revision_effect"):
            if not any(agrees(value,e["value"]) for e in target):
                reasons.append("numeric_or_interval")
            if kind=="revision_effect" and not any(e.get("supersedes_id") for e in target):
                reasons.append("revision_not_visible")
        elif kind in ("trend","comparison"):
            if not target or not prior:
                reasons.append("comparison_operand")
            elif not agrees(value,target[0]["value"]-prior[0]["value"]):
                reasons.append("numeric_difference")
            if len(target)+len(prior)!=len(references):
                reasons.append("comparison_extra_operand")
        elif kind=="evidence_conflict":
            if len(target)<2 or agrees(target[0]["value"],target[1]["value"]):
                reasons.append("conflict_not_established")
        if check_prose:
            sentence=claim["sentence"]
            if re.search(r"\b(?:caus\w*|diagnos\w*|stress(?:ed)?|readiness|disease)\b",sentence,re.I):
                reasons.append("prose_interpretation")
            if value is not None:
                tokens=re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?",sentence)
                if not any(agrees(float(token),value) for token in tokens):
                    reasons.append("prose_number")
                if claim["unit"].casefold() not in sentence.casefold():
                    reasons.append("prose_unit")
            elif kind=="missing_evidence" and not re.search(r"missing|unavailable|absen|no\b|not\b|insufficient|unknown",sentence,re.I):
                reasons.append("prose_missing_discrepancy")
        valid=not reasons
        supported_references=0
        if valid:
            for event in references:
                if kind in ("numeric_observation","revision_effect"):
                    supported_references+=int(event in target and agrees(source_value(event),value))
                elif kind=="missing_evidence":
                    supported_references+=int(interval(event)==interval(query) and source_value(event) is None)
                else:
                    supported_references+=int(event in target or event in prior)
        item={"claim_id":identifier,"valid":valid,"reasons":sorted(set(reasons)),
              "reference_count":len(reference_errors),
              "valid_reference_count":supported_references}
        active.remove(identifier)
        memo[identifier]=item
        return item
    return [evaluate(claim["claim_id"]) for claim in claims]


def required_slots(events,query):
    _,newest=visible_versions(events,query)
    features=[e for e in newest.values() if e["record_type"]=="feature" and in_scope(e,query)]
    def get(quantity,bounds):
        values=[e for e in features if e["quantity"]==quantity and interval(e)==bounds]
        if len(values)>1:
            raise ValueError("Ambiguous benchmark reference")
        return values[0] if values else None
    target=get("eda_median",interval(query))
    slots=[{"slot":"target_eda","quantity":"eda_median","kind":"direct","value":source_value(target) if target else None}]
    if query["family"] in ("current_evidence","conflict_timing"):
        prior=get("eda_median",(query["event_start_seconds"]-120,query["event_start_seconds"]))
        value=target["value"]-prior["value"] if target and prior and source_value(target) is not None and source_value(prior) is not None else None
        slots.append({"slot":"eda_difference","quantity":"eda_median","kind":"difference","value":value})
    else:
        quantity="eda_missing_fraction" if query["family"]=="evidence_sufficiency" else "acceleration_magnitude_sd"
        event=get(quantity,interval(query))
        slots.append({"slot":quantity,"quantity":quantity,"kind":"direct","value":source_value(event) if event else None})
    return slots


def score_persistent(output,events):
    groups=defaultdict(list)
    for identifier,item in output.get("persistent_before",{}).items():
        groups[identifier.split("/claim/")[0]].append((identifier,item))
    counts={"correction_required":0,"corrected":0,"corrected_by_5s":0,"residual_incorrect":0,
            "unaffected":0,"collateral_withdrawn":0,"initially_incorrect":0}
    details=[]
    for group in groups.values():
        claims=[item["claim"] for _,item in group]
        before_query={**output["query"],"knowledge_time":group[0][1]["created_at"]}
        before=score_claims(claims,events,before_query,remap_versions=True)
        after=score_claims(claims,events,output["query"],remap_versions=True)
        for (identifier,item),old,new in zip(group,before,after):
            active=item["state"] in ("supported","unverified","pending")
            required=old["valid"] and not new["valid"]
            unaffected=old["valid"] and new["valid"]
            withdrawn=not active
            transition=item.get("last_transition") or {}
            counts["correction_required"]+=int(required)
            counts["corrected"]+=int(required and withdrawn)
            counts["corrected_by_5s"]+=int(required and withdrawn and transition.get("flag_seconds",float("inf"))<=5)
            counts["residual_incorrect"]+=int(required and active)
            counts["unaffected"]+=int(unaffected)
            counts["collateral_withdrawn"]+=int(unaffected and withdrawn)
            counts["initially_incorrect"]+=int(not old["valid"])
            details.append({"record_id":identifier,"required_change":required,"active":active,
                            "current_valid":new["valid"],"reasons":new["reasons"],"transition":transition})
    return counts,details


def score_case(output,episode):
    events=episode["variants"][output["case"]["variant"]]["events"]
    query=output["query"]
    answer=output.get("display") or {"claims":[],"explanation":"","answer_status":"insufficient_evidence"}
    claims=answer["claims"]
    scored=score_claims(claims,events,query)
    slots=required_slots(events,query)
    for slot in slots:
        kinds=("trend","comparison") if slot["kind"]=="difference" else ("numeric_observation","revision_effect")
        slot["supplied"]=slot["value"] is not None and any(result["valid"] and claim["quantity"]==slot["quantity"]
            and claim["claim_type"] in kinds and agrees(claim["value"],slot["value"]) for claim,result in zip(claims,scored))
    paragraph=answer["explanation"].strip()!=" ".join(claim["sentence"] for claim in claims).strip()
    persistent,persistent_details=score_persistent(output,events)
    answerable=sum(slot["value"] is not None for slot in slots)
    supplied=sum(slot["supplied"] for slot in slots)
    errors=sum(not claim["valid"] for claim in scored)
    initial=output["initial"]
    repair=output.get("repair")
    calls=[initial]+([repair] if repair else [])
    row={**output["case"],"claim_count":len(claims),"claim_errors":errors,"case_error":int(bool(errors or paragraph)),
         "reference_count":sum(r["reference_count"] for r in scored),"valid_reference_count":sum(r["valid_reference_count"] for r in scored),
         "required_slots":len(slots),"answerable_slots":answerable,"supplied_slots":supplied,
         "useful_eligible":int(answerable>0),"useful_complete":int(answerable>0 and supplied==answerable),
         "all_slots_answerable":int(answerable==len(slots)),"abstained":int(not claims),
         "partial":int(answer["answer_status"]=="partially_answered"),"failed":int(output["status"]=="failed"),
         "initial_parse_failure":int(bool(initial.get("error"))),"initial_truncation":int(initial.get("truncated",False)),
         "timeout_calls":sum("timeout" in call.get("error","").lower() for call in calls),"repair_calls":int(repair is not None),
         "input_tokens":sum(call.get("response",{}).get("usage",{}).get("prompt_tokens",0) for call in calls),
         "output_tokens":sum(call.get("response",{}).get("usage",{}).get("completion_tokens",0) for call in calls),
         "generation_seconds":output["seconds"],"end_to_end_seconds":output.get("end_to_end_seconds"),
         "database_update_seconds":output["database_update_seconds"],"retrieval_seconds":output["retrieval_seconds"],
         "paragraph_discrepancy":int(paragraph),**persistent}
    return {"metrics":row,"claims":scored,"required_slots":slots,"persistent":persistent_details}


def evaluate(run_id="minimum_v1"):
    directory=Path(f"artifacts/runs/{run_id}/cases")
    paths=sorted(directory.glob("*.json"))
    if not paths:
        raise FileNotFoundError(directory)
    episodes={}
    metrics=[]
    for path in paths:
        output=read_json(path)
        identifier=output["case"]["episode_id"]
        if identifier not in episodes:
            archived=Path(f"artifacts/runs/{run_id}/input_episodes/{identifier}.json")
            episodes[identifier]=read_json(archived if archived.exists() else f"artifacts/prepared/{identifier}.json")
        result=score_case(output,episodes[identifier])
        metrics.append(result["metrics"])
        write_json(f"artifacts/evaluation/{run_id}/cases/{path.name}",result)
    write_json(f"artifacts/evaluation/{run_id}/metrics.json",metrics)
    return {"run_id":run_id,"evaluated_cases":len(metrics),"prose_scope":"exact lexical checks plus separate automated audit"}
