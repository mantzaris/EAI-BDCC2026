# Frozen final held-out evaluation

Registered 23 September 2026, before test measurement access. The current user explicitly authorizes this one final evaluation and an identical replay. This supersedes the earlier test-access reservation only for this stage. No fitting, recalibration, new seed, graph intervention, target change, candidate selection, information-budget extension, or subsequent experiment is authorized by this protocol.

## Starting evidence and exposure

Clean main started at `c1f0a2173c2e24ca87a2b7f35ca8887258a876c2`; verified origin was current. No subsequent final evaluation or unrelated modifications were found. Historical reports, ledgers, source guards, predictions and checkpoints are preserved. The [starting inventory](../manifests/final_test/starting_state.json) hashes all historical tracked files. Prior cumulative GPU-job time is 997.8225433584303 seconds, reconciled from the prior ledger, not CUDA spans. Historical GPU fitting/evaluation/supplement sources are respectively `48e31b66745d577105c5aa8f2b8b2e6690fafd0b`, `70e03d050022e294340712071c0d8a261fb04438`, `541723f5c858cb852742b7080e59e0a391b37779`.

Existing runners forbid test measurement access. Executed-mode receipts and saved populations identify only training and validation workloads. No prior test prediction file or outcome-dependent summary was found. This is a repository/execution-record audit, not proof about unrecorded activity outside the project. All 36 validation days were previously exposed. Onset was secondary in the residual pilot and became a registered exploratory primary endpoint in the subsequent onset study after seeing favorable development evidence. The final evaluation preserves that endpoint and the unsuccessful strengthened-baseline comparison. It does not make the earlier validation independent.

Only timestamps, sensor ordering, dataset shapes, opaque file hashes and split membership were inspected for this freeze. [Split metadata](../manifests/final_test/split_metadata.json) contains no measurement values or outcomes. Original complete-day split: training Jan 1-Apr 19, 2017 (108 days, incomplete Mar 12 excluded); validation Apr 20-May 25 (36 days); test May 26-Jun 30 (36 days). Test permitted rows begin May 26 01:30 and end Jun 30 23:55. There are 10,333 timestamp-eligible test origins before any outcome/missingness exclusion. Every input/outcome window must stay inside its split with regular five-minute spacing and the original two-sided 90-minute boundary embargo. No test prevalence is previewed.

## Frozen task, roster and dependencies

History has 12 five-minute frames and the future has six. The event is at least 48 of the 325 sensors at/below half their original training-fitted 85th-percentile reference speed in each of three consecutive future frames. Nonfinite/nonpositive values are unknown. Observed lower/upper event bounds must agree and future observation coverage must be at least .95. Onset further excludes currently or possibly active sustained events over the last three frames. These are forecast-origin event groups, not independently verified road incidents. Historical fixed target constants use the full outer training period; earlier rolling evaluations do not establish their availability at historical inner cutoffs.

The [machine-readable manifest](../configs/final_test_manifest.json) pins all source/dependency and checkpoint hashes, original configuration, model metadata, graph operators, original split membership, seeds and tolerances. The seal is completed only after development-only CUDA verification, then committed before the first test read. Its own commit is supplied externally at execution, avoiding a self-referential hash. The evaluator checks the manifest and source bytes against that actual Git commit and rejects mismatched files, graphs, split definitions, missing checkpoints and existing output directories.

Roster: A_G, R_union, A_mono; aggregate correction B and capacity control K; C (no graph), D (distance similarity), M (regional only), S (multiscale summaries), E (within/cross-region messages), F (training dependency); E_internal, E_self, D_rewire_20261004/20261005, E_rewire_20261004/20261005. D self uses the already-trained matched C arm, as in the main study. This is 17 families and 45 raw prediction vectors, each with its frozen calibrated counterpart. Every correction retains seeds 20261001, 20261002, 20261003. Both rewiring seeds are retained. No required checkpoint is missing. The unrecoverable original sklearn fit is not reconstructed from its 128 predictions or renamed as a main-study baseline.

All main-study weights, normalization, target/feature free speeds, adjacency, dependency estimation, alpha, logistic maps and strict alarm cutoffs are fixed. Graphs are reconstructed only from the original frozen metadata and established deterministic rewiring seeds; no new intervention is permitted. R_union uses the exact union of anchor and correction fitting examples, stride three, and is a central competitive aggregate control. B and E remain training-selected comparators; F remains secondary regardless of its test rank.

## Analysis frozen before access

Primary endpoint: raw onset Brier, with original squared-loss fitting and post-shrinkage clipping. Secondary: raw all-time Brier. Frozen calibrated versions are separate secondary diagnostics. Average seed-specific losses, not probabilities; do not introduce an ensemble or select the best seed. All arms share exactly the same origins, outcomes, masks and equal weights.

Four primary raw onset contrasts: C-B, D-C, E-D, E-B. Negative differences favor the first model. Use the existing paired calendar-block procedure with 2,000 resamples, seed 20261007, three-day blocks primary and one-day sensitivity. Preserve contiguous calendar segments and all overlapping origins within each selected day. Report pointwise 95% and family-four Bonferroni percentile 98.75% marginal intervals. This approximate dependence-aware assessment conditions on the fitted models and registered seed membership; it does not cover all training, selection, or temporal-distribution uncertainty. Do not interpret intervals crossing zero as equivalence.

Separately label B-R_union secondary. Report every family and descriptive local/graph-versus-aggregate and real-versus-trained-null comparisons. Secondary contrasts retain pointwise intervals without pretending to belong to the primary adjusted family. No F-specific null was trained; do not invent one now.

Retain practical scales: local change at least .0001 absolute and 1% relative Brier reduction; graph change at least .00005 and .5%; maximum material recall decrease .02 and FPR increase .01. Report actual effects and alarms separately. A materiality scale is not a significance test or automatic equivalence margin.

Report per-seed and seed-mean scores, seed SD, event/non-event loss contributions, reliability bins, mean probabilities, zero/one clipping and cutoff-tie fractions, support/exclusions, frozen-cutoff recall/FPR and block intervals. Frozen alarms use strict probability greater than cutoff, with no jitter or test threshold selection. Episode summaries group positive origins separated by less than 30 minutes; a gap of at least 30 minutes starts a new group. False alarms are grouped by the same rule among alarmed eligible non-event origins. These groups are not observed incidents. Zero event support produces undefined detection quantities, never evidence of perfect detection. Main calibration used only 30 positive origins in five groups on four days; this weak support remains a limitation even if a fitted map is monotone.

Verify the existing clipped correction identity on CUDA for every arm and endpoint. Family reliability pools seed-origin diagnostic pairs without calling their count independent support. Validation and test are displayed separately and never pooled into a supposedly independent sample. Any reversal is retained without retuning.

## Verification, execution and costs

Before test access, replay all 45 raw and 45 calibrated prediction vectors on the complete original validation workload. Check restoration, exact label/mask/origin alignment, zero-alpha baseline recovery, finite bounded probabilities, frozen threshold equality, original test guard, disabled final fitting, corrupted hash rejection and unpopulated test rows. Graph operator hashes are computed on CUDA and their bytes serialized for the seal. Existing prior scientific checks cover masking/permutation/projection/null invariants; do not rerun unrelated historical suites.

Predeclare maximum absolute prediction tolerance 1e-10 and metric tolerance 1e-12; labels, masks and origin identities must match exactly. An identical authorized held-out replay checks all predictions and every numeric metric leaf, including intervals, using CUDA comparisons. Report actual differences; claim exactness only if zero. No completed output may be overwritten. Infrastructure recovery must retain failed receipts and resume the same frozen computation. A post-exposure code correction must be explicitly disclosed with impact and original evidence.

CUDA scientific work only on the existing NVIDIA RTX 6000 Ada Generation (48 GB). No CPU numerical fallback. Set the allocator ceiling to 32 billion bytes. [Budget wrapper](../scripts/final_test_budget.py) holds an exclusive persistent ledger lock, reserves bounded job time, includes startup/failures/serialization, kills timed-out process groups and closes receipts. Stage cap 1,800 additional seconds and cumulative cap 86,400 seconds. Existing measured evaluation/replay costs suggest well under 180 seconds total; initially reserve 180 for preflight, 600 for final evaluation and 180 for replay, subject to remaining cap. No new timing campaign. Summarize the existing 128-origin transfer-inclusive measured costs on CUDA. CUDA event spans include host gaps and are not active-kernel totals.

## Outputs and manuscript boundary

Save raw/calibrated predictions together with origin IDs, timestamps, bounds, eligibility, onset, coverage and exclusion flags under results/final_test. Keep raw measurements private. The existing policy permits compact derived outcomes/predictions; their publication/redistribution terms remain an explicit unresolved prerequisite. Preserve recoverable main-study checkpoints and exact hashes. Each run records source/protocol revision, timestamps, dependencies, driver/device, GPU/host memory, full job charge and CUDA timing scope.

Create FINAL_TEST_REPORT.md and a complete comparative conference draft. Verify official author requirements, use the provided unmodified template, inspect the compiled PDF and trace numerical claims to saved artifacts. The manuscript compares representations rather than proposing a new theorem or claiming a comprehensive GNN benchmark. No conference submission, new experiment, or further model development follows this handoff.

## Commands

Run from the repository root on the configured GPU host with the existing environment and private data links. Git checkout must contain the designated committed protocol.

```sh
python3 scripts/final_test_budget.py --reserve 180 --phase verification --source-sha "$FINAL_SOURCE" -- /workspace/EAI-BDCC2026-stage1/.venv/bin/python scripts/run_final_test.py preflight --protocol-commit "$FINAL_SOURCE"
# After preflight, seal and commit the manifest locally, then deploy that commit.
python3 scripts/final_test_budget.py --reserve 600 --phase evaluation --source-sha "$FINAL_PROTOCOL" -- /workspace/EAI-BDCC2026-stage1/.venv/bin/python scripts/run_final_test.py evaluate --protocol-commit "$FINAL_PROTOCOL"
python3 scripts/final_test_budget.py --reserve 180 --phase replay --source-sha "$FINAL_PROTOCOL" -- /workspace/EAI-BDCC2026-stage1/.venv/bin/python scripts/run_final_test.py replay --protocol-commit "$FINAL_PROTOCOL"
```
