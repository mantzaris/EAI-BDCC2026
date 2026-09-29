# Study status

Updated: 2026-09-28 (local). Overall completion: **35%** (estimated against the eight stage gates).

| Stage | State |
|---|---|
| 0 Environment and acquisition | Complete: all sources, live Neo4j, CUDA inference, parameter/tensor placement and 171-package dependency lock |
| 1 Synthetic correctness | Local tests and live Neo4j/relational parity passed; immutable displayed-text maintenance added |
| 2 GPU generation and five conditions | All five conditions executed on GPU; format failures found in development and retained |
| 3 Real data adapters | Development unit/provenance audit completed; fixed splits and 100 prepared episodes rebuilt; replay arrays separately hashed |
| 4 Freeze and development pilot | Pilot v1 complete but fails format gate; v2 diagnostic run underway; final balanced schedule prepared for v3 |
| 5 Locked experiments | Pending: 3,600 initial calls, at most 2,880 repairs |
| 6 Analysis and interface | Independent evaluator, clustered bootstrap, plotting, open-loop workload and automated audit implemented; execution/interface pending |
| 7 Manuscript package | Pending |

All changes are committed and pushed to `main`, without branches, as instructed.
No held-out generations or research results exist yet. Forty correctness tests pass.
Sixty prepared base episodes are held out; forty are for development. No protocol
freeze has occurred. The user confirmed continuing with the current pod.
Pilot v1 had 100 initial cases, 69 bounded repairs, and 20 interactive requests;
67 initial outputs truncated and 71 final cases failed. All failures are retained.
The second development run tests a larger limit. Final format instructions explicitly
name every required JSON field, and the schema enforces at most three claims.

Next executable step (on the pod in `/workspace/temporal-evidence-graphs`):

```sh
.venv/bin/python -m temporal_evidence.cli pilot --run-id pilot_v3
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
