"""Frozen Stage 2 information comparison and chronological development protocol."""
import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from .predictive_baselines import features


def inner_windows(timestamps, train_rows, origins, days, cuts=(54, 81), embargo=90):
    t = pd.DatetimeIndex(timestamps)
    boundaries = [pd.Timestamp(days[i]) for i in cuts]
    outer = np.zeros(len(t), bool)
    outer[train_rows] = True
    groups = np.split(np.asarray(days), cuts)
    result = {}
    for role, group in zip(('fit', 'diagnosis', 'calibration'), groups):
        allowed = outer & t.normalize().isin(pd.DatetimeIndex(group))
        for boundary in boundaries:
            allowed &= (t < boundary-pd.Timedelta(minutes=embargo)) | (t >= boundary+pd.Timedelta(minutes=embargo))
        good = np.ones(len(origins), bool)
        for offset in range(-11, 7):
            ids = np.asarray(origins)+offset
            good &= allowed[ids]
            good &= (t[ids]-t[origins]).asi8 == offset*300_000_000_000
        result[role] = dict(days=group.tolist(), rows=np.flatnonzero(allowed), origins=np.asarray(origins)[good])
    return result


def matched_features(history, mask, blocks, calendar, selected):
    """No selector lives here; selected IDs are an already frozen input.

    A contains all Stage 1 heterogeneity statistics. Selected deviations recover
    their histories from the supplied block means; hidden identities are unused.
    """
    base = features(history, mask, blocks, calendar, 'heterogeneity')
    selected = np.asarray(selected, int)
    if not len(selected):
        return base
    L, k = history.shape[1], len(np.unique(blocks))
    means = base[:, :L*k].reshape(len(history), L, k)
    observed = mask[:, :, selected]
    deviations = np.where(observed, history[:, :, selected]-means[:, :, blocks[selected]], 0.)
    return np.concatenate((base, deviations.reshape(len(history), -1), observed.reshape(len(history), -1)), axis=1)


def payload_bytes(history_frames, sensors, blocks, selected):
    """FP64 summaries/values/calendar, int64 counts/IDs, unpacked uint8 full mask.

    Masks for added locals are already contained in the full mask: do not double
    count a repeated feature representation as extra transmitted information.
    """
    components = dict(means=8*history_frames*blocks, counts=8*history_frames*blocks,
                      heterogeneity=8*history_frames*blocks*4, masks=history_frames*sensors,
                      calendar=8*6, local_values=8*history_frames*selected, sensor_ids=8*selected)
    return dict(components=components, total=sum(components.values()), sensor_values_read=history_frames*sensors)


class LogisticCalibration:
    def fit(self, probability, labels):
        p, y = np.asarray(probability), np.asarray(labels, int)
        self.constant = None
        if len(np.unique(y)) < 2:
            self.constant = (y.sum()+.5)/(len(y)+1)
            self.model = None
        else:
            self.model = LogisticRegression(C=1., solver='lbfgs').fit(logit(np.clip(p, 1e-5, 1-1e-5))[:, None], y)
        return self

    def predict(self, probability):
        probability = np.asarray(probability, float)
        if self.constant is not None:
            return np.full(len(probability), self.constant)
        return self.model.predict_proba(logit(np.clip(probability, 1e-5, 1-1e-5))[:, None])[:, 1]

    def record(self):
        return dict(constant=self.constant, intercept=None if self.model is None else float(self.model.intercept_[0]),
                    slope=None if self.model is None else float(self.model.coef_[0, 0]), family='logistic C=1; clip=1e-5')


def alarm_threshold(probability, labels, target=.05):
    """Smallest threshold satisfying empirical negative-origin FPR, including ties."""
    negative = np.asarray(probability)[np.asarray(labels) == 0]
    if not len(negative):
        raise ValueError('False-alarm threshold needs inner non-events')
    permitted = int(np.floor(target*len(negative)+1e-12))
    descending = np.sort(negative)[::-1]
    return float(np.nextafter(descending[permitted], np.inf))


def score_record(y, p, threshold=None):
    y, p = np.asarray(y, int), np.asarray(p, float)
    if not len(y) or not np.isfinite(p).all() or np.any((p < 0)|(p > 1)):
        raise ValueError('Require complete probability observations')
    loss = (p-y)**2
    result = dict(n=len(y), positives=int(y.sum()), prevalence=float(y.mean()), brier=float(loss.mean()),
                  event_loss=float(loss[y == 1].mean()) if y.sum() else None,
                  nonevent_loss=float(loss[y == 0].mean()) if (y == 0).any() else None,
                  event_contribution=float(loss[y == 1].sum()/len(y)),
                  nonevent_contribution=float(loss[y == 0].sum()/len(y)),
                  pr_auc=float(average_precision_score(y, p)) if y.sum() else None,
                  probability_quantiles=np.quantile(p, [0, .1, .5, .9, .99, 1]).tolist(),
                  mean_probability=float(p.mean()), zero_probabilities=int((p == 0).sum()))
    result['reliability'] = []
    for lo, hi in zip(np.arange(0, 1, .2), np.arange(.2, 1.01, .2)):
        keep = (p >= lo)&((p < hi) if hi < .999 else (p <= 1))
        if keep.any():
            result['reliability'].append(dict(lower=float(lo), upper=float(hi), n=int(keep.sum()),
                probability=float(p[keep].mean()), observed=float(y[keep].mean())))
    if threshold is not None:
        alarm = p >= threshold
        tp, fp = int((alarm & (y == 1)).sum()), int((alarm & (y == 0)).sum())
        result.update(threshold=float(threshold), tp=tp, fp=fp, fn=int(y.sum())-tp, tn=int((y == 0).sum())-fp,
            recall=tp/int(y.sum()) if y.sum() else None, false_alarm_rate=fp/int((y == 0).sum()),
            precision=tp/(tp+fp) if tp+fp else None)
    return result


def paired_uncertainty(y, a, b, days, block_days=1, repeats=2000, seed=20260923):
    """Noncircular moving day blocks; preserve paired forecasts within each day."""
    y, a, b, days = map(np.asarray, (y, a, b, days))
    unique = np.unique(days)
    clusters = [np.flatnonzero(days == d) for d in unique]
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(repeats):
        draws = []
        while len(draws) < len(unique):
            start = int(rng.integers(0, len(unique)-block_days+1))
            draws.extend(range(start, start+block_days))
        ids = np.concatenate([clusters[j] for j in draws[:len(unique)]])
        la, lb = np.mean((a[ids]-y[ids])**2), np.mean((b[ids]-y[ids])**2)
        estimates.append((lb-la, (la-lb)/la if la else np.nan))
    estimates = np.asarray(estimates)
    la, lb = np.mean((a-y)**2), np.mean((b-y)**2)
    return dict(n=len(y), days=len(unique), positives=int(y.sum()), block_days=block_days,
                a_brier=float(la), b_brier=float(lb), difference_b_minus_a=float(lb-la),
                relative_reduction=float((la-lb)/la),
                difference_95=np.quantile(estimates[:, 0], [.025, .975]).tolist(),
                relative_reduction_95=np.nanquantile(estimates[:, 1], [.025, .975]).tolist())
