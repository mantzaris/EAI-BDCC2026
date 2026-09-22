"""Fixed-sample Stage 1 pilot. Run GPU executions through budget-run.

All conditions use the same fitted model and saved validation origins. This
is a hybrid implementation: NumPy conditioning/enclosure + eager GPU fine dynamics.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import time
import numpy as np
import pandas as pd
import yaml
from threadpoolctl import threadpool_limits
from traffic_risk_twins.conditional_history import GaussianHistory
from traffic_risk_twins.scenarios import make_scenarios
from traffic_risk_twins.graph_dynamics import rollout,rollout_torch
from traffic_risk_twins.graph_enclosures import Partition,enclose,labels_from_bounds,coarse_rollout
from traffic_risk_twins.event_functionals import event
from traffic_risk_twins.scenario_estimators import bernoulli_summary,two_level,allocate_two_level
from traffic_risk_twins.data_access import sha256,save_json


class FineBackend:
    def __init__(self,W,coefficients,device):
        self.W,self.coefficients,self.device=W,coefficients,device
        self.device_seconds=0.
        if device == 'cuda':
            import torch
            self.torch=torch
            if torch.cuda.get_device_name() != 'NVIDIA RTX 6000 Ada Generation':
                raise RuntimeError('Intended RTX 6000 Ada not available')
            torch.set_num_threads(4)
            torch.backends.cuda.matmul.allow_tf32=False
            torch.backends.cudnn.allow_tf32=False
            torch.cuda.set_per_process_memory_fraction(32_000_000_000/torch.cuda.get_device_properties(0).total_memory)
            self.Wgpu=torch.tensor(W,device='cuda',dtype=torch.float64)

    def fine(self,initial,forcing,precision='float64'):
        timing={}
        start=time.perf_counter()
        if self.device == 'cpu':
            states=rollout(initial.astype(precision),forcing.astype(precision),self.W.astype(precision),self.coefficients)
            timing['fine_seconds']=time.perf_counter()-start
            timing.update(transfer_seconds=0.,device_seconds=0.)
            return states,timing
        torch=self.torch
        torch.cuda.synchronize()
        dtype=getattr(torch,precision)
        before=time.perf_counter()
        x=torch.as_tensor(initial,device='cuda',dtype=dtype)
        f=torch.as_tensor(forcing,device='cuda',dtype=dtype)
        W=self.Wgpu.to(dtype)
        torch.cuda.synchronize()
        transfer=time.perf_counter()-before
        begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        before=time.perf_counter(); begin.record()
        states=rollout_torch(x,f,W,self.coefficients)
        end.record(); torch.cuda.synchronize()
        timing['fine_seconds']=time.perf_counter()-before
        timing['device_seconds']=begin.elapsed_time(end)/1000
        self.device_seconds += timing['device_seconds']
        before=time.perf_counter(); result=states.cpu().numpy(); torch.cuda.synchronize()
        timing['transfer_seconds']=transfer+time.perf_counter()-before
        if torch.cuda.max_memory_allocated() > 32_000_000_000:
            raise MemoryError('VRAM cap exceeded')
        return result,timing


def run(args):
    config=yaml.safe_load(Path(args.config).read_text())
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    data=np.load(args.inputs)
    model=GaussianHistory(data['gaussian_mean'],data['U'],data['diagonal'])
    W=data['W']; coefficients=data['coefficients']; blocks=data['blocks']; n=len(W)
    partition=Partition.build(W,blocks)
    backend=FineBackend(W,coefficients,args.device)
    cpu=FineBackend(W,coefficients,'cpu')
    threshold=int(data['threshold'])
    arrays={key:data[key] for key in data.files} # resident model/bank, measured startup cost
    data.close()
    rows=[]; timing_rows=[]; recon_rows=[]; audit_rows=[]; allocation_rows=[]
    def sample(i,fraction,N,stream=0):
        stamp=pd.Timestamp(int(arrays['timestamps'][i]))
        regime=int(stamp.dayofweek >= 5)*3+stamp.hour//8
        candidates=np.flatnonzero(arrays['bank_regime'] == regime)
        selected=arrays['ordering'][:int(np.ceil(fraction*n))]
        return make_scenarios(model,arrays['history'][i],arrays['history_mask'][i],blocks,selected,
            arrays['calendar'][i],arrays['prior_mean'][i],arrays['bank'],candidates,
            arrays['seasonal_forcing'][i],N,config['seed'],int(arrays['origins'][i]),stream)

    # Warm-up is explicit, outcome-independent, timed and charged in outer ledger.
    before=time.perf_counter()
    wx=np.zeros((32,2,n)); wf=np.zeros((32,6,n))
    backend.fine(wx,wf)
    warmup=time.perf_counter()-before
    startup=time.perf_counter()-start
    maximum=min(args.origin_limit,len(arrays['origins']))
    if maximum > config['max_validation_origins']:
        raise ValueError('Too many validation origins')
    for i in range(maximum):
        origin_start=time.perf_counter()
        origin=int(arrays['origins'][i])
        for fraction in config['retained_fractions']:
            for N in config['scenario_counts']:
                pipeline_start=before=time.perf_counter()
                initial,forcing,info=sample(i,fraction,N)
                generation=time.perf_counter()-before
                fine,tf=backend.fine(initial,forcing)
                e0=time.perf_counter(); labels=event(fine,threshold); event_seconds=time.perf_counter()-e0
                summary=bernoulli_summary(labels)
                fine_total=time.perf_counter()-pipeline_start
                raw=arrays['future'][i]; mask=arrays['future_mask'][i]
                speeds=arrays['free']*(1-__import__('scipy').special.expit(fine)).mean(axis=0)
                row=dict(origin=origin,retention=fraction,N=N,method='fine_mc',device=args.device,
                         probability=summary['estimate'],mc_low=summary['interval'][0],mc_high=summary['interval'][1],
                         zero_upper=summary['zero_event_one_sided_upper'],events=int(labels.sum()),
                         label=int(arrays['labels'][i]),eligible=bool(arrays['label_eligible'][i]),
                         current_active=bool(arrays['current_active'][i]),day=str(pd.Timestamp(int(arrays['timestamps'][i])).date()),
                         total_seconds=fine_total,payload_bytes=info['payload_bytes'],sensor_values_read=info['sensor_values_read'])
                for h in (2,5):
                    good=mask[h]
                    row[f'mae_{(h+1)*5}min_raw']=float(np.abs(speeds[h]-raw[h])[good].mean())
                    row[f'mae_{(h+1)*5}min_capped']=float(np.abs(speeds[h]-np.minimum(raw[h],arrays['free']))[good].mean())
                rows.append(row)
                timing_rows.append(dict(origin=origin,retention=fraction,N=N,method='fine_mc',device=args.device,
                        **info['timings'],**tf,event_seconds=event_seconds,total_seconds=fine_total))
                # Reconstruction diagnostics, outside prediction service time.
                if N == max(config['scenario_counts']):
                    hidden=arrays['history_mask'][i].copy()
                    hidden[:,arrays['ordering'][:int(np.ceil(fraction*n))]]=False
                    if hidden.any():
                        truth=arrays['history'][i][hidden]
                        samples=initial[:,hidden]
                        err=samples.mean(axis=0)-truth
                        rec=dict(origin=origin,retention=fraction,hidden_count=len(truth),rmse=float(np.sqrt(np.mean(err**2))),
                                 near_threshold_rmse=float(np.sqrt(np.mean(err[np.abs(truth)<=1]**2))) if (np.abs(truth)<=1).any() else None)
                        for level in (.5,.8,.95):
                            lower,upper=np.quantile(samples,[(1-level)/2,1-(1-level)/2],axis=0)
                            rec[f'coverage_{int(level*100)}']=float(((truth>=lower)&(truth<=upper)).mean())
                        recon_rows.append(rec)
                    else:
                        recon_rows.append(dict(origin=origin,retention=fraction,hidden_count=0,rmse=None,coverage_50=None,coverage_80=None,coverage_95=None))
                # Coarse computation includes reductions of initial states and forcing.
                selective_start=before=time.perf_counter(); center,radius=enclose(initial,forcing,partition,coefficients)
                low,high=labels_from_bounds(center,radius,partition,threshold)
                enclosure_time=time.perf_counter()-before
                before=time.perf_counter(); unresolved=np.flatnonzero(low != high)
                xi,ff=initial[unresolved],forcing[unresolved]
                compaction=time.perf_counter()-before
                empirical=low.copy(); refine_time=0.; refine_transfer=0.
                if len(unresolved):
                    refined,rt=backend.fine(xi,ff)
                    empirical[unresolved]=event(refined,threshold)
                    refine_time=rt['fine_seconds']; refine_transfer=rt['transfer_seconds']
                empirical_summary=bernoulli_summary(empirical)
                empirical_total=generation+time.perf_counter()-selective_start
                if not np.array_equal(empirical,labels):
                    raise ArithmeticError('Empirical selective labels disagree with coupled fine labels')
                violation=float(np.max(np.abs(fine-center[...,blocks])-radius[...,blocks]))
                if violation > 1e-10:
                    raise ArithmeticError('Enclosure violation: disable claim')
                coarse=event(center,threshold,partition.sizes)
                # Certified mode: every numerical certificate is unverified, so all samples refine.
                # Actually execute this full fallback separately, not a synthetic speed estimate.
                before=time.perf_counter(); fallback,fbt=backend.fine(initial,forcing)
                fallback_labels=event(fallback,threshold)
                bernoulli_summary(fallback_labels)
                fallback_wall=time.perf_counter()-before
                assert np.array_equal(fallback_labels,labels)
                certified_total=generation+enclosure_time+fallback_wall
                for method,total in [('empirical_selective',empirical_total),('certified_fallback',certified_total)]:
                    copied=row.copy(); copied.update(method=method,total_seconds=total)
                    rows.append(copied)
                    timing_rows.append(dict(origin=origin,retention=fraction,N=N,method=method,device=args.device,
                        **info['timings'],enclosure_seconds=enclosure_time,compaction_seconds=compaction if method == 'empirical_selective' else 0.,
                        fine_seconds=refine_time if method == 'empirical_selective' else fbt['fine_seconds'],
                        transfer_seconds=refine_transfer if method == 'empirical_selective' else fbt['transfer_seconds'],total_seconds=total))
                audit_rows.append(dict(origin=origin,retention=fraction,N=N,unresolved_fraction=len(unresolved)/N,
                      refined_fraction_certified=1.,coarse_fine_agreement=float((coarse == labels).mean()),
                      correction_variance=float((labels.astype(float)-coarse.astype(float)).var(ddof=1)),
                      maximum_enclosure_violation=violation,mean_radius=float(radius.mean()),
                      actual_mean_error=float(np.abs(fine-center[...,blocks]).mean()),
                      scenario_hash=hashlib.sha256(initial[:,-2:].tobytes()+forcing.tobytes()).hexdigest()))
                # Competent four-thread vectorized CPU reference, including generation again.
                before=time.perf_counter(); ci,cf,cinfo=sample(i,fraction,N)
                cpu_generation=time.perf_counter()-before
                cfine,ct=cpu.fine(ci,cf)
                e0=time.perf_counter(); cpu_labels=event(cfine,threshold); cpu_event=time.perf_counter()-e0
                ci0=time.perf_counter(); bernoulli_summary(cpu_labels); cpu_interval=time.perf_counter()-ci0
                if not np.array_equal(ci,initial) or not np.array_equal(cf,forcing):
                    raise AssertionError('Scenario identity changed across backends')
                if not np.array_equal(cpu_labels,labels):
                    raise ArithmeticError('CPU/GPU FP64 label mismatch')
                timing_rows.append(dict(origin=origin,retention=fraction,N=N,method='fine_mc',device='cpu',
                    **cinfo['timings'],**ct,event_seconds=cpu_event,total_seconds=cpu_generation+ct['fine_seconds']+cpu_event+cpu_interval))
                # A small prespecified precision audit: first eight time-selected origins.
                if i < 8 and N == 256:
                    fp32,pt=backend.fine(initial,forcing,'float32')
                    audit_rows[-1].update(fp32_label_flips=int(np.sum(event(fp32,threshold) != labels)),
                        fp32_max_state_error=float(np.max(np.abs(fp32-fine))),
                        cpu_gpu_max_state_error=float(np.max(np.abs(cfine-fine))))
                # Two-level allocation at 15%, as in the plan's numerical panel.
                if fraction == .15:
                    allocation_start=time.perf_counter()
                    # 64 independent allocation draws; not reused in either estimation set.
                    before=time.perf_counter(); ax,af,_=sample(i,fraction,64,stream=10+N)
                    ag=time.perf_counter()-before
                    before=time.perf_counter(); az=coarse_rollout(ax,af,partition,coefficients)
                    ac=event(az,threshold,partition.sizes); cheap_time=ag+time.perf_counter()-before
                    fa,at=backend.fine(ax,af); al=event(fa,threshold)
                    costs=np.array([cheap_time/64,(cheap_time+at['fine_seconds']+at['transfer_seconds'])/64])
                    variances=np.array([ac.var(ddof=1),(al.astype(float)-ac).var(ddof=1)])
                    # Target N fine scenarios' measured cost, with a hard minimum feasibility adjustment.
                    budget=max(fine_total,32*costs.sum())
                    n0,n1=allocate_two_level(variances,costs,budget)
                    # Bound finite-sample allocation above by 2N to avoid a near-zero-cost blowup.
                    n0,n1=min(int(n0),2*N),min(int(n1),2*N)
                    before=time.perf_counter()
                    x0,f0,_=sample(i,fraction,n0,stream=20+N)
                    z0=coarse_rollout(x0,f0,partition,coefficients); c0=event(z0,threshold,partition.sizes)
                    x1,f1,_=sample(i,fraction,n1,stream=30+N)
                    z1=coarse_rollout(x1,f1,partition,coefficients); c1=event(z1,threshold,partition.sizes)
                    y1,_=backend.fine(x1,f1); fine1=event(y1,threshold)
                    result=two_level(c0,c1,fine1)
                    elapsed=time.perf_counter()-before
                    copied=row.copy(); copied.update(method='two_level',probability=result['clipped_for_scoring'],
                        raw_probability=result['estimate'],mc_low=result['interval'][0],mc_high=result['interval'][1],
                        n0=n0,n1=n1,total_seconds=elapsed,allocation_budget_seconds=budget,zero_upper=None,events=None)
                    for key in list(copied):
                        if key.startswith('mae_'): copied[key]=None
                    rows.append(copied)
                    allocation_rows.append(dict(origin=origin,N=N,**result,pilot_c0=float(costs[0]),pilot_c1=float(costs[1]),
                        pilot_v0=float(variances[0]),pilot_v1=float(variances[1]),budget_seconds=budget,
                        estimator_seconds=elapsed,allocation_and_estimator_seconds=time.perf_counter()-allocation_start,
                        allocation_stream=10+N,cheap_stream=20+N,correction_stream=30+N))
        # Persist only completed origin blocks; any interruption leaves no partial means.
        for name,records in [('predictions',rows),('timings',timing_rows),('reconstruction',recon_rows),('enclosures',audit_rows),('allocations',allocation_rows)]:
            pd.DataFrame(records).to_csv(output/(name+'.csv'),index=False)
        elapsed=time.perf_counter()-start
        remaining=args.max_wall_seconds-elapsed
        estimated=(elapsed-startup)/(i+1)*(maximum-i-1)*1.5
        print(json.dumps(dict(completed_origins=i+1,elapsed_seconds=elapsed,conservative_remaining_projection=estimated)),flush=True)
        # Outcome-independent projected runtime gate; never select only fast scenarios within N.
        if i+1 < maximum and estimated > remaining:
            raise TimeoutError('Projected remaining pilot exceeds reservation; completed origins checkpointed')
    metadata=dict(source_sha=args.source_sha,config_sha256=sha256(args.config),input_sha256=sha256(args.inputs),
        completed_origins=maximum,complete=True,device=args.device,precision='FP64 reference, FP32 audit',
        numerical_certification='theorem exact arithmetic; floating bounds empirical; certified mode refines all',
        implementation='four-thread NumPy conditioning/enclosure plus eager GPU fine dynamics; all transfers included',
        cpu_threads=4,startup_seconds=startup,warmup_seconds=warmup,total_wall_seconds=time.perf_counter()-start,
        cuda_rollout_event_seconds=backend.device_seconds,
        cuda_timing_scope='CUDA events around every rollout, including warm-up, failed/repeated audits, correction and fallback; transfers separately timed',
        host_peak_rss_bytes=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),
        max_gpu_allocated_bytes=int(backend.torch.cuda.max_memory_allocated()) if args.device == 'cuda' else 0,
        max_gpu_reserved_bytes=int(backend.torch.cuda.max_memory_reserved()) if args.device == 'cuda' else 0,
        no_test_measurements=True,compilation_attempted=False,
        sample_count_protocol='fixed N; common draws across retention and N prefixes; independent allocation/cheap/correction streams')
    save_json(output/'run.json',metadata)
    print(json.dumps(metadata,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/stage1_pilot.yaml')
    parser.add_argument('--inputs',default='data/processed/pilot_inputs.npz')
    parser.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    parser.add_argument('--output',required=True)
    parser.add_argument('--source-sha',required=True)
    parser.add_argument('--origin-limit',type=int,default=128)
    parser.add_argument('--max-wall-seconds',type=float,default=2400)
    args=parser.parse_args()
    with threadpool_limits(4): run(args)
