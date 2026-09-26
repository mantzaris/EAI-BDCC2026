"""Explicit frozen inference/replay; no training, calibration fit, or graph selection."""
import argparse
import csv
import gzip
import hashlib
from pathlib import Path
import resource
import time
import torch
from traffic_risk_twins.final_test.access import FinalData, verify_files, committed_manifest, utc
from traffic_risk_twins.final_test.analysis import summaries, summarize_existing_costs
from traffic_risk_twins.residual_gpu.baseline import GPUQuantileBoost
from traffic_risk_twins.residual_gpu.data import sha256, to_cuda
from traffic_risk_twins.onset_graph.io import read, save, load_weights
from traffic_risk_twins.onset_graph.supplement import read_predictions
from traffic_risk_twins.onset_graph.evaluation import onset
from traffic_risk_twins.onset_graph.calibration import apply_calibration
from run_onset_graph import collect, get_graph, load_model
from run_residual_gpu import env_record


def graph_hash(W):
    return hashlib.sha256(W.detach().double().contiguous().cpu().numpy().tobytes()).hexdigest()


def serialize(path, part, predictions):
    names = ('origins','time_ns','day','y','lower','upper','eligible','active','coverage')
    fields = {k:part[k].cpu().tolist() for k in names}
    fields.update(onset_eligible=onset(part).cpu().tolist(),
        excluded_future_coverage=(part['coverage']<.95).cpu().tolist(),
        excluded_ambiguous=(part['lower']!=part['upper']).cpu().tolist())
    fields.update({k:v.cpu().tolist() for k,v in predictions.items()})
    with gzip.open(path,'wt',newline='') as out:
        writer=csv.writer(out,lineterminator='\n');writer.writerow(fields);writer.writerows(zip(*fields.values()))


def prediction_difference(part, predictions, path):
    with gzip.open(path,'rt') as stream:rows=list(csv.DictReader(stream))
    integers=('origins','time_ns','day');booleans=('lower','upper','eligible','active')
    columns=list(('origins','time_ns','day','y','lower','upper','eligible','active','coverage'))+list(predictions)
    reference={key:to_cuda([int(r[key]) if key in integers else r[key]=='True' if key in booleans else float(r[key]) for r in rows],
        torch.long if key in integers else torch.bool if key in booleans else torch.float64) for key in columns}
    for key in ('origins','time_ns','day','y','lower','upper','eligible','active','coverage'):
        assert torch.equal(part[key],reference[key]), 'Reference alignment differs: '+key
    return torch.stack([(p-reference[k]).abs().max() for k,p in predictions.items()]).max().item()


def metric_difference(a,b):
    # Compare all numeric leaves with matching structure, on CUDA. Counts and interval endpoints included.
    av=[];bv=[]
    def descend(x,y):
        assert type(x) is type(y)
        if isinstance(x,dict):
            assert x.keys()==y.keys()
            for k in x:descend(x[k],y[k])
        elif isinstance(x,list):
            assert len(x)==len(y)
            for xx,yy in zip(x,y):descend(xx,yy)
        elif isinstance(x,(int,float)) and not isinstance(x,bool):av.append(x);bv.append(y)
        else:assert x==y
    descend(a,b)
    return (to_cuda(av,torch.float64)-to_cuda(bv,torch.float64)).abs().max().item()


@torch.no_grad()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['preflight','evaluate','replay'])
    parser.add_argument('--manifest',default='configs/final_test_manifest.json')
    parser.add_argument('--protocol-commit',required=True)
    args=parser.parse_args()
    manifest=committed_manifest(args.manifest,args.protocol_commit);verify_files(manifest)
    if args.mode!='preflight' and not manifest['sealed']:raise PermissionError('Seal required')
    out=Path('results/final_test')/args.mode
    if out.exists():raise FileExistsError('Existing evidence cannot be overwritten: '+str(out))
    if args.mode=='replay' and not Path('results/final_test/evaluate/complete.json').exists():raise ValueError('Evaluation must finish first')
    out.mkdir(parents=True)
    assert torch.cuda.is_available()
    prop=torch.cuda.get_device_properties(0)
    assert prop.name=='NVIDIA RTX 6000 Ada Generation',prop.name
    assert prop.total_memory>=47_000_000_000
    torch.cuda.set_per_process_memory_fraction(32_000_000_000/prop.total_memory)
    torch.set_default_device('cuda');torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    start=time.perf_counter();ev1,ev2=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);ev1.record()
    config=read(manifest['configuration']);metadata=read(manifest['model_metadata']);art=Path(manifest['artifact_directory'])
    data=FinalData(config);anchor_state=load_weights(art/'anchor.pt.gz')
    data.feature_free=anchor_state['feature_free'];anchor=GPUQuantileBoost.from_state(anchor_state['baseline'])
    graphs={'distance':data.W}
    for key in manifest['graph_keys']:get_graph(data,art,key,graphs)
    graph_hashes={key:graph_hash(graphs[key]) for key in manifest['graph_keys']}
    if manifest['sealed']:assert graph_hashes==manifest['graph_operator_sha256']
    if args.mode=='preflight':
        try:data.load('test')
        except ValueError:pass
        else:raise AssertionError('Historical guard removed')
        try:data.fit_feature_transform()
        except RuntimeError:pass
        else:raise AssertionError('Final reader exposes fitting')
        bad=dict(manifest);bad['files']={manifest['configuration']:dict(bytes=0,sha256='invalid')}
        try:verify_files(bad)
        except ValueError:pass
        else:raise AssertionError('Hash rejection failed')
        data.load('validation');ids=data.splits['validation']['origins']
        testrows=to_cuda(data.splits['test']['rows'],torch.long)
        assert torch.isnan(data.raw[testrows]).all()
    else:
        assert read('results/final_test/preflight/complete.json')['passed']
        ids=data.load_final(manifest,args.protocol_commit,out/'test_access_started.json')
    part=data.prepare(ids);part['p']=anchor.predict(part['X'])
    raw,thresholds,families,times=collect(config,data,art,part,metadata,graphs)
    assert families==manifest['families'], 'Frozen roster mismatch'
    calibrated={};ct={}
    reps={r['key']:r for f in metadata['families'].values() for r in f['replicates']}
    for key,p in raw.items():
        rec=metadata['controls'][key] if key in metadata['controls'] else reps[key]
        calibrated[key]=apply_calibration(p,rec['calibrator']);ct[key]=to_cuda(rec['calibrated_cutoff'],torch.float64)
        assert thresholds[key].item()==rec['raw_cutoff']
        assert torch.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    difference={}
    if args.mode=='preflight':
        prior=Path('results/onset_graph/study01/main')
        for name,predictions in [('raw',raw),('calibrated',calibrated)]:
            difference[name]=prediction_difference(part,predictions,prior/('validation_'+name+'_predictions.csv.gz'))
            assert difference[name]<=manifest['tolerances']['prediction_max_absolute']
        # Restore and check exact alpha=0 baseline recovery on the complete replay workload.
        from traffic_risk_twins.onset_graph.models import predict
        model=load_model(config,data,art,metadata['families']['C']['replicates'][0],graphs)
        assert torch.equal(predict(model,part,0),part['p'].clamp(0,1))
        del model
        save(out/'checks.json',dict(all_45_checkpoint_predictions_replayed=True,all_90_raw_calibrated_columns=True,
            old_test_guard=True,no_final_fitting=True,hash_rejection=True,zero_alpha_recovery=True,
            masks_labels_origins_aligned=True,test_measurements_unread=True,graph_operator_sha256=graph_hashes))
    else:
        for name,predictions,cuts in [('raw',raw,thresholds),('calibrated',calibrated,ct)]:
            result=summaries(part,predictions,cuts,families,config['bootstrap'],name=='raw')
            if args.mode=='replay':
                reference=Path('results/final_test/evaluate')
                difference[name+'_prediction']=prediction_difference(part,predictions,reference/(name+'_predictions.csv.gz'))
                difference[name+'_metrics']=metric_difference(result,read(reference/(name+'_metrics.json')))
                assert difference[name+'_prediction']<=manifest['tolerances']['prediction_max_absolute']
                assert difference[name+'_metrics']<=manifest['tolerances']['metric_max_absolute']
            else:
                serialize(out/(name+'_predictions.csv.gz'),part,predictions)
                save(out/(name+'_metrics.json'),result)
        if args.mode=='evaluate':save(out/'historical_cost_summary.json',summarize_existing_costs('results/onset_graph/study01/main/complete_costs.json'))
    ev2.record();torch.cuda.synchronize()
    environment=env_record(args.protocol_commit);environment['test_access']=args.mode!='preflight'
    environment['driver']=__import__('subprocess').check_output(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'],text=True).strip()
    save(out/'complete.json',dict(passed=True,mode=args.mode,completed_utc=utc(),protocol_commit=args.protocol_commit,
        manifest_sha256=sha256(args.manifest),implementation_commit=manifest.get('implementation_commit'),environment=environment,
        max_absolute_differences=difference,graph_operator_sha256=graph_hashes,io_slices=data.io_records,
        wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=ev1.elapsed_time(ev2)/1000,
        cuda_scope='Full scientific phase including host gaps; not active kernel time',
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        max_host_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,source_unchanged_checked=True,
        scientific_numerics='CUDA only',test_access=args.mode!='preflight',no_fit=True))
    print(args.mode,'PASS',difference,flush=True)


if __name__=='__main__':main()
