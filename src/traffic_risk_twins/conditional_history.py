"""Low-rank + strictly positive diagonal Gaussian, exact Matheron conditioning."""
from dataclasses import dataclass, field
import hashlib
import numpy as np
from scipy.linalg import cho_factor, cho_solve, qr
from scipy import sparse
from sklearn.utils.extmath import randomized_svd


def remove_redundant_rows(A, values):
    """Generic small-problem reference. Pilot uses analytic disjoint constraints."""
    A = np.asarray(A, float)
    if not len(A):
        return A, np.asarray(values)
    _, R, piv = qr(A.T, mode='economic', pivoting=True)
    tolerance = np.finfo(float).eps*max(A.shape)*np.max(np.abs(R))
    rank = int(np.sum(np.abs(np.diag(R)) > tolerance))
    keep = piv[:rank]
    reference = np.linalg.lstsq(A[keep], np.asarray(values)[keep], rcond=None)[0]
    if not np.allclose(A@reference, values, rtol=1e-10, atol=1e-10):
        raise ValueError('Inconsistent exact observations')
    return A[keep], np.asarray(values)[keep]


@dataclass
class GaussianHistory:
    mean: np.ndarray
    U: np.ndarray
    diagonal: np.ndarray
    cache: dict = field(default_factory=dict)

    @classmethod
    def fit(cls, histories, rank=16, seed=20260922, split='train'):
        if split != 'train':
            raise ValueError('Gaussian fitting is training-only')
        X = np.asarray(histories, float).reshape(len(histories), -1)
        mean = np.nanmean(X, axis=0)
        if not np.isfinite(mean).all():
            raise ValueError('All-missing training coordinate')
        # Training-mean fill affects fitting only; unavailable observations are never constraints.
        centered = np.where(np.isfinite(X), X-mean, 0.)
        _, s, vt = randomized_svd(centered, n_components=min(rank, min(centered.shape)-1), random_state=seed)
        U = vt.T*(s/np.sqrt(len(X)-1))
        residual = centered.var(axis=0, ddof=1)-(U*U).sum(axis=1)
        # Explicit covariance-model floor; NOT observation noise or a solve ridge.
        diagonal = np.maximum(residual, 1e-6)
        return cls(mean, U, diagonal)

    def __post_init__(self):
        if not np.all(np.isfinite(self.diagonal) & (self.diagonal > 0)):
            raise ValueError('Strictly positive finite diagonal required')

    def factor(self, A):
        A = sparse.csr_matrix(A)
        key = hashlib.sha256(A.indptr.tobytes()+A.indices.tobytes()+A.data.tobytes()).hexdigest()
        if key in self.cache:
            return self.cache[key]
        if np.any(np.diff(A.tocsc().indptr) > 1):
            raise ValueError('Fast solver requires disjoint independent row supports')
        B = A@self.U
        diagonal = np.asarray(A.multiply(A)@self.diagonal).ravel()
        if np.any(diagonal <= 0):
            raise ValueError('Empty or redundant observation row')
        inv = 1/diagonal
        factor = cho_factor(np.eye(self.U.shape[1])+B.T@(inv[:, None]*B))
        item = (A, B, inv, factor)
        if len(self.cache) >= 8:
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = item
        return item

    def correction(self, delta, factor):
        A, B, inv, chol = factor
        v = delta*inv
        lam = v-(cho_solve(chol, (v@B).T).T@B.T)*inv
        return (lam@B)@self.U.T + np.asarray(A.T@lam.T).T*self.diagonal

    def sample(self, A, values, count, rng, mean=None):
        mean = self.mean if mean is None else np.asarray(mean)
        factor = self.factor(A)
        # Independent standard normals; no MCMC and no sensor shuffling.
        noise = rng.standard_normal((count, self.U.shape[1]+len(mean)))
        raw = mean + noise[:, :self.U.shape[1]]@self.U.T
        raw += noise[:, self.U.shape[1]:]*np.sqrt(self.diagonal)
        samples = raw+self.correction(values-np.asarray(A@raw.T).T, factor)
        if len(values) and np.max(np.abs(np.asarray(A@samples.T).T-values)) > 2e-8:
            raise ArithmeticError('Exact conditioning residual exceeded audit tolerance')
        return samples

    def conditional_mean(self, A, values, mean=None):
        mean = self.mean if mean is None else np.asarray(mean)
        return mean+self.correction((values-A@mean)[None, :], self.factor(A))[0]
