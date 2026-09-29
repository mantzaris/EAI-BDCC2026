# Semantic Structure and Revision in Temporal Evidence Graphs

Research paper package for EAI BDCC 2026. The revised study connects a fixed typed
ontology, temporal support, graph structure and independent semantic fidelity.
The submission is one self-contained paper, with spacious labeled networks from
actual Neo4j exports and matching interactive dashboard views. The current PDF has
20 main pages plus one reference page. Its new classic network complements the
preserved structured diagrams, with individually visible ontology instances and
computed support/revision annotations.

- [Revised main paper](paper/semantic_structure_revision.pdf)
- [Prose revision and preservation checks](PROSE_REVISION.md)
- [Classic ontology-instance addition](CLASSIC_NETWORK_ADDITION.md)
- [Graph-view revision and validation](GRAPH_VIEW_REVISION.md)
- [Shared dashboard/publication network representation](docs/review_network_views.md)
- [Theory/results change summary](THEORY_RESULTS_CHANGES.md)
- [Exact reproduction commands and artifact map](docs/semantic_reproduction.md)
- [Ontology and construction rules](docs/ontology_construction.md)
- [Protocol and amendments](docs/semantic_analysis_protocol.md)

The original minimum_v1 inputs, runtime, scores and interpretations remain
unchanged. Its [original paper and report](paper/archive/minimum_v1/) are archived.
New analysis uses semantic_analysis_v1; the focused GPU study uses
structure_study_v1, with a separate primitive-name admission replication.

## Measured findings

Only 18 of 1,201 original M1 displayed claims declare parents, and none of the
210 eligible waveform revision batches has transitive exposure. Checked displays
are fully grounded under the new bounded proposition protocol, with subject-mean
required recall of 75.5–78.25%. The 240-case extension used 325 GPU calls and
9,600 matched replay cells. Full maintenance misses no required changes; direct
maintenance misses 720/1,260 in exact programs and 183/1,210 in admitted generated
programs. Exposure predicts every eligible primary miss set. The separate
admission replication preserves all candidates and links and is reported independently.

The original systems workload still has no adequate replacement among 236
candidates. Candidate completion is not successful correction. See the generated
summary for uncertainty, exclusions and the full outcome crosswalk.

## Rebuild and verify

From this directory, using the existing environment:

```sh
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.publication --prose-only
bash paper/build.sh
PYTHONPATH=src .venv/bin/python scripts/check_prose_revision.py
```

This is the current manuscript-only workflow. It preserves experimental artifacts
and compares equations, numbers, citations, figures and prose length with the
completed paper at `c62001f`. Its record is
[paper/prose_revision/validation.json](paper/prose_revision/validation.json).

For a full analysis reproduction from saved outputs, the original workflow remains:

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q --junitxml=artifacts/analysis/review_views_v1/pytest.xml
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.analyze
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.structural_analysis
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.alias_analysis
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.publication
MPLCONFIGDIR=.local/matplotlib PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.figures
bash paper/build.sh
PYTHONPATH=src .venv/bin/python scripts/check_semantic_manuscripts.py
```

The full-analysis checker validates refreshed analysis/code manifests. The older
check_manuscript.py belongs to the archived manuscript. Analysis uses saved answers and exports,
without repeating original GPU calls. [STATUS.md](STATUS.md) records completion;
[DECISIONS.md](DECISIONS.md) records choices. No conference submission is performed.

## Dashboard and original experiment

The dashboard opens the two recorded paper networks, with time, focus, witness,
provenance expansion and object-detail controls. The PPG-DaLiA case also offers a
**Classic network** layout matching Figure 4. Reversible review actions remain
available in the separate review workspace:

```sh
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli dashboard
```

See [dashboard instructions](docs/dashboard.md), [RunPod connection instructions](docs/runpod.md)
and the preserved [research plan](Temporal_Evidence_Graphs_Codex_Research_Plan.md).
The previous unrelated paper is in ../congestion-onset-graphs/.

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
