"""Separate CPU database replication correcting primitive proposition admission."""
from pathlib import Path
from neo4j import GraphDatabase
from temporal_evidence.io import read_json,write_json,digest_file,utc_now
from temporal_evidence.structure.program import validate
from temporal_evidence.structure.replay import replay_case,CONDITIONS,METHODS
from temporal_evidence.semantic.aliases import canonical_case

ROOT=Path("artifacts/runs/structure_study_v1")

def run():
    target=ROOT/"primitive_alias_replication";target.mkdir(parents=True,exist_ok=True)
    for folder in ("candidates","replay"):(target/folder).mkdir(exist_ok=True)
    cases=read_json(ROOT/"cases.json")
    manifest={"registered_at":utc_now(),"correction":"Primitive test names already defined in the input map to singleton comparison propositions.",
        "scope":"post-core CPU-only corrected replication; original admission and all model outputs unchanged",
        "original_cases_sha256":digest_file(ROOT/"cases.json"),"original_core_frozen_sha256":digest_file(ROOT/"core/frozen.json"),
        "normalizer_sha256":digest_file("src/temporal_evidence/semantic/aliases.py"),"new_gpu_calls":0}
    if not (target/"manifest.json").exists():write_json(target/"manifest.json",manifest)
    adequate=0
    with GraphDatabase.driver("bolt://127.0.0.1:7687",auth=None) as driver:
        for i,original in enumerate(cases):
            case=canonical_case(original);saved=ROOT/"core/candidates"/(case["case_id"]+".json");candidate=read_json(saved)
            claims,decisions=validate(candidate["final_candidate"],case)
            root=any(c["proposition"]=="answer" for c in claims);adequate+=root
            write_json(target/"candidates"/saved.name,{"case_id":case["case_id"],"accepted":claims,"decisions":decisions,
                "adequate_answer":root,"original_candidate_sha256":digest_file(saved),"normalization":"primitive test name to its explicit comparison"})
            path=target/"replay"/saved.name
            if not path.exists():
                rows=[replay_case(case,claims,"generated_alias",m,c,driver,str(target/"replay.sqlite"),"structure_study_v1/primitive_alias_replication")
                      for c in CONDITIONS for m in METHODS]
                for condition in CONDITIONS:
                    group={r["method"]:r for r in rows if r["condition"]==condition}
                    assert group["M1"]["logical_hash"]==group["B3"]["logical_hash"]
                    assert group["B1"]["logical_hash"]==group["B2"]["logical_hash"]
                write_json(path,rows)
            print(f"Primitive-name replication {i+1}/{len(cases)}",flush=True)
    write_json(target/"completion.json",{"cases":len(cases),"cells":len(cases)*20,"admissible_roots":adequate,"new_gpu_calls":0,"finished_at":utc_now()})

if __name__=="__main__":run()
