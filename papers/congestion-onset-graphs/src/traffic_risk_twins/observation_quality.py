"""Recorded-speed transforms; unknown indicators remain unknown in labels."""
from dataclasses import dataclass
import numpy as np
from scipy.special import expit, logit
from .chronological_splits import development_guard


def valid_mask(values, zero_convention='unknown'):
    if zero_convention not in ('unknown', 'missing', 'valid'):
        raise ValueError('Explicit zero convention required')
    mask = np.isfinite(values) & (values >= 0)
    if zero_convention != 'valid':
        mask &= values != 0
    return mask


@dataclass
class SpeedTransform:
    free: np.ndarray
    epsilon: float = .001

    @classmethod
    def fit(cls, values, mask, split='train'):
        if split != 'train':
            raise ValueError('Transforms are training-only')
        free = np.nanquantile(np.where(mask, values, np.nan), .85, axis=0)
        if not np.all(np.isfinite(free) & (free > 0)):
            raise ValueError('Sensor lacks valid positive training reference speed')
        return cls(free)

    def forward(self, values, mask):
        state = logit(np.clip(1-values/self.free, self.epsilon, 1-self.epsilon))
        return np.where(mask, state, np.nan)

    def inverse(self, state):
        return self.free*(1-expit(state))
