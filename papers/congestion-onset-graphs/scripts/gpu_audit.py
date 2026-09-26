"""GPU checks must run inside the persistent budget wrapper."""
import argparse
import importlib.metadata
import json
import platform
import resource
import subprocess
import time
from pathlib import Path
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from traffic_risk_twins.graph_dynamics import rollout,rollout_torch
from traffic_risk_twins.graph_enclosures import Partition,enclose
from traffic_risk_twins.event_functionals import event
from traffic_risk_twins.data_access import save_json


def audit(source_sha):
    start=time.perf_counter()
    if torch.cuda.get_device_name() != 'NVIDIA RTX 6000 Ada Generation':
        raise RuntimeError('Wrong GPU')
    torch.backends.cuda.matmul.allow_tf32=False
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(32_000_000_000/torch.cuda.get_device_properties(0).total_memory)
    rng=np.random.default_rng(91377)
    begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
    max_error=0.; flips=0; violations=0.; device_time=0.
    for j in range(40):
        W=rng.uniform(size=(12,12)); W/=W.sum(axis=1,keepdims=True)
        initial=rng.normal(size=(32,2,12)); forcing=rng.normal(size=(32,6,12))
        coef=rng.dirichlet(np.ones(4))*.98
        cpu=rollout(initial,forcing,W,coef)
        inputs=[torch.tensor(a,device='cuda',dtype=torch.float64) for a in (initial,forcing,W)]
        begin.record(); gpu=rollout_torch(*inputs,coef); end.record(); torch.cuda.synchronize()
        device_time+=begin.elapsed_time(end)/1000
        observed=gpu.cpu().numpy()
        max_error=max(max_error,float(np.max(np.abs(cpu-observed))))
        flips+=int(np.sum(event(cpu,4) != event(observed,4)))
        partition=Partition.build(W,np.repeat(np.arange(3),4))
        z,r=enclose(initial,forcing,partition,coef)
        violations=max(violations,float(np.max(np.abs(observed-z[...,partition.labels])-r[...,partition.labels])))
    if flips or violations > 1e-10 or max_error > 1e-10:
        raise AssertionError('GPU agreement/enclosure audit failed')
    # Constructed cancellation: float32 rounds the first forcing to -1.
    initial=np.full((1,2,4),2.)
    forcing=np.zeros((1,6,4)); forcing[:,0]=-1.-1e-8
    precision={}
    for dtype in ('float32','float64'):
        inputs=[torch.tensor(a,device='cuda',dtype=getattr(torch,dtype)) for a in (initial,forcing,np.eye(4))]
        begin.record(); states=rollout_torch(*inputs,[.5,0,0,0]); end.record(); torch.cuda.synchronize()
        device_time+=begin.elapsed_time(end)/1000
        states=states.cpu().numpy()
        precision[dtype]=dict(label=bool(event(states,4)[0]),first_state=float(states[0,0,0]))
    assert precision['float32']['label'] != precision['float64']['label']
    packages=['numpy','scipy','pandas','scikit-learn','matplotlib','h5py','PyYAML','pytest','threadpoolctl','torch']
    environment={p:importlib.metadata.version(p) for p in packages}
    save_json('manifests/gpu_environment.json',dict(source_sha=source_sha,python=platform.python_version(),packages=environment,
        gpu_name=torch.cuda.get_device_name(),vram_bytes=torch.cuda.get_device_properties(0).total_memory,
        torch_cuda_runtime=torch.version.cuda,driver=subprocess.check_output(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'],text=True).strip(),
        cpu=platform.processor(),host_memory=subprocess.check_output(['free','-b'],text=True),
        disk=subprocess.check_output(['df','-B1','/workspace'],text=True)))
    result=dict(source_sha=source_sha,random_graphs=40,coupled_scenarios=1280,cpu_gpu_max_state_error=max_error,
        cpu_gpu_label_flips=flips,maximum_positive_enclosure_violation=violations,constructed_threshold_case=precision,
        wall_seconds=time.perf_counter()-start,cuda_rollout_event_seconds=device_time,
        host_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        max_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),all_assertions_passed=True)
    save_json('results/gpu_audit.json',result)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--source-sha',required=True)
    args=parser.parse_args()
    with threadpool_limits(4): audit(args.source_sha)
