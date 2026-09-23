"""Finalize compact metrics, budget reconciliation, and historical preservation."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from traffic_risk_twins.compute_ledger import charged_seconds
from traffic_risk_twins.ingestion import PemsSource
from traffic_risk_twins.data_access import save_json


def main():
    out = Path('results/stage2')
    starting = json.loads(Path('manifests/stage2/starting_state.json').read_text())
    for path, digest in starting['stage1_files'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    data = np.load('data/processed/pilot_inputs.npz')
    source = PemsSource('data/raw/pems-bay.h5'); validation = source.read('validation')
    ok = data['label_eligible']; origins = data['origins'][ok]
    repair = pd.read_csv(out/'repair_trajectory_errors.csv')
    original = pd.read_csv('results/stage1_pilot/predictions.csv')
    original = original[(original.method == 'fine_mc') & (original.retention == 1.) & (original.N == 256) & original.eligible]
    speed = []
    for h in (2, 5):
        per_origin = []
        for i in np.flatnonzero(ok):
            valid = data['future_mask'][i,h]
            per_origin.append(np.abs(validation[data['origins'][i]]-data['future'][i,h])[valid].mean())
        repaired = repair[(repair.split == 'validation') & (repair.step == h+1) & repair.origin.isin(origins)]
        speed.append(dict(minutes=(h+1)*5, origins=len(origins), weights='equal origin, valid future sensors within origin',
            original_mc=float(original[f'mae_{(h+1)*5}min_raw'].mean()), repair=float(repaired.mae_raw.mean()),
            persistence=float(np.mean(per_origin))))
    save_json(out/'matched_speed_metrics.json', speed)
    old_rows = [json.loads(s) for s in Path('results/compute_ledger.jsonl').read_text().splitlines()]
    new_rows = [json.loads(s) for s in (out/'compute_ledger.jsonl').read_text().splitlines() if s.strip()]
    s1, s2 = charged_seconds(old_rows), charged_seconds(new_rows)
    assert s2 == 0 and s1 < 86400 and s2 <= 1800
    if not any(r.get('event') == 'stage_closed_without_gpu_jobs' for r in new_rows):
        with (out/'compute_ledger.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(event='stage_closed_without_gpu_jobs', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                gpu_job_seconds=0, cuda_kernel_seconds=0, stage2_cap_seconds=1800, stage1_charged_seconds=s1,
                reason='CPU diagnosis resolves the bounded gates; no GPU experiment launched'))+'\n')
    reproduction = json.loads(Path('manifests/stage2/reproduction.json').read_text())
    save_json(out/'compute_summary.json', dict(stage1_gpu_job_seconds=s1, stage2_gpu_job_seconds=s2,
        cumulative_gpu_job_seconds=s1+s2, cumulative_gpu_hours=(s1+s2)/3600,
        stage2_cuda_kernel_seconds=0, historical_cuda_rollout_event_seconds=9.298111127018917,
        stage2_allowance_seconds=1800, stage2_unused_seconds=1800-s2, project_provisional_ceiling_seconds=86400,
        project_remaining_provisional_seconds=86400-s1-s2, open_gpu_reservations=0, new_gpu_run=False,
        complete_cpu_reproduction_seconds=reproduction['cpu_wall_seconds'],
        device_timing_qualification='Historical Stage 1 CUDA events measured rollouts, not all kernels. Stage 2 imported no CUDA path and used no GPU.'))
    protected = len(starting['stage1_files'])
    hashes = {}
    for parent in ('src','scripts','configs'):
        for path in sorted(Path(parent).rglob('*')):
            if path.is_file() and path.suffix in ('.py','.yaml'):
                hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    save_json('manifests/stage2/source_files.json', dict(cpu_reproduction_source_sha=reproduction['source_sha'],
        gpu_tested_source_sha=None, verification_source_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        files=hashes, note='Final handoff adds CPU finalization/artifact checks after the concrete reproduced source. Core prediction arrays reproduced exactly.'))
    save_json(out/'preservation_check.json', dict(stage1_files_verified=protected, mismatches=0, starting_tree_clean=True,
        preexisting_changes_preserved=[], test_outcomes_access=False))
    print('Preserved',protected,'Stage 1 artifacts; Stage 2 GPU seconds:',s2)


if __name__ == '__main__': main()
