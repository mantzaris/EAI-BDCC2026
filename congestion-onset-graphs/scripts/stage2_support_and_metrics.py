"""Exact development support, paired detection uncertainty, and compact metrics."""
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from traffic_risk_twins.ingestion import PemsSource, label_origins
from traffic_risk_twins.observation_quality import SpeedTransform, valid_mask
from traffic_risk_twins.event_functionals import episode_counts
from traffic_risk_twins.stage2_protocol import inner_windows, paired_uncertainty, LogisticCalibration
from traffic_risk_twins.data_access import save_json


def main():
    start = time.perf_counter(); out = Path('results/stage2')
    if (out/'development_support.json').exists(): raise FileExistsError('Preserve support analysis')
    data = np.load('data/processed/pilot_inputs.npz'); source = PemsSource('data/raw/pems-bay.h5')
    transform = SpeedTransform(data['free']); result = {}; panel_records = []
    for split in ('train', 'validation'):
        raw = source.read(split); mask = valid_mask(raw); state = transform.forward(raw, mask)
        origins = source.splits[split]['origins']; labs = label_origins(state, mask, origins, int(data['threshold']))
        positive = labs['low'] & labs['eligible']
        result[split] = dict(origins=len(origins), eligible=int(labs['eligible'].sum()), positives=int(positive.sum()),
            prevalence=float(positive.sum()/labs['eligible'].sum()), days=len(source.splits[split]['days']),
            **episode_counts(source.timestamps[origins], positive))
        if split == 'train':
            inn = inner_windows(source.timestamps, source.splits['train']['rows'], origins, source.splits['train']['days'])
            result['inner_complete_resolution'] = {}
            for role, item in inn.items():
                keep = np.isin(origins, item['origins']); p = positive[keep]
                result['inner_complete_resolution'][role] = dict(origins=int(keep.sum()), positives=int(p.sum()),
                    first_day=item['days'][0], last_day=item['days'][-1], **episode_counts(source.timestamps[origins[keep]], p))
        else:
            positive_origins = origins[positive]
            groups = np.cumsum(np.r_[True, np.diff(source.timestamps[positive_origins].asi8) >= 30*60*10**9])-1
            mapping = dict(zip(positive_origins.tolist(), groups.tolist()))
            idx = {int(o):j for j,o in enumerate(origins)}
            for i, o in enumerate(data['origins']):
                j = idx[int(o)]
                assert labs['low'][j] == data['labels'][i] and labs['eligible'][j] == data['label_eligible'][i]
                panel_records.append(dict(origin=int(o), day=str(source.timestamps[o].date()), label=int(labs['low'][j]),
                    eligible=bool(labs['eligible'][j]), current_active=bool(labs['current_active'][j]),
                    coverage=float(labs['coverage'][j]), episode_id=mapping.get(int(o), -1)))
    panel = pd.DataFrame(panel_records); panel.to_csv(out/'validation_panel.csv', index=False)
    for name, keep in [('panel', panel.eligible), ('onset_panel', panel.eligible & ~panel.current_active)]:
        g = panel[keep]; positive = g[g.label == 1]
        result[name] = dict(origins=len(g), positives=int(g.label.sum()), prevalence=float(g.label.mean()),
            days=int(g.day.nunique()), event_days=int(positive.day.nunique()), represented_episode_groups=int(positive.episode_id.nunique()))
    result['exposed_validation_days'] = source.splits['validation']['days']
    result['untouched_validation_days'] = []
    result['test_access'] = False
    result['independence_qualification'] = 'Merged positive-target groups are counting units, not statistically proven independent episodes; uncertainty clusters whole days.'
    result['cpu_seconds'] = time.perf_counter()-start
    save_json(out/'development_support.json', result)
    # nextafter thresholds encode strict tie handling; preserve their last bit.
    classifier = pd.read_csv(out/'matched_predictions.csv', float_precision='round_trip')
    simulator = pd.read_csv(out/'simulator_predictions.csv', float_precision='round_trip')
    outer = classifier[classifier.split == 'validation'].copy()
    simulator['model'] = 'simulator_'+simulator.model
    merged = pd.concat([outer, simulator], ignore_index=True)
    compact = []
    for name, group in merged.groupby('model'):
        for kind in ('probability', 'calibrated_probability'):
            for subset, take in [('all_time', group.eligible), ('onset', group.eligible & ~group.current_active)]:
                g = group[take]; p = g[kind].to_numpy(); y = g.label.to_numpy()
                constant = np.full(len(g), result['train']['prevalence'])
                r = paired_uncertainty(y, constant, p, g.day, 1)
                # Difference from a fixed reference retains paired day resampling;
                # individual score CI is generated directly below.
                days = np.unique(g.day); indices = [np.flatnonzero(g.day.to_numpy() == d) for d in days]
                rng = np.random.default_rng(20260923); bs = []
                for _ in range(2000):
                    ii = np.concatenate([indices[j] for j in rng.integers(0, len(days), len(days))])
                    bs.append(np.mean((p[ii]-y[ii])**2))
                from traffic_risk_twins.stage2_protocol import score_record
                threshold_col = 'alarm_threshold' if kind == 'probability' else 'calibrated_alarm_threshold'
                score = score_record(y, p, float(g[threshold_col].iloc[0]))
                compact.append(dict(model=name, probability_kind=kind, subset=subset,
                    **{k:v for k,v in score.items() if k not in ('probability_quantiles','reliability')},
                    brier_low=float(np.quantile(bs,.025)), brier_high=float(np.quantile(bs,.975))))
    pd.DataFrame(compact).to_csv(out/'predictive_metrics.csv', index=False)
    detection = {}
    a = outer[outer.model == 'A'].set_index('origin')
    for name, group in merged.groupby('model'):
        if name == 'A': continue
        g = group[group.eligible & ~group.current_active].sort_values('origin')
        aa = a.loc[g.origin]; y = g.label.to_numpy(); p = g.probability.to_numpy()
        alarma = aa.probability.to_numpy() >= aa.alarm_threshold.to_numpy()
        alarmb = p >= g.alarm_threshold.to_numpy()
        days = g.day.to_numpy(); unique = np.unique(days); clusters = [np.flatnonzero(days == d) for d in unique]
        rng = np.random.default_rng(20260923); differences = []
        for _ in range(2000):
            ii = np.concatenate([clusters[j] for j in rng.integers(0,len(unique),len(unique))]); pos = ii[y[ii] == 1]
            if len(pos): differences.append(float(alarmb[pos].mean()-alarma[pos].mean()))
        detection[name] = dict(positives=int(y.sum()), recall_difference=float(alarmb[y == 1].mean()-alarma[y == 1].mean()),
            recall_difference_day_95=np.quantile(differences,[.025,.975]).tolist(),
            bootstrap_draws_without_positive_events=2000-len(differences))
    save_json(out/'paired_detection.json', detection)
    # Recheck the pandas-to-NumPy compatibility fix against saved calibration.
    maxima = []
    for name, group in classifier[classifier.split == 'inner_calibration'].groupby('model'):
        cal = LogisticCalibration().fit(group.probability, group.label)
        g = outer[outer.model == name]
        maxima.append(float(np.max(np.abs(cal.predict(g.probability)-g.calibrated_probability))))
    # Round-trip decimal CSV probabilities can change optimizer termination at
    # tiny scale. Verify prediction equivalence, not bit identity of a refit.
    assert max(maxima) < 1e-7
    save_json(out/'calibration_regression.json', dict(maximum_saved_probability_difference=max(maxima),
        numerical_adapter_only=True, test_access=False))


if __name__ == '__main__': main()
