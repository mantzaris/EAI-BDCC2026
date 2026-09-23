"""CPU-only single repair gate and training-only simulator risk calibration."""
import time
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from threadpoolctl import threadpool_limits
from traffic_risk_twins.ingestion import PemsSource, label_origins
from traffic_risk_twins.observation_quality import valid_mask, SpeedTransform
from traffic_risk_twins.graph_dynamics import Dynamics, fit_dynamics, residual_bank, rollout
from traffic_risk_twins.stage2_protocol import inner_windows, score_record, LogisticCalibration, alarm_threshold, paired_uncertainty
from traffic_risk_twins.chronological_splits import uniform_origins
from traffic_risk_twins.scenarios import rng_stream
from traffic_risk_twins.residual_location import ResidualLocation
from traffic_risk_twins.event_functionals import event
from traffic_risk_twins.data_access import save_json, sha256
from stage2_inner_diagnosis import transitions


def main(config):
    start = time.perf_counter(); out = Path('results/stage2')
    if (out/'repair_results.json').exists(): raise FileExistsError('Preserve attempted repair')
    data = np.load(config['input_archive']); source = PemsSource(config['raw_file'])
    raw = source.read('train'); mask = valid_mask(raw); transform = SpeedTransform(data['free'])
    state = transform.forward(raw, mask); filled = np.where(mask, state, -6.906754778648553)
    outer = source.splits['train']; oo = outer['origins'][::12]
    inner = inner_windows(source.timestamps, outer['rows'], oo, outer['days'])
    diagnosis = np.load('data/processed/stage2/inner_diagnosis.npz')
    model = Dynamics(diagnosis['coefficients'], diagnosis['seasonal'])
    correction = ResidualLocation.fit(diagnosis['bank'], state[diagnosis['bank_origins']], diagnosis['bank_regimes'])
    centered = correction.centered_bank(diagnosis['bank'], state[diagnosis['bank_origins']], diagnosis['bank_regimes'])
    origins = diagnosis['origins']; labels = label_origins(state, mask, origins, int(data['threshold']))
    rows = []; trajectory = []
    def evaluate_origin(initial, base_forcing, repaired_forcing, truth, observed, origin, label, eligible, active, day, split, coeff):
        results = []
        for name, forcing in [('original', base_forcing), ('location_repair', repaired_forcing)]:
            before = time.perf_counter()
            paths = rollout(initial, forcing, data['W'], coeff)
            p = float(event(paths, int(data['threshold'])).mean())
            results.append(dict(split=split, origin=int(origin), model=name, N=len(initial), label=int(label),
                eligible=bool(eligible), current_active=bool(active), day=day, probability=p,
                rollout_event_seconds=time.perf_counter()-before))
            for h in (2, 5):
                speeds = transform.inverse(paths[:, h]).mean(axis=0)
                good = observed[h]
                trajectory.append(dict(split=split, origin=int(origin), model=name, step=h+1,
                    mae_raw=float(np.abs(speeds-truth[h])[good].mean())))
        return results
    for i, o in enumerate(origins):
        t = source.timestamps[o]; regime = int(t.dayofweek >= 5)*3+t.hour//8
        chosen = diagnosis['residual_ids'][i]; fi = np.arange(o+1, o+7)
        initial = np.broadcast_to(state[o-11:o+1], (256, 12, len(data['W'])))
        seasonal = model.forcing_mean(source.timestamps[fi])
        base = diagnosis['bank'][chosen]+seasonal
        repair = centered[chosen]+correction.location(state[o], regime)+seasonal
        rows.extend(evaluate_origin(initial, base, repair, raw[fi], mask[fi], o, labels['low'][i],
            labels['eligible'][i], labels['current_active'][i], str(t.date()), 'inner_diagnosis', model.coefficients))
    df = pd.DataFrame(rows); tt = pd.DataFrame(trajectory)
    metrics = {name:score_record(g.label, g.probability) for name, g in df.groupby('model')}
    mae = tt[tt.step == 6].groupby('model').mae_raw.mean().to_dict()
    accepted = (metrics['location_repair']['brier'] <= .95*metrics['original']['brier'] and
                mae['location_repair'] <= 1.02*mae['original'])
    print('Inner repair gate:', accepted, 'Brier', {k:v['brier'] for k,v in metrics.items()}, 'MAE', mae, flush=True)
    # Freeze this gate before accessing any outer future labels in the private archive.
    save_json(out/'repair_inner_gate.json', dict(accepted=accepted, metrics=metrics, mae_30min=mae,
        parameters=correction.table.tolist(), group_counts=correction.counts.tolist(),
        outer_repaired_outcomes_not_yet_accessed=True))
    # Always perform original simulator calibration; repair is calibrated only if accepted.
    fit_rows = np.concatenate((inner['fit']['rows'], inner['diagnosis']['rows']))
    premodel = fit_dynamics(filled, source.timestamps, data['W'], transitions(source.timestamps, fit_rows))
    preorigins = np.concatenate((inner['fit']['origins'], inner['diagnosis']['origins']))
    prebank = []; prebank_origins = []
    fit_days = inner['fit']['days']+inner['diagnosis']['days']
    for days in np.array_split(np.asarray(fit_days), 3):
        hold = np.asarray(source.timestamps.normalize().isin(pd.DatetimeIndex(days)))
        m = fit_dynamics(filled, source.timestamps, data['W'], transitions(source.timestamps, fit_rows[~hold[fit_rows]]))
        bo = np.asarray([o for o in preorigins if hold[o-1:o+7].all()])
        prebank.append(residual_bank(filled, source.timestamps, data['W'], m, bo)); prebank_origins.extend(bo)
    prebank = np.concatenate(prebank); prebank_origins = np.asarray(prebank_origins)
    bt = source.timestamps[prebank_origins]
    regimes = np.asarray((bt.dayofweek >= 5).astype(int)*3+bt.hour//8)
    calorigins = uniform_origins(inner['calibration']['origins'], 128)
    callabels = label_origins(state, mask, calorigins, int(data['threshold']))
    calcorrection = ResidualLocation.fit(prebank, state[prebank_origins], regimes)
    calcentered = calcorrection.centered_bank(prebank, state[prebank_origins], regimes)
    calrows = []
    for i, o in enumerate(calorigins):
        t = source.timestamps[o]; regime = int(t.dayofweek >= 5)*3+t.hour//8
        chosen = rng_stream(config['seed'], o, 201).choice(np.flatnonzero(regimes == regime), 256)
        fi = np.arange(o+1, o+7); initial = np.broadcast_to(state[o-11:o+1], (256, 12, len(data['W'])))
        forcing = premodel.forcing_mean(source.timestamps[fi])
        for name, residual in [('original', prebank[chosen])]+([('location_repair', calcentered[chosen]+calcorrection.location(state[o], regime))] if accepted else []):
            paths = rollout(initial, residual+forcing, data['W'], premodel.coefficients)
            calrows.append(dict(split='inner_calibration', origin=int(o), model=name, day=str(t.date()), N=256,
                probability=float(event(paths, int(data['threshold'])).mean()), label=int(callabels['low'][i]),
                eligible=bool(callabels['eligible'][i]), current_active=bool(callabels['current_active'][i])))
    calibration = pd.DataFrame(calrows)
    calibration.to_csv(out/'simulator_inner_calibration.csv', index=False)
    # Original raw outer probabilities reuse Stage 1, saving all repeated computation.
    original = pd.read_csv('results/stage1_pilot/predictions.csv')
    orig = original[(original.method == 'fine_mc') & (original.retention == 1.) & (original.N == 256)].copy()
    outer_rows = []
    if accepted:
        outer_correction = ResidualLocation.fit(data['bank'], state[data['bank_origins']], data['bank_regime'])
        outer_centered = outer_correction.centered_bank(data['bank'], state[data['bank_origins']], data['bank_regime'])
        for i, o in enumerate(data['origins']):
            stamp = pd.Timestamp(int(data['timestamps'][i])); regime = int(stamp.dayofweek >= 5)*3+stamp.hour//8
            chosen = rng_stream(config['seed'], o, 1).choice(np.flatnonzero(data['bank_regime'] == regime), 256)
            # Omit unavailable measurements; Stage 1 full-retention has one missing
            # history on this panel. Reuse its exact conditional sampler there.
            before = time.perf_counter()
            if data['history_mask'][i].all():
                initial = np.broadcast_to(data['history'][i], (256, 12, len(data['W']))).copy()
            else:
                from traffic_risk_twins.conditional_history import GaussianHistory
                from traffic_risk_twins.scenarios import make_scenarios
                gaussian = GaussianHistory(data['gaussian_mean'], data['U'], data['diagonal'])
                initial, _, _ = make_scenarios(gaussian, data['history'][i], data['history_mask'][i], data['blocks'],
                    data['ordering'], data['calendar'][i], data['prior_mean'][i], data['bank'],
                    np.flatnonzero(data['bank_regime'] == regime), data['seasonal_forcing'][i], 256, config['seed'], int(o))
            forcing = outer_centered[chosen]+outer_correction.location(initial[:, -1], regime)+data['seasonal_forcing'][i]
            paths = rollout(initial, forcing, data['W'], data['coefficients'])
            p = float(event(paths, int(data['threshold'])).mean())
            total = time.perf_counter()-before
            outer_rows.append(dict(split='validation', origin=int(o), model='location_repair', N=256,
                label=int(data['labels'][i]), eligible=bool(data['label_eligible'][i]), current_active=bool(data['current_active'][i]),
                day=str(stamp.date()), probability=p, complete_seconds=total))
            for h in (2, 5):
                speeds = transform.inverse(paths[:, h]).mean(axis=0); good = data['future_mask'][i, h]
                trajectory.append(dict(split='validation', origin=int(o), model='location_repair', step=h+1,
                                      mae_raw=float(np.abs(speeds-data['future'][i, h])[good].mean())))
        save_json(out/'repair_outer_parameters.json', dict(table=outer_correction.table.tolist(), counts=outer_correction.counts.tolist()))
    for _, r in orig.iterrows():
        outer_rows.append(dict(split='validation', origin=int(r.origin), model='original', N=256,
            label=int(r.label), eligible=bool(r.eligible), current_active=bool(r.current_active), day=r.day, probability=r.probability,
            complete_seconds=r.total_seconds, timing_source='historical Stage 1 GPU'))
    outer_table = pd.DataFrame(outer_rows); outer_metrics = {}; calrecords = {}
    for name, cal in calibration.groupby('model'):
        eligible = cal.eligible; calibrator = LogisticCalibration().fit(cal.probability[eligible], cal.label[eligible])
        take = eligible & ~cal.current_active
        threshold = alarm_threshold(cal.probability[take], cal.label[take])
        threshold_cal = alarm_threshold(calibrator.predict(cal.probability[take]), cal.label[take])
        which = outer_table.model == name; g = outer_table[which]
        q = calibrator.predict(g.probability); outer_table.loc[which, 'calibrated_probability'] = q
        outer_table.loc[which, 'alarm_threshold'] = threshold
        outer_table.loc[which, 'calibrated_alarm_threshold'] = threshold_cal
        ok = g.eligible.to_numpy(); onset = ok & ~g.current_active.to_numpy()
        outer_metrics[name] = dict(raw=score_record(g.label[ok], g.probability[ok], threshold),
            calibrated=score_record(g.label[ok], q[ok], threshold_cal),
            onset_raw=score_record(g.label[onset], g.probability[onset], threshold),
            onset_calibrated=score_record(g.label[onset], q[onset], threshold_cal))
        calrecords[name] = dict(parameters=calibrator.record(), origins=cal.origin.tolist(),
            inner_raw=score_record(cal.label[eligible], cal.probability[eligible]),
            inner_onset_alarm=score_record(cal.label[take], cal.probability[take], threshold))
    outer_table.to_csv(out/'simulator_predictions.csv', index=False)
    df.to_csv(out/'repair_inner_predictions.csv', index=False)
    pd.DataFrame(trajectory).to_csv(out/'repair_trajectory_errors.csv', index=False)
    classifier = pd.read_csv(out/'matched_predictions.csv')
    aa = classifier[(classifier.split == 'validation') & (classifier.model == 'A')].set_index('origin')
    pairs = {}
    for name, group in outer_table.groupby('model'):
        g = group[group.eligible]; a = aa.loc[g.origin]
        for kind in ('probability', 'calibrated_probability'):
            for block in (1, 3):
                pairs[f'{name}_{kind}_versus_A_block{block}'] = paired_uncertainty(g.label, a.probability, g[kind], g.day, block)
    save_json(out/'simulator_pairs.json', pairs)
    save_json(out/'repair_results.json', dict(repair_accepted_on_inner=accepted, repairs_attempted=1,
        repair='current-severity conditional residual location', inner_metrics=metrics, inner_mae=mae,
        outer_metrics=outer_metrics, calibration=calrecords, cpu_seconds=time.perf_counter()-start, gpu_seconds=0,
        raw_sha256=sha256(config['raw_file']), config_sha256=sha256('configs/stage2_residual_repair.yaml'),
        test_access=False, more_repairs_scheduled=False))
    print({name:{kind:m[kind]['brier'] for kind in ('raw','calibrated')} for name,m in outer_metrics.items()})


if __name__ == '__main__':
    config = yaml.safe_load(Path('configs/stage2_diagnosis.yaml').read_text())
    with threadpool_limits(config['cpu_threads']): main(config)
