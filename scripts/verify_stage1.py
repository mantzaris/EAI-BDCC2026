"""Verify delivered artifacts without raw data, GPU use, or test-outcome access."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from traffic_risk_twins.compute_ledger import charged_seconds
from traffic_risk_twins.data_access import save_json


def main():
    source=json.loads(Path('manifests/gpu_source_files.json').read_text())
    for name,digest in source['files'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest,name
    run=json.loads(Path('results/stage1_pilot/run.json').read_text())
    assert run['complete'] and run['completed_origins'] == 128
    assert run['source_sha'] == source['source_sha']
    assert hashlib.sha256(Path('configs/stage1_pilot.yaml').read_bytes()).hexdigest() == run['config_sha256']
    predictions=pd.read_csv('results/stage1_pilot/predictions.csv')
    assert len(predictions) == 2560
    groups=predictions.groupby(['method','retention','N'])
    assert len(groups) == 20 and (groups.size() == 128).all()
    fine=predictions[predictions.method == 'fine_mc'].sort_values(['origin','retention','N'])
    assert np.allclose(fine.probability*fine.N,fine.events,rtol=0,atol=1e-10)
    for method in ('empirical_selective','certified_fallback'):
        other=predictions[predictions.method == method].sort_values(['origin','retention','N'])
        assert np.array_equal(fine.probability.to_numpy(),other.probability.to_numpy())
    assert predictions.groupby('origin').label.nunique().max() == 1
    assert predictions.groupby('origin').eligible.nunique().max() == 1
    enclosure=pd.read_csv('results/stage1_pilot/enclosures.csv')
    assert len(enclosure) == 768 and enclosure.maximum_enclosure_violation.max() <= 1e-10
    assert enclosure.unresolved_fraction.eq(1).all()
    allocation=pd.read_csv('results/stage1_pilot/allocations.csv')
    assert len(allocation) == 256
    assert ((allocation.n0 >= 32)&(allocation.n1 >= 32)).all()
    assert (allocation.allocation_stream != allocation.cheap_stream).all()
    assert (allocation.cheap_stream != allocation.correction_stream).all()
    cpu=json.loads(Path('results/cpu_reference.json').read_text())
    assert cpu['scenario_hashes_match'] and cpu['event_disagreements'] == 0
    rows=[json.loads(s) for s in Path('results/compute_ledger.jsonl').read_text().splitlines()]
    started={r['job_id'] for r in rows if r['event'] == 'start'}
    finished={r['job_id'] for r in rows if r['event'] == 'finish'}
    assert started == finished and charged_seconds(rows) < 7200
    assert all(r['returncode'] == 0 for r in rows if r['event'] == 'finish')
    for name in ('information_prediction','enclosure_cost'):
        for extension in ('pdf','svg','png'):
            assert Path(f'results/figures/{name}.{extension}').stat().st_size > 1000
    assert not Path('results/stage2_confirmation').exists()
    assert not Path('data/processed/stage2_frozen_inputs.npz').exists()
    save_json('results/delivery_verification.json',dict(gpu_source_sha=source['source_sha'],source_files_checked=len(source['files']),
        completed_origins=128,prediction_rows=len(predictions),enclosure_rows=len(enclosure),all_assertions_passed=True,
        charged_gpu_seconds=charged_seconds(rows),open_reservations=0,stage2_executed=False,
        verification_scope='Artifact consistency plus existing mathematical/CPU/GPU audit results; no new GPU work.'))
    print('Stage 1 artifact verification passed.')


if __name__ == '__main__': main()
