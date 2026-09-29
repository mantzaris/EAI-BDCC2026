"""Run the authorized bounded core after the development and semantic gates."""
import asyncio
from pathlib import Path
import subprocess
import sys
from temporal_evidence.io import read_json,write_json,utc_now
from temporal_evidence.structure.generate import run
from temporal_evidence.structure.replay import run as replay

root=Path("artifacts/runs/structure_study_v1")
pilot=read_json(root/"pilot_v2/completion.json")
parity=read_json(root/"pilot_v2_replay/completion.json")
assert pilot["cases"]==12 and pilot["format_failures"]==0 and pilot["calls"]<=24
assert parity["cases"]==12 and parity["cells"]==480
assert read_json(root/"pre_inference_gates.json")["passed"]
write_json(root/"core_launch.json",{"started_at":utc_now(),"pilot_v2":pilot,
    "estimated_generation_seconds":pilot["invocation_wall_seconds"]*20,
    "choice":"Use clarified development prompt; preserve semantic failures and realized structures. No further tuning.",
    "maximum_core_calls":480,"post_correction_generation_calls":0})
monitor=subprocess.Popen([sys.executable,"scripts/monitor_resources.py","--output",str(root/"resources.jsonl")],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    asyncio.run(run())
    replay()
finally:
    monitor.terminate(); monitor.wait(timeout=10)
write_json(root/"completed.json",{"finished_at":utc_now(),"core":read_json(root/"core/completion.json"),"replay":read_json(root/"replay/completion.json")})
