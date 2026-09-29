from temporal_evidence.experiment import maintain_explanations
from temporal_evidence.synthetic.fixtures import record
from temporal_evidence.storage.relational import RelationalStore


def test_retraction_and_restoration_store_actual_text_versions():
    store=RelationalStore()
    first={"claim_id":"a","sentence":"EDA is 2 units.","evidence_ids":["e"]}
    second={"claim_id":"b","sentence":"Motion is 1 unit.","evidence_ids":["m"]}
    original={"claims":[first,second],"explanation":"EDA is 2 units. Motion is 1 unit."}
    store.put_many([record("case/claim/a",2,kind="claim"),record("case/claim/b",1,kind="claim"),
                    record("case/explanation",sources=("case/claim/a","case/claim/b"),kind="explanation",metadata={"display":original})])
    displays={"case/claim/a":{"state":"contradicted","claim":first},"case/claim/b":{"state":"supported","claim":second}}
    versions=maintain_explanations(store,displays,20)
    assert versions[0].metadata["display"]["explanation"]=="Motion is 1 unit."
    assert store.snapshot(15)["case/explanation"].metadata["display"]==original
    displays["case/claim/a"]["state"]="supported"
    restored=maintain_explanations(store,displays,30)
    assert restored[0].metadata["display"]["explanation"]==original["explanation"]
    assert restored[0].supersedes_id==versions[0].record_id
