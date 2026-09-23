"""Independent invariants corresponding to relevant historical scientific checks."""
import copy
import torch
from .data import aggregate_features,local_features,observed_labels
from .models import ResidualCorrection,corrected_probability
from .baseline import GPUQuantileBoost,SavedBaseline
from .evaluation import alignment,alarm_threshold,block_estimates


def scientific_checks(config):
    torch.manual_seed(1901);torch.cuda.manual_seed_all(1901)
    dev='cuda';checks=[]
    x=torch.randn(12,12,32,device=dev,dtype=torch.float64)
    mask=torch.ones_like(x,dtype=torch.bool);mask[:,:,0]=False
    blocks=torch.arange(32,device=dev)//2
    cal=torch.ones(12,6,device=dev,dtype=torch.float64)
    a=aggregate_features(x,mask,blocks,cal)
    poison=x.clone();poison[:,:,0]=1e50
    assert torch.equal(a,aggregate_features(poison,mask,blocks,cal))
    checks.append('Historical masked-feature poisoning invariant on GPU')
    z=local_features(x,mask,a[:,:192].reshape(-1,12,16),blocks)
    zm=mask.permute(0,2,1).any(-1)
    W=torch.rand(32,32,device=dev);W/=W.sum(1,keepdim=True)
    models={f:ResidualCorrection(f,config['correction'],a.mean(0),a.std(0).clamp_min(.01),blocks,W) for f in ('B','C','D')}
    base=torch.linspace(.1,.8,12,device=dev,dtype=torch.float64)
    for model in models.values():
        r=model(a,base,z,zm)
        assert torch.equal(corrected_probability(base,r),base)
        assert torch.equal(corrected_probability(base,r+1,0),base)
    checks.append('Zero head and alpha zero exactly recover FP64 supplied baseline')
    assert sum(p.numel() for p in models['C'].parameters())==sum(p.numel() for p in models['D'].parameters())
    model=models['D'];optimizer=torch.optim.AdamW(model.parameters(),lr=.01)
    for step in range(2):
        optimizer.zero_grad();r=model(a,base,z,zm);loss=(corrected_probability(base,r)-1).square().mean();loss.backward()
        assert model.head.weight.grad.abs().sum()>0
        if step==1: assert model.temporal[0].weight.grad.abs().sum()>0
        optimizer.step()
    checks.append('Nonzero head gradient, then nonzero temporal gradient from zero initialization')
    with torch.no_grad():
        original=model(a,base,z,zm)
        permutation=torch.randperm(32,device=dev)
        alternate=ResidualCorrection('D',config['correction'],model.mean,model.scale,blocks[permutation],W[permutation][:,permutation])
        for target,source in zip(alternate.parameters(),model.parameters()):target.copy_(source)
        changed=alternate(a,base,z[:,permutation],zm[:,permutation])
        assert torch.allclose(original,changed,atol=2e-6,rtol=1e-5)
        bad=z.clone();bad[:,0,:,:3]=1e20
        assert torch.equal(model(a,base,bad,zm),original)
        hidden=torch.zeros(12,16,device=dev,dtype=torch.bool);hidden[:,:4]=True
        zz=z.clone();zz[:,blocks>=4,:,:3]=1e20
        assert torch.equal(model(a,base,zz,zm,hidden),model(a,base,z,zm,hidden))
    checks.append('Nonzero graph model invariant to consistent sensor/W/block permutation')
    checks.append('Node and unacquired-region poisoning cannot affect predictions')
    probabilities=corrected_probability(base,torch.tensor([-10,10]*6,device=dev))
    assert ((probabilities>=0)&(probabilities<=1)).all()
    identity=alignment((torch.arange(12,device=dev)%2).double(),base,probabilities)
    checks.append('Post-clipping Brier identity with both clipping boundaries')
    raw=torch.full((20,2),50.,device=dev,dtype=torch.float64);mm=torch.ones_like(raw,dtype=torch.bool)
    label=observed_labels(raw,mm,torch.tensor([11],device=dev),torch.tensor([100.,100.],device=dev),2)
    assert label['y'].item()==1 and label['eligible'].item()
    mm[13,0]=False
    uncertain=observed_labels(raw,mm,torch.tensor([11],device=dev),torch.tensor([100.,100.],device=dev),2)
    assert not uncertain['eligible'].item() # coverage 11/12, below .95
    checks.append('Threshold equality and missing-future coverage; no imputed observed label')
    p=torch.tensor([.1]*18+[.8]*2+[.9,.7],device=dev,dtype=torch.float64)
    y=torch.tensor([0]*20+[1,1],device=dev)
    threshold=alarm_threshold(p,y)
    assert ((p[y==0]>=threshold).sum()==0) and ((p[y==1]>=threshold).sum()==1)
    checks.append('Historical tie-safe alarm regression on GPU')
    values=torch.rand(12,1,device=dev,dtype=torch.float64).expand(-1,2)
    boot=block_estimates(values,torch.arange(12,device=dev)//2,3,50,18)
    assert torch.equal(boot[:,0],boot[:,1])
    checks.append('Paired identical forecasts remain identical in block resampling')
    toy=torch.linspace(-2,2,100,device=dev,dtype=torch.float64)[:,None]
    spec=dict(config['baseline'],trees=5,max_leaves=3,max_bins=8,min_leaf=5)
    tree=GPUQuantileBoost(spec).fit(toy,(toy[:,0]>=0).double())
    fitted=tree.predict(toy)
    assert fitted[:50].max()<fitted[50:].min()
    restored=GPUQuantileBoost.from_state(copy.deepcopy(tree.state_dict()))
    assert torch.equal(fitted,restored.predict(toy))
    checks.append('GPU boosting separates an ordered known-label problem and restores exactly')
    saved=SavedBaseline(torch.tensor([3,1],device=dev),torch.tensor([.7,.2],device=dev,dtype=torch.float64))
    assert torch.equal(saved.predict(torch.tensor([1,3],device=dev)),torch.tensor([.2,.7],device=dev,dtype=torch.float64))
    checks.append('Saved-baseline adapter is exact and origin-indexed')
    return dict(passed=True,checks=checks,alignment_example=identity,device=dev)
