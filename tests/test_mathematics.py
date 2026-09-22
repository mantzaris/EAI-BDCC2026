from fractions import Fraction as F
from itertools import product
import numpy as np
import pytest
from scipy import sparse
from traffic_risk_twins.cell_transmission import two_cell, step
from traffic_risk_twins.conditional_history import GaussianHistory, remove_redundant_rows
from traffic_risk_twins.retained_information import retain, independent_constraints
from traffic_risk_twins.graph_dynamics import rollout
from traffic_risk_twins.graph_enclosures import Partition, enclose, selective
from traffic_risk_twins.event_functionals import event, observed_bounds
from traffic_risk_twins.scenario_estimators import bernoulli_summary, two_level, allocate_two_level


def test_two_cell_exact_arithmetic_and_external_queue():
    a,qa,ea = two_cell((F(40),F(10)))
    b,qb,eb = two_cell((F(10),F(40)))
    assert a == (30,25) and b == (20,45)
    assert (qa,qb,ea,eb) == (10,0,5,5)
    for x,q,e in [(a,qa,ea),(b,qb,eb)]:
        assert sum(x)+q+e == 50+20
    assert max(a) < 42 <= max(b)


def test_ctm_storage_and_conservation_over_200_steps():
    rng = np.random.default_rng(17)
    n=20
    rho = rng.uniform(5,80,n)
    length=np.full(n,.5); v=np.full(n,60.); w=np.full(n,20.)
    jam=np.full(n,120.); capacity=np.full(n,1800.); capacity[12]=700.
    queue=0.; exited=0.; initial=float(rho@length)
    dt=5/3600; demand=2200.
    for j in range(200):
        rho,queue,out=step(rho,queue,demand,length,v,w,jam,capacity,dt)
        exited += out
        assert rho.min() >= -1e-12 and np.all(rho <= jam+1e-12)
        assert abs(rho@length+queue+exited-initial-(j+1)*demand*dt) < 1e-9
    with pytest.raises(ValueError): step(rho,0,100,length,v,w,jam,capacity,1.)


def test_fraction_reference_boundary_grid():
    # Independent scalar rational recurrence, 243 initial/forcing combinations.
    W=np.array([[.25,.75],[.5,.5]])
    p=Partition.build(W,[0,0]); coef=np.array([.5,.125,.25,.0625])
    for values in product((-1,0,1),repeat=5):
        x=np.array(values[:4],float).reshape(1,2,2)
        f=np.full((1,3,2),values[4]/8)
        rational=[list(map(F,values[:2])),list(map(F,values[2:4]))]
        for h in range(3):
            old,cur=rational[-2:]
            neighbor=[cur[0]/4+3*cur[1]/4,(cur[0]+cur[1])/2]
            rational.append([cur[i]/2+old[i]/8+neighbor[i]/4+max(neighbor[i],0)/16+F(values[4],8) for i in range(2)])
        exact=np.array(rational[2:],float)[None]
        fine=rollout(x,f,W,coef)
        assert np.array_equal(fine,exact)  # dyadic arithmetic is exact here
        z,r=enclose(x,f,p,coef)
        assert np.all(exact >= (z-r)[...,p.labels]-1e-15)
        assert np.all(exact <= (z+r)[...,p.labels]+1e-15)


def test_300_fresh_graph_enclosures_and_defect_counterexample():
    rng=np.random.default_rng(7213)
    for j in range(300):
        W=rng.uniform(size=(12,12))*(rng.uniform(size=(12,12))>.6)+np.eye(12)
        W/=W.sum(axis=1,keepdims=True)
        p=Partition.build(W,np.repeat(np.arange(3),4))
        scale=1e-12 if j%3 == 0 else 3.
        initial=rng.normal(size=(5,2,12))*scale
        forcing=rng.normal(size=(5,6,12))*scale
        coef=rng.dirichlet(np.ones(4))*(1.05 if j%2 else .98)
        fine=rollout(initial,forcing,W,coef)
        z,r=enclose(initial,forcing,p,coef)
        error=np.abs(fine-z[...,p.labels])
        assert np.max(error-r[...,p.labels]) <= 1e-12
        labels,detail=selective(initial,forcing,W,coef,p,4,'empirical')
        assert np.array_equal(labels,event(fine,4))
    W=np.array([[1,0,0,0],[0,0,1,0],[0,0,1,0],[0,0,0,1]],float)
    p=Partition.build(W,[0,0,1,1])
    initial=np.array([[[-2,-2,2,2],[-2,-2,2,2]]],float)
    forcing=np.zeros((1,3,4)); coef=[0,0,1,0]
    fine=rollout(initial,forcing,W,coef)
    p.defect[:]=0  # Deliberately wrong implementation must fail independently.
    z,r=enclose(initial,forcing,p,coef)
    assert np.any(np.abs(fine-z[...,p.labels]) > r[...,p.labels])


def test_equitable_and_singleton_terminal_cases():
    W=np.array([[.4,.1,.2,.3],[.1,.4,.3,.2],[.2,.3,.4,.1],[.3,.2,.1,.4]])
    p=Partition.build(W,[0,0,1,1])
    assert np.all(p.defect == 0)
    singleton=Partition.build(W,np.arange(4))
    rng=np.random.default_rng(42)
    initial=rng.normal(size=(7,2,4)); forcing=rng.normal(size=(7,6,4)); coef=[.5,.1,.2,.1]
    z,r=enclose(initial,forcing,singleton,coef)
    assert np.array_equal(z,rollout(initial,forcing,W,coef))
    assert np.count_nonzero(r) == 0 and np.count_nonzero(singleton.defect) == 0


def test_gaussian_analytic_moments_and_constraints():
    rng=np.random.default_rng(141)
    U=rng.normal(size=(8,3))*.3; diagonal=np.arange(1,9)/10
    model=GaussianHistory(np.arange(8)/10,U,diagonal)
    A=sparse.csr_matrix([[1,0,0,0,0,0,0,0],[0,0,.5,.5,0,0,0,0]])
    values=np.array([.7,-.2])
    covariance=U@U.T+np.diag(diagonal)
    dense=A.toarray()
    gain=covariance@dense.T@np.linalg.inv(dense@covariance@dense.T)
    mean=model.mean+gain@(values-dense@model.mean)
    cov=covariance-gain@dense@covariance
    samples=model.sample(A,values,80000,rng)
    assert np.max(np.abs(samples.mean(axis=0)-mean)) < .015
    assert np.max(np.abs(np.cov(samples,rowvar=False)-cov)) < .02
    assert np.max(np.abs(samples@dense.T-values)) < 1e-12
    # Check dependence did not disappear under conditioning.
    assert abs(np.cov(samples,rowvar=False)[4,5]-cov[4,5]) < .01


@pytest.mark.parametrize('mode',['missing','all','none','partial'])
def test_retained_constraints_missing_and_full(mode):
    rng=np.random.default_rng(7); L,n=3,8
    history=rng.normal(size=(L,n)); mask=np.ones((L,n),bool)
    if mode == 'missing': mask[0,:]=False; mask[1,3]=False
    if mode == 'none': mask[:]=False
    selected=np.arange(n) if mode == 'all' else np.array([0,4])
    blocks=np.repeat([0,1],4)
    info=retain(history,mask,blocks,selected,[1,0])
    A,values=independent_constraints(info,blocks)
    model=GaussianHistory(np.zeros(L*n),rng.normal(size=(L*n,3)),np.ones(L*n))
    samples=model.sample(A,values,20,rng).reshape(20,L,n)
    for t in range(L):
        for b in [0,1]:
            ids=(blocks == b)&mask[t]
            if ids.any(): assert np.allclose(samples[:,t,ids].mean(axis=1),history[t,ids].mean(),atol=1e-10)
    for i in selected:
        assert np.allclose(samples[:,:,i][:,mask[:,i]],history[:,i][mask[:,i]])
    if mode == 'all': assert np.max(np.abs(samples-history)) < 1e-10
    if mode == 'none': assert samples.var() > 0


def test_redundancy_removal_and_inconsistent_observation_rejection():
    A=np.array([[1,0],[0,1],[.5,.5]])
    B,b=remove_redundant_rows(A,[1,2,1.5])
    assert len(B) == 2 and np.allclose(np.linalg.solve(B,b),[1,2])
    with pytest.raises(ValueError): remove_redundant_rows(A,[1,2,3])


def test_event_equality_and_missing_bounds():
    states=np.zeros((1,6,4))
    assert event(states,4)[0]
    states[:]=-np.nextafter(0.,1.)
    assert not event(states,1)[0]
    mask=np.ones_like(states,bool); mask[:,:,0]=False
    low,high,eligible=observed_bounds(states,mask,1)
    assert not low[0] and high[0] and not eligible[0]
    states[:,:,1:]=1
    low,high,_=observed_bounds(states,mask,2)
    assert low[0] and high[0]


def test_zero_event_interval_and_two_level_exact_enumeration():
    summary=bernoulli_summary(np.zeros(256,int))
    assert summary['zero_event_one_sided_upper'] > .01 and summary['interval'][1] > 0
    # Four equiprobable states: exact fine risk 1/2, coarse risk 1/4.
    fine=np.array([0,1,0,1]); coarse=np.array([0,0,0,1])
    assert fine.mean() == .5 and coarse.mean() == .25
    # Enumerate all independent cheap/correction draws, two per sample set.
    estimates=[]
    for a,b,c,d in product(range(4),repeat=4):
        estimates.append(two_level(coarse[[a,b]],coarse[[c,d]],fine[[c,d]])['estimate'])
    assert np.mean(estimates) == .5
    assert np.min(estimates) < 0 or np.max(estimates) > 1
    zero=two_level([0,0],[0,0],[0,0])
    assert zero['interval'][1] > 0
    with pytest.raises(ValueError): two_level([0,0],[0,0],[0,0],[1,2],[2,3])
    counts=allocate_two_level([.1,.2],[1.,3.],200.)
    assert counts.min() >= 32 and counts@[1,3] <= 200


def test_certified_mode_explicitly_falls_back_to_coupled_fine():
    W=np.eye(2); p=Partition.build(W,[0,0])
    initial=np.ones((5,2,2)); forcing=np.ones((5,6,2)); coef=[.5,.1,.1,.1]
    labels,detail=selective(initial,forcing,W,coef,p,1,mode='certified')
    assert detail['refined'].all() and not detail['unresolved'].any()
    assert np.array_equal(labels,event(rollout(initial,forcing,W,coef),1))


def test_scenario_prefix_invariance_across_sample_counts_and_batches():
    model=GaussianHistory(np.zeros(5),np.ones((5,2))*.2,np.ones(5))
    A=sparse.csr_matrix([[1,0,0,0,0]])
    small=model.sample(A,[.4],7,np.random.default_rng(10))
    large=model.sample(A,[.4],19,np.random.default_rng(10))
    assert np.array_equal(small,large[:7])
    rng=np.random.default_rng(10)
    batched=np.concatenate([model.sample(A,[.4],7,rng),model.sample(A,[.4],12,rng)])
    assert np.allclose(large,batched,rtol=0,atol=1e-15)
