# Study status

Updated: 2026-09-28. Overall completion: **23%** (estimated against the eight stage gates).

| Stage | State |
|---|---|
| 0 Environment and acquisition | CUDA BF16 verified; all three sources acquired and inventoried; pinned model downloaded; live Neo4j / vLLM installation underway |
| 1 Synthetic correctness | Immutable replay and five-condition fixtures pass; live Neo4j parity check pending |
| 2 GPU generation and five conditions | Output contract, GPU guard, bounded repair client and validation implemented; live fixture pending |
| 3 Real data adapters | Both adapters, original metadata, fixed participant splits, and 100 prepared base episodes available; final development audit pending |
| 4 Freeze and development pilot | Pending |
| 5 Locked experiments | Pending: 3,600 initial calls, at most 2,880 repairs |
| 6 Analysis and interface | Pending |
| 7 Manuscript package | Pending |

All changes are committed and pushed to `main`, without branches, as instructed.
No test generations or research results exist yet. Twenty-five correctness tests pass.
Sixty prepared base episodes are held out; forty are for development. No protocol
freeze has occurred. Slow package downloads remain an operational delay, not a data
access blocker. The user confirmed continuing with the current pod.

Next executable step (on the pod in `/workspace/temporal-evidence-graphs`):

```sh
python -m temporal_evidence.cli check-environment
python -m temporal_evidence.cli validate-core --graph
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
