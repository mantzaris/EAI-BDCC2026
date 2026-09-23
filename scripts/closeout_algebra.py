"""Three bounded rational checks; no data, model fit, RNG, NumPy or GPU imports.

Run via scripts/closeout_budget.py to keep an append-only CPU reservation ledger.
Finite checks support the displayed examples, not any general sufficiency theorem.
"""
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path
import time


def main():
    started = time.perf_counter(); cpu = time.process_time()
    target = Path('results/closeout/algebra_checks.json')
    if target.exists(): raise FileExistsError('Preserve the previous algebra record')
    # A connected, symmetric, row-stochastic W; QW = Q and WP = P.
    w = ((F(15,16), F(1,16)), (F(1,16), F(15,16)))
    assert all(sum(row) == 1 for row in w)
    assert all(sum(w[i][j] for i in range(2)) == 1 for j in range(2))
    x, y = (F(-2), F(4)), (F(1), F(1))
    trajectory = []
    for h in range(1, 7):
        x = tuple(sum(w[i][j]*x[j] for j in range(2))/2 for i in range(2))
        y = tuple(sum(w[i][j]*y[j] for j in range(2))/2 for i in range(2))
        assert sum(x) == sum(y)
        # Independent spectral expression for this particular two-node map.
        assert x == (F(1,2)**h*(1-3*F(7,8)**h), F(1,2)**h*(1+3*F(7,8)**h))
        trajectory.append(dict(h=h, x=[str(v) for v in x], y=[str(v) for v in y],
                               equal_mean=str(sum(x)/2), count_x=sum(v>=0 for v in x),
                               count_y=sum(v>=0 for v in y)))
    labels = [int(any(all(r[key] >= 2 for r in trajectory[s:s+3]) for s in range(4)))
              for key in ('count_x','count_y')]
    assert labels == [0, 1]
    # Four equiprobable states; Y is a monotone, persistent two-sensor count event.
    states = [(bits, bits[0]*bits[1]) for bits in product((0,1), repeat=2)]
    def bayes_risk(observed):
        groups = {}
        for bits, label in states:
            groups.setdefault(tuple(bits[j] for j in observed), []).append(label)
        return sum(sum((F(label)-F(sum(labels),len(labels)))**2 for label in labels)
                   for labels in groups.values())/4
    risks = {name: bayes_risk(ids) for name,ids in [('none',()),('first',(0,)),('second',(1,)),('both',(0,1))]}
    assert risks == dict(none=F(3,16), first=F(1,8), second=F(1,8), both=F(0))
    first_gain = risks['none']-risks['second']; conditional_gain = risks['first']-risks['both']
    assert conditional_gain > first_gain  # Violates diminishing returns.
    # Posterior quantization is a derived bound, not a new measured traffic result.
    step = F(1,255); error = step/2; bayes_bound = error**2
    assert bayes_bound == F(1,260100)
    record = dict(questions_record='configs/research_closeout.json', seed=None,
        arithmetic='fractions.Fraction; hand-specified, no random sampling',
        exact_mean_counterexample=dict(W=[[str(v) for v in row] for row in w],
            dynamics='x_next = (1/2) W x; zero forcing; one block', D='0',
            x_initial=['-2','4'], y_initial=['1','1'], threshold_count=2, sustained_frames=3,
            horizon_frames=6, trajectory=trajectory, event_labels=labels,
            conclusion='Exact mean closure and D=0 do not determine a sensor-count event'),
        selection_counterexample=dict(law='Independent fair bits; Y=X1 AND X2',
            bayes_risks={k:str(v) for k,v in risks.items()}, first_gain=str(first_gain),
            gain_after_other_sensor=str(conditional_gain), submodular=False,
            conclusion='Monotone task and independent measurements do not imply submodular Brier benefit'),
        posterior_quantization=dict(bits=8, grid_points=256, maximum_error=str(error),
            true_posterior_excess_brier_bound=str(bayes_bound), decimal_bound=float(bayes_bound),
            arbitrary_fitted_probability_absolute_loss_change_bound=str(2*error),
            qualification='Expectation bound assumes true posterior; fitted risks need separate error/calibration accounting; packet overhead excluded'),
        gpu_seconds=0, cuda_seconds=0, measurements_loaded=False, test_access=False,
        cpu_seconds=time.process_time()-cpu, internal_wall_seconds=time.perf_counter()-started,
        general_theorem_proved_by_numerics=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))


if __name__ == '__main__': main()
