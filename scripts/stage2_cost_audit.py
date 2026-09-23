"""Complete paired CPU costs and raw MC uncertainty for the repaired simulator."""
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from traffic_risk_twins.ingestion import PemsSource
from traffic_risk_twins.observation_quality import SpeedTransform, valid_mask
from traffic_risk_twins.conditional_history import GaussianHistory
from traffic_risk_twins.residual_location import ResidualLocation
from traffic_risk_twins.scenarios import make_scenarios
from traffic_risk_twins.graph_dynamics import rollout
from traffic_risk_twins.event_functionals import event
from traffic_risk_twins.scenario_estimators import bernoulli_summary
from traffic_risk_twins.data_access import save_json


def main():
    start = time.perf_counter(); out = Path('results/stage2')
    if (out/'simulator_cost_audit.csv').exists(): raise FileExistsError('Preserve cost audit')
    data = np.load('data/processed/pilot_inputs.npz'); data = {k:data[k] for k in data.files}
    params = json.loads((out/'repair_outer_parameters.json').read_text())
    correction = ResidualLocation(np.asarray(params['table']), np.asarray(params['counts']))
    source = PemsSource('data/raw/pems-bay.h5'); raw = source.read('train')
    before = time.perf_counter()
    bank_states = SpeedTransform(data['free']).forward(raw[data['bank_origins']], valid_mask(raw[data['bank_origins']]))
    centered = correction.centered_bank(data['bank'], bank_states, data['bank_regime'])
    preparation = time.perf_counter()-before
    gaussian = GaussianHistory(data['gaussian_mean'], data['U'], data['diagonal'])
    saved = pd.read_csv(out/'simulator_predictions.csv').set_index(['origin','model'])
    rows = []; maxima = 0.
    def pipeline(i, model):
        before = time.perf_counter()
        t = pd.Timestamp(int(data['timestamps'][i])); regime = int(t.dayofweek >= 5)*3+t.hour//8
        candidates = np.flatnonzero(data['bank_regime'] == regime)
        bank = data['bank'] if model == 'original' else centered
        initial, forcing, meta = make_scenarios(gaussian, data['history'][i], data['history_mask'][i], data['blocks'],
            data['ordering'], data['calendar'][i], data['prior_mean'][i], bank, candidates, data['seasonal_forcing'][i],
            256, 20260922, int(data['origins'][i]))
        if model == 'location_repair': forcing += correction.location(initial[:, -1], regime)
        generation = time.perf_counter()-before
        paths = rollout(initial, forcing, data['W'], data['coefficients'])
        summary = bernoulli_summary(event(paths, int(data['threshold'])))
        return summary, time.perf_counter()-before, generation
    before = time.perf_counter()
    pipeline(0, 'original'); pipeline(0, 'location_repair')
    warmup = time.perf_counter()-before
    for repeat in range(5):
        for i in np.unique(np.linspace(0, len(data['origins'])-1, 16, dtype=int)):
            for model in (('original','location_repair') if repeat%2 == 0 else ('location_repair','original')):
                summary, elapsed, generation = pipeline(i, model)
                expected = float(saved.loc[(int(data['origins'][i]),model)].probability)
                maxima = max(maxima, abs(summary['estimate']-expected))
                assert summary['estimate'] == expected
                rows.append(dict(origin=int(data['origins'][i]), repeat=repeat, model=model, N=256,
                    total_seconds=elapsed, preparation_seconds=generation, probability=summary['estimate'],
                    mc_lower=summary['interval'][0], mc_upper=summary['interval'][1]))
    table = pd.DataFrame(rows); table.to_csv(out/'simulator_cost_audit.csv', index=False)
    save_json(out/'simulator_cost_audit.json', dict(cpu_seconds=time.perf_counter()-start, gpu_seconds=0,
        warmup_seconds=warmup, bank_preparation_seconds=preparation, origins=16, repeats=5, N=256,
        maximum_saved_probability_difference=maxima,
        means=table.groupby('model').total_seconds.mean().to_dict(), p95=table.groupby('model').total_seconds.quantile(.95).to_dict(),
        complete_scope='Regime lookup, RNG, retained summaries/masks, exact conditioning, bank gathering, location repair, rollout, labels, binomial interval. Resident transformed inputs and fitted banks; archival IO and bank preparation are job/offline costs.',
        supersedes='The complete_seconds field in simulator_predictions.csv excludes RNG selection for the new repair and is not a complete service cost; use this audit instead.'))


if __name__ == '__main__':
    with threadpool_limits(4): main()
