"""Conditional masked-detail diagnostic; no unacquired value enters the policy."""
import time
import torch
from .training import fit_correction,shrink_and_alarm
from .models import predict_correction,corrected_probability
from .evaluation import metric,paired_summary
from .data import to_cuda,sha256


def initial_priority(aggregate):
    means=aggregate[:,:192].reshape(-1,12,16)
    extras=aggregate[:,390:].reshape(-1,12,16,4)
    score=extras[:,-1,:,0].clamp_min(0).sqrt()*torch.exp(-means[:,-1].abs()/2)
    score=score+(means[:,-1]-means[:,-3]).clamp_min(0)
    return score/score.amax(1,keepdim=True).clamp_min(1e-8)


@torch.no_grad()
def choose_regions(model,part,budget,policy,fixed,seed,stop_priority):
    N=len(part['p']);regions=torch.zeros(N,16,device='cuda',dtype=torch.bool)
    stopped=torch.zeros(N,device='cuda',dtype=torch.bool)
    base=initial_priority(part['X']);adj=model.P.T@model.W@model.P
    adj=adj/adj.sum(1,keepdim=True).clamp_min(1e-8)
    rng=torch.Generator(device='cuda').manual_seed(seed)
    if policy=='uniform':order=torch.rand(N,16,device='cuda',generator=rng).argsort(1)
    elif policy=='training_fixed':order=fixed.expand(N,-1)
    elif policy!='aggregate_priority_adaptive':raise ValueError(policy)
    acquired_signal=torch.zeros_like(base)
    for step in range(budget):
        if policy=='aggregate_priority_adaptive':
            score=(base+.25*(acquired_signal@adj)).masked_fill(regions,-torch.inf)
            priority,choice=score.max(1)
            stopped |= priority<stop_priority
        else:choice=order[:,step]
        regions[torch.arange(N,device='cuda'),choice] |= ~stopped
        if policy=='aggregate_priority_adaptive':
            # Reveal through a masking boundary before ANY encoder/selector use.
            reveal=torch.where(regions[:,model.blocks,None,None],part['Z'],torch.zeros_like(part['Z']))
            chunks=[]
            for start in range(0,N,256):
                _,h=model.encode_local(reveal[start:start+256],part['node_mask'][start:start+256],regions[start:start+256])
                chunks.append(h.norm(dim=-1)@model.P/model.P.sum(0).clamp_min(1))
            acquired_signal=torch.cat(chunks)*regions
            acquired_signal=acquired_signal/acquired_signal.amax(1,keepdim=True).clamp_min(1e-8)
    return regions,stopped


def refinement(c,out,private,source):
    # Imported lazily by the GPU runner to keep normal forecasting independent.
    from run_residual_gpu import read,save,save_part,baseline_and_parts
    gate=read(out/'refinement_gate.json')
    if not gate['admitted']:raise RuntimeError('Refinement gate failed; no conditional experiment allowed')
    if (out/'refinement_complete.json').exists():raise FileExistsError('Preserve refinement')
    selected=read(out/'selected.json');family=gate['selected_family']
    data,baseline,parts=baseline_and_parts(c,out,private,False)
    norm=torch.load(private/'normalization.pt',map_location='cuda',weights_only=False)
    models=[];records=[]
    reg=selected[family]['regularization']
    for seed in c['correction']['seeds']:
        name=f'refine_{family}_{seed}'
        model,record=fit_correction(family,c['correction'],parts,norm['mean'],norm['scale'],data.blocks,data.W,
            seed,reg,private/(name+'.pt'),max_epochs=c['refinement']['masked_fit_epochs'],masked=True)
        shrink=shrink_and_alarm(model,parts['shrinkage'],c['correction']['alpha_grid'])
        record.update(name=name,**shrink,checkpoint_sha256=sha256(private/(name+'.pt')))
        models.append(model);records.append(record)
    train=parts['correction_fit'];ok=train['eligible']
    priority=initial_priority(train['X'][ok])
    fixed=(priority*(train['y'][ok]-train['p'][ok]).abs()[:,None]).mean(0).argsort(descending=True)
    save(out/'refinement_frozen.json',dict(source_sha=source,models=records,fixed_ranking=fixed.tolist(),
        outer_loaded=False,alpha_selection='full-access shrinkage role; identical alpha across detail policies/budgets'))
    del parts
    data.load('validation');part=data.prepare(data.splits['validation']['origins']);part['p']=baseline.predict(part['X'])
    keep=part['eligible'];base_loss=(part['y'][keep]-part['p'][keep]).square()
    predictions={'A_T':part['p']};metrics={};regions_out={};timings=[]
    for model,rep in zip(models,records):
        for budget in c['refinement']['budgets']:
            for policy in c['refinement']['policies']:
                name=f'{policy}_{budget}_{rep["seed"]}'
                torch.cuda.synchronize();start=time.perf_counter()
                regions,stopped=choose_regions(model,part,budget,policy,fixed,c['refinement']['random_seed'],c['refinement']['stop_priority'])
                residual=predict_correction(model,part,region_mask=regions)
                probability=corrected_probability(part['p'],residual,rep['alpha']);torch.cuda.synchronize()
                predictions[name]=probability
                regions_out[name+'_region_bits']=(regions.long()*(2**torch.arange(16,device='cuda'))).sum(1)
                timings.append(dict(name=name,wall_seconds=time.perf_counter()-start,mean_regions=regions.double().sum(1).mean().item(),
                    stopped=int(stopped.sum().item()),budget=budget,seed=rep['seed'],policy=policy))
                metrics[name]=dict(metric=metric(part['y'][keep],probability[keep],to_cuda(rep['threshold'],torch.float64)),
                    pair=paired_summary(base_loss,(part['y'][keep]-probability[keep]).square(),part['day'][keep],c['bootstrap']))
    save_part(out/'detail_predictions.csv.gz',part,predictions);save_part(out/'detail_reveals.csv.gz',part,regions_out)
    save(out/'detail_metrics.json',metrics);save(out/'detail_timings.json',timings)
    save(out/'refinement_complete.json',dict(complete=True,source_sha=source,selected_family=family,
        numerical_device='cuda',test_access=False,measurement_interpretation='All values already resident; representation/processing diagnostic, not physical acquisition or IO savings'))
