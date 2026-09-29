"""Every request and error is retained; there is no CPU or remote API fallback."""
from __future__ import annotations
import json
import time
import httpx
from pydantic import ValidationError
from temporal_evidence.generation.contract import Answer
from temporal_evidence.generation.prompts import messages
from temporal_evidence.io import append_journal,read_json,read_journal,utc_now
from pathlib import Path
from temporal_evidence.validation.checker import validate,safe_display


class GPUClient:
    def __init__(self, config, base_url="http://127.0.0.1:8000", log_path="artifacts/runs/requests.jsonl"):
        placement=read_json("artifacts/manifests/gpu_placement.json")
        assert placement["first_forward_tensor_devices"] and all(d.startswith("cuda") for d in placement["parameter_devices"])
        self.config=config
        self.client=httpx.AsyncClient(base_url=base_url,timeout=httpx.Timeout(180.0,connect=10.0))
        self.log_path=log_path
        self.journal={}
        if Path(log_path).exists():
            for item in read_journal(log_path):
                self.journal[(item["case_id"],item["phase"])]=item

    async def generate(self, case_id, prompt, phase="initial"):
        model=self.config["model"]
        request={"model":model["name"],"messages":prompt,"temperature":model["temperature"],"top_p":model["top_p"],
                 "top_k":model["top_k"],"max_tokens":model["max_output_tokens"],"seed":self.config["generation_seed"],
                 "chat_template_kwargs":{"enable_thinking":False},"guided_json":Answer.model_json_schema()}
        key=(case_id,phase)
        if key in self.journal:
            previous=dict(self.journal[key])
            if previous["request"] != request:
                raise ValueError("A resumed request differs from its journal; use a new development run ID")
            if previous.get("event")=="started":
                previous.update(error="interrupted_request_unknown_outcome",seconds=0.,event="finished")
                append_journal(self.log_path,previous)
                self.journal[key]=previous
            if previous.get("error"):
                return None,previous
            return Answer.model_validate_json(previous["response"]["choices"][0]["message"]["content"]),previous
        started=time.perf_counter()
        record={"case_id":case_id,"phase":phase,"started_at":utc_now(),"request":request,"event":"started"}
        append_journal(self.log_path,record)
        answer=None
        try:
            response=await self.client.post("/v1/chat/completions",json=request)
            record["http_status"]=response.status_code
            response.raise_for_status()
            payload=response.json()
            record["response"]=payload
            choice=payload["choices"][0]
            record["truncated"]=choice["finish_reason"]=="length"
            answer=Answer.model_validate_json(choice["message"]["content"])
            if record["truncated"]:
                record["error"]="output_truncated"
                answer=None
            if payload.get("usage",{}).get("prompt_tokens",0)>model["max_input_tokens"]:
                record["error"]="input_budget_exceeded"
                answer=None
        except (httpx.HTTPError,ValueError,KeyError,ValidationError) as error:
            record["error"]=f"{type(error).__name__}: {str(error)[:1000]}"
        record["seconds"]=time.perf_counter()-started
        record["event"]="finished"
        append_journal(self.log_path,record)
        self.journal[key]=record
        return answer,record

    async def answer(self,case_id,method,query,evidence,records,previous=None):
        prompt=messages(query,evidence,previous)
        candidate,initial=await self.generate(case_id,prompt)
        result={"initial":initial,"repair":None,"raw_candidate":None if candidate is None else candidate.model_dump()}
        decisions,paragraph=([],[]) if candidate is None or method=="B0" else validate(candidate,records,query)
        if method!="B0" and (candidate is None or paragraph or any(d.state!="supported" for d in decisions)):
            critique={"validation":[d.to_dict() for d in decisions],"paragraph":paragraph,
                      "format_error":initial.get("error")}
            repair_prompt=prompt+([{"role":"assistant","content":candidate.model_dump_json()}] if candidate else [])
            repair_prompt += [{"role":"user","content":"Repair this answer using only the same evidence. Checks: "+json.dumps(critique)}]
            candidate,repair=await self.generate(case_id,repair_prompt,"repair")
            result["repair"]=repair
            decisions,paragraph=([],[]) if candidate is None else validate(candidate,records,query)
        result.update(validation=[d.to_dict() for d in decisions],paragraph_discrepancies=paragraph,
                      final_candidate=None if candidate is None else candidate.model_dump(),
                      display=None if candidate is None else (candidate.model_dump() if method=="B0" else safe_display(candidate,decisions)),
                      seconds=initial["seconds"]+(result["repair"]["seconds"] if result["repair"] else 0))
        return result

    async def close(self):
        await self.client.aclose()
