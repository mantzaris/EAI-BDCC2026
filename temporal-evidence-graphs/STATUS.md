# Study status

Updated: 2026-09-28. Overall completion: **2%** (estimated against the eight stage gates).

| Stage | State |
|---|---|
| 0 Environment and acquisition | CUDA BF16 calculation verified; dataset and runtime setup underway |
| 1 Synthetic correctness | Pending |
| 2 GPU generation and five conditions | Pending |
| 3 Real data adapters | Pending |
| 4 Freeze and development pilot | Pending |
| 5 Locked experiments | Pending: 3,600 initial calls, at most 2,880 repairs |
| 6 Analysis and interface | Pending |
| 7 Manuscript package | Pending |

All changes are committed and pushed to `main`, without branches, as instructed.
No test generations or research results exist yet. No access blocker is currently known.

Next executable step (on the pod in `/workspace/temporal-evidence-graphs`):

```sh
bash scripts/bootstrap_pod.sh
```

The supplied research plan is the governing prospective protocol. Deviations and
resolved choices are recorded in [DECISIONS.md](DECISIONS.md).
