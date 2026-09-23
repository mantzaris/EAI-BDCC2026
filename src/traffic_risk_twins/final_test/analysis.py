"""Frozen GPU summaries; seed losses are averaged, never probabilities."""
import torch
from ..residual_gpu.data import to_cuda
from ..residual_gpu.evaluation import alignment
from ..onset_graph.evaluation import onset, population, resample
from ..onset_graph.io import read


PRIMARY = [('C', 'B'), ('D', 'C'), ('E', 'D'), ('E', 'B')]
SECONDARY = [('B', 'R_union')] + [(a,b) for a in ('C','D','M','S','E','F')
    for b in ('B','K','R_union','A_mono','D') if a != b] + [
    ('D','D_rewire_20261004'), ('D','D_rewire_20261005'), ('E','E_self'),
    ('E','E_internal'), ('E','E_rewire_20261004'), ('E','E_rewire_20261005')]


def summaries(part, predictions, thresholds, families, config, primary=True):
    result = population(part, predictions, thresholds, families, PRIMARY, config,
                        primary_family=primary)
    extra = population_pairs(part, predictions, families, SECONDARY, config)
    result['secondary_paired'] = extra
    result['diagnostics'] = {}
    for endpoint, keep in [('onset', onset(part)), ('all_time', part['eligible'])]:
        y, days, times = part['y'][keep], part['day'][keep], part['time_ns'][keep]
        for name, keys in families.items():
            p = torch.stack([predictions[k][keep] for k in keys])
            loss = (p-y).square()
            alarm = torch.stack([predictions[k][keep] > thresholds[k] for k in keys]).double()
            pos = y == 1
            values = torch.stack([loss.mean(0), (alarm*pos).mean(0),
                (alarm*~pos).mean(0), pos.double(), (~pos).double()], 1)
            draws = resample(values, days, 3, config['replicates'], config['seed'])
            rec = dict(brier=loss.mean().item(), event_contribution=(loss*pos).mean().item(),
                nonevent_contribution=(loss*~pos).mean().item(), prevalence=y.mean().item(),
                zero_fraction=(p==0).double().mean().item(), one_fraction=(p==1).double().mean().item(),
                tie_fraction=torch.stack([(predictions[k][keep]==thresholds[k]).double().mean() for k in keys]).mean().item(),
                mean_probability=p.mean().item(), n=len(y), positives=int(pos.sum().item()),
                brier_95=torch.quantile(draws[:,0], draws.new_tensor([.025,.975])).tolist(),
                mean_detected_groups=to_cuda([result['models'][k][endpoint]['episodes']['detected_groups'] for k in keys],torch.float64).mean().item(),
                mean_false_alarm_groups=to_cuda([result['models'][k][endpoint]['episodes']['false_alarm_groups'] for k in keys],torch.float64).mean().item())
            for label,a,b in [('recall',1,3),('fpr',2,4)]:
                good = draws[:,b] > 0
                rec[label+'_95'] = torch.quantile(draws[good,a]/draws[good,b], draws.new_tensor([.025,.975])).tolist() if good.any() else None
                if not values[:,b].sum():
                    result['families'][name][endpoint]['mean_'+label] = None
            rec['reliability'] = []
            bid = torch.bucketize(p, p.new_tensor([.01,.05,.1,.2,.4,.6,.8]), right=True)
            labels = y.expand_as(p)
            for b in range(8):
                take = bid == b
                if take.any():
                    rec['reliability'].append(dict(bin=b, seed_origin_count=int(take.sum().item()),
                        predicted=p[take].mean().item(), observed=labels[take].mean().item()))
            identities = [alignment(y, predictions['A_G'][keep], predictions[k][keep]) for k in keys]
            rec['alignment'] = {k:to_cuda([r[k] for r in identities],torch.float64).mean().item() for k in identities[0]}
            result['diagnostics'].setdefault(name,{})[endpoint] = rec
    return result


def population_pairs(part, predictions, families, pairs, config):
    result = {}
    for endpoint, keep in [('onset', onset(part)), ('all_time', part['eligible'])]:
        y, days = part['y'][keep], part['day'][keep]
        losses = {name:torch.stack([(predictions[k][keep]-y).square() for k in keys]).mean(0)
                  for name,keys in families.items()}
        for a,b in dict.fromkeys(pairs):
            d = losses[a]-losses[b]
            r = dict(a=a,b=b,difference=d.mean().item(),relative_reduction=(-d.mean()/losses[b].mean()).item(),
                     primary=False, meaning='Descriptive secondary; no multiplicity-adjusted claim')
            for length in config['block_days']:
                draws = resample(torch.stack([losses[a],losses[b]],1),days,length,config['replicates'],config['seed'])
                r[str(length)] = dict(pointwise_95=torch.quantile(draws[:,0]-draws[:,1],d.new_tensor([.025,.975])).tolist())
            if len(families[a]) == len(families[b]):
                r['seed_differences'] = [((predictions[ka][keep]-y).square()-(predictions[kb][keep]-y).square()).mean().item()
                                         for ka,kb in zip(families[a],families[b])]
            result[a+'_minus_'+b+'_'+endpoint] = r
    return result


def summarize_existing_costs(path):
    source = read(path)
    names = list(dict.fromkeys(r['family'] for r in source['repeats']))
    return dict(source=path, scope=source['scope'], first_seed_only=True, no_new_timing=True,
        families={name:dict(complete_seconds=to_cuda([r['complete_wall_seconds'] for r in source['repeats'] if r['family']==name],torch.float64).mean().item(),
                           repeats=[r['complete_wall_seconds'] for r in source['repeats'] if r['family']==name]) for name in names})
