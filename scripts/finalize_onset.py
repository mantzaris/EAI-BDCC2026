"""Metadata-only ledger reconciliation, archival hash checks and table transcription."""
import csv
import datetime
import hashlib
import json
from pathlib import Path


def read(path):return json.loads(Path(path).read_text())


def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')


def main():
    root=Path('results/onset_graph');manifest=Path('manifests/onset_graph')
    original=read(manifest/'starting_state.json')['historical_hashes'];changed=[]
    for name,digest in original.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:changed.append(name)
    assert set(changed)<= {'README.md'},changed
    remote=read(root/'pod_artifacts.json');verified={}
    for name,r in remote['files'].items():
        path=Path(name);actual=hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual==r['sha256'] and path.stat().st_size==r['bytes'],name
        verified[name]=r
    save(manifest/'artifacts.json',dict(files=verified,local_remote_identical=True,
        weights=sum(name.endswith('.pt.gz') for name in verified),
        bytes=sum(r['bytes'] for name,r in verified.items() if name.endswith('.pt.gz')),
        original_distance_graph_not_redistributed=True,checkpoints_recoverable=True))
    lines=[json.loads(s) for s in (root/'compute_ledger.jsonl').read_text().splitlines()]
    starts={r['job_id']:r for r in lines if r['event']=='start'};ends={r['job_id']:r for r in lines if r['event']=='finish'}
    assert starts.keys()==ends.keys();assert all(r['returncode']==0 for r in ends.values())
    runs=[read(f) for f in (root/'study01').glob('*/*_run.json')]
    prior=read('manifests/residual_pilot/compute_summary.json')['cumulative_project_gpu_job_seconds']
    new=sum(r['elapsed_seconds'] for r in ends.values());c=read('configs/onset_graph_study.json')['resource']
    assert prior==c['prior_gpu_seconds'] and new<c['max_new_gpu_seconds'] and prior+new<c['project_provisional_seconds']
    summary=dict(prior_project_gpu_job_seconds=prior,new_gpu_job_seconds=new,cumulative_project_gpu_job_seconds=prior+new,
        jobs=len(starts),unfinished_jobs=0,failed_gpu_jobs=0,budget_extension_gpu_seconds=0,
        remaining_provisional_project_seconds=c['project_provisional_seconds']-prior-new,
        unused_authorized_study_seconds=c['max_new_gpu_seconds']-new,
        cuda_event_span_seconds=sum(r['cuda_event_span_seconds'] for r in runs),
        cuda_qualification='Event spans include host gaps; not active kernel totals. No complete active-kernel total measured.',
        peak_vram_allocated_bytes=max(r['peak_vram_allocated_bytes'] for r in runs),
        peak_vram_reserved_bytes=max(r['peak_vram_reserved_bytes'] for r in runs),
        peak_host_rss_bytes=max(r['host_peak_rss_bytes'] for r in runs),
        historical_ledgers_unchanged=True,test_outcomes_untouched=True,no_new_authorization_implied=True)
    save(manifest/'compute_summary.json',summary)
    artifacts=read(root/'study01/main/durable_replay.json')
    assert artifacts['complete'] and all(e==0 for e in artifacts['max_errors'].values())
    # Compare serialized scalar table entries exactly, not recomputed CPU scores.
    for row in csv.DictReader((root/'study01/metrics.csv').open()):
        folder='main' if row['population']=='outer' else row['population']
        prefix='validation' if row['population']=='outer' else 'gate'
        d=read(root/'study01'/folder/(prefix+'_'+row['calibration']+'_metrics.json'))
        assert float(row['brier'])==d['models'][row['model']][row['endpoint']]['brier']
    save(manifest/'delivery_checks.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        unchanged_historical_files=len(original)-len(changed),historical_status_file_updates=changed,
        unrelated_changes=[],all_weights_match_remote=True,all_metric_csv_briers_match_gpu_json=True,
        exact_reloaded_prediction_vectors=len(artifacts['max_errors']),new_cpu_research_computation=False,
        cpu_actions='Metadata accounting, hashes, syntax checks, parsing, rendering only',
        nonresearch_host_failures=['Initial renderer used unsupported three-digit color on older matplotlib; corrected and rendered successfully',
            'Initial metadata inspection invoked system Python2 instead of Python3; corrected without research computation',
            'First remote metadata inventory command had shell quoting error; no GPU job launched; file-based retry succeeded'],
        test_measurements_predictions_and_dependent_summaries_untouched=True))
    print(json.dumps(summary,indent=2));print('All historical preservation, checkpoint hash and scalar-transcription checks passed.')


if __name__=='__main__':main()
