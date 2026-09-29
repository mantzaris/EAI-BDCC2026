"""Reproducible pre-inference gates and reconfirmation of frozen observations."""
from collections import Counter
from pathlib import Path
import subprocess
import sys
from temporal_evidence.io import read_json,write_json,digest_file,utc_now
from temporal_evidence.study import verify_frozen
from temporal_evidence.semantic.export import read_export
from temporal_evidence.semantic.ontology import validate_export

def run():
    verify_frozen(read_json("artifacts/manifests/minimum_run.json"))
    tests=subprocess.run([sys.executable,"-m","pytest","tests/test_semantic_protocol.py","-q"],capture_output=True,text=True)
    assert tests.returncode==0,tests.stdout+tests.stderr
    root=Path("artifacts/analysis/semantic_analysis_v1/exports"); manifest=read_json(root/"manifest.json")
    nodes=Counter(); edges=Counter(); paths=0
    for item in manifest["scopes"]:
        assert digest_file(root/item["file"])==item["sha256"]
        assert not validate_export(read_export(root/item["file"]))
        method=item["scope"].split("/")[-1]
        nodes.update({(method,k):v for k,v in item["node_types"].items()})
        edges.update({(method,k):v for k,v in item["edge_types"].items()}); paths+=item["verified_paths"]
    saved=read_json("artifacts/manifests/database_accounting.json")["neo4j_matched_run"]
    assert all(nodes[(r["method"],r["kind"])]==r["count"] for r in saved["nodes"])
    assert all(nodes[(r["method"],"assessment")]==r["count"] for r in saved["support_assessments"])
    assert all(edges[(r["method"],r["relation"]) ]==r["count"] for r in saved["edges"])
    counts=Counter()
    for path in Path("artifacts/runs/minimum_v1/cases").glob("*.json"):
        output=read_json(path)
        if output["case"]["method"]=="M1":
            for c in (output["display"] or {}).get("claims",[]):
                counts["M1_claims"]+=1; counts["M1_claims_with_parent"]+=bool(c["depends_on_claim_ids"])
    scope=read_json("artifacts/analysis/minimum_v1/contract_scope.json")
    counts["B0_contract_invalid"]=sum(r["contract_invalid"] for r in scope["rows"] if r["method"]=="B0")
    counts["B0_locally_supported_background"]=sum(r["off_target_locally_supported"] for r in scope["rows"] if r["method"]=="B0")
    metrics=read_json("artifacts/evaluation/minimum_v1/metrics.json")
    correction={m:{"required":sum(r["correction_required"] for r in metrics if r["method"]==m),"corrected":sum(r["corrected"] for r in metrics if r["method"]==m)} for m in ("B1","B2","M1","B3")}
    assert all(r["required"]==r["corrected"] for r in correction.values())
    report={"passed":True,"completed_at":utc_now(),"focused_tests":tests.stdout.strip(),"frozen_integrity":"original runtime and input hashes unchanged",
        "actual_export_scopes":len(manifest["scopes"]),"verified_stored_paths":paths,"counts_match_original_accounting":True,
        "reconfirmed":dict(counts),"original_correction":correction,"export_manifest_sha256":digest_file(root/"manifest.json"),"test_source_sha256":digest_file("tests/test_semantic_protocol.py")}
    write_json("artifacts/runs/structure_study_v1/pre_inference_gates.json",report)
    write_json("artifacts/analysis/semantic_analysis_v1/reconfirmation.json",report); print(report)

if __name__=="__main__": run()
