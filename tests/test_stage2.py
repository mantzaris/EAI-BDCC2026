import numpy as np
import pandas as pd
from traffic_risk_twins.predictive_baselines import features
from traffic_risk_twins.stage2_protocol import (inner_windows, matched_features,
    alarm_threshold, score_record, paired_uncertainty, payload_bytes)


def test_zero_local_exact_and_hidden_identity_invariance():
    rng = np.random.default_rng(28)
    x = rng.normal(size=(5, 12, 6)); mask = np.ones_like(x, bool)
    blocks = np.repeat(np.arange(2), 3); calendar = np.ones((5, 6))
    np.testing.assert_array_equal(matched_features(x, mask, blocks, calendar, []),
                                  features(x, mask, blocks, calendar, 'heterogeneity'))
    # Swap only two unretained identities within a block; block statistics and
    # selected histories contain exactly the same information after permutation.
    perm = [0, 2, 1, 3, 4, 5]
    np.testing.assert_allclose(matched_features(x, mask, blocks, calendar, [0]),
                              matched_features(x[:, :, perm], mask, blocks, calendar, [0]), atol=1e-14)


def test_masked_hidden_values_do_not_enter_features():
    x = np.ones((3, 12, 6)); mask = np.ones_like(x, bool); mask[:, :, 0] = False
    alternate = x.copy(); alternate[:, :, 0] = 1e50
    blocks = np.repeat(np.arange(2), 3); calendar = np.zeros((3, 6))
    np.testing.assert_array_equal(matched_features(x, mask, blocks, calendar, [0, 2]),
                                  matched_features(alternate, mask, blocks, calendar, [0, 2]))


def test_inner_windows_are_disjoint_with_actual_time_embargo():
    t = pd.date_range('2017-01-01', periods=288*12, freq='5min')
    origins = np.arange(11, len(t)-6)
    result = inner_windows(t, np.arange(len(t)), origins, t.normalize().unique().strftime('%Y-%m-%d'), cuts=(4, 8))
    used = []
    for role in ('fit', 'diagnosis', 'calibration'):
        windows = result[role]['origins'][:, None]+np.arange(-11, 7)
        used.append(set(windows.ravel()))
        for boundary in (pd.Timestamp('2017-01-05'), pd.Timestamp('2017-01-09')):
            assert np.all(np.abs(t[windows.ravel()].asi8-boundary.value) >= 90*60*10**9)
    assert not used[0]&used[1] and not used[1]&used[2] and not used[0]&used[2]


def test_alarm_threshold_respects_ties_without_outer_data():
    p = np.array([.1]*18+[.8]*2+[.9, .7]); y = np.array([0]*20+[1, 1])
    threshold = alarm_threshold(p, y, .05)
    assert .8 < threshold < .9
    assert ((p[y == 0] >= threshold).sum()) == 0
    assert score_record(y, p, threshold)['tp'] == 1


def test_brier_contributions_and_paired_identity():
    y = np.array([0, 1, 1, 0]); p = np.array([.1, .8, .3, .5])
    record = score_record(y, p)
    assert np.isclose(record['event_contribution']+record['nonevent_contribution'], .79/4)
    result = paired_uncertainty(y, p, p, np.array(['a', 'a', 'b', 'b']), repeats=30)
    assert result['difference_95'] == [0., 0.]
    assert result['relative_reduction'] == 0


def test_payload_counts_mask_once_and_monotone_information():
    a, b, c = [payload_bytes(12, 325, 16, k) for k in (0, 49, 325)]
    assert b['total']-a['total'] == 49*(12*8+8)
    assert c['total']-a['total'] == 325*(12*8+8)
    assert a['sensor_values_read'] == b['sensor_values_read'] == c['sensor_values_read'] == 3900
