"""Small shared temporal correction with matched self/neighbor message branches."""
import torch
from torch import nn


class ResidualCorrection(nn.Module):
    def __init__(self, family, config, mean, scale, blocks, W):
        super().__init__()
        assert mean.is_cuda and W.is_cuda
        self.family=family
        self.register_buffer('mean',mean.float())
        self.register_buffer('scale',scale.float())
        self.register_buffer('blocks',blocks)
        self.register_buffer('W',W.float())
        self.register_buffer('P',torch.nn.functional.one_hot(blocks,16).float())
        w,a,h=config['width'],config['aggregate_width'],config['head_width']
        with torch.device('cuda'):
            self.aggregate=nn.Sequential(nn.Linear(len(mean)+1,a),nn.ReLU())
            if family in ('C','D'):
                self.temporal=nn.Sequential(nn.Linear(48,w),nn.ReLU(),nn.Linear(w,w),nn.ReLU())
                self.message=nn.Linear(2*w,w)
                self.local_head=nn.Sequential(nn.Linear(16*(w+1),a),nn.ReLU())
            self.hidden=nn.Sequential(nn.Linear(a if family=='B' else 2*a,h),nn.ReLU())
            self.head=nn.Linear(h,1)
            nn.init.zeros_(self.head.weight);nn.init.zeros_(self.head.bias)

    def encode_local(self,Z,node_mask,region_mask=None):
        if region_mask is not None:
            node_mask=node_mask & region_mask[:,self.blocks]
        available=node_mask & (Z[:,:,:,-1]>0).any(-1)
        # Poisoned values cannot survive the mask, including per-frame missingness.
        valid_frame=(Z[:,:,:,-1]>0)&available[:,:,None]
        z=torch.where(valid_frame[:,:,:,None],Z,torch.zeros_like(Z))
        h=self.temporal(z.flatten(2))*available[:,:,None]
        if self.family=='D':
            weights=self.W[None]*available[:,None,:]
            message=torch.bmm(weights,h)/weights.sum(-1,keepdim=True).clamp_min(1e-8)
        else:
            message=h
        h=torch.relu(self.message(torch.cat([h,message],-1)))*available[:,:,None]
        count=available.float()@self.P
        pooled=torch.einsum('bnw,nk->bkw',h,self.P)/count.clamp_min(1)[:,:,None]
        fraction=count/self.P.sum(0).clamp_min(1)
        return torch.cat([pooled,fraction[:,:,None]],-1).flatten(1),h

    def forward(self,X,p,Z=None,node_mask=None,region_mask=None):
        assert X.is_cuda and p.is_cuda
        x=((X.float()-self.mean)/self.scale).clamp(-10,10)
        a=self.aggregate(torch.cat([x,p.float()[:,None]],1))
        if self.family!='B':
            pooled,_=self.encode_local(Z,node_mask,region_mask)
            a=torch.cat([a,self.local_head(pooled)],1)
        return .5*torch.tanh(self.head(self.hidden(a)).squeeze(-1))


def corrected_probability(base,residual,alpha=1.):
    assert base.is_cuda and residual.is_cuda
    return (base.double()+alpha*residual.double()).clamp(0,1)


@torch.no_grad()
def predict_correction(model,part,base=None,region_mask=None,batch_size=512):
    model.eval();base=part['p'] if base is None else base
    output=[]
    for start in range(0,len(base),batch_size):
        s=slice(start,start+batch_size)
        output.append(model(part['X'][s],base[s],part['Z'][s],part['node_mask'][s],None if region_mask is None else region_mask[s]))
    return torch.cat(output)
