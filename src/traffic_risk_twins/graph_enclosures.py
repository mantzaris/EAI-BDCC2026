"""Exact-arithmetic formula; floating computations are explicitly EMPIRICAL.

No arbitrary epsilon is presented as a numerical proof. Certified mode must
refine every sample until a validated rounding enclosure is implemented.
"""
from dataclasses import dataclass
import numpy as np
from .graph_dynamics import rollout
from .event_functionals import event


@dataclass
class Partition:
    labels: np.ndarray
    quotient: np.ndarray
    defect: np.ndarray
    sizes: np.ndarray

    @classmethod
    def build(cls, W, labels):
        W, labels = np.asarray(W, float), np.asarray(labels, int)
        if not np.isfinite(W).all() or np.any(W < 0) or not np.allclose(W.sum(axis=1), 1):
            raise ValueError('Nonnegative row-stochastic W required')
        k = int(labels.max())+1
        if not np.array_equal(np.unique(labels), np.arange(k)):
            raise ValueError('Partition must have consecutive nonempty blocks')
        block_weights = np.stack([W[:, labels == b].sum(axis=1) for b in range(k)], axis=1)
        quotient = np.stack([block_weights[labels == a].mean(axis=0) for a in range(k)])
        defect = np.stack([np.abs(block_weights[labels == a]-quotient[a]).max(axis=0) for a in range(k)])
        return cls(labels, quotient, defect, np.bincount(labels))

    def reduce(self, x):
        means = np.stack([x[..., self.labels == b].mean(axis=-1) for b in range(len(self.sizes))], axis=-1)
        radii = np.stack([np.abs(x[..., self.labels == b]-means[..., b, None]).max(axis=-1) for b in range(len(self.sizes))], axis=-1)
        return means, radii


def enclose(initial, forcing, partition, coefficients, theta=0.):
    z, r = partition.reduce(initial[:, -2:])
    fbar, delta = partition.reduce(forcing)
    zp, zc = z[:, 0], z[:, 1]
    rp, rc = r[:, 0], r[:, 1]
    a0,a1,beta,gamma = coefficients
    centers, radii = [], []
    for h in range(forcing.shape[1]):
        neighbor = zc@partition.quotient.T
        nxt = a0*zc+a1*zp+beta*neighbor+gamma*np.maximum(neighbor-theta,0)+fbar[:, h]
        error = rc@(partition.quotient+partition.defect).T+np.abs(zc)@partition.defect.T
        rn = a0*rc+a1*rp+(beta+gamma)*error+delta[:, h]
        centers.append(nxt); radii.append(rn)
        zp,zc,rp,rc = zc,nxt,rc,rn
    return np.stack(centers,axis=1), np.stack(radii,axis=1)


def labels_from_bounds(center, radius, partition, threshold_count):
    if not np.isfinite(center).all() or not np.isfinite(radius).all():
        raise ArithmeticError('Nonfinite enclosure')
    low = event(center-radius, threshold_count, partition.sizes)
    high = event(center+radius, threshold_count, partition.sizes)
    return low, high


def selective(initial, forcing, W, coefficients, partition, threshold_count, mode='certified'):
    if mode not in ('certified', 'empirical'):
        raise ValueError('Unknown numerical mode')
    center, radius = enclose(initial, forcing, partition, coefficients)
    low, high = labels_from_bounds(center, radius, partition, threshold_count)
    unresolved = low != high
    numerical_fallback = np.ones(len(initial), bool) if mode == 'certified' else np.zeros(len(initial), bool)
    refine = unresolved | numerical_fallback
    labels = low.copy()
    # Exact SAME arrays and indices; no outcome-dependent resampling.
    if refine.any():
        labels[refine] = event(rollout(initial[refine], forcing[refine], W, coefficients), threshold_count)
    return labels, dict(unresolved=unresolved, refined=refine, center=center, radius=radius,
                        numerical_guarantee='fine_floating_reference' if mode == 'certified' else 'empirical_only')
