from dataclasses import asdict,replace
from copy import deepcopy
from temporal_evidence.evaluation.exact import score_claims,required_slots,score_persistent
from temporal_evidence.synthetic.fixtures import record
from temporal_evidence.schema import Query


def fixture():
    events=[record("a",2).to_dict()]
    query=asdict(Query("synthetic","V101","symbolic",0,10,10))
    claim={"claim_id":"c","claim_type":"numeric_observation","subject_id":"V101","quantity":"eda_median",
           "event_start_seconds":0,"event_end_seconds":10,"operator":"approximately_equal","value":2,
           "unit":"synthetic_unit","evidence_ids":["a"],"depends_on_claim_ids":[],"sentence":"EDA is 2 synthetic_unit."}
    return [claim],events,query


def test_evaluator_rejects_wrong_value_subject_time_and_prose():
    claims,events,query=fixture()
    assert score_claims(claims,events,query)[0]["valid"]
    for field,value in [("value",20),("subject_id","other"),("event_end_seconds",11),("sentence","EDA is 20 synthetic_unit.")]:
        changed=deepcopy(claims);changed[0][field]=value
        assert not score_claims(changed,events,query)[0]["valid"]


def test_evaluator_reconstructs_historical_and_current_snapshots():
    claims,events,query=fixture()
    revised={**events[0],"record_id":"a/v2","version":2,"supersedes_id":"a","value":4,"ingested_at_seconds":20}
    events.append(revised)
    assert score_claims(claims,events,query)[0]["valid"]
    now={**query,"knowledge_time":20}
    assert "superseded_reference" in score_claims(claims,events,now)[0]["reasons"]
    assert "numeric_or_interval" in score_claims(claims,events,now,remap_versions=True)[0]["reasons"]


def test_evaluator_rejects_cycle_and_allows_alternative_support():
    claims,events,query=fixture()
    claims[0]["depends_on_claim_ids"]=["c"]
    assert not score_claims(claims,events,query)[0]["valid"]
    claims[0]["depends_on_claim_ids"]=[]
    events.append({**events[0],"record_id":"b","logical_id":"b","value":None,"evidence_state":"invalidated"})
    claims[0]["evidence_ids"].append("b")
    assert score_claims(claims,events,query)[0]["valid"]


def test_persistent_correction_denominator_and_benign_retention():
    claims,events,query=fixture()
    events.append({**events[0],"record_id":"a/v2","version":2,"supersedes_id":"a","value":4,"ingested_at_seconds":20})
    output={"query":{**query,"knowledge_time":20},"persistent_before":{"old/claim/c":{
        "claim":claims[0],"state":"supported","created_at":10,"last_transition":None}}}
    counts,_=score_persistent(output,events)
    assert counts["correction_required"]==counts["residual_incorrect"]==1
    output["persistent_before"]["old/claim/c"].update(state="contradicted",last_transition={"flag_seconds":.1})
    counts,_=score_persistent(output,events)
    assert counts["corrected_by_5s"]==1
    events[-1]["value"]=2
    counts,_=score_persistent(output,events)
    assert counts["correction_required"]==0 and counts["collateral_withdrawn"]==1


def test_empty_outputs_do_not_fill_required_slots():
    _,events,query=fixture()
    slots=required_slots(events,query)
    assert len(slots)==2 and slots[0]["value"]==2 and slots[1]["value"] is None
