"""The plan's nonnegative, two-lag graph recurrence, NumPy and eager PyTorch."""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize


def calendar_features(timestamps):
    import pandas as pd
    t = pd.DatetimeIndex(timestamps)
    phase = 2*np.pi*(t.hour*60+t.minute)/1440
    return np.stack((np.ones(len(t)), np.sin(phase), np.cos(phase), np.sin(2*phase),
                     np.cos(2*phase), (t.dayofweek >= 5).astype(float)), axis=1)


@dataclass
class Dynamics:
    coefficients: np.ndarray
    seasonal: np.ndarray
    theta: float = 0.

    def __post_init__(self):
        if len(self.coefficients) != 4 or np.any(np.asarray(self.coefficients) < 0):
            raise ValueError('Four nonnegative coefficients required')

    def forcing_mean(self, timestamps):
        return calendar_features(timestamps)@self.seasonal


def fit_dynamics(states, timestamps, W, valid_transition, cap=.98, split='train'):
    if split != 'train' or cap not in (.98, 1.05):
        raise ValueError('Training-only fit; only prespecified stability families')
    ids = np.flatnonzero(valid_transition)
    ids = ids[ids >= 2]
    X = np.asarray(states)
    neighbor = X[ids-1]@W.T
    features = np.stack((X[ids-1], X[ids-2], neighbor, np.maximum(neighbor, 0)), axis=-1)
    C = calendar_features(np.asarray(timestamps)[ids])
    target = X[ids]
    # Eliminate unpenalized seasonal intercepts then solve only four constrained coefficients.
    seasonal_y = np.linalg.lstsq(C, target, rcond=None)[0]
    seasonal_x = np.linalg.lstsq(C, features.reshape(len(ids), -1), rcond=None)[0]
    f = (features-(C@seasonal_x).reshape(features.shape)).reshape(-1, 4)
    y = (target-C@seasonal_y).ravel()
    gram, cross = f.T@f/len(y), f.T@y/len(y)
    result = minimize(lambda c: .5*c@gram@c-cross@c, [.6,.1,.1,.05], jac=lambda c: gram@c-cross,
                      bounds=[(0, cap)]*4, constraints=[dict(type='ineq', fun=lambda c: cap-c.sum(), jac=lambda c: -np.ones(4))],
                      method='SLSQP', options={'ftol':1e-11,'maxiter':200})
    if not result.success:
        raise RuntimeError(result.message)
    coef = np.maximum(result.x, 0)
    seasonal = np.linalg.lstsq(C, target-np.einsum('tnj,j->tn',features,coef), rcond=None)[0]
    return Dynamics(coef, seasonal)


def rollout(initial, forcing, W, coefficients, theta=0.):
    previous, current = initial[:, -2].copy(), initial[:, -1].copy()
    a0, a1, beta, gamma = coefficients
    states = []
    for h in range(forcing.shape[1]):
        neighbor = current@W.T
        nxt = a0*current+a1*previous+beta*neighbor+gamma*np.maximum(neighbor-theta, 0)+forcing[:, h]
        states.append(nxt)
        previous, current = current, nxt
    return np.stack(states, axis=1)


def rollout_torch(initial, forcing, W, coefficients, theta=0.):
    import torch
    previous, current = initial[:, -2], initial[:, -1]
    a0, a1, beta, gamma = coefficients
    states = []
    for h in range(forcing.shape[1]):
        neighbor = current@W.T
        nxt = a0*current+a1*previous+beta*neighbor+gamma*torch.relu(neighbor-theta)+forcing[:, h]
        states.append(nxt)
        previous, current = current, nxt
    return torch.stack(states, dim=1)


def residual_bank(states, timestamps, W, model, origins, horizon=6):
    """Each entry is an intact multivariate H-frame residual sequence."""
    ids = np.arange(2, len(states))
    neighbor = states[ids-1]@W.T
    a0,a1,beta,gamma = model.coefficients
    residual = np.full_like(states, np.nan)
    residual[ids] = states[ids]-(a0*states[ids-1]+a1*states[ids-2]+beta*neighbor+gamma*np.maximum(neighbor-model.theta,0)+model.forcing_mean(np.asarray(timestamps)[ids]))
    return np.stack([residual[o+1:o+horizon+1] for o in origins])
