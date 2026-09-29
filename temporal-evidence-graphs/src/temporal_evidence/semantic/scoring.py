"""Independent bounded proposition oracle: only immutable events and task scope.

No imports from validation, replay, original evaluation, or database assessments.
Proposition truth and quality of the emitted witness are deliberately separate.
"""
from itertools import product
import math
import re


def interval(x): return (x["event_start_seconds"], x["event_end_seconds"])


def close(a, b):
    return a is not None and b is not None and math.isfinite(a) and math.isfinite(b) and abs(a-b) <= max(1e-6, .01*abs(b))


def snapshot(events, time):
    visible, latest = {}, {}
    for e in events:
        if e["ingested_at_seconds"] > time: continue
        if e["record_id"] in visible and visible[e["record_id"]] != e: raise ValueError("immutable conflict")
        visible[e["record_id"]] = e
        key = e["logical_id"]
        rank = lambda r: (r["version"], r["ingested_at_seconds"], r["record_id"])
        if key not in latest or rank(e) > rank(latest[key]): latest[key] = e
    return visible, latest


def normalized_unit(unit):
    # Only documented notation aliases; never equate native acceleration scales.
    return {"µS": "uS", "μS": "uS"}.get(unit, unit)


def canonical(claim, query, witness, records, reference_value=None):
    op = claim["operator"]
    if op in {"approximately_equal", "revised", "remains_supported"}: op = "value"
    if op in {"greater_than", "less_than"}: op = "difference"
    versions = sorted({(records[i]["logical_id"], records[i]["version"]) for i in witness if i in records})
    return [query["dataset_id"], claim["subject_id"], query["session_id"], *interval(claim),
            claim["quantity"], op, reference_value if reference_value is not None else claim.get("value"),
            normalized_unit(claim["unit"]), claim.get("temporal_mode", "current_at_knowledge_time"), versions]


def proposition(claim, events, query, remap_citations=False):
    time = query["knowledge_time"]
    if claim.get("temporal_mode") == "historical":
        time = claim.get("as_of_knowledge_time", time)
        if time > query["knowledge_time"]: return {"grounded": False, "reasons": ["future_historical_scope"], "witnesses": [], "witness_valid": False}
    visible, latest = snapshot(events, time)
    def scoped(e):
        return e["record_type"] == "feature" and all(e[k] == query[k] for k in ("dataset_id", "subject_id", "session_id"))
    features = [e for e in latest.values() if scoped(e)]
    def matching(bounds):
        return [e for e in features if interval(e) == bounds and e["quantity"] == claim["quantity"]
                and normalized_unit(e["unit"]) == normalized_unit(claim["unit"])
                and e["evidence_state"] == "available" and e["value"] is not None]
    bounds = interval(claim); kind = claim["claim_type"]; op = claim["operator"]; value = claim.get("value")
    reasons, witnesses, refs = [], [], []
    reference_value = None
    if claim["subject_id"] != query["subject_id"]: reasons.append("wrong_subject")
    if bounds[0] < query["event_start_seconds"]-120 or bounds[1] > query["event_end_seconds"] or bounds[1] < bounds[0]:
        reasons.append("outside_evidence_scope")
    target = matching(bounds)
    if kind in {"numeric_observation", "revision_effect"}:
        if op not in ({"approximately_equal"} if kind == "numeric_observation" else {"revised", "remains_supported"}): reasons.append("operator")
        for e in target:
            if close(value, e["value"]) and (kind != "revision_effect" or e.get("supersedes_id")):
                witnesses.append([e["record_id"]]); reference_value = e["value"]
    elif kind in {"trend", "comparison"}:
        if op not in {"difference", "greater_than", "less_than"}: reasons.append("operator")
        prior = matching((bounds[0]-120, bounds[0]))
        for a,b in product(target,prior):
            delta = a["value"]-b["value"]
            if close(value,delta) and (op != "greater_than" or delta > 0) and (op != "less_than" or delta < 0):
                witnesses.append([a["record_id"], b["record_id"]]); reference_value = delta
    elif kind == "missing_evidence":
        # Closed producer/task universe: assertion is about available published
        # features in this recording log, never absence in the external world.
        expected = {e["quantity"] for e in events if e["record_type"] == "feature"}
        available = [e for e in features if interval(e)==bounds and e["quantity"]==claim["quantity"]
                     and e["evidence_state"]=="available" and e["value"] is not None]
        if op == "missing" and value is None and claim["quantity"] in expected and not available:
            witnesses = [[f"availability:{query['dataset_id']}:{query['subject_id']}:{bounds}:{claim['quantity']}:{time}"]]
        else: reasons.append("absence_not_established")
    elif kind == "evidence_conflict":
        if op != "disagrees": reasons.append("operator")
        witnesses = [[a["record_id"], b["record_id"]] for a,b in product(target,target)
                     if a["logical_id"] < b["logical_id"] and not close(a["value"],b["value"])]
    else: reasons.append("unadjudicated_claim_type")
    if not witnesses: reasons.append("no_admissible_numeric_witness")
    citation_errors = []
    for rid in claim.get("evidence_ids", []):
        e = visible.get(rid)
        if e is None: citation_errors.append("unknown_reference"); continue
        latest_e = latest[e["logical_id"]]
        if remap_citations: e = latest_e
        elif e["record_id"] != latest_e["record_id"]: citation_errors.append("obsolete_reference")
        if not scoped(e): citation_errors.append("reference_scope")
        refs.append(e["record_id"])
    witness_valid = bool(witnesses) and not citation_errors and (
        kind == "missing_evidence" or any(set(w) <= set(refs) for w in witnesses))
    if not witness_valid: citation_errors.append("declared_witness_incomplete")
    audit = []
    sentence = claim.get("sentence", "")
    if value is not None:
        nums = [float(n) for n in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", sentence)]
        if not any(close(n,value) for n in nums): audit.append("sentence_number")
        if claim["unit"].casefold() not in sentence.casefold(): audit.append("sentence_unit")
    if re.search(r"\b(?:caus\w*|diagnos\w*|stress(?:ed)?|readiness|disease)\b", sentence, re.I): audit.append("extra_interpretation")
    if bounds != interval(query) and re.search(r"\btarget\b|\bcurrent window\b", sentence, re.I): audit.append("background_label_conflict")
    return {"claim_id": claim["claim_id"], "grounded": not reasons, "reasons": sorted(set(reasons)),
        "witnesses": witnesses, "witness_valid": witness_valid and not reasons, "citation_errors": sorted(set(citation_errors)),
        "canonical": canonical(claim,query,witnesses[0] if witnesses else [],visible,reference_value),
        "background": bounds != interval(query), "raw_sentence": sentence, "prose_audit": audit,
        "declared_parents": claim.get("depends_on_claim_ids", []), "prose_scope": "structured propositions plus limited discrepancy audit"}


def requirements(events, query):
    _, current = snapshot(events, query["knowledge_time"])
    candidates = [e for e in current.values() if e["record_type"]=="feature" and
                  all(e[k]==query[k] for k in ("dataset_id", "subject_id", "session_id"))]
    def one(quantity,bounds):
        es = [e for e in candidates if e["quantity"]==quantity and interval(e)==bounds]
        if len(es)>1: raise ValueError("ambiguous task requirement")
        return es[0] if es and es[0]["evidence_state"]=="available" and es[0]["value"] is not None else None
    target=one("eda_median",interval(query)); tasks=[("target_eda","eda_median","value",target,None)]
    if query["family"] in {"current_evidence", "conflict_timing"}:
        tasks.append(("eda_difference","eda_median","difference",target,one("eda_median",(query["event_start_seconds"]-120,query["event_start_seconds"]))))
    else:
        quantity = "eda_missing_fraction" if query["family"]=="evidence_sufficiency" else "acceleration_magnitude_sd"
        tasks.append((quantity,quantity,"value",one(quantity,interval(query)),None))
    result=[]
    for name,quantity,operation,a,b in tasks:
        value = (a["value"]-b["value"] if a and b else None) if operation=="difference" else (a["value"] if a else None)
        result.append({"name":name,"quantity":quantity,"operation":operation,"value":value,
            "interval":list(interval(query)), "unit":a["unit"] if a else None,
            "witnesses": [[a["record_id"],b["record_id"]] if b else [a["record_id"]]] if value is not None else []})
    return result


def score(claims, events, query, remap_citations=False):
    decisions=[proposition(c,events,query,remap_citations) for c in claims]
    reqs=requirements(events,query)
    for r in reqs:
        r["matched"] = r["value"] is not None and any(d["grounded"] and c["quantity"]==r["quantity"]
            and list(interval(c))==r["interval"] and close(c.get("value"),r["value"])
            and ((c["claim_type"] in {"comparison","trend"}) == (r["operation"]=="difference"))
            and c["claim_type"] in {"numeric_observation","revision_effect","comparison","trend"}
            for c,d in zip(claims,decisions))
    emitted=len(decisions); grounded=sum(d["grounded"] for d in decisions)
    answerable=sum(r["value"] is not None for r in reqs); matched=sum(r["matched"] for r in reqs)
    precision=grounded/emitted if emitted else None; recall=matched/answerable if answerable else None
    summary = None if recall is None else (2*precision*recall/(precision+recall) if precision and recall else 0.)
    return {"emitted":emitted,"grounded":grounded,"answerable":answerable,"matched":matched,
        "precision":precision,"recall":recall,"harmonic":summary,"empty":not claims,
        "witness_valid":sum(d["witness_valid"] for d in decisions),"prose_flagged":sum(bool(d["prose_audit"]) for d in decisions),
        "claims":decisions,"requirements":reqs}
