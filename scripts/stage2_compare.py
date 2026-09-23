"""CPU-only saved comparison audit and frozen matched information classifier."""
import datetime
import json
import resource
import time
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from traffic_risk_twins.ingestion import PemsSource, label_origins
from traffic_risk_twins.observation_quality import valid_mask, SpeedTransform
from traffic_risk_twins.graph_dynamics import calendar_features
from traffic_risk_twins.stage2_protocol import (inner_windows, matched_features, payload_bytes,
    LogisticCalibration, alarm_threshold, score_record, paired_uncertainty)
from traffic_risk_twins.data_access import save_json, sha256


def main(config):
    start = time.perf_counter()
    output = Path(config['output_directory']); output.mkdir(parents=True, exist_ok=True)
    if (output/'matched_predictions.csv').exists():
        raise FileExistsError('Preserve completed Stage 2 comparisons; choose a new output directory')
    data = np.load(config['input_archive'])
    source = PemsSource(config['raw_file'])
    raw = source.read('train'); mask = valid_mask(raw)
    state = SpeedTransform(data['free']).forward(raw, mask)
    outer = source.splits['train']
    origins = outer['origins'][::config['training_origin_stride']]
    labels = label_origins(state, mask, origins, int(data['threshold']))
    inner = inner_windows(source.timestamps, outer['rows'], origins, outer['days'])
    C = calendar_features(source.timestamps)
    hi = origins[:, None]+np.arange(-11, 1)
    roles = {role: np.isin(origins, value['origins']) & labels['eligible'] for role, value in inner.items()}
    calibration = roles['calibration']
    pre_calibration = roles['fit'] | roles['diagnosis']
    metadata = {role: dict(days=d['days'], origins=d['origins'].tolist(), n=int(roles[role].sum()),
                          positives=int(labels['low'][roles[role]].sum())) for role, d in inner.items()}
    save_json('manifests/stage2/inner_protocol.json', metadata)
    outer_metadata = pd.DataFrame(dict(origin=data['origins'], day=pd.to_datetime(data['timestamps']).strftime('%Y-%m-%d'),
        label=data['labels'].astype(int), eligible=data['label_eligible'], current_active=data['current_active']))
    ok = outer_metadata.eligible.to_numpy()
    onset = ok & ~outer_metadata.current_active.to_numpy()
    y = outer_metadata.label.to_numpy()
    days = outer_metadata.day.to_numpy()
    # Existing saved predictions, no new labels; join and check exact origins.
    saved = pd.read_csv('results/stage1_pilot/predictions.csv')
    original = pd.read_csv('results/tables/baseline_predictions.csv')
    audit, audit_rows = {}, []
    baseline_a = original[original.model == 'heterogeneity'].set_index('origin').loc[data['origins']].probability.to_numpy()
    for model, group in original.groupby('model'):
        p = group.set_index('origin').loc[data['origins']].probability.to_numpy()
        audit[model] = {'all_time': score_record(y[ok], p[ok]), 'onset': score_record(y[onset], p[onset])}
    full_train_labels = label_origins(state, mask, outer['origins'], int(data['threshold']))
    constant = float(full_train_labels['low'][full_train_labels['eligible']].mean())
    audit['constant_training_prevalence'] = dict(value=constant, all_time=score_record(y[ok], np.full(ok.sum(), constant)),
                                                onset=score_record(y[onset], np.full(onset.sum(), constant)))
    for (retention, N), group in saved[saved.method == 'fine_mc'].groupby(['retention', 'N']):
        g = group.set_index('origin').loc[data['origins']]
        assert np.array_equal(g.label.to_numpy(), y) and np.array_equal(g.eligible.to_numpy(), ok)
        assert np.array_equal(g.current_active.to_numpy(), outer_metadata.current_active.to_numpy())
        assert np.allclose(g.probability*g.N, g.events)
        p = g.probability.to_numpy(); sample_n = g.N.to_numpy()
        gap = float(np.mean((p[ok]-y[ok])**2)-np.mean((baseline_a[ok]-y[ok])**2))
        record = dict(retention=float(retention), N=int(N), n=int(ok.sum()),
                      expected_mc_bound=float(np.mean(1/(4*sample_n[ok]))),
                      estimated_mc_variance=float(np.mean(p[ok]*(1-p[ok])/(sample_n[ok]-1))),
                      observed_brier_gap=gap, bound_fraction_of_gap=float(np.mean(1/(4*sample_n[ok]))/gap))
        audit_rows.append(record)
        audit[f'fine_{retention}_{N}'] = dict(all_time=score_record(y[ok], p[ok]), onset=score_record(y[onset], p[onset]))
    pd.DataFrame(audit_rows).to_csv(output/'mc_contribution.csv', index=False)
    save_json(output/'comparison_audit.json', dict(metrics=audit, equal_origins=True, equal_labels=True,
        equal_eligibility=True, equal_weights=True, weights='one per eligible origin', source_test_access=False,
        horizon_frames=6, sustained_frames=3, threshold_count=int(data['threshold']),
        old_calibration='Stage 1 coefficients were descriptive diagnostics; probabilities were not calibrated',
        old_alarm='Stage 1 validation-selected alarm performance is optimistic; excluded from frozen Stage 2 alarms',
        training_origins=len(origins), outer_train_prevalence=constant))
    predictions = []; metrics = {}; pairs = {}; timings = []; resources = {}
    for fraction, name in ((0., 'A'), (.15, 'B'), (1., 'C')):
        selected = data['ordering'][:int(np.ceil(fraction*len(data['W'])))]
        before = time.perf_counter()
        X = matched_features(state[hi], mask[hi], data['blocks'], C[origins], selected)
        Xouter = matched_features(data['history'], data['history_mask'], data['blocks'], data['calendar'], selected)
        feature_seconds = time.perf_counter()-before
        setting = dict(config['shared_settings'][0], random_state=config['seed'])
        model = HistGradientBoostingClassifier(**setting)
        before = time.perf_counter()
        model.fit(X[pre_calibration], labels['low'][pre_calibration])
        inner_p = model.predict_proba(X[calibration])[:, 1]
        inner_seconds = time.perf_counter()-before
        calibrator = LogisticCalibration().fit(inner_p, labels['low'][calibration])
        inner_cal = calibrator.predict(inner_p)
        inner_onset = ~labels['current_active'][calibration]
        threshold_raw = alarm_threshold(inner_p[inner_onset], labels['low'][calibration][inner_onset])
        threshold_cal = alarm_threshold(inner_cal[inner_onset], labels['low'][calibration][inner_onset])
        before = time.perf_counter()
        model.fit(X[labels['eligible']], labels['low'][labels['eligible']])
        fit_seconds = time.perf_counter()-before
        before = time.perf_counter(); p = model.predict_proba(Xouter)[:, 1]
        prediction_seconds = time.perf_counter()-before
        if name == 'A':
            difference = float(np.max(np.abs(p-baseline_a)))
            assert difference < 1e-12, ('A no longer reproduces Stage 1', difference)
            save_json(output/'baseline_reproduction.json', dict(maximum_probability_difference=difference,
                      identical_features_at_zero=True, original_prediction_sha256=sha256('results/tables/baseline_predictions.csv')))
        q = calibrator.predict(p)
        metrics[name] = dict(calibration=calibrator.record(),
            inner_raw=score_record(labels['low'][calibration], inner_p),
            inner_calibrated=score_record(labels['low'][calibration], inner_cal),
            inner_onset_raw=score_record(labels['low'][calibration][inner_onset], inner_p[inner_onset], threshold_raw),
            outer_raw=score_record(y[ok], p[ok], threshold_raw), outer_calibrated=score_record(y[ok], q[ok], threshold_cal),
            outer_onset_raw=score_record(y[onset], p[onset], threshold_raw),
            outer_onset_calibrated=score_record(y[onset], q[onset], threshold_cal))
        resources[name] = dict(fraction=fraction, features=X.shape[1], **payload_bytes(12, len(data['W']), 16, len(selected)))
        timings.append(dict(model=name, feature_seconds=feature_seconds, inner_fit_predict_seconds=inner_seconds,
                            final_fit_seconds=fit_seconds, batch_128_prediction_seconds=prediction_seconds))
        for frame, ids, pp, qq, yy, eligible, active, dd in [
            ('validation', data['origins'], p, q, y, ok, data['current_active'], days),
            ('inner_calibration', origins[calibration], inner_p, inner_cal, labels['low'][calibration],
             np.ones(calibration.sum(), bool), labels['current_active'][calibration], source.timestamps[origins[calibration]].strftime('%Y-%m-%d'))]:
            for row in zip(ids, pp, qq, yy, eligible, active, dd):
                o, pr, pc, label, eligible_row, active_row, day = row
                predictions.append(dict(split=frame, origin=int(o), model=name, day=day, probability=float(pr),
                    calibrated_probability=float(pc), label=int(label), eligible=bool(eligible_row), current_active=bool(active_row),
                    alarm_threshold=threshold_raw, calibrated_alarm_threshold=threshold_cal))
        print(name, 'raw Brier', metrics[name]['outer_raw']['brier'], 'elapsed', time.perf_counter()-start, flush=True)
    table = pd.DataFrame(predictions)
    table.to_csv(output/'matched_predictions.csv', index=False)
    vv = table[table.split == 'validation']
    for name in ('B', 'C'):
        for column in ('probability', 'calibrated_probability'):
            a = vv[vv.model == 'A'].set_index('origin').loc[data['origins'], column].to_numpy()
            b = vv[vv.model == name].set_index('origin').loc[data['origins'], column].to_numpy()
            for length in config['bootstrap_block_days']:
                for subset, take in [('all_time', ok), ('onset', onset)]:
                    pairs[f'{name}_minus_A_{column}_{subset}_block{length}'] = paired_uncertainty(y[take], a[take], b[take], days[take], length)
    save_json(output/'matched_metrics.json', metrics)
    save_json(output/'matched_pairs.json', pairs)
    save_json(output/'information_cost.json', resources)
    pd.DataFrame(timings).to_csv(output/'classifier_timings.csv', index=False)
    save_json(output/'classifier_run.json', dict(complete=True, cpu_seconds=time.perf_counter()-start,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024, gpu_seconds=0,
        raw_sha256=sha256(config['raw_file']), inputs_sha256=sha256(config['input_archive']),
        config_sha256=sha256('configs/stage2_diagnosis.yaml'), test_measurements_read=False,
        executed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))


if __name__ == '__main__':
    config = yaml.safe_load(Path('configs/stage2_diagnosis.yaml').read_text())
    with threadpool_limits(config['cpu_threads']): main(config)
