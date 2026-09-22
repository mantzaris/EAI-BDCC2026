"""Development-only scores and whole-day uncertainty, separate from MC intervals."""
import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.linear_model import LogisticRegression
from scipy.special import logit
from .chronological_splits import development_guard


def evaluate(y,probability,days,split='validation',seed=20260922):
    development_guard(split)
    y,probability,days = np.asarray(y,int),np.asarray(probability,float),np.asarray(days)
    if not len(y) or not np.isfinite(probability).all() or np.any((probability < 0)|(probability > 1)):
        raise ValueError('Complete probabilities in [0,1] required; clip separately if desired')
    unique = np.unique(days)
    losses = (y-probability)**2
    rng = np.random.default_rng(seed)
    clusters = [np.flatnonzero(days == d) for d in unique]
    bootstrap = [float(losses[np.concatenate([clusters[i] for i in rng.integers(0,len(clusters),len(clusters))])].mean()) for _ in range(1000)]
    result = dict(n=len(y),days=len(unique),positives=int(y.sum()),prevalence=float(y.mean()),
                  brier=float(losses.mean()),brier_day_bootstrap_95=np.quantile(bootstrap,[.025,.975]).tolist(),
                  pr_auc=float(average_precision_score(y,probability)) if y.sum() else None)
    if len(np.unique(y)) == 2:
        fit = LogisticRegression(C=1.,solver='lbfgs').fit(logit(np.clip(probability,1e-5,1-1e-5))[:,None],y)
        result['calibration_intercept'] = float(fit.intercept_[0])
        result['calibration_slope'] = float(fit.coef_[0,0])
    bins = []
    for low, high in zip(np.arange(0,1,.2),np.arange(.2,1.01,.2)):
        take = (probability >= low)&((probability < high) if high < .999 else (probability <= 1))
        if take.any(): bins.append(dict(count=int(take.sum()),mean_probability=float(probability[take].mean()),frequency=float(y[take].mean())))
    result['reliability'] = bins
    return result
