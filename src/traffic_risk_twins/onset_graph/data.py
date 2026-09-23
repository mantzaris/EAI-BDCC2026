"""Reuse the guarded measurement reader; change only chronological role metadata."""
import numpy as np
import pandas as pd
import torch
from ..residual_gpu.data import PilotData,to_cuda


class StudyData(PilotData):
    def interval(self,lo,hi,cuts):
        days=self.splits['train']['days'];group=days[lo:hi]
        allowed=np.zeros(len(self.timestamps),bool);allowed[self.splits['train']['rows']]=True
        allowed &= self.timestamps.normalize().isin(pd.DatetimeIndex(group))
        for cut in cuts:
            if cut<len(days):
                boundary=pd.Timestamp(days[cut])
                allowed &= (self.timestamps<boundary-pd.Timedelta(minutes=90))|(self.timestamps>=boundary+pd.Timedelta(minutes=90))
        origins=self.splits['train']['origins'];keep=np.ones(len(origins),bool)
        for offset in range(-11,7):keep &= allowed[origins+offset]
        return dict(days=group,rows=np.flatnonzero(allowed),origins=origins[keep])

    def fold_roles(self,cuts):
        names=['anchor','correction','early','shrink','calibration','gate'];lower=0
        roles={}
        for name,upper in zip(names,cuts):
            roles[name]=self.interval(lower,upper,cuts);lower=upper
        return roles

    def fit_free(self,rows):
        selected=to_cuda(rows,torch.long)
        free=torch.nanquantile(self.raw[selected].masked_fill(~self.mask[selected],torch.nan),.85,dim=0)
        assert torch.isfinite(free).all() and (free>0).all()
        self.feature_free=free;return free


def subset(part,indices):
    n=len(part['p']) if 'p' in part else len(part['origins'])
    return {k:v[indices] for k,v in part.items() if isinstance(v,torch.Tensor) and v.ndim and v.shape[0]==n}
