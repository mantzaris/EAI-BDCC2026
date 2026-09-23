"""CPU-only dense/CSR comparison after GPU jobs finish; identical saved scenarios."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import time
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from threadpoolctl import threadpool_limits
from traffic_risk_twins.conditional_history import GaussianHistory
from traffic_risk_twins.scenarios import make_scenarios
from traffic_risk_twins.graph_dynamics import rollout
from traffic_risk_twins.event_functionals import event
from traffic_risk_twins.scenario_estimators import bernoulli_summary
from traffic_risk_twins.data_access import save_json


def sparse_rollout(initial,forcing,W,coefficients):
    previous,current=initial[:,-2].copy(),initial[:,-1].copy()
    a0,a1,beta,gamma=coefficients
    states=[]
    for h in range(forcing.shape[1]):
        neighbor=(W@current.T).T
        nxt=a0*current+a1*previous+beta*neighbor+gamma*np.maximum(neighbor,0)+forcing[:,h]
        states.append(nxt);previous,current=current,nxt
    return np.stack(states,axis=1)


def main(args):
    with np.load('data/processed/pilot_inputs.npz') as archive:
        a={k:archive[k] for k in archive.files}
    model=GaussianHistory(a['gaussian_mean'],a['U'],a['diagonal'])
    W=a['W']; sparseW=csr_matrix(W); n=len(W)
    hashes=pd.read_csv('results/stage1_pilot/enclosures.csv')
    hashes=hashes[(hashes.retention == .15)&(hashes.N == 1024)].set_index('origin').scenario_hash
    rows=[];start=time.perf_counter();max_error=0.
    # Warm both CPU kernels on a fixed outcome-independent zero scenario.
    wx=np.zeros((32,2,n));wf=np.zeros((32,6,n))
    warm_start=time.perf_counter();rollout(wx,wf,W,a['coefficients']);sparse_rollout(wx,wf,sparseW,a['coefficients'])
    warm=time.perf_counter()-warm_start
    for i,origin in enumerate(a['origins']):
        stamp=pd.Timestamp(int(a['timestamps'][i]));regime=int(stamp.dayofweek>=5)*3+stamp.hour//8
        candidates=np.flatnonzero(a['bank_regime'] == regime)
        before=time.perf_counter()
        initial,forcing,info=make_scenarios(model,a['history'][i],a['history_mask'][i],a['blocks'],
            a['ordering'][:int(np.ceil(.15*n))],a['calendar'][i],a['prior_mean'][i],a['bank'],candidates,
            a['seasonal_forcing'][i],1024,20260922,int(origin))
        generation=time.perf_counter()-before
        digest=hashlib.sha256(initial[:,-2:].tobytes()+forcing.tobytes()).hexdigest()
        if digest != hashes.loc[origin]:
            raise AssertionError('CPU timing sample differs from saved GPU scenario')
        outputs={}
        # Alternate measurement order by index, independent of outcomes.
        order=['dense','csr'] if i%2 == 0 else ['csr','dense']
        for backend in order:
            before=time.perf_counter()
            states=rollout(initial,forcing,W,a['coefficients']) if backend == 'dense' else sparse_rollout(initial,forcing,sparseW,a['coefficients'])
            kernel=time.perf_counter()-before
            before=time.perf_counter();labels=event(states,int(a['threshold']));summary=bernoulli_summary(labels)
            event_time=time.perf_counter()-before
            outputs[backend]=(states,labels)
            rows.append(dict(origin=int(origin),backend=backend,generation_seconds=generation,rollout_seconds=kernel,
                event_and_interval_seconds=event_time,total_seconds=generation+kernel+event_time,
                scenario_sha256=digest,events=int(labels.sum())))
        max_error=max(max_error,float(np.max(np.abs(outputs['dense'][0]-outputs['csr'][0]))))
        if not np.array_equal(outputs['dense'][1],outputs['csr'][1]):
            raise AssertionError('CPU sparse/dense event disagreement')
    frame=pd.DataFrame(rows)
    frame.to_csv('results/cpu_reference.csv',index=False)
    aggregate={name:dict(mean_seconds=float(g.total_seconds.mean()),p95_seconds=float(g.total_seconds.quantile(.95)),
        mean_rollout_seconds=float(g.rollout_seconds.mean()),mean_generation_seconds=float(g.generation_seconds.mean())) for name,g in frame.groupby('backend')}
    save_json('results/cpu_reference.json',dict(core_source_sha=args.source_sha,origin_count=128,N=1024,retention=.15,
        device='CPU only, no CUDA imported',threads=4,warmup_seconds=warm,wall_seconds=time.perf_counter()-start,
        maximum_state_difference=max_error,event_disagreements=0,scenario_hashes_match=True,results=aggregate,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-sha',required=True)
    with threadpool_limits(4): main(parser.parse_args())
