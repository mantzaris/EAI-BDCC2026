# Study status

## Semantic revision — in progress (20%)

The requested representation/theory revision is separate from the completed
minimum study below. Actual Neo4j exports, ontology documentation, a semantic
projection, independent scoring and a deterministic 240-case structural selection
are implemented. Nine focused semantic/structural tests and all 56 tests pass.
Original runtime/input hashes remain unchanged. Extension GPU inference,
aggregate analysis, figures, manuscript/supplement and PDF checks remain pending.

See the [new protocol](docs/semantic_analysis_protocol.md) and
[original paper/report archive](paper/archive/minimum_v1/).

## Preserved minimum study

Updated: 2026-09-29. Minimum-study completion: **100%**.

All eight core stages are complete. Optional expanded seeds, another generator,
review-budget simulations and a human study were not run. No conference submission
was requested or attempted.

| Stage | Completed evidence |
|---|---|
| 0 Environment and acquisition | All three sources, source terms/inventories, live Neo4j, CUDA placement checks and pinned package closure |
| 1 Synthetic correctness | Direct/transitive, AND/OR, historical, restoration, duplicate/out-of-order and prose checks; live graph/relational parity |
| 2 GPU generation and conditions | All five matched conditions and bounded repair policy executed on CUDA |
| 3 Real adapters | Verified units and timing, fixed subject partitions, 100 prepared development/test episodes, separately hashed faults |
| 4 Freeze and pilot | Four retained pilots; final pilot passed; manifest and runtime hashes frozen before held-out generation |
| 5 Locked experiments | 3,600 cases accounted for, 1,620 repairs; three retained B0 transport failures; all six systems cells complete |
| 6 Analysis and interface | Paired subject analysis, resource/database accounting, 60-output CUDA audit, working isolated review dashboard and scripted examples |
| 7 Manuscript package | Report, five figures, fourteen tables, anonymized PDF: 20 main pages and 23 total; mechanical and visual checks complete |

Read [REPORT.md](REPORT.md), the [paper PDF](paper/temporal_evidence_maintenance.pdf),
or the [numerical ledger](artifacts/analysis/measurements.md).
All work is committed directly to `main`, without branches, as instructed.

The main experiment ran on 2026-09-29 from approximately 01:14 to 04:08 UTC.
The systems and verifier stages completed by 04:24 UTC. All study inference and
its resource monitor have finished; the provided pod remains available.
Forty-seven local tests pass, as does the saved live Neo4j validation. Integrity
checks account for 720 matched prompt/evidence groups and 5,220 main attempts.
Protocol hash:
`a22b68b4e3d33c7cbcaa253a6af27232a574a69692b5dcb793191ee1d2ceef63`.

The main finding is no correction advantage for transitive propagation over direct
checking in generated waveform answers. Contract violations include accurate
background facts outside the required interval; useful coverage is limited.
All 236 systems answers omit a required difference, so no complete replacement
is observed. These limitations and the verifier's mistakes are retained in the paper.

To regenerate the results and PDF locally, without GPU inference:

```sh
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli evaluate --run-id minimum_v1
MPLCONFIGDIR=.local/matplotlib PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli analyze --run-id minimum_v1
PYTHONPATH=src .venv/bin/python -m temporal_evidence.analysis.publication
PYTHONPATH=src .venv/bin/python -m temporal_evidence.analysis.measurements
bash paper/build.sh
PYTHONPATH=src .venv/bin/python scripts/check_manuscript.py
```

The existing `minimum_v1` run needs no inference resumption. The README describes
an isolated future replication namespace and its explicit additional call budget.
Before an actual submission, human authors must review the draft and verify the
submission system's exact cutoff/timezone. Neither is claimed completed here.
