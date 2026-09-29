# Protocol decisions

## 2026-09-28 — Initial execution

- User authorized implementation and direct pushes to `main`. No branches.
- Minimum study only: exactly synthetic_physiology_streams_v1, WESAD, and
  PPG-DaLiA; B0, B1, B2, M1, B3; 20 test episodes per source and four variants.
- Available GPU is RTX 5090, 32,607 MiB VRAM. Test BF16 Qwen3-8B at reduced
  concurrency before considering any quantization; no CPU model offload.
- Available disk is an approximately 75 GiB container overlay, below the suggested
  100 GB persistent allocation. Store original archives plus selected synchronized
  recording files, monitor free space, and copy manifests and experimental outputs
  to the local repository incrementally. Persistence across pod deletion is not
  assumed. Do not create another paid resource.
- Docker and Java are absent. Install Neo4j Community as a local tar distribution
  with a dedicated Java runtime. Bind research services to loopback.
- Freeze all selected subjects before inspecting test outcomes. Keep test waveforms
  separate from development tuning; structural inventories may include both splits.
- Progress percentages estimate completion of the plan's gates, not scientific
  success or percentage of generator calls. Track actual call counts separately.

## 2026-09-28 — Acquisition and runtime repairs

- WESAD's author HTML retains a commented-out obsolete archive link. Resolve only
  active links. HTTP/1.1 avoids a pod-side HTTP/2 download failure.
- WESAD downloaded locally; original archive and synchronized recordings are hashed.
  Slow pod transfers motivate local host-side numerical feature extraction. Neural
  generation remains exclusively on the pod GPU. Numerical extraction is not a
  trained model; compare a fixed sample with CUDA calculations before freezing.
- Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218` downloaded through
  parallel resumable byte ranges, independently of inference installation.
- Reuse the pod's existing PyTorch 2.8.0+cu128 and CUDA libraries through a Python
  3.12 virtual environment with system site packages. This replaces the initial
  unfinished Python 3.11 environment, avoiding redundant CUDA downloads. Record
  the entire resolved environment and test GPU placement before any generation.
- The generated explanation is required to concatenate its claim sentences.
  Checked methods retain only supported claim sentences after the bounded repair.
  Keep original paragraph output and discrepancies for evaluation. Lexical checks
  are limited; a separately pinned GPU model will perform the required auxiliary
  fidelity audit. No human annotation is claimed.
- UCI's PPG-DaLiA packaged and legacy archive downloads stalled repeatedly. Use the
  unchanged original archive linked from the authors' PPG-DaLiA page, and record
  both the UCI CC BY 4.0 statement and the author's non-commercial research terms.
- Select two episodes at 25% and 75% of each recording's common channel duration,
  rounded down to the 5-second update grid. Require at least 600 seconds; all
  acquired recordings satisfy this. Selection uses duration, not model failures,
  protocol labels, or held-out outcomes. Target windows are 30 seconds and comparison
  windows are the strictly preceding 120 seconds. Prepare seven 5-second updates
  ending at each target time, with four paired replay variants.
- Native wrist EDA is reported in uS. WESAD acceleration uses recorded 1/64g
  units; PPG-DaLiA's synchronized acceleration is in g (verified below).
  Synthetic units are explicitly marked. Spectral pulse/respiration frequency
  estimates require concentration >= 0.5; these are simple recording summaries,
  not validated physiological truth or a replacement for reference heart rates.
- WESAD's extracted synchronized pickles were verified and removed as redundant
  cache copies after preparation; the original hashed archive is retained. Adapters
  support direct reading from that archive. This recovered 12.88 GiB of local disk.
- Use pip for the system-site-packages overlay: uv's installer redownloaded existing
  CUDA dependencies. The tested final environment will be recorded before freezing.

## 2026-09-28 — Development audit before any model evaluation

- Verified PPG-DaLiA ACC scaling using development subject S2: 300 synchronized
  samples multiplied by 64 exactly match original raw ACC.csv at sample offset
  4416. Use g for the synchronized pickle, while the raw CSV uses 1/64g.
  Evidence is in `artifacts/manifests/ppg_acc_unit_verification.json`. Rebuilt all
  prepared episodes before protocol freeze; no held-out outputs existed.
- Channel-fault replays now write separate hashed NumPy arrays. Feature revisions
  cite new observation versions referencing the altered arrays; restoration points
  back to the original recording. Hidden intervention labels stay evaluator-only.
- Repeated revisions revisit dependencies on all earlier versions of the logical
  evidence item, preserving immutable citations while handling v1 -> v2 -> v3.
- Implemented an independent evaluator that reconstructs snapshots from immutable
  events without importing the runtime replay or validation modules. Required fact
  recall counts answerable slots; empty answers do not receive a zero claim-error
  rate. Persistent correction results retain explicit conditional denominators.
- The pilot includes 100 batched development cases plus a separate 20-request
  concurrency-one workload. Both include actual bounded-repair costs. No hourly
  price has been supplied, so report observed time and tokens without invented cost.

## 2026-09-28 — Live pilot and prospective design corrections

- CUDA verification measured 8,190,735,360 BF16 parameters and first-forward tensors
  on cuda:0. Neo4j Community 5.26.0 and indexed SQLite produce identical full
  correction assessments. Both batch revision lookups and assessment writes.
- Pilot v1 (512 output tokens) produced 67 truncated initial outputs and 71 failed
  final cases out of 100. Retain all candidates, repairs and failures. A completion-time
  config hash originally captured the later development config; preserve the emitted
  summary and an explicitly corrected hash verified against all recorded requests.
  Subsequent pilots snapshot configuration and source hashes before any requests.
- Pilot v2 increases the common limit to 1,024 tokens. Development inspection finds
  whitespace loops after the claims array: decoder grammar alone does not explain
  the remaining required keys to the model. Add those keys and all claim fields to
  the shared prompt; enforce the intended maximum of three claims in the schema.
  Use a uniform 1,536-token ceiling for the final development pilot and prospective
  run, with a 4,096-token input budget. No test generations have been inspected.
- Replace deterministic even/odd fault and question assignments with independent
  seeded rank schedules. Every source retains 20 test episodes, five of each family,
  and ten missingness/ten corruption interventions. Both fault types occur in every
  held-out source/family group. Store the complete assignment table before testing.
- Correct raw scalar sample accounting: feature computations process 360 seconds
  per channel including repeated windows and the fault replay; the unique original
  recording interval spans 150 seconds. These counts exclude full-file decoding and
  must not be confused with ingested derived events or independent participants.
- Batch four independent scenarios through a shared four-request semaphore; retain
  sequential checkpoints within each scenario. The final pilot measures this exact
  schedule. Interactive requests remain concurrency one.
- Persist actual recomposed explanation versions when unsupported claims are
  withdrawn or restored, with links to the previous immutable text.
- Use a separate systems workload at 1, 5 and 20 events/s, 60 seconds per cell,
  independently scheduled arrivals, database-specific retrieval, and four concurrent
  GPU requests. Its separate maximum is 472 GPU calls including validation repairs.
- The auxiliary verifier is separately pinned Qwen2.5-3B-Instruct, BF16 on CUDA,
  with 60 stratified final explanations and four calibration examples. Report this
  as automated annotation; sharing the Qwen family limits verifier independence.
- Pilot v2 completed 100 initial cases and 20 interactive requests: five initial
  truncations, one failed final case, and 33 batch repair calls. Its source snapshots,
  original episode inputs and raw outputs are retained separately from the final
  balanced schedule. Pilot v3 additionally uses vLLM's verified
  `--guided-decoding-disable-any-whitespace` option with xgrammar. This constrains
  JSON formatting uniformly across methods, not the numerical answers.
- The pre-freeze gate requires the complete 100-case pilot, 20 interactive requests,
  matching configuration/source hashes, zero initial truncations, and at least 95
  parsed final answers. Reliability/usefulness results are still reported even when
  the model or validator loses required information; format success is not accuracy.
- All numeric claim intervals in the bounded output contract refer to the requested
  target; comparison evidence may include the earlier baseline. An unqualified
  baseline value presented as the requested EDA median is a time-scope error.
  Report metrics as query-scoped evidence faithfulness, not physiological truth.
- Request journals rotate at 8 MiB while retaining ordered start/finish records,
  allowing complete raw outputs to be pushed to Git without oversized individual
  files. Interrupted requests with unknown outcomes are retained and not repeated.
- Pilot v3 completed with 100 initial cases, 51 batch repairs, zero initial
  truncations, zero failed final cases and 20 interactive requests. Its measured
  batch schedule projects 3.10 hours for the minimum study. Interactive median
  and p95 latency were 13.29 and 17.04 seconds, including repairs.
- The pre-freeze systems smoke test exposed an ambiguous reference-slot lookup:
  the symbolic fixture contains alternative support and an intermediate difference
  with the same quantity label. Define its two answer slots using the actual
  retrieved target and baseline operands. Retain the failed smoke run and the
  successful two-request-per-backend repeat. Request-snapshot adequacy is labeled
  explicitly; log the latest ingested event index at generation completion so
  delayed replacements can also be examined for staleness.
- Rerun the complete development pilot as `pilot_v4` after that systems-only fix,
  then freeze all source hashes. No held-out generation occurred before this fix.

## 2026-09-28 — Frozen run and reporting boundary

- Pilot v4 passed with 100 initial cases, 52 repairs, no initial truncations or final
  failures, and 20 interactive requests. The frozen held-out run started at
  2026-09-29 01:14:46 UTC with protocol hash
  `a22b68b4e3d33c7cbcaa253a6af27232a574a69692b5dcb793191ee1d2ceef63`.
- Development of the dashboard, manuscript and reporting scripts continues outside
  the frozen runtime. No prompt, threshold, case, inference setting or runtime
  predicate is changed after freezing. Local verification checks every frozen hash.
- The dashboard appends isolated ReviewEvent and explanation versions. Scripted
  examples are labeled automated demonstrations; no human study is conducted.
  A reviewer-supplied correction is not independently certified by the interface.
- Add a descriptive completion-time check for the separate systems workload, using
  its recorded completion event index. Remap cited versions to the latest known
  numerical values and report replacements that were adequate for their request
  snapshot but stale at completion. Preserve the frozen request-snapshot adequacy
  and deadline metrics unchanged. This is additional reporting, not a tuned metric.
- Before scoring held-out outcomes, a reporting review identified that the initial
  bootstrap implementation pooled conditional denominators within subjects. Match
  the prospective plan literally: compute each metric within a base episode, pair
  methods on that episode, average paired differences within subjects, then sample
  subjects. For conditional correction, retain only episodes with defined
  denominators in both methods; disclose eligible episodes and subjects. Targeted
  tests cover unequal episode denominators and disjoint conditional eligibility.
  This changes no experimental inputs or runtime predicates. The historical
  pilot-v3 analysis predates this reporting repair and remains preserved as such.
- Add a descriptive accounting category for persistent claims whose sole later
  exact-check error is `dependency`. This exposes the distinction between a
  generator-declared prerequisite and an independently necessary derivation.
  Do not change the frozen support contract, primary correction metrics, or
  bootstrap contrasts; do not infer semantic necessity from graph membership.

## 2026-09-29 — Completed main run and interpretation

- All 3,600 planned cases are accounted for: 3,597 completed and three retained
  transport ReadErrors, one per source in B0. The request journal contains 5,220
  attempts, including 1,620 bounded repairs. Do not retry the failed cases or tune
  the frozen runtime. Direct and transitive checked methods have identical
  correction completeness in this generated waveform task.
- Inspection after the locked main run shows that the target-interval contract
  rejects some **correctly labelled** baseline statements, not only misleading
  time attribution. Add a clearly post-hoc descriptive breakdown: direct numeric
  observations with only `wrong_time`/`numeric_or_interval` errors that pass the
  same exact checks at their own stated interval and original knowledge time.
  These account for 107/254 synthetic, 115/278 WESAD, and 111/267 PPG-DaLiA B0
  invalid claims. Declared dependencies can propagate this rejection to otherwise
  correct comparisons. Preserve all original metrics and clarify in the abstract,
  results, discussion and report that they are contract-compliance measures, not
  unrestricted factuality or hallucination estimates.
- Token accounting now explicitly counts attempts without returned usage. Their
  server-side token cost is unknown; reported token sums include available usage
  only. This is a reporting clarification and does not change any case outcome.
- Move supplementary generation, scope-breakdown, storage-outcome and completion-
  staleness tables into an appendix while retaining all principal outcomes in the
  main manuscript. Zero-width bootstrap intervals are described as resampling
  identical observed subject differences, not proof of equivalence.
- All six systems cells complete with logical graph/relational agreement. Every
  one of 236 displays contains only the target observation, omitting the requested
  difference; none is an adequate replacement. Label the measured latency as
  candidate completion, with successful-replacement latency undefined. The
  descriptive staleness count cannot demonstrate retained usefulness in this case.
- The 60-output verifier audit parses completely and passes four diagnostics, but
  has 14 disagreements with exact checks, including visible null/rounding mistakes
  and missed numerical/reference errors. Retain all annotations and describe the
  verifier's limited value rather than treating it as semantic ground truth.
- Preserve both local author-archive and pod UCI PPG-DaLiA acquisition manifests.
  Their ZIP bytes differ, but all 15 subject pickles and the shared README have
  identical hashes. The frozen prepared feature inputs are unchanged.
- The completed manuscript uses the official template with 20 main pages and
  three additional reference/appendix pages. Mechanical and visual checks are
  recorded separately from scientific author review and conference submission.
