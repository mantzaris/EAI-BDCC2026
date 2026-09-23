"""Monotone training-only calibration; strict tie-excluding alarm rules."""
import torch


def apply_calibration(p,state):
    if state['identity']:return p.double()
    a,b=state['slope'],state['intercept']
    x=torch.logit(p.double().clamp(state['epsilon'],1-state['epsilon']))
    return (a*x+b).sigmoid()


def fit_calibration(p,y,c):
    assert p.is_cuda and y.is_cuda
    if int((y==1).sum().item())<c['min_positives']:
        return dict(identity=True,reason='fewer than5positive origins',n=len(y),positives=int(y.sum().item()))
    x=torch.logit(p.detach().double().clamp(c['epsilon'],1-c['epsilon']))
    loga=torch.zeros((),device='cuda',dtype=torch.float64,requires_grad=True)
    b=torch.zeros_like(loga,requires_grad=True)
    opt=torch.optim.Adam([loga,b],lr=c['learning_rate'],capturable=True)
    with torch.enable_grad():
        for _ in range(c['steps']):
            a=loga.clamp(-3,3).exp();q=(a*x+b).sigmoid()
            loss=(q-y).square().mean()+c['regularization']*((a-1).square()+b.square())
            opt.zero_grad();loss.backward();opt.step()
    return dict(identity=False,slope=loga.detach().clamp(-3,3).exp(),intercept=b.detach(),epsilon=c['epsilon'],
        n=len(y),positives=int(y.sum().item()))


def alarm_cutoff(p,y,target=.05):
    negative=p[y==0];assert len(negative)>0
    k=int(torch.floor(p.new_tensor(target*len(negative))+1e-12).item())
    cutoff=negative.sort(descending=True).values[k]
    return cutoff


def json_calibration(state):return {k:v.item() if isinstance(v,torch.Tensor) else v for k,v in state.items()}
