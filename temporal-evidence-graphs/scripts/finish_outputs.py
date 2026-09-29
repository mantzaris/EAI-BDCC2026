"""Finish the known launcher handoff and preserve completed study outputs.

This coordinator waits for the already-authorized experiment. It never starts a
second main runner and never changes the frozen protocol or requests extra cases.
"""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from temporal_evidence.io import read_json, utc_now, write_json


def process_arguments(pid):
    try:
        return (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    except FileNotFoundError:
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pipeline-pid', type=int, required=True)
    parser.add_argument('--primary-server-pid', type=int, required=True)
    args = parser.parse_args()
    status_path = 'artifacts/manifests/output_finalization.json'
    record = {'started_at': utc_now(), 'pipeline_pid': args.pipeline_pid,
              'primary_server_pid': args.primary_server_pid, 'state': 'waiting_for_pipeline'}
    write_json(status_path, record)
    print('Waiting for the existing main pipeline to exit', flush=True)
    while b'scripts/complete_study.py' in process_arguments(args.pipeline_pid):
        time.sleep(20)
    try:
        assert read_json('artifacts/runs/minimum_v1/completion.json')['accounted_cases'] == 3600
        systems = read_json('artifacts/streaming/streaming_v1/summary.json')
        assert len(systems['cells']) == 6 and systems['logical_parity']
        status = read_json('artifacts/manifests/execution_status.json')
        if status['stage'] != 'experiments_complete':
            # The running launcher's older process-name guard stops here. The
            # corrected launcher verifies the supplied primary process identity.
            assert status['stage'] == 'isolated_streaming_benchmark' and status['returncode'] == 0
            record['state'] = 'resuming_known_audit_handoff'
            write_json(status_path, record)
            subprocess.run([sys.executable, 'scripts/complete_study.py', '--audit-only',
                            '--primary-server-pid', str(args.primary_server_pid)], check=True)
        assert read_json('artifacts/audit/minimum_v1/summary.json')['sampled'] == 60
        subprocess.run([sys.executable, 'scripts/collect_database.py'], check=True)
        stopped = []
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():
                continue
            arguments = process_arguments(int(process.name))
            if b'scripts/monitor_resources.py' in arguments and b'artifacts/runs/resources.jsonl' in arguments:
                os.kill(int(process.name), signal.SIGTERM)
                stopped.append(int(process.name))
        record.update(state='reporting', stopped_resource_monitors=stopped)
        write_json(status_path, record)
        subprocess.run([sys.executable, '-m', 'temporal_evidence.analysis.publication'], check=True)
        record.update(state='complete', finished_at=utc_now())
        write_json(status_path, record)
        subprocess.run([sys.executable, 'scripts/backup_outputs.py', '--destination',
                        '/tmp/temporal-evidence-final-outputs.tar.gz', '--include', 'artifacts', 'paper/generated'], check=True)
        print('Complete outputs backed up; final paper interpretation and PDF checks remain', flush=True)
    except Exception as error:
        record.update(state='failed', error=repr(error), finished_at=utc_now())
        write_json(status_path, record)
        raise


if __name__ == '__main__':
    main()
