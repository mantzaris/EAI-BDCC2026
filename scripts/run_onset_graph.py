"""Registered GPU study: chronological fitting, nulls, then frozen evaluation."""
import argparse
import datetime
import gzip
import csv
from pathlib import Path
import resource
import time
import torch
from traffic_risk_twins.residual_gpu.baseline import GPUQuantileBoost
from traffic_risk_twins.residual_gpu.data import to_cuda,sha256
from traffic_risk_twins.residual_gpu.evaluation import support
from traffic_risk_twins.onset_graph.data import StudyData,subset
from traffic_risk_twins.onset_graph.graphs import dependency_graph,graph_summary,rewire,GraphFeatures
from traffic_risk_twins.onset_graph.models import build,predict
from traffic_risk_twins.onset_graph.training import fit,choose_alpha
from traffic_risk_twins.onset_graph.calibration import fit_calibration,apply_calibration,alarm_cutoff,json_calibration
from traffic_risk_twins.onset_graph.evaluation import onset,metric,population,ranking_curve
from traffic_risk_twins.onset_graph.io import read,save,save_weights,load_weights,restore_state,save_predictions
from run_residual_gpu import env_record


def fold_spec(c,name):return next(f for f in c['folds'] if f['name']==name)


def paths(c,run,fold):
    out=Path(c['output'])/run/fold;art=Path(c['artifacts'])/run/fold
    out.mkdir(parents=True,exist_ok=True);art.mkdir(parents=True,exist_ok=True);return out,art


def setup_parts(c,fold,art,fit_anchor=False):
    data=StudyData(c);data.load('train');roles=data.fold_roles(fold['cuts'])
    if not fit_anchor:
        saved=load_weights(art/'anchor.pt.gz');data.feature_free=saved['feature_free'];anchor=GPUQuantileBoost.from_state(saved['baseline'])
    else:anchor=None
    return data,roles,anchor


def prepared(data,roles,anchor):
    parts={}
    previous=None
    for name,role in roles.items():
        ids=to_cuda(role['origins'],torch.long)
        first=data.time_ns[ids.min()-11];last=data.time_ns[ids.max()+6]
        assert previous is None or first>previous;previous=last
        if name=='anchor':continue
        parts[name]=data.prepare(ids);parts[name]['p']=anchor.predict(parts[name]['X'])
    return parts


def fit_trees(data,role,config):
    part=data.prepare(role['origins'][::3]);keep=part['eligible']
    model=GPUQuantileBoost(config);start=time.perf_counter();model.fit(part['X'][keep],part['y'][keep]);torch.cuda.synchronize()
    return model,dict(n=int(keep.sum().item()),positives=int(part['y'][keep].sum().item()),wall_seconds=time.perf_counter()-start)


def fit_anchor(c,data,roles,fold,art,out,source):
    cut=fold['cuts'][0];selection_start=cut-c['anchor_selection_days']
    early=data.interval(0,selection_start,fold['cuts']+[selection_start])
    later=data.interval(selection_start,cut,fold['cuts']+[selection_start])
    data.fit_free(early['rows']);selection=data.prepare(later['origins']);keep=onset(selection)
    attempts=[]
    for l2 in c['baseline_l2_choices']:
        settings=dict(c['baseline'],l2=l2);model,record=fit_trees(data,early,settings)
        p=model.predict(selection['X']);score=(p[keep]-selection['y'][keep]).square().mean()
        file=art/f'anchor_tune_{l2}.pt.gz';save_weights(file,dict(baseline=model.state_dict(),feature_free=data.feature_free,source_sha=source))
        attempts.append(dict(l2=l2,selection_onset=score.item(),selection_all_time=(p-selection['y']).square().mean().item(),
            checkpoint=str(file),sha256=sha256(file),**record));del model
    chosen=int(to_cuda([r['selection_onset'] for r in attempts],torch.float64).argmin().item());settings=dict(c['baseline'],l2=attempts[chosen]['l2'])
    del selection;data.fit_free(roles['anchor']['rows']);anchor,record=fit_trees(data,roles['anchor'],settings)
    save_weights(art/'anchor.pt.gz',dict(baseline=anchor.state_dict(),feature_free=data.feature_free,source_sha=source))
    union=dict(origins=torch.cat([to_cuda(roles[k]['origins'],torch.long)[::3] for k in ('anchor','correction')]))
    part=data.prepare(union['origins']);keep=part['eligible'];start=time.perf_counter()
    refresh=GPUQuantileBoost(settings).fit(part['X'][keep],part['y'][keep]);torch.cuda.synchronize()
    save_weights(art/'refreshed.pt.gz',dict(baseline=refresh.state_dict(),feature_free=data.feature_free,source_sha=source))
    save(out/'anchor_fits.json',dict(attempts=attempts,selected_l2=settings['l2'],anchor=record,
        refresh=dict(n=int(keep.sum().item()),positives=int(part['y'][keep].sum().item()),wall_seconds=time.perf_counter()-start),
        anchor_training_stride=3,correction_training_stride=3,refresh_exact_union=True,source_sha=source,
        old_A_T='Separate unchanged reference,54days stride12',no_correction_trained_against_in_sample_refresh=True))
    return anchor


def family_fit(c,name,kind,parts,data,W,mean,scale,art,out,source,graph_key,internal_only=False,fixed_reg=None,masked=False):
    records=[];tuning=[]
    choices=c['correction']['regularization'] if fixed_reg is None else []
    for reg in choices:
        filename=f'{name}_tune_{reg}.pt.gz'
        model,record=fit(kind,c['correction'],parts,mean,scale,data.blocks,W,c['correction']['tuning_seed'],reg,art/filename,graph_key,source,internal_only,masked)
        records.append(record);tuning.append(record);save(out/(name+'_attempts.json'),records);del model
    if fixed_reg is None:
        scores=to_cuda([r['best_early_onset'] for r in tuning],torch.float64)
        best=len(tuning)-1-int(scores.flip(0).argmin().item());reg=tuning[best]['regularization']
    else:reg=fixed_reg
    replicates=[]
    for seed in c['correction']['seeds']:
        key=f'{name}_{seed}';file=art/(key+'.pt.gz')
        model,record=fit(kind,c['correction'],parts,mean,scale,data.blocks,W,seed,reg,file,graph_key,source,internal_only,masked)
        alpha,shrink=choose_alpha(model,parts['shrink'],c['correction']['alpha_grid'])
        q=predict(model,parts['calibration'],alpha);keep=onset(parts['calibration'])
        calibrator=fit_calibration(q[keep],parts['calibration']['y'][keep],c['calibration'])
        calibrated=apply_calibration(q,calibrator)
        raw_cut=alarm_cutoff(q[keep],parts['calibration']['y'][keep]);cal_cut=alarm_cutoff(calibrated[keep],parts['calibration']['y'][keep])
        rep=dict(key=key,kind=kind,seed=seed,regularization=reg,alpha=alpha,checkpoint=str(file),graph_key=graph_key,
            internal_only=internal_only,calibrator=json_calibration(calibrator),raw_cutoff=raw_cut.item(),calibrated_cutoff=cal_cut.item(),
            calibration_raw=metric(parts['calibration']['y'][keep],q[keep],raw_cut,parts['calibration']['time_ns'][keep],parts['calibration']['day'][keep]),
            calibration_calibrated=metric(parts['calibration']['y'][keep],calibrated[keep],cal_cut,parts['calibration']['time_ns'][keep],parts['calibration']['day'][keep]))
        record.update(shrinkage=shrink,replicate=rep);records.append(record);replicates.append(rep)
        save(out/(name+'_attempts.json'),records);del model
    return dict(kind=kind,regularization=reg,replicates=replicates)


def get_graph(data,art,key,graphs):
    if key in graphs:return graphs[key]
    if key=='dependency':graphs[key]=load_weights(art/'dependency.pt.gz')['W']
    elif key=='self':graphs[key]=torch.eye(len(data.W),device='cuda',dtype=data.W.dtype)
    elif '_rewire_' in key:
        base,seed=key.split('_rewire_');original=get_graph(data,art,base,graphs)
        graphs[key]=rewire(original,int(seed))[0]
    elif key.endswith('_mismatch'):
        base=key[:-9];original=get_graph(data,art,base,graphs)
        gen=torch.Generator(device='cuda').manual_seed(20261006);perm=torch.randperm(len(original),device='cuda',generator=gen)
        graphs[key]=original[perm][:,perm]
    else:raise KeyError(key)
    return graphs[key]


def load_model(c,data,art,rep,graphs,override_graph=None):
    checkpoint=load_weights(rep['checkpoint']);W=get_graph(data,art,override_graph or rep['graph_key'],graphs)
    state=checkpoint['state'];model=build(rep['kind'],c['correction'],state['mean'],state['scale'],data.blocks,W,rep['seed'],rep['internal_only'])
    return restore_state(model,state)


@torch.no_grad()
def controls_prediction(part,anchor,refresh,mono):
    return {'A_G':part['p'],'R_union':refresh.predict(part['X']),'A_mono':apply_calibration(part['p'],mono)}


@torch.no_grad()
def collect(c,data,art,part,metadata,graphs,calibrated=False,sensitivity=False):
    refresh=GPUQuantileBoost.from_state(load_weights(art/'refreshed.pt.gz')['baseline'])
    predictions=controls_prediction(part,None,refresh,metadata['mono']);thresholds={};families={k:[k] for k in predictions};times=[]
    for name,p in list(predictions.items()):
        rec=metadata['controls'][name]
        if calibrated:predictions[name]=apply_calibration(p,rec['calibrator'])
        thresholds[name]=to_cuda(rec['calibrated_cutoff' if calibrated else 'raw_cutoff'],torch.float64)
    for name,f in metadata['families'].items():
        families[name]=[]
        for rep in f['replicates']:
            model=load_model(c,data,art,rep,graphs);start=time.perf_counter();a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);a.record()
            p=predict(model,part,rep['alpha']);b.record();torch.cuda.synchronize()
            times.append(dict(key=rep['key'],origins=len(p),wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=a.elapsed_time(b)/1000))
            if calibrated:p=apply_calibration(p,rep['calibrator'])
            predictions[rep['key']]=p;families[name].append(rep['key'])
            thresholds[rep['key']]=to_cuda(rep['calibrated_cutoff' if calibrated else 'raw_cutoff'],torch.float64)
            del model
    return predictions,thresholds,families,times


def train_fold(c,fold,out,art,source):
    if (out/'training_complete.json').exists():raise FileExistsError('Completed fold preserved')
    data,roles,_=setup_parts(c,fold,art,True);anchor=fit_anchor(c,data,roles,fold,art,out,source)
    parts=prepared(data,roles,anchor);mean=parts['correction']['X'][parts['correction']['eligible']].mean(0)
    scale=parts['correction']['X'][parts['correction']['eligible']].std(0).clamp_min(.01)
    Wf,finfo=dependency_graph(data,roles['anchor']['rows']);save_weights(art/'dependency.pt.gz',dict(W=Wf,source_sha=source))
    graphs={'distance':data.W,'dependency':Wf}
    save(out/'graphs.json',dict(distance=graph_summary(data.W,data.blocks),dependency=dict(**graph_summary(Wf,data.blocks),estimation=finfo)))
    keep=onset(parts['correction']);mono=fit_calibration(parts['correction']['p'][keep],parts['correction']['y'][keep],c['calibration'])
    metadata=dict(fold=fold,source_sha=source,mono=json_calibration(mono),controls={},families={})
    refresh=GPUQuantileBoost.from_state(load_weights(art/'refreshed.pt.gz')['baseline'])
    base_preds=controls_prediction(parts['calibration'],anchor,refresh,mono);keep=onset(parts['calibration'])
    for name,p in base_preds.items():
        cal=fit_calibration(p[keep],parts['calibration']['y'][keep],c['calibration']);q=apply_calibration(p,cal)
        rc=alarm_cutoff(p[keep],parts['calibration']['y'][keep]);cc=alarm_cutoff(q[keep],parts['calibration']['y'][keep])
        metadata['controls'][name]=dict(calibrator=json_calibration(cal),raw_cutoff=rc.item(),calibrated_cutoff=cc.item(),
            calibration_raw=metric(parts['calibration']['y'][keep],p[keep],rc,parts['calibration']['time_ns'][keep],parts['calibration']['day'][keep]),
            calibration_calibrated=metric(parts['calibration']['y'][keep],q[keep],cc,parts['calibration']['time_ns'][keep],parts['calibration']['day'][keep]))
    for name in c['correction']['families']:
        print('FIT',fold['name'],name,flush=True);graph_key='dependency' if name=='F' else 'distance'
        metadata['families'][name]=family_fit(c,name,name,parts,data,graphs[graph_key],mean,scale,art,out,source,graph_key)
        save(out/'models.json',metadata)
    metadata['families']['E_internal']=family_fit(c,'E_internal','E',parts,data,data.W,mean,scale,art,out,source,'distance',
        internal_only=True,fixed_reg=metadata['families']['E']['regularization'])
    shrink=parts['shrink'];pp,tt,ff,_=collect(c,data,art,shrink,metadata,graphs)
    keep=onset(shrink);scores={name:torch.stack([(pp[k][keep]-shrink['y'][keep]).square().mean() for k in keys]).mean() for name,keys in ff.items()}
    def choose(names):return names[int(torch.stack([scores[n] for n in names]).argmin().item())]
    G=choose(c['graph']['strong_aggregate_candidates']);X=choose(c['graph']['expanded_candidates']);local=choose(['C','D','S','E','F'])
    metadata.update(strong_aggregate=G,expanded=X,budget_candidate=local,shrinkage_mean_onset={k:v.item() for k,v in scores.items()})
    save(out/'models.json',metadata)
    gate=parts['gate'];raw,th,families,_=collect(c,data,art,gate,metadata,graphs)
    calibrated,ct,_,_=collect(c,data,art,gate,metadata,graphs,True)
    contrasts=[('C',G),('D','C'),(X,'D'),(X,G)]
    raw_result=population(gate,raw,th,families,contrasts,c['bootstrap']);cal_result=population(gate,calibrated,ct,families,[],c['bootstrap'])
    save(out/'gate_raw_metrics.json',raw_result);save(out/'gate_calibrated_metrics.json',cal_result)
    save_predictions(out/'gate_raw_predictions.csv.gz',gate,raw);save_predictions(out/'gate_calibrated_predictions.csv.gz',gate,calibrated)
    if fold['name']=='main':
        local_r=raw_result['families'][local];gr=raw_result['families'][G];lc=cal_result['families'][local];gc=cal_result['families'][G]
        on=raw_result['support']['onset'];target=c['budget_extension'];pr=c['practical']
        lr,gg=to_cuda(local_r['onset']['brier']),to_cuda(gr['onset']['brier'])
        support_ok=on['episodes']>=target['min_onset_groups'] and on['event_days']>=target['min_event_days']
        performance=(lr<=.99*gg)&(gg-lr>=.0001)&(to_cuda(local_r['all_time']['brier'])<=1.02*to_cuda(gr['all_time']['brier']))
        detection=(to_cuda(lc['onset']['mean_recall'])>=to_cuda(gc['onset']['mean_recall'])-.02)&(to_cuda(lc['onset']['mean_fpr'])<=to_cuda(gc['onset']['mean_fpr'])+.01)
        calibration=to_cuda(lc['onset']['brier'])<=to_cuda(gc['onset']['brier'])
        admitted=support_ok and bool((performance&detection&calibration).item())
        save(out/'budget_decision.json',dict(admitted=admitted,candidate=local,G=G,support_sufficient=support_ok,
            performance=bool(performance.item()),detection=bool(detection.item()),calibration=bool(calibration.item()),support=raw_result['support'],
            source_sha=source,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_candidate_outer_evaluated=False))
    save(out/'split_manifest.json',dict(roles={k:dict(days=v['days'],origins=v['origins'].tolist(),first_row=int(v['rows'][0]),last_row=int(v['rows'][-1])) for k,v in roles.items()},
        support={k:support(v) for k,v in parts.items()},validation_exposed_days=data.splits['validation']['days'],untouched_validation_days=[],test_access=False,io_slices=data.io_records))
    save(out/'training_complete.json',dict(complete=True,source_sha=source,models=len(metadata['families']),G=G,X=X,
        anchor_sha256=sha256(art/'anchor.pt.gz'),test_access=False))
    print('TRAIN COMPLETE',fold['name'],'G=',G,'X=',X,flush=True)


def train_nulls(c,fold,out,art,source):
    if (out/'nulls_complete.json').exists():raise FileExistsError('Preserve null study')
    data,roles,anchor=setup_parts(c,fold,art);parts=prepared(data,roles,anchor);metadata=read(out/'models.json')
    mean=parts['correction']['X'][parts['correction']['eligible']].mean(0);scale=parts['correction']['X'][parts['correction']['eligible']].std(0).clamp_min(.01)
    graphs={'distance':data.W};manifest={};targets=list(dict.fromkeys(['D',metadata['expanded']]))
    for target in targets:
        base='dependency' if target=='F' else 'distance';original=get_graph(data,art,base,graphs)
        if target not in ('D','F'):
            name=target+'_self';W=get_graph(data,art,'self',graphs)
            metadata['families'][name]=family_fit(c,name,target,parts,data,W,mean,scale,art,out,source,'self')
        for seed in c['graph']['null_seeds']:
            key=base+'_rewire_'+str(seed)
            if key not in graphs:
                W,stats=rewire(original,seed,c['graph']['rewire_rounds'],c['graph']['rewire_batch_pairs']);graphs[key]=W
                manifest[key]=dict(**stats,**graph_summary(W,data.blocks))
            name=target+'_rewire_'+str(seed);print('NULL',name,flush=True)
            metadata['families'][name]=family_fit(c,name,target,parts,data,graphs[key],mean,scale,art,out,source,key)
            save(out/'models_with_nulls.json',metadata)
    save(out/'null_graphs.json',manifest);save(out/'models_with_nulls.json',metadata)
    save(out/'nulls_complete.json',dict(complete=True,source_sha=source,targets=targets,identity_D_F='matched C reused',test_access=False))


def evaluate(c,fold,out,art,source):
    if (out/'evaluation_complete.json').exists():raise FileExistsError('Preserve evaluation')
    assert read(out/'nulls_complete.json')['complete'];decision=read(out/'budget_decision.json')
    data=StudyData(c);stored=load_weights(art/'anchor.pt.gz');data.feature_free=stored['feature_free'];anchor=GPUQuantileBoost.from_state(stored['baseline'])
    data.load('validation');start=time.perf_counter();part=data.prepare(data.splits['validation']['origins']);part['p']=anchor.predict(part['X']);torch.cuda.synchronize()
    preparation=time.perf_counter()-start;metadata=read(out/'models_with_nulls.json');graphs={'distance':data.W}
    raw,th,families,times=collect(c,data,art,part,metadata,graphs);cal,ct,_,cal_times=collect(c,data,art,part,metadata,graphs,True)
    G,X=metadata['strong_aggregate'],metadata['expanded'];contrasts=[('C',G),('D','C'),(X,'D'),(X,G)]
    raw_metrics=population(part,raw,th,families,contrasts,c['bootstrap']);cal_metrics=population(part,cal,ct,families,[],c['bootstrap'])
    save(out/'validation_raw_metrics.json',raw_metrics);save(out/'validation_calibrated_metrics.json',cal_metrics)
    save_predictions(out/'validation_raw_predictions.csv.gz',part,raw);save_predictions(out/'validation_calibrated_predictions.csv.gz',part,cal)
    blocks={}
    for i,(lo,hi) in enumerate(c['validation_blocks']):
        import pandas as pd
        lower=pd.Timestamp(lo).value//(86400*10**9);upper=pd.Timestamp(hi).value//(86400*10**9)
        take=(part['day']>=lower)&(part['day']<=upper);block=subset(part,take)
        # All candidates retained; block comparisons are descriptive robustness.
        blocks[str(i+1)]=dict(dates=[lo,hi],raw=population(block,{k:v[take] for k,v in raw.items()},th,families,contrasts,c['bootstrap']),
            calibrated=population(block,{k:v[take] for k,v in cal.items()},ct,families,[],c['bootstrap']))
    save(out/'validation_blocks.json',blocks)
    null_pairs=[]
    for target in list(dict.fromkeys(['D',X])):
        self_name='C' if target in ('D','F') else target+'_self';null_pairs.append((target,self_name))
        null_pairs.extend((target,target+'_rewire_'+str(seed)) for seed in c['graph']['null_seeds'])
    null_pairs.append(('E','E_internal'))
    # These are mechanism diagnostics outside the declared four-contrast family.
    save(out/'topology_metrics.json',population(part,raw,th,families,null_pairs,c['bootstrap'],all_pairs=False,primary_family=False))
    sensitivity={};curves={};keep=onset(part)
    for target in list(dict.fromkeys(['D',X])):
        for graph in ['self']+[(('dependency' if target=='F' else 'distance')+'_rewire_'+str(seed)) for seed in c['graph']['null_seeds']]+[('dependency' if target=='F' else 'distance')+'_mismatch']:
            for rep in metadata['families'][target]['replicates']:
                model=load_model(c,data,art,rep,graphs,graph);p=predict(model,part,rep['alpha']);key=rep['key']+'__eval_'+graph
                sensitivity[key]=dict(onset=metric(part['y'][keep],p[keep],th[rep['key']],part['time_ns'][keep],part['day'][keep]),
                    all_time=metric(part['y'][part['eligible']],p[part['eligible']],th[rep['key']],part['time_ns'][part['eligible']],part['day'][part['eligible']]),
                    interpretation='Evaluation perturbation, not retrained competitor');del model
    for family in list(dict.fromkeys(['A_G',G,'C','D',X])):
        key=families[family][0];curves[family]=ranking_curve(part['y'][keep],raw[key][keep])
    save(out/'sensitivity_metrics.json',sensitivity);save(out/'ranking_curves.json',curves)
    illustration(c,data,part,raw,families,out)
    save(out/'inference_timings.json',dict(preparation_and_anchor_seconds=preparation,raw_replicates=times,calibrated_replicates=cal_times,
        scope='resident parsed data; feature preparation/anchor separately; model restore and archival IO included in full job ledger',io_slices=data.io_records))
    save(out/'evaluation_complete.json',dict(complete=True,source_sha=source,test_access=False,origins=len(part['p']),
        G=G,X=X,budget_decision_preceded_outer=True,budget_admitted=decision['admitted']))
    print('OUTER COMPLETE', {k:v['onset']['brier'] for k,v in raw_metrics['families'].items()},flush=True)


def illustration(c,data,part,raw,families,out):
    import pandas as pd
    stamp=pd.Timestamp('2017-04-20 08:00').value
    pick=torch.where((part['time_ns']>=stamp)&part['eligible'])[0][0];origin=part['origins'][pick]
    sensors=torch.where(data.blocks==0)[0][:4];history=part['Z'][pick,sensors,:,0]
    ops=GraphFeatures(data.W,data.blocks);summary=ops.summaries(part['X'][pick:pick+1],part['Z'][pick:pick+1])
    save(out/'illustration.json',dict(rule=c['illustration'],origin=origin.item(),timestamp_ns=part['time_ns'][pick].item(),
        sensor_column_indices=sensors.tolist(),sensor_history_scaled=history.tolist(),
        regional_mean_scaled=(part['X'][pick,:192].reshape(12,16)[:,0]/7).tolist(),
        regional_summary_hops=summary[0,0,:,:6].tolist(),label=part['y'][pick].item(),
        probabilities={k:[raw[n][pick].item() for n in keys] for k,keys in families.items()},
        meaning='Fixed-window transformed illustration, not a population estimate or raw speed export'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['audit','train','nulls','evaluate','replay','budget'],required=True)
    p.add_argument('--fold',default='main');p.add_argument('--run-id',default='study01');p.add_argument('--source-sha',required=True);args=p.parse_args()
    c=read('configs/onset_graph_study.json');fold=fold_spec(c,args.fold);out,art=paths(c,args.run_id,args.fold)
    marker=out/(args.mode+'_run.json')
    if marker.exists():raise FileExistsError('Preserve completed invocation')
    start=time.perf_counter();assert torch.cuda.is_available() and torch.cuda.device_count()==1
    prop=torch.cuda.get_device_properties(0);assert prop.name==c['resource']['device']
    torch.cuda.set_per_process_memory_fraction(c['resource']['max_allocated_vram_bytes']/prop.total_memory)
    torch.set_default_device('cuda');torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);a.record()
    if args.mode=='train':train_fold(c,fold,out,art,args.source_sha)
    elif args.mode=='nulls':train_nulls(c,fold,out,art,args.source_sha)
    elif args.mode=='evaluate':evaluate(c,fold,out,art,args.source_sha)
    elif args.mode=='audit':
        from traffic_risk_twins.onset_graph.checks import audit
        audit(c,out,art,args.source_sha)
    elif args.mode=='replay':
        from traffic_risk_twins.onset_graph.checks import replay
        replay(c,fold,out,art,args.source_sha)
    else:
        if not read(out/'budget_decision.json')['admitted']:raise RuntimeError('Budget gate did not pass')
        from traffic_risk_twins.onset_graph.budget import run_budget
        run_budget(c,fold,out,art,args.source_sha)
    b.record();torch.cuda.synchronize();assert torch.cuda.max_memory_allocated()<=c['resource']['max_allocated_vram_bytes']
    save(marker,dict(complete=True,source_sha=args.source_sha,config_sha256=sha256('configs/onset_graph_study.json'),
        environment=env_record(args.source_sha),internal_wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=a.elapsed_time(b)/1000,
        qualification='Event spans include host gaps; not active kernel totals',peak_vram_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_vram_reserved_bytes=torch.cuda.max_memory_reserved(),host_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,test_access=False))
    print('FINISHED',args.mode,args.fold,flush=True)


if __name__=='__main__':main()
