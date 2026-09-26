# Stage 1 handoff: When Averages Hide Congestion

**Decision: simplify before any further campaign.** The reproducible real-data
pilot completed, but selective refinement saved no runtime and the stochastic
predictor lost to the aggregate baselines. Retaining more local detail improved
the working model more than increasing its scenario count; that does not yet
establish a competitive forecasting method or a new theorem. Stage 2 was not run.

This document is the self-contained handoff for another research collaborator.
All findings below are from training/validation development work, **not test-set
validation**. The repository is `mantzaris/EAI-BDCC2026`, worked directly on `main`.

## 1. Starting state, delivered implementation, and execution

Work started September 22, 2026 at **23:01:31 UTC** (19:01:31 America/New_York).
Starting commit: **`c0a25bdeecd86b24729f6fa8625dfe25af02ca22`**. The working tree
was clean, contained only LICENSE, and had no applicable AGENTS.md or README.
Origin was verified as `https://www.github.com/mantzaris/EAI-BDCC2026`; fetching
showed local and remote main identical. No feature branch, PR, stash, reset,
history rewrite, or unrelated-file deletion was used. There were no pre-existing
user changes to preserve. The complete supplied plan was found in Downloads
and copied unchanged to `research_plan/EAI_BDCC_2026_Research_Plan.md`.

The `traffic_risk_twins` package and CLI implement:

- Source acquisition and manifests, source HDF axes/measurement separation,
  quality masks, complete-day splitting, and embargo/window checks.
- Fixed spatial block means/counts/masks/calendar, training-only nested local
  selection, and explicit all-sensor history-read accounting.
- Calendar-conditioned rank-16-plus-diagonal Gaussian histories and independent
  Matheron draws. Redundant exact constraints are removed analytically; missing
  observations are omitted. Fully observed states use their deterministic law.
- The plan's two-lag nonnegative graph recurrence, constrained CPU fit, seasonal
  forcing, intact multivariate out-of-fold residual banks, NumPy/CSR references,
  and eager CUDA fine evaluation.
- Quotient weights Wbar, structural defect D, initial/forcing radii, the stated
  enclosure recurrence, sustained-event bounds, and coupled fine fallback.
- Fixed-N fine MC, empirical selective MC, conservative numerical fallback, and
  independent two-level allocation/cheap/correction samples with shared randomness
  within each correction. Raw estimates and separately clipped probabilities are
  distinguished, with nondegenerate zero-event uncertainty.
- Small seasonal/persistence, aggregate-history, and heterogeneity-augmented
  baselines; day-cluster score intervals; reconstruction/dependence diagnostics;
  scientific plotting; and an append-only timeout/reservation compute ledger.

The two-cell queue calculation and a conservation-based 20-cell CTM are separate
correctness checks; no theorem for the predictive recurrence is claimed for CTM.
There is no large GNN/transformer, full campaign, paper draft, paid-resource
creation, or background experiment.

Execution used CPU-only fitting (16.07 s), local and Pod tests, two complete
128-origin GPU pilots, two GPU correctness audits, and further CPU-only analyses.
The second pilot corrects unnecessary work found in the first: drawing Gaussian
histories when all values are already known, and constructing unused radii for
two-level cheap samples. Confidence-interval reduction is also included in final
service timings. Both pilots remain available and both consume the same budget.

## 2. Source and artifact provenance

| Role | Commit / record |
|---|---|
| Starting repository | `c0a25bdeecd86b24729f6fa8625dfe25af02ca22` |
| Initial implementation and first GPU pilot | `a2cc0400b71a71f06a6fde17270de8aa777a0f3e` |
| **Final GPU-tested source** | **`128f8f15257c51677e197ec2493ddc4c0d098820`** |
| Final pilot | `results/stage1_pilot/run.json` and CSV peers |
| Preserved initial pilot | `results/stage1_pilot_initial/` |
| Source content verification | `manifests/gpu_source_files.json`, `source_integrity_verification.json`: 27 files checked, zero mismatches |
| Persistent compute record | `results/compute_ledger.jsonl`, summarized in `compute_summary.json` |

The later delivery commit adds CPU analysis scripts, environment/provenance
records, compact results, figures, and these reports. It does not change the
GPU-tested core. Those CPU analysis paths were executed and checked separately;
they are not misrepresented as part of the earlier GPU commit. The final delivery
SHA is provided in the closing message, not embedded circularly in its own commit.

The frozen GPU configuration SHA-256 is
`48830e12a13e1ea4ed397fd7740682cac00acd33827425e7f4c1c0f266eda426`.
The private fitted-input archive SHA-256 is
`65afcc26e5c3ca971557167f9de1252533c7f9acb20fe417671898dadc202ea3`.
Its array-level hashes, dimensions, transformations, exact origins, retained
sensor indices, and training folds are in `manifests/derived_data.json`.
The actual run explicitly used `--origin-limit 128`; the early `pilot_origins: 16`
metadata field is unused by the driver. `max_validation_origins: 128` is enforced.

## 3. Data, terms, splits, and event support

The primary data were retrieved from the [originating DCRNN research release](https://github.com/liyaguang/DCRNN),
not a synthetic substitute. `pems-bay.h5` is **135,930,936 bytes**, SHA-256
`65d69fb0a2323dba9867179eb7af47c8b814186bc459ff0a4937d21614153c8f`.
Its 52,116 five-minute frames contain 325 speed sensors, January 1–June 30, 2017.
The archive has no timezone metadata. A gap after March 12 01:55 omits 12 nominal
frames; that incomplete date is excluded. There are no duplicate timestamps.
Speed units are mph; no flow data were relabeled as speed or incidents.

The source graph order equals the HDF sensor axis, and coordinates are reindexed
explicitly. There are 2,694 positive source entries, including 325 self loops;
removing those leaves **2,369 directed edges**. Twelve empty rows receive identity
fallbacks, then rows are normalized. Neighborhood direction is a predictive
convention, not verified causal road propagation.

The originating code's MIT license was not taken as a measurement license.
The [Zenodo derivative API](https://zenodo.org/api/records/5724362) explicitly
declares CC BY 4.0. General [Caltrans terms](https://dot.ca.gov/conditions-of-use)
also provide public-information context, but the PeMS-specific terms link did
not yield retrievable dataset terms. Conclusive originating measurement rights
remain unresolved. The bounded local pilot uses the authors' public research
release; raw data, coordinates, adjacency, and residual/model archives are **not
redistributed in Git**. Only retrieval instructions, hashes, and compact results
are delivered. LargeST metadata/CC BY-NC terms were inspected as the single flow
fallback, but no annual LargeST file was downloaded or evaluated.

Complete days are split 60/20/20, with all 12-history/6-outcome frames contained
within their split. Each boundary has a 90-minute embargo on both sides.

| Split | Dates | Complete days | Frames after embargo | Forecast origins |
|---|---|---:|---:|---:|
| Training | Jan 1–Apr 19, excluding Mar 12 | 108 | 31,086 | 31,052 |
| Validation | Apr 20–May 25 | 36 | 10,332 | 10,315 |
| Test, timestamp indexing only | May 26–Jun 30 | 36 | 10,350 | 10,333 |

Training has no zero, negative, or nonfinite values in retained frames, and six
identical value vectors at distinct times. Validation has 304 zeros, no negative/
nonfinite values, and no duplicate value vectors. Because neither zero semantics
nor upstream imputation flags are conclusively supplied, zeros are unknown event
indicators. Future lower/upper labels treat unknown indicators as 0/1; no future
label is imputed. At least 95% coverage and matching bounds are required. Six
validation origins fail coverage; none has ambiguous binary bounds. Test value
frequencies, missingness, duplicates, and outcomes remain uninspected.

Training 85th-percentile reference speeds define the clipped log-odds transform.
The frozen event requires at least **48/325 sensors** at state >=0 for three
consecutive future frames within the 30-minute horizon. Training supplies the
90th-percentile severity threshold with the prescribed 10% floor. Event support
is **116 training episode groups on 73 event days**, and **47 validation groups
on 26 event days**. The plan's support gate is met, so the region alternative was
not invoked. Overlapping origins and same-day episodes are not treated as
independent observations; uncertainty resamples whole days.

The saved 128-origin rule uses uniformly spaced validation indices without
outcome filtering. There are 127 scorable origins, 20 positives on 17 days, and
only five positives in the 110-origin onset subset. These counts constrain every
predictive interpretation. The target is the released recorded-speed process;
upstream-imputed values cannot be identified without original quality flags.

## 4. Theory audit and correctness findings

The graph enclosure was independently re-derived through the structural residual
E = WP - P Wbar. Its blockwise absolute maxima are D. Writing x=Pz+eta yields
Wx-PWbar*z = W*eta+E*z; nonnegative W bounds the first term by (Wbar+D)r and the
second by D|z|. ReLU's Lipschitz constant 1 and nonnegative coefficients give the
stated radius recurrence. Finite initial/forcing deviations initialize induction.
Weighted counts and the max-of-three-frame-min functional are monotone; equality
belongs to an event. Singletons recover W exactly with zero D and radii.
No mathematical correction to the plan's recurrence was required.

The exact-arithmetic proof does **not** certify floating-point reductions and
thresholds. No complete outward/rounding proof was implemented. The conservative
path therefore routes every sample to its identical fine floating-point reference;
the empirical selective path has no numerical-certification claim. A deliberately
constructed FP32/FP64 cancellation example produces different event labels.

Selective refinement is already established by
[Elfverson et al.](https://arxiv.org/html/1408.6856v1), as is its extension in
[adaptive subset simulation](https://arxiv.org/html/2208.05392v2).
[Equitable quotient dynamics](https://arxiv.org/html/1608.04283v2),
[clustered physical-network reduction](https://arxiv.org/abs/1403.4789), and
[graph memory closures](https://arxiv.org/html/2405.09324v2) are close established
work. A 2026 nonlinear equitable-partition paper exposes a related structural
residual in publisher search extracts; full access and a complete comparison
remain outstanding, as does the full Sensors crowd coarse-to-fine paper.
Gaussian conditioning, Matheron's identity, MC, multilevel allocation, and the
conditional Brier decomposition are background. **No first-of-its-kind claim is
supported.** See `STAGE1_PROOF_AUDIT.md` for assumptions, comparisons, and gaps.

Initial checks: 19 tests passed locally and on the Pod. After the two performance
repairs: **21 tests passed locally and 21 on the Pod**. The suite checks exact
Fraction arithmetic in 243 boundary cases; 300 fresh graphs with five scenarios
each; heterogeneous D counterexamples; singleton/equitable limits; 80,000 Gaussian
draws against analytic moments; retained/missing/full observations; complete-day
and poisoned-test access; fixed selection; scenario prefixes; zero-event bounds;
all 256 draw combinations in an enumerable two-level problem; CTM conservation
over 200 steps including external queues; and ledger failures/restarts.
Each GPU audit passed 40 graphs/1,280 coupled scenarios. The final real pilot
detected no FP64 CPU/GPU label discrepancy or enclosure violation. The 6,144
scenario FP32 real-data audit found no flips; the constructed flip remains a
documented numerical limitation. No unexpected test or GPU job failed.

## 5. Measured findings

At N=1,024, Brier scores are **0.08431, 0.07537, 0.06325** for 0/15/100% retention.
Paired 15%-minus-0% difference is -0.00894, day-bootstrap 95% interval
[-0.02532, 0.00464]; full-minus-0% is -0.02105 [-0.04064, -0.00439]. Increasing
N from 256 to 1,024 changes scores by less than 0.0005 in magnitude, with intervals
containing zero. Retained detail appears useful within this fitted model;
evidence for the practical 15% setting is uncertain.

But seasonal/persistence, aggregate-history, and aggregate-plus-heterogeneity
baselines score **0.03666, 0.03699, and 0.02646**. Even full-retention MC is worse
than the augmented baseline by 0.03680 [0.01655, 0.05939]. Its 15/30-minute raw
speed MAE is 2.088/2.657 mph, versus matched raw persistence at 1.665/2.267 mph.
The simulation is not competitive. Calibration diagnostics show substantial
underprediction despite useful ranking; no fitted calibration was applied to
reported simulator risks.

Hidden-history RMSE improves from 1.3623 to 1.1909 log-odds units with 15%
retention. Nominal 95% coverage is only 86.88% and 90.07%. Residual spatial
dependence remains. Thus information loss, conditional-model error, numerical
approximation, and MC noise must stay distinct. Mean estimated MC variance at
15%, N=1,024 is only about 3.0e-5; its reduction cannot explain away the roughly
0.049 Brier gap to the augmented baseline.

**Every coarse scenario was unresolved.** Mean radii are around 28–29 log odds,
against actual mean errors around 1.1. Fine/coarse point-event agreement near
94% does not make those loose bounds useful. At 15%, N=1,024, complete hybrid
fine computation averages **142.1 ms**, empirical selection **167.8 ms**, and
conservative fallback **161.1 ms**. The paired four-thread dense CPU averages
210.0 ms. A separate same-Pod dense/CSR audit confirms dense is faster here:
230.8 versus 237.4 ms complete time, with no label disagreements. Host timing
variability and CPU-dominated conditioning preclude a broad GPU speedup claim.

Two-level MC averages 94.8 ms at the larger cost target, **110.7 ms including
allocation**, with mean N0/N1=264/368 and estimated variance about 5.6e-5.
Its Brier is 0.07533. These are different sample allocations and imperfectly
matched actual costs; an equal-time-to-error win was not established. Raw
estimates and Hoeffding intervals remain separate from probability clipping.

The optimized full-observation conditional law makes full-retention N=1,024
computation 26.1 ms, but its numeric payload is larger: 40,820 bytes versus 7,020
at 0% and 12,116 at 15%. These include array masks/counts/IDs/calendar, not network
framing. Every representation still reads all 3,900 history values for summaries.

## 6. Hardware, resource use, and stopping state

The verified device is **NVIDIA RTX 6000 Ada Generation**, 49,140 MiB reported
VRAM, driver 570.124.06, PyTorch 2.8.0+cu128/CUDA 12.8. This is not RTX A6000 or
RTX PRO 6000. The host CPU is AMD EPYC 75F3; actual Pod quotas are 13.6 CPU
equivalents and approximately 62 GB RAM. Benchmarks use four threads. Final peak
RSS was 1.605 GB, GPU allocated memory 92.7 MB, reserved memory 123.7 MB.

The final GPU pilot used 283.8766 charged seconds (282.5970 internal wall seconds),
including 0.0892 s measured warm-up. **Cumulative GPU-job usage is 668.6237 seconds
= 0.185729 hours**, including both pilots, both audits, and a conservative
30-second discovery allowance. Total CUDA rollout-event time is **9.2981 seconds**.
Transfer/cast/setup costs are included in charged wall time; CUDA event timing
is not presented as a complete kernel profiler trace. No compilation was tried.
All ledger reservations are closed; no experiment remains running. Existing
Jupyter/SSH services and the Pod remain available. Allocation billing is separate
from GPU-job time and is not estimated here.

Raw measurements total 137.6 MB; the private processed input archive is 46.3 MB;
dependency downloads were about 80.5 MB by rounded pip logs; documentation is
under 1 MB; the isolated Pod environment is about 369 MB. The 12 GB download,
20 GB processed/cache, 32 GB active VRAM, and 7,200 s GPU-job limits were respected.
No raw data, secrets, environments, or model banks are committed.

## 7. Limits and omissions

The unresolved originating-data terms and missing upstream quality flags limit
redistribution and raw-observation claims. Episode/day counts are finite, and
the onset panel has five positive days. Gaussian undercoverage, conditional
residual regime misspecification, one-step-only dynamics fitting, and poor
probability calibration limit prediction. The graph proof's novelty is unresolved;
floating-point certification is absent and all empirical scenarios refine.

No relaxed-stability fit, short-rollout training loss, matched-pair observational
study, calibrated probabilities, large-N risk reference, equal-byte model study,
compilation, graph-scale LargeST run, test scoring, or full paper was executed.
These are explicitly outside the completed pilot evidence. The final source
contains reusable components, not an assertion that the entire research plan
has been experimentally validated.

The official CFP's linked ZIP was preserved privately and hashed. It actually
contains `llncs.cls`, despite the CFP's LNICST wording and SICC publication text.
No template was substituted or manuscript drafted. Venue/template and remote
presentation details should be resolved before any later writing/submission.

## 8. Proposed Stage 2, not authorized or executed

**Recommendation: simplify; do not launch the 24-hour campaign.** Close the
current selective-acceleration branch. First decide whether the application and
graph bound retain a worthwhile contribution after proper prior-work attribution.
If not, stop the intended study rather than expanding a generic benchmark.

If a later session authorizes continuation, use these gates and bounds:

| Work | Bounded matrix / output | Acceptance or stop criterion |
|---|---|---|
| Data and theory gate, CPU/read-only | Resolve originating terms/quality provenance; obtain closest inaccessible full papers; compare E/D assumptions explicitly | No raw-truth, open-data, or novel-theorem claim without evidence; narrow or withdraw claims if equivalent prior results exist |
| Model repair, CPU first | Two prespecified stability families, 0.98 and 1.05; one short-rollout-loss implementation; one logistic calibration family cross-fitted by whole validation days; fixed rank-16 prior and existing aggregate baselines | No threshold/event/region search. Require a useful calibrated Brier gap (tolerance 0.005) to the augmented baseline with paired day uncertainty, and honestly report conditional coverage. Stop if the model remains materially worse |
| Optional numerical confirmation, only after preceding gates | One frozen finalist, same 128 validation origins, retention 0/15/100%, N=1,024/4,096; identical information within numerical comparisons; retain raw/clipped/calibrated fields separately | No test access. No selective speed claim unless complete runtime improves and numerical guarantees are defensible. Record all completed scenarios and allocation costs |

The optional panel has four times the Stage 1 total N. Linear scaling of the
measured 282.60 s panel projects **1,130 s (0.314 GPU-hours)**; a 1.5 safety factor
projects **1,696 s (0.471 hours)**. Cap it at **1,800 seconds (0.5 GPU-hours)**,
with checkpoints and the existing runtime projection gate. These are measured-cost
projections for one same-size frozen model, not guarantees or a 24-hour allocation.
`configs/stage2_proposed.yaml` and `results/stage2_projection.json` preserve the
proposal. A repaired frozen input artifact would first be prepared and hashed in
the separately authorized Stage 2 session.

Prospective execution command **only after new authorization and the gates**:

```bash
PYTHONPATH=src OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 \
  python -m traffic_risk_twins.cli budget-run \
  --ledger results/stage2_compute_ledger.jsonl --reserve-seconds 1800 -- \
  python scripts/run_pilot.py --device cuda \
  --config configs/stage2_proposed.yaml \
  --inputs data/processed/stage2_frozen_inputs.npz \
  --source-sha "$(git rev-parse HEAD)" --origin-limit 128 \
  --max-wall-seconds 1750 --output results/stage2_confirmation
```

The Stage 2 ledger would be separate; the Stage 1 ledger must never be reset or
replaced. The proposed input file and Stage 2 results do not exist. This command
has not run. Any future test campaign still requires a frozen design and explicit
authorization after review of the model, data, and novelty gates.

## 9. Reproduction and review map

`README.md` has installation, acquisition, CPU training, test, budgeted pilot,
summary, and figure commands. Use `environment.cpu.lock` for the fitted CPU
environment and `environment.gpu.lock`/`manifests/pod_freeze.txt` for Pod provenance.
The private inputs remain at `data/processed/pilot_inputs.npz` locally and under
`/workspace/EAI-BDCC2026-stage1/` on the Pod. They can be regenerated from the
originating files; exact compressed hashes can depend on environment/container
serialization, so array-level hashes are also supplied.

Read [STAGE1_DATA_AUDIT.md](STAGE1_DATA_AUDIT.md) for exact split lists, graph,
masks, terms, and transformations; [STAGE1_PROOF_AUDIT.md](STAGE1_PROOF_AUDIT.md)
for the independent proof and literature boundaries; and
[STAGE1_PILOT_REPORT.md](STAGE1_PILOT_REPORT.md) for metrics, uncertainty, timing,
and numerical diagnostics. Compact results are in `results/tables/` and
`results/stage1_pilot/`. The two actual-result figures are
[information/prediction](../results/figures/information_prediction.pdf) and
[enclosure/cost](../results/figures/enclosure_cost.pdf), each with SVG, PNG, and alt
text. Delivery is authorized directly to main. The closing message records the actual
pushed SHA, remote containment check, and final working-tree state after delivery.
