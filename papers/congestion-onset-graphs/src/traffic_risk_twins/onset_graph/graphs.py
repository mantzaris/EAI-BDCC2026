"""GPU graph estimation, degree-preserving nulls and fixed linear projections."""
import torch
from ..residual_gpu.data import transform,to_cuda


def projection(blocks,dtype=torch.float64):
    L=torch.nn.functional.one_hot(blocks,16).to(dtype)
    return L.T/L.sum(0)[:,None],L


def propagate(W,x):
    """x[...,N] -> (Wx)[...,N], repeated sparse products, never a dense power."""
    return torch.sparse.mm(W,x.reshape(-1,x.shape[-1]).T.contiguous()).T.reshape(x.shape)


def graph_summary(W,blocks):
    R,L=projection(blocks,W.dtype);off=W.clone();off.fill_diagonal_(0)
    boundary=blocks[:,None]!=blocks[None,:]
    return dict(nodes=len(W),nonself_edges=int((off>0).sum().item()),
        outdegree=(off>0).sum(1).tolist(),indegree=(off>0).sum(0).tolist(),
        cross_edges=int(((off>0)&boundary).sum().item()),cross_weight=off[boundary].sum().item(),
        row_sum_error=(W.sum(1)-1).abs().max().item(),Q=(R@W@L).tolist(),
        deviation_response_norm=torch.linalg.matrix_norm(R@W-(R@W@L)@R).item())


@torch.no_grad()
def dependency_graph(data,rows):
    rows=to_cuda(rows,torch.long);complete=data.mask[rows].all(1);rows=rows[complete]
    values=transform(data.raw[rows],data.mask[rows],data.feature_free)
    R,L=projection(data.blocks);common=values@R.T
    design=torch.cat([data.calendar[rows],common],1)
    coefficients=torch.linalg.pinv(design,rtol=1e-8)@values
    residual=values-design@coefficients;residual-=residual.mean(0)
    normalized=residual/residual.square().sum(0).sqrt().clamp_min(1e-12)
    corr=normalized.T@normalized;scores=corr.abs();scores.fill_diagonal_(-torch.inf)
    original=data.W.clone();original.fill_diagonal_(0);degree=(original>0).sum(1)
    ranks=scores.argsort(1,descending=True).argsort(1);keep=ranks<degree[:,None]
    W=torch.where(keep,corr.abs().clamp_min(1e-12),0)
    W[degree==0,degree==0]=1
    W/=W.sum(1,keepdim=True)
    assert torch.equal((W-torch.diag(W.diag())>0).sum(1),degree)
    return W,dict(training_complete_vectors=len(rows),cutoff_row=int(rows.max().item()),
        regression_features=design.shape[1],negative_selected_edges=int((keep&(corr<0)).sum().item()),
        edge_overlap_original=int((keep&(original>0)).sum().item()),
        residual_calendar_max_inner_product=(design.T@residual).abs().max().item(),
        interpretation='Absolute partial association; no causal direction; no validation fitting')


@torch.no_grad()
def rewire(W,seed,rounds=1000,batch_pairs=32):
    """Disjoint directed double swaps preserve per-node degrees and row weights."""
    out=W.clone();edge=torch.nonzero((W>0)&~torch.eye(len(W),device='cuda',dtype=torch.bool))
    E=len(edge);rng=torch.Generator(device='cuda').manual_seed(seed);accepted=0
    for _ in range(rounds):
        pair=torch.randperm(E,device='cuda',generator=rng)[:min(2*batch_pairs,E//2*2)].reshape(-1,2)
        e1,e2=edge[pair[:,0]],edge[pair[:,1]];a,b=e1.unbind(1);c,d=e2.unbind(1)
        nodes=torch.stack([a,b,c,d],1)
        distinct=(nodes[:,:,None]==nodes[:,None,:]).sum((1,2))==4
        valid=distinct&(out[a,d]==0)&(out[c,b]==0)
        # Only node-disjoint proposals may execute together: no duplicate new edges.
        conflict=(nodes[:,None,:,None]==nodes[None,:,None,:]).any((2,3))
        earlier=torch.tril(torch.ones_like(conflict),diagonal=-1)
        valid &= ~((conflict&earlier)&valid[None,:]).any(1)
        ids=torch.where(valid)[0];a,b,c,d=a[ids],b[ids],c[ids],d[ids]
        w1,w2=out[a,b].clone(),out[c,d].clone();out[a,b]=0;out[c,d]=0;out[a,d]=w1;out[c,b]=w2
        edge[pair[ids,0],1]=d;edge[pair[ids,1],1]=b;accepted+=len(ids)
    assert torch.equal((out>0).sum(0),(W>0).sum(0))
    assert torch.equal((out>0).sum(1),(W>0).sum(1))
    assert torch.equal(out.sort(1).values,W.sort(1).values)
    assert torch.equal(out.diag(),W.diag())
    return out,dict(seed=seed,rounds=rounds,accepted_swaps=accepted,
        preserved=['per-node indegree','per-node outdegree','source-row weight multiset','diagonal fallbacks'],
        edge_overlap=int(((out>0)&(W>0)).sum().item()),uniform_null_sample=False)


class GraphFeatures:
    def __init__(self,W,blocks):
        self.W=W.float();self.blocks=blocks;self.R,self.L=projection(blocks,torch.float32)
        self.Q=self.R@self.W@self.L;self.sparse=self.W.to_sparse_coo().coalesce()
        lift=self.L;self.lifts=[]
        for h in range(1,5):
            lift=torch.sparse.mm(self.sparse,lift)
            if h in (1,2,4):self.lifts.append(self.R@lift)

    def summaries(self,X,Z,region_mask=None):
        z=X[:,:192].reshape(-1,12,16).float()/7
        valid=(Z[:,:,:,-1]>0);v=torch.where(valid,Z[:,:,:,1],0).permute(0,2,1)
        details=[]
        for h in range(1,5):
            v=propagate(self.sparse,v)
            if h in (1,2,4):details.append(v@self.R.T)
        coarse=[z@T.T for T in self.lifts]
        reveal=torch.ones_like(z) if region_mask is None else region_mask[:,None,:].expand_as(z).float()
        details=[d*reveal for d in details]
        fraction=X[:,192:384].reshape(-1,12,16).float()/self.L.sum(0)
        return torch.stack(coarse+details+[fraction,reveal],-1).permute(0,2,1,3)

    def regional(self,X):
        z=X[:,:192].reshape(-1,12,16).float()/7
        counts=X[:,192:384].reshape(-1,12,16).float()/self.L.sum(0)
        extras=X[:,390:].reshape(-1,12,16,4).float()
        extra=torch.stack([extras[...,0]/49,extras[...,1]/7,extras[...,2]/7,extras[...,3]],-1)
        return torch.cat([z[...,None],counts[...,None],extra],-1).permute(0,2,1,3)
