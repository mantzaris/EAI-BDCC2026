"""Verify delivered scientific artifacts without loading measurements or fitting."""
import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
import yaml
from traffic_risk_twins.compute_ledger import charged_seconds
from traffic_risk_twins.data_access import save_json


def main():
    root = Path.cwd(); out = root/'results/stage2'
    def read(name):
        return json.loads((out/name).read_text())
    def table(name):
        return pd.read_csv(out/name, float_precision='round_trip')
    checks = []
    starting = json.loads(Path('manifests/stage2/starting_state.json').read_text())
    for path, digest in starting['stage1_files'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    checks.append('All 89 protected Stage 1 artifacts unchanged')
    cfg = yaml.safe_load(Path('configs/stage2_diagnosis.yaml').read_text())
    assert cfg['max_gpu_seconds'] == 1800 and not cfg['selective_refinement_enabled']
    assert cfg['forecasting_path'] == 'fine_mc' and not cfg['stage3_enabled']
    assert cfg['test_outcomes_access'] == 'forbidden'
    assert len(cfg['shared_settings']) == 1
    checks.append('Frozen scope, one shared setting, fine default and budget')

    panel = table('validation_panel.csv').set_index('origin').sort_index()
    assert len(panel) == 128 and panel.eligible.sum() == 127
    assert panel.loc[panel.eligible, 'label'].sum() == 20
    assert (panel.eligible & ~panel.current_active).sum() == 110
    classifier = table('matched_predictions.csv')
    outer = classifier[classifier.split == 'validation']
    simulator = table('simulator_predictions.csv')
    assert set(classifier.split) == {'validation', 'inner_calibration'}
    assert set(simulator.split) == {'validation'}
    assert (simulator.N == 256).all()
    assert np.array_equal(simulator.probability*simulator.N,
                          np.rint(simulator.probability*simulator.N))
    cm = read('matched_metrics.json'); sm = read('repair_results.json')['outer_metrics']
    for family, frame, metrics in [('classifier', outer, cm), ('simulator', simulator, sm)]:
        for name, group in frame.groupby('model'):
            g = group.set_index('origin').sort_index()
            assert g.index.equals(panel.index) and not g.index.duplicated().any()
            for col in ('label','eligible','current_active','day'):
                assert np.array_equal(g[col], panel[col]), (name, col)
            for onset in (False, True):
                h = g[g.eligible & (~g.current_active if onset else True)]
                for calibrated in (False, True):
                    prob = h['calibrated_probability' if calibrated else 'probability'].to_numpy()
                    key = ('onset_' if onset else '')+('calibrated' if calibrated else 'raw')
                    if family == 'classifier': key = 'outer_'+key
                    reference = metrics[name][key]
                    assert len(h) == reference['n'] and h.label.sum() == reference['positives']
                    assert abs(np.mean((prob-h.label.to_numpy())**2)-reference['brier']) < 1e-14
                    threshold = h['calibrated_alarm_threshold' if calibrated else 'alarm_threshold'].iloc[0]
                    assert threshold == reference['threshold']
                    alarm = prob >= threshold
                    assert int((alarm & (h.label.to_numpy() == 1)).sum()) == reference['tp']
                    assert int((alarm & (h.label.to_numpy() == 0)).sum()) == reference['fp']
    checks.append('Common origins/masks/weights; direct Brier and alarm counts agree with fitted-run records')
    checks.append('Fixed N raw simulator means are integer event counts divided by 256')
    # Independent storage-boundary check: the tie must remain excluded after CSV.
    tied = .03125; cutoff = np.nextafter(tied, np.inf)
    restored = pd.read_csv(io.StringIO('threshold\n'+repr(cutoff)+'\n'), float_precision='round_trip').threshold[0]
    assert restored > tied and restored == cutoff
    checks.append('CSV preserves the strict tie threshold, including the nextafter bit')
    assert read('baseline_reproduction.json')['maximum_probability_difference'] < 1e-14
    gate = read('repair_inner_gate.json')
    assert gate['accepted'] and gate['metrics']['location_repair']['brier'] <= .95*gate['metrics']['original']['brier']
    assert gate['mae_30min']['location_repair'] <= 1.02*gate['mae_30min']['original']
    assert sm['location_repair']['raw']['brier'] > 1.05*cm['A']['outer_raw']['brier']
    assert read('repair_results.json')['repairs_attempted'] == 1
    checks.append('Exact A recovery, passed inner repair gate and failed outer adequacy gate')

    old = table('enclosure_widths.csv').set_index(['origin','retention']).sort_index()
    new = table('tightening_widths.csv').set_index(['origin','retention']).sort_index()
    assert len(old) == 48 and old.index.equals(new.index)
    assert (old.unresolved == 1).all() and (new.unresolved == 1).all()
    assert (new.mean_radius <= old.mean_radius).all()
    assert (new.maximum_violation <= 0).all() and (old.maximum_violation <= 0).all()
    assert read('enclosure_summary.json')['all_coupled_labels_equal']
    assert read('tightening_summary.json')['all_labels_equal']
    for name, method, column in [('enclosure_repeated_timings.csv', 'empirical_selective', 'seconds'),
                                 ('tightening_timings.csv', 'tightened_selective', 'complete_seconds')]:
        times = table(name)
        grouped = times.groupby(['repeat','method'])[column].mean().unstack()
        assert len(grouped) == 5 and (grouped[method] > grouped['fine']).all()
        assert len(times) == 16*5*2
    cost = table('simulator_cost_audit.csv')
    assert len(cost) == 16*5*2 and (cost.N == 256).all()
    assert read('simulator_cost_audit.json')['maximum_saved_probability_difference'] == 0
    checks.append('Enclosure dominance, empirical containment, coupling and five failed paired runtime gates')

    reproduction = json.loads(Path('manifests/stage2/reproduction.json').read_text())
    assert reproduction['complete'] and len(reproduction['jobs']) == 8
    assert all(j['returncode'] == 0 for j in reproduction['jobs'])
    assert max(reproduction['maximum_differences'].values()) == 0
    assert reproduction['gpu_seconds'] == 0 and not reproduction['test_access']
    checks.append('Eight committed-source CPU jobs reproduced predictions and radii exactly')
    for p in ('results/compute_ledger.jsonl', 'results/stage2/compute_ledger.jsonl'):
        rows = [json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()]
        starts = {r['job_id'] for r in rows if r['event'] == 'start'}
        finishes = {r['job_id'] for r in rows if r['event'] == 'finish'}
        assert starts == finishes
        if 'stage2' in p: assert charged_seconds(rows) == 0
        else: assert charged_seconds(rows) == read('compute_summary.json')['cumulative_gpu_job_seconds']
    assert not read('compute_summary.json')['new_gpu_run']
    checks.append('No open GPU reservations; Stage 2 zero and cumulative usage reconciled')
    source = json.loads(Path('manifests/stage2/source_files.json').read_text())
    for path, digest in source['files'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    for report in ('DECISIONS','MODEL_DIAGNOSTICS','ENCLOSURE_DIAGNOSTICS','DATA_AND_NOVELTY','REPORT'):
        assert Path('reports/STAGE2_'+report+'.md').stat().st_size > 1000
    for name in ('paired_predictions','enclosure_width_cost'):
        for suffix in ('pdf','svg','png'): assert (out/'figures'/(name+'.'+suffix)).stat().st_size > 1000
    checks.append('Source hashes, required reports and both figures in all three formats present')
    save_json(out/'delivery_verification.json', dict(passed=True, checks=checks,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_sha=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        raw_data_loaded=False, test_outcomes_access=False, gpu_seconds=0))
    print('Passed',len(checks),'artifact consistency checks; no measurement data loaded.')


if __name__ == '__main__': main()
