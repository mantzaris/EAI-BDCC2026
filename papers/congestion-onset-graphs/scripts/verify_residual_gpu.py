"""Checkpoint replay and transfer-inclusive costs; no fitting or selection."""
import argparse
import csv
import gzip
from pathlib import Path
import time
import h5py
import torch
from run_residual_gpu import read, save, env_record, load_model
from traffic_risk_twins.residual_gpu.data import PilotData, to_cuda, valid, transform, aggregate_features, local_features
from traffic_risk_twins.residual_gpu.baseline import GPUQuantileBoost
from traffic_risk_twins.residual_gpu.models import predict_correction, corrected_probability


def detection(y, p, threshold):
    positive=y==1; alarm=p>=threshold
    tp=(positive&alarm).sum(); fp=(~positive&alarm).sum()
    return dict(tp=tp.item(), fp=fp.item(), positives=positive.sum().item(), negatives=(~positive).sum().item(),
                recall=(tp.double()/positive.sum()).item(), fpr=(fp.double()/(~positive).sum()).item())


@torch.no_grad()
def verify(c, out, private):
    data=PilotData(c)
    stored=torch.load(private/'baseline.pt', map_location='cuda', weights_only=False)
    base=GPUQuantileBoost.from_state(stored['baseline']);data.feature_free=stored['feature_free']
    data.load('validation');part=data.prepare(data.splits['validation']['origins']);part['p']=base.predict(part['X'])
    with gzip.open(out/'validation_predictions.csv.gz','rt') as stream: rows=list(csv.DictReader(stream))
    assert torch.equal(part['origins'],to_cuda([int(r['origins']) for r in rows],torch.long))
    for key in ('y','coverage'):
        assert torch.equal(part[key],to_cuda([float(r[key]) for r in rows],torch.float64))
    for key in ('eligible','active','lower','upper'):
        assert torch.equal(part[key],to_cuda([r[key]=='True' for r in rows],torch.bool))
    expected=read(out/'primary_metrics.json');selected=read(out/'selected.json')
    assert torch.all(data.W>=0) and torch.allclose(data.W.sum(1),torch.ones_like(data.W[:,0]),atol=1e-12,rtol=0)
    records={};families={};models={}
    names=[('A_T',None,None)]+[(f,r['name'],r) for f in selected for r in selected[f]['replicates']]
    for family,name,rep in names:
        key=name or 'A_T';p=part['p'];raw=p
        threshold=read(out/'baseline_alarm.json')['threshold']
        if rep is not None:
            model=load_model(c,data,private,family,name)
            residual=predict_correction(model,part)
            raw=corrected_probability(p,residual,1)
            p=corrected_probability(p,residual,rep['alpha']);threshold=rep['threshold']
            if family not in models:models[family]=model
        saved=to_cuda([float(r[key]) for r in rows],torch.float64)
        error=(saved-p).abs().max();assert error<1e-12
        rec=dict(replay_max_abs_error=error.item(),alpha=rep['alpha'] if rep else None)
        for label,keep in [('all_time',part['eligible']),('onset',part['eligible']&~part['active'])]:
            y=part['y'][keep];q=p[keep];loss=(y-q).square()
            brier=loss.mean();assert torch.abs(brier-to_cuda(expected['per_model'][key][label]['brier'],torch.float64))<1e-12
            event=(loss*(y==1)).mean();non=(loss*(y==0)).mean()
            rec[label]=dict(brier=brier.item(),unshrunk_brier=(raw[keep]-y).square().mean().item(),
                event_contribution=event.item(),nonevent_contribution=non.item(),mean_probability=q.mean().item(),
                detection=detection(y,q,to_cuda(threshold,torch.float64)))
        records[key]=rec
    # Mean losses/detection across independent seeds; never an ensemble probability.
    for family in selected:
        keys=[r['name'] for r in selected[family]['replicates']];families[family]={}
        for subset in ('all_time','onset'):
            values={}
            for key in ('brier','unshrunk_brier','event_contribution','nonevent_contribution','mean_probability'):
                values[key]=to_cuda([records[k][subset][key] for k in keys],torch.float64).mean().item()
            for key in ('recall','fpr'):
                values[key]=to_cuda([records[k][subset]['detection'][key] for k in keys],torch.float64).mean().item()
            families[family][subset]=values
    save(out/'checkpoint_replay.json',dict(passed=True,records=records,family_mean=families,
        comparison='Replayed all nine frozen checkpoints and baseline against saved predictions on CUDA',
        tolerance=1e-12,graph_nonnegative_row_sum_check=True,test_access=False))

    # Timestamp-only fixed panel. Host selection/parsing is metadata, not CPU numerical inference.
    all_ids=data.splits['validation']['origins']
    panel_index=torch.linspace(0,len(all_ids)-1,128,device='cuda').long().cpu().tolist()
    ids=[int(all_ids[i]) for i in panel_index];gpu_ids=to_cuda(ids,torch.long)
    def parse():
        with h5py.File(c['raw_file'],'r') as f:
            return [f['speed/block0_values'][i-11:i+1] for i in ids]
    host=parse()
    def transfer():return torch.stack([to_cuda(h,torch.float64) for h in host])
    raw=transfer();torch.cuda.synchronize()
    def compute(raw,family):
        m=valid(raw);state=transform(raw,m,data.feature_free)
        X=aggregate_features(state,m,data.blocks,data.calendar[gpu_ids]);p=base.predict(X)
        if family!='A_T':
            Z=local_features(state,m,X[:,:192].reshape(-1,12,16),data.blocks)
            p=corrected_probability(p,models[family](X,p,Z,m.permute(0,2,1).any(-1)),selected[family]['replicates'][0]['alpha'])
        return p
    def timed(call):
        torch.cuda.synchronize();start=time.perf_counter();a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        a.record();value=call();b.record();torch.cuda.synchronize()
        return value,dict(wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=a.elapsed_time(b)/1000)
    start=time.perf_counter()
    for f in ('A_T','B','C','D'):compute(raw,f).cpu()
    torch.cuda.synchronize();warmup=time.perf_counter()-start;timings=[]
    for repeat in range(3):
        for family in (('A_T','B','C','D') if repeat%2==0 else ('D','C','B','A_T')):
            torch.cuda.synchronize();total=time.perf_counter();t=time.perf_counter();host=parse();io=time.perf_counter()-t
            raw,h2d=timed(transfer);p,device=timed(lambda:compute(raw,family));_,d2h=timed(lambda:p.cpu())
            timings.append(dict(family=family,repeat=repeat,origins=128,archival_read_wall_seconds=io,
                h2d=h2d,feature_baseline_correction=device,d2h=d2h,complete_wall_seconds=time.perf_counter()-total))
    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as prof:
        compute(raw,'D');torch.cuda.synchronize()
    activities=[e for e in prof.events() if e.device_type==torch.autograd.DeviceType.CUDA]
    save(out/'transfer_costs.json',dict(panel_origins=ids,warmup_seconds=warmup,repeats=timings,
        profiler_scope='One additional 128-origin D forward including summaries and baseline, resident raw input; excludes transfers',
        profiled_kernel_seconds=sum(e.time_range.elapsed_us() for e in activities if not any(t in e.name.lower() for t in ('memcpy','memset')))/1e6,
        profiled_device_activity_seconds=sum(e.time_range.elapsed_us() for e in activities)/1e6,
        profiled_cuda_events=len(activities),host_history_dtype='float64',host_to_device_value_bytes=128*12*325*8,
        output_bytes=128*8,scope='Checkpoint loading excluded; fixed panel file parsing, H2D, raw transforms, summaries, frozen baseline, correction, D2H included',
        warm_cache=True,no_cpu_benchmark=True,no_selection_or_fitting=True,test_access=False))


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-sha',required=True);p.add_argument('--run-id',default='pilot01');args=p.parse_args()
    c=read('configs/residual_pilot.json');out=Path(c['output'])/args.run_id;private=Path('checkpoints/residual_pilot')/args.run_id
    if (out/'verification_run.json').exists():raise FileExistsError('Preserve completed verification')
    start=time.perf_counter();assert torch.cuda.is_available() and torch.cuda.device_count()==1
    prop=torch.cuda.get_device_properties(0);assert prop.name==c['resource']['device']
    torch.cuda.set_per_process_memory_fraction(c['resource']['max_allocated_vram_bytes']/prop.total_memory)
    torch.set_default_device('cuda');torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);a.record();verify(c,out,private);b.record();torch.cuda.synchronize()
    assert torch.cuda.max_memory_allocated()<=c['resource']['max_allocated_vram_bytes']
    save(out/'verification_run.json',dict(complete=True,source_sha=args.source_sha,environment=env_record(args.source_sha),
        internal_wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=a.elapsed_time(b)/1000,
        peak_vram_allocated_bytes=torch.cuda.max_memory_allocated(),peak_vram_reserved_bytes=torch.cuda.max_memory_reserved(),test_access=False))
    print('Checkpoint replay and complete cost verification passed',flush=True)


if __name__=='__main__':main()
