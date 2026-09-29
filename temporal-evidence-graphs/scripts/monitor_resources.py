"""One-second GPU/host samples; stop by interrupting this dedicated process."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from datetime import datetime,timezone

parser=argparse.ArgumentParser()
parser.add_argument("--output",required=True)
args=parser.parse_args()
path=Path(args.output)
path.parent.mkdir(parents=True,exist_ok=True)
while True:
    started=time.monotonic()
    result=subprocess.check_output(["nvidia-smi","--query-gpu=memory.used,memory.total,utilization.gpu,power.draw",
                                    "--format=csv,noheader,nounits"],text=True)
    values=[float(value.strip()) for value in result.strip().split(",")]
    report={"time":datetime.now(timezone.utc).isoformat(),"memory_used_mib":values[0],"memory_total_mib":values[1],
            "gpu_utilization_percent":values[2],"power_watts":values[3]}
    memory=Path("/sys/fs/cgroup/memory.current")
    report["host_cgroup_memory_bytes"]=int(memory.read_text()) if memory.exists() else None
    with path.open("a") as stream:
        stream.write(json.dumps(report)+"\n")
    time.sleep(max(0,1-(time.monotonic()-started)))
