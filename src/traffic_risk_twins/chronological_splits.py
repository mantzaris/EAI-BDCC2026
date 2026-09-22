"""Complete-day splits; this module reads timestamps, never outcome values."""
import numpy as np
import pandas as pd


def split_days(timestamps, history=12, horizon=6, embargo_minutes=90):
    index = pd.DatetimeIndex(timestamps)
    if not index.is_monotonic_increasing or index.has_duplicates:
        raise ValueError('Timestamps must be unique and increasing')
    complete, incomplete = [], []
    for day in index.normalize().unique():
        actual = index[index.normalize() == day]
        expected = pd.date_range(day, periods=288, freq='5min')
        (complete if actual.equals(expected) else incomplete).append(day)
    n = len(complete)
    if n < 5:
        raise ValueError('At least five complete days required')
    cuts = (int(n*.6), int(n*.8))
    groups = dict(train=complete[:cuts[0]], validation=complete[cuts[0]:cuts[1]], test=complete[cuts[1]:])
    boundary = [groups['validation'][0], groups['test'][0]]
    embargo = pd.Timedelta(minutes=embargo_minutes)
    result = {}
    for name, days in groups.items():
        allowed = np.asarray(index.normalize().isin(days))
        for b in boundary:
            allowed &= np.asarray((index < b-embargo) | (index >= b+embargo))
        # Every frame of history and outcome must be eligible and consecutive.
        starts = np.arange(history-1, len(index)-horizon)
        good = np.ones(len(starts), dtype=bool)
        for offset in range(-history+1, horizon+1):
            good &= allowed[starts+offset]
            good &= (index[starts+offset]-index[starts]).asi8 == offset*300_000_000_000
        result[name] = dict(days=[str(d.date()) for d in days], rows=np.flatnonzero(allowed), origins=starts[good])
    result['excluded_incomplete_days'] = [str(d.date()) for d in incomplete]
    return result


def development_guard(split):
    if split not in ('train', 'validation'):
        raise ValueError('Stage 1 cannot read or score test measurements')


def uniform_origins(origins, maximum):
    origins = np.asarray(origins, dtype=int)
    return origins[np.unique(np.linspace(0, len(origins)-1, min(maximum, len(origins)), dtype=int))]
