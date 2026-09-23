"""Read-only checks of saved development artifacts; never opens measurement files."""
import argparse
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def snapshot():
    target = Path('manifests/closeout/starting_state.json')
    if target.exists(): raise FileExistsError('Do not reset the historical snapshot')
    sha = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    assert sha == read('configs/research_closeout.json')['starting_commit']
    paths = subprocess.check_output(['git','ls-tree','-r','--name-only',sha],text=True).splitlines()
    hashes = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
    save(target, dict(starting_commit=sha, inspected_utc='2026-09-23T04:26:41Z',
        branch='main',origin='https://www.github.com/mantzaris/EAI-BDCC2026',
        preexisting_tracked_changes=[],preexisting_untracked_changes=[],applicable_agents=[],
        no_remote_advance=True, files=hashes, permitted_status_update=['README.md']))


def evidence():
    panel = {r['origin']:r for r in rows('results/stage2/validation_panel.csv')}
    assert len(panel) == 128
    classifier = rows('results/stage2/matched_predictions.csv')
    simulator = rows('results/stage2/simulator_predictions.csv')
    assert {r['split'] for r in classifier} == {'validation','inner_calibration'}
    assert {r['split'] for r in simulator} == {'validation'}
    frames = {name:[r for r in classifier if r['model']==name and r['split']=='validation'] for name in ('A','B','C')}
    frames.update({name:[r for r in simulator if r['model']==name] for name in ('original','location_repair')})
    metrics={}; compact=rows('results/stage2/predictive_metrics.csv')
    for name, group in frames.items():
        assert len(group)==128 and {r['origin'] for r in group}==set(panel)
        for r in group:
            for key in ('label','eligible','current_active','day'):
                assert r[key] == panel[r['origin']][key], (name,key,r['origin'])
            if name in ('original','location_repair'):
                assert int(r['N'])==256 and float(r['probability'])*256==round(float(r['probability'])*256)
        metrics[name]={}
        for kind in ('probability','calibrated_probability'):
            for subset in ('all_time','onset'):
                selected=[r for r in group if r['eligible']=='True' and (subset=='all_time' or r['current_active']=='False')]
                positives=sum(int(r['label']) for r in selected)
                score=math.fsum((float(r[kind])-int(r['label']))**2 for r in selected)/len(selected)
                threshold='alarm_threshold' if kind=='probability' else 'calibrated_alarm_threshold'
                tp=sum(float(r[kind])>=float(r[threshold]) and r['label']=='1' for r in selected)
                fp=sum(float(r[kind])>=float(r[threshold]) and r['label']=='0' for r in selected)
                model=name if name in ('A','B','C') else 'simulator_'+name
                ref=next(r for r in compact if r['model']==model and r['probability_kind']==kind and r['subset']==subset)
                assert abs(score-float(ref['brier']))<1e-14
                assert [len(selected),positives,tp,fp]==[int(ref[k]) for k in ('n','positives','tp','fp')]
                metrics[name][kind+'_'+subset]=dict(n=len(selected),positives=positives,brier=score,tp=tp,fp=fp,
                    days=len({r['day'] for r in selected}),event_days=len({r['day'] for r in selected if r['label']=='1'}))
    s1=rows('results/stage1_pilot/predictions.csv'); old={}
    for retention in ('0.0','0.15','1.0'):
        group=[r for r in s1 if r['method']=='fine_mc' and r['retention']==retention and int(r['N'])==1024]
        assert len(group)==128
        for r in group:
            assert all(r[k]==panel[r['origin']][k] for k in ('label','eligible','current_active','day'))
        eligible=[r for r in group if r['eligible']=='True']
        old[retention]=dict(n=len(eligible),brier=math.fsum((float(r['probability'])-int(r['label']))**2 for r in eligible)/len(eligible),
                            expected_mc_bound=1/(4*1024))
    widths=read('results/stage2/tightening_summary.json')
    assert all(v['unresolved']==1 for v in widths['width_by_retention'].values())
    ratios=[r['tightened_selective']/r['fine'] for r in widths['repeat_timings']]
    assert len(ratios)==5 and min(ratios)>1.1
    oldledger=[json.loads(line) for line in Path('results/compute_ledger.jsonl').read_text().splitlines()]
    starts={r['job_id'] for r in oldledger if r['event']=='start'}
    finishes={r['job_id']:r for r in oldledger if r['event']=='finish'}
    assert starts==set(finishes)
    gpu=sum(r['elapsed_seconds'] for r in finishes.values())
    assert gpu==read('results/stage2/compute_summary.json')['cumulative_gpu_job_seconds']
    assert '31 passed' in Path('results/stage2/regression_tests.txt').read_text()
    reproduction=read('manifests/stage2/reproduction.json')
    assert reproduction['complete'] and all(j['returncode']==0 for j in reproduction['jobs'])
    assert max(reproduction['maximum_differences'].values())==0
    save('results/closeout/evidence_audit.json',dict(metrics=metrics,stage1_fine_n1024=old,
        tightened_selective_time_ratios=ratios, cumulative_gpu_seconds=gpu,
        common_origins_labels_masks_and_onset=True, equal_origin_weights=True,
        compared_information_differs_by_design=True, equal_wire_bytes_or_equal_time_established=False,
        historical_tests_passed=31,new_regression_tests_run=False,historical_cpu_reproduction_exact=True,
        saved_support=read('results/stage2/development_support.json'),
        saved_pairs=read('results/stage2/matched_pairs.json'),
        model_fits=0,new_predictions=0,measurement_files_read=0,test_access=False))


def delivery():
    old=read('manifests/closeout/starting_state.json')
    changed=[p for p,d in old['files'].items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=d]
    assert changed==['README.md'] or changed==[]
    output=Path('results/closeout/delivery_verification.json')
    local_targets=[]
    for path in [Path('README.md'),Path('reports/CAMPAIGN_CLOSEOUT.md'),Path('reports/RESEARCH_RESET.md'),
                 Path('reports/RESET_NOVELTY_AND_PROVENANCE.md')]:
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if '://' not in link and not link.startswith('#'):
                target=path.parent/link.split('#')[0]
                local_targets.append(target)
                # This report may link to the verification being created now.
                assert target.exists() or target.resolve()==output.resolve(),(str(path),link)
    assert not Path('reports/RESTART_PROTOCOL.md').exists()
    assert read('configs/research_closeout.json')['max_new_gpu_seconds']==0
    assert 'selective_refinement_enabled: false' in Path('configs/stage2_diagnosis.yaml').read_text()
    for model,pretty in [('A','0.02646'),('B','0.03061'),('C','0.03046'),('location_repair','0.03360')]:
        actual=read('results/closeout/evidence_audit.json')['metrics'][model]['probability_all_time']['brier']
        assert format(actual,'.5f')==pretty and pretty in Path('reports/CAMPAIGN_CLOSEOUT.md').read_text()
    ledger=[json.loads(line) for line in Path('results/closeout/compute_ledger.jsonl').read_text().splitlines()]
    starts={r['job_id'] for r in ledger if r['event']=='cpu_start'}
    ends={r['job_id']:r for r in ledger if r['event']=='cpu_finish'}
    assert starts==set(ends) and all(r['returncode']==0 for r in ends.values())
    seconds=sum(r['elapsed_seconds'] for r in ends.values());assert seconds<300
    assert all(r.get('gpu_seconds',0)==0 for r in ledger)
    save(output,dict(passed=True,historical_files=len(old['files']),
        historical_files_unchanged_except_status=changed,preserved_artifacts=len(old['files'])-len(changed),
        required_local_links_valid=True,numerical_transcription_valid=True,synthetic_cpu_job_seconds=seconds,
        new_gpu_seconds=0,cumulative_gpu_seconds=read('results/closeout/evidence_audit.json')['cumulative_gpu_seconds'],
        source_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        audit_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),test_access=False))
    assert all(target.exists() for target in local_targets)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('snapshot','evidence','delivery'))
    mode=parser.parse_args().mode;start=time.perf_counter()
    success=False
    try:
        globals()[mode]()
        success=True
    finally:
        elapsed=time.perf_counter()-start
        directory=Path('results/closeout');directory.mkdir(parents=True,exist_ok=True)
        with (directory/'artifact_audit_ledger.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(mode=mode,elapsed_seconds=elapsed,gpu_seconds=0,
                utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                success=success,measurement_files_read=0))+'\n')
    print(mode,'completed in',round(elapsed,6),'seconds; no measurement data opened.')


if __name__=='__main__': main()
