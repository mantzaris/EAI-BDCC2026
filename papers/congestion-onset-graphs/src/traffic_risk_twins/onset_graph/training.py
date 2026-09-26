"""All-time Brier fitting with chronological onset selection on CUDA."""
import time
import torch
from ..residual_gpu.models import corrected_probability
from ..residual_gpu.data import sha256
from .models import build,predict
from .evaluation import onset
from .io import save_weights,load_weights,compact_state,restore_state


def fit(kind,c,parts,mean,scale,blocks,W,seed,reg,path,graph_key,source,internal_only=False,masked=False):
    if path.exists():raise FileExistsError(path)
    model=build(kind,c,mean,scale,blocks,W,seed,internal_only)
    opt=torch.optim.AdamW(model.parameters(),lr=c['learning_rate'],weight_decay=c['weight_decay'],capturable=True)
    train,early=parts['correction'],parts['early'];ids=torch.where(train['eligible'])[0][::3]
    best=torch.tensor(torch.inf,device='cuda',dtype=torch.float64);wait=0;history=[]
    rng=torch.Generator(device='cuda').manual_seed(seed)
    begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);begin.record();start=time.perf_counter()
    best_epoch=0
    for epoch in range(c['max_epochs']):
        model.train();order=ids[torch.randperm(len(ids),device='cuda',generator=rng)];loss_sum=train['p'].new_zeros(())
        for index in order.split(c['batch_size']):
            rm=None
            if masked:
                budgets=torch.tensor([4,8,16],device='cuda')[torch.randint(3,(len(index),),device='cuda',generator=rng)]
                rank=torch.rand(len(index),16,device='cuda',generator=rng).argsort(1).argsort(1);rm=rank<budgets[:,None]
            r=model(train['X'][index],train['p'][index],train['Z'][index],train['node_mask'][index],rm)
            p=corrected_probability(train['p'][index],r)
            brier=(p-train['y'][index]).square().mean();loss=brier+reg*r.square().mean()
            opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);opt.step()
            loss_sum+=brier.detach()*len(index)
        with torch.no_grad():
            q=predict(model,early);keep=onset(early);score=(q[keep]-early['y'][keep]).square().mean()
            all_score=(q[early['eligible']]-early['y'][early['eligible']]).square().mean()
        history.append(dict(epoch=epoch+1,train_all_time_brier=(loss_sum/len(ids)).item(),early_onset=score.item(),early_all_time=all_score.item()))
        if bool((score<best-c['minimum_improvement']).item()):
            best=score;wait=0;best_epoch=epoch+1
            save_weights(path,dict(state=compact_state(model),kind=kind,seed=seed,regularization=reg,graph_key=graph_key,
                internal_only=internal_only,source_sha=source,epoch=best_epoch))
        else:wait+=1
        if wait>=c['patience']:break
    end.record();torch.cuda.synchronize();restore_state(model,load_weights(path)['state'])
    record=dict(kind=kind,seed=seed,regularization=reg,best_early_onset=best.item(),best_epoch=best_epoch,epochs=len(history),history=history,
        training_origins=len(ids),parameters=sum(p.numel() for p in model.parameters()),fit_wall_seconds=time.perf_counter()-start,
        cuda_event_span_seconds=begin.elapsed_time(end)/1000,checkpoint_sha256=sha256(path),checkpoint=str(path),
        graph_key=graph_key,source_sha=source,internal_only=internal_only,masked=masked)
    return model,record


@torch.no_grad()
def choose_alpha(model,part,grid):
    # Alpha must scale the pre-clipping residual, not the already-clipped delta.
    r=[]
    for start in range(0,len(part['p']),256):
        s=slice(start,start+256)
        r.append(model(part['X'][s],part['p'][s],part['Z'][s],part['node_mask'][s]))
    r=torch.cat(r);keep=onset(part);alphas=part['p'].new_tensor(grid)
    q=(part['p'][None]+alphas[:,None]*r.double()[None]).clamp(0,1)
    scores=(q[:,keep]-part['y'][keep]).square().mean(1);i=int(scores.argmin().item())
    return grid[i],dict(alpha=grid[i],grid=grid,onset_briers=scores.tolist())
