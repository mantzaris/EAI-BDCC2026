"""Diagnose simulator defects on chronological training holdout, CPU only."""
import json
import time
import resource
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from threadpoolctl import threadpool_limits
from traffic_risk_twins.ingestion import PemsSource, label_origins
from traffic_risk_twins.observation_quality import valid_mask, SpeedTransform
from traffic_risk_twins.chronological_splits import uniform_origins
from traffic_risk_twins.stage2_protocol import inner_windows, score_record
from traffic_risk_twins.graph_dynamics import fit_dynamics, calendar_features, residual_bank, rollout
from traffic_risk_twins.conditional_history import GaussianHistory
from traffic_risk_twins.retained_information import retain, independent_constraints
from traffic_risk_twins.event_functionals import event
from traffic_risk_twins.scenarios import rng_stream
from traffic_risk_twins.data_access import save_json, sha256


def transitions(timestamps, rows):
    valid = np.zeros(len(timestamps), bool); valid[rows] = True
    good = valid & np.roll(valid, 1) & np.roll(valid, 2)
    good[:2] = False
    good[2:] &= (timestamps[2:]-timestamps[:-2]).asi8 == 600_000_000_000
    return good


def main(config):
    start = time.perf_counter(); out = Path('results/stage2')
    if (out/'inner_model_diagnosis.json').exists(): raise FileExistsError('Preserve diagnosis')
    data = np.load(config['input_archive']); source = PemsSource(config['raw_file'])
    speed = source.read('train'); mask = valid_mask(speed)
    transform = SpeedTransform(data['free']); state = transform.forward(speed, mask)
    outer = source.splits['train']; all_origins = outer['origins'][::12]
    inner = inner_windows(source.timestamps, outer['rows'], all_origins, outer['days'])
    fit = inner['fit']; ids = fit['rows']; W = data['W']; C = calendar_features(source.timestamps)
    filled = np.where(mask, state, -6.906754778648553)
    model = fit_dynamics(filled, source.timestamps, W, transitions(source.timestamps, ids))
    bank = []; bank_origins = []; fold_records = []
    for j, days in enumerate(np.array_split(np.asarray(fit['days']), 3)):
        hold = np.asarray(source.timestamps.normalize().isin(pd.DatetimeIndex(days)))
        fit_rows = ids[~hold[ids]]
        m = fit_dynamics(filled, source.timestamps, W, transitions(source.timestamps, fit_rows))
        oo = np.asarray([o for o in fit['origins'] if hold[o-1:o+7].all()])
        bank.append(residual_bank(filled, source.timestamps, W, m, oo)); bank_origins.extend(oo)
        fold_records.append(dict(fold=j, held_days=days.tolist(), bank_sequences=len(oo)))
    bank = np.concatenate(bank); bank_origins = np.asarray(bank_origins)
    tbank = source.timestamps[bank_origins]
    regimes = (tbank.dayofweek >= 5).astype(int)*3+tbank.hour//8
    origins = uniform_origins(inner['diagnosis']['origins'], 128)
    labels = label_origins(state, mask, origins, int(data['threshold']))
    hi = origins[:, None]+np.arange(-11, 1); fi = origins[:, None]+np.arange(1, 7)
    raw_residual = residual_bank(filled, source.timestamps, W, model, origins)
    rows = []; trajectory_rows = []; mc_means = []; residual_ids = []
    for i, origin in enumerate(origins):
        t = source.timestamps[origin]; regime = int(t.dayofweek >= 5)*3+t.hour//8
        candidates = np.flatnonzero(regimes == regime)
        chosen = rng_stream(config['seed'], origin, 201).choice(candidates, 256)
        initial = np.broadcast_to(state[hi[i]], (256, 12, len(W)))
        seasonal = model.forcing_mean(source.timestamps[fi[i]])
        states = rollout(initial, bank[chosen]+seasonal, W, model.coefficients)
        mean = states.mean(axis=0); mc_means.append(mean); residual_ids.append(chosen)
        p = float(event(states, int(data['threshold'])).mean())
        rows.append(dict(origin=int(origin), day=str(t.date()), label=int(labels['low'][i]),
                         eligible=bool(labels['eligible'][i]), probability=p, current_active=bool(labels['current_active'][i]), N=256))
        for h in range(6):
            truth = state[fi[i, h]]; valid = mask[fi[i, h]]
            pred_speed = transform.inverse(states[:, h]).mean(axis=0)
            current_severe = state[origin] >= 0
            trajectory_rows.append(dict(origin=int(origin), step=h+1, state_bias=float((mean[h]-truth)[valid].mean()),
                state_rmse=float(np.sqrt(np.mean((mean[h]-truth)[valid]**2))),
                mae_raw=float(np.abs(pred_speed-speed[fi[i, h]])[valid].mean()),
                persistence_mae_raw=float(np.abs(speed[origin]-speed[fi[i, h]])[valid].mean()),
                severe_fraction_prediction=float((states[:, h] >= 0).mean()), severe_fraction_observed=float((truth[valid] >= 0).mean()),
                severe_current_state_bias=float((mean[h]-truth)[valid & current_severe].mean()) if (valid & current_severe).any() else None,
                mean_noise_sd=float(states[:, h].std(axis=0).mean())))
    pd.DataFrame(rows).to_csv(out/'inner_simulator_predictions.csv', index=False)
    pd.DataFrame(trajectory_rows).to_csv(out/'inner_trajectory_diagnostics.csv', index=False)
    x = state[origins]; mean_residual = raw_residual.mean(axis=1)
    condition = []
    for name, take in [('current_severe', x >= 0), ('current_not_severe', x < 0), ('near_threshold', np.abs(x) < 1)]:
        condition.append(dict(group=name, n=int(take.sum()), future_residual_mean=float(mean_residual[take].mean()),
                              future_residual_sd=float(mean_residual[take].std())))
    flat = bank.reshape(-1, len(W)); spatial = np.corrcoef(flat, rowvar=False)
    # Training-only covariance, not the Stage 1 model fitted across this inner block.
    seasonal_coef = np.linalg.lstsq(C[ids], state[ids], rcond=None)[0]
    season = C@seasonal_coef
    hfit = fit['origins'][:, None]+np.arange(-11, 1)
    gaussian = GaussianHistory.fit(state[hfit]-season[hfit], rank=16)
    reconstruction = []
    for fraction in (0., .15):
        errors = []; cover = []; standardized = []; residual_consistency = 0.
        selected = data['ordering'][:int(np.ceil(fraction*len(W)))]
        for i in np.unique(np.linspace(0, len(origins)-1, 16, dtype=int)):
            retained = retain(state[hi[i]], mask[hi[i]], data['blocks'], selected, C[origins[i]])
            A, b = independent_constraints(retained, data['blocks'])
            samples = gaussian.sample(A, b, 256, rng_stream(config['seed'], origins[i], 203),
                                       mean=season[hi[i]].ravel()+gaussian.mean)
            hidden = mask[hi[i]].copy(); hidden[:, selected] = False; hidden = hidden.ravel()
            truth = state[hi[i]].ravel(); mean = gaussian.conditional_mean(A, b, mean=season[hi[i]].ravel()+gaussian.mean)
            errors.extend((mean-truth)[hidden].tolist())
            quantile = np.quantile(samples, [.025, .975], axis=0)
            cover.extend(((truth >= quantile[0]) & (truth <= quantile[1]))[hidden].tolist())
            standardized.extend(((mean-truth)**2/np.maximum(samples.var(axis=0, ddof=1), 1e-10))[hidden].tolist())
            residual_consistency = max(residual_consistency, float(np.max(np.abs(A@samples.T-b[:, None]))))
        reconstruction.append(dict(retention=fraction, hidden_rmse=float(np.sqrt(np.mean(np.square(errors)))),
            nominal_95_coverage=float(np.mean(cover)), mean_squared_standardized_error=float(np.mean(standardized)),
            maximum_constraint_residual=residual_consistency, diagnostic_origins=16, conditional_samples=256))
    result = dict(cpu_seconds=time.perf_counter()-start, gpu_seconds=0, inner_fit_days=fit['days'],
        inner_diagnosis_days=inner['diagnosis']['days'], coefficients=model.coefficients.tolist(), bank_shape=list(bank.shape),
        bank_oof_folds=fold_records, inner_full_retention=score_record(labels['low'], [r['probability'] for r in rows]),
        residual_global_mean=float(bank.mean()), residual_sd=float(bank.std()),
        residual_lag1=float(np.corrcoef(bank[:, :-1].ravel(), bank[:, 1:].ravel())[0, 1]),
        residual_mean_absolute_spatial_correlation=float(np.abs(spatial-np.eye(len(W))).sum()/(len(W)*(len(W)-1))),
        heldout_residual_mean=float(raw_residual.mean()), heldout_residual_sd=float(raw_residual.std()),
        residual_by_current_state=condition, covariance_diagnostics=reconstruction,
        transform_lower_clip_fraction=float((state[ids] <= -6.906754778648552).mean()),
        transform_upper_clip_fraction=float((state[ids] >= 6.906754778648552).mean()),
        clipped_inverse_max_error=float(np.max(np.abs(transform.inverse(state[ids])-np.clip(speed[ids], .001*data['free'], .999*data['free'])))),
        raw_inverse_mae=float(np.abs(transform.inverse(state[ids])-speed[ids]).mean()),
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024, test_access=False)
    private = Path('data/processed/stage2'); private.mkdir(exist_ok=True)
    np.savez_compressed(private/'inner_diagnosis.npz', origins=origins, bank=bank, bank_origins=bank_origins,
        bank_regimes=regimes, coefficients=model.coefficients, seasonal=model.seasonal, mean_trajectories=np.asarray(mc_means),
        residual_ids=np.asarray(residual_ids), observed_residual=raw_residual)
    result['private_archive_sha256'] = sha256(private/'inner_diagnosis.npz')
    save_json(out/'inner_model_diagnosis.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    config = yaml.safe_load(Path('configs/stage2_diagnosis.yaml').read_text())
    with threadpool_limits(config['cpu_threads']): main(config)
