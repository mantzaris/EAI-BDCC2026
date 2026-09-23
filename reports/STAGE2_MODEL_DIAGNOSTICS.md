# Stage 2 model diagnosis and single repair

All findings are **exploratory training/validation**, never test. Stage 1 results
remain unchanged. Decisions were saved in STAGE2_DECISIONS.md before comparisons;
one shared learner setting, one simulator repair, and one calibration family were
used. No GPU job was needed.

## Comparison validity and denominators

Saved rows reproduce the reported Stage 1 Brier scores. All compared outer risks
use the identical 128 time-selected origins, the same 48/325 sensor event,
three consecutive frames in the next six, and the same missing-outcome bounds.
One origin fails future coverage, leaving **127 eligible origins, 20 positives,
20 represented episode groups on 17 days**, across all 36 validation days. Onset
excludes currently active sustained events: **110 origins, five positives from
five groups on five days**. Each eligible origin receives weight one. Full
validation has 10,309 eligible origins, 1,478 positives, 47 groups on 26 days.
These merged target-period groups are not proven statistically independent.

Training has 31,052 eligible origins and 3,130 positives: prevalence
**0.10079866**. Its constant-probability forecast scores **0.13589308** all-time
and 0.04645140 on onset. Outer pilot prevalence is **0.15748031** all-time and
0.04545455 on onset. Thus the strong aggregate Brier is not just a rare-event
always-negative result; ranking, event loss and warning counts also matter.

Source/code inspection found no outer-label fitting, future feature, or split-window
overlap in the reported Stage 1 baselines. Descriptive calibration regressions
were fitted to validation but were **not applied** to their probabilities.
Stage 1's validation-selected alarm threshold was optimistic; Stage 2 replaces it
with a training-only threshold. Upstream PeMS processing/quality flags remain
unverified, so this audit cannot rule out all preprocessing artifacts in the
released recorded process.

Stage 1's heterogeneity baseline A receives all 12 frames of block means/counts,
calendar, and block variance/minimum/maximum/severe fraction. Those extra 768
statistic features are absent from zero-retention MC. Its original Brier advantage
is a valid prediction comparison, **not an identified aggregation information loss**.

## Matched local-information experiment

A/B/C use the same HistGradientBoostingClassifier: 100 iterations, 15 leaves,
L2=10, learning rate .1, minimum leaf 20, no early stopping, seed 20260922.
There was one setting and no hyperparameter search. All use the same 2,588
stride-12 outer-training histories and frozen event/transform design. B adds
49 training-selected local histories as block-mean deviations and masks; C adds
all 325 histories. At zero added locals, the feature matrix is exactly A.
Re-fitted raw A reproduces saved Stage 1 probabilities to **1.11e-16**.

Inner roles are Jan 1–Feb 23, Feb 24–Mar 23 (excluding incomplete Mar 12), and
Mar 24–Apr 19. The first 54 days fit diagnosis models, next 27 diagnose repairs,
and last 27 calibrate models fitted only on earlier days. Ninety-minute embargoes
apply on both sides of inner boundaries and all 18 frames remain in the role.
The original outer-training free speeds/threshold/partition/selector are frozen
design constants. They already summarize all outer-training days; inner diagnostics
are not independent validation of these constants. No new fitted preprocessing
uses inner evaluation data. Histograms/bins are learned on the relevant fit subset.

Final classifiers refit all original outer training for exact A recovery; logistic
maps from chronological out-of-fold probabilities are transported to the refits.
This transport can fail. The classifier calibration block contains 643 sampled
origins, 37 positives (5.75%), versus 15.75% positives in the outer panel.
All validation days were already exposed in Stage 1; no result is an independent
confirmation. No new region, origin selection or event definition was searched.

| Model | Raw Brier | Training-calibrated Brier | All-time PR-AUC | Onset raw Brier |
|---|---:|---:|---:|---:|
| A: aggregate plus heterogeneity | .02645607 | .03384796 | .974766 | .02397217 |
| B: A plus 15% local histories | .03061073 | .03807335 | .961819 | .02446303 |
| C: A plus full local histories | .03046243 | .03645572 | .963947 | .02411244 |

Raw B-minus-A is **+0.00415466**, 95% paired-day interval
[-0.00108586, 0.01038632], a **15.70% deterioration** in point Brier. C-minus-A
is +0.00400637 [-0.00125024, 0.00997672], a 15.14% deterioration. Three-day-block
intervals also contain zero. Neither reaches the predeclared 5% improvement gate.
This is limited evidence of useful local identity for this learner/task, not proof
that local information is universally useless or that its Bayes value is zero.

The information payload is **13,164 / 18,260 / 46,964 bytes** for A/B/C:
FP64 means, four heterogeneity statistics and local histories; int64 counts/IDs;
unpacked uint8 full history masks; six calendar values. Full masks are counted
once even where model features repeat selected masks. This conservative numeric
encoding excludes network framing and compression; all 3,900 history sensor values
are read at the edge. Feature dimensions are 1,158 / 2,334 / 8,958. Additional
local detail has a clear information cost without a measured predictive gain.

## Monte Carlo versus model error

For an unbiased fixed-N mean of conditionally independent Bernoulli events,
expected added squared error from MC is p(1-p)/N <= 1/(4N). For saved N=1,024
rows the average bound is **0.000244140625**. Estimated variance uses
p_hat(1-p_hat)/(N-1), the unbiased sample-variance/N estimator.

| Retention | Observed gap to A, N=1,024 | Estimated MC variance | Worst expected MC bound / gap |
|---|---:|---:|---:|
| 0% | .05785079 | .00002460 | 0.422% |
| 15% | .04891509 | .00003010 | 0.499% |
| 100% | .03679860 | .00003411 | 0.663% |

At N=256 the bound is .0009765625, still only 1.7–2.7% of the original gaps.
These are expected sampling contributions conditional on the frozen fitted bank,
not bounds on realized differences between two observed Brier scores. They are
not applied to calibrated, clipped, dependent or two-level estimators. Independent
sampling from an overlapping historical bank does not make its records independent
observational evidence. More simulation cannot plausibly repair the main gap.

## Trajectory and reconstruction diagnosis on inner training holdout

The initial 54-day model has coefficients (.542815, .270266, .097465, .069455),
sum .98. Its bank contains 1,292 complete 6-by-325 out-of-fold sequences; three
held-day folds stay within those 54 days. The diagnosis uses 128 uniformly selected
origins in the next block, 14 positive, N=256, and full observed histories.

- The inverse transform matches the explicitly clipped speed reference to
  1.42e-14. 14.52% of initial training values hit the lower log-odds clip; none
  hit the upper clip. Mean raw inverse distortion is .13388 mph. Saturation is
  a model limitation, not an implementation error or a physical speed limit.
- Residual-bank mean is .00945 and SD .81158; held-out teacher-forced residual
  mean/SD are -.01828/.88047. Mean absolute off-diagonal spatial correlation is
  .04202; pooled lag-one correlation is -.02053. These summaries do not establish
  independence or adequate operating-regime conditioning.
- Future mean residual at currently severe sensors is **+.15942**, versus
  **-.02563** at nonsevere sensors and +.12510 near the threshold. Calendar-only
  residual location therefore misses state dependence.
- Mean predicted severe fraction decays .03549 to .02501 over six steps while
  observed fractions remain about .039. Currently severe sensors' state bias
  reaches -.49221 at step six. Original 30-minute raw MAE is 2.76225 mph, versus
  persistence 2.35317. Full retention removes initial observation uncertainty;
  this remaining failure is future model error.
- Independently fitting the Gaussian on initial training only gives hidden RMSE
  1.63886/1.33842 at 0/15% retention and nominal-95% coverage .76808/.83139.
  Mean squared standardized errors are 2.99885/2.32769. Exact constraint residuals
  stay below 1.01e-11. Covariance undercoverage and distribution mismatch persist;
  no covariance scaling menu was attempted because full-retention errors remained.

## The one attempted repair and its outcomes

Fit residual location by existing calendar regime and the sensor's current severe/
nonsevere indicator, pooling sensors: 6 regimes x 2 groups x 6 offsets. Minimum
100 positions per group; smaller groups use the regime mean. Subtract each bank
sequence's own fitted location, then add the forecast initial state's location.
The intact centered multivariate sequence is sampled as a unit. No sensor shuffling,
new architecture, extra stability family, or coefficient/threshold change occurs.

Inner raw Brier improves **.04770863 to .03537107** (25.86%); 30-minute MAE
improves 2.76225 to 2.64852 mph. This passes the saved >=5% Brier and <=2% MAE
deterioration gate. Only then were location parameters refit on the original full
training OOF bank and outer repaired forecasts evaluated at the same N=256.

| Full-retention simulator | Raw Brier | Calibrated Brier | Raw all-time PR-AUC | Raw onset Brier |
|---|---:|---:|---:|---:|
| Original, historical paired scenarios | .06286549 | .04732007 | .965183 | .03302404 |
| Residual-location repair | .03359661 | .03589472 | .968443 | .02873216 |

Repair-minus-A raw difference is **+.00714054**, day interval
[-.00428797, .01831371], three-day interval [.00036668, .01859827]. Its point
Brier is **26.99% worse than A**, failing the <=5% relative adequacy cutoff
**.02777887**. Calibrated repair also fails. This is a provisional point gate,
not a statistical noninferiority conclusion. Calibration training has only
128 origins/five positives; its onset subset has one positive. Treat calibration
and alarm transport particularly cautiously.

Repaired outer raw speed MAE averages 1.94129/2.47641 mph across all 128 forecast
origins at 15/30 minutes; these per-origin summaries include the one binary-event
ineligible origin. The matched eligible speed comparison is reported separately
in the handoff, rather than compared with differently masked Stage 1 numbers.
One targeted repair was attempted and retained as a diagnostic. No second repair
was added after its outer adequacy failure.

## Calibration, warnings, and loss decomposition

A/B/C training onset thresholds .0555951/.0477270/.0487408 achieve 29/597=4.858%
inner false alarms. Outer onset recall is **4/5** for every classifier and false
alarms are **4/105=3.810%**. Their paired recall differences are exactly zero
on these five positives; bootstrap equality is not evidence of precise population
recall. Simulators detect 5/5 with the same 4/105 false alarms, but their inner
alarm panel has only one positive. Simulator-minus-A recall interval is [0,.667].
No warning lead-time claim is made from this sparse panel.

All-time event/non-event Brier contributions are .021556/.004900 for A,
.028035/.002575 for B, .024105/.006358 for C, .062189/.000677 for original MC,
and .030696/.002901 for the repair. The simulator gap is dominated by event
underprediction. Mean raw probabilities are .13768/.12875/.13561 for A/B/C,
.07031 original MC and .11519 repaired MC, against prevalence .15748.
Quantiles and reliability bins are saved for every raw/calibrated model.
Training calibration worsens A/B/C and repaired outer Brier; it improves original
MC but does not make it competitive. It validates neither trajectories nor bounds.

The fitted forcing now depends on the initial state but is fixed before rollout.
The old pathwise theorem does not require independence between them; it applies
only if coarse/fine evaluations share the **same realized repaired forcing** and
bound its actual deviations. No floating-point guarantee is inherited.

Compact evidence: `results/stage2/{comparison_audit,matched_metrics,matched_pairs,
repair_results,simulator_pairs,development_support}.json`, prediction CSVs,
`predictive_metrics.csv`, and the model/trajectory diagnostic tables. New final
service timings supersede the partial repair timer, as documented in the handoff.
