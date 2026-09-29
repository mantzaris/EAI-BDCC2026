import json
from temporal_evidence.analysis.systems import completion_adequacy


def example(completion_index):
    feature = {"record_id":"a/v11","subject_id":"V101","event_start_seconds":0,"event_end_seconds":10,
               "ingested_at_seconds":100.5,"quantity":"eda_median","value":4.,"unit":"synthetic_unit",
               "evidence_state":"available","version":11,"supersedes_id":"a/v10"}
    baseline = {**feature,"record_id":"b","event_start_seconds":-120,"event_end_seconds":0,
                "ingested_at_seconds":10,"value":1.,"version":1,"supersedes_id":None}
    payload = {"subject_id":"V101","target_interval":[0,10],"evidence":[feature,baseline]}
    claim = {"claim_id":"target","claim_type":"numeric_observation","subject_id":"V101","quantity":"eda_median",
             "event_start_seconds":0,"event_end_seconds":10,"operator":"approximately_equal","value":4.,
             "unit":"synthetic_unit","evidence_ids":["a/v11"],"depends_on_claim_ids":[],"sentence":"EDA median is 4 synthetic_unit."}
    difference = {**claim,"claim_id":"difference","claim_type":"comparison","operator":"difference","value":3.,
                  "evidence_ids":["a/v11","b"],"sentence":"The signed difference is 3 synthetic_unit."}
    return {"index":10,"completed_after_event_index":completion_index,"result":{
        "initial":{"request":{"messages":[{"content":"system"},{"content":json.dumps(payload)}]}},
        "display":{"claims":[claim,difference]}}}


def test_completion_check_retains_content_after_benign_versions_but_detects_stale_values():
    unchanged = completion_adequacy(example(20),20)
    changed = completion_adequacy(example(40),20)
    restored = completion_adequacy(example(60),20)
    assert unchanged["adequate_at_completion"] and not unchanged["target_value_changed"]
    assert not changed["adequate_at_completion"] and changed["target_value_changed"]
    assert restored["adequate_at_completion"]
