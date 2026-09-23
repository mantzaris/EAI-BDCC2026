"""Evaluate the single predeclared enclosure tightening; never enable by default."""
import time
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from threadpoolctl import threadpool_limits
from traffic_risk_twins.conditional_history import GaussianHistory
from traffic_risk_twins.scenarios import make_scenarios
from traffic_risk_twins.graph_enclosures import Partition, enclose, labels_from_bounds
from traffic_risk_twins.graph_dynamics import rollout
from traffic_risk_twins.event_functionals import event, sustained_count
from traffic_risk_twins.scenario_estimators import bernoulli_summary
from traffic_risk_twins.enclosure_diagnostics import JointNodeEnclosure
from traffic_risk_twins.data_access import save_json


def main(config):
    start = time.perf_counter(); out = Path('results/stage2')
    if (out/'tightening_widths.csv').exists(): raise FileExistsError('Preserve tightening results')
    loaded = np.load(config['input_archive']); data = {k:loaded[k] for k in loaded.files}
    gaussian = GaussianHistory(data['gaussian_mean'], data['U'], data['diagonal'])
    W, blocks, coefficients = data['W'], data['blocks'], data['coefficients']; threshold = int(data['threshold'])
    before = time.perf_counter(); partition = Partition.build(W, blocks); tight = JointNodeEnclosure(W, partition)
    setup_seconds = time.perf_counter()-before
    indices = np.unique(np.linspace(0, len(data['origins'])-1, 16, dtype=int))
    def sample(i, fraction):
        t = pd.Timestamp(int(data['timestamps'][i])); regime = int(t.dayofweek >= 5)*3+t.hour//8
        return make_scenarios(gaussian, data['history'][i], data['history_mask'][i], blocks,
            data['ordering'][:int(np.ceil(fraction*len(W)))], data['calendar'][i], data['prior_mean'][i],
            data['bank'], np.flatnonzero(data['bank_regime'] == regime), data['seasonal_forcing'][i],
            256, config['seed'], int(data['origins'][i]))
    widths = []; timings = []; maximum_violation = -np.inf
    for i in indices:
        for fraction in (0., .15, 1.):
            initial, forcing, _ = sample(i, fraction)
            fine = rollout(initial, forcing, W, coefficients)
            center, radius = tight.enclose(initial, forcing, coefficients)
            old_center, old_radius = enclose(initial, forcing, partition, coefficients)
            assert np.allclose(center, old_center, atol=1e-12)
            assert np.all(radius <= old_radius+1e-10)
            violation = float(np.max(np.abs(fine-center[..., blocks])-radius[..., blocks]))
            assert violation <= 1e-10; maximum_violation = max(maximum_violation, violation)
            low, high = labels_from_bounds(center, radius, partition, threshold)
            truth = event(fine, threshold)
            assert np.all(low <= truth) and np.all(truth <= high)
            cminus = sustained_count(((center-radius >= 0)*partition.sizes).sum(axis=-1))
            cplus = sustained_count(((center+radius >= 0)*partition.sizes).sum(axis=-1))
            widths.append(dict(origin=int(data['origins'][i]), retention=fraction, mean_radius=float(radius.mean()),
                final_radius=float(radius[:, -1].mean()), unresolved=float(np.mean(low != high)),
                lower_severity=float(cminus.mean()/len(W)), upper_severity=float(cplus.mean()/len(W)),
                maximum_violation=violation, old_mean_radius=float(old_radius.mean())))
        for repeat in range(5):
            methods = ('fine', 'tightened_selective') if repeat % 2 == 0 else ('tightened_selective', 'fine')
            results = {}
            for method in methods:
                before = time.perf_counter(); initial, forcing, _ = sample(i, .15)
                preparation = time.perf_counter()-before
                if method == 'fine':
                    result = event(rollout(initial, forcing, W, coefficients), threshold)
                else:
                    center, radius = tight.enclose(initial, forcing, coefficients)
                    low, high = labels_from_bounds(center, radius, partition, threshold)
                    ids = np.flatnonzero(low != high); result = low.copy()
                    if len(ids): result[ids] = event(rollout(initial[ids], forcing[ids], W, coefficients), threshold)
                bernoulli_summary(result)
                results[method] = result
                timings.append(dict(origin=int(data['origins'][i]), repeat=repeat, method=method,
                                    complete_seconds=time.perf_counter()-before, preparation_seconds=preparation))
            assert np.array_equal(results['fine'], results['tightened_selective'])
    width = pd.DataFrame(widths); timing = pd.DataFrame(timings)
    width.to_csv(out/'tightening_widths.csv', index=False); timing.to_csv(out/'tightening_timings.csv', index=False)
    summary = timing.groupby(['repeat', 'method']).complete_seconds.mean().unstack()
    summary['relative_saving'] = 1-summary.tightened_selective/summary.fine
    save_json(out/'tightening_summary.json', dict(cpu_seconds=time.perf_counter()-start, gpu_seconds=0,
        construction_seconds=setup_seconds, repeat_timings=summary.reset_index().to_dict(orient='records'),
        width_by_retention=width.groupby('retention').mean().drop(columns='origin').to_dict(orient='index'),
        maximum_violation=maximum_violation, all_labels_equal=True, selective_enabled=False,
        theoretical_tightening='max over nodes of w_i*r + abs(E_i*z)', numerical_guarantee='empirical only',
        radius_row_sum_original=np.sum(partition.quotient+partition.defect, axis=1).tolist(),
        true_block_weight_row_sums=np.sum(tight.weights, axis=1).tolist()))
    print(summary.to_string())


if __name__ == '__main__':
    config = yaml.safe_load(Path('configs/stage2_diagnosis.yaml').read_text())
    with threadpool_limits(config['cpu_threads']): main(config)
