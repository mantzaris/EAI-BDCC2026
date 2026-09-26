"""CPU-only training and preparation. Does not import torch or read test values."""
import argparse
import datetime
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from threadpoolctl import threadpool_limits
from traffic_risk_twins.ingestion import PemsSource,load_graph,label_origins
from traffic_risk_twins.observation_quality import valid_mask,SpeedTransform
from traffic_risk_twins.chronological_splits import uniform_origins
from traffic_risk_twins.retained_information import spatial_partition,fixed_selector
from traffic_risk_twins.conditional_history import GaussianHistory
from traffic_risk_twins.graph_dynamics import calendar_features,fit_dynamics,residual_bank,rollout
from traffic_risk_twins.predictive_baselines import features,fit_predict
from traffic_risk_twins.observational_evaluation import evaluate
from traffic_risk_twins.data_access import save_json,sha256


def prepare(config):
    start=time.perf_counter()
    source=PemsSource('data/raw/pems-bay.h5')
    train,validation=source.read('train'),source.read('validation')
    train_mask,val_mask=valid_mask(train),valid_mask(validation)
    tr_rows=source.splits['train']['rows']
    transform=SpeedTransform.fit(train[tr_rows],train_mask[tr_rows])
    ytrain=transform.forward(train,train_mask); yval=transform.forward(validation,val_mask)
    W,graph=load_graph('data/raw/adj_mx_bay.pkl',source.sensors)
    coords=pd.read_csv('data/raw/graph_sensor_locations_bay.csv',header=None,index_col=0).loc[source.sensors].to_numpy()
    blocks=spatial_partition(coords,config['observation_blocks'])
    C=calendar_features(source.timestamps)
    # Calendar regression on training only; missing fitting entries get train means.
    means=np.nanmean(ytrain[tr_rows],axis=0)
    calendar_coef=np.linalg.lstsq(C[tr_rows],np.where(train_mask[tr_rows],ytrain[tr_rows],means),rcond=None)[0]
    season=C@calendar_coef
    filled=np.where(train_mask,ytrain,season)
    valid=np.zeros(len(source.timestamps),bool); valid[tr_rows]=True
    transitions=valid&np.roll(valid,1)&np.roll(valid,2)
    dynamics=fit_dynamics(filled,source.timestamps,W,transitions)
    ordering,score=fixed_selector(ytrain[tr_rows],blocks,W,dynamics.coefficients)
    train_origins=source.splits['train']['origins']
    # Fixed six-frame spacing; no event-based sampling. All H-frame banks stay in their OOF fold.
    fit_origins=train_origins[::12]
    history_index=fit_origins[:,None]+np.arange(-11,1)
    histories=ytrain[history_index]-season[history_index]
    gaussian=GaussianHistory.fit(histories,rank=config['factor_rank'])
    folds=np.array_split(np.asarray(source.splits['train']['days']),3)
    bank=[]; bank_origin=[]; oof=[]
    for fold,days in enumerate(folds):
        hold=np.asarray(source.timestamps.normalize().isin(pd.DatetimeIndex(days)))
        fit_valid=transitions&~hold&~np.roll(hold,1)&~np.roll(hold,2)
        model=fit_dynamics(filled,source.timestamps,W,fit_valid)
        eligible=[int(o) for o in train_origins[::6] if hold[o-1:o+7].all()]
        bank.append(residual_bank(filled,source.timestamps,W,model,eligible))
        bank_origin.extend(eligible)
        oof.append(dict(fold=fold,held_days=days.tolist(),fit_transitions=int(fit_valid.sum()),bank_sequences=len(eligible),coefficients=model.coefficients.tolist()))
    bank=np.concatenate(bank); bank_origin=np.asarray(bank_origin)
    # Coarse calendar regimes, fixed in advance; retain entire residual sequences.
    bank_regime=(source.timestamps[bank_origin].dayofweek >= 5).astype(int)*3+source.timestamps[bank_origin].hour//8
    val_origins=uniform_origins(source.splits['validation']['origins'],config['max_validation_origins'])
    hi=val_origins[:,None]+np.arange(-11,1); fi=val_origins[:,None]+np.arange(1,7)
    audit=json.loads(Path('manifests/data_audit.json').read_text())
    threshold=audit['threshold_count']
    labels=label_origins(yval,val_mask,val_origins,threshold)
    train_labels=label_origins(ytrain,train_mask,fit_origins,threshold)
    baseline_rows=[]; baseline_metrics={}
    for kind in ('seasonal_persistence','aggregate_memory','heterogeneity'):
        before=time.perf_counter()
        X=features(ytrain[history_index],train_mask[history_index],blocks,C[fit_origins],kind)
        Xval=features(yval[hi],val_mask[hi],blocks,C[val_origins],kind)
        eligible=train_labels['eligible']
        predictions,_=fit_predict(X[eligible],train_labels['low'][eligible],Xval,kind)
        elapsed=time.perf_counter()-before
        ok=labels['eligible']
        metrics=evaluate(labels['low'][ok],predictions[ok],source.timestamps[val_origins[ok]].strftime('%Y-%m-%d'))
        onset=ok&~labels['current_active']
        metrics['onset']=evaluate(labels['low'][onset],predictions[onset],source.timestamps[val_origins[onset]].strftime('%Y-%m-%d'))
        metrics['training_and_prediction_seconds']=elapsed
        metrics['information']='block histories, counts, calendar' if kind != 'heterogeneity' else 'additional local variance, min, max, severe fractions'
        baseline_metrics[kind]=metrics
        for o,p in zip(val_origins,predictions): baseline_rows.append(dict(origin=int(o),model=kind,probability=float(p)))
    # Ordinary full-history persistence and training-seasonal speeds; more information than 0%.
    raw_future=validation[fi]
    capped=np.minimum(raw_future,transform.free)
    persistence=np.broadcast_to(validation[val_origins,None,:],raw_future.shape)
    seasonal_speed=transform.inverse(season[fi])
    for name,prediction in [('full_sensor_speed_persistence',persistence),('seasonal_speed',seasonal_speed)]:
        ordinary={}
        for offset in (2,5):
            observed=val_mask[fi][:,offset]&np.isfinite(prediction[:,offset])
            ordinary[str((offset+1)*5)+'min_raw_mae']=float(np.abs(prediction[:,offset]-raw_future[:,offset])[observed].mean())
            ordinary[str((offset+1)*5)+'min_capped_mae']=float(np.abs(prediction[:,offset]-capped[:,offset])[observed].mean())
        baseline_metrics[name]=ordinary
    Path('data/processed').mkdir(parents=True,exist_ok=True)
    # Only saved validation origins, no test data; model bank is non-redistributed.
    target=Path('data/processed/pilot_inputs.npz')
    np.savez_compressed(target,W=W,blocks=blocks,ordering=ordering,selection_score=score,
        gaussian_mean=gaussian.mean,U=gaussian.U,diagonal=gaussian.diagonal,
        coefficients=dynamics.coefficients,seasonal=dynamics.seasonal,free=transform.free,
        bank=bank.astype(np.float32),bank_origins=bank_origin,bank_regime=np.asarray(bank_regime),
        origins=val_origins,timestamps=source.timestamps[val_origins].asi8,
        history=yval[hi],history_mask=val_mask[hi],prior_mean=(season[hi]+gaussian.mean.reshape(12,-1)).reshape(len(hi),-1),
        calendar=C[val_origins],future=raw_future,future_mask=val_mask[fi],
        seasonal_forcing=dynamics.forcing_mean(source.timestamps[fi.ravel()]).reshape(len(fi),6,-1),
        labels=labels['low'],label_eligible=labels['eligible'],current_active=labels['current_active'],
        threshold=np.asarray(threshold))
    save_json('results/tables/baseline_metrics.json',baseline_metrics)
    pd.DataFrame(baseline_rows).to_csv('results/tables/baseline_predictions.csv',index=False)
    metadata=dict(prepared_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpu_seconds=time.perf_counter()-start,
                  fitting_device='CPU only',coefficients=dynamics.coefficients.tolist(),stability_sum=float(dynamics.coefficients.sum()),
                  dynamics_fit='constrained one-step least squares; short-rollout-loss optimization omitted in Stage 1',
                  gaussian_training_histories=len(fit_origins),gaussian_rank=gaussian.U.shape[1],diagonal_floor=1e-6,
                  missing_fitting_policy='training-mean fill of calendar-centered histories; omit unavailable exact constraints',
                  seasonal_features=['intercept','daily_sin','daily_cos','second_harmonic_sin','second_harmonic_cos','weekend'],
                  residual_sequence_count=len(bank),oof_folds=oof,regime_rule='weekday/weekend x hour//8',
                  residual_float32_storage='rounding to float32 is part of the fixed empirical working law',
                  origin_selection='128 uniformly spaced indices in split-contained validation origins; no future labels consulted',
                  validation_origins=val_origins.tolist(),selected_15_percent=ordering[:int(np.ceil(.15*len(W)))].tolist(),
                  data_file=str(target),data_bytes=target.stat().st_size,data_sha256=sha256(target),raw_sha256=audit['source_sha256'],
                  config_sha256=sha256('configs/stage1_pilot.yaml'),test_access=False)
    # Residual dependence is diagnostic, not extra independent observations.
    flat=bank.reshape(-1,len(W))
    corr=np.corrcoef(flat,rowvar=False)
    metadata['residual_mean_absolute_offdiagonal_correlation']=float(np.abs(corr-np.eye(len(W))).sum()/(len(W)*(len(W)-1)))
    metadata['residual_lag1_correlation']=float(np.corrcoef(bank[:,:-1].ravel(),bank[:,1:].ravel())[0,1])
    save_json('manifests/derived_data.json',metadata)
    print(json.dumps({k:v for k,v in metadata.items() if k not in ('oof_folds','validation_origins','selected_15_percent')},indent=2))


if __name__ == '__main__':
    config=yaml.safe_load(Path('configs/stage1_pilot.yaml').read_text())
    with threadpool_limits(config['cpu_threads']): prepare(config)
