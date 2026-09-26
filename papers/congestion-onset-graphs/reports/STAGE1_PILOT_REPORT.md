# Stage 1 feasibility pilot

Final GPU-tested source: `128f8f15257c51677e197ec2493ddc4c0d098820`.
Date: September 22, 2026. Data: real PEMS-BAY **validation**, never test.
The complete final panel is `results/stage1_pilot/`; its successful `run.json`
records the source/config/input hashes. The earlier implementation and its complete
panel are preserved separately under `results/stage1_pilot_initial/`.

## Executed matrix and model

All **128** uniformly time-selected validation origins completed at retained
fractions 0%, 15% (49/325 sensors), and 100%, with N=256 and N=1,024. Each cell
used the same fitted model. One 16-block spatial quotient and the full 325-node
graph were used. There were 491,520 base fine scenario evaluations across the
matrix; the smaller N uses a prefix of the larger draw, so these are not all
distinct independent scenarios across experimental conditions. Fine, empirical
selective, and conservative fallback labels agree scenario by scenario.

Two-level MC ran at 15% retention for both N-based cost targets. Its independent
allocation pilots comprised 16,384 draws; estimation used 43,352 cheap samples
and 59,060 correction samples in total. Within a correction, the initial state
and full multivariate residual sequence are identical at both resolutions.
No scenario was resampled because its label or runtime was inconvenient.

The CPU training fit took 16.07 seconds, using 2,588 training history windows and
5,174 out-of-fold multivariate residual sequences from three training-day folds.
The four fitted coefficients are (0.5528816584, 0.2703355470, 0.0835082615,
0.0732745330), summing to 0.98. The seasonal intercept uses six known-calendar
features per sensor. The Gaussian has rank 16 plus a positive diagonal; exact
valid observations have zero measurement noise. A 1e-6 prior diagonal floor is
explicit, not hidden observation regularization.

One-step constrained fitting was implemented; the optional short-rollout loss
and relaxed 1.05 stability family were not evaluated. These are limitations of
the fitted model and possible bounded repairs, not unexplained changes to the
event definition. No GNN, transformer, compilation, test campaign, large fine-MC
reference, or additional retention/partition sweep was run.

## Information, reconstruction, and prediction

The panel contains 127 coverage-eligible origins, 20 positive targets on 17 days,
and all 36 validation days. The onset subset contains 110 origins and only five
positive targets on five days. Reported intervals resample complete days, with
1,000 CPU replicates. These are development estimates, not confirmatory tests.

| Retained locals | N | Event Brier | 95% day-bootstrap interval | Onset Brier |
|---|---:|---:|---|---:|
| 0% | 256 | 0.083843 | [0.046992, 0.121542] | 0.041372 |
| 0% | 1,024 | 0.084307 | [0.047602, 0.121755] | 0.041843 |
| 15% | 256 | 0.075232 | [0.040585, 0.110664] | 0.034658 |
| 15% | 1,024 | 0.075371 | [0.041214, 0.110367] | 0.035284 |
| 100% | 256 | 0.062865 | [0.034434, 0.092301] | 0.033024 |
| 100% | 1,024 | 0.063255 | [0.034897, 0.092533] | 0.033122 |

At N=1,024, the paired Brier difference for 15%-minus-0% retention is -0.008936
with interval [-0.025319, 0.004638]. Full-minus-0% is -0.021052 with interval
[-0.040640, -0.004389]. Full retention helps this fitted model on this development
panel; the 15% improvement is uncertain. Increasing N from 256 to 1,024 changed
Brier by only +0.00014 to +0.00046, with all paired intervals containing zero.
These fluctuations do not mean larger N systematically worsens forecasts.

The aggregate baselines are stronger:

| Training-fitted baseline | Brier | 95% day-bootstrap interval | Onset Brier |
|---|---:|---|---:|
| Seasonal/persistence features | 0.036657 | [0.019804, 0.054008] | 0.021945 |
| Aggregate-history logistic model | 0.036992 | [0.018396, 0.056338] | 0.025069 |
| Aggregate history + local variance/extremes/severe fraction | 0.026456 | [0.007458, 0.049403] | 0.023972 |

Even full-information MC minus the heterogeneity baseline has a positive Brier
difference of 0.036799, interval [0.016554, 0.059394]. This rejects a claim that
the present stochastic predictor is competitive. The augmented baseline receives
additional transformed local statistics; it is not an equal-information 0%
comparison. No equal-transmitted-byte model comparison was established.

Hidden-history RMSE decreases from **1.3623** to **1.1909** log-odds units at 15%
retention. Empirical 50/80/95% coverage changes from **42.83/69.83/86.88%** to
**48.22/75.13/90.07%**. Coverage remains low, especially in the tails. Full
retention has no hidden valid values, so its hidden-error metric is undefined,
not zero evidence of perfect forecasting. A separate CPU audit finds mean
absolute cross-sensor hidden-error correlation 0.1473 at 0% and 0.0944 at 15%.
The maximum retained-constraint residual is 1.19e-11. Spatial block error
summaries are saved in `results/tables/reconstruction_dependence.json`.

At N=1,024, 15/30-minute raw speed MAE is 3.227/3.242 mph for 0%,
2.709/2.971 for 15%, and 2.088/2.657 for full retention. On the same eligible
origins, raw full-sensor persistence scores 1.665/2.267 mph. Both raw and
identically reference-capped target comparisons are retained; the speed cap is a
model transform, not a physical limit. The model remains weaker than persistence.

Reliability bins and regularized calibration intercept/slope diagnostics are
saved, without applying calibration to reported simulator probabilities. The
N=1,024 calibration intercepts range from 2.70 to 3.90, consistent with substantial
underprediction. Fine-MC PR-AUC ranges from 0.913 to 0.971 against prevalence
0.1575; good ranking has not produced good probability calibration. Validation
warning thresholds achieve about 5.7% false alarms and detect five of five onset
positives, but are selected/described on the same sparse validation subset.
This is not a credible held-out recall or warning-lead-time claim.

## Enclosures and estimation

Every scenario remained unresolved: **unresolved fraction 1.000** in every
retention/N cell. At N=1,024, mean radii are 29.12, 28.26, and 28.05 log-odds
units, versus actual mean fine/coarse discrepancies 1.156, 1.123, and 1.148.
No enclosure violation was detected. Coarse point labels agree with fine labels
about 93.0–94.3%, but the bound is too loose to exploit that agreement.

The conservative mode refines all scenarios because numerical certification is
unverified; the empirical mode also refined all scenarios because of bound width.
Thus **certification saved no complete runtime**. A rounding proof alone would
not fix the observed ambiguity. Fine and selective MC have the same Bernoulli
variance at equal N; no variance-reduction claim is made for selection.

Two-level MC at the N=1,024 cost target has Brier 0.075327. Mean counts are
N0=264.2 and N1=368.2; the allocation is discrete, floored, capped, and derived
from independent 64-draw pilots. Raw estimates remained in [0,1] in this panel,
but both raw and clipped fields are saved. The exactly enumerable unit check
includes out-of-range finite estimates and verifies the unbiased mean.

Two-level estimated simulation variance averages about 5.6e-5 at that cost target,
versus about 3.0e-5 for 15% fine MC with 1,024 draws. Two-level complete estimation
averages 94.8 ms, or **110.7 ms including its allocation pilot**. Cost targets were
not always matched exactly; this is not a demonstrated equal-time-to-error win.
No high-N truth reference or independent repeated real-panel MC study was run.
Hoeffding union intervals remain valid when empirical variance is zero; fine MC
uses exact binomial intervals with positive zero-event upper bounds.

## Hardware, timings, and compute ledger

The GPU is **NVIDIA RTX 6000 Ada Generation**, 49,140 MiB reported by nvidia-smi;
driver 570.124.06, PyTorch 2.8.0+cu128, CUDA runtime 12.8, Python 3.12.3. This is
neither RTX A6000 nor RTX PRO 6000. The host is AMD EPYC 75F3; the Pod quota is
13.6 CPU equivalents and 61,999,996,928 bytes RAM. Benchmarks use four CPU threads.
Host-wide 503 GiB RAM/128 logical CPUs are not the Pod's resource entitlement.

| 15% retention, N=1,024 | Mean computation time | p95 |
|---|---:|---:|
| Vectorized dense CPU, in the paired pilot | 210.0 ms | 246.0 ms |
| Hybrid CPU conditioning + eager GPU fine | 142.1 ms | 160.7 ms |
| Empirical selective, all unresolved | 167.8 ms | 188.0 ms |
| Conservative numerical fallback | 161.1 ms | 183.3 ms |

The GPU fine row includes about 5.08 ms conditioning setup, 121.22 ms sampling,
2.78 ms residual gathering, 2.29 ms fine stepping, 8.64 ms transfers, and event/
interval reduction overhead. Selective computation additionally pays about
21.56 ms enclosure/reductions and 3.21 ms compaction. Totals include sensor-history
summaries, constraints, reconstruction, full forcing preparation, initial
reductions, event labels, and intervals. Shared preparation is measured once and
charged to each compared method. They start from an in-memory transformed history
and resident fitted bank; raw archival I/O, source transformation, offline fitting,
diagnostic checks, and result-file writes are reported separately at job level.

The independent same-Pod CPU-only dense/CSR panel checks all 128 identical saved
scenarios at 15%, N=1,024, alternating backend order. Dense stepping averages
30.45 ms and CSR 37.00 ms; total times are 230.8 and 237.4 ms respectively.
There are no event disagreements and maximum state discrepancy is 5.33e-15.
Dense BLAS is a competent CPU choice here. Differences between this separate
timing panel and paired CPU timings show host allocation/cache/order variability;
do not extrapolate a universal GPU crossover from this single device/graph panel.

Full retention uses the deterministic conditional law when all coordinates are
observed, avoiding unnecessary Gaussian generation. Its final complete N=1,024
GPU time is **26.1 ms**, compared with 248.8 ms before this repair. Its information
payload is larger. Numeric array payloads are 7,020, 12,116, and 40,820 bytes at
0/15/100%, including counts, masks, IDs, and calendar; these are actual array
sizes, not serialized network packets. All 3,900 history values are read for
summaries regardless of retention. No sensor-acquisition saving is claimed.

The final pilot job used **283.8766 s** including interpreter setup; its internal
wall measurement is 282.5970 s, with 0.0892 s warm-up separately recorded.
Peak process RSS was 1.605 GB, peak allocated GPU memory 92,702,208 bytes and peak
reserved GPU memory 123,731,968 bytes. CUDA events around rollouts measured 4.4421 s.
Transfers/casts/setup remain in wall costs; this is not a complete GPU-kernel
profiler trace. Compilation was not attempted because these measurements do not
justify its cost against predominantly CPU conditioning work.

The append-only ledger charges **668.6237 seconds = 0.185729 GPU-hours** across
both pilots, both GPU audits, and a 30-second conservative discovery allowance.
Total CUDA rollout-event time is **9.2981 seconds** across those runs. Every
reservation is closed, every GPU job exited zero, and no experiment remains
running. CPU fitting, summaries, and CPU-only audits do not consume GPU-job time.
Pod idle allocation and provider billing are different quantities and are not
inferred from this ledger. The 7,200-second Stage 1 cap was not approached.

## Reproducible outputs and decision

Figures [information/prediction](../results/figures/information_prediction.pdf)
and [enclosure/cost](../results/figures/enclosure_cost.pdf) have SVG and PNG peers
and alt text. They are produced entirely from actual numerical outputs by
`scripts/build_pilot_figures.py`. Metric detail, paired day intervals, reconstruction,
allocation, timing components, scenario hashes, and precision audits are saved
in compact CSV/JSON files. No test result, synthetic substitute, or fabricated
performance number is presented.

**Simplify.** Retained detail improves this working model, but a stronger
aggregate baseline and undercoverage limit the scientific claim. More scenarios
do not resolve the model's prediction gap. Stop the selective-acceleration branch
in its current form. Any Stage 2 should first address data-quality/terms and
theory novelty gates, then one bounded model/calibration repair, before a full
campaign is reconsidered.
