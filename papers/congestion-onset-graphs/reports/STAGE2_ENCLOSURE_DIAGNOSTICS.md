# Stage 2 enclosure diagnosis

**Decision: stop refinement work; keep it disabled.** The original bound is valid
in exact arithmetic but uninformative here. One justified tightening reduces
width substantially and still resolves no scenario. Neither implementation has
a floating-point certificate. This is a real PEMS-BAY development diagnostic,
not a general impossibility result for selective refinement.

## Frozen workload and coupling

Use 16 uniformly spaced indices from the saved 128 Stage 1 validation origins,
retention 0/15/100%, and 256 scenarios per origin. The 12,288 scenario evaluations
reuse the original initial-history and forcing seed streams; fine event counts
match the saved Stage 1 rows exactly. This is a smaller coupled diagnostic set,
not a new origin search. All fine trajectories are computed for diagnosis.

Each timing panel uses the same 16 origins, 15% retention, N=256, five repetitions,
and alternating method order. Every method independently pays for retained summaries,
conditioning, sampling, forcing, initial reductions, bound propagation, compaction,
fine evaluation, event labels and binomial intervals. Inputs and fitted banks are
resident; archival I/O and offline construction are separate job costs. Timings
use four threads on the local Intel i5-10400 CPU, not the Pod CPU or GPU. No new
GPU run or compilation occurred.

## Attribution of radius growth

The existing recurrence is linear in nonnegative radii once the coarse centers
are fixed. Initialize three additive components: initial within-block variation,
structural injection, and forcing injection. Propagate each through

    r_next = a0*r + a1*r_previous + (beta+gamma)*(Wbar+D)*r + injection.

Only the structural component receives (beta+gamma)*D*|z|; only the forcing
component receives delta. Their sum recovers the original radius. Propagation
acts on all three components, so "dynamical amplification" is not a fourth
independent additive source. The saved tables also show newly injected versus
inherited radius to avoid double counting.

Full-retention means on the fixed diagnostic set:

| Future frame | Initial component | Structural component | Forcing component | Total radius | Actual mean error |
|---|---:|---:|---:|---:|---:|
| 1 | 4.125 | 1.583 | 1.836 | 7.545 | 1.135 |
| 2 | 5.425 | 3.378 | 3.888 | 12.690 | 1.137 |
| 3 | 7.206 | 5.835 | 6.665 | 19.706 | 1.117 |
| 4 | 9.582 | 9.108 | 10.328 | 29.017 | 1.107 |
| 5 | 12.766 | 13.493 | 15.182 | 41.442 | 1.103 |
| 6 | 17.036 | 19.372 | 21.665 | 58.073 | 1.105 |

Mean initial radius is 2.968. Each subsequent step injects about 1.57–1.59
structural and 1.79–1.84 forcing radius, but inherited radius reaches 54.69 at
step six. Although W has row sums one and fitted coefficient sum .98,
**Wbar+D row sums range from 2.824 to 4.985**. Entrywise maxima combine different
nodes' worst connections, introducing artificial growth into the bound. The
fine dynamics do not exhibit that radius growth. No implementation error or
enclosure escape explains these findings.

Across all six frames, the original mean radius is 29.278/28.208/28.079 at
0/15/100%, versus mean center-to-event-threshold distance 3.893 and actual mean
fine/coarse error 1.148/1.092/1.118. Full interval widths are twice those radii.
Every sustained-fraction interval is [0,1]; every event remains unresolved.

## Oracle-only diagnostic

After computing the fine trajectory, take its exact minimum and maximum within
each block and frame. These are the smallest rectangles containing those actual
node values. They cannot be obtained cheaply and are **not a certificate speedup**.

At 0/15/100%, oracle unresolved fractions are .36963/.28833/.27808; mean rectangle
widths are 5.417/5.158/5.234 log odds. Mean sustained upper fractions are
.19992/.17309/.16928, while lower fractions remain zero. Even these oracle boxes
cannot certify positive sustained events on this diagnostic set because spatially
mixed blocks lose within-block counts. This isolates remaining coarsening loss
from inflated propagated radii. It does not say a more informative representation
could never do better. No oracle quantity enters model fitting or deployed forecasts.

## The one attempted tightening

Let w_ib be node i's total weight into block b, and E_ib=w_ib-Wbar_ab for i in a.
Instead of entrywise block maxima before multiplication, use

    e*_a = max_(i in block a) [sum_b w_ib*r_b + |sum_b E_ib*z_b|].

For x=Pz+eta with |eta_j|<=r_block(j), nonnegative W gives

    |(Wx)_i-(Wbar*z)_a| <= sum_b w_ib*r_b + |(E*z)_i|.

Taking the block maximum therefore bounds the neighbor discrepancy. The same
ReLU Lipschitz and nonnegative-coefficient argument yields the old radius
recurrence with e*. No error term is discarded. For a fixed radius, e* is no
larger than the original e; monotonicity then inductively ensures tighter radii
with identical centers. E*1=0 retains cancellation of common state offsets that
D|z| loses. This is a direct triangle-inequality improvement, not claimed novelty.

Weights and residual are n-by-k; each step performs two N-by-k times k-by-n
products and block maxima: O(N*n*k), with the unchanged O(N*n) preparation costs.
Construction time is recorded separately; complete online times include all
additional products and reductions. No partition adjustment or second tightening
was attempted. The original implementation and all Stage 1 results are preserved.

| Retention | Original mean radius | Tightened mean radius | Tightened final radius | Unresolved |
|---|---:|---:|---:|---:|
| 0% | 29.278 | 8.884 | 12.488 | 100% |
| 15% | 28.208 | 8.544 | 12.156 | 100% |
| 100% | 28.079 | 8.524 | 12.146 | 100% |

The mean sustained upper fraction is still .995/.991/.992 and the lower is
zero. The radius reduction is about 70%, but every scenario remains ambiguous.
No unexplained enclosure violation or coupled-label disagreement occurred.
The maximum fine-error-minus-radius is negative for both methods.

## Complete repeated costs and decision gate

Original selective time / its paired fine time across five repetitions:
**1.2393, 1.1650, 1.1610, 1.1745, 1.1837**.
Tightened selective ratios:
**1.2505, 1.2613, 1.2356, 1.2231, 1.2192**.

The original panel's mean fine/selective times are about 61.31/72.61 ms;
the tightening panel's mean fine/selective times are about 58.20/72.05 ms.
Use each panel's paired reference: host/cache variation prevents interpreting
the difference between those two fine means as a method improvement. All five
repetitions lose; the required ratio <=.90 is nowhere approached. Fewer unresolved
scenarios would not itself establish savings, and here even that condition fails.

The exact-arithmetic proposition remains separate from numerical certification.
FP64 checks, including 256 exhausted initial-state corners on a heterogeneous
four-node graph, support implementation consistency but are not an outward rounding
proof. The Stage 1 FP32 cancellation counterexample remains relevant. Conservative
numerical mode would refine all samples even if an empirical interval resolved one.
No formal rounding proof was attempted for these practically uninformative bounds.

The mean-location repair changes the joint initial/forcing law, not the fixed
pathwise recurrence. This enclosure diagnostic deliberately uses the original
Stage 1 scenarios for attribution; no repair-specific enclosure speed claim is
made. The code can enclose arbitrary supplied coupled forcing under the stated
assumptions, but that fact does not validate a stochastic model or a numerical claim.

Outputs: `enclosure_components.csv`, `enclosure_widths.csv`,
`enclosure_repeated_timings.csv`, `tightening_widths.csv`, `tightening_timings.csv`,
their JSON summaries, and `figures/enclosure_width_cost.{pdf,svg,png}` under
`results/stage2/`. No further refinement work is recommended for this project stage.
