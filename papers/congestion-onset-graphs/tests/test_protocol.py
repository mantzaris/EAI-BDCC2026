import json
import sys
import numpy as np
import pandas as pd
import pytest
import h5py
from traffic_risk_twins.chronological_splits import split_days, uniform_origins
from traffic_risk_twins.ingestion import PemsSource
from traffic_risk_twins.observation_quality import SpeedTransform
from traffic_risk_twins.retained_information import fixed_selector
from traffic_risk_twins.compute_ledger import charged_seconds,run_budgeted


def test_day_splits_windows_embargo_and_timestamp_gap():
    idx=pd.date_range('2017-01-01',periods=20*288,freq='5min')
    idx=idx.delete(288*2+10)
    splits=split_days(idx)
    assert splits['excluded_incomplete_days'] == ['2017-01-03']
    origin_sets=[]
    for name in ('train','validation','test'):
        rows=set(splits[name]['rows'])
        for o in splits[name]['origins']:
            assert all(i in rows for i in range(o-11,o+7))
            assert idx[o+6]-idx[o-11] == pd.Timedelta(minutes=85)
        origin_sets.append(set(splits[name]['origins']))
    assert not origin_sets[0]&origin_sets[1] and not origin_sets[1]&origin_sets[2]
    for name in ('validation','test'):
        boundary=pd.Timestamp(splits[name]['days'][0])
        for other in ('train','validation','test'):
            rows=splits[other]['rows']
            assert not np.any((idx[rows]>=boundary-pd.Timedelta(minutes=90))&(idx[rows]<boundary+pd.Timedelta(minutes=90)))


def test_hdf_test_measurements_inaccessible(tmp_path):
    path=tmp_path/'source.h5'
    dates=pd.date_range('2017-01-01',periods=10*288,freq='5min')
    values=np.ones((len(dates),2)); values[8*288:]=1e100  # poison test values
    with h5py.File(path,'w') as f:
        f['speed/axis1']=dates.asi8; f['speed/axis0']=[10,20]; f['speed/block0_items']=[10,20]
        f['speed/block0_values']=values
    source=PemsSource(path)
    for name in ('train','validation'):
        loaded=source.read(name)
        assert not np.isfinite(loaded[8*288:]).any()
    with pytest.raises(ValueError): source.read('test')


def test_training_only_selection_and_origin_rule():
    state=np.arange(100*8).reshape(100,8)/100
    blocks=np.repeat([0,1],4)
    ranking,_=fixed_selector(state,blocks,np.eye(8),[.5,.1,.1,.1])
    assert len(set(ranking)) == 8 and set(blocks[ranking[:2]]) == {0,1}
    with pytest.raises(ValueError): fixed_selector(state,blocks,np.eye(8),[.5,.1,.1,.1],split='test')
    with pytest.raises(ValueError): SpeedTransform.fit(state,np.ones_like(state,bool),split='validation')
    origins=np.arange(11,100)
    assert np.array_equal(uniform_origins(origins,3),[11,55,99])


def test_ledger_failed_jobs_and_unfinished_reservations(tmp_path):
    path=tmp_path/'ledger.jsonl'
    code=run_budgeted(path,[sys.executable,'-c','raise SystemExit(2)'],1)
    assert code == 2
    rows=[json.loads(s) for s in path.read_text().splitlines()]
    assert charged_seconds(rows) > 0
    with path.open('a') as out:
        out.write(json.dumps(dict(event='start',job_id='interrupted',reserved_seconds=7199.99))+'\n')
    with pytest.raises(RuntimeError): run_budgeted(path,[sys.executable,'-c','pass'],1)
