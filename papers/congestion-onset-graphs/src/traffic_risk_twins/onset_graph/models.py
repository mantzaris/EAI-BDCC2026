"""Matched additive corrections with explicit aggregate, local and graph inputs."""
import torch
from torch import nn
from ..residual_gpu.models import ResidualCorrection,corrected_probability
from .graphs import GraphFeatures


class Correction(ResidualCorrection):
    def __init__(self,kind,c,mean,scale,blocks,W,internal_only=False):
        settings=dict(c)
        if kind=='K':settings['aggregate_width']=c['capacity_aggregate_width']
        old_kind='B' if kind in ('B','K') else ('C' if kind=='C' else 'D')
        super().__init__(old_kind,settings,mean,scale,blocks,W)
        self.kind=kind;self.internal_only=internal_only;self.ops=None
        if kind=='E':self.message=nn.Linear(3*c['width'],c['width'],device='cuda')
        if kind in ('M','S'):
            width=c['width'];channels=6 if kind=='M' else 8
            self.temporal=nn.Sequential(nn.Linear(12*channels,width),nn.ReLU(),nn.Linear(width,width),nn.ReLU())
            self.ops=GraphFeatures(W,blocks)

    def encode_local(self,Z,node_mask,region_mask=None):
        if self.kind!='E':return super().encode_local(Z,node_mask,region_mask)
        available=node_mask&(Z[:,:,:,-1]>0).any(-1)
        if region_mask is not None:available &= region_mask[:,self.blocks]
        m=(Z[:,:,:,-1]>0)&available[:,:,None]
        z=torch.where(m[:,:,:,None],Z,0);h=self.temporal(z.flatten(2))*available[:,:,None]
        weights=self.W[None]*available[:,None,:];denom=weights.sum(-1,keepdim=True).clamp_min(1e-8)
        within=self.blocks[:,None]==self.blocks[None,:]
        internal=torch.bmm(weights*within,h)/denom
        external=torch.zeros_like(internal) if self.internal_only else torch.bmm(weights*~within,h)/denom
        h=torch.relu(self.message(torch.cat([h,internal,external],-1)))*available[:,:,None]
        count=available.float()@self.P;pooled=torch.einsum('bnw,nk->bkw',h,self.P)/count.clamp_min(1)[:,:,None]
        return torch.cat([pooled,(count/self.P.sum(0))[:,:,None]],-1).flatten(1),h

    def forward(self,X,p,Z=None,node_mask=None,region_mask=None):
        if self.kind not in ('M','S'):return super().forward(X,p,Z,node_mask,region_mask)
        x=((X.float()-self.mean)/self.scale).clamp(-10,10)
        a=self.aggregate(torch.cat([x,p.float()[:,None]],1))
        safe_Z=None if self.kind=='M' else torch.where(node_mask[:,:,None,None],Z,torch.zeros_like(Z))
        values=self.ops.regional(X) if self.kind=='M' else self.ops.summaries(X,safe_Z,region_mask)
        h=self.temporal(values.flatten(2));counts=X[:,192:384].reshape(-1,12,16).amax(1)>0
        h=h*counts[:,:,None]
        if self.kind=='M':
            weights=self.ops.Q[None]*counts[:,None,:]
            message=torch.bmm(weights,h)/weights.sum(-1,keepdim=True).clamp_min(1e-8)
        else:message=h
        h=torch.relu(self.message(torch.cat([h,message],-1)))*counts[:,:,None]
        pooled=torch.cat([h,counts[:,:,None].float()],-1).flatten(1)
        a=torch.cat([a,self.local_head(pooled)],1)
        return .5*torch.tanh(self.head(self.hidden(a)).squeeze(-1))


def build(kind,c,mean,scale,blocks,W,seed,internal_only=False):
    torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    return Correction(kind,c,mean,scale,blocks,W,internal_only)


@torch.no_grad()
def predict(model,part,alpha=1,region_mask=None,batch=256):
    outputs=[]
    for start in range(0,len(part['p']),batch):
        s=slice(start,start+batch)
        r=model(part['X'][s],part['p'][s],part['Z'][s],part['node_mask'][s],None if region_mask is None else region_mask[s])
        outputs.append(corrected_probability(part['p'][s],r,alpha))
    return torch.cat(outputs)
