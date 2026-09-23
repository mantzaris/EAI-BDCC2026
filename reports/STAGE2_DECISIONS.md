# Stage 2 decisions, saved before new model comparisons

Opened 2026-09-23 UTC (2026-09-22 America/New_York). Work directly on main;
starting delivery 3f9e2e1308235a75bf0a1d84cbe2e6c50eaa97bd, clean tree,
verified origin mantzaris/EAI-BDCC2026. Fetch/fast-forward found no subsequent
changes. No applicable AGENTS.md was found. Preserve every Stage 1 artifact.
This record and configs/stage2_diagnosis.yaml precede new comparisons. Append
decisions and deviations with their evidence; do not rewrite unfavorable results.

## Evidence and scope

Read the complete research plan, README, all four Stage 1 reports, configurations,
source implementations, saved prediction/metric schemas, and compute records.
Stage 1 used 128 time-selected validation origins, 127 eligible, 20 positives
on 17 days; the onset subset has 110 origins and five positives. N=1,024 Brier
is 0.08430686 / 0.07537116 / 0.06325467 at 0/15/100% local retention. The
aggregate-plus-heterogeneity classifier scores 0.0264561. These rounded values
will be recomputed from saved rows before interpretation. Its variance, extrema,
and severe-fraction histories supply information absent from the 0% simulator.
The original comparison mixes learner and information effects.

All 36 validation days informed Stage 1 event support, aggregate model evaluation,
and pilot decisions. No validation block will be called untouched confirmation.
Reuse exactly the saved 128 origins for primary comparisons, without outcome
selection. All results are exploratory validation. Test measurement reads,
test scores, a new dataset, Stage 3, and the full study are prohibited.

Stage 1 charged 668.6237159054726 GPU-job seconds, with 9.298111127018917 seconds
of CUDA rollout events (not a complete kernel profiler). Stage 2 permits at most
1,800 additional GPU-job seconds including warm-up, failures, and retries. A
separate append-only ledger retains that stage cap and reconciles cumulative
usage against 86,400 seconds. No budget resets. Begin with CPU diagnostics;
launch GPU work only for a remaining question after correctness and projection
checks. The existing RTX 6000 Ada reports 49,140 MiB, 48,519 MiB free and driver
570.124.06; no compute application was active at inspection. No resources rented.
Retain 12 GB download, 20 GB processed/cache, and 32 GB active VRAM limits.

## Primary predictive comparison, frozen choices

A is the Stage 1 heterogeneity feature set and histogram gradient-boosted learner.
B adds the frozen training-selected 49/325 local histories as deviations from
their own block means, plus local masks. C adds all 325 local histories/masks.
At zero added sensors the feature function returns A exactly. The final raw A
must reproduce the saved Stage 1 predictions within CSV roundoff; investigate
any failure before reporting local-information effects.

Use one shared prespecified setting (no search): 100 boosting iterations, 15
leaves, L2=10, learning rate 0.1, min leaf size 20, seed 20260922, no early
stopping. This matches Stage 1's effective settings. All arms have the same
training origins (the original stride-12 rule), dates, target, masks, fitting
allowance, calendar, and calibration procedure. Full information is diagnostic,
not a new architecture. No random sensor-set search or chosen winning regions.

Split the 108 original training days chronologically at days 54 and 81. First
54 days fit initial diagnostics; next 27 diagnose/select any permitted repair;
last 27 provide out-of-fold calibration/alarm data from models fitted only on
earlier days. Apply 90-minute embargo on both sides of each inner boundary and
require entire 12+6 windows within their role. Save actual indices/dates.
Final A/B/C refit the same original outer-training origins to reproduce A;
calibration maps learned from chronological out-of-fold predictions are transported
to these refits. Report this transport limitation. No new preprocessing is fitted
on inner held-out values. The original free speeds, event threshold, partition,
and fixed selector are frozen outer-training design constants; their earlier use
of all training days is disclosed, and inner diagnostics are not independent
validation of those constants.

Raw all-time Brier on identical eligible outer origins is the primary measure.
One regularized logistic calibration of clipped logits (clip 1e-5, C=1) is a
separately labeled diagnostic for each arm, fitted on the last inner block only.
Never pick raw versus calibrated after observing outer performance. Fit alarm
thresholds on inner onset-eligible non-events to maximize recall subject to
empirical false-alarm rate <=5%, with deterministic treatment of ties; freeze
them for outer onset evaluation. Report all-time detection separately.

Practically interesting local detail requires >=5% relative Brier reduction
versus A, paired day/block uncertainty supporting a reduction, and no material
event-detection degradation (predeclared point recall drop >5 percentage points).
Report 2,000 paired bootstrap replicates for whole days and moving three-day
blocks; report exact event counts and sparse-support limitations. A point gate
with uncertain intervals is provisional, not confirmation. Full-local failure
supports only a task/model-specific limited-evidence finding.

Count numeric/transmitted array bytes for summaries, counts, full masks,
calendar, selected IDs and histories, including A's additional statistics.
All sensors are read at the edge; no acquisition saving is claimed.

## Diagnosis and bounded repair rules

Reconcile saved scores, eligibility, onset conventions, features, label construction,
and chronological isolation. Report constant training-prevalence risk, event and
non-event loss contributions, probability distributions, reliability and episodes.
For each raw fine-MC mean use its actual N to average 1/(4N), and the unbiased
sample-variance/N estimate where possible. These bound/estimate expected sampling
contribution; they do not bound a realized difference of observed Brier scores.
Do not apply them to calibration, clipping or two-level estimates.

Inspect saturation/inversion, conditional covariance and exact constraints,
teacher-forced residual means/variance/dependence, calendar regimes, and accumulated
full-retention rollout drift. Select at most two small repairs using the initial
inner fit and diagnosis block; append the defect, exact change and selection rule
before outer repaired evaluation. Training-only probability recalibration remains
a diagnostic and cannot establish trajectory validity. Do not automatically
increase N, relax stability, refit covariance or add a speculative repair menu.

A stochastic candidate must have raw or explicitly calibrated Brier <=1.05*A
on the matched panel and a concrete paper-relevant capability beyond classification.
The calibrated gate is distinct from trajectory adequacy; it is provisional,
not a noninferiority proof. If inner repair fails, report it and finish other work.

## Enclosure and final decision rules

Fine MC is the default Stage 2 forecasting path. Selective refinement is disabled;
preserve the original code and negative results. On 16 uniformly selected saved
origins with 256 coupled scenarios, decompose initial variation, D, forcing and
propagation contributions; compare radius to threshold distance, actual error,
and sustained-fraction intervals. Any fine-state-assisted analysis is oracle-only.
Never remove a nonzero term and call it a certificate.

Allow at most one inexpensive, mathematically justified adjustment only if the
diagnosis gives a specific reason. Re-enabling selection requires coupled label
identity, a defensible numerical qualification, and >=10% complete runtime saving
over five repeated paired timings beyond noise. Fewer unresolved samples alone
is insufficient. Stop bound work if even an oracle-tight block radius is useless.

Update originating-data processing/terms and nearest selective/graph-abstraction
literature using primary evidence; no new registration or contact. Software MIT,
public access, mirror declarations and underlying measurement rights are distinct.
Do not claim a generic conditional-variance identity as novelty.

Assess (1) useful matched retained information, (2) competitive stochastic prediction
with meaningful theory/computation, and (3) a substantive bounded negative study.
Recommend one justified continue/simplify/stop outcome. Propose Stage 3 only if
evidence supports it, with a narrow budget inside the cumulative provisional
24-hour ceiling. Execute none of Stage 3. Deliver reports, compact results,
figures, tests and provenance on main and verify the authorized push.

## Subsequent decisions and deviations

None at initial save. New records will be appended here with evidence.
