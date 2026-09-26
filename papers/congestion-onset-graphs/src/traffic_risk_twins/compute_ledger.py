"""Append-only reservations survive interruptions; no restart resets the budget."""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid
import fcntl


def charged_seconds(rows):
    finishes = {r['job_id']:r for r in rows if r['event'] == 'finish'}
    return sum(finishes[r['job_id']]['elapsed_seconds'] if r['job_id'] in finishes else r['reserved_seconds']
               for r in rows if r['event'] == 'start')


def run_budgeted(ledger, command, reserve_seconds, cap=7200):
    ledger = Path(ledger)
    ledger.parent.mkdir(parents=True,exist_ok=True)
    if not 0 < reserve_seconds <= cap <= 7200:
        raise ValueError('Stage 1 cap cannot exceed 7200 seconds')
    with ledger.open('a+') as stream:
        # Hold exclusive ledger lock throughout the child; concurrent jobs cannot race.
        fcntl.flock(stream,fcntl.LOCK_EX)
        stream.seek(0)
        rows = [json.loads(line) for line in stream if line.strip()]
        used = charged_seconds(rows)
        if used+reserve_seconds > cap:
            raise RuntimeError('GPU reservation exceeds remaining cumulative budget')
        job = uuid.uuid4().hex
        def append(row):
            stream.seek(0,2); stream.write(json.dumps(row)+'\n'); stream.flush(); os.fsync(stream.fileno())
        append(dict(event='start',job_id=job,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    reserved_seconds=reserve_seconds,prior_charged_seconds=used,command=command))
        start = time.monotonic()
        proc = None
        code = 1
        try:
            proc = subprocess.Popen(command,start_new_session=True)
            code = proc.wait(timeout=reserve_seconds)
        except BaseException:
            if proc is not None:
                os.killpg(proc.pid,signal.SIGTERM)
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL); proc.wait()
            raise
        finally:
            elapsed = time.monotonic()-start
            append(dict(event='finish',job_id=job,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        elapsed_seconds=elapsed,returncode=code))
        return code
