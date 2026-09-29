"""Open-loop arrivals use a producer thread independent of all completions.

This is a separate systems workload, not additional physiological participants.
Both implementations maintain an identical symbolic dependency fixture. Generator
requests retrieve their inputs from that implementation's database snapshot.
"""
from __future__ import annotations
import asyncio
from dataclasses import replace,asdict
from pathlib import Path
import queue
import threading
import time
import numpy as np
from temporal_evidence.io import append_jsonl,digest_object,read_json,write_json,utc_now
from temporal_evidence.study import load_config
from temporal_evidence.schema import Query
from temporal_evidence.synthetic.fixtures import correction_fixture
from temporal_evidence.replay.temporal import apply_revision,current_versions
from temporal_evidence.generation.client import GPUClient
from temporal_evidence.generation.contract import Answer
from temporal_evidence.evaluation.exact import score_claims,required_slots,agrees


async def cell(method,rate,config,study):
    run_id=config["run_id"]
    cell_id=f"{method}-{rate}eps"
    directory=Path(f"artifacts/streaming/{run_id}/{cell_id}")
    directory.mkdir(parents=True,exist_ok=True)
    summary_path=directory/"summary.json"
    if summary_path.exists():
        return read_json(summary_path)
    if (directory/"events.jsonl").exists():
        raise RuntimeError("Interrupted open-loop cell retained; use a new systems run ID, do not mix clocks")
    if method=="M1":
        from temporal_evidence.storage.graph import GraphStore
        store=GraphStore(scope=f"{run_id}/{cell_id}")
    else:
        from temporal_evidence.storage.relational import RelationalStore
        store=RelationalStore(f".local/{run_id}.sqlite",scope=cell_id)
    records,_=correction_fixture()
    records=[replace(r,event_start_seconds=-120,event_end_seconds=0) if r.logical_id=="b" else r for r in records]
    store.put_many(records)
    original=next(r for r in records if r.logical_id=="a")
    client=GPUClient(study,log_path=str(directory/"requests.jsonl"))
    semaphore=asyncio.Semaphore(config["generation_concurrency"])
    count=round(rate*config["duration_seconds"])
    arrivals=queue.Queue()
    start=time.perf_counter()+.25
    start_utc=utc_now()
    event_rows=[]
    generations=[]
    tasks=[]
    errors=[]
    claim_state="supported"
    previous=original
    active_generations=0
    peak_pending=0
    def produce():
        for index in range(1,count+1):
            scheduled=start+(index-1)/rate
            time.sleep(max(0,scheduled-time.perf_counter()))
            arrivals.put((index,scheduled,time.perf_counter()))
    producer=threading.Thread(target=produce,daemon=True)
    producer.start()
    async def generate(index,scheduled,kind,query,evidence,snapshot):
        nonlocal active_generations
        entered=time.perf_counter()
        async with semaphore:
            active_generations+=1
            generation_started=time.perf_counter()
            try:
                result=await client.answer(f"{cell_id}-{index}-{kind}",method,query,evidence,snapshot)
                elapsed=time.perf_counter()-scheduled
                claims=(result["display"] or {}).get("claims",[])
                exact=score_claims(claims,[r.to_dict() for r in snapshot.values()],asdict(query))
                # The fixture also contains an alternative sensor and a derived
                # difference with the same quantity label. Only the two retrieved
                # operands define this particular request's answer slots.
                slots=required_slots([r.to_dict() for r in evidence],asdict(query))
                adequate=all(any(item["valid"] and claim["quantity"]==slot["quantity"] and agrees(claim["value"],slot["value"])
                                 and claim["claim_type"] in (("comparison","trend") if slot["kind"]=="difference" else ("numeric_observation","revision_effect"))
                                 for claim,item in zip(claims,exact)) for slot in slots)
                row={"index":index,"kind":kind,"arrival_to_complete_seconds":elapsed,
                     "completed_after_event_index":event_rows[-1]["index"] if event_rows else 0,
                     "adequacy_scope":"request_snapshot",
                     "queue_seconds":generation_started-entered,"generation_seconds":result["seconds"],
                     "adequate":adequate,"failed":result["display"] is None,
                     "deadline_missed":kind=="affected_repair" and (elapsed>config["repair_deadline_seconds"] or not adequate),
                     "validation_repair_calls":int(result["repair"] is not None),
                     "input_tokens":sum(call.get("response",{}).get("usage",{}).get("prompt_tokens",0)
                                        for call in [result["initial"],result["repair"]] if call),
                     "output_tokens":sum(call.get("response",{}).get("usage",{}).get("completion_tokens",0)
                                         for call in [result["initial"],result["repair"]] if call),
                     "result":result}
                generations.append(row);write_json(directory/f"explanation-{index}-{kind}.json",row)
            except Exception as error:
                errors.append({"index":index,"kind":kind,"error":repr(error)})
            finally:
                active_generations-=1
    try:
        for _ in range(count):
            while arrivals.empty():
                await asyncio.sleep(.001)
            index,scheduled,actual_arrival=arrivals.get_nowait()
            processing_started=time.perf_counter()
            value=4. if ((index+10)//20)%2 else 2.
            event=replace(original,record_id=f"a/v{index+1}",version=index+1,value=value,
                          supersedes_id=previous.record_id,ingested_at_seconds=100+index/rate)
            update=apply_revision(store,event,method)
            previous=event
            completed=time.perf_counter()
            states={identifier:assessment["state"] for identifier,assessment in update["assessments"].items()}
            expected="supported" if value==2 else "contradicted"
            assert states["direct_claim"]==states["downstream_claim"]==expected
            assert states["or_claim"]=="supported" and "unaffected" not in states
            material=expected!=claim_state
            affected=material and expected!="supported"
            claim_state=expected
            row={"index":index,"scheduled_seconds":scheduled-start,"arrival_lateness_seconds":actual_arrival-scheduled,
                 "event_queue_seconds":processing_started-scheduled,"database_update_seconds":update["seconds"],
                 "event_to_flag_seconds":completed-scheduled if affected else None,
                 "flag_deadline_missed":affected and completed-scheduled>config["flag_deadline_seconds"],
                 "affected":affected,"event_backlog":arrivals.qsize(),"pending_explanations":sum(not task.done() for task in tasks),
                 "states_hash":digest_object(states),"record_count":len(store._records)}
            event_rows.append(row)
            demands=[]
            if index%config["explanation_every_events"]==0:
                demands.append("scheduled")
            if affected:
                demands.append("affected_repair")
            if demands:
                retrieval_start=time.perf_counter()
                snapshot=store.snapshot(event.ingested_at_seconds)
                selected=current_versions(snapshot)
                evidence=[selected[name] for name in ("a","b")]
                query=Query(original.dataset_id,original.subject_id,original.session_id,0,10,event.ingested_at_seconds,
                            question="Report the target EDA median and its difference from the preceding 120-second median (target minus earlier).")
                row["retrieval_seconds"]=time.perf_counter()-retrieval_start
                for kind in demands:
                    tasks.append(asyncio.create_task(generate(index,scheduled,kind,query,evidence,snapshot)))
            peak_pending=max(peak_pending,sum(not task.done() for task in tasks))
            append_jsonl(directory/"events.jsonl",row)
            await asyncio.sleep(0)
        await asyncio.gather(*tasks)
        elapsed=time.perf_counter()-start
        repairs=[r for r in generations if r["kind"]=="affected_repair"]
        flags=[r["event_to_flag_seconds"] for r in event_rows if r["affected"]]
        def quantiles(values):
            return {"p50":float(np.quantile(values,.5)),"p95":float(np.quantile(values,.95))} if values else {"p50":None,"p95":None}
        summary={"cell_id":cell_id,"method":method,"offered_events_per_second":rate,"duration_seconds":config["duration_seconds"],
                 "started_at":start_utc,"finished_at":utc_now(),"wall_seconds_including_drain":elapsed,
                 "derived_events":len(event_rows),"raw_samples_processed":0,"completed_explanations":len(generations),
                 "achieved_events_per_second_including_drain":len(event_rows)/elapsed,
                 "explanations_per_second_including_drain":len(generations)/elapsed,
                 "peak_event_backlog":max(r["event_backlog"] for r in event_rows),"peak_pending_explanations":peak_pending,
                 "end_arrival_pending_explanations":event_rows[-1]["pending_explanations"],
                 "event_to_flag":quantiles(flags),"event_to_generated_repair":quantiles([r["arrival_to_complete_seconds"] for r in repairs]),
                 "explanation_latency":quantiles([r["arrival_to_complete_seconds"] for r in generations]),
                 "database_update":quantiles([r["database_update_seconds"] for r in event_rows]),
                 "retrieval":quantiles([r["retrieval_seconds"] for r in event_rows if "retrieval_seconds" in r]),
                 "flag_misses":sum(r["flag_deadline_missed"] for r in event_rows),"flag_denominator":len(flags),
                 "repair_misses":sum(r["deadline_missed"] for r in repairs),"repair_denominator":len(repairs),
                 "initial_gpu_calls":len(generations),"validation_repairs":sum(r["validation_repair_calls"] for r in generations),
                 "input_tokens":sum(r["input_tokens"] for r in generations),"output_tokens":sum(r["output_tokens"] for r in generations),
                 "logical_hash":digest_object([r["states_hash"] for r in event_rows]),"final_nodes":len(store._records),
                 "errors":errors,"maintenance":"immediate status retraction plus separately measured GPU replacement"}
        write_json(summary_path,summary)
        return summary
    finally:
        await client.close();store.close()


async def benchmark(config_path="configs/streaming.yaml"):
    config=load_config(config_path);study=load_config(config["study_config"])
    manifest=read_json("artifacts/manifests/minimum_run.json")
    assert study==manifest["config"]
    results=[]
    for rate,order in zip(config["rates"],config["method_orders"]):
        for method in order:
            result=await cell(method,rate,config,study)
            results.append(result)
            print(f"Streaming cell completed: {method} at {rate} events/s",flush=True)
        pair=[r for r in results if r["offered_events_per_second"]==rate]
        assert pair[0]["logical_hash"]==pair[1]["logical_hash"],"Graph/relational logical divergence"
    write_json(f"artifacts/streaming/{config['run_id']}/summary.json",{"config":config,"cells":results,"logical_parity":True})
    return results
