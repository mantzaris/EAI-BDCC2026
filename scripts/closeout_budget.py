"""Run only the declared tiny algebra check under a persistent 300-second CPU cap."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


def main():
    cfg = json.loads(Path('configs/research_closeout.json').read_text())
    assert cfg['max_new_gpu_seconds'] == 0 and not cfg['stage3_enabled']
    directory = Path('results/closeout'); directory.mkdir(parents=True,exist_ok=True)
    with (directory/'compute_ledger.jsonl').open('a+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX); stream.seek(0)
        rows = [json.loads(line) for line in stream if line.strip()]
        finished = {r['job_id']:r for r in rows if r['event'] == 'cpu_finish'}
        used = sum(finished[r['job_id']]['elapsed_seconds'] if r['job_id'] in finished else r['reserved_seconds']
                   for r in rows if r['event'] == 'cpu_start')
        reserve = cfg['synthetic_job_timeout_seconds']
        if used+reserve > cfg['max_new_synthetic_cpu_seconds']: raise RuntimeError('Persistent CPU cap exceeded')
        def append(row):
            stream.seek(0,2); stream.write(json.dumps(row)+'\n'); stream.flush(); os.fsync(stream.fileno())
        job = uuid.uuid4().hex
        append(dict(event='cpu_start', job_id=job, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            reserved_seconds=reserve, prior_charged_seconds=used, gpu_seconds=0,
            command=[sys.executable,'scripts/closeout_algebra.py'],
            source_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            script_sha256=hashlib.sha256(Path('scripts/closeout_algebra.py').read_bytes()).hexdigest()))
        started=time.perf_counter(); status=1
        try:
            env=dict(os.environ, CUDA_VISIBLE_DEVICES='')
            result=subprocess.run([sys.executable,'scripts/closeout_algebra.py'],env=env,timeout=reserve)
            status=result.returncode
        finally:
            append(dict(event='cpu_finish',job_id=job,elapsed_seconds=time.perf_counter()-started,
                        returncode=status,gpu_seconds=0,cuda_seconds=0))
        if status: raise SystemExit(status)


if __name__ == '__main__': main()
