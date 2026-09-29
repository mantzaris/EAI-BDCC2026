"""Task-defined structural reference truth, independent of candidate support flags.

This module never imports the runtime support evaluator. Formula definitions are
fixed before inference and evaluated against immutable numerical source events.
"""

def reference(case, events, knowledge_time):
    latest={}
    for event in events:
        if event["ingested_at_seconds"]>knowledge_time: continue
        previous=latest.get(event["logical_id"])
        if previous is None or (event["version"],event["ingested_at_seconds"],event["record_id"])>(previous["version"],previous["ingested_at_seconds"],previous["record_id"]):
            latest[event["logical_id"]]=event
    truths={}
    for name,test in case["tests"].items():
        event=latest.get(test["logical_id"])
        ok=event is not None and event["dataset_id"]==case["dataset"] and event["subject_id"]==case["subject"]
        ok=ok and event["unit"]==test["unit"] and event["quantity"]==test["quantity"]
        ok=ok and [event["event_start_seconds"],event["event_end_seconds"]]==test["interval"]
        ok=ok and event["evidence_state"]=="available" and event["value"] is not None
        if ok:
            difference=event["value"]-test["threshold"]
            ok=difference>=0 if test["operator"]=="ge" else difference<=0
        truths[name]=bool(ok)
    return {name:any(all(truths[token] for token in clause) for clause in clauses)
            for name,clauses in case["propositions"].items()}
