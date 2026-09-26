"""Scenario generation from retained inputs only; no future observations accepted."""
import hashlib
import time
import numpy as np
from .retained_information import retain,independent_constraints


def rng_stream(seed,origin,stream):
    return np.random.default_rng(np.random.SeedSequence([seed,int(origin),stream]))


def make_scenarios(model,history,mask,blocks,selected,calendar,prior_mean,
                   bank,bank_candidates,seasonal_forcing,count,seed,origin,stream=0):
    timings={}
    start=time.perf_counter()
    retained=retain(history,mask,blocks,selected,calendar)
    A,values=independent_constraints(retained,blocks)
    model.factor(A)
    timings['conditioning_setup_seconds']=time.perf_counter()-start
    start=time.perf_counter()
    samples=model.sample(A,values,count,rng_stream(seed,origin,stream*2),mean=prior_mean)
    initial=samples.reshape(count,*history.shape)
    timings['sampling_seconds']=time.perf_counter()-start
    start=time.perf_counter()
    indices=rng_stream(seed,origin,stream*2+1).choice(bank_candidates,size=count,replace=True)
    forcing=np.asarray(bank[indices],float)+seasonal_forcing
    timings['residual_gather_seconds']=time.perf_counter()-start
    return initial,forcing,dict(timings=timings,payload_bytes=retained.payload_bytes,
         sensor_values_read=retained.sensor_reads,residual_indices=indices,
         constraints=A,values=values,scenario_id=f'{seed}:{origin}:{stream}:0-{count-1}')
