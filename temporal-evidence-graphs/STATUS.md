# Study status

Updated: 2026-09-28 (local). Overall completion: **40%** (estimated against the eight stage gates).

| Stage | State |
|---|---|
| 0 Environment and acquisition | Complete: all sources, live Neo4j, CUDA inference, parameter/tensor placement and 171-package dependency lock |
| 1 Synthetic correctness | Local tests and live Neo4j/relational parity passed; immutable displayed-text maintenance added |
| 2 GPU generation and five conditions | All five conditions executed on GPU; format failures found in development and retained |
| 3 Real data adapters | Development unit/provenance audit completed; fixed splits and 100 prepared episodes rebuilt; replay arrays separately hashed |
| 4 Freeze and development pilot | Pilot v3 passed; corrected systems smoke test passed; v4 repeats the complete gate before automatic freeze |
| 5 Locked experiments | Queued: 3,600 initial calls, at most 2,880 repairs |
| 6 Analysis and interface | Independent evaluator, clustered bootstrap, plotting, open-loop workload and automated audit implemented; execution/interface pending |
| 7 Manuscript package | Pending |

All changes are committed and pushed to `main`, without branches, as instructed.
No held-out generations existed when this status was written. Forty-one tests pass.
Sixty prepared base episodes are held out; forty are for development. No protocol
freeze has occurred. The user confirmed continuing with the current pod.
Pilot v1 had 100 initial cases, 69 bounded repairs, and 20 interactive requests;
67 initial outputs truncated and 71 final cases failed. All failures are retained.
Pilot v2 had five truncations and one final failure. Pilot v3 had zero truncations
and zero final failures, 51 batch repairs, and interactive p50/p95 of 13.29/17.04
seconds. A separate systems smoke test exposed an ambiguous reference-slot lookup;
its failed and corrected runs are retained. Pilot v4 repeats the full development
gate after that systems-only fix. Final format instructions explicitly name every
JSON field, with at most three claims and a common 1,536-output-token ceiling.

The sequential pipeline is running on the pod, PID 31802. It executes pilot v4,
live core validation, freeze, the held-out matrix, independent evaluation, analysis,
isolated load tests and the CUDA fidelity audit. It stops on a failed required check.
Stage times are logged in `artifacts/manifests/execution_stages.jsonl`.

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
