"""Count comparisons avoid floating-point ambiguity in attainable thresholds."""
import numpy as np


def sustained_count(counts, duration=3):
    counts = np.asarray(counts)
    if counts.shape[-1] < duration:
        raise ValueError('Horizon shorter than sustained duration')
    windows = [counts[..., h:h+duration].min(axis=-1) for h in range(counts.shape[-1]-duration+1)]
    return np.stack(windows, axis=-1).max(axis=-1)


def event(states, threshold_count, weights=None):
    indicator = np.asarray(states) >= 0  # threshold equality IS an event
    counts = indicator.sum(axis=-1) if weights is None else (indicator*np.asarray(weights)).sum(axis=-1)
    return sustained_count(counts) >= threshold_count


def observed_bounds(future, mask, threshold_count):
    low = sustained_count(((future >= 0) & mask).sum(axis=-1)) >= threshold_count
    high = sustained_count(((future >= 0) | ~mask).sum(axis=-1)) >= threshold_count
    coverage = np.asarray(mask).mean(axis=(-2, -1))
    return low, high, (low == high) & (coverage >= .95)


def training_threshold(futures, masks, minimum=.10, split='train'):
    if split != 'train':
        raise ValueError('Event threshold is training-only')
    low = sustained_count(((futures >= 0) & masks).sum(axis=-1))
    high = sustained_count(((futures >= 0) | ~masks).sum(axis=-1))
    eligible = (low == high) & (masks.mean(axis=(-2, -1)) >= .95)
    if not eligible.any():
        raise ValueError('No unambiguous training severities')
    n = futures.shape[-1]
    return int(np.ceil(max(minimum*n, float(np.quantile(low[eligible], .9)))))


def episode_counts(timestamps, positive):
    """Merge positive target-origin runs separated by gaps strictly shorter than 30 min."""
    times = np.asarray(timestamps, dtype='datetime64[ns]')[np.asarray(positive, bool)]
    if not len(times):
        return dict(episodes=0, event_days=0)
    episodes = 1+int(np.sum(np.diff(times) >= np.timedelta64(30, 'm')))
    return dict(episodes=episodes, event_days=len(np.unique(times.astype('datetime64[D]'))))
