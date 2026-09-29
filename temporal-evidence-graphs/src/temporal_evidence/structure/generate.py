"""One common GPU candidate per structural case, with one bounded repair."""
import argparse
import asyncio
import json
from pathlib import Path
import time
import httpx
from temporal_evidence.io import read_json,write_json,append_journal,read_journal,digest_file,utc_now
from temporal_evidence.structure.program import ProgramAnswer,validate

ROOT=Path("artifacts/runs/structure_study_v1")
SYSTEM="""You explain explicit numerical rules on recorded features, without diagnoses.
Return compact JSON with exactly claims and explanation. A claim has claim_id,
proposition, value (boolean), witnesses (array of nonempty arrays of input tokens),
sentence. Each witness is AND; the list of witnesses is OR. Inputs may be test IDs
or earlier claim_id values. Never invent tests or proposition names. A claim means
exactly its supplied proposition definition, regardless of your chosen witnesses.
Use only provided measurements. Preserve units and time labels if stating numbers.
Explain the requested grouping through intermediate propositions where appropriate,
then include the answer proposition. Use at most 16 claims. Direct test citations
are allowed. Alternative witnesses must use distinct eligible recording windows.
The explanation must equal the claim sentences joined with single spaces. No extra
interpretations, clinical claims or discussion of this instruction. JSON only.
"""


def messages(case):
    prefixes={1:[],2:[4],3:[2,4],4:[1,2,4]}[case["intended_depth"]]
    planned=[f"{r}_first_{n}" for r in case["routes"] for n in prefixes]+["answer"]
    payload={"task":"Determine whether at least one eligible recording window satisfies all four specified numerical comparisons.",
        "dataset":case["dataset"],"subject":case["subject"],"knowledge_time":case["knowledge_time"],
        "intended_evidence_to_answer_depth":case["intended_depth"],"requested_propositions_in_order":planned,
        "grouping_instruction":"For each route, use the preceding prefix claim and remaining tests; the answer may use complete-route claims. At depth 1 cite tests directly.",
        "tests":{k:{kk:v for kk,v in t.items() if kk not in {"margin","observation_ids","logical_id"}} for k,t in case["tests"].items()},
        "proposition_definitions_OR_of_AND_tests":case["propositions"]}
    return [{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps(payload,separators=(",",":"))}]


async def run(pilot=False):
    gates=read_json(ROOT/"pre_inference_gates.json"); assert gates["passed"]
    placement=read_json(ROOT/"gpu_placement.json")
    assert placement["first_forward_tensor_devices"] and all(d.startswith("cuda") for d in placement["parameter_devices"])
    cases=read_json(ROOT/("pilot_cases.json" if pilot else "cases.json")); name="pilot_v1" if pilot else "core"
    directory=ROOT/name; directory.mkdir(parents=True,exist_ok=True); (directory/"candidates").mkdir(exist_ok=True)
    config={"model":"Qwen/Qwen3-8B","temperature":.7,"top_p":.8,"top_k":20,"seed":20260929,
        "max_tokens":4096,"max_input_tokens":8192,"concurrency":4,"max_calls":2*len(cases)}
    sources={str(p):digest_file(p) for p in sorted(Path("src/temporal_evidence/structure").glob("*.py"))}
    freeze={"config":config,"sources":sources,"cases_sha256":digest_file(ROOT/("pilot_cases.json" if pilot else "cases.json")),
        "schema":ProgramAnswer.model_json_schema(),"system_prompt":SYSTEM}
    if (directory/"frozen.json").exists(): assert read_json(directory/"frozen.json")==freeze
    else: write_json(directory/"frozen.json",freeze)
    journal_path=directory/"requests.jsonl"; existing={}
    if journal_path.exists():
        for row in read_journal(journal_path): existing[(row["case_id"],row["phase"])]=row
    semaphore=asyncio.Semaphore(4); start=time.perf_counter()
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000",timeout=240) as client:
        async def call(case_id,prompt,phase):
            request={k:v for k,v in config.items() if k not in {"max_input_tokens","concurrency","max_calls"}}
            request.update(messages=prompt,guided_json=ProgramAnswer.model_json_schema(),chat_template_kwargs={"enable_thinking":False})
            key=(case_id,phase)
            if key in existing:
                row=existing[key]; assert row["request"]==request
                if row["event"]!="finished":
                    row={**row,"event":"finished","error":"interrupted_request_unknown_outcome","seconds":None}; append_journal(journal_path,row)
                answer=None if row.get("error") else ProgramAnswer.model_validate_json(row["response"]["choices"][0]["message"]["content"]).model_dump()
                return answer,row
            row={"case_id":case_id,"phase":phase,"request":request,"started_at":utc_now(),"event":"started"}
            append_journal(journal_path,row); tick=time.perf_counter(); answer=None
            try:
                response=await client.post("/v1/chat/completions",json=request); row["http_status"]=response.status_code; response.raise_for_status()
                row["response"]=response.json(); choice=row["response"]["choices"][0]
                if choice["finish_reason"]=="length": raise ValueError("truncated_output")
                if row["response"].get("usage",{}).get("prompt_tokens",0)>8192: raise ValueError("input_budget_exceeded")
                answer=ProgramAnswer.model_validate_json(choice["message"]["content"]).model_dump()
            except (httpx.HTTPError,ValueError,KeyError) as error: row["error"]=f"{type(error).__name__}: {str(error)[:1000]}"
            row.update(event="finished",seconds=time.perf_counter()-tick,finished_at=utc_now()); append_journal(journal_path,row); existing[key]=row
            return answer,row
        async def one(case):
            path=directory/"candidates"/(case["case_id"]+".json")
            if path.exists(): return read_json(path)
            async with semaphore:
                prompt=messages(case); raw,initial=await call(case["case_id"],prompt,"initial"); candidate=raw
                accepted,decisions=validate(candidate,case); repair=None
                has_answer=any(c["proposition"]=="answer" for c in accepted)
                paragraph=bool(candidate and candidate["explanation"].strip()!=" ".join(c["sentence"] for c in candidate["claims"]).strip())
                if candidate is None or not has_answer or any(not d["accepted"] for d in decisions) or paragraph:
                    critique={"format_error":initial.get("error"),"validation":decisions,"missing_answer":not has_answer,"paragraph_mismatch":paragraph}
                    repair_prompt=prompt+([{"role":"assistant","content":json.dumps(candidate,separators=(",",":"))}] if candidate else [])
                    repair_prompt += [{"role":"user","content":"One repair: correct these checks using the same evidence. "+json.dumps(critique,separators=(",",":"))}]
                    candidate,repair=await call(case["case_id"],repair_prompt,"repair"); accepted,decisions=validate(candidate,case)
                result={"case_id":case["case_id"],"raw_candidate":raw,"final_candidate":candidate,"accepted":accepted,"decisions":decisions,
                    "initial":initial,"repair":repair,"completed_at":utc_now(),"origin":"GPU_model_proposal",
                    "adequate_answer":any(c["proposition"]=="answer" for c in accepted)}
                write_json(path,result); print(f"{name}: {len(list((directory/'candidates').glob('*.json')))}/{len(cases)}",flush=True)
                return result
        results=await asyncio.gather(*(one(c) for c in cases))
    calls=[call for r in results for call in (r["initial"],r.get("repair")) if call]
    summary={"cases":len(results),"calls":len(calls),"repairs":sum(r["repair"] is not None for r in results),
        "adequate_answers":sum(r["adequate_answer"] for r in results),"format_failures":sum(r["final_candidate"] is None for r in results),
        "invocation_wall_seconds":time.perf_counter()-start,"finished_at":utc_now(),
        "input_tokens":sum(c.get("response",{}).get("usage",{}).get("prompt_tokens",0) for c in calls),
        "output_tokens":sum(c.get("response",{}).get("usage",{}).get("completion_tokens",0) for c in calls),
        "unknown_usage":sum("usage" not in c.get("response",{}) for c in calls)}
    assert len(calls)<=config["max_calls"]; write_json(directory/"completion.json",summary); print(summary,flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--pilot",action="store_true"); a=p.parse_args(); asyncio.run(run(a.pilot))
