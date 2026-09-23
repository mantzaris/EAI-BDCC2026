"""CUDA-only descriptive diagnostics and transfer-inclusive frozen inference costs."""
import csv
import gzip
import time
import h5py
import torch
from ..residual_gpu.data import to_cuda, valid, transform, aggregate_features, local_features
from ..residual_gpu.baseline import GPUQuantileBoost
from ..residual_gpu.models import corrected_probability
from ..residual_gpu.evaluation import alignment
from .data import StudyData
from .evaluation import resample
from .calibration import apply_calibration
from .io import read, save, load_weights


def read_predictions(path):
    with gzip.open(path,'rt') as stream:rows=list(csv.DictReader(stream))
    integers=('origins','time_ns','day');booleans=('lower','upper','eligible','active')
    return {key:to_cuda([int(r[key]) if key in integers else r[key]=='True' if key in booleans else float(r[key]) for r in rows],
        torch.long if key in integers else torch.bool if key in booleans else torch.float64) for key in rows[0]}


@torch.no_grad()
def supplement(c,fold,out,art,source):
    from run_onset_graph import load_model
    metadata=read(out/'models_with_nulls.json');families={name:[name] for name in ('A_G','R_union','A_mono')}
    families.update({name:[r['key'] for r in f['replicates']] for name,f in metadata['families'].items()})
    summary={};pairs={}
    for calibration in ('raw','calibrated'):
        rows=read_predictions(out/('validation_'+calibration+'_predictions.csv.gz'))
        reference=read(out/('validation_'+calibration+'_metrics.json'));summary[calibration]={};pairs[calibration]={}
        for endpoint,keep in [('onset',rows['eligible']&~rows['active']),('all_time',rows['eligible'])]:
            y=rows['y'][keep];day=rows['day'][keep];group_loss={}
            for name,keys in families.items():
                p=torch.stack([rows[k][keep] for k in keys]);loss=(p-y).square();group_loss[name]=loss.mean(0)
                score=loss.mean();assert (score-to_cuda(reference['families'][name][endpoint]['brier'],torch.float64)).abs()<1e-12
                record=dict(brier=score.item(),seed_briers=loss.mean(1).tolist(),zero_fraction=(p==0).double().mean().item(),
                    event_contribution=(loss*(y==1)).mean().item(),nonevent_contribution=(loss*(y==0)).mean().item(),
                    mean_probability=p.mean().item(),prevalence=y.mean().item(),
                    mean_detected_groups=to_cuda([reference['models'][k][endpoint]['episodes']['detected_groups'] for k in keys],torch.float64).mean().item(),
                    mean_false_alarm_groups=to_cuda([reference['models'][k][endpoint]['episodes']['false_alarm_groups'] for k in keys],torch.float64).mean().item())
                identities=[alignment(y,rows['A_G'][keep],rows[k][keep]) for k in keys]
                record['alignment']={key:to_cuda([r[key] for r in identities],torch.float64).mean().item() for key in identities[0]}
                summary[calibration].setdefault(name,{})[endpoint]=record
            comparisons=[(local,control) for local in ('C','D','M','S','E','F') for control in ('B','K','R_union','A_mono')]
            comparisons += [(name,'D') for name in ('M','S','E','F')]+[('B','R_union')]
            for a,b in comparisons:
                va,vb=group_loss[a],group_loss[b];d=va-vb
                draws=resample(d[:,None],day,3,c['bootstrap']['replicates'],c['bootstrap']['seed'])[:,0]
                r=dict(difference=d.mean().item(),relative_reduction=(-d.mean()/vb.mean()).item(),
                    pointwise_95=torch.quantile(draws,draws.new_tensor([.025,.975])).tolist(),
                    interpretation='Supplementary unadjusted comparison, not the declared primary family')
                if len(families[a])==len(families[b]):
                    r['paired_seed_differences']=[((rows[ka][keep]-y).square()-(rows[kb][keep]-y).square()).mean().item()
                        for ka,kb in zip(families[a],families[b])]
                pairs[calibration][a+'_minus_'+b+'_'+endpoint]=r
    save(out/'family_diagnostics.json',summary);save(out/'supplementary_pairs.json',pairs)

    setup=time.perf_counter();data=StudyData(c);stored=load_weights(art/'anchor.pt.gz');data.feature_free=stored['feature_free']
    anchor=GPUQuantileBoost.from_state(stored['baseline']);refresh=GPUQuantileBoost.from_state(load_weights(art/'refreshed.pt.gz')['baseline'])
    graphs={'distance':data.W};models={};representatives={}
    for name in c['correction']['families']:
        rep=metadata['families'][name]['replicates'][0];models[name]=load_model(c,data,art,rep,graphs);representatives[name]=rep
    torch.cuda.synchronize();setup_seconds=time.perf_counter()-setup
    all_ids=data.splits['validation']['origins'];index=torch.linspace(0,len(all_ids)-1,128,device='cuda').long().tolist()
    ids=[int(all_ids[i]) for i in index];gpu_ids=to_cuda(ids,torch.long)
    def parse():
        with h5py.File(c['raw_file'],'r') as stream:return [stream['speed/block0_values'][i-11:i+1] for i in ids]
    host=parse()
    def transfer():return torch.stack([to_cuda(h,torch.float64) for h in host])
    raw=transfer()
    def compute(raw,family):
        mask=valid(raw);state=transform(raw,mask,data.feature_free)
        X=aggregate_features(state,mask,data.blocks,data.calendar[gpu_ids])
        if family=='R_union':return refresh.predict(X)
        p=anchor.predict(X)
        if family=='A_mono':return apply_calibration(p,metadata['mono'])
        if family=='A_G':return p
        Z=local_features(state,mask,X[:,:192].reshape(-1,12,16),data.blocks) if family not in ('B','K','M') else None
        r=models[family](X,p,Z,mask.permute(0,2,1).any(-1))
        return corrected_probability(p,r,representatives[family]['alpha'])
    def timed(call):
        torch.cuda.synchronize();start=time.perf_counter();a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        a.record();value=call();b.record();torch.cuda.synchronize()
        return value,dict(wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=a.elapsed_time(b)/1000)
    names=['A_G','R_union','A_mono']+c['correction']['families']
    warm=time.perf_counter()
    for family in names:compute(raw,family).cpu()
    torch.cuda.synchronize();warmup=time.perf_counter()-warm;timings=[]
    for repeat in range(3):
        for family in names if repeat%2==0 else names[::-1]:
            torch.cuda.synchronize();total=time.perf_counter();start=time.perf_counter();host=parse();io=time.perf_counter()-start
            raw,h2d=timed(transfer);p,device=timed(lambda:compute(raw,family));_,d2h=timed(lambda:p.cpu())
            timings.append(dict(family=family,repeat=repeat,origins=128,archival_read_wall_seconds=io,h2d=h2d,
                feature_baseline_correction=device,d2h=d2h,complete_wall_seconds=time.perf_counter()-total))
    save(out/'complete_costs.json',dict(setup_and_all_weights_restore_seconds=setup_seconds,panel_origins=ids,warmup_seconds=warmup,repeats=timings,
        scope='Warm-cache HDF history parsing, transfers, transforms, summaries, anchor, correction, output transfer; no future-label preparation',
        restore_in_setup=True,graph_preparation_in_setup=True,first_seed_only=True,no_cpu_model=True,
        qualification='CUDA event spans include launch/host gaps; not active kernel totals',test_access=False,source_sha=source))
    # Byte accounting is a specified serialization, not a claim about compressed files.
    # Keep graph metadata separate from per-origin payloads. Counts are metadata.
    sensors=len(data.W);edges=int((data.W>0).sum().item());regional_count=16;frames=12
    info=dict(sensors=sensors,regions=regional_count,frames=frames,
        common_summary_float32_bytes=1158*4,common_counts_uint16_bytes=frames*regional_count*2,
        common_region_valid_bitset_bytes=24,common_timestamp_bytes=8,
        local_history_float32_bytes=frames*sensors*4,local_frame_mask_bitset_bytes=(frames*sensors+7)//8,
        local_ids_uint16_bytes=sensors*2,local_derived_input_float32_bytes=frames*sensors*4*4,
        S_additional_summary_float32_bytes=3*frames*regional_count*4,
        graph_CSR_float64_uint32_bytes=edges*(8+4)+(sensors+1)*4,
        sensor_region_uint16_bytes=2*sensors,region_identity_uint16_bytes=2*regional_count,
        note='1158 summary floats already include counts; uint16 count bytes are a disclosed alternative, not double-counted. '
             'C/D/E/F local payload transmits one transformed history plus masks/IDs; deviations/changes derived at receiver. '
             'S transmits 3 extra regional deviation summaries; its coarse contribution is computable from common means and shared graph operators. '
             'All summaries require all-sensor ingestion; no acquisition savings or measured compressed-file savings.',
        all_sensors_read_for_initial_summaries=True,budget_extension_executed=False)
    save(out/'information_cost.json',info)
    # Explicitly verify alignment residuals already asserted by alignment().
    save(out/'supplement_checks.json',dict(saved_metrics_recomputed_on_cuda=True,alignment_identity_checked=True,
        cost_panel_selected_by_timestamps_only=True,future_values_read_for_costs=False,test_access=False,source_sha=source))
