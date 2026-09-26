"""CUDA metrics with timestamp-preserving bootstrap and declared multiplicity."""
import torch
from ..residual_gpu.evaluation import support,alignment


def onset(part):return part['eligible']&~part['active']


def resample(values,days,length,repeats=2000,seed=20261007):
    unique,group=torch.unique(days,sorted=True,return_inverse=True)
    totals=values.new_zeros(len(unique),values.shape[1]).index_add_(0,group,values)
    counts=torch.bincount(group,minlength=len(unique)).double()
    breaks=torch.where(unique[1:]-unique[:-1]!=1)[0]+1
    boundaries=[0]+breaks.tolist()+[len(unique)]
    rng=torch.Generator(device='cuda').manual_seed(seed)
    total=values.new_zeros(repeats,values.shape[1]);n=values.new_zeros(repeats)
    for lo,hi in zip(boundaries[:-1],boundaries[1:]):
        size=hi-lo;block=min(length,size)
        starts=torch.randint(size-block+1,(repeats,(size+block-1)//block),device='cuda',generator=rng)
        ids=(starts[:,:,None]+torch.arange(block,device='cuda')).flatten(1)[:,:size]+lo
        total+=totals[ids].sum(1);n+=counts[ids].sum(1)
    return total/n[:,None]


def episode_metrics(y,p,cutoff,times,days):
    def groups(mask):
        ix=torch.where(mask)[0]
        if not len(ix):return dict(groups=0,detected=0,event_days=0)
        t=times[ix];start=torch.cat([torch.ones(1,device='cuda',dtype=torch.bool),t[1:]-t[:-1]>=1800*10**9])
        gid=start.long().cumsum(0)-1;n=int(start.sum().item())
        hit=torch.zeros(n,device='cuda',dtype=torch.long).scatter_reduce_(0,gid,(p[ix]>cutoff).long(),reduce='amax')
        return dict(groups=n,detected=int(hit.sum().item()),event_days=int(torch.unique(days[ix]).numel()))
    event=groups(y==1);false=groups((y==0)&(p>cutoff))
    return dict(positive_groups=event['groups'],detected_groups=event['detected'],false_alarm_groups=false['groups'],
        false_alarm_groups_per_day=(p.new_tensor(false['groups'])/len(torch.unique(days))).item(),
        meaning='Clusters of forecast origins separated by30minutes, not independently observed incidents')


def metric(y,p,cutoff,times,days,uncertainty=True):
    y,p=y.double(),p.double();assert torch.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    loss=(y-p).square();positive=y==1;alarm=p>cutoff;tp=positive&alarm;fp=~positive&alarm
    result=dict(n=len(y),positives=int(positive.sum().item()),prevalence=y.mean().item(),brier=loss.mean().item(),
        event_contribution=(loss*positive).mean().item(),nonevent_contribution=(loss*~positive).mean().item(),
        tp=int(tp.sum().item()),fp=int(fp.sum().item()),recall=(tp.sum().double()/positive.sum()).item() if positive.any() else None,
        fpr=(fp.sum().double()/(~positive).sum()).item() if (~positive).any() else None,
        cutoff=cutoff.item(),alarm_rule='strict >',zero_count=int((p==0).sum().item()),one_count=int((p==1).sum().item()),
        cutoff_ties=int((p==cutoff).sum().item()),unique_scores=int(torch.unique(p).numel()),mean_probability=p.mean().item(),
        quantiles=torch.quantile(p,p.new_tensor([0,.1,.5,.9,.99,1])).tolist(),episodes=episode_metrics(y,p,cutoff,times,days))
    bin_id=torch.bucketize(p,p.new_tensor([.01,.05,.1,.2,.4,.6,.8]),right=True)
    result['reliability']=[]
    for b in range(8):
        m=bin_id==b
        if m.any():result['reliability'].append(dict(bin=b,n=int(m.sum().item()),predicted=p[m].mean().item(),observed=y[m].mean().item()))
    if uncertainty:
        v=torch.stack([loss,tp.double(),fp.double(),positive.double(),(~positive).double()],1)
        draws=resample(v,days,3)
        result['brier_95']=torch.quantile(draws[:,0],p.new_tensor([.025,.975])).tolist()
        for key,a,b in [('recall_95',1,3),('fpr_95',2,4)]:
            good=draws[:,b]>0
            result[key]=torch.quantile(draws[good,a]/draws[good,b],p.new_tensor([.025,.975])).tolist() if good.any() else None
    return result


def population(part,predictions,thresholds,families,contrasts,c,all_pairs=True,primary_family=True):
    result=dict(support=support(part),models={},families={},paired={},alignment={})
    for endpoint,keep in [('onset',onset(part)),('all_time',part['eligible'])]:
        y=part['y'][keep];days=part['day'][keep];losses={}
        for name,p in predictions.items():
            result['models'].setdefault(name,{})[endpoint]=metric(y,p[keep],thresholds[name],part['time_ns'][keep],days)
            losses[name]=(y-p[keep]).square()
            if name!='A_G' and 'A_G' in predictions:
                result['alignment'].setdefault(name,{})[endpoint]=alignment(y,predictions['A_G'][keep],p[keep])
        group_loss={}
        for name,keys in families.items():
            stack=torch.stack([losses[k] for k in keys]);group_loss[name]=stack.mean(0)
            result['families'].setdefault(name,{})[endpoint]=dict(brier=stack.mean().item(),seed_briers=stack.mean(1).tolist(),
                seed_std=stack.mean(1).std(unbiased=False).item(),seed_min=stack.mean(1).min().item(),seed_max=stack.mean(1).max().item(),
                mean_recall=torch.tensor([result['models'][k][endpoint]['recall'] or 0 for k in keys],device='cuda',dtype=torch.float64).mean().item(),
                mean_fpr=torch.tensor([result['models'][k][endpoint]['fpr'] or 0 for k in keys],device='cuda',dtype=torch.float64).mean().item())
        comparison=list(contrasts)
        if all_pairs:
            comparison+= [(f,'A_G') for f in families if f!='A_G']
        comparison=list(dict.fromkeys(comparison))
        for a,b in comparison:
            if a not in group_loss or b not in group_loss:continue
            va,vb=group_loss[a],group_loss[b];delta=(va-vb).mean()
            r=dict(a=a,b=b,difference=delta.item(),relative_reduction=(-delta/vb.mean()).item(),primary=primary_family and (a,b) in contrasts and endpoint=='onset')
            for block in c['block_days']:
                draws=resample(torch.stack([va,vb],1),days,block,c['replicates'],c['seed']);d=draws[:,0]-draws[:,1]
                r[str(block)]=dict(pointwise_95=torch.quantile(d,d.new_tensor([.025,.975])).tolist())
                if primary_family and (a,b) in contrasts and endpoint=='onset':
                    tail=c['familywise_alpha']/(2*4)
                    r[str(block)]['bonferroni_family4']=torch.quantile(d,d.new_tensor([tail,1-tail])).tolist()
            result['paired'][a+'_minus_'+b+'_'+endpoint]=r
    return result


def ranking_curve(y,p):
    order=p.argsort(descending=True);q=p[order];labels=y[order]
    end=torch.cat([q[1:]!=q[:-1],torch.ones(1,device='cuda',dtype=torch.bool)])
    tp=labels.cumsum(0)[end];fp=(1-labels).cumsum(0)[end]
    return dict(thresholds=q[end].tolist(),recall=(tp/labels.sum().clamp_min(1)).tolist(),
        fpr=(fp/(1-labels).sum().clamp_min(1)).tolist(),precision=(tp/(tp+fp)).tolist(),
        use='descriptive ranking only; no deployed threshold selection')
