"""Fixed selectors and disjoint exact constraints for block summaries plus locals."""
from dataclasses import dataclass
import numpy as np
from scipy import sparse


def spatial_partition(coordinates, blocks=16):
    """Balanced deterministic recursive coordinate splits; no outcome access."""
    groups = [np.arange(len(coordinates))]
    while len(groups) < min(blocks, len(coordinates)):
        eligible = [i for i, g in enumerate(groups) if len(g) > 1]
        j = max(eligible, key=lambda i: len(groups[i]))
        g = groups.pop(j)
        axis = np.argmax(np.ptp(coordinates[g], axis=0))
        order = g[np.argsort(coordinates[g, axis], kind='stable')]
        mid = len(g)//2
        groups.extend((order[:mid], order[mid:]))
    labels = np.empty(len(coordinates), int)
    for j, g in enumerate(sorted(groups, key=lambda g: int(g.min()))):
        labels[g] = j
    return labels


def fixed_selector(training_state, blocks, W, coefficients, split='train'):
    if split != 'train':
        raise ValueError('Sensor selection is training-only')
    a0, a1, beta, gamma = coefficients
    G = (a0+a1)*np.eye(len(W))+(beta+gamma)*W
    influence = np.ones(len(W))
    power = np.eye(len(W))
    for _ in range(6):
        power = power@G
        influence += power.sum(axis=0)
    uncertainty = np.nanstd(training_state, axis=0)
    near = np.nanmean(np.abs(training_state) <= 1, axis=0)
    score = uncertainty*influence*(.01+near)
    rank = np.lexsort((np.arange(len(W)), -score))
    # First take each block's best sensor, ordered by score; fractions are nested.
    champions = [next(i for i in rank if blocks[i] == b) for b in np.unique(blocks)]
    champions.sort(key=lambda i: (-score[i], i))
    return np.asarray(champions+[i for i in rank if i not in champions], int), score


@dataclass
class Retained:
    means: np.ndarray
    counts: np.ndarray
    mask: np.ndarray
    selected: np.ndarray
    local_values: np.ndarray
    calendar: np.ndarray
    sensor_reads: int

    @property
    def payload_bytes(self):
        return sum(a.nbytes for a in (self.means, self.counts, self.mask, self.selected, self.local_values, self.calendar))


def retain(history, mask, blocks, selected, calendar):
    history, mask = np.asarray(history), np.asarray(mask, bool)
    means, counts = [], []
    for b in np.unique(blocks):
        valid = mask[:, blocks == b]
        counts.append(valid.sum(axis=1))
        sums = np.where(valid, history[:, blocks == b], 0).sum(axis=1)
        means.append(sums/np.maximum(1, counts[-1]))
    return Retained(np.stack(means, axis=1), np.stack(counts, axis=1), mask.copy(),
                    np.asarray(selected, int), np.where(mask[:, selected], history[:, selected], 0),
                    np.asarray(calendar), history.size)


def independent_constraints(retained, blocks):
    """Eliminate selected coordinates from sums; remaining row supports are disjoint.

    Dropping a fully retained block mean is exact row redundancy elimination.
    Unselected sensor VALUES cannot be passed to this function.
    """
    L, n = retained.mask.shape
    rows, cols, weights, rhs = [], [], [], []
    selected = set(retained.selected.tolist())
    for t in range(L):
        known = {}
        for j, sensor in enumerate(retained.selected):
            if retained.mask[t, sensor]:
                known[sensor] = retained.local_values[t, j]
                row = len(rhs)
                rows.append(row); cols.append(t*n+sensor); weights.append(1.)
                rhs.append(known[sensor])
        for b in np.unique(blocks):
            valid = np.flatnonzero((blocks == b) & retained.mask[t])
            hidden = [i for i in valid if i not in selected]
            total = retained.means[t, b]*retained.counts[t, b]-sum(known.get(i, 0.) for i in valid)
            if hidden:
                row = len(rhs)
                rows.extend([row]*len(hidden)); cols.extend(t*n+np.asarray(hidden)); weights.extend([1/len(hidden)]*len(hidden))
                rhs.append(total/len(hidden))
            elif abs(total) > 1e-9*max(1., abs(retained.means[t, b]*retained.counts[t, b])):
                raise ValueError('Inconsistent redundant aggregate constraint')
    A = sparse.csr_matrix((weights, (rows, cols)), shape=(len(rhs), L*n))
    return A, np.asarray(rhs)
