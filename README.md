# When Averages Hide Congestion

Stage 1 studies whether retaining local traffic histories improves sustained
low-speed forecasts more than increasing Monte Carlo samples. The preserved
[research plan](research_plan/EAI_BDCC_2026_Research_Plan.md) defines the task.
The final handoff is [reports/STAGE1_REPORT.md](reports/STAGE1_REPORT.md).

This is a small recorded-speed predictive model. Its event is not an observed
incident or a causal traffic cascade. The graph enclosure is an exact-arithmetic
result; floating-point bounds are empirical. `certified` mode conservatively
evaluates every scenario on the fine graph. No acceleration claim is implied.

## Setup and CPU reproduction

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
measurement slices. Test-reading APIs reject requests during Stage 1.

## Bounded pilot

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
build figures from numerical outputs. Stage 2 requires separate authorization.
