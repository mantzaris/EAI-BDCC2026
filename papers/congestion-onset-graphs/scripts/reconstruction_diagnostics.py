"""CPU-only dependence/consistency audit on the same saved retained inputs."""
import json
from pathlib import Path
import time
import subprocess
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from traffic_risk_twins.conditional_history import GaussianHistory
from traffic_risk_twins.retained_information import retain,independent_constraints
from traffic_risk_twins.scenarios import rng_stream
from traffic_risk_twins.data_access import save_json


def main():
    start=time.perf_counter()
    with np.load('data/processed/pilot_inputs.npz') as loaded:
        a={k:loaded[k] for k in loaded.files}
    n=len(a['W']); model=GaussianHistory(a['gaussian_mean'],a['U'],a['diagonal'])
    rows=[]; maximum_constraint_error=0.
    for fraction in (0.,.15,1.):
        selected=a['ordering'][:int(np.ceil(n*fraction))]
        errors=[]
        for i,origin in enumerate(a['origins']):
            r=retain(a['history'][i],a['history_mask'][i],a['blocks'],selected,a['calendar'][i])
            A,b=independent_constraints(r,a['blocks'])
            samples=model.sample(A,b,1024,rng_stream(20260922,origin,0),mean=a['prior_mean'][i])
            maximum_constraint_error=max(maximum_constraint_error,float(np.max(np.abs(A@samples.T-b[:,None]))))
            error=(samples.mean(axis=0).reshape(12,n)-a['history'][i])[-1]
            error[selected]=np.nan; error[~a['history_mask'][i,-1]]=np.nan
            errors.append(error)
        errors=np.asarray(errors)
        valid=np.isfinite(errors).sum(axis=0) >= 16
        if valid.any():
            corr=pd.DataFrame(errors[:,valid]).corr(min_periods=16).to_numpy()
            offdiag=~np.eye(len(corr),dtype=bool)
            mean_corr=float(np.nanmean(np.abs(corr[offdiag]))) if offdiag.any() else None
            perblock=[]
            for b in np.unique(a['blocks']):
                err=errors[:,a['blocks'] == b]
                perblock.append(dict(block=int(b),rmse=float(np.sqrt(np.nanmean(err**2))) if np.isfinite(err).any() else None,
                                     observed_hidden_errors=int(np.isfinite(err).sum())))
        else:
            mean_corr=None; perblock=[]
        rows.append(dict(retention=fraction,mean_absolute_hidden_error_sensor_correlation=mean_corr,
                         sensors_with_16_valid_hidden_errors=int(valid.sum()),blocks=perblock))
    save_json('results/tables/reconstruction_dependence.json',dict(device='CPU',conditional_samples_per_origin=1024,
        source_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        origin_count=len(a['origins']),maximum_exact_constraint_residual=maximum_constraint_error,
        elapsed_seconds=time.perf_counter()-start,results=rows,
        interpretation='Correlations across validation origins, not independent episodes; full retention has no hidden-sensor error.'))


if __name__ == '__main__':
    with threadpool_limits(4): main()
