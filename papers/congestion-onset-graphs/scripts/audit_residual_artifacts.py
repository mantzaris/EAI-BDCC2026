"""Host-only file integrity, resource bookkeeping and dependency metadata."""
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re


def read(path):return json.loads(Path(path).read_text())
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')


def charge(path):
    rows=[json.loads(s) for s in Path(path).read_text().splitlines() if s.strip()]
    starts={r['job_id']:r for r in rows if r['event']=='start'}
    ends={r['job_id']:r for r in rows if r['event']=='finish'}
    assert starts.keys()==ends.keys(), 'Unfinished GPU reservation'
    assert all(r['returncode']==0 for r in ends.values())
    return sum(r['elapsed_seconds'] for r in ends.values()),len(starts)


def main():
    root=Path('results/residual_pilot/pilot01');out=Path('manifests/residual_pilot')
    old=read(out/'starting_state.json');changed=[]
    for path,expected in old['historical_hashes'].items():
        if sha(path)!=expected:changed.append(path)
    assert changed in ([],['README.md']), changed
    prior,_=charge('results/compute_ledger.jsonl');new,jobs=charge('results/residual_pilot/compute_ledger.jsonl')
    config=read('configs/residual_pilot.json');assert prior==config['resource']['prior_gpu_seconds']
    assert new<=14400 and prior+new<=86400
    runs={k:read(root/(k+'_run.json')) for k in ('audit','train','evaluate','verification')}
    assert all(v['complete'] and not v['test_access'] for v in runs.values())
    assert not read(root/'refinement_gate.json')['admitted']
    assert read(root/'checkpoint_replay.json')['passed']
    write(out/'compute_summary.json',dict(prior_project_gpu_job_seconds=prior,new_gpu_job_seconds=new,
        cumulative_project_gpu_job_seconds=prior+new,new_gpu_jobs=jobs,unfinished_jobs=0,refinement_gpu_seconds=0,
        unused_pilot_allowance_seconds=14400-new,remaining_provisional_project_seconds=86400-prior-new,
        cuda_event_span_seconds=sum(v['cuda_event_span_seconds'] for v in runs.values()),
        cuda_span_qualification='Includes host gaps; not active kernel time',
        profiled_audit_active_kernel_seconds=read(root/'gpu_checks.json')['profiled_kernel_seconds'],
        profiled_single_D_forward_active_kernel_seconds=read(root/'transfer_costs.json')['profiled_kernel_seconds'],
        full_campaign_active_kernel_seconds=None,no_new_authorization_implied=True))
    private=Path('data/processed/residual_pilot/pilot01')
    checkpoints={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(private.glob('*.pt'))}
    for attempt in read(root/'attempts.json'):
        assert checkpoints[attempt['name']+'.pt']['sha256']==attempt['checkpoint_sha256']
    integrity=read(root/'training_integrity.json')
    assert checkpoints['baseline.pt']['sha256']==integrity['baseline_checkpoint_sha256']
    assert checkpoints['normalization.pt']['sha256']==integrity['normalization_sha256']
    write(out/'checkpoints.json',dict(private_local_directory=str(private),
        private_pod_directory='/workspace/EAI-BDCC2026-residual/checkpoints/residual_pilot/pilot01',
        checkpoint_files=checkpoints,redistributed_in_git=False,source_sha=runs['train']['source_sha']))
    inputs={}
    for path in (config['raw_file'],config['input_archive']):
        p=Path(path);inputs[path]=dict(sha256=sha(p),bytes=p.stat().st_size,operation='Opaque byte hashing; no measurement decoding')
    assert inputs[config['raw_file']]['sha256']=='65d69fb0a2323dba9867179eb7af47c8b814186bc459ff0a4937d21614153c8f'
    assert inputs[config['input_archive']]['sha256']=='65afcc26e5c3ca971557167f9de1252533c7f9acb20fe417671898dadc202ea3'
    write(out/'inputs.json',dict(reused_inputs=inputs,new_dataset_downloads=0,
        test_outcomes_opened=False,original_provenance='manifests/pems_download.json',
        analysis_terms='Unresolved as documented in RESET_NOVELTY_AND_PROVENANCE.md; no identified ban is bypassed',
        raw_redistribution=False))
    links=[]
    for path in [Path('reports/RESIDUAL_PILOT_REPORT.md'),Path('reports/RESIDUAL_PILOT_PROTOCOL.md')]:
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if target.startswith(('https://','http://','#')):continue
            resolved=path.parent/target.split('#')[0]
            assert resolved.exists(),(str(path),target)
            links.append(dict(source=str(path),target=target))
    write(out/'artifact_verification.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        historical_files_checked=len(old['historical_hashes']),historical_changes=changed,local_links_checked=links,
        no_cpu_experiment=True,checkpoints_hash_matched=True,ledger_reconciled=True,
        matplotlib_rendering_version=importlib.metadata.version('matplotlib'),
        result_hashes={str(p):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}))
    print('Historical preservation, local links, checkpoint hashes and GPU ledgers verified.')


if __name__=='__main__':main()
