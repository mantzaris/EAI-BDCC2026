"""CPU coupled width attribution and repeated complete-cost diagnosis."""
import hashlib
import time
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from threadpoolctl import threadpool_limits
from traffic_risk_twins.conditional_history import GaussianHistory
from traffic_risk_twins.scenarios import make_scenarios
from traffic_risk_twins.graph_enclosures import Partition, selective
from traffic_risk_twins.graph_dynamics import rollout
from traffic_risk_twins.event_functionals import event, sustained_count
from traffic_risk_twins.scenario_estimators import bernoulli_summary
from traffic_risk_twins.enclosure_diagnostics import radius_sources, oracle_block_intervals
from traffic_risk_twins.data_access import save_json


def main(config):
    start = time.perf_counter(); out = Path('results/stage2')
    if (out/'enclosure_components.csv').exists(): raise FileExistsError('Preserve enclosure results')
    data = np.load(config['input_archive']); data = {k:data[k] for k in data.files}
    gaussian = GaussianHistory(data['gaussian_mean'], data['U'], data['diagonal'])
    W, blocks, coefficients = data['W'], data['blocks'], data['coefficients']
    partition = Partition.build(W, blocks); threshold = int(data['threshold'])
    indices = np.unique(np.linspace(0, len(data['origins'])-1, config['enclosure_diagnostic_origins'], dtype=int))
    N = config['enclosure_scenarios']; rows = []; components = []; timings = []
    def sample(i, fraction):
        stamp = pd.Timestamp(int(data['timestamps'][i])); regime = int(stamp.dayofweek >= 5)*3+stamp.hour//8
        return make_scenarios(gaussian, data['history'][i], data['history_mask'][i], blocks,
            data['ordering'][:int(np.ceil(fraction*len(W)))], data['calendar'][i], data['prior_mean'][i],
            data['bank'], np.flatnonzero(data['bank_regime'] == regime), data['seasonal_forcing'][i],
            N, config['seed'], int(data['origins'][i]))
    original = pd.read_csv('results/stage1_pilot/predictions.csv')
    max_violation = -np.inf
    for i in indices:
        for fraction in (0., .15, 1.):
            initial, forcing, info = sample(i, fraction)
            fine = rollout(initial, forcing, W, coefficients); fine_event = event(fine, threshold)
            expected = original[(original.origin == data['origins'][i]) & (original.N == N) &
                                (original.retention == fraction) & (original.method == 'fine_mc')].iloc[0]
            assert int(fine_event.sum()) == expected.events
            center, radius, sources = radius_sources(initial, forcing, partition, coefficients)
            low_count = sustained_count(((center-radius >= 0)*partition.sizes).sum(axis=-1))
            high_count = sustained_count(((center+radius >= 0)*partition.sizes).sum(axis=-1))
            lo, hi = oracle_block_intervals(fine, blocks)
            oracle_low = sustained_count(((lo >= 0)*partition.sizes).sum(axis=-1))
            oracle_high = sustained_count(((hi >= 0)*partition.sizes).sum(axis=-1))
            error = np.abs(fine-center[..., blocks])
            violation = float(np.max(error-radius[..., blocks])); max_violation = max(max_violation, violation)
            assert violation <= 1e-10
            origin = int(data['origins'][i])
            rows.append(dict(origin=origin, retention=fraction, N=N, mean_radius=float(radius.mean()),
                mean_center_threshold_distance=float(np.abs(center).mean()), mean_fine_error=float(error.mean()),
                maximum_violation=violation, unresolved=float(np.mean((low_count >= threshold) != (high_count >= threshold))),
                lower_severity=float(low_count.mean()/len(W)), upper_severity=float(high_count.mean()/len(W)),
                oracle_unresolved=float(np.mean((oracle_low >= threshold) != (oracle_high >= threshold))),
                oracle_lower_severity=float(oracle_low.mean()/len(W)), oracle_upper_severity=float(oracle_high.mean()/len(W)),
                oracle_interval_width=float((hi-lo).mean()), mean_interval_width=float(2*radius.mean()),
                scenario_sha256=hashlib.sha256(initial.tobytes()+forcing.tobytes()).hexdigest()))
            for h in range(6):
                component = sources['components'][:, h].mean(axis=(0, 2))
                injection = sources['injections'][:, h].mean(axis=(0, 2))
                components.append(dict(origin=origin, retention=fraction, step=h+1, initial_component=component[0],
                    structural_component=component[1], forcing_component=component[2],
                    structural_injection=injection[1], forcing_injection=injection[2],
                    inherited_radius=float(sources['inherited'][:, h].mean()),
                    initial_radius=float(sources['initial_radius'].mean()), mean_radius=float(radius[:, h].mean()),
                    mean_center_threshold_distance=float(np.abs(center[:, h]).mean()), actual_error=float(error[:, h].mean())))
        # Five paired repetitions at 15%, alternating method order. Each method
        # pays for its own complete preparation, compaction and probability interval.
        for repeat in range(config['enclosure_timing_repeats']):
            labels = {}
            methods = ('fine', 'empirical_selective') if repeat % 2 == 0 else ('empirical_selective', 'fine')
            for method in methods:
                before = time.perf_counter(); initial, forcing, info = sample(i, .15)
                preparation = time.perf_counter()-before
                if method == 'fine':
                    result = event(rollout(initial, forcing, W, coefficients), threshold)
                else:
                    result, _ = selective(initial, forcing, W, coefficients, partition, threshold, mode='empirical')
                bernoulli_summary(result)
                total = time.perf_counter()-before
                labels[method] = result
                timings.append(dict(origin=int(data['origins'][i]), repeat=repeat, method=method,
                                    seconds=total, preparation_seconds=preparation, N=N, retention=.15, device='cpu'))
            assert np.array_equal(labels['fine'], labels['empirical_selective'])
    pd.DataFrame(rows).to_csv(out/'enclosure_widths.csv', index=False)
    pd.DataFrame(components).to_csv(out/'enclosure_components.csv', index=False)
    pd.DataFrame(timings).to_csv(out/'enclosure_repeated_timings.csv', index=False)
    width = pd.DataFrame(rows); timing = pd.DataFrame(timings)
    grouped = timing.groupby(['repeat', 'method']).seconds.mean().unstack()
    grouped['relative_saving'] = 1-grouped.empirical_selective/grouped.fine
    save_json(out/'enclosure_summary.json', dict(cpu_seconds=time.perf_counter()-start, gpu_seconds=0,
        origins=data['origins'][indices].tolist(), N=N, repeats=config['enclosure_timing_repeats'],
        width_by_retention=width.groupby('retention').mean().drop(columns=['origin', 'N']).to_dict(orient='index'),
        repeat_timing=grouped.reset_index().to_dict(orient='records'), maximum_enclosure_violation=max_violation,
        all_coupled_labels_equal=True, oracle='Uses already-evaluated fine trajectory min/max per block; cannot accelerate',
        numerical_qualification='Empirical FP64 only; conservative certified path still always refines',
        test_access=False))
    print(grouped.to_string())


if __name__ == '__main__':
    config = yaml.safe_load(Path('configs/stage2_diagnosis.yaml').read_text())
    with threadpool_limits(config['cpu_threads']): main(config)
