"""Persistent, locked GPU-job reservations for the authorized frozen final evaluation."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid


def charged(rows,phase=None):
    ends={r['job_id']:r for r in rows if r['event']=='finish'}
    return sum(ends[r['job_id']]['elapsed_seconds'] if r['job_id'] in ends else r['reserved_seconds']
               for r in rows if r['event']=='start' and (phase is None or r['phase']==phase))


def main():
    p=argparse.ArgumentParser();p.add_argument('--reserve',type=int,required=True)
    p.add_argument('--phase',choices=['verification','evaluation','replay'],required=True);p.add_argument('--source-sha',required=True)
    p.add_argument('command',nargs=argparse.REMAINDER);args=p.parse_args()
    command=args.command[1:] if args.command and args.command[0]=='--' else args.command
    c=json.loads(Path('configs/final_test_manifest.json').read_text())['resource']
    ledger=Path('results/final_test/compute_ledger.jsonl');ledger.parent.mkdir(parents=True,exist_ok=True)
    with ledger.open('a+') as out:
        fcntl.flock(out,fcntl.LOCK_EX);out.seek(0)
        rows=[json.loads(line) for line in out if line.strip()]
        total=charged(rows);phase=charged(rows,args.phase)
        phase_cap=c['max_new_gpu_seconds']
        assert 0<args.reserve and command
        if total+args.reserve>c['max_new_gpu_seconds'] or phase+args.reserve>phase_cap or total+args.reserve+c['prior_gpu_seconds']>c['project_provisional_seconds']:
            raise RuntimeError('Reservation exceeds persistent pilot/phase/project budget')
        def append(value):
            out.seek(0,2);out.write(json.dumps(value)+'\n');out.flush();os.fsync(out.fileno())
        job=uuid.uuid4().hex
        append(dict(event='start',job_id=job,phase=args.phase,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    reserved_seconds=args.reserve,prior_new_seconds=total,prior_project_seconds=c['prior_gpu_seconds']+total,
                    source_sha=args.source_sha,command=command))
        started=time.monotonic();process=None;code=1;reason=None
        try:
            env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',PYTHONPATH='src',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',CUBLAS_WORKSPACE_CONFIG=':4096:8')
            process=subprocess.Popen(command,env=env,start_new_session=True)
            code=process.wait(timeout=args.reserve)
        except BaseException as error:
            reason=type(error).__name__
            if process is not None and process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait()
            raise
        finally:
            append(dict(event='finish',job_id=job,phase=args.phase,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        elapsed_seconds=time.monotonic()-started,returncode=code,error=reason))
        raise SystemExit(code)


if __name__=='__main__':main()
