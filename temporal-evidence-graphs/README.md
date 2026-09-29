# Temporal Evidence Maintenance for Revisable Monitoring Explanations

Completed minimum study and manuscript draft for [EAI BDCC 2026](https://bdcc-conf.eai-conferences.org/2026/).
Read the [paper PDF](paper/temporal_evidence_maintenance.pdf),
[implementation report](REPORT.md), or [measured results](artifacts/analysis/measurements.md).
The governing prospective protocol is
[Temporal_Evidence_Graphs_Codex_Research_Plan.md](Temporal_Evidence_Graphs_Codex_Research_Plan.md).

## Research question

> When an observation is corrected, becomes outdated, or fails a quality check,
> can a temporal evidence graph identify and repair the generated explanations
> that depend on it, while preserving useful answers and keeping latency low?

The study uses graph databases to represent temporal evidence and dependencies
between observations and generated explanations. It includes Neo4j Community and a strong indexed relational control,
with synthetic physiology, WESAD, and PPG-DaLiA. Five conditions distinguish fresh
generation, direct checking, and transitive maintenance.

## Project status

RunPod gateway and direct SSH access verified on 28 September 2026. See
[connection instructions and environment observations](docs/runpod.md).
The frozen study accounts for all 3,600 initial cases, 1,620 repairs, six systems
cells, and a 60-explanation automated audit. [STATUS.md](STATUS.md)
records completed gates and commands; [DECISIONS.md](DECISIONS.md)
records protocol choices. All development pilots and failures are retained.

Direct checking matches full propagation on the generated waveform task. Error
rates measure a strict query contract that also rejects correctly labelled
background facts. Useful coverage is limited, and no complete replacement is
produced in the systems workload. The paper preserves these negative findings.

This directory contains the new paper's work within the shared repository. The
previous paper is in [`../congestion-onset-graphs/`](../congestion-onset-graphs/README.md).

## Local review and verification

The dashboard and exact analyses do not require a GPU or raw recordings:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dashboard.lock
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli dashboard
```

Open <http://127.0.0.1:8501>. See [dashboard instructions](docs/dashboard.md) for
correction, rejection, alternative-support and history examples. Review actions
are isolated from experimental artifacts. No human-performance result is claimed.

## Recompute the completed results

These commands regenerate exact case
scores, paired subject-level analysis, scientific figures and manuscript numbers:

```sh
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli evaluate --run-id minimum_v1
MPLCONFIGDIR=.local/matplotlib PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli analyze --run-id minimum_v1
PYTHONPATH=src .venv/bin/python -m temporal_evidence.analysis.publication
PYTHONPATH=src .venv/bin/python -m temporal_evidence.analysis.measurements
bash paper/build.sh
PYTHONPATH=src .venv/bin/python scripts/check_manuscript.py
```

The publication builder requires every planned case, all six systems cells,
the 60-explanation audit, and matching frozen hashes. It refuses partial results.
The compiled PDF is `paper/temporal_evidence_maintenance.pdf` (20 main pages, 23 total).
Building it requires `latexmk`, pdfLaTeX with the standard LaTeX packages, and
Poppler's `pdfinfo`, `pdffonts`, and `pdftotext` for validation. Conference requirements and
the official template provenance are in [docs/conference.md](docs/conference.md).

## GPU reproduction

The recorded deployment uses Python 3.12.3, PyTorch 2.8.0+cu128, vLLM 0.10.2,
Qwen3-8B BF16, an RTX 5090, Neo4j Community 5.26.0, and indexed SQLite.
`requirements.lock` is the tested GPU dependency closure; `requirements-dashboard.lock`
describes the separate Python 3.10 local reporting/interface environment.

On Linux x86_64 with Python 3.12, a compatible NVIDIA driver, `uv`, `curl` and `tar`
available, bootstrap the fixed packages and downloaded model revisions with
`bash scripts/bootstrap_pod.sh`. This uses the existing system CUDA installation
through a virtual environment, installs the local database, and binds services
to loopback. Run `PYTHONPATH=src .venv/bin/python scripts/serve_model.py` in a
dedicated process. Its worker verifies parameter and first-forward tensor placement
on CUDA. There is no CPU inference fallback. The provided pod is already configured.

The original experiment is complete and its model process has stopped. If an
incomplete copy must be resumed after restoring the CUDA server, the command is:

```sh
.venv/bin/python -m temporal_evidence.cli run --resume
```

Run only one runner per namespace. A completed run will
reuse its saved case identifiers. A new inference replication must use an isolated
workspace or a new replication namespace and preserve the original outputs,
source hashes, and prepared inputs. After starting the CUDA server, a separately
budgeted full replication can be launched with:

```sh
PYTHONPATH=src .venv/bin/python scripts/replicate_frozen.py --run-id replication_01
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli evaluate --run-id replication_01
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli analyze --run-id replication_01
```

The replication command creates separate database scopes and journals while
verifying the same frozen sources and input episodes. Use `--resume` after an
interruption. This is an additional 3,600 initial requests with bounded repairs;
it is not executed as part of the minimum study. Repeated generation does not add
independent subjects.

The saved prepared features suffice for generator replay. Rebuilding numerical
features requires the provider recordings and records new extraction wall times;
compare numerical/provenance content, rather than expecting the timing-bearing
episode JSON files to have identical bytes.

Original data acquisition and preparation commands are:

```sh
.venv/bin/python -m temporal_evidence.cli acquire-data --datasets wesad
.venv/bin/python -m temporal_evidence.cli acquire-data --datasets ppg_dalia --author-source
.venv/bin/python -m temporal_evidence.cli generate-synthetic
.venv/bin/python -m temporal_evidence.cli inventory-data
.venv/bin/python -m temporal_evidence.cli prepare-features
```

Use those preparation commands in a separate reproduction workspace; the frozen
study retains its exact prepared files. Acquisition manifests preserve source URLs,
hashes, original documentation, and usage statements. Raw archives, model weights,
credentials, and local database files are excluded from Git.

## Artifact map

| Path | Evidence |
|---|---|
| `artifacts/manifests/minimum_run.json` | Prospective 3,600-case matrix, model/config/source hashes |
| `artifacts/prepared/` | Immutable replay inputs; evaluator-only metadata separated |
| `artifacts/runs/pilot_v*/` | Complete development inputs, requests, repairs, failures and timing |
| `artifacts/runs/minimum_v1/` | Frozen study outputs and segmented request journals |
| `artifacts/evaluation/minimum_v1/` | Independent per-claim, per-slot and persistent-display scores |
| `artifacts/analysis/` | Paired bootstrap intervals, denominators, integrity and resource reports |
| `artifacts/streaming/` | Independent arrival logs, queues, latency and logical parity |
| `artifacts/audit/` | Separate CUDA verifier, sampled cases and all annotations |
| `artifacts/review_examples/` | Explicitly scripted correction, surviving support and false-review examples |
| `paper/` | Anonymized manuscript, generated numbers, bibliography and official template |

No optional expanded seeds, second generator comparison, review-budget simulation,
clinical classifier, or human study is included in this minimum protocol.
