"""Two focused, offline reviewer checks; no model or database calls.

Run from the project root: PYTHONPATH=src .venv/bin/python scripts/reviewer_checks.py
Only artifacts/analysis/reviewer_checks.json is written. Archived inputs stay frozen.
"""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import platform
import random
import statistics
import time

from temporal_evidence.semantic.aliases import canonical_case
from temporal_evidence.semantic.scoring import score
from temporal_evidence.semantic.statistics import cluster_ratio, cluster_mean
from temporal_evidence.structure.program import updates
from temporal_evidence.structure.oracle import reference

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {}


def read(name):
    path = ROOT/name
    payload = path.read_bytes()
    INPUTS[name] = hashlib.sha256(payload).hexdigest()
    return json.loads(payload)


def evaluate(indices, clauses, state):
    for index in indices:
        state[index] = any(all(state[token] for token in witness)
                           for witness in clauses[index])
    return state


def exhaustive(initial, clauses, claim_indices, reverse, changes):
    state = initial.copy()
    for index, value in changes:
        state[index] = value
    return evaluate(claim_indices, clauses, state)


def selective(initial, clauses, claim_indices, reverse, changes):
    state = initial.copy()
    for index, value in changes:
        state[index] = value
    reached = set()
    agenda = [index for index, _ in changes]
    while agenda:
        for index in reverse.get(agenda.pop(), ()):
            if index not in reached:
                reached.add(index)
                agenda.append(index)
    return evaluate(sorted(reached), clauses, state)


def structural():
    prefix = 'artifacts/runs/structure_study_v1/'
    cases = read(prefix+'cases.json')
    rng = random.Random(20261108)
    rows = []
    for original in cases:
        case = canonical_case(original)
        filename = case['case_id']+'.json'
        candidate = read(prefix+'primitive_alias_replication/candidates/'+filename)
        archive = read(prefix+'primitive_alias_replication/replay/'+filename)
        claims = candidate['accepted']
        names = list(case['tests'])+[c['claim_id'] for c in claims]
        index = {name:i for i,name in enumerate(names)}
        claim_indices = list(range(len(case['tests']),len(names)))
        clauses, reverse = {}, defaultdict(set)
        for c in claims:
            cid = index[c['claim_id']]
            clauses[cid] = [[index[t] for t in w] for w in c['witnesses']]
            for witness in clauses[cid]:
                for token in witness:
                    assert token < cid
                    reverse[token].add(cid)
        initial = [True]*len(names)
        for condition in ['necessary','route_loss','benign','irrelevant']:
            revisions = updates(case,condition)
            truth = reference(case,case['events']+revisions,revisions[0]['ingested_at_seconds'])
            changed_logicals = {r['logical_id'] for r in revisions}
            changes = [(index[name],truth[name]) for name,test in case['tests'].items()
                       if test['logical_id'] in changed_logicals]
            args = initial,clauses,claim_indices,reverse,changes
            expected = [truth[c['proposition']] for c in claims]
            methods = {'all':exhaustive,'selective':selective}
            for method in methods.values():
                result = method(*args)
                assert [result[i] for i in claim_indices] == expected
            group = {r['method']:r for r in archive if r['condition']==condition}
            assert [group['M1']['states'][c['claim_id']] for c in claims] == expected
            # Verify that the visited-set schedule equals the archived graph traversal.
            reached = set(); agenda = [i for i,_ in changes]
            while agenda:
                for i in reverse.get(agenda.pop(),()):
                    if i not in reached: reached.add(i); agenda.append(i)
            assert {names[i] for i in reached} == set(group['M1']['scheduled_ids'])
            direct = set().union(*(reverse.get(i,set()) for i,_ in changes)) if changes else set()
            required = {index[c['claim_id']] for c in claims if not truth[c['proposition']]}
            assert len(required)==group['B1']['required_changes']
            assert len(required-direct)==group['B1']['missed_changes']
            timings = {name:[] for name in methods}
            for iteration in range(36):
                order = list(methods); rng.shuffle(order)
                for name in order:
                    tick = time.perf_counter_ns(); methods[name](*args)
                    elapsed = (time.perf_counter_ns()-tick)/1000
                    if iteration>=5: timings[name].append(elapsed)
            rows.append({'case_id':case['case_id'],'dataset':case['dataset'],
                'subject':case['subject'],'episode_id':case['episode_id'],'condition':condition,
                'required':len(required),'missed_direct':len(required-direct),
                'all_checks':len(claim_indices),'selective_checks':len(reached),
                'all_us':statistics.median(timings['all']),
                'selective_us':statistics.median(timings['selective'])})
    result = {}
    for label,subset in [('all_updates',rows),('excluding_irrelevant',[r for r in rows if r['condition']!='irrelevant'])]:
        total = sum(r['all_checks'] for r in subset)
        selected = sum(r['selective_checks'] for r in subset)
        result[label] = {'groups':len(subset),'all_checks':total,'selective_checks':selected,
            'avoided_fraction_pooled':(total-selected)/total,
            'median_all_us':statistics.median(r['all_us'] for r in subset),
            'median_selective_us':statistics.median(r['selective_us'] for r in subset)}
    result.update(required=sum(r['required'] for r in rows),
                  missed_direct=sum(r['missed_direct'] for r in rows),
                  missed_exhaustive=0,missed_selective=0,
                  identical_state_vectors=len(rows),cell_measurements=rows)
    assert result['required']==1294 and result['missed_direct']==208
    assert result['all_updates']['all_checks']==3636
    assert result['all_updates']['selective_checks']==2012
    result['archived_corrected_summary'] = read('artifacts/analysis/semantic_analysis_v1/primitive_alias_summary.json')
    result['timing_scope'] = ('In-memory compiled Boolean witness kernels; includes copying initial cached states, '
        'writing precomputed input truths, scheduling, AND/OR claim evaluation and cache writes. '
        'Excludes compilation, numerical feature lookup/evaluation, database I/O and generation. '
        'Five warmups and 31 randomized-order measurements per cell. Medians of per-cell medians; no database benchmark.')
    return result


def regeneration():
    temporal = read('artifacts/analysis/semantic_analysis_v1/temporal_checkpoints.json')
    old = {r['case_id']:r for r in temporal if r['method']=='M1' and r['position']=='maintained'}
    episodes = {}
    rows = []
    for cid,stop in sorted(old.items()):
        saved = read('artifacts/runs/minimum_v1/cases/'+cid+'.json')
        previous = read('artifacts/runs/minimum_v1/cases/'+stop['from_case_id']+'.json')
        assert {k:v for k,v in saved['query'].items() if k!='knowledge_time'} == {
            k:v for k,v in previous['query'].items() if k!='knowledge_time'}
        eid = stop['episode_id']
        if eid not in episodes: episodes[eid]=read('artifacts/prepared/'+eid+'.json')
        events = episodes[eid]['variants'][stop['variant']]['events']
        retained = [item['claim'] for rid,item in saved['persistent_before'].items()
                    if rid.startswith(stop['from_case_id']+'/claim/') and item['state'] in {'supported','unverified','pending'}]
        rescored = score(retained,events,saved['query'],remap_citations=True)
        assert all(rescored[k]==stop[k] for k in ['answerable','matched','grounded','emitted','empty'])
        fresh = score((saved.get('display') or {}).get('claims',[]),events,saved['query'],remap_citations=True)
        assert fresh['answerable']==stop['answerable']
        for stage,value in [('withdraw_stop',rescored),('fresh_checked',fresh)]:
            rows.append({**saved['case'],'stage':stage,
                **{k:value[k] for k in ['answerable','matched','grounded','emitted','empty']},
                'answerable_question':int(value['answerable']>0),
                'complete':int(value['answerable']>0 and value['matched']==value['answerable']),
                'generation_seconds':saved['seconds'] if stage=='fresh_checked' else 0,
                'requests':int(saved.get('initial') is not None)+int(saved.get('repair') is not None) if stage=='fresh_checked' else 0})
    assert len(rows)==960
    summaries=[]; gains=[]
    for dataset in ['synthetic','wesad','ppg_dalia']:
        grouped = {}
        for stage in ['withdraw_stop','fresh_checked']:
            group = [r for r in rows if r['dataset']==dataset and r['stage']==stage]
            grouped[stage]=group
            summaries.append({'dataset':dataset,'stage':stage,'transitions':len(group),
                **{k:sum(r[k] for r in group) for k in ['answerable','matched','grounded','emitted','empty','answerable_question','complete','requests']},
                'recall':cluster_ratio(group,'matched','answerable'),
                'precision':cluster_ratio(group,'grounded','emitted'),
                'median_archived_generation_seconds':statistics.median(r['generation_seconds'] for r in group)})
        episode_counts=defaultdict(lambda:defaultdict(lambda:[0,0]))
        for stage,group in grouped.items():
            for r in group:
                count=episode_counts[(r['subject'],r['episode_id'])][stage]
                count[0]+=r['matched']; count[1]+=r['answerable']
        paired=[]
        for (subject,eid),counts in episode_counts.items():
            a,b=counts['withdraw_stop'],counts['fresh_checked']
            assert a[1]==b[1] and a[1]>0
            paired.append({'dataset':dataset,'subject':subject,'episode_id':eid,'gain':b[0]/b[1]-a[0]/a[1]})
        gains.append({'dataset':dataset,'paired_recall_gain':cluster_mean(paired,'gain')})
    return {'summary':summaries,'paired_gains':gains,
        'scope':'All 480 M1 transitions (160 per source). Saved fresh checked answers to the identical later-time query are an offline regeneration proxy. No new model calls, candidate selection or online event-triggered policy test. Original generation times were measured on RTX 5090.',
        'uncertainty':'Episode-first subject-cluster bootstrap, 2000 resamples, seed 20260929; paired differences computed within episode before subject averaging.'}


def main():
    result={'structural':structural(),'regeneration':regeneration(),
        'execution':{'python':platform.python_version(),'platform':platform.platform(),
            'cpu':next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),platform.processor())},
        'input_sha256':INPUTS,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    target=ROOT/'artifacts/analysis/reviewer_checks.json'
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'input_sha256','script_sha256','structural'}},indent=2))
    print(json.dumps({k:v for k,v in result['structural'].items() if k not in {'cell_measurements','archived_corrected_summary'}},indent=2))


if __name__=='__main__': main()
