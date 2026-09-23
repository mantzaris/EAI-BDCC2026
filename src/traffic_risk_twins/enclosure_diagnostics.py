"""Additive attribution of the existing bound; oracle diagnostics never certify."""
import numpy as np
from .graph_enclosures import enclose


def radius_sources(initial, forcing, partition, coefficients):
    center, radius = enclose(initial, forcing, partition, coefficients)
    z0, r0 = partition.reduce(initial[:, -2:])
    _, delta = partition.reduce(forcing)
    a0, a1, beta, gamma = coefficients
    previous = np.stack((r0[:, 0], np.zeros_like(r0[:, 0]), np.zeros_like(r0[:, 0])), axis=1)
    current = np.stack((r0[:, 1], np.zeros_like(r0[:, 1]), np.zeros_like(r0[:, 1])), axis=1)
    centers = np.concatenate((z0[:, 1:2], center[:, :-1]), axis=1)
    contributions = []; injections = []; propagation = []
    for h in range(forcing.shape[1]):
        inherited = a0*current+a1*previous+(beta+gamma)*(current@(partition.quotient+partition.defect).T)
        added = np.zeros_like(current)
        added[:, 1] = (beta+gamma)*(np.abs(centers[:, h])@partition.defect.T)
        added[:, 2] = delta[:, h]
        nxt = inherited+added
        contributions.append(nxt); injections.append(added); propagation.append(inherited.sum(axis=1))
        previous, current = current, nxt
    components = np.stack(contributions, axis=1)
    if not np.allclose(components.sum(axis=2), radius, atol=1e-11, rtol=1e-12):
        raise ArithmeticError('Additive attribution lost a radius term')
    return center, radius, dict(components=components, injections=np.stack(injections, axis=1),
                               inherited=np.stack(propagation, axis=1), initial_radius=r0)


def oracle_block_intervals(fine, labels):
    """Smallest block rectangles for already-computed fine states; unavailable cheaply."""
    low = np.stack([fine[..., labels == b].min(axis=-1) for b in np.unique(labels)], axis=-1)
    high = np.stack([fine[..., labels == b].max(axis=-1) for b in np.unique(labels)], axis=-1)
    return low, high


class JointNodeEnclosure:
    """One exact-arithmetic tightening, empirical in floating point.

    Keep each node's row weights together before the block maximum; retain
    signed cancellation in E z. The original fine dynamical map is unchanged.
    """
    def __init__(self, W, partition):
        self.partition = partition
        self.weights = np.stack([W[:, partition.labels == b].sum(axis=1) for b in range(len(partition.sizes))], axis=1)
        self.residual = self.weights-partition.quotient[partition.labels]

    def enclose(self, initial, forcing, coefficients):
        part = self.partition
        z, r = part.reduce(initial[:, -2:]); fbar, delta = part.reduce(forcing)
        zp, zc, rp, rc = z[:, 0], z[:, 1], r[:, 0], r[:, 1]
        a0, a1, beta, gamma = coefficients
        centers, radii = [], []
        for h in range(forcing.shape[1]):
            neighbor = zc@part.quotient.T
            nxt = a0*zc+a1*zp+beta*neighbor+gamma*np.maximum(neighbor, 0)+fbar[:, h]
            node_error = rc@self.weights.T+np.abs(zc@self.residual.T)
            error = np.stack([node_error[:, part.labels == b].max(axis=1) for b in range(len(part.sizes))], axis=1)
            rn = a0*rc+a1*rp+(beta+gamma)*error+delta[:, h]
            centers.append(nxt); radii.append(rn)
            zp, zc, rp, rc = zc, nxt, rc, rn
        return np.stack(centers, axis=1), np.stack(radii, axis=1)
