from copy import deepcopy
from temporal_evidence.semantic.scoring import proposition, score, snapshot
from temporal_evidence.semantic.ontology import validate_export
from temporal_evidence.structure.program import build_case, fixture, validate, updates, runtime_support
from temporal_evidence.structure.oracle import reference
from temporal_evidence.schema import Record
from temporal_evidence.io import read_json


def inputs():
    episode=read_json("artifacts/prepared/wesad-S6-e0.json")
    q={"dataset_id":"wesad","subject_id":"S6","session_id":"session_1","family":"current_evidence",
       "event_start_seconds":episode["start"],"event_end_seconds":episode["end"],"knowledge_time":episode["end"]+1}
    events=episode["variants"]["clean"]["events"]
    _, latest=snapshot(events,q["knowledge_time"])
    e=next(e for e in latest.values() if e["quantity"]=="eda_median" and e["event_end_seconds"]==episode["start"] and e["event_start_seconds"]==episode["start"]-120)
    c={"claim_id":"c","claim_type":"numeric_observation","subject_id":"S6","quantity":"eda_median",
       "event_start_seconds":e["event_start_seconds"],"event_end_seconds":e["event_end_seconds"],"operator":"approximately_equal",
       "value":e["value"],"unit":"uS","evidence_ids":[e["record_id"]],"depends_on_claim_ids":[],"sentence":f"Baseline EDA median was {e['value']} uS."}
    return episode,events,q,c


def test_grounded_background_does_not_supply_target_or_hide_errors():
    _,events,q,c=inputs()
    assert proposition(c,events,q)["grounded"]
    assert score([c],events,q)["matched"]==0
    wrong=deepcopy(c); wrong["subject_id"]="S99"
    assert not proposition(wrong,events,q)["grounded"]
    wrong=deepcopy(c); wrong["value"]+=100
    assert not proposition(wrong,events,q)["grounded"]
    wrong=deepcopy(c); wrong["event_start_seconds"]=q["event_start_seconds"]; wrong["event_end_seconds"]=q["event_end_seconds"]
    assert not proposition(wrong,events,q)["grounded"]


def test_canonical_matching_duplicates_and_empty_output():
    _,events,q,c=inputs()
    q={**q,"event_start_seconds":c["event_start_seconds"],"event_end_seconds":c["event_end_seconds"]}
    a=score([c],events,q); duplicate={**c,"claim_id":"different_id"}
    b=score([c,duplicate],events,q)
    assert a["matched"]==b["matched"]==1
    assert b["claims"][0]["canonical"]==b["claims"][1]["canonical"]
    empty=score([],events,q)
    assert empty["precision"] is None and empty["recall"]==empty["harmonic"]==0


def test_version_semantics_historical_truth_and_current_correction():
    _,events,q,c=inputs(); old=next(e for e in events if e["record_id"]==c["evidence_ids"][0])
    revision={**old,"record_id":old["record_id"]+"new","version":2,"supersedes_id":old["record_id"],"value":old["value"]+1,"ingested_at_seconds":q["knowledge_time"]+10}
    es=events+[revision]
    assert proposition(c,es,q)["grounded"]
    later={**q,"knowledge_time":q["knowledge_time"]+10}
    assert not proposition(c,es,later)["grounded"]
    historical={**c,"temporal_mode":"historical","as_of_knowledge_time":q["knowledge_time"]}
    assert proposition(historical,es,later)["grounded"]


def test_absence_requires_closed_producer_universe():
    _,events,q,c=inputs()
    c={**c,"claim_type":"missing_evidence","operator":"missing","value":None,"quantity":"imaginary_quantity","evidence_ids":[]}
    assert not proposition(c,events,q)["grounded"]


def test_typed_relation_validation_detects_wrong_direction():
    nodes=[{"id":"o","labels":["Observation"],"properties":{"kind":"observation"}},
           {"id":"s","labels":["Sensor"],"properties":{"kind":"sensor"}}]
    edge={"id":"e","source":"o","target":"s","type":"OBSERVED_BY"}
    assert not validate_export({"nodes":nodes,"edges":[edge]})
    assert validate_export({"nodes":nodes,"edges":[{**edge,"source":"s","target":"o"}]})


def test_structural_counterexample_and_surviving_independent_alternative():
    episode,*_=inputs()
    for depth in (1,2,3,4):
        for regime in ("single","alternative"):
            case=build_case(episode,depth,regime); candidate=fixture(case)
            accepted,decisions=validate(candidate,case)
            assert len(accepted)==len(candidate["claims"]) and all(d["complete_witness_family"] for d in decisions)
            for condition in ("necessary","route_loss","benign","irrelevant"):
                revised=case["events"]+updates(case,condition)
                oracle=reference(case,revised,case["knowledge_time"]+30)
                state=runtime_support(accepted,case,{e["record_id"]:Record.from_dict(e) for e in revised})
                assert all(state[c["claim_id"]]==oracle[c["proposition"]] for c in accepted)
                assert oracle["answer"] == (condition in {"benign","irrelevant"} or (condition=="route_loss" and regime=="alternative"))
            if depth>1:
                assert all(token not in case["tests"] for w in accepted[-1]["witnesses"] for token in w)
                assert not reference(case,case["events"]+updates(case,"necessary"),case["knowledge_time"]+30)["answer"]


def test_model_links_are_never_silently_inserted_and_weak_witness_rejected():
    episode,*_=inputs(); case=build_case(episode,4,"alternative")
    direct={"claims":[{"claim_id":"r","proposition":"answer","value":True,
        "witnesses":[["A1","A2","A3","A4"]],"sentence":"All four tests hold in A."}],"explanation":""}
    accepted,decisions=validate(direct,case)
    assert accepted==direct["claims"] and not decisions[0]["complete_witness_family"]
    weak=deepcopy(direct); weak["claims"][0]["witnesses"]=[["A1"]]
    assert not validate(weak,case)[0]


def test_direct_full_predictions_use_independent_change_set():
    from temporal_evidence.structure.replay import replay_case
    episode,*_=inputs()
    for depth in (1,4):
        case=build_case(episode,depth,"alternative"); claims=fixture(case)["claims"]
        for condition in ("necessary","route_loss","benign","irrelevant"):
            direct=replay_case(case,claims,"fixture","B1",condition)
            full=replay_case(case,claims,"fixture","B3",condition)
            assert direct["theory_direct_prediction_agrees"]
            assert full["missed_changes"]==full["collateral"]==0
            if condition=="necessary":
                assert (direct["xi"]>0)==(depth>1)
            if condition in {"benign","irrelevant"}: assert direct["xi"] is None


def test_actual_export_projection_has_stored_and_derived_witness_ids():
    from temporal_evidence.semantic.export import read_export
    from temporal_evidence.semantic.projection import core,records,dependency_statistics
    from pathlib import Path
    path=Path("artifacts/analysis/semantic_analysis_v1/exports/minimum_v1__wesad-S6-e0__correction__M1.json.gz")
    graph=read_export(path); rs=records(graph)
    claim=next(r for r in rs.values() if r["record_type"]=="claim" and "-c0-" in r["record_id"])
    cid=claim["record_id"].split("/claim/")[0]; t=claim["metadata"]["query"]["knowledge_time"]
    before=core(graph,cid,t+.01); after=core(graph,cid,t+30+.01,include_withdrawn=True)
    assert dependency_statistics(before)["claims"]>0
    edge_ids={e["id"] for e in graph["edges"]}
    assert all(set(e["witness_edge_ids"])<=edge_ids for e in after["edges"])
    assert any(not e["directly_stored"] for e in after["edges"])
    assert all(n.get("assessment",{}).get("known_at",0)<=after["knowledge_time"] for n in after["nodes"] if n.get("assessment"))


def test_primitive_normalization_resolves_explicit_meaning_without_adding_links():
    from temporal_evidence.semantic.aliases import canonical_case
    from temporal_evidence.semantic.structural_analysis import audit_program
    episode,*_=inputs();case=build_case(episode,2,"single")
    primitive={"claim_id":"c1","proposition":"A1","value":True,"witnesses":[["A1"]],"sentence":"The specified EDA comparison holds."}
    candidate={"claims":[primitive],"explanation":primitive["sentence"]}
    assert not validate(candidate,case)[0]
    accepted,_=validate(candidate,canonical_case(case))
    assert accepted==candidate["claims"] and accepted[0]["witnesses"]==[["A1"]]
    assert audit_program(accepted,case)[0]["grounded"]
    wrong=deepcopy(case)
    for e in wrong["events"]:
        if e["record_id"]==wrong["tests"]["A1"]["source_id"]:e["value"]=wrong["tests"]["A1"]["threshold"]-1
    assert not audit_program(accepted,wrong)[0]["grounded"]


def test_native_fractional_unit_is_not_an_extra_prose_number():
    from temporal_evidence.semantic.structural_analysis import audit_program
    episode,*_=inputs();case=build_case(episode,1,"single");t=case["tests"]["A3"]
    c={"claim_id":"c","proposition":"A3","value":True,"witnesses":[["A3"]],
       "sentence":f"Acceleration SD is at least {t['threshold']} 1/64g."}
    assert not audit_program([c],case)[0]["prose_audit"]["unmatched_numbers"]


def test_participant_names_are_scoped_to_dataset_in_uncertainty():
    from temporal_evidence.semantic.statistics import cluster_ratio
    rows=[{"dataset":s,"subject":"S1","episode_id":s+"e0","n":n,"d":1} for s,n in (("wesad",0),("ppg_dalia",1))]
    result=cluster_ratio(rows,"n","d")
    assert result["subjects"]==2 and result["mean"]==.5


def test_historical_projection_retains_earlier_evidence_after_correction():
    import json
    from temporal_evidence.semantic.export import read_export
    from temporal_evidence.semantic.projection import core,records
    graph=read_export("artifacts/analysis/semantic_analysis_v1/exports/minimum_v1__wesad-S6-e0__correction__M1.json.gz")
    rs=records(graph);claim=next(r for r in rs.values() if r["record_type"]=="claim" and "-c0-" in r["record_id"])
    case=claim["record_id"].split("/claim/")[0];t=claim["metadata"]["query"]["knowledge_time"]
    for node in graph["nodes"]:
        if node["properties"].get("id","").startswith(case+"/claim/") and node["semantic_type"]=="claim":
            record=json.loads(node["properties"]["payload"])
            record["metadata"]["claim"].update(temporal_mode="historical",as_of_knowledge_time=t)
            node["properties"]["payload"]=json.dumps(record)
    projected=core(graph,case,t+30+.01,include_withdrawn=True)
    assert all(e["directly_stored"] for e in projected["edges"])
    assert all(e["resolved_knowledge_time"]==t for e in projected["edges"])
