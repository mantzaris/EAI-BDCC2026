"""Chronological correction fitting; all optimization and selection on CUDA."""
import copy
import time
import torch
from .models import ResidualCorrection,corrected_probability,predict_correction
from .evaluation import alarm_threshold


def build_model(family,c,mean,scale,blocks,W,seed):
    torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    return ResidualCorrection(family,c,mean,scale,blocks,W)


def fit_correction(family,c,parts,mean,scale,blocks,W,seed,regularization,checkpoint_path,
                   max_epochs=None,masked=False):
    model=build_model(family,c,mean,scale,blocks,W,seed)
    optimizer=torch.optim.AdamW(model.parameters(),lr=c['learning_rate'],weight_decay=c['weight_decay'],capturable=True)
    train,early=parts['correction_fit'],parts['early_stop']
    ids=torch.where(train['eligible'])[0][::3]
    best=torch.tensor(torch.inf,device='cuda',dtype=torch.float64);best_state=copy.deepcopy(model.state_dict())
    wait=0;history=[];start=time.perf_counter()
    begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);begin.record()
    rng=torch.Generator(device='cuda').manual_seed(seed)
    epochs=max_epochs or c['max_epochs']
    for epoch in range(epochs):
        model.train();perm=ids[torch.randperm(len(ids),device='cuda',generator=rng)]
        train_losses=[]
        for index in perm.split(c['batch_size']):
            rm=None
            if masked:
                choices=torch.tensor([0,4,8,16],device='cuda')
                budget=choices[torch.randint(4,(len(index),),device='cuda',generator=rng)]
                rank=torch.rand((len(index),16),device='cuda',generator=rng).argsort(1).argsort(1)
                rm=rank<budget[:,None]
            residual=model(train['X'][index],train['p'][index],train['Z'][index],train['node_mask'][index],rm)
            p=corrected_probability(train['p'][index],residual)
            mse=(p-train['y'][index]).square().mean()
            objective=mse+regularization*residual.square().mean()
            optimizer.zero_grad(set_to_none=True);objective.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),5.)
            optimizer.step();train_losses.append(mse.detach())
        with torch.no_grad():
            r=predict_correction(model,early);p=corrected_probability(early['p'],r)
            score=(p[early['eligible']]-early['y'][early['eligible']]).square().mean()
        history.append(dict(epoch=epoch+1,training_brier=torch.stack(train_losses).mean().item(),early_brier=score.item()))
        if bool((score<best-c['minimum_improvement']).item()):
            best=score;best_state=copy.deepcopy(model.state_dict());wait=0
            torch.save(dict(state=best_state,epoch=epoch+1,seed=seed,regularization=regularization),checkpoint_path)
        else:
            wait+=1
        if epoch==0 or (epoch+1)%10==0:
            print(f'{family} seed={seed} lambda={regularization} epoch={epoch+1} early={score.item():.6f}',flush=True)
        if wait>=c['patience']: break
    end.record();torch.cuda.synchronize()
    model.load_state_dict(best_state);model.eval()
    return model,dict(family=family,seed=seed,regularization=regularization,best_early_brier=best.item(),
        epochs=len(history),history=history,fit_wall_seconds=time.perf_counter()-start,cuda_event_span_seconds=begin.elapsed_time(end)/1000,
        parameters=sum(p.numel() for p in model.parameters()),masked_inputs=masked)


@torch.no_grad()
def shrink_and_alarm(model,part,grid):
    residual=predict_correction(model,part)
    take=part['eligible'];y=part['y'][take];base=part['p'][take];r=residual[take]
    candidates=torch.tensor(grid,device='cuda',dtype=torch.float64)
    probabilities=(base[None]+candidates[:,None]*r.double()[None]).clamp(0,1)
    losses=(probabilities-y).square().mean(1)
    i=int(losses.argmin().item());alpha=grid[i]
    p=corrected_probability(part['p'],residual,alpha)
    onset=take&~part['active']
    threshold=alarm_threshold(p[onset],part['y'][onset])
    return dict(alpha=alpha,shrinkage_brier=losses[i].item(),grid_brier=losses.tolist(),threshold=threshold.item())
