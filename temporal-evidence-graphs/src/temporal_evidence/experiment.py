"""Paired replay runner. Cases are resumed by immutable identifiers."""
from __future__ import annotations
import asyncio
from dataclasses import asdict,replace
from pathlib import Path
import time
import numpy as np

from temporal_evidence.generation.client import GPUClient
from temporal_evidence.io import digest_file,digest_object,read_json,write_json,utc_now
from temporal_evidence.replay.temporal import apply_revision,current_versions
from temporal_evidence.schema import Record
from temporal_evidence.storage.relational import RelationalStore
from temporal_evidence.study import METHODS,VARIANTS,episode_rows,load_config,make_cases,query_evidence,verify_frozen


def displayed_records(display,case,query,store):
    if not display:
        return []
    identifiers={claim["claim_id"]:f"{case['case_id']}/claim/{claim['claim_id']}" for claim in display["claims"]}
    records=[]
    common=dict(dataset_id=case["dataset"],subject_id=case["subject"],session_id="session_1",
                event_start_seconds=query.event_start_seconds,event_end_seconds=query.event_end_seconds,
                ingested_at_seconds=query.knowledge_time+1e-6)
    for claim_index,claim in enumerate(display["claims"]):
        dependencies=tuple(identifiers.get(identifier,identifier) for identifier in claim["depends_on_claim_ids"])
        sources=tuple(claim["evidence_ids"])+dependencies
        if case["method"]=="B0":
            # Keep arbitrary unverified proposals as data, without promoting their
            # potentially cyclic or duplicate dependency proposals into the DAG.
            dependencies=()
            sources=()
        if claim["claim_type"]=="missing_evidence":
            watch_id=f"watch/{case['dataset']}/{case['subject']}/{query.event_start_seconds:g}/{claim['quantity']}"
            watch=store.get(watch_id+"/v1")
            if watch is None:
                watch=Record(record_id=watch_id+"/v1",logical_id=watch_id,record_type="feature",value=0.,
                             quantity=claim["quantity"]+"_availability",unit="boolean",operator="measured",**common,
                             metadata={"monitored_quantity":claim["quantity"]})
                records.append(watch)
            sources+=(watch.record_id,)
        identifier=identifiers[claim["claim_id"]]+(f"/{claim_index}" if case["method"]=="B0" else "")
        records.append(Record(record_id=identifier,logical_id=identifier,
                              record_type="claim",quantity=claim["quantity"],value=claim["value"],unit=claim["unit"],
                              source_ids=sources,operator="identity",**common,
                              metadata={"claim":claim,"query":asdict(query),"claim_dependency_records":list(dependencies),
                                        "accepted":case["method"]!="B0"}))
    identifier=case["case_id"]+"/explanation"
    records.append(Record(record_id=identifier,logical_id=identifier,record_type="explanation",source_ids=tuple(r.record_id for r in records if r.record_type=="claim"),
                          metadata={"display":display,"case_id":case["case_id"]},**common))
    return records


def ingest_until(store,events,known_at,method,ingested,displays):
    arrivals=sorted([event for event in events if event.ingested_at_seconds<=known_at and event.record_id not in ingested],
                    key=lambda event:(event.ingested_at_seconds,event.version,event.record_id))
    results=[]
    ordinary=[event for event in arrivals if event.supersedes_id is None]
    if ordinary:
        started=time.perf_counter()
        store.put_many(ordinary)
        results.append({"kind":"ordinary_ingestion","seconds":time.perf_counter()-started,"records":len(ordinary)})
    for event in arrivals:
        if event.supersedes_id is not None:
            result=apply_revision(store,event,method)
            result.update(trigger_id=event.record_id,ingested_at=event.ingested_at_seconds)
            results.append(result)
    # Negative-evidence claims subscribe to explicit query-availability records.
    for watch in list(store._records.values()):
        if watch.version!=1 or "monitored_quantity" not in watch.metadata:
            continue
        relevant=[event for event in ordinary if event.record_type=="feature"
                  and event.quantity==watch.metadata["monitored_quantity"]
                  and (event.event_start_seconds,event.event_end_seconds)==(watch.event_start_seconds,watch.event_end_seconds)
                  and event.ingested_at_seconds>watch.ingested_at_seconds]
        for event in relevant:
            change=replace(watch,record_id=watch.logical_id+"/v2",version=2,supersedes_id=watch.record_id,
                           value=float(event.evidence_state=="available" and event.value is not None),
                           ingested_at_seconds=event.ingested_at_seconds,source_ids=(event.record_id,))
            result=apply_revision(store,change,method)
            result.update(trigger_id=event.record_id,ingested_at=event.ingested_at_seconds)
            results.append(result)
    ingested.update(event.record_id for event in arrivals)
    visible=store.snapshot(known_at)
    latest=current_versions(visible)
    for result in results:
        for identifier,assessment in result.get("assessments",{}).items():
            if identifier in displays:
                old=displays[identifier]["state"]
                displays[identifier]["state"]=assessment["state"]
                displays[identifier]["current_evidence_ids"]=[latest[visible[source].logical_id].record_id
                    if source in visible else source for source in displays[identifier]["claim"]["evidence_ids"]]
                if old!=assessment["state"]:
                    displays[identifier]["last_transition"]={"trigger_id":result["trigger_id"],"flag_seconds":result["seconds"]}
    return results


async def scenario(episode_row,variant,checkpoints,run_id,config,client,semaphore,graph_driver=None):
    episode=read_json(episode_row["path"])
    stores={}
    for method in METHODS:
        scope=f"{run_id}/{episode['episode_id']}/{variant}/{method}"
        if method in {"B2","M1"}:
            from temporal_evidence.storage.graph import GraphStore
            stores[method]=GraphStore(scope=scope,driver=graph_driver)
        else:
            stores[method]=RelationalStore(f".local/{run_id}.sqlite",scope=scope)
    ingested={method:set() for method in METHODS}
    displays={method:{} for method in METHODS}
    previous_common=None
    output=[]
    try:
        for checkpoint in checkpoints:
            base={key:episode_row[key] for key in ["episode_id","dataset","subject","family","split"]}
            base.update(variant=variant,checkpoint=checkpoint,knowledge_time=episode["end"]+(1,31,91)[checkpoint])
            cases=[{**base,"method":method,"case_id":f"{episode['episode_id']}-{variant}-c{checkpoint}-{method}"} for method in METHODS]
            async def execute(case):
                case_started=time.perf_counter()
                method=case["method"]
                store=stores[method]
                query,evidence,events=query_evidence(case,episode)
                # Only visible runtime events enter the validator; evaluator_only is never passed.
                update_started=time.perf_counter()
                revisions=ingest_until(store,events,query.knowledge_time,method,ingested[method],displays[method])
                update_seconds=time.perf_counter()-update_started
                retrieval_started=time.perf_counter()
                snapshot=store.snapshot(query.knowledge_time)
                retrieval_seconds=time.perf_counter()-retrieval_started
                path=Path(f"artifacts/runs/{run_id}/cases/{case['case_id']}.json")
                if path.exists():
                    result=read_json(path)
                else:
                    persistent_before={key:dict(value) for key,value in displays[method].items()}
                    async with semaphore:
                        result=await client.answer(case["case_id"],method,query,evidence,snapshot,
                                                   previous_common if case["family"]=="revision_impact" else None)
                    result.update(case=case,query=asdict(query),evidence_hash=digest_object([r.to_dict() for r in evidence]),
                                  revisions=revisions,persistent_before=persistent_before,
                                  database_update_seconds=update_seconds,retrieval_seconds=retrieval_seconds,
                                  end_to_end_seconds=time.perf_counter()-case_started,
                                  completed_at=utc_now(),status="completed" if result["display"] is not None else "failed")
                    if result["display"] is None:
                        result["failure_reason"]=(result["repair"] or result["initial"]).get("error","No parsed output")
                    write_json(path,result)
                new_records=displayed_records(result["display"],case,query,store)
                if new_records:
                    store.put_many(new_records)
                for record in new_records:
                    if record.record_type=="claim":
                        displays[method][record.record_id]={"claim":record.metadata["claim"],"state":"supported" if method!="B0" else "unverified",
                                                           "current_evidence_ids":record.metadata["claim"]["evidence_ids"],
                                                           "created_at":query.knowledge_time,"last_transition":None}
                return result
            completed=await asyncio.gather(*(execute(case) for case in cases))
            output.extend(completed)
            previous_common=completed[0]["display"]  # Same prior B0 output is shown to all methods, never a gold answer.
            write_json(f"artifacts/runs/{run_id}/progress.json",{"updated_at":utc_now(),
                "completed_case_files":len(list(Path(f"artifacts/runs/{run_id}/cases").glob("*.json")))})
    finally:
        for store in stores.values():
            store.close()
    return output


async def pilot(config_path="configs/minimum_study.yaml",run_id="pilot_v1"):
    config=load_config(config_path)
    from neo4j import GraphDatabase
    driver=GraphDatabase.driver("bolt://127.0.0.1:7687",auth=None)
    Path(".local").mkdir(exist_ok=True)
    client=GPUClient(config,log_path=f"artifacts/runs/{run_id}/requests.jsonl")
    rows=episode_rows("development")
    selected=[]
    for index in range(8):
        dataset=("synthetic","wesad","ppg_dalia")[index%3]
        candidates=[row for row in rows if row["dataset"]==dataset]
        selected.append((candidates[index%len(candidates)],VARIANTS[index%4],(0,1,2) if index<6 else (0,)))
    semaphore=asyncio.Semaphore(4)
    started=time.perf_counter()
    results=[]
    try:
        for row,variant,checkpoints in selected:
            results.extend(await scenario(row,variant,checkpoints,run_id,config,client,semaphore,driver))
            print(f"Pilot: {len(results)}/100 initial cases accounted for",flush=True)
        seconds=time.perf_counter()-started
        interactive=[]
        for index in range(20):
            row,variant,_=selected[index%len(selected)]
            episode=read_json(row["path"])
            case={**row,"variant":variant,"knowledge_time":episode["end"]+31}
            query,evidence,events=query_evidence(case,episode)
            visible={r.record_id:r for r in events if r.ingested_at_seconds<=query.knowledge_time}
            request_started=time.perf_counter()
            result=await client.answer(f"interactive-{index}","M1",query,evidence,visible)
            interactive.append({"index":index,"seconds":time.perf_counter()-request_started,
                                "failed":result["display"] is None,"repair":result["repair"] is not None})
        write_json(f"artifacts/runs/{run_id}/interactive.json",interactive)
        initial_seconds=[r["initial"]["seconds"] for r in results]
        repairs=[r["repair"] for r in results if r["repair"]]
        report={"run_id":run_id,"initial_cases":len(results),"repair_calls":len(repairs),"batch_wall_seconds":seconds,
                "initial_cases_per_second_including_repairs_and_database":len(results)/seconds,
                "initial_latency_p50":float(np.quantile(initial_seconds,.5)),"initial_latency_p95":float(np.quantile(initial_seconds,.95)),
                "failed_cases":sum(r["status"]=="failed" for r in results),
                "truncated_initial":sum(r["initial"].get("truncated",False) for r in results),
                "all_methods_produced_output":all(any(r["case"]["method"]==method and r["display"] is not None for r in results) for method in METHODS),
                "estimated_minimum_seconds_including_repairs_and_database":seconds/len(results)*3600,
                "config_sha256":digest_file(config_path),"completed_at":utc_now()}
        report.update(interactive_requests=len(interactive),interactive_concurrency=1,
                      interactive_p50=float(np.quantile([r["seconds"] for r in interactive],.5)),
                      interactive_p95=float(np.quantile([r["seconds"] for r in interactive],.95)))
        write_json("artifacts/manifests/pilot.json",report)
        write_json(f"artifacts/runs/{run_id}/summary.json",report)
        return report
    finally:
        await client.close()
        driver.close()


async def run(manifest_path="artifacts/manifests/minimum_run.json"):
    manifest=read_json(manifest_path)
    verify_frozen(manifest)
    config=manifest["config"]
    run_id=manifest["run_id"]
    from neo4j import GraphDatabase
    driver=GraphDatabase.driver("bolt://127.0.0.1:7687",auth=None)
    driver.verify_connectivity()
    Path(".local").mkdir(exist_ok=True)
    client=GPUClient(config,log_path=f"artifacts/runs/{run_id}/requests.jsonl")
    semaphore=asyncio.Semaphore(4)
    started=time.perf_counter()
    try:
        rows=episode_rows("test")
        # Randomize scenario order once, independently of outcomes.
        work=[(row,variant) for row in rows for variant in VARIANTS]
        order=np.random.default_rng(20260928).permutation(len(work))
        for position,index in enumerate(order):
            row,variant=work[int(index)]
            await scenario(row,variant,(0,1,2),run_id,config,client,semaphore,driver)
            print(f"Locked run: {position+1}/{len(work)} scenarios accounted for",flush=True)
        outputs=Path(f"artifacts/runs/{run_id}/cases")
        actual={path.stem for path in outputs.glob("*.json")}
        expected={case["case_id"] for case in manifest["cases"]}
        assert actual==expected,(len(actual),len(expected))
        summary={"run_id":run_id,"accounted_cases":len(actual),"expected_cases":len(expected),
                 "invocation_wall_seconds":time.perf_counter()-started,"finished_at":utc_now(),"protocol_hash":manifest["protocol_hash"]}
        write_json(f"artifacts/runs/{run_id}/completion.json",summary)
        return summary
    finally:
        await client.close()
        driver.close()
