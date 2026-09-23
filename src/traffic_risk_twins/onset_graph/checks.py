"""Independent GPU invariants, historical replay, and durable weight restoration."""
import csv
import gzip
from pathlib import Path
import torch
from ..residual_gpu.checks import scientific_checks
from ..residual_gpu.data import to_cuda
from ..residual_gpu.baseline import GPUQuantileBoost
from ..residual_gpu.models import ResidualCorrection,predict_correction,corrected_probability
from .models import build,predict
from .graphs import projection,propagate,rewire
from .data import StudyData
from .io import read,save,load_weights,save_weights,compact_state,restore_state
from .calibration import fit_calibration,apply_calibration,alarm_cutoff
from .evaluation import resample


def prior_replay(c,out,art,source):
    data=StudyData(c);private=Path(c['reference_private']);record={};reference_art=art.parent/'references'
    stored=torch.load(private/'baseline.pt',map_location='cuda',weights_only=True)
    data.feature_free=stored['feature_free'];baseline=GPUQuantileBoost.from_state(stored['baseline'])
    data.load('validation');part=data.prepare(data.splits['validation']['origins']);part['p']=baseline.predict(part['X'])
    norm=torch.load(private/'normalization.pt',map_location='cuda',weights_only=True)
    selected=read('results/residual_pilot/pilot01/selected.json')
    with gzip.open('results/residual_pilot/pilot01/validation_predictions.csv.gz','rt') as stream:rows=list(csv.DictReader(stream))
    assert torch.equal(part['origins'],to_cuda([int(r['origins']) for r in rows],torch.long))
    assert torch.equal(part['y'],to_cuda([float(r['y']) for r in rows],torch.float64))
    save_weights(reference_art/'A_T.pt.gz',stored)
    saved=to_cuda([float(r['A_T']) for r in rows],torch.float64);assert torch.equal(saved,part['p'])
    expected=read('results/residual_pilot/pilot01/primary_metrics.json')
    predictions={'A_T':part['p']}
    for family in ('B','C','D'):
        for rep in selected[family]['replicates']:
            model=ResidualCorrection(family,c['correction'],norm['mean'],norm['scale'],data.blocks,data.W)
            full=torch.load(private/(rep['name']+'.pt'),map_location='cuda',weights_only=True);model.load_state_dict(full['state']);model.eval()
            p=corrected_probability(part['p'],predict_correction(model,part),rep['alpha'])
            saved=to_cuda([float(r[rep['name']]) for r in rows],torch.float64);error=(p-saved).abs().max();assert error<1e-12
            export=reference_art/(rep['name']+'.pt.gz');save_weights(export,dict(state=compact_state(model),alpha=rep['alpha'],family=family,
                cutoff=rep['threshold'],source_sha=source,original_source='29c64549c12e5daaad187cfe15f774d0ff3cd962'))
            fresh=ResidualCorrection(family,c['correction'],norm['mean'],norm['scale'],data.blocks,data.W)
            restore_state(fresh,load_weights(export)['state']);q=corrected_probability(part['p'],predict_correction(fresh,part),rep['alpha']);assert torch.equal(q,p)
            predictions[rep['name']]=p;record[rep['name']]=dict(saved_max_error=error.item(),compact_reload_exact=True)
    scores={}
    for key,p in predictions.items():
        scores[key]={}
        for endpoint,keep in [('all_time',part['eligible']),('onset',part['eligible']&~part['active'])]:
            score=(p[keep]-part['y'][keep]).square().mean();assert torch.abs(score-to_cuda(expected['per_model'][key][endpoint]['brier'],torch.float64))<1e-12
            scores[key][endpoint]=score.item()
    save(out/'prior_replay.json',dict(complete=True,records=record,scores=scores,original_artifacts_unchanged=True,
        recoverability='Local private originals plus committed compact parameters; original graph requires verified private input',
        previous_onset_secondary=True,new_candidate_evaluation=False,test_access=False))


def audit(c,out,art,source):
    old=scientific_checks(c);save(out/'inherited_gpu_checks.json',old)
    torch.manual_seed(20261009);torch.cuda.manual_seed_all(20261009);checks=[]
    # Independent 4-node mechanism: WL=LQ can hold while RW differs from QR.
    L=torch.tensor([[1.,0],[1,0],[0,1],[0,1]],device='cuda',dtype=torch.float64);R=L.T/2
    W=torch.zeros(4,4,device='cuda',dtype=torch.float64);W[:,0]=1;Q=R@W@L
    x=torch.tensor([1.,-1,0,0],device='cuda',dtype=torch.float64);other=-x;z=R@x;u=x-L@z
    assert torch.equal(R@L,torch.eye(2,device='cuda',dtype=torch.float64))
    assert torch.equal(W@L,L@Q) and not torch.allclose(R@W,Q@R)
    assert torch.equal(R@x,R@other) and not torch.equal(R@W@x,R@W@other)
    assert torch.allclose(R@W@x,Q@z+R@W@u)
    assert torch.allclose(R@torch.eye(4,device='cuda',dtype=torch.float64)@u,torch.zeros(2,device='cuda',dtype=torch.float64))
    mask=torch.tensor([False,True,True,True],device='cuda');observed=torch.where(mask,x,0)
    counts=R@mask.double();zo=(R@observed)/counts.clamp_min(.01);v=mask*(x-L@zo);completed=L@zo+v
    assert torch.allclose(R@v,torch.zeros_like(zo)) and torch.allclose(R@completed,zo)
    assert torch.allclose(R@W@completed,Q@zo+R@W@v)
    save(out/'projection_example.json',dict(W=W,R=R,L=L,x=x,other=other,shared_z=z,response=R@W@x,other_response=R@W@other,
        forward_invariance_WL_LQ=True,mean_closure_RW_QR=False,missing_mask=mask,completed_predictor_state=completed,
        interpretation='Hand-specified mechanism counterexample, not measurement prevalence or novel theorem'))
    checks.append('Directed mean-closure counterexample and exact fixed-projection/missing-completion identities')
    N=32;blocks=torch.arange(N,device='cuda')//2;W=torch.rand(N,N,device='cuda');W[W<.8]=0;W.fill_diagonal_(1);W/=W.sum(1,keepdim=True)
    R,L=projection(blocks,torch.float32);vector=torch.randn(7,N,device='cuda');sparse=W.to_sparse_coo()
    assert torch.allclose(propagate(sparse,vector),vector@W.T,atol=1e-6)
    checks.append('Sparse graph application matches independent dense matrix reference')
    null,stats=rewire(W,20261004,rounds=100);assert stats['accepted_swaps']>0 and not torch.equal(null,W)
    checks.append('Actual double swaps preserve per-node degrees and row weight multisets')
    mean=torch.zeros(1158,device='cuda');scale=torch.ones_like(mean);X=torch.randn(7,1158,device='cuda');X[:,192:384]=2
    Z=torch.randn(7,N,12,4,device='cuda');Z[:,:,:,-1]=1;Z[:,0,:,-1]=0
    mask=Z[:,:,:,-1].bool().any(-1);p=torch.linspace(.2,.8,7,device='cuda').double()
    permutation=torch.randperm(N,device='cuda');differences={}
    for kind in c['correction']['families']:
        model=build(kind,c['correction'],mean,scale,blocks,W,20261001)
        r=model(X,p,Z,mask);assert torch.equal(corrected_probability(p,r),p)
        loss=(corrected_probability(p,r)-1).square().mean();loss.backward();assert model.head.weight.grad.abs().sum()>0
        with torch.no_grad():model.head.weight.normal_(0,.1);model.head.bias.fill_(.02)
        expected=model(X,p,Z,mask);assert expected.abs().max()>1e-6
        poisoned=Z.clone();poisoned[:,0,:,:3]=torch.nan
        assert torch.allclose(model(X,p,poisoned,mask),expected,atol=1e-7)
        if kind=='M':assert torch.equal(model(X,p,torch.full_like(Z,torch.nan),~mask),expected)
        fresh=build(kind,c['correction'],mean,scale,blocks[permutation],W[permutation][:,permutation],20261001)
        restore_state(fresh,compact_state(model));actual=fresh(X,p,Z[:,permutation],mask[:,permutation])
        difference=(actual-expected).abs().max();assert difference<2e-5,(kind,difference.item())
        differences[kind]=difference.item()
        artifact=art/(kind+'_synthetic_check.pt.gz');save_weights(artifact,dict(state=compact_state(model)))
        restored=build(kind,c['correction'],mean,scale,blocks,W,20261001);restore_state(restored,load_weights(artifact)['state'])
        assert torch.equal(restored(X,p,Z,mask),expected)
    checks.append('All8 representations: zero recovery, learnable head, poison masks, simultaneous permutation and compact reload')
    tied=torch.tensor([0.,0,0,.1,.5,.9],device='cuda',dtype=torch.float64);y=torch.tensor([0.,0,0,0,1,1],device='cuda',dtype=torch.float64)
    cut=alarm_cutoff(tied,y);assert torch.equal(tied>cut,torch.tensor([False,False,False,False,True,True],device='cuda'))
    calibration=fit_calibration(tied.repeat(5),y.repeat(5),c['calibration']);q=apply_calibration(tied,calibration)
    assert torch.all(q[1:]>=q[:-1]) and q[0]==q[1] and q[1]==q[2]
    checks.append('Strict tie rule controls calibration false positives; monotone calibration preserves ties')
    days=torch.tensor([1,2,6,7],device='cuda');values=torch.tensor([[1.],[1.],[9.],[9.]],device='cuda',dtype=torch.float64)
    draws=resample(values,days,3,200);assert torch.equal(draws,torch.full_like(draws,5))
    checks.append('Calendar-gap bootstrap preserves separate constant segments without bridging gaps')
    data=StudyData(c)
    try:data.load('test')
    except ValueError:pass
    else:raise AssertionError('Test reader accepted forbidden split')
    checks.append('Test measurement reader rejects access before loading')
    save(out/'gpu_checks.json',dict(passed=True,checks=checks,permutation_max_errors=differences,source_sha=source))
    prior_replay(c,out,art,source)


def replay(c,fold,out,art,source):
    from run_onset_graph import collect
    data=StudyData(c);stored=load_weights(art/'anchor.pt.gz');data.feature_free=stored['feature_free']
    base=GPUQuantileBoost.from_state(stored['baseline']);data.load('validation')
    part=data.prepare(data.splits['validation']['origins']);part['p']=base.predict(part['X'])
    metadata=read(out/'models_with_nulls.json');graphs={'distance':data.W};errors={}
    for calibrated,filename in [(False,'validation_raw_predictions.csv.gz'),(True,'validation_calibrated_predictions.csv.gz')]:
        pp,_,_,_=collect(c,data,art,part,metadata,graphs,calibrated)
        with gzip.open(out/filename,'rt') as f:rows=list(csv.DictReader(f))
        assert torch.equal(part['origins'],to_cuda([int(r['origins']) for r in rows],torch.long))
        assert torch.equal(part['y'],to_cuda([float(r['y']) for r in rows],torch.float64))
        for key,p in pp.items():
            expected=to_cuda([float(r[key]) for r in rows],torch.float64);error=(p-expected).abs().max()
            assert error<1e-10,(key,error.item());errors[filename+'/'+key]=error.item()
    save(out/'durable_replay.json',dict(complete=True,source_sha=source,max_errors=errors,test_access=False,
        weights='Compressed versioned parameters reloaded; original private graph reconstructed from verified archive'))
