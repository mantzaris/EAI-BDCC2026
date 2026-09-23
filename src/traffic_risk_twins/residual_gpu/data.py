"""Metadata/IO on host; all values, features, labels and graph math on CUDA."""
from pathlib import Path
import hashlib
import h5py
import numpy as np
import pandas as pd
import torch
from ..chronological_splits import split_days


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def to_cuda(value, dtype=None):
    return torch.as_tensor(value, device='cuda', dtype=dtype)


def valid(values):
    assert values.is_cuda
    return torch.isfinite(values)&(values>0)


def transform(values, mask, free):
    assert values.is_cuda and free.is_cuda
    safe = torch.where(mask, values, torch.zeros_like(values))
    state = torch.logit((1-safe/free).clamp(.001,.999))
    return torch.where(mask, state, torch.zeros_like(state))


def aggregate_features(history, mask, blocks, calendar):
    assert history.is_cuda and mask.is_cuda
    values = torch.where(mask, history, torch.zeros_like(history))
    means, counts, extras = [], [], []
    for b in range(int(blocks.max().item())+1):
        v, m = values[:,:,blocks==b], mask[:,:,blocks==b]
        count = m.sum(-1); mean = v.sum(-1)/count.clamp_min(1)
        variance = torch.where(m,(v-mean[:,:,None]).square(),0).sum(-1)/count.clamp_min(1)
        low = v.masked_fill(~m,torch.inf).amin(-1)
        high = v.masked_fill(~m,-torch.inf).amax(-1)
        severe = ((v>=0)&m).sum(-1)/count.clamp_min(1)
        means.append(mean); counts.append(count)
        extras.extend([variance,torch.where(count>0,low,0),torch.where(count>0,high,0),severe])
    means = torch.stack(means,-1); counts=torch.stack(counts,-1)
    return torch.cat([means.flatten(1),counts.flatten(1),calendar,torch.stack(extras,-1).flatten(1)],1).double()


def local_features(history, mask, means, blocks):
    clean = torch.where(mask,history,0)
    deviation = torch.where(mask,clean-means[:,:,blocks],0)
    difference = torch.zeros_like(clean)
    difference[:,1:] = torch.where(mask[:,1:]&mask[:,:-1],clean[:,1:]-clean[:,:-1],0)
    # B,N,L,C ordered history, shared sensor encoder. No unmasked unavailable value.
    return torch.stack([clean/7,deviation/7,difference/7,mask.to(clean.dtype)],-1).permute(0,2,1,3).float()


def observed_labels(raw, mask, origins, free, threshold=48):
    future_id=origins[:,None]+torch.arange(1,7,device='cuda')
    f,m=raw[future_id],mask[future_id]
    severe=(transform(f,m,free)>=0)
    low_count=(severe&m).sum(-1); high_count=(severe|~m).sum(-1)
    low_severity=low_count.unfold(-1,3,1).amin(-1).amax(-1)
    high_severity=high_count.unfold(-1,3,1).amin(-1).amax(-1)
    coverage=m.double().mean((-1,-2)); low=low_severity>=threshold; high=high_severity>=threshold
    ci=origins[:,None]+torch.arange(-2,1,device='cuda')
    current=((transform(raw[ci],mask[ci],free)>=0)|~mask[ci]).sum(-1).ge(threshold).all(-1)
    return dict(y=low.double(),lower=low,upper=high,coverage=coverage,eligible=(low==high)&(coverage>=.95),active=current)


class PilotData:
    def __init__(self, config):
        self.config=config
        with h5py.File(config['raw_file'],'r') as f:
            self.timestamps=pd.DatetimeIndex(f['speed/axis1'][:].astype('datetime64[ns]'))
            self.sensor_ids=f['speed/axis0'][:]
            assert np.array_equal(f['speed/block0_items'][:],self.sensor_ids)
            shape=f['speed/block0_values'].shape
        self.splits=split_days(self.timestamps)
        archive=np.load(config['input_archive'])
        self.W=to_cuda(archive['W'],torch.float64)
        self.blocks=to_cuda(archive['blocks'],torch.long)
        self.target_free=to_cuda(archive['free'],torch.float64)
        self.historical_origins=to_cuda(archive['origins'],torch.long)
        self.raw=torch.full(shape,torch.nan,device='cuda',dtype=torch.float64)
        self.loaded=[]; self.io_records=[]
        meta=np.stack([self.timestamps.hour,self.timestamps.minute,self.timestamps.dayofweek],1)
        meta=to_cuda(meta,torch.float64)
        phase=2*torch.pi*(meta[:,0]+meta[:,1]/60)/24
        self.calendar=torch.stack([torch.ones_like(phase),phase.sin(),phase.cos(),(2*phase).sin(),(2*phase).cos(),(meta[:,2]>=5).double()],1)
        self.day=to_cuda(self.timestamps.normalize().asi8//(24*3600*10**9),torch.long)
        self.time_ns=to_cuda(self.timestamps.asi8,torch.long)
        self.roles=self.make_roles()

    def make_roles(self):
        days=self.splits['train']['days'];cuts=self.config['inner_day_cuts']
        groups=np.split(np.asarray(days),cuts)
        bounds=[pd.Timestamp(days[i]) for i in cuts]
        allowed_outer=np.zeros(len(self.timestamps),bool);allowed_outer[self.splits['train']['rows']]=True
        result={}
        for role,group in zip(self.config['inner_roles'],groups):
            allowed=allowed_outer & self.timestamps.normalize().isin(pd.DatetimeIndex(group))
            for b in bounds:
                allowed &= (self.timestamps < b-pd.Timedelta(minutes=90)) | (self.timestamps>=b+pd.Timedelta(minutes=90))
            origins=self.splits['train']['origins']
            good=np.ones(len(origins),bool)
            for offset in range(-11,7):
                good &= allowed[origins+offset]
            result[role]=dict(days=group.tolist(),rows=np.flatnonzero(allowed),origins=origins[good])
        return result

    def load(self, split):
        if split not in ('train','validation'):
            raise ValueError('Test measurement access forbidden')
        if split in self.loaded: return
        rows=self.splits[split]['rows']
        groups=np.split(rows,np.flatnonzero(np.diff(rows)!=1)+1)
        with h5py.File(self.config['raw_file'],'r') as f:
            for group in groups:
                if len(group):
                    lo,hi=int(group[0]),int(group[-1])+1
                    self.raw[lo:hi]=to_cuda(f['speed/block0_values'][lo:hi],torch.float64)
                    self.io_records.append(dict(split=split,first_row=lo,last_row_exclusive=hi))
        self.loaded.append(split)
        self.mask=valid(self.raw)

    def fit_feature_transform(self):
        rows=to_cuda(self.roles['baseline_fit']['rows'],torch.long)
        self.feature_free=torch.nanquantile(self.raw[rows].masked_fill(~self.mask[rows],torch.nan),.85,dim=0)
        assert torch.isfinite(self.feature_free).all() and (self.feature_free>0).all()

    @torch.no_grad()
    def prepare(self, origins):
        origins=to_cuda(origins,torch.long)
        arrays=[]; local=[]; masks=[]; labels={}
        for batch in origins.split(512):
            hi=batch[:,None]+torch.arange(-11,1,device='cuda')
            m=self.mask[hi];state=transform(self.raw[hi],m,self.feature_free)
            agg=aggregate_features(state,m,self.blocks,self.calendar[batch])
            arrays.append(agg)
            local.append(local_features(state,m,agg[:,:192].reshape(-1,12,16),self.blocks))
            masks.append(m.permute(0,2,1).any(-1))
            label=observed_labels(self.raw,self.mask,batch,self.target_free,self.config['threshold_count'])
            for k,v in label.items(): labels.setdefault(k,[]).append(v)
        return dict(origins=origins,day=self.day[origins],time_ns=self.time_ns[origins],X=torch.cat(arrays),
                    Z=torch.cat(local),node_mask=torch.cat(masks),**{k:torch.cat(v) for k,v in labels.items()})
