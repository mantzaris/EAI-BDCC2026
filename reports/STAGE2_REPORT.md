# Stage 2 handoff: diagnosis, simplification, and model repair

**Recommendation: stop the current submission-oriented method campaign.** The
matched learner finds no local-detail benefit on this exploratory panel. One
targeted simulator repair helps substantially but remains outside the adequacy
gate. One mathematically justified enclosure tightening remains uninformative and
slower than fine computation. The package is useful diagnostic evidence, not a
completed full study, independent confirmation, or submission-ready negative paper.

**No Stage 2 GPU run occurred. Test outcomes remain untouched. Stage 3 was not
started and is not proposed on the present evidence.**

## 1. Starting state, decisions, and preservation

The repository was inspected at `/home/resort/Documents/repos/EAI-BDCC2026` on
2026-09-23 UTC (the prior evening in America/New_York). Starting main was
**3f9e2e1308235a75bf0a1d84cbe2e6c50eaa97bd**, with a clean working tree and origin
`https://www.github.com/mantzaris/EAI-BDCC2026`. Fetch/fast-forward found no newer
remote work. No applicable AGENTS.md was present. No branch, PR, stash, reset,
force-push, or published-history rewrite was used. There were no unrelated changes.

README, all four Stage 1 reports, source/result/configuration evidence, the complete
original research plan, and the persistent ledger were read. The supplied Stage 1
summary agrees with actual files. **89 historical Stage 1 reports/results/manifests/
configuration/plan artifacts are checked by SHA-256 and unchanged.** Original
implementation modules also remain intact; Stage 2 code is additive.

`STAGE2_DECISIONS.md` and `configs/stage2_diagnosis.yaml` were saved and committed
before new model comparisons (`427e4eb`). Subsequent decisions recorded the one
residual-location repair and one enclosure tightening before their evaluation.
One classifier setting was used; no architecture, selector, target or region search
was added. The earlier Stage 1 proposal is preserved; this user's Stage 2 scope
supersedes its suggested validation calibration, larger N, and absolute .005 gate.
Here calibration is training-only, N stays at existing values, and gates are relative.

The concrete **CPU-reproduced source SHA is
a1ff98eb6ba147c361cb2f3020d19a9f0689e379**. A fresh directory replayed all eight
CPU analysis/plot scripts from that commit in 182.474 seconds. Raw/calibrated
prediction arrays and tightened widths reproduced with **zero maximum difference**.
Finalization, artifact checks and reports were added afterward. A later CSV
round-trip precision fix was rechecked on the affected summaries: maximum Brier
change 1.05e-17, unchanged alarm counts and paired detection. Model predictions
are unchanged. These distinctions are recorded in `manifests/stage2/source_files.json`
and `results/stage2/table_precision_check.json`. There is **no new GPU-tested
source SHA**. Historical Stage 1 GPU source remains
128f8f15257c51677e197ec2493ddc4c0d098820.

The final artifact verifier ran from committed CPU source
**d37c555b1d8909dc903dea5fc60865f4d04a9a52**. Its ten groups of consistency
checks passed without loading measurement data. The later delivery adds only
reports, provenance and results.

## 2. Data, comparison audit, and actual denominators

Reuse the originating DCRNN PEMS-BAY release: 52,116 five-minute frames, 325 speed
sensors, Jan 1–Jun 30, 2017, mph. Raw HDF SHA-256 is
`65d69fb0a2323dba9867179eb7af47c8b814186bc459ff0a4937d21614153c8f`.
The private Stage 1 fitted-input hash is
`65afcc26e5c3ca971557167f9de1252533c7f9acb20fe417671898dadc202ea3`.
The graph order is aligned, with 2,369 directed nonself edges, 12 isolated-row
fallbacks, and 16 fixed geographic blocks. Timestamps are naive; incomplete
March 12 is excluded. These details and exact date lists remain in Stage 1 manifests.

The complete-day outer split stays 108 training days (Jan 1–Apr 19, excluding
Mar 12), 36 validation days (Apr 20–May 25), and 36 test days (May 26–Jun 30).
Each input has 12 frames and its outcome six future frames, all inside its split,
with a 90-minute embargo on both sides of boundaries. Training-only 85th-percentile
free speeds define clipped log odds. A positive event requires at least 48/325
sensors at state >=0 for three consecutive future frames. Equality is positive.
Zeros remain unknown indicators; future labels use explicit lower/upper bounds
and require >=95% coverage. Future missing values are never imputed into labels.

| Development population | Eligible origins | Positive origins | Episode groups | Event days |
|---|---:|---:|---:|---:|
| Entire training | 31,052 | 3,130 | 116 | 73 |
| Entire validation | 10,309 of 10,315 | 1,478 | 47 | 26 |
| Saved 128-origin panel | 127 | 20 | 20 represented | 17 |
| Onset subset of panel | 110 | 5 | 5 represented | 5 |

Episode groups merge positive target periods separated by less than 30 minutes;
they are not proven statistically independent. Uncertainty resamples whole days
and moving three-day blocks. Every scored model uses the same panel, target,
horizon, eligibility and equal-origin weights. Recomputed Stage 1 scores match;
raw A refitting agrees to 1.11e-16. The initial simulator comparison supplied
different information and used different learners, so it was not an information-
loss estimate. A additionally receives variance, extrema and severe-fraction
histories. No local deployment-time selection looks at discarded current values.

All 36 validation days informed Stage 1 support/model decisions. There are **no
untouched validation day blocks**. Results are exploratory validation throughout.
Source inspection and tests found no new future-feature or outer-label fitting;
unknown upstream processing prevents a stronger claim about original measurements.
Test data were not used for event counts, fitting, calibration, scoring, or choices.

## 3. Matched predictive comparison and uncertainty

A is the strongest clean Stage 1 aggregate-plus-heterogeneity histogram-gradient-
boosted classifier. B adds 49 fixed training-selected histories/masks as local
deviations. C adds all 325. At zero additions, A is recovered exactly. Each uses
the same 2,588 training histories, one shared setting (100 iterations, 15 leaves,
L2=10, learning rate .1, minimum leaf 20, seed 20260922), and no search.

Inner training roles contain 54/27/27 chronological days, cut at February 24 and
March 24, with embargoes and contained windows. New fitted model/calibration steps
use their proper earlier training roles. The already-frozen free speeds, target,
partition and selector summarize all outer training; inner diagnostics do not
independently validate those design constants. Classifier logistic calibration
uses 643 final-block out-of-fold predictions with 37 positives, then transports
that map to the full-training refit. No outer labels calibrate probabilities.

| Model | Raw all-time Brier | Training-calibrated Brier | Raw PR-AUC | Payload bytes |
|---|---:|---:|---:|---:|
| Constant training prevalence .10079866 | .13589308 | Not fitted | .157480 | — |
| A: aggregate + heterogeneity | **.02645607** | .03384796 | .974766 | 13,164 |
| B: A + 15% local histories | .03061073 | .03807335 | .961819 | 18,260 |
| C: A + full local histories | .03046243 | .03645572 | .963947 | 46,964 |

Pilot prevalence is .157480 all-time and .045455 on onset. The payload includes
FP64 statistics/histories/calendar, int64 counts/IDs, and full unpacked masks,
counted once; protocol framing/compression is excluded. All 3,900 history values
are read for edge summaries. More local information therefore has a measured cost.

| Raw paired comparison | Brier difference | 95% whole-day interval | 95% three-day interval |
|---|---:|---|---|
| B minus A | +.00415466 | [-.00108586, .01038632] | [-.00186381, .00682069] |
| C minus A | +.00400637 | [-.00125024, .00997672] | [-.00209000, .00735276] |

Point Brier deteriorates 15.70%/15.14%; neither meets the predeclared >=5% relative
improvement gate. Broad intervals prevent a claim that added information must harm
prediction. This is limited evidence of useful local identity for this task,
fixed selector and learner, not a statement about all digital twins or Bayes risk.

Alarms target <=5% false-positive rate on inner onset non-events, with deterministic
tie handling. A/B/C achieve 29/597=4.858% there. Each detects **4/5** outer onset
positives with **4/105=3.810%** false alarms. They have no paired recall drop on
this panel, but five positives are inadequate for a strong detection conclusion.
Raw and calibrated scores, reliability bins, probability quantiles, and event/
non-event loss contributions are saved. Training calibration worsens A/B/C outer
scores; its lower-prevalence calibration block and transport are material limits.

## 4. Monte Carlo diagnosis and the one model repair

For the raw fixed-N independent Bernoulli means only, average expected sampling
variance is bounded by average 1/(4N): **.000244140625 at N=1,024**. Estimated
variance is .00002460/.00003010/.00003411 at 0/15/100% retention, against gaps
to A of .05785/.04892/.03680. The worst bound is under 0.7% of those gaps.
This concerns expected sampling error, not a bound on realized score differences.
It is not applied to clipped, calibrated, dependent, or two-level estimates.
More samples are not a plausible primary repair.

CPU inner diagnostics separate exact conditioning from covariance undercoverage,
clipping from inversion, and full-retention future error from hidden-state error.
The inverse/declared clipping matches to 1.42e-14. The Gaussian's inner nominal-95%
coverage is only 76.81%/83.14% at 0/15%, while retained consistency is within
1.01e-11. Full retention still predicts severe congestion that decays too quickly.
Future residual mean is +.15942 at currently severe sensors versus -.02563 at
nonsevere sensors, despite overall bank mean near zero.

The **only repair** conditions residual location on current sensor severity and
the existing calendar regime. It subtracts each complete historical sequence's
own fitted location and adds the current initial-state location, preserving the
intact centered multivariate draw. Coefficients, stability cap, transform, event,
N and graph remain fixed. Inner Brier improves .04770863 to .03537107 and
30-minute speed MAE 2.76225 to 2.64852 mph, passing the saved inner gate.

| Full-retention simulator, N=256 | Raw Brier | Training-calibrated Brier |
|---|---:|---:|
| Original, saved Stage 1 scenarios | .06286549 | .04732007 |
| Residual-location repair | **.03359661** | .03589472 |

The repair's raw gap to A is **+.00714054**, day interval [-.00428797, .01831371],
three-day interval [.00036668, .01859827]. Its point Brier is **26.99% worse**
than A, failing the <=5% relative adequacy cutoff **.02777887**. Calibration
also fails. These are provisional gates, not a statistical noninferiority proof.
Simulator calibration has 128 inner origins/five positives; its onset alarm
panel has only one positive. Both simulators detect 5/5 outer onset events with
4/105 false alarms, but their recall advantage over A has day interval [0,.667].

On identical 127 eligible origins and equal-origin raw-speed masks, 15/30-minute
MAE is **2.09323/2.66293** mph original MC, **1.94707/2.48514** repaired, and
**1.66495/2.26683** persistence. Repair helps but still loses to persistence.
The event/non-event Brier contributions change from .062189/.000677 to
.030696/.002901; event underprediction dominates the original failure. Calibration
does not validate trajectories. A second repair was not attempted after the gate
failure, and no new GPU verification was scientifically warranted.

The initial-state-dependent forcing remains fixed before rollout. The original
pathwise theorem permits dependence between initial state and forcing if coarse/
fine evaluations use exactly the same realized arrays and deviations. No new
numerical certification or repair-specific speedup is claimed.

## 5. Enclosure diagnosis and single tightening

Sixteen prespecified saved origins, N=256, and 0/15/100% retention reproduce the
original coupled fine event counts. Initial variation, D injection, and forcing
injection are propagated separately. At full retention their mean step-six
contributions are **17.04/19.37/21.66**, total radius 58.07, while actual mean
fine/coarse error is 1.11. Wbar+D combines different nodes' worst entries and
has row sums **2.824–4.985**, although true row sums are one.

The one permitted tightening uses the block maximum of
`sum_b w_ib*r_b + abs(sum_b E_ib*z_b)`. It keeps each row together and retains
signed cancellation. It is justified by the same triangle inequality, includes
all error terms, and costs O(N*n*k) per step. Exact-arithmetic correctness is
distinct from empirical FP64 checks; no floating-point certificate was built.

At 15%, mean radius falls **28.208 to 8.544**, versus mean center-threshold
distance 3.893. **Both bounds leave every scenario unresolved.** Oracle rectangles
using already-computed fine minima/maxima still leave 28.83% unresolved at 15%;
they are diagnostic only and provide no cheap guarantee or acceleration.

Across five paired CPU repetitions, original selective is **16.1–23.9% slower**
than fine and tightened selective is **21.9–26.1% slower**. Every coupled decision
agrees; no interval escape was detected. The required >=10% complete-time saving
fails in every repetition. Selective refinement stays disabled in the default
Stage 2 forecasting path. The original implementation/results remain preserved.

## 6. Costs, hardware, budgets, and validation

The existing RunPod reports **NVIDIA RTX 6000 Ada Generation**, 49,140 MiB total,
48,519 MiB free at inspection, driver 570.124.06, and no active compute application.
No alternative GPU or rental was used. Stage 2 computations ran on the local
**Intel i5-10400 (6 cores/12 threads), four threads**, Python 3.8.10 and the
preserved CPU dependency versions. Local timings are not Pod/GPU benchmarks.

Initial complete classifier analysis took 72.23 seconds; final A/B/C fits took
3.09/6.71/25.85 seconds. Their 128-row prediction calls took 1.38/2.00/1.94 ms,
excluding feature construction (separately recorded). These are batch timings,
not measured per-request service latencies. Peak measured process RAM was about
1.49 GB. Complete original/repaired full-retention CPU service costs on 16 paired
origins x five repeats x N=256 averaged **24.02/25.78 ms**, p95 73.49/65.35 ms.
Warm-up .14076 s and bank preparation .09413 s are separately recorded.

The service audit includes regime lookup, RNG, summaries/masks, conditioning,
gathering/location shift, stepping, labels, and binomial intervals. It supersedes
the partial `complete_seconds` repair timer in `simulator_predictions.csv`, which
started after RNG selection. That historical field is retained with this explicit
qualification; use `simulator_cost_audit.csv` for complete costs. Archival I/O,
fitting, output writes and analyst/browsing time are not silently folded into a
per-query kernel number. The complete committed CPU reproduction took 182.474 s.

| Compute accounting | Seconds | GPU-hours |
|---|---:|---:|
| Stage 1 conservative GPU-job total | 668.623716 | .185729 |
| **Stage 2 GPU jobs / CUDA kernel time** | **0 / 0** | **0** |
| **Cumulative GPU-job total** | **668.623716** | **.185729** |

Historical CUDA rollout events total 9.298111 s and did not cover all GPU kernels.
The Stage 2 1,800-second allowance remains unused. The original provisional
24-hour ceiling has 85,731.38 seconds of arithmetic headroom; that is **not an
authorization or recommendation to spend it**. Separate Stage 1/Stage 2 ledgers
are preserved and all reservations are closed. Stage 2 allocated no VRAM, reused
data, and remained below download/cache limits: private raw files occupy 137.62 MB,
processed inputs/caches 69.38 MB, and source documents 6.18 MB on the local host.
The final read-only Pod check found no GPU compute process or experiment worker.
No experiment remains running;
existing RunPod Jupyter/SSH services were left available.

**31 tests passed**, comprising the preserved 21 and ten new checks: exact A
recovery, hidden-identity permutation invariance, unavailable-value poisoning,
inner embargo/window disjointness, tied alarm thresholds, independent Brier
contributions/paired equality, payload accounting, a known conditional-residual
reference, oracle containment/source attribution, exhaustive 256-corner tightening
coverage/dominance, and calibration array compatibility (some share test functions).
The fresh committed reproduction additionally returned zero scientific discrepancy.
No scientific regression or GPU job failed. A pandas indexing deprecation warning
was corrected with an array conversion and prediction-equivalence checks. Two
document acquisitions failed completeness/parse checks; they are provenance limits,
not hidden successful literature reviews.

## 7. Data and novelty limitations; gate decisions

New originating DCRNN code evidence confirms zero-valued measurements are masked
in its loss/evaluation. The HDF still lacks original quality/imputation flags.
Caltrans documents computed speeds and version changes; exact PEMS-BAY processing
lineage is unresolved. Software MIT, public links, a derivative mirror's license,
and underlying measurement rights remain distinct. No actual new restriction on
this local analysis was identified; raw redistribution is not authorized by this
audit. No direct PeMS account requirement was bypassed. Small document reads,
including unsuccessful capped/invalid-PDF attempts, total 13.50 MB; no new data.

Selective threshold refinement and multilevel allocation are established. Equitable
quotients and graph memory are established. The new focused comparison with
[Coogan–Arcak's mixed-monotone box abstraction](https://coogan.ece.gatech.edu/papers/pdf/coogan2015hscc.pdf)
further limits broad enclosure novelty: their reachable-set result already covers
monotone discrete-time systems, including traffic examples. Node aggregation is
a different reduction, but here it has no useful runtime consequence. The closest
2026 equitable-partition and crowd papers still lack a completed full-text audit.
No conditional-variance identity, Gaussian formula or triangle-inequality tightening
is advertised as novel. See STAGE2_DATA_AND_NOVELTY.md for primary links/access records.

| Gate | Outcome |
|---|---|
| Clean matched A baseline and common denominators | **Passed**; saved A reproduced |
| >=5% local-detail Brier improvement, paired support | **Failed point gate; uncertainty inconclusive** for benefit/harm |
| No material detection degradation B/C | Passed on five onset positives; weak support |
| Single residual repair's inner acceptance | **Passed**; Brier and trajectory MAE improve |
| Repaired simulator within 5% of A plus useful capability | **Failed** Brier and trajectory adequacy; no demonstrated distinctive capability |
| Enclosure correctness checks | Passed empirically; exact-arithmetic derivation retained |
| Floating-point certificate and >=10% complete speedup | **Not established / failed**; all scenarios unresolved |
| Data lineage/redistribution and theoretical novelty | **Unresolved**, no unsupported claim enabled |
| Substantive submission-ready negative study | **Not established** by this exposed, single-task panel |

Retain the code and evidence as a bounded research diagnosis. Stop the current
method campaign rather than expand model/sample searches to preserve the initial
narrative. The evidence supports neither the planned positive information result,
a competitive stochastic/theoretical package, nor a broad negative generalization.
**No Stage 3 matrix or execution command is proposed.** A new strategic review
would first need to justify a substantive reframe and its data/validation basis.

## 8. Reproduction and handoff map

README contains setup and commands. `scripts/reproduce_stage2.py --directory NEW_DIR`
copies committed source into a new directory, links the existing private inputs,
disables CUDA and runs the bounded CPU pipeline without overwriting historical
results. Configurations are `stage2_diagnosis.yaml`, `stage2_residual_repair.yaml`
and `stage2_enclosure_tightening.yaml`. Source, inner-date, hardware, download,
reproduction and preservation manifests are under `manifests/stage2/`.

- [STAGE2_DECISIONS.md](STAGE2_DECISIONS.md): saved gates, allowed changes and deviations.
- [STAGE2_MODEL_DIAGNOSTICS.md](STAGE2_MODEL_DIAGNOSTICS.md): full score, calibration, MC and repair evidence.
- [STAGE2_ENCLOSURE_DIAGNOSTICS.md](STAGE2_ENCLOSURE_DIAGNOSTICS.md): derivation, attribution, oracle limits and costs.
- [STAGE2_DATA_AND_NOVELTY.md](STAGE2_DATA_AND_NOVELTY.md): source rights/quality evidence and closest literature.
- [Paired prediction figure](../results/stage2/figures/paired_predictions.pdf) and
  [enclosure/cost figure](../results/stage2/figures/enclosure_width_cost.pdf), with SVG/PNG/alt-text peers.
- `results/stage2/`: compact prediction/metric/timing tables, logs, ledger and checks.

Main-branch commits and push are explicitly authorized. The closing message records
the actual final pushed SHA and remote containment/worktree verification, avoiding
a circular self-hash in this report. No test outcomes or Stage 3 work are included.
