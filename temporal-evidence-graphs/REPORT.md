# Semantic revision report

The completed extension, independent semantics and new theory are summarized in
[THEORY_RESULTS_CHANGES.md](THEORY_RESULTS_CHANGES.md), generated directly from
the analysis outputs. Read the [revised main PDF](paper/semantic_structure_revision.pdf)
and the [graph-view revision report](GRAPH_VIEW_REVISION.md).
[Reproduction commands](docs/semantic_reproduction.md) cover scoring, actual database
exports, shared dashboard views, figures, frozen inputs and the single PDF build. Final page and integrity
checks are recorded in artifacts/manifests/semantic_manuscript_validation.json.

The report below preserves the original experiment and its interpretation.
Its page counts and links describe the archived minimum-v1 manuscript.

# Preserved minimum-v1 implementation and experiment report

The minimum three-source study is complete. The result does **not** establish a
correction advantage for transitive graph propagation on the generated waveform
answers, or a low-latency complete-repair capability. Direct checking matches the
full methods under the frozen numerical contract. The controlled symbolic fixture
demonstrates the narrower situation in which a necessary transitive path matters.

Start with the [anonymized manuscript PDF](paper/archive/minimum_v1/temporal_evidence_maintenance.pdf)
or the [complete numerical ledger](artifacts/analysis/measurements.md). The PDF has
20 main pages, one reference page, and two appendix pages. This is a completed
experimental package and manuscript draft, not a conference submission.

## Completed work

- A synthetic waveform generator and exact symbolic dependency fixtures, WESAD
  and PPG-DaLiA adapters, original source inventories, fixed participant splits,
  separately hashed replay interventions, and immutable prepared features.
- Neo4j Community and indexed SQLite implementations with versioned evidence,
  historical snapshots, direct/transitive maintenance, AND/OR support, restoration,
  and immutable explanation revisions.
- Five matched conditions: B0 unchecked generation; B1 checked flat evidence with
  direct maintenance; B2 graph storage with direct maintenance; M1 full graph;
  B3 full relational maintenance. All checked methods have the same bounded repair
  allowance and fresh-answer checks.
- Pinned CUDA-only Qwen3-8B generation and Qwen2.5-3B-Instruct verification, raw
  prompts/responses, segmented request journals, failures, placement checks,
  timings, token accounting, and resource telemetry.
- Independent event-log evaluation, paired episode-to-subject bootstrap analysis,
  open-loop systems measurements, five reproducible figures, fourteen manuscript
  tables, and a local review dashboard with working correction/rejection/history
  actions and scripted successful and mistaken-review examples.

## Runs and integrity

The frozen protocol hash is
`a22b68b4e3d33c7cbcaa253a6af27232a574a69692b5dcb793191ee1d2ceef63`.
The main run, `minimum_v1`, contains 60 held-out base episodes, four variants,
three checkpoints, and five methods: **3,600 initial cases and 1,620 repairs**.
There are ten held-out subjects and 20 base episodes per source, with 240 cases
per source/method cell. Development episodes are separate.

All 3,600 cases are accounted for: 3,597 completed and three transport ReadErrors,
one per source in B0. They were not retried or removed. There are no initial
truncations or client timeout attempts. The [integrity report](artifacts/analysis/minimum_v1/integrity.json)
verifies frozen hashes, exact case membership, 720 matched initial prompt/evidence
groups, temporal visibility, sampling settings, repair bounds, and one start and
finish record for each of the 5,220 attempts.

The main GPU stage ran on 29 September 2026, approximately 01:14–04:08 UTC.
The isolated `streaming_v1` study then completed all six cells and all 3,120
derived events, with graph/relational logical parity. Its 236 initial requests and
236 repairs reach its separate 472-request ceiling. The verifier completed its
60 sampled outputs and four diagnostic calls. [Stage records](artifacts/manifests/execution_stages.jsonl)
and the [finalization record](artifacts/manifests/output_finalization.json) retain
the operational history. A known launcher process-name guard stopped the first
handoff; the coordinator resumed only the audit, without repeating experiments.

## Findings

All checked methods have zero observed display violations under the frozen
query contract and correct every eligible old claim, with no collateral
withdrawals. The paired M1–B2 correction differences are zero in all sources.
M1–B1 case-error differences are also zero. Zero-width bootstrap intervals arise
from identical observed subject differences; they do not prove universal
equivalence or a zero semantic error probability.

| Source | M1 required-fact recall | M1 complete useful coverage | M1 corrected/required | M1 collateral/unaffected |
|---|---:|---:|---:|---:|
| Synthetic | 79.3% | 60.5% | 73/73 | 0/247 |
| WESAD | 76.9% | 55.9% | 74/74 | 0/349 |
| PPG-DaLiA | 76.7% | 55.5% | 80/80 | 0/328 |

These are the saved aggregate proportions; the paired estimand first computes
within-episode differences and then gives subjects equal weight. Every principal
contrast includes ten subjects and 20 eligible episode pairs per source.
All methods, denominators, strata and intervals appear in the numerical ledger.

The primary error rates are **contract violations, not hallucination estimates**.
B0 has 799 invalid displayed claims; a post-hoc descriptive check finds that 333
are direct numerical background statements supported at their own stated interval.
The target-only contract rejects these even when the preceding interval is
correctly labelled. A comparison can also fail through a declared parent link to
such a statement. This affects interpretation of both error and recall. The
[scope breakdown](artifacts/analysis/minimum_v1/contract_scope.json) preserves
examples and source hashes. No original metric or runtime rule was changed.

Only 18 of M1's 1,201 displayed claims declare parent claims, and no initially
valid persistent claim has a parent dependency as its sole later error. Direct
operand citations generally suffice in this task. In the separate common symbolic
fixture, full graph and relational maintenance correct 4/4 required changes;
direct-only methods correct 2/4. These constructed cases do not demonstrate an
empirical advantage on unrestricted generated reasoning chains.

At 1 and 5 events/s both backends meet all one-second flag targets. At 20 events/s,
M1 misses 21/30 and B3 misses 17/30; flag p95 is 33.69 and 77.70 seconds,
respectively. M1 and B3 peak event queues reach 347 and 394. Every one of the
236 systems displays contains only a target observation and omits the requested
difference, despite a repair request. Both methods miss all 40 adequate-replacement
targets. Reported candidate-completion times include incomplete answers;
**successful-replacement latency is undefined**. Zero completion-staleness counts
are uninformative when there are no initially adequate replacements.

The auxiliary verifier parses all 60 sampled explanations and passes 4/4 simple
diagnostics, but accepts ten exact-invalid outputs and flags four exact-valid
outputs. Its saved rationales include missing numerical/reference mistakes,
confusing null with an available measurement, and rejecting permitted rounding.
This is an automated, imperfect check from the same model family, not human-rated
semantic quality. [Every disagreement](artifacts/analysis/minimum_v1/audit_details.json)
is retained.

## Compute and storage accounting

The experiment uses an RTX 5090, Qwen3-8B BF16, vLLM 0.10.2, PyTorch 2.8.0+cu128,
Neo4j Community 5.26.0 and SQLite. Parameters and first-forward tensors are checked
on CUDA; there is no CPU neural inference fallback. Numerical feature extraction
and exact aggregation use the host.

The matched stage takes 2.89 hours and returns usage for 8,525,358 input and
2,880,024 output tokens. Three ReadErrors have **unknown server-side token cost**;
the available totals do not assign them zero cost. Observed main-stage GPU memory
peaks at 28,441 MiB, mean utilization is 88.66%, and pod cgroup memory peaks near
28.46 GiB, including file cache and other processes. The systems stage takes
15.14 minutes, and the verifier stage 33.78 seconds including process setup.

The numerical ledger separately accounts for all four development pilots,
interactive pilot requests, and the failed and corrected systems smoke tests.
Earlier truncations and failures remain available. These are workload wall times,
not GPU kernel time or total billable pod time; downloads, initial server
compilation and unlogged gaps are excluded. No account hourly price was supplied,
so no monetary cost is invented. The [resource report](artifacts/analysis/resources.json)
contains the full sampling and timing scope.

[Database accounting](artifacts/manifests/database_accounting.json) records logical
node/edge counts, assessments, retained display claims, revision chains and physical
file sizes. Physical Neo4j storage includes development scopes while the SQLite
file covers different conditions, so their byte sizes are not a fair compression
comparison. The load test has one cell per method/rate on one shared host and
does not establish a universal engine ranking.

## Reproduction and validation

Follow [README.md](README.md) for the pinned local reporting environment, CUDA
setup, acquisition and isolated replication commands. Saved prepared features
suffice for regenerating exact scores, analyses and the paper without raw recordings
or GPU inference:

```sh
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli evaluate --run-id minimum_v1
MPLCONFIGDIR=.local/matplotlib PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli analyze --run-id minimum_v1
PYTHONPATH=src .venv/bin/python -m temporal_evidence.analysis.publication
PYTHONPATH=src .venv/bin/python -m temporal_evidence.analysis.measurements
bash paper/build.sh
PYTHONPATH=src .venv/bin/python scripts/check_manuscript.py
```

The publication gate refuses incomplete runs. All 47 local tests pass; live Neo4j
fixture validation also passed. Dashboard tests exercise actual correction,
restoration and unresolved-claim operations. A browser inspection checked the
review interface. [Scripted examples](artifacts/review_examples) include surviving
alternative support and a mistaken rejection; no reviewer performance is claimed.
PDF checks verify generated hashes, anonymous author metadata, embedded fonts,
resolved references, no overflowing boxes, 20 main pages, and all five figures
and fourteen tables. Rendered figures and tables were visually inspected.

Raw provider recordings, model weights and credentials are excluded from Git.
Local PPG-DaLiA acquisition used the author archive after UCI downloads stalled;
the pod later obtained a separate UCI archive. The [archive comparison](artifacts/manifests/acquisition/ppg_dalia_archive_equivalence.json)
confirms identical hashes for all 15 subject pickles and the shared README.
Both source manifests are preserved. Rebuilding features should occur in a separate
workspace because extraction timings would change otherwise identical episode JSON.

## Scope and submission status

Protocol choices and reporting clarifications are recorded in [DECISIONS.md](DECISIONS.md).
The study has one generation seed, small participant cohorts, a narrow numerical
contract, controlled replay faults, and a single deployment. It does not establish
physiological accuracy, clinical safety, aviation readiness, human review benefits,
or an intrinsic graph-storage factuality advantage. Expanded seeds, another
generator, review-budget simulations and a human study are optional extensions
and were not run.

The [conference call](https://bdcc-conf.eai-conferences.org/2026/call-for-papers/)
was rechecked on 29 September 2026: the full-paper date is 30 September, with
anonymized English submissions and 12–20 main pages excluding references and
appendices. The exact upload cutoff/timezone remains unverified. The draft uses
the linked official template and discloses substantive AI assistance. Human
authors still need to review and approve any submission; no upload was attempted.

All study inference and its dedicated resource monitor have finished. The provided
pod remains available; it was not terminated. Repository changes are made directly
on `main`, as requested.
