import importlib.metadata
import platform
import shutil
import subprocess
from pathlib import Path
from temporal_evidence.io import utc_now,write_json


def check_environment():
    import torch
    assert torch.cuda.is_available(), "A CUDA GPU is required; CPU fallback is prohibited"
    a=torch.arange(64*64,device="cuda",dtype=torch.float32).reshape(64,64)/4096
    result=a.to(torch.bfloat16)@a.to(torch.bfloat16)
    torch.cuda.synchronize()
    assert result.device.type=="cuda" and result.isfinite().all()
    from neo4j import GraphDatabase
    with GraphDatabase.driver("bolt://127.0.0.1:7687",auth=None) as driver:
        rows,_,_=driver.execute_query("CALL dbms.components() YIELD name,versions,edition RETURN name,versions,edition")
        database=[dict(row) for row in rows]
    versions={p:importlib.metadata.version(p) for p in ["torch","vllm","transformers","numpy","neo4j","pydantic"]}
    report={"checked_at":utc_now(),"python":platform.python_version(),"platform":platform.platform(),
            "versions":versions,"cuda_runtime":torch.version.cuda,"gpu":torch.cuda.get_device_name(),
            "bf16_operation_device":str(result.device),"gpu_memory_bytes":torch.cuda.get_device_properties(0).total_memory,
            "database":database,"disk_free_bytes":shutil.disk_usage(".").free,
            "nvidia_smi":subprocess.check_output(["nvidia-smi"],text=True)}
    for name in ["memory.max","cpu.max"]:
        path=Path("/sys/fs/cgroup")/name
        report[name]=path.read_text().strip() if path.exists() else None
    write_json("artifacts/manifests/environment.json",report)
    # A small fixed CPU reference versus a GPU quantile computation.
    import numpy as np
    sample=np.array([.1,.7,1.,1.2,1.4,1.8,2.0],dtype=np.float64)
    tensor=torch.as_tensor(sample,device="cuda")
    quantiles=torch.quantile(tensor,torch.tensor([.25,.5,.75],device="cuda",dtype=torch.float64)).cpu().numpy()
    reference=np.quantile(sample,[.25,.5,.75])
    assert np.allclose(quantiles,reference,atol=1e-12,rtol=1e-12)
    write_json("artifacts/manifests/numeric_cuda_reference.json",{"cpu_reference":reference.tolist(),
               "cuda_quantiles":quantiles.tolist(),"atol":1e-12,"device":"cuda:0","passed":True})
    return report


def validate_core(graph=False):
    from dataclasses import replace
    from uuid import uuid4
    from temporal_evidence.synthetic.fixtures import correction_fixture,record
    from temporal_evidence.storage.relational import RelationalStore
    from temporal_evidence.replay.temporal import apply_revision
    modes={};scores=[]
    claims={"direct_claim","downstream_claim","or_claim","unaffected"}
    for mode in ["correction","invalidation","benign","irrelevant"]:
        records,revision=correction_fixture()
        if mode=="invalidation":
            revision=replace(revision,value=None,evidence_state="invalidated")
        elif mode=="benign":
            revision=replace(revision,value=2)
        elif mode=="irrelevant":
            extra=record("unrelated",10)
            records.append(extra)
            revision=replace(extra,record_id="unrelated/v2",version=2,ingested_at_seconds=20,supersedes_id="unrelated",value=20)
        required={"direct_claim","downstream_claim"} if mode in {"correction","invalidation"} else set()
        results={}
        for method in ["B0","B1","B2","M1","B3"]:
            if graph and method in {"B2","M1"}:
                from temporal_evidence.storage.graph import GraphStore
                store=GraphStore(scope=f"validation-{mode}-{method}-{uuid4().hex}")
            else:
                store=RelationalStore()
            store.put_many(records)
            result=apply_revision(store,revision,method)
            assert store.snapshot(15)["a"].value==2 and revision.record_id not in store.snapshot(15)
            states={identifier:result["assessments"].get(identifier,{"state":"supported"})["state"] for identifier in claims}
            corrected=sum(states[identifier]!="supported" for identifier in required)
            collateral=sum(states[identifier]!="supported" for identifier in claims-required)
            scores.append({"mode":mode,"method":method,"correction_required":len(required),"corrected":corrected,
                           "residual":len(required)-corrected,"unaffected":len(claims-required),"collateral":collateral,
                           "flag_service_seconds":result["seconds"],"states":states})
            assert collateral==0
            if method in {"M1","B3"}:assert corrected==len(required)
            if mode=="correction":
                restored=replace(revision,record_id="a/v3",version=3,ingested_at_seconds=30,supersedes_id=revision.record_id,value=2)
                restoration=apply_revision(store,restored,method)
                if method in {"M1","B3"}:
                    assert restoration["assessments"]["direct_claim"]["state"]=="supported"
                    assert restoration["assessments"]["downstream_claim"]["state"]=="supported"
                result["restoration"]=restoration
            results[method]=result;store.close()
        assert results["M1"]["assessments"]==results["B3"]["assessments"]
        modes[mode]=results
    primary=modes["correction"]
    assert primary["M1"]["assessments"]["downstream_claim"]["state"]=="contradicted"
    assert primary["M1"]["assessments"]["or_claim"]["state"]=="supported"
    assert "downstream_claim" not in primary["B2"]["assessments"]
    report={"checked_at":utc_now(),"real_neo4j":graph,"passed":True,"results":primary,
            "symbolic_modes":modes,"symbolic_scores":scores,"interpretation":"Deterministic fixtures, not independent physiological samples"}
    write_json("artifacts/manifests/core_validation.json",report)
    return report
