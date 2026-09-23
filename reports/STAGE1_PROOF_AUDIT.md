# Stage 1 proof and correctness audit

Audit date: September 22, 2026. This audit independently re-derived the bound and
implemented new arithmetic/reference checks. It does not count the planning
document's 200 toy graphs as validation. No second human or external mathematical
referee has reviewed this work; “independent” here means a separate derivation and
independent numerical references, not an external endorsement.

## Decision

The displayed graph recurrence and enclosure are valid in exact arithmetic under
the assumptions below. No correction to that recurrence was necessary. The
implementation's floating-point graph bound is **empirical**, not a verified
rounding enclosure. The `certified` path therefore evaluates every scenario with
the coupled fine floating-point reference. It guarantees identity with that
reference, not an exact real-arithmetic threshold decision. Empirical selective
results are separately labeled. Theoretical novelty remains unestablished.

## Independent derivation and dimensions

Let P be the n-by-k block incidence matrix and Q = diag(block sizes)^(-1) P^T.
Then QP = I_k, Wbar = QWP is k-by-k, and the structural residual
E = WP - P Wbar is n-by-k. For i in block a,
E_ib = sum_{j in B_b} W_ij - Wbar_ab. Thus D_ab = max_{i in B_a}|E_ib|.
This makes explicit that D is a blockwise absolute structural residual of a
standard quotient, not a variance of sensor states.

Write x = Pz + eta with |eta_i| <= r_a for i in B_a. For each row i,

```
Wx - P Wbar z = W eta + E z
|(W eta)_i| <= sum_b (sum_{j in B_b} W_ij) r_b
              <= sum_b (Wbar_ab + D_ab) r_b
|(E z)_i| <= sum_b D_ab |z_b|.
```

The first inequality uses W_ij >= 0. Consequently e = (Wbar+D)r + D|z|
encloses the neighbor discrepancy. For the stated coefficients,

```
F_i(x_h,x_{h-1},f_h)
  = a0*x_i,h + a1*x_i,h-1 + beta*(Wx_h)_i
    + gamma*ReLU((Wx_h)_i-theta) + f_i,h
```

and its quotient expression, ReLU's global Lipschitz constant 1 gives

```
|F_i - Fbar_a|
  <= a0*r_a,h + a1*r_a,h-1 + (beta+gamma)*e_a,h + delta_a,h.
```

The two starting radii are maxima about the sampled block means at h=-1 and
h=0. Each forcing center is the mean of the **same complete scenario forcing**;
its maximum deviation is delta. Induction establishes the claim for all six
steps. Shapes are x,f in R^n, z,r,delta,e in R^k, W in R^(n x n), and Wbar,D in
R^(k x k). All quantities have log-odds units except weights and coefficients.

Needed assumptions:

- A fixed nonempty partition; finite states, forcing, coefficients, and theta.
- Nonnegative W and the four coefficients. The implementation additionally
  requires row-stochastic W, consistent with the fitted model. Row stochasticity
  is not needed for the displayed finite-horizon induction itself.
- Both fine and coarse systems use identical coefficients, scalar threshold,
  time grid, scenario initial states, and forcing sequences.
- Absolute initial/forcing deviations are bounded as stated. No Gaussian or
  temporal/spatial independence assumption is needed for this deterministic bound.

The sum-of-coefficients cap 0.98 is a modeling/stability choice. The bound remains
valid for the prespecified 1.05 family or other finite nonnegative coefficients,
although radii may grow. Validation did not trigger a relaxed-model fit in this
pilot. Centering is not free: replacing x by x-m changes all corresponding drift
and forcing terms, including the nonlinear threshold expression. No centering
ablation was silently substituted into the recurrence.

## Event monotonicity, threshold equality, and terminal resolution

If z_a-r_a >= 0 every node in block a meets the local threshold; if
z_a+r_a < 0 none does. Weighted block counts therefore bound the fine sensor count.
The minimum across three consecutive future counts and maximum across all four
three-frame windows are monotone. Integer count comparisons implement the
attainable event threshold directly, avoiding a second rounding decision in q*n.
Equality belongs to the event. A negative label is certain only when the upper
sustained count is strictly below the count threshold.

For singletons, P=Q=I, Wbar=W, D=0, initial radii and forcing deviations vanish,
and coarse dynamics recover fine dynamics. D=0 alone is insufficient for general
blocks: within-block states and forcing can still differ. Conversely, zero
initial radius does not remove a nonzero E*z structural error. A deliberately
disabled D in a heterogeneous four-node example fails the enclosure check.

Successive arbitrary partitions need not give nested intervals. The pilot uses
one coarse partition and the finite fine terminal model, and does not assume
nested refinement or extrapolate a convergence rate to infinitely fine graphs.

## Numerical guarantees

Neither FP64 nor an arbitrary audit tolerance certifies exact arithmetic. A full
rounding proof would need to cover: quotient and D construction; dot products;
block means and maximum deviations; each signed sum in the center recurrence;
nonnegative radius accumulation; lifting; and the event comparison. Bounds on
roundoff in just the radius update omit necessary sources. GPU reduction order,
FMA, overflow/underflow, and reduced-precision matmul modes also matter.

This implementation deliberately does not advertise a partial gamma_m bound as
a complete certificate. TF32 is disabled for GPU reference computations. FP64
empirical enclosures are audited against every coupled fine pilot trajectory;
an unexplained violation aborts the run. A pass tolerance of 1e-10 is an error
detector, not an outward rounding proof. All numerical certificates are considered
uncertain in the conservative mode, so every scenario refines.

The GPU audit includes a constructive precision counterexample: initial state 2,
a0=1/2, all other coefficients zero, first forcing -1-1e-8, subsequent forcing
zero. FP32 rounds the first forcing to -1, yielding zero, hence positive labels
at equality. FP64 yields a negative first state, remaining negative, hence a
negative sustained label. This is not a contradiction of the theorem.

## Conditioning and estimator audit

The Gaussian is a working law with covariance UU^T+diag(d), d>0. Calendar means
and covariance are training-only. The covariance diagonal floor 1e-6 is explicitly
part of that prior, not a ridge added to observations. Omega=0 throughout.

Selected coordinates are subtracted from each block sum. Remaining hidden means
and exact selected coordinates have disjoint supports; fully observed block means
are redundant and removed. A retained block with no valid observations contributes
no constraint. Woodbury inversion then acts on A diag(d) A^T + (AU)(AU)^T without
forming an nL-by-nL covariance. Matheron samples use independent standard normals,
not independent shuffling of sensor observations. Generic QR redundancy removal
is checked separately on small systems. Retained consistency is numerical to a
reported tolerance, not symbolically exact floating-point equality.

Fine and conservative selective MC use complete fixed-N Bernoulli samples and
Clopper–Pearson intervals; zero-event samples have a positive upper bound.
Two-level samples have independent allocation, cheap, and correction streams.
Within each correction, coarse and fine use the same arrays and residual indices.
The uncertainty interval is a bounded-variable Hoeffding union bound, which stays
nonzero when pilot/sample variance is zero. Unclipped estimates are retained;
clipped scoring probabilities are separately named. Allocation has a 32-sample
floor and a 2N upper cap per level, so it is a constrained pilot heuristic, not an
assertion that continuous optimal allocation is attained.

The Brier decomposition in the plan is standard conditional orthogonality under
the stated independence and frozen-model assumptions. Its Bayes information-loss
and conditional-model-error terms are not separately identified from this pilot.
Changing N alters sampling error; it cannot establish that model error disappears.

## Closest prior work and remaining novelty gates

The focused search was performed on September 22, 2026. Primary sources support
the following comparison; a search is not proof of absence of prior art.

| Prior work | Relevant established result | Boundary for this project |
|---|---|---|
| [Elfverson, Hellman and Målqvist, failure probabilities](https://arxiv.org/html/1408.6856v1), §§5–7 | Samplewise threshold refinement and its combination with multilevel probability estimation | Selective evaluation, parallel realizations, and MLMC acceleration are established. The present contribution would have to be the particular computable graph bound and information study. |
| [Elfverson et al., adaptive subset simulation](https://arxiv.org/html/2208.05392v2), assumptions and adaptive thresholds | Samplewise error control and maintaining required subset relations | A finite count functional avoids a continuous-severity premise for label correctness; it supplies no automatic rare-event cost theorem. |
| [Schaub et al., graph partitions and cluster synchronization](https://arxiv.org/html/1608.04283v2), §§II–III | Equitable quotient identities and invariant clustered dynamics, with nonlinear examples | The D=0 algebra and exact clustered quotient are established. This project needs comparison of off-manifold componentwise residual bounds, not a claim to have invented quotients. |
| [Monshizadeh et al., structure-preserving network reduction](https://arxiv.org/abs/1403.4789) | Clustered physical-network reduction and H2 error for almost equitable partitions | An H2 input-output error is different from the present scenario/timewise radius, but broad graph-error novelty is not defensible. Full comparison remains needed. |
| [Yu et al., learning coarse graph dynamics](https://arxiv.org/html/2405.09324v2) | Mori–Zwanzig graph memory analysis and learned closures | Supports a strong aggregate-memory baseline; memory and unresolved interactions are not novel here. |
| [Peherstorfer et al., optimal multifidelity model management](https://doi.org/10.1137/15M1046472) | Cost/variance-based allocation among correlated fidelities | The allocation formula is background. This audit located the primary record; full manuscript comparison was not completed. |

Two particularly relevant gaps remain. The publisher search record for
[The link between equitable partitions and local agreements in multi-agent systems
with nonlinear interactions](https://www.sciencedirect.com/science/article/abs/pii/S1751570X26000804)
exposes a quasi-equitable residual E=AP-PB discussion. Direct full-text access
failed; the identity is close enough that novelty must remain an explicit gate.
The [2026 Sensors coarse-to-fine crowd paper](https://www.mdpi.com/1424-8220/26/13/4094)
also could not be read in full. Neither inaccessible paper is claimed to have been
ruled out. A positive-system reachability comparison and a complete match of
assumptions and norms remain necessary before any new-theorem claim.

## Executed checks and interpretation

The initial 19 local tests and the same 19 tests on the Pod passed. After removing
unnecessary computation, 21 local tests passed, adding the deterministic full-
observation law and coarse-only/center equivalence checks. Final Pod outcomes
are recorded in `results/pod_cpu_tests.txt`. The tests comprise:
243 exact dyadic two-node initial/forcing cases checked against a scalar Fraction
reference; 300 new random/near-boundary 12-node graphs with five scenarios each;
equitable and heterogeneous structural cases; singleton recovery; 80,000
conditional samples compared with analytic moments; exact constraints, redundancy,
all/missing observations; zero-event and threshold-equality checks; all 256
independent two-level draw combinations of an enumerable four-state model;
conservation over 200 CTM steps including external queues; poison-test HDF access,
window/embargo integrity; fixed selection; scenario prefix invariance; and ledger
failure/reservation persistence. Some pytest cases are parameterized.

The separate GPU audit passed 40 new graphs and 1,280 coupled scenarios, with no
FP64 event disagreement or positive enclosure violation. Its constructed FP32
counterexample is an expected finding, not an unexplained test failure. The
bounded pilot adds coupled checks on every reported real-data scenario; its
counts and numerical results are in STAGE1_PILOT_REPORT.md. These finite checks
support implementation correctness; they neither prove floating certification
nor establish theoretical originality.
