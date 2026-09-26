# Current status: frozen final evaluation and comparative draft

This paper now lives in `papers/congestion-onset-graphs/`. Run the commands below
from this directory. Its code, data, results and manuscript keep their internal
relative layout. See the [repository index](../../README.md) for sibling papers.

The authorized final test evaluation is complete. Test data have now been evaluated, with no retraining or test-driven selection. [FINAL_TEST_REPORT.md](reports/FINAL_TEST_REPORT.md) is the current handoff; the [compiled comparative manuscript](manuscript/graph_representations_draft.pdf) is an anonymous draft for review. All historical results and reports below retain their original scope and exposure status.

C remains worse than aggregate correction B. Favorable graph point estimates are uncertain under the primary three-day multiplicity adjustment. E beats both trained rewired controls in secondary test comparisons but raises false alarms. R_union is the strongest main-family point predictor. See the report for full scores, uncertainty and qualifications.

The final stage used 35.503393 GPU-job seconds, bringing cumulative usage to 1,033.325936 seconds. No experiment remains running or scheduled. Review the science and unresolved measurement-use/publication provenance before submission; do not retune using the now-exposed test period.

Reproduction and rendering instructions: [frozen protocol](reports/FINAL_TEST_PROTOCOL.md), [manifest](configs/final_test_manifest.json), [manuscript commands](manuscript/README.md). Selective refinement remains disabled.

---

# Historical handoff before final evaluation

The preceding handoff was the [exploratory onset/graph study](reports/ONSET_GRAPH_STUDY_REPORT.md),
completed 23 September 2026. The authorized study implemented all six local/regional
graph representations, stronger aggregate controls, chronological evaluations and
matched trained graph nulls on CUDA. Historical reports and results are preserved.

The previous secondary onset finding did not persist under this registered follow-up.
On 8,981 identical onset-eligible validation origins, raw Brier was R_union .01216714,
aggregate correction B .01216962, local C .01239595, distance graph D .01253247,
training-selected expanded E .01228246, and dependency graph F .01214400.
C was worse than B; E improved D but not B and raised false alarms beyond tolerance.
Neither D nor E consistently beat both trained rewired nulls. F's tiny increment
over B was uncertain. Every validation day was already exposed: these remain
exploratory findings, not confirmation or proof of zero local information value.

That handoff recommended a narrow chronological comparison
of aggregate refitting R_union versus aggregate correction B with stronger alarm
calibration support. No next experiment is scheduled. The optional information-budget
extension failed its training-only gate and did not run. The original test measurements,
predictions and event-dependent summaries were unopened at that delivery. Selective enclosures remain
disabled; no simulator campaign, full study or paper was launched.

New GPU-job time was **287.963973 seconds**; cumulative project use is
**997.822543 seconds**, reconciled in the [ledger summary](manifests/onset_graph/compute_summary.json).
All eight new jobs finished. CUDA event spans are recorded separately and are not
active-kernel totals. The actual device was the RTX 6000 Ada Generation, with peak
allocated VRAM 1.86 GB. All 187 compact checkpoints are versioned with hashes and
[restore instructions](artifacts/onset_graph/README.md), so weights survive the Pod.

The [original research plan](research_plan/EAI_BDCC_2026_Research_Plan.md),
[Stage 1](reports/STAGE1_REPORT.md), [Stage 2](reports/STAGE2_REPORT.md),
[campaign closeout](reports/CAMPAIGN_CLOSEOUT.md), [research reset](reports/RESEARCH_RESET.md)
and [prior residual pilot](reports/RESIDUAL_PILOT_REPORT.md) retain every positive,
negative and inconclusive result. Stage 2's original simulator/local-feature/enclosure
campaign failed its gates; its exploratory results are not overwritten by subsequent
experiments. Data-use terms and upstream measurement preprocessing remain unresolved;
see the [updated source audit](reports/ONSET_GRAPH_SOURCES.md). Raw data remain private.

## Onset/graph reproduction

Read the frozen [protocol](reports/ONSET_GRAPH_PROTOCOL.md) and
[configuration](configs/onset_graph_study.json) before any future authorized compute.
The modular implementation is `src/traffic_risk_twins/onset_graph/`, reusing the
prior guarded data and baseline modules. There is no CPU experiment fallback.
Dependencies match `environment.residual-gpu.lock` and run JSON environment records.
Reuse private `data/raw/pems-bay.h5` and `data/processed/pilot_inputs.npz` without
new downloads. The original private residual checkpoints are needed only for the
historical-original replay audit; compact converted references are now also versioned.

Fitting/checks/nulls used `48e31b66745d577105c5aa8f2b8b2e6690fafd0b`;
outer evaluation/checkpoint replay used `70e03d050022e294340712071c0d8a261fb04438`;
supplementary CUDA diagnostics used `541723f5c858cb852742b7080e59e0a391b37779`.
Later source differences concern reporting/rendering/metadata, not fitted behavior.

The following is documentation, **not a new run authorization**. Use a new run ID,
retain the persistent ledger, and record the actual committed executable source.
The wrapper serializes GPU jobs, times startup/failed runs and enforces reservations.

```bash
ONSET_PYTHON=/workspace/EAI-BDCC2026-stage1/.venv/bin/python
ONSET_SOURCE_SHA=$(git rev-parse HEAD)
ONSET_RUN_ID=reproduction02
$ONSET_PYTHON scripts/onset_budget.py --reserve 240 --phase core --source-sha "$ONSET_SOURCE_SHA" -- \
  $ONSET_PYTHON scripts/run_onset_graph.py --mode audit --run-id "$ONSET_RUN_ID" --source-sha "$ONSET_SOURCE_SHA"
for ONSET_FOLD in rolling1 rolling2 main; do
  $ONSET_PYTHON scripts/onset_budget.py --reserve 600 --phase core --source-sha "$ONSET_SOURCE_SHA" -- \
    $ONSET_PYTHON scripts/run_onset_graph.py --mode train --fold "$ONSET_FOLD" --run-id "$ONSET_RUN_ID" --source-sha "$ONSET_SOURCE_SHA"
done
$ONSET_PYTHON scripts/onset_budget.py --reserve 600 --phase core --source-sha "$ONSET_SOURCE_SHA" -- \
  $ONSET_PYTHON scripts/run_onset_graph.py --mode nulls --run-id "$ONSET_RUN_ID" --source-sha "$ONSET_SOURCE_SHA"
# Read the frozen training-only budget_decision.json before outer evaluation.
# study01 did not admit an extension; no policy was fit or executed.
$ONSET_PYTHON scripts/onset_budget.py --reserve 600 --phase core --source-sha "$ONSET_SOURCE_SHA" -- \
  $ONSET_PYTHON scripts/run_onset_graph.py --mode evaluate --run-id "$ONSET_RUN_ID" --source-sha "$ONSET_SOURCE_SHA"
$ONSET_PYTHON scripts/onset_budget.py --reserve 180 --phase core --source-sha "$ONSET_SOURCE_SHA" -- \
  $ONSET_PYTHON scripts/run_onset_graph.py --mode replay --run-id "$ONSET_RUN_ID" --source-sha "$ONSET_SOURCE_SHA"
$ONSET_PYTHON scripts/onset_budget.py --reserve 240 --phase core --source-sha "$ONSET_SOURCE_SHA" -- \
  $ONSET_PYTHON scripts/run_onset_graph.py --mode supplement --run-id "$ONSET_RUN_ID" --source-sha "$ONSET_SOURCE_SHA"
```

Render delivered figures and scalar CSV transcriptions from saved GPU outputs only:

```bash
python3 scripts/build_onset_figures.py
python3 scripts/finalize_onset.py
```

The latter checks archival hashes, historical preservation and ledger metadata;
it does not fit or score a CPU model. The illustrative local window is categorical,
not an invertible raw-speed export. The four main figures and illustration have
PDF/SVG exports and PNG previews under `results/onset_graph/study01/main/figures/`.

## Residual pilot reproduction

Read the frozen [protocol](reports/RESIDUAL_PILOT_PROTOCOL.md) and
[configuration](configs/residual_pilot.json) before using compute. The numerical
implementation lives in `src/traffic_risk_twins/residual_gpu/`: baseline adapter,
data/masks, correction models, fitting, evaluation, checks and the unexecuted
conditional selection branch are separate. This path requires the verified
RTX 6000 Ada Generation and CUDA; it has no CPU experiment fallback.

The fitting/evaluation source was
`29c64549c12e5daaad187cfe15f774d0ff3cd962`; checkpoint replay and expanded timing
used `637c41b72666113f2e11ec8263ff4e6526f1c5f6`, with unchanged trained behavior.
Dependencies are recorded in `environment.residual-gpu.lock` and the individual
run JSON files. Reuse the existing private `data/raw/pems-bay.h5` and
`data/processed/pilot_inputs.npz`; no new download is needed. The configured Pod
used its existing `/workspace/EAI-BDCC2026-stage1/.venv/bin/python` environment.

The following documents reproduction; it is not authorization for a new run.
Keep `results/residual_pilot/compute_ledger.jsonl` across checkouts and use a new
run ID. The wrapper includes startup, warm-up, failures and retries in its budget.
The source SHA must identify the actual committed executable checkout.

```bash
PILOT_PYTHON=/workspace/EAI-BDCC2026-stage1/.venv/bin/python
PILOT_SOURCE_SHA=$(git rev-parse HEAD)
PILOT_RUN_ID=reproduction02
$PILOT_PYTHON scripts/residual_budget.py --reserve 180 --phase core --source-sha "$PILOT_SOURCE_SHA" -- \
  $PILOT_PYTHON scripts/run_residual_gpu.py --mode audit --run-id "$PILOT_RUN_ID" --source-sha "$PILOT_SOURCE_SHA"
$PILOT_PYTHON scripts/residual_budget.py --reserve 3600 --phase core --source-sha "$PILOT_SOURCE_SHA" -- \
  $PILOT_PYTHON scripts/run_residual_gpu.py --mode train --run-id "$PILOT_RUN_ID" --source-sha "$PILOT_SOURCE_SHA"
# Inspect the durable training-only refinement_gate.json before evaluation.
# In pilot01 the gate failed; no refine invocation was made.
$PILOT_PYTHON scripts/residual_budget.py --reserve 600 --phase core --source-sha "$PILOT_SOURCE_SHA" -- \
  $PILOT_PYTHON scripts/run_residual_gpu.py --mode evaluate --run-id "$PILOT_RUN_ID" --source-sha "$PILOT_SOURCE_SHA"
$PILOT_PYTHON scripts/residual_budget.py --reserve 180 --phase core --source-sha "$PILOT_SOURCE_SHA" -- \
  $PILOT_PYTHON scripts/verify_residual_gpu.py --run-id "$PILOT_RUN_ID" --source-sha "$PILOT_SOURCE_SHA"
```

Checkpoints are written under `checkpoints/residual_pilot/<run-id>/` and are
excluded from Git. The delivered originals also have an ignored local copy at
`data/processed/residual_pilot/pilot01/`; exact hashes are in
`manifests/residual_pilot/checkpoints.json`. Replay refuses to overwrite a
completed verification. A missing private checkpoint is not replaced by a claim
that the original model was recovered.

Render the delivered figures/CSV transcriptions from saved GPU statistics only:

```bash
python3 scripts/build_residual_figures.py
```

PDF, SVG and PNG exports are under `results/residual_pilot/pilot01/figures/`.
`scripts/audit_residual_artifacts.py` checks hashes, historical preservation,
links and ledger arithmetic using CPU metadata operations only; it requires
the existing private files and refreshes its own verification manifests.
It does not decode measurements, fit models or recompute research metrics.

## Review the closeout

Read the reports above and `results/closeout/evidence_audit.json`. The new
`configs/research_closeout.json` freezes the zero-GPU/no-experiment scope.
`results/closeout/compute_ledger.jsonl` records the single completed synthetic
job; `artifact_audit_ledger.jsonl` separately records saved-table, preservation
and link checks. `scripts/closeout_algebra.py` and its saved rational outputs
document the counterexamples; `scripts/closeout_budget.py` refuses to overwrite
them. The checks are elementary synthetic evidence, not traffic experiments or
new general proofs.

To verify the delivered closeout using committed artifacts only:

```bash
python3 scripts/audit_closeout.py delivery
```

This writes a new verification record and appends to the closeout artifact
ledger. Preserve those records before a deliberate replay. The remaining
commands document historical reproduction workflows; they are not part of the
closeout and do not authorize new fits or experiments.

## Historical setup and reproduction

Python 3.8+ is supported; GPU verification uses Python 3.12 and the environment
recorded in `manifests/gpu_environment.json`. The installation uses the Pod's
existing CUDA-compatible PyTorch. Raw measurements, environments, and model
banks are deliberately excluded from Git.

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r environment.cpu.lock  # Tested Python 3.8 environment; see GPU record for Python 3.12
pip install -e '.[test]' --no-deps
python -m pytest -q
```

Stage 2 reuses the existing private `data/raw/` files and
`data/processed/pilot_inputs.npz`; it needs no download or CUDA installation.
With those inputs, replay all bounded analyses in a **new** directory:

```bash
PYTHONPATH=src OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 timeout 900 \
  python scripts/reproduce_stage2.py --directory /tmp/eai-stage2-new-reproduction
```

The launcher copies committed source, links existing private inputs, disables
CUDA, and writes new results in the specified directory. It records the latest
verification in `manifests/stage2/reproduction.json` in this checkout; preserve
that manifest before deliberately replacing a historical verification. The
recorded eight-script CPU replay took 182.47 seconds. Timing varies by host.
The frozen workload, gates and limits are in
`configs/stage2_diagnosis.yaml`; its forecasting default is fine Monte Carlo,
with selective refinement disabled. Additional configurations record the one
residual repair and one enclosure tightening.

To check delivered tables without raw data or rebuild the two figures:

```bash
PYTHONPATH=src python scripts/verify_stage2.py
python scripts/build_stage2_figures.py
```

PDF, SVG and PNG figures are in `results/stage2/figures/`. The artifact verifier
checks historical hashes, common denominators, exact alarm decisions, complete
sample counts, paired timing records and ledger reconciliation. CPU dependency
versions are in `environment.cpu.lock`; Stage 2 hardware/provenance records are
under `manifests/stage2/`. Neither command evaluates test outcomes.

## Historical Stage 1 preparation

These commands document the original data preparation; reuse existing files for
Stage 2 instead of downloading or refitting them:

```bash
python scripts/probe_sources.py
PYTHONPATH=src python scripts/fetch_pems.py
PYTHONPATH=src python -m traffic_risk_twins.cli audit-data
PYTHONPATH=src OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 python scripts/prepare_pilot.py
```

The downloader refuses existing files. Preserve original artifacts and reuse
them; do not overwrite raw files to reproduce a run. Read
`reports/STAGE1_DATA_AUDIT.md` for terms and masks. Source documentation is
downloaded into ignored `data/source_evidence/`; only small hashes and manifests
are committed. The audit accesses all timestamps but only training/validation
measurement slices. Test-reading APIs reject requests during both stages.

## Historical Stage 1 GPU pilot

The following commands record the Stage 1 workflow. They are not part of Stage 2
reproduction and do not authorize another GPU campaign.

Only run after checking remaining cumulative time in `results/compute_ledger.jsonl`.
An interrupted reservation is charged in full until explicitly reconciled with
execution evidence. Never replace the ledger to regain budget. The source SHA
argument records which committed code actually executes; use that checkout.

```bash
PYTHONPATH=src python -m traffic_risk_twins.cli budget-run \
  --reserve-seconds 120 -- python scripts/gpu_audit.py --source-sha "$(git rev-parse HEAD)"
PYTHONPATH=src OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 \
  python -m traffic_risk_twins.cli budget-run --reserve-seconds 2400 -- \
  python scripts/run_pilot.py --device cuda --source-sha "$(git rev-parse HEAD)" \
  --output results/stage1_pilot --origin-limit 128 --max-wall-seconds 2350
```

Use a new output directory for every deliberate repetition. Every launched
fixed-N scenario is completed before its result is saved. Outcome-independent
runtime projections can stop before another complete origin; incomplete runs
are marked by the absence of a successful `run.json` and must not be reported
as completed panels. `--device cpu` provides the CPU path without GPU use.

The pilot compares common fitted models and common scenarios at equal N.
Two-level Monte Carlo has independent allocation, cheap, and correction sets;
each correction uses the same fine/coarse initial state and forcing. Its raw
estimate and bounded-variable uncertainty are saved before separately labeled
clipping for predictive scores. Allocation budgets are targets, not proven
equal wall times; measured complete runtime determines that comparison.

The final GPU-tested core is commit
`128f8f15257c51677e197ec2493ddc4c0d098820`. The initial pilot at
`a2cc0400b71a71f06a6fde17270de8aa777a0f3e` is preserved under
`results/stage1_pilot_initial/`; both runs are charged to the same ledger.
The later delivery adds CPU analysis, figures, and reports without changing the
GPU-tested core. `environment.gpu.lock` records the tested direct GPU dependencies;
`manifests/pod_freeze.txt` records the complete installed Pod environment including
unrelated preinstalled notebook packages, and is not a portable pip requirements file.

Rebuild the saved-result summaries and figures locally:

```bash
PYTHONPATH=src python scripts/summarize_pilot.py
python scripts/build_pilot_figures.py
```

The summary's matched speed baselines need the private raw file; figures use only
committed tables. `scripts/reconstruction_diagnostics.py` and
`scripts/benchmark_cpu_reference.py` provide the CPU-only dependence and dense/CSR
audits. The latter ran on the same Pod after GPU experiments had ended.

## Package layout

`src/traffic_risk_twins/` separates ingestion and quality, chronological splits,
retained information, conditional histories, graph dynamics and enclosures,
events, estimators, predictive baselines, evaluation, and the compute ledger.
`cell_transmission.py` is an independent conservation check, not a model claimed
to satisfy the graph theorem. Scripts prepare data, run the bounded pilot, and
build figures from numerical outputs. Stage 2 adds matched-information prediction,
chronological calibration, residual-location repair and enclosure attribution in
separate modules. Any new stage requires separate authorization.
