"""Bounded GPU pilot. Train/gate is a separate invocation from outer evaluation."""
import argparse
import csv
import datetime
import gzip
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import time
import torch
from traffic_risk_twins.residual_gpu.data import PilotData,sha256,to_cuda
from traffic_risk_twins.residual_gpu.baseline import GPUQuantileBoost,SavedBaseline
from traffic_risk_twins.residual_gpu.models import corrected_probability,predict_correction
from traffic_risk_twins.residual_gpu.training import fit_correction,build_model,shrink_and_alarm
from traffic_risk_twins.residual_gpu.evaluation import support,metric,paired_summary,alignment,alarm_threshold
from traffic_risk_twins.residual_gpu.checks import scientific_checks


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)


def read(path):return json.loads(Path(path).read_text())


def env_record(source_sha):
    prop=torch.cuda.get_device_properties(0)
    packages={n:importlib.metadata.version(n) for n in ('torch','numpy','pandas','h5py')}
    return dict(source_sha=source_sha,python=platform.python_version(),packages=packages,torch_cuda=torch.version.cuda,
                device=prop.name,total_vram_bytes=prop.total_memory,substantive_numerics='CUDA only',test_access=False)


def save_part(path,part,predictions):
    # Host serialization only: every derived numerical value is computed on GPU.
    keys=['origins','day','y','lower','upper','eligible','active','coverage']
    fields={k:part[k].detach().cpu().tolist() for k in keys}
    fields.update({k:v.detach().cpu().tolist() for k,v in predictions.items()})
    with gzip.open(path,'wt',newline='') as out:
        writer=csv.writer(out);writer.writerow(fields)
        writer.writerows(zip(*fields.values()))


def freeze_metadata(data,out):
    roles={k:dict(days=v['days'],origins=v['origins'].tolist(),first_row=int(v['rows'][0]),last_row=int(v['rows'][-1])) for k,v in data.roles.items()}
    save(out/'split_manifest.json',dict(roles=roles,outer_dates={k:v['days'] for k,v in data.splits.items() if isinstance(v,dict)},
        validation_origins=data.splits['validation']['origins'].tolist(),validation_exposed_days=data.splits['validation']['days'],
        untouched_validation_days=[],test_access=False,embargo_minutes=90))


def baseline_and_parts(c,out,private,training):
    data=PilotData(c);data.load('train')
    if training:
        data.fit_feature_transform()
        initial=data.prepare(data.roles['baseline_fit']['origins'][::c['baseline_training_stride']])
        start=time.perf_counter();a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);a.record()
        baseline=GPUQuantileBoost(c['baseline']).fit(initial['X'][initial['eligible']],initial['y'][initial['eligible']])
        b.record();torch.cuda.synchronize()
        save(out/'baseline_fit.json',dict(name=c['baseline']['name'],wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=a.elapsed_time(b)/1000,
                training_origins=int(initial['eligible'].sum().item()),training_support=support(initial),historical_model_port=False,
                historic_checkpoint_missing=True,features=initial['X'].shape[1],cutoff_day=data.roles['baseline_fit']['days'][-1]))
        torch.save(dict(baseline=baseline.state_dict(),feature_free=data.feature_free),private/'baseline.pt')
        del initial
    else:
        stored=torch.load(private/'baseline.pt',map_location='cuda',weights_only=False)
        baseline=GPUQuantileBoost.from_state(stored['baseline']);data.feature_free=stored['feature_free']
    parts={}
    for role in c['inner_roles'][1:]:
        parts[role]=data.prepare(data.roles[role]['origins'])
        parts[role]['p']=baseline.predict(parts[role]['X'])
    return data,baseline,parts


def training(c,out,private,source):
    if (out/'refinement_gate.json').exists():raise FileExistsError('Preserve completed training; use a new run id')
    data,baseline,parts=baseline_and_parts(c,out,private,True);freeze_metadata(data,out)
    train=parts['correction_fit'];take=train['eligible']
    mean=train['X'][take].mean(0);scale=train['X'][take].std(0).clamp_min(.01)
    torch.save(dict(mean=mean,scale=scale),private/'normalization.pt')
    checks={}
    # Full outcome cutoffs and disjoint history/outcome windows on the GPU.
    previous=None
    for role in c['inner_roles']:
        origins=to_cuda(data.roles[role]['origins'],torch.long)
        first=data.time_ns[origins.min()-11];last=data.time_ns[origins.max()+6]
        if previous is not None:assert first>previous
        previous=last
    checks['chronological_outcome_cutoffs']=True
    save(out/'training_support.json',{k:support(v) for k,v in parts.items()})
    selected={};attempts=[]
    for family in c['correction']['families']:
        tuning=[]
        for reg in c['correction']['regularization']:
            name=f'{family}_tune_{reg}'
            model,record=fit_correction(family,c['correction'],parts,mean,scale,data.blocks,data.W,c['correction']['tuning_seed'],reg,private/(name+'.pt'))
            record.update(name=name,checkpoint_sha256=sha256(private/(name+'.pt')),phase='setting_selection')
            attempts.append(record);tuning.append(record);save(out/'attempts.json',attempts)
            del model
        # GPU selection; reverse regularization order makes exact ties prefer stronger shrinkage.
        scores=to_cuda([r['best_early_brier'] for r in tuning],torch.float64)
        reversed_best=int(scores.flip(0).argmin().item());best=len(tuning)-1-reversed_best
        selected[family]=dict(regularization=tuning[best]['regularization'],replicates=[])
        for seed in c['correction']['seeds']:
            reg=selected[family]['regularization'];name=f'{family}_{seed}'
            model,record=fit_correction(family,c['correction'],parts,mean,scale,data.blocks,data.W,seed,reg,private/(name+'.pt'))
            shrink=shrink_and_alarm(model,parts['shrinkage'],c['correction']['alpha_grid'])
            record.update(name=name,checkpoint_sha256=sha256(private/(name+'.pt')),phase='selected_replication',**shrink)
            attempts.append(record);selected[family]['replicates'].append(dict(name=name,seed=seed,**shrink));save(out/'attempts.json',attempts)
            del model
    save(out/'selected.json',selected)
    onset=parts['shrinkage']['eligible']&~parts['shrinkage']['active']
    threshold=alarm_threshold(parts['shrinkage']['p'][onset],parts['shrinkage']['y'][onset])
    save(out/'baseline_alarm.json',dict(threshold=threshold.item(),selection_role='shrinkage'))
    gate=parts['refinement_gate'];keep=gate['eligible'];onset=keep&~gate['active'];predictions={'A_T':gate['p']}
    means={};gate_metrics={};family_vectors={}
    gate_metrics['A_T']=metric(gate['y'][onset],gate['p'][onset],threshold)
    base_loss=(gate['y'][keep]-gate['p'][keep]).square().mean()
    means['A_T']=base_loss
    for family in selected:
        losses=[];detection=[]
        for r in selected[family]['replicates']:
            model=load_model(c,data,private,family,r['name'])
            prediction=corrected_probability(gate['p'],predict_correction(model,gate),r['alpha'])
            predictions[r['name']]=prediction
            losses.append((prediction[keep]-gate['y'][keep]).square().mean())
            tm=to_cuda(r['threshold'],torch.float64)
            detection.append(metric(gate['y'][onset],prediction[onset],tm));del model
        means[family]=torch.stack(losses).mean()
        # These scalar values originated on CUDA; convert back for decision arithmetic.
        recalls=to_cuda([d['recall'] if d['recall'] is not None else 0 for d in detection],torch.float64)
        fprs=to_cuda([d['false_alarm_rate'] for d in detection],torch.float64)
        family_vectors[family]=(recalls.mean(),fprs.mean())
        gate_metrics[family]=dict(replicates=detection,mean_recall=recalls.mean().item(),mean_fpr=fprs.mean().item())
    sup=support(gate);rc=c['refinement'];supported=(sup['onset']['episodes']>=rc['min_onset_episode_groups'] and sup['onset']['event_days']>=rc['min_onset_event_days'])
    candidate='C' if bool((means['C']<=means['D']).item()) else 'D'
    recall,fpr=family_vectors[candidate];base_rec=to_cuda(gate_metrics['A_T']['recall'] or 0);base_fpr=to_cuda(gate_metrics['A_T']['false_alarm_rate'])
    performance=(means[candidate]<=.95*means['A_T'])&(means[candidate]<means['B'])
    detection_ok=(recall>=torch.maximum(base_rec,family_vectors['B'][0])-.05)&(fpr<=torch.minimum(base_fpr,family_vectors['B'][1])+.02)
    admitted=supported and bool(performance.item()) and bool(detection_ok.item())
    save_part(out/'training_gate_predictions.csv.gz',gate,predictions)
    # Durable decision precedes ALL new outer measurement access.
    save(out/'refinement_gate.json',dict(admitted=admitted,selected_family=candidate,support_sufficient=supported,
        performance_passed=bool(performance.item()),detection_passed=bool(detection_ok.item()),support=sup,
        mean_brier={k:v.item() for k,v in means.items()},onset_detection=gate_metrics,
        source_sha=source,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),outer_measurements_loaded=False,
        reason='admitted' if admitted else 'predeclared training performance, detection or episode-support gate not met'))
    save(out/'training_integrity.json',dict(**checks,io_slices=data.io_records,baseline_checkpoint_sha256=sha256(private/'baseline.pt'),
        normalization_sha256=sha256(private/'normalization.pt'),test_access=False,original_target_constants_frozen=True,
        no_later_predictor_preprocessing=True,training_evaluation_baseline_identical=True,historical_transfer_has_baseline_mismatch=True))
    print('TRAINING GATE',read(out/'refinement_gate.json'),flush=True)


def load_model(c,data,private,family,name):
    norm=torch.load(private/'normalization.pt',map_location='cuda',weights_only=False)
    model=build_model(family,c['correction'],norm['mean'],norm['scale'],data.blocks,data.W,0)
    stored=torch.load(private/(name+'.pt'),map_location='cuda',weights_only=False)
    model.load_state_dict(stored['state']);model.eval();return model


def analyze_population(c,part,predictions,thresholds,base_key,family_keys):
    result=dict(support=support(part),per_model={},paired={},family_mean={},alignment={})
    for subset,keep in [('all_time',part['eligible']),('onset',part['eligible']&~part['active'])]:
        y=part['y'][keep];days=part['day'][keep];losses={}
        for name,p in predictions.items():
            result['per_model'].setdefault(name,{})[subset]=metric(y,p[keep],thresholds[name])
            losses[name]=(p[keep]-y).square()
            if subset=='all_time' and name!=base_key:
                result['alignment'][name]=alignment(y,predictions[base_key][keep],p[keep])
        family_losses={base_key:losses[base_key]}
        for family,keys in family_keys.items():
            family_losses[family]=torch.stack([losses[k] for k in keys]).mean(0)
            result['family_mean'].setdefault(family,{})[subset]=dict(brier=family_losses[family].mean().item(),
                seed_briers=[losses[k].mean().item() for k in keys],aggregation='mean loss over seeds; not ensemble probability')
        for name,loss in family_losses.items():
            if name==base_key:continue
            for reference in [base_key]+(['B'] if name in ('C','D') else [])+(['C'] if name=='D' else []):
                result['paired'][f'{name}_minus_{reference}_{subset}']=paired_summary(family_losses[reference],loss,days,c['bootstrap'])
        if subset=='all_time':
            for family,keys in family_keys.items():
                # Mean alignment terms over seeds computed on GPU; no ensemble diagnostic.
                p=torch.stack([predictions[k][keep] for k in keys]);base=predictions[base_key][keep]
                delta=p-base;error=y-base
                aligned=2*(delta*error).mean();magnitude=delta.square().mean()
                observed=(error.square()[None]-(y[None]-p).square()).mean()
                assert torch.abs(observed-aligned+magnitude)<1e-10
                result['alignment'][family+'_seed_mean']=dict(twice_alignment=aligned.item(),squared_magnitude=magnitude.item(),improvement=observed.item())
    return result


def historical_reference(data):
    with open('results/tables/baseline_predictions.csv') as stream:
        rows=[r for r in csv.DictReader(stream) if r['model']=='heterogeneity']
    adapter=SavedBaseline(to_cuda([int(r['origin']) for r in rows],torch.long),to_cuda([float(r['probability']) for r in rows],torch.float64))
    # Verify independently saved Stage2 references and known labels on GPU, not CPU arithmetic.
    with open('results/stage2/matched_predictions.csv') as stream:
        rows=[r for r in csv.DictReader(stream) if r['model']=='A' and r['split']=='validation']
    origins=to_cuda([int(r['origin']) for r in rows],torch.long)
    expected=to_cuda([float(r['probability']) for r in rows],torch.float64)
    error=(adapter.predict(origins)-expected).abs().max()
    assert error<1e-12
    return adapter,dict(saved_probability_maximum_difference=error.item(),gpu_lookup=True,tree_inference_port=False)


def evaluation(c,out,private):
    gate=read(out/'refinement_gate.json')
    if gate['admitted'] and not (out/'refinement_complete.json').exists():
        raise RuntimeError('Complete or explicitly defer admitted refinement before outer scoring')
    selected=read(out/'selected.json');base_alarm=to_cuda(read(out/'baseline_alarm.json')['threshold'],torch.float64)
    data=PilotData(c);stored=torch.load(private/'baseline.pt',map_location='cuda',weights_only=False)
    baseline=GPUQuantileBoost.from_state(stored['baseline']);data.feature_free=stored['feature_free']
    # Training-only gate is already durable. Only now read outer development measurements.
    data.load('validation');start=time.perf_counter()
    part=data.prepare(data.splits['validation']['origins']);part['p']=baseline.predict(part['X'])
    torch.cuda.synchronize();preparation=time.perf_counter()-start
    predictions={'A_T':part['p']};thresholds={'A_T':base_alarm};family_keys={};inference=[]
    for family,record in selected.items():
        family_keys[family]=[]
        for rep in record['replicates']:
            model=load_model(c,data,private,family,rep['name'])
            before=time.perf_counter();a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);a.record()
            r=predict_correction(model,part);p=corrected_probability(part['p'],r,rep['alpha']);b.record();torch.cuda.synchronize()
            inference.append(dict(model=rep['name'],resident_prepared_inference_wall_seconds=time.perf_counter()-before,cuda_event_span_seconds=a.elapsed_time(b)/1000))
            predictions[rep['name']]=p;thresholds[rep['name']]=to_cuda(rep['threshold'],torch.float64);family_keys[family].append(rep['name']);del model
    primary=analyze_population(c,part,predictions,thresholds,'A_T',family_keys)
    save(out/'primary_metrics.json',primary);save_part(out/'validation_predictions.csv.gz',part,predictions)
    adapter,agreement=historical_reference(data)
    indices=torch.searchsorted(part['origins'],data.historical_origins)
    assert torch.equal(part['origins'][indices],data.historical_origins)
    panel={k:v[indices] for k,v in part.items() if isinstance(v,torch.Tensor) and v.shape[0]==len(part['origins'])}
    panel_base=adapter.predict(panel['origins']);pp={'A_H':panel_base};tt={'A_H':to_cuda(.055595092652235494,torch.float64)}
    # The historical A_H alarm is its saved training-selected rule; transferred rules remain training-frozen A_T rules.
    pp['A_T']=panel['p'];tt['A_T']=base_alarm
    for family,record in selected.items():
        for rep in record['replicates']:
            model=load_model(c,data,private,family,rep['name'])
            r=predict_correction(model,panel,base=panel_base)
            pp[rep['name']]=corrected_probability(panel_base,r,rep['alpha']);tt[rep['name']]=to_cuda(rep['threshold'],torch.float64);del model
    reference=analyze_population(c,panel,pp,tt,'A_H',family_keys)
    reference.update(agreement=agreement,interpretation='transferred correction: different baseline from correction training; no outer selection',
                     historical_baseline_artifact='saved predictions only',alarm_transfer_mismatch=True)
    with open('results/stage2/validation_panel.csv') as stream:
        old={int(r['origin']):r for r in csv.DictReader(stream)}
    order=panel['origins'].cpu().tolist()
    assert torch.equal(panel['y'],to_cuda([int(old[o]['label']) for o in order],torch.float64))
    assert torch.equal(panel['eligible'],to_cuda([old[o]['eligible']=='True' for o in order],torch.bool))
    assert torch.equal(panel['active'],to_cuda([old[o]['current_active']=='True' for o in order],torch.bool))
    save(out/'historical_panel_metrics.json',reference);save_part(out/'historical_transferred_predictions.csv.gz',panel,pp)
    save(out/'inference_timings.json',dict(primary_preparation_and_baseline_seconds=preparation,replicates=inference,
            full_pipeline=complete_inference_timing(c,data,baseline,private,selected),io_slices=data.io_records,
            measurement_scope='Complete runtime from parsed resident raw histories; archival I/O and checkpoints separate; no CPU benchmark'))
    save(out/'evaluation_complete.json',dict(complete=True,test_access=False,primary_origins=len(part['p']),
        baseline_checkpoint_sha256=sha256(private/'baseline.pt'),refinement_ran=gate['admitted'],
        information=dict(aggregate_features=1158,aggregate_numeric_bytes_fp64=9264,full_history_values_read=3900,
             full_history_value_bytes_fp64=31200,full_mask_unpacked_bytes=3900,sensor_ids_int64_bytes=2600,
             note='All sensors read for summaries. Payloads exclude framing, compression and reusable metadata. GPU local channels are derived, not additional telemetry.')))
    print('PRIMARY SEED MEAN',primary['family_mean'],flush=True)
    print('HISTORICAL TRANSFER SEED MEAN',reference['family_mean'],flush=True)


def complete_inference_timing(c,data,baseline,private,selected):
    # Fixed timestamp-spaced 128 input origins; no label reading in timed function.
    allids=data.splits['validation']['origins']
    indices=torch.linspace(0,len(allids)-1,128,device='cuda').long()
    origins=to_cuda(allids,torch.long)[indices]
    from traffic_risk_twins.residual_gpu.data import transform,aggregate_features,local_features
    records=[]
    models={f:load_model(c,data,private,f,selected[f]['replicates'][0]['name']) for f in selected}
    def call(f):
        hi=origins[:,None]+torch.arange(-11,1,device='cuda');m=data.mask[hi];x=transform(data.raw[hi],m,data.feature_free)
        X=aggregate_features(x,m,data.blocks,data.calendar[origins]);p=baseline.predict(X)
        if f!='A_T':
            Z=local_features(x,m,X[:,:192].reshape(-1,12,16),data.blocks)
            p=corrected_probability(p,models[f](X,p,Z,m.permute(0,2,1).any(-1)),selected[f]['replicates'][0]['alpha'])
        return p
    with torch.no_grad():
        start=time.perf_counter()
        for f in ['A_T','B','C','D']:call(f)
        torch.cuda.synchronize();warmup=time.perf_counter()-start
        for repeat in range(3):
            for f in (['A_T','B','C','D'] if repeat%2==0 else ['D','C','B','A_T']):
                a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
                torch.cuda.synchronize();start=time.perf_counter();a.record();call(f);b.record();torch.cuda.synchronize()
                records.append(dict(family=f,repeat=repeat,origins=128,wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=a.elapsed_time(b)/1000))
    return dict(warmup_seconds=warmup,repeats=records,seed_used=c['correction']['seeds'][0])


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['audit','train','evaluate','refine'],required=True)
    p.add_argument('--run-id',default='pilot01');p.add_argument('--source-sha',required=True);args=p.parse_args()
    c=read('configs/residual_pilot.json');out=Path(c['output'])/args.run_id;private=Path('checkpoints/residual_pilot')/args.run_id
    out.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    marker=out/(args.mode+'_run.json')
    if marker.exists():raise FileExistsError('Preserve completed invocation')
    started=time.perf_counter()
    if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; CPU experimental fallback prohibited')
    assert torch.cuda.device_count()==1
    prop=torch.cuda.get_device_properties(0)
    assert prop.name==c['resource']['device'],prop.name
    torch.cuda.set_per_process_memory_fraction(c['resource']['max_allocated_vram_bytes']/prop.total_memory)
    torch.set_default_device('cuda');torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.cuda.reset_peak_memory_stats()
    a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);a.record()
    if args.mode=='audit':
        with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,torch.profiler.ProfilerActivity.CUDA]) as profiler:
            checks=scientific_checks(c)
        device_events=[e for e in profiler.events() if e.device_type==torch.autograd.DeviceType.CUDA]
        checks['profiled_device_activity_seconds']=sum(e.time_range.elapsed_us() for e in device_events)/1e6
        checks['profiled_kernel_seconds']=sum(e.time_range.elapsed_us() for e in device_events if not any(t in e.name.lower() for t in ('memcpy','memset')))/1e6
        checks['profiled_cuda_events']=len(device_events)
        save(out/'gpu_checks.json',checks)
    elif args.mode=='train':training(c,out,private,args.source_sha)
    elif args.mode=='evaluate':evaluation(c,out,private)
    else:
        from traffic_risk_twins.residual_gpu.selection import refinement
        refinement(c,out,private,args.source_sha)
    b.record();torch.cuda.synchronize()
    assert torch.cuda.max_memory_allocated()<=c['resource']['max_allocated_vram_bytes']
    save(marker,dict(complete=True,mode=args.mode,source_sha=args.source_sha,config_sha256=sha256('configs/residual_pilot.json'),
        environment=env_record(args.source_sha),internal_wall_seconds=time.perf_counter()-started,
        cuda_event_span_seconds=a.elapsed_time(b)/1000,
        cuda_timing_qualification='CUDA events measure synchronized device timeline spans including host gaps; not a sum of active kernel durations',
        peak_vram_allocated_bytes=torch.cuda.max_memory_allocated(),peak_vram_reserved_bytes=torch.cuda.max_memory_reserved(),
        host_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,test_access=False))
    print(args.mode,'complete',read(marker),flush=True)


if __name__=='__main__':main()
