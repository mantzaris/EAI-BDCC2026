"""Fixed-N estimators; independent levels, common randomness within correction pairs."""
import numpy as np
from scipy.stats import beta


def bernoulli_summary(labels, confidence=.95):
    labels = np.asarray(labels)
    if not len(labels) or not np.isin(labels,[0,1]).all():
        raise ValueError('Complete nonempty binary sample required')
    n, k = len(labels), int(labels.sum())
    alpha = 1-confidence
    lo = 0. if k == 0 else float(beta.ppf(alpha/2,k,n-k+1))
    hi = 1. if k == n else float(beta.ppf(1-alpha/2,k+1,n-k))
    return dict(estimate=k/n,n=n,events=k,interval=[lo,hi],interval_type='Clopper-Pearson two-sided',
                zero_event_one_sided_upper=float(1-alpha**(1/n)) if k == 0 else None)


def two_level(cheap, paired_coarse, paired_fine, cheap_ids=None, correction_ids=None):
    cheap, c, f = map(lambda x: np.asarray(x,dtype=float),(cheap,paired_coarse,paired_fine))
    if min(len(cheap),len(c)) < 2 or len(c) != len(f):
        raise ValueError('Complete paired samples and at least two samples per level required')
    if cheap_ids is not None and correction_ids is not None and set(cheap_ids)&set(correction_ids):
        raise ValueError('Cheap and correction sets must be independent/disjoint')
    if not all(np.isin(x,[0,1]).all() for x in (cheap,c,f)):
        raise ValueError('Binary indicators required')
    difference = f-c
    estimate = float(cheap.mean()+difference.mean())
    variance = float(cheap.var(ddof=1)/len(cheap)+difference.var(ddof=1)/len(c))
    # Hoeffding union bound; widths 1 and 2. Valid even with zero empirical variance.
    radius = np.sqrt(np.log(4/.05)/(2*len(cheap)))+2*np.sqrt(np.log(4/.05)/(2*len(c)))
    return dict(estimate=estimate,clipped_for_scoring=float(np.clip(estimate,0,1)),
                variance_estimate=variance,correction_variance=float(difference.var(ddof=1)),
                interval=[float(estimate-radius),float(estimate+radius)],interval_type='Hoeffding union 95%, untruncated',
                n0=len(cheap),n1=len(c))


def allocate_two_level(variances,costs,budget,minimum=32):
    variances,costs = np.asarray(variances,float),np.asarray(costs,float)
    if np.any(costs <= 0) or np.any(variances < 0) or minimum*costs.sum() > budget:
        raise ValueError('Invalid or insufficient pilot budget')
    # Explicit allocation floor for zero pilot variance, not an uncertainty estimate.
    v = np.maximum(variances,1e-6)
    remaining = budget-minimum*costs.sum()
    counts = minimum+np.floor(remaining*np.sqrt(v/costs)/np.sqrt(v*costs).sum()).astype(int)
    return counts
