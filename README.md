# When Averages Hide Congestion

This project studies whether retaining local traffic histories improves sustained
low-speed forecasts more than increasing Monte Carlo samples. The preserved
[research plan](research_plan/EAI_BDCC_2026_Research_Plan.md) defines the task.
The current handoff is the [campaign closeout](reports/CAMPAIGN_CLOSEOUT.md) and
[research reset assessment](reports/RESEARCH_RESET.md), dated 23 September 2026.
It recommends **C: defer a restart**. Neither task-specific aggregation
sufficiency nor budgeted telemetry yet has a concrete new contribution,
established independent event support and a documented deployment/data-use path.
The [source and provenance audit](reports/RESET_NOVELTY_AND_PROVENANCE.md)
records the closest work and unresolved evidence.

The historical [Stage 1 handoff](reports/STAGE1_REPORT.md),
[Stage 2 handoff](reports/STAGE2_REPORT.md) and all their results remain unchanged.

Stage 2 recommends stopping the current method campaign: adding local histories
did not improve the matched classifier, the single residual repair remained
outside the simulator adequacy gate, and tighter enclosures still cost more than
fine simulation. These are exploratory validation findings. Test outcomes remain
untouched. Stage 2 used no GPU time; cumulative GPU-job usage is 668.62 seconds.
The closeout also used zero GPU time. One hand-specified synthetic algebra job
took 0.0324 seconds of wall time; no models were fit and no measurement files
were opened. No Stage 3 or restart pilot is scheduled or authorized.

This is a small recorded-speed predictive model. Its event is not an observed
incident or a causal traffic cascade. The graph enclosure is an exact-arithmetic
result; floating-point bounds are empirical. `certified` mode conservatively
evaluates every scenario on the fine graph. No acceleration claim is implied.

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
