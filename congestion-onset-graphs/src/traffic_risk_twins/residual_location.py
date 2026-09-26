"""One small residual repair; complete multivariate sequences stay coupled."""
from dataclasses import dataclass
import numpy as np


@dataclass
class ResidualLocation:
    table: np.ndarray
    counts: np.ndarray

    @classmethod
    def fit(cls, bank, origin_states, regimes, minimum=100):
        bank, regimes = np.asarray(bank), np.asarray(regimes, int)
        groups = np.asarray(origin_states) >= 0
        table = np.empty((6, 2, bank.shape[1])); counts = np.zeros((6, 2), int)
        overall = bank.mean(axis=(0, 2))
        for regime in range(6):
            take = regimes == regime
            pooled = bank[take].mean(axis=(0, 2)) if take.any() else overall
            for group in range(2):
                mask = groups[take] == group
                counts[regime, group] = mask.sum()
                table[regime, group] = bank[take].transpose(0, 2, 1)[mask].mean(axis=0) if mask.sum() >= minimum else pooled
        return cls(table, counts)

    def location(self, initial_states, regimes):
        x = np.atleast_2d(initial_states)
        regimes = np.broadcast_to(np.asarray(regimes, int), (len(x),))
        values = self.table[regimes[:, None], (x >= 0).astype(int)]
        return values.transpose(0, 2, 1)

    def centered_bank(self, bank, origin_states, regimes):
        return np.asarray(bank)-self.location(origin_states, regimes)
