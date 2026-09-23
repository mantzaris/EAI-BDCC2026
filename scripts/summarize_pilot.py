"""Recompute reported development metrics from compact, completed numerical outputs."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from traffic_risk_twins.observational_evaluation import evaluate
from traffic_risk_twins.data_access import save_json


def paired_difference(frame,column_a,column_b):
    difference=np.asarray(frame[column_a])-np.asarray(frame[column_b])
    days=frame['day'].to_numpy(); clusters=[np.flatnonzero(days == d) for d in np.unique(days)]
    rng=np.random.default_rng(20260922)
    values=[]
    for _ in range(1000):
        ids=np.concatenate([clusters[i] for i in rng.integers(0,len(clusters),len(clusters))])
        values.append(float(difference[ids].mean()))
    return dict(mean=float(difference.mean()),day_bootstrap_95=np.quantile(values,[.025,.975]).tolist(),days=len(clusters))


def main(directory):
    directory=Path(directory)
    run=json.loads((directory/'run.json').read_text())
    if not run['complete'] or run['completed_origins'] != 128:
        raise ValueError('Final Stage 1 summary requires the complete prespecified panel')
    predictions=pd.read_csv(directory/'predictions.csv')
    timings=pd.read_csv(directory/'timings.csv')
    enclosures=pd.read_csv(directory/'enclosures.csv')
    reconstruction=pd.read_csv(directory/'reconstruction.csv')
    allocations=pd.read_csv(directory/'allocations.csv')
    metrics={}; metric_rows=[]
    for (method,retention,N),group in predictions.groupby(['method','retention','N']):
        key=f'{method}/retention={retention}/N={N}'
        score=group[group.eligible]
        result=evaluate(score.label,score.probability,score.day)
        onset=score[~score.current_active]
        result['onset']=evaluate(onset.label,onset.probability,onset.day)
        # Development threshold chosen on these same validation negatives: descriptive only.
        negative=onset[onset.label == 0].probability.to_numpy()
        threshold=float(np.quantile(negative,.95))
        warn=onset.probability.to_numpy() > threshold
        y=onset.label.to_numpy().astype(bool)
        result['development_warning'] = dict(threshold=threshold,comparison='strict greater',
            false_alarm_rate=float(warn[~y].mean()),recall=float(warn[y].mean()) if y.any() else None,
            precision=float(y[warn].mean()) if warn.any() else None,
            note='Threshold selected and described on validation, not an independent detection evaluation; no lead-time estimate.')
        if method == 'fine_mc':
            result['ordinary']={c:float(score[c].mean()) for c in score.columns if c.startswith('mae_')}
            result['estimated_mc_variance_mean']=float((score.probability*(1-score.probability)/N).mean())
        metrics[key]=result
        metric_rows.append(dict(method=method,retention=retention,N=N,brier=result['brier'],
            brier_low=result['brier_day_bootstrap_95'][0],brier_high=result['brier_day_bootstrap_95'][1],
            onset_brier=result['onset']['brier'],n=result['n'],positives=result['positives'],pr_auc=result['pr_auc'],
            mean_seconds=float(group.total_seconds.mean()),p95_seconds=float(group.total_seconds.quantile(.95))))
    comparisons={}
    fine=predictions[(predictions.method == 'fine_mc')&predictions.eligible].copy()
    fine['loss']=(fine.label-fine.probability)**2
    pivot=fine.pivot(index=['origin','day'],columns=['retention','N'],values='loss').reset_index()
    for fraction in (.15,1.):
        comparisons[f'information_{fraction}_minus_0_at_1024']=paired_difference(pivot,(fraction,1024),(0.,1024))
    for fraction in (0.,.15,1.):
        comparisons[f'1024_minus_256_at_retention_{fraction}']=paired_difference(pivot,(fraction,1024),(fraction,256))
    baselines=pd.read_csv('results/tables/baseline_predictions.csv')
    for fraction in (0.,.15,1.):
        g=fine[(fine.retention == fraction)&(fine.N == 1024)]
        for kind,b in baselines.groupby('model'):
            joined=g.merge(b,on='origin',suffixes=('_fine','_baseline'))
            joined['baseline_loss']=(joined.label-joined.probability_baseline)**2
            comparisons[f'retention_{fraction}_minus_{kind}']=paired_difference(joined,'loss','baseline_loss')
    cost=timings.groupby(['device','method','retention','N']).total_seconds.agg(['mean','median',lambda x:x.quantile(.95)]).reset_index()
    cost.columns=['device','method','retention','N','mean_seconds','median_seconds','p95_seconds']
    for field in ['conditioning_setup_seconds','sampling_seconds','residual_gather_seconds','enclosure_seconds','compaction_seconds','fine_seconds','transfer_seconds','event_seconds']:
        means=timings.groupby(['device','method','retention','N'])[field].mean().reset_index(name=field)
        cost=cost.merge(means,on=['device','method','retention','N'])
    enc=enclosures.groupby(['retention','N']).agg(unresolved_fraction=('unresolved_fraction','mean'),
        coarse_fine_agreement=('coarse_fine_agreement','mean'),correction_variance=('correction_variance','mean'),
        mean_radius=('mean_radius','mean'),actual_mean_error=('actual_mean_error','mean'),
        maximum_enclosure_violation=('maximum_enclosure_violation','max')).reset_index()
    rec=reconstruction.groupby('retention').agg(origins=('origin','count'),mean_rmse=('rmse','mean'),
        coverage_50=('coverage_50','mean'),coverage_80=('coverage_80','mean'),coverage_95=('coverage_95','mean')).reset_index()
    out=Path('results/tables')
    pd.DataFrame(metric_rows).to_csv(out/'pilot_metrics.csv',index=False)
    cost.to_csv(out/'pilot_costs.csv',index=False); enc.to_csv(out/'pilot_enclosures.csv',index=False)
    rec.to_csv(out/'pilot_reconstruction.csv',index=False)
    save_json(out/'pilot_metrics_detail.json',metrics)
    save_json(out/'paired_comparisons.json',comparisons)
    allocation_summary=dict(raw_outside_unit_interval=int(((allocations.estimate < 0)|(allocations.estimate > 1)).sum()),
        allocation_cases=len(allocations),mean_n0=float(allocations.n0.mean()),mean_n1=float(allocations.n1.mean()),
        mean_estimator_seconds=float(allocations.estimator_seconds.mean()),
        mean_allocation_and_estimator_seconds=float(allocations.allocation_and_estimator_seconds.mean()),
        mean_budget_ratio=float((allocations.estimator_seconds/allocations.budget_seconds).mean()),
        uncertainty='Hoeffding union bounds, raw estimate retained; clipping separately used for scores')
    save_json(out/'allocation_summary.json',allocation_summary)
    # Ordinary baselines on exactly the same eligible origins and origin weighting.
    from traffic_risk_twins.ingestion import PemsSource
    from traffic_risk_twins.observation_quality import valid_mask
    from scipy.special import expit
    source=PemsSource('data/raw/pems-bay.h5')
    values=source.read('validation')
    g=fine[(fine.retention == 1.)&(fine.N == 1024)].sort_values('origin')
    origins=g.origin.to_numpy()
    with np.load('data/processed/pilot_inputs.npz') as a:
        free=a['free']
    matched={}
    for name in ('persistence_raw','persistence_capped'):
        item={}
        prediction=values[origins] if name == 'persistence_raw' else np.minimum(values[origins],free)
        for h in (3,6):
            target=values[origins+h];mask=valid_mask(target)&valid_mask(values[origins])
            for target_name,target_values in [('raw',target),('capped',np.minimum(target,free))]:
                item[f'mae_{h*5}min_{target_name}']=float(np.nanmean(np.nanmean(np.where(mask,np.abs(prediction-target_values),np.nan),axis=1)))
        matched[name]=item
    save_json(out/'matched_ordinary_baselines.json',dict(origins=len(origins),weighting='equal origins, valid sensors within origin',results=matched))
    print(pd.DataFrame(metric_rows).query("method == 'fine_mc'").to_string(index=False))
    print(enc.to_string(index=False)); print(rec.to_string(index=False)); print(json.dumps(comparisons,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',default='results/stage1_pilot')
    main(p.parse_args().results)
