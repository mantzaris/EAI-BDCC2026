"""Metrics and paired temporal-block resampling stay on CUDA."""
import torch


def scalar(x):
    return x.detach().item()


def support(part):
    take=part['eligible'];y=part['y'][take];times=part['time_ns'][take];days=part['day'][take]
    def counts(positive):
        tt=times[positive]
        episodes=0 if not len(tt) else int(((tt[1:]-tt[:-1])>=1800*10**9).sum().item())+1
        return dict(positives=int(positive.sum().item()),episodes=episodes,event_days=int(torch.unique(days[positive]).numel()))
    onset=~part['active'][take]
    return dict(origins=len(take),eligible=int(take.sum().item()),excluded=int((~take).sum().item()),
                ambiguous=int((part['lower']!=part['upper']).sum().item()),
                below_coverage=int((part['coverage']<.95).sum().item()),days=int(torch.unique(days).numel()),
                prevalence=scalar(y.mean()),all_time=counts(y.bool()),
                onset=dict(n=int(onset.sum().item()),**counts(y.bool()&onset)))


def alarm_threshold(p,y,target=.05):
    negative=p[y==0]
    if not len(negative): raise ValueError('No calibration non-events')
    permitted=int(torch.floor(p.new_tensor(target*len(negative))+1e-12).item())
    descending=negative.sort(descending=True).values
    return torch.nextafter(descending[permitted],p.new_tensor(torch.inf))


def metric(y,p,threshold):
    assert y.is_cuda and p.is_cuda and len(y)>0
    assert torch.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    y,p=y.double(),p.double();loss=(p-y).square();positive=y.bool();negative=~positive
    alarm=p>=threshold;tp=(alarm&positive).sum();fp=(alarm&negative).sum()
    record=dict(n=len(y),positives=int(positive.sum().item()),prevalence=scalar(y.mean()),brier=scalar(loss.mean()),
        event_contribution=scalar(loss[positive].sum()/len(y)),nonevent_contribution=scalar(loss[negative].sum()/len(y)),
        mean_probability=scalar(p.mean()),zero_probabilities=int((p==0).sum().item()),
        probability_quantiles=torch.quantile(p,p.new_tensor([0,.1,.5,.9,.99,1])).tolist(),
        threshold=scalar(threshold),tp=int(tp.item()),fp=int(fp.item()),
        recall=scalar(tp/positive.sum()) if positive.any() else None,
        false_alarm_rate=scalar(fp/negative.sum()) if negative.any() else None)
    bins=torch.bucketize(p,p.new_tensor([.2,.4,.6,.8]),right=True)
    record['reliability']=[]
    for b in range(5):
        keep=bins==b
        if keep.any(): record['reliability'].append(dict(bin=b,n=int(keep.sum().item()),predicted=scalar(p[keep].mean()),observed=scalar(y[keep].mean())))
    return record


def block_estimates(values,days,block_days,repeats=2000,seed=20260927):
    """values N by K; same resampled complete days for every model and seed."""
    assert values.is_cuda and days.is_cuda
    _,group=torch.unique(days,sorted=True,return_inverse=True);nd=int(group.max().item())+1
    if nd<block_days: raise ValueError('Insufficient days for requested blocks')
    totals=values.new_zeros(nd,values.shape[1]).index_add_(0,group,values)
    counts=torch.bincount(group,minlength=nd).double()
    gen=torch.Generator(device='cuda').manual_seed(seed)
    start=torch.randint(nd-block_days+1,(repeats,(nd+block_days-1)//block_days),device='cuda',generator=gen)
    ids=(start[:,:,None]+torch.arange(block_days,device='cuda')).flatten(1)[:,:nd]
    return totals[ids].sum(1)/counts[ids].sum(1)[:,None]


def paired_summary(loss_a,loss_b,days,config):
    means=torch.stack([loss_a.mean(),loss_b.mean()]);difference=means[1]-means[0]
    record=dict(a_brier=scalar(means[0]),b_brier=scalar(means[1]),difference=scalar(difference),
                relative_reduction=scalar(-difference/means[0]))
    for length in config['block_days']:
        resampled=block_estimates(torch.stack([loss_a,loss_b],1),days,length,config['replicates'],config['seed'])
        delta=resampled[:,1]-resampled[:,0]
        relative=-delta/resampled[:,0].clamp_min(1e-15)
        record[str(length)]=dict(difference_95=torch.quantile(delta,delta.new_tensor([.025,.975])).tolist(),
            relative_reduction_95=torch.quantile(relative,relative.new_tensor([.025,.975])).tolist(),
            b_brier_95=torch.quantile(resampled[:,1],delta.new_tensor([.025,.975])).tolist())
    return record


def alignment(y,base,p):
    delta=p.double()-base.double();e=y.double()-base.double()
    lhs=(e.square()-(y.double()-p.double()).square()).mean()
    aligned=2*(delta*e).mean();magnitude=delta.square().mean()
    error=(lhs-(aligned-magnitude)).abs()
    assert error<1e-10
    return dict(improvement=scalar(lhs),twice_alignment=scalar(aligned),squared_magnitude=scalar(magnitude),identity_error=scalar(error),
                delta_mean=scalar(delta.mean()),delta_rms=scalar(delta.square().mean().sqrt()))
