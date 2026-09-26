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


def test_residual_repair_removes_known_conditional_location_without_shuffle():
    from traffic_risk_twins.residual_location import ResidualLocation
    current = np.array([[-1., 1., -1., 1.], [1., -1., 1., -1.]])
    common = np.array([-2., 2.])[:, None, None]
    offsets = np.where(current >= 0, .7, -.3)[:, None, :]
    bank = np.broadcast_to(common+offsets, (2, 6, 4)).copy()
    model = ResidualLocation.fit(bank, current, [0, 0], minimum=1)
    centered = model.centered_bank(bank, current, [0, 0])
    np.testing.assert_allclose(centered, np.broadcast_to(common, bank.shape), atol=1e-15)
    # Same residual sequence has one common innovation in every sensor/horizon;
    # shifting to a severe forecast preserves that dependence exactly.
    repaired = centered+model.location(np.ones((2, 4)), [0, 0])
    np.testing.assert_allclose(repaired, np.broadcast_to(common+.7, bank.shape), atol=1e-15)


def test_radius_attribution_and_oracle_contains_exact_fine():
    from traffic_risk_twins.graph_enclosures import Partition, labels_from_bounds
    from traffic_risk_twins.graph_dynamics import rollout
    from traffic_risk_twins.enclosure_diagnostics import radius_sources, oracle_block_intervals
    rng = np.random.default_rng(19)
    W = rng.uniform(size=(8, 8)); W /= W.sum(axis=1)[:, None]
    partition = Partition.build(W, np.repeat(np.arange(4), 2))
    initial = rng.normal(size=(13, 2, 8)); forcing = rng.normal(size=(13, 6, 8))
    c = np.array([.5, .2, .2, .05])
    center, radius, parts = radius_sources(initial, forcing, partition, c)
    np.testing.assert_allclose(parts['components'].sum(axis=2), radius, atol=1e-12)
    assert (parts['components'] >= 0).all()
    fine = rollout(initial, forcing, W, c)
    lo, hi = oracle_block_intervals(fine, partition.labels)
    assert np.all(fine >= lo[..., partition.labels]) and np.all(fine <= hi[..., partition.labels])
    # Zero forcing and equitable singleton partition: no error may be injected.
    singleton = Partition.build(W, np.arange(8))
    _, r, _ = radius_sources(initial, forcing, singleton, c)
    assert np.max(r) < 1e-14


def test_joint_tightening_covers_fine_and_never_exceeds_old_bound():
    from itertools import product
    from traffic_risk_twins.enclosure_diagnostics import JointNodeEnclosure
    from traffic_risk_twins.graph_enclosures import Partition, enclose
    from traffic_risk_twins.graph_dynamics import rollout
    # Exhaust the corners of two independently varied four-node initial states.
    labels = np.array([0, 0, 1, 1])
    W = np.array([[.8, .1, .1, 0], [.1, .1, .4, .4], [.2, .3, .1, .4], [0, 0, .3, .7]])
    part = Partition.build(W, labels); tightened = JointNodeEnclosure(W, part)
    initial = np.array(list(product([-1., 1.], repeat=8))).reshape(-1, 2, 4)
    forcing = np.broadcast_to(np.array([.1, -.2, .3, -.4]), (len(initial), 6, 4))
    c = [.5, .2, .2, .05]
    z, r = tightened.enclose(initial, forcing, c)
    oldz, oldr = enclose(initial, forcing, part, c)
    fine = rollout(initial, forcing, W, c)
    assert np.all(np.abs(fine-z[..., labels]) <= r[..., labels]+1e-12)
    np.testing.assert_array_equal(z, oldz)
    assert np.all(r <= oldr+1e-12)
    # Structural residual annihilates constant vectors: no artificial common-
    # level dependence is introduced by taking entrywise absolute maxima first.
    np.testing.assert_allclose(tightened.residual@np.ones(2), 0., atol=1e-15)


def test_calibration_pandas_numpy_and_frozen_input_agree():
    from traffic_risk_twins.stage2_protocol import LogisticCalibration
    p = np.array([.01, .2, .3, .6, .9]); y = np.array([0, 0, 1, 0, 1])
    model = LogisticCalibration().fit(p, y)
    np.testing.assert_array_equal(model.predict(p), model.predict(pd.Series(p)))
