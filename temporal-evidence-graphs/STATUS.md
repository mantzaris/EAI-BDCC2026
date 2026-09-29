# Study status

Updated: 2026-09-28 (local). Overall completion: **55%** (estimated against the eight stage gates).

| Stage | State |
|---|---|
| 0 Environment and acquisition | Complete: all sources, live Neo4j, CUDA inference, parameter/tensor placement and 171-package dependency lock |
| 1 Synthetic correctness | Local tests and live Neo4j/relational parity passed; immutable displayed-text maintenance added |
| 2 GPU generation and five conditions | All five conditions executed on GPU; format failures found in development and retained |
| 3 Real data adapters | Development unit/provenance audit completed; fixed splits and 100 prepared episodes rebuilt; replay arrays separately hashed |
| 4 Freeze and development pilot | Complete: v4 passed, all source/episode hashes frozen and verified locally |
| 5 Locked experiments | Running; 1,144/3,600 cases backed up locally at approximately 02:10 UTC; at most 2,880 repairs |
| 6 Analysis and interface | Analysis pipeline ready; functional isolated review dashboard with tested actions; systems/audit queued |
| 7 Manuscript package | Full draft structure and generated-table/figure pipeline ready; final numerical results and PDF pending |

All changes are committed and pushed to `main`, without branches, as instructed.
The held-out run started at 2026-09-29 01:14:46 UTC. Forty-five tests pass.
Sixty prepared base episodes are held out; forty are for development. Protocol hash:
`a22b68b4e3d33c7cbcaa253a6af27232a574a69692b5dcb793191ee1d2ceef63`.
The user confirmed continuing with the current pod.
Pilot v1 had 100 initial cases, 69 bounded repairs, and 20 interactive requests;
67 initial outputs truncated and 71 final cases failed. All failures are retained.
Pilot v2 had five truncations and one final failure. Pilot v3 had zero truncations
and zero final failures, 51 batch repairs, and interactive p50/p95 of 13.29/17.04
seconds. A separate systems smoke test exposed an ambiguous reference-slot lookup;
its failed and corrected runs are retained. Pilot v4 repeats the full development
gate after that systems-only fix. Final format instructions explicitly name every
JSON field, with at most three claims and a common 1,536-output-token ceiling.
Pilot v4 passed with zero initial truncations or final failures, 52 repairs,
309.62 seconds batch wall time and interactive p50/p95 of 13.34/17.07 seconds.

The sequential pipeline is running on the pod, PID 31802. It executes pilot v4,
live core validation, freeze, the held-out matrix, independent evaluation, analysis,
isolated load tests and the CUDA fidelity audit. It stops on a failed required check.
Stage times are logged in `artifacts/manifests/execution_stages.jsonl`.
Frozen experimental source is unchanged; dashboard/analysis/manuscript files are
outside that runtime boundary. The dashboard AppTest exercised a correction and
confirmed two withdrawals with two supported claims retained.
The final reporting gate audits all 720 matched evidence/prompt groups and request
start/finish accounting. Publication numbers require complete experiments.

Operational note: the already-running launcher's handoff guard expects the older
API-module command spelling, while this server uses `vllm serve`. The launcher
source now accepts both verified entrypoints and provides `--audit-only`; if the
running instance stops at that guard after the systems benchmark, resume just the
handoff/audit with the corrected source. Do not repeat the completed model study.

Next operational check (on the pod in `/workspace/temporal-evidence-graphs`):

```sh
cat artifacts/manifests/execution_status.json
tail -n 10 logs/final_pipeline.log
```

The supplied research plan is the governing prospective protocol. Deviations and
resolved choices are recorded in [DECISIONS.md](DECISIONS.md).

Local checks and preparation (from this project directory):

```sh
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli prepare-features
```

Original recordings remain in ignored `data/raw/`. WESAD's redundant pickle cache
was pruned after hash verification to reclaim 12.88 GiB; its adapter can read those
same immutable members directly from the retained ZIP. PPG-DaLiA was acquired from
the original authors after two UCI download paths stalled. Acquisition manifests
record URLs, hashes, original documentation, and the differing usage statements.
