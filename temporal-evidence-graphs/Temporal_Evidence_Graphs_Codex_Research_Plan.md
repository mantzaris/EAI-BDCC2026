# Temporal Evidence Graphs for Reliable Generative Explanations of Physiological Data Streams

Research and implementation plan for Codex

Prepared: 2026-09-28

Target: EAI BDCC 2026

Status: Prospective plan. No experiments or results are claimed in this document.

## 1. Objective and scope

Implement and evaluate a GPU-based generative AI system that produces inspectable explanations of physiological data streams. Maintain a temporal graph connecting observations, computed features, generated claims, and explanations. When evidence arrives late, is corrected, or becomes unusable, identify affected claims, update their status, and repair the explanations that depend on them.

Use exactly three benchmark sources in the core study:

1. One synthetic benchmark with known evidence dependencies and controlled faults.
2. WESAD, a real laboratory physiological dataset.
3. PPG-DaLiA, a real physiological dataset recorded during daily activities.

The primary research question is:

> Does explicit maintenance of temporal evidence dependencies improve the reliability and correction behavior of generated monitoring explanations, and what computational advantage or disadvantage does a graph implementation have relative to a comparably capable relational implementation?

The contribution is the evaluated method for maintaining and revising explanations under changing evidence. A graph database, a dashboard, or an LLM producing triples is not sufficient as the contribution by itself.

Build a complete, reproducible experimental package suitable for writing a conference paper. Prioritize measured results on all three benchmark sources before extensive interface development.

## 2. Connection to the motivating proposal

The motivating proposal concerns interpretable monitoring of physiological and behavioral signals, individual change over time, evidence-linked explanations, and human review. It places the generative query and explanation layer outside the model that produces readiness assessments.

This study evaluates that explanation and monitoring layer. Its reusable components are:

- Evidence provenance from observations to generated claims.
- Temporal validity and correction tracking.
- Explicit handling of absent or unreliable evidence.
- A review interface that highlights affected claims and their dependencies.
- Reproducible reliability and latency measurements.

The core paper does not require an aircrew readiness classifier. It does not establish aviation readiness, diagnosis, or improved human decision performance. The physiological datasets provide real signals for evaluating the explanation infrastructure. Keep the paper focused on this component and its measured properties.

## 3. Instructions to the implementing Codex agent

Read this document completely before implementation. Inspect the existing repository and its applicable AGENTS.md instructions, preserve unrelated work, and reuse compatible infrastructure.

Implement the minimum study first, then expand only after its outputs are complete. Maintain a concise STATUS.md with completed stages, commands, run identifiers, unresolved issues, and the next executable step. Record changes to the planned protocol in a dated DECISIONS.md.

Required operating rules:

- Run all LLM inference, neural verification if used, and neural training if added on CUDA GPUs. Do not silently fall back to CPU inference.
- Use the available RunPod GPU environment or produce exact commands for that environment if access has not yet been supplied. Creating this plan does not itself launch paid compute.
- Host parsing, file I/O, database transactions, dashboard serving, and statistical aggregation may use the host CPU. The experiment's model computation must be GPU-based.
- Implement exactly one synthetic benchmark and both named real datasets. Do not silently replace a missing real dataset with generated data or drop a dataset to meet the deadline.
- Keep real recordings immutable. Store replay faults, corrections, and derived files separately.
- Freeze the test manifest, prompts, thresholds, and model configuration before the final evaluation.
- Do not tune against held-out outcomes, fabricate results, hide failed generations, or stop experiments because an interim result is favorable.
- Preserve negative findings. A relational implementation matching or outperforming the graph implementation is an informative result.
- Continue routine implementation and repair work autonomously. Report a concrete blocker only when access, necessary input, or an external dependency is actually missing.

## 4. Questions and planned comparisons

| Question | Main comparison | Evidence needed |
| --- | --- | --- |
| Does evidence checking improve generated explanations? | Recent-context generation versus checked flat evidence | Unsupported claims, coverage, valid references |
| Do temporal dependencies improve correction behavior? | Graph without transitive propagation versus full temporal graph | Correction completeness, residual errors, collateral revisions |
| Does a graph database provide an implementation advantage? | Full graph versus relational dependency tracking | Equivalent logical results, update latency, memory, throughput |
| Are displayed dependencies behaviorally meaningful? | Targeted evidence intervention versus irrelevant intervention | Required explanation changes and unwanted changes |
| Can the system sustain stream updates? | Increasing offered load at fixed hardware | Queue growth, p50/p95 latency, deadlines, achieved throughput |
| Does prioritization help a limited review process? | Impact ranking versus uncertainty-only and random ranking | Error resolution under a simulated review budget |

The last question is an extension. It must be labeled a simulated review experiment unless an actual user study is conducted separately.

Predeclare two principal contrasts: full graph versus graph without propagation for correction behavior, and full graph versus checked flat evidence for overall explanation reliability. Treat graph versus relational dependency tracking as a separate systems comparison. Do not interpret that comparison as proof that graph storage intrinsically improves factuality.

## 5. Dataset selection and acquisition

### 5.1 Synthetic benchmark

Working identifier: synthetic_physiology_streams_v1.

Create a controlled generator with physiological-style waveforms, feature records, event timestamps, ingestion timestamps, and an evaluator-only dependency oracle. It is a test environment for evidence maintenance, not a validated physiological simulator.

For each virtual subject, generate a 30-minute session containing:

- A cardiac pulse-like signal whose frequency changes across piecewise-smooth states.
- A respiration-like oscillation with changing frequency and amplitude.
- An EDA-like slow component and discrete response-like events.
- A three-axis motion channel with independent movement periods.
- Subject-specific offsets and noise levels.

Suggested generator equations, with all parameters stored in the manifest:

```text
latent_state[t] = bounded piecewise-smooth process
cardiac_rate[t] = subject_cardiac_baseline + cardiac_loading * latent_state[t] + noise[t]
respiration_rate[t] = subject_respiration_baseline + respiration_loading * latent_state[t] + noise[t]
eda[t] = subject_eda_baseline + slow_drift[t] + sum(event_amplitude * response_kernel[t - event_time]) + noise[t]
motion[t] = activity_process[t] + sensor_noise[t]
```

Generate waveforms at documented synthetic sampling rates, for example 128 Hz cardiac, 32 Hz respiration, 8 Hz EDA, and 32 Hz motion. These are generator choices. They are not device specifications or scientific claims about the real datasets.

Use combinations where motion and the latent physiological state vary independently. Include no-change intervals, genuine feature changes, conflicting sensors, and changes that remain supported after one source is removed. Avoid making every artifact imply a physiological change.

Create 10 development subjects and 10 held-out test subjects using non-overlapping seed namespaces. Use seeds 101-110 for development and 1001-1010 for test. Assign separate seeded random streams to waveform generation, fault placement, question selection, and generation sampling.

The oracle records exact numeric values, revision histories, and the dependencies needed for benchmark queries. Keep latent variables and fault metadata out of model prompts and runtime validation. The evaluator may access them.

Two different synthetic evaluations are required:

1. Symbolic evidence-maintenance tests with exact feature records and dependency truth.
2. Waveform-to-feature replay tests exercising extraction, timing, and explanation generation.

These are two modes of the same synthetic benchmark, not additional datasets. Separate their results.

### 5.2 WESAD

Official dataset record: https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detection

Current author landing page reached through the official record: https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html

WESAD contains 15 participants with chest and wrist physiology and motion. Useful channels include ECG, BVP, EDA, respiration, and acceleration. The author page links the original archive, approximately 2.5 GB compressed. Its stated use terms permit scientific, non-commercial use with attribution. Save those terms with the acquisition manifest. Do not assume commercial deployment rights from this research access. [R2, R3]

Acquisition requirements:

- Resolve the original archive from the author page at execution time; support a user-provided local archive as an alternative.
- Download resumably, record the resolved URL and date, calculate SHA-256, and preserve the bundled README.
- Inventory actual subject IDs, channel names, units, sampling rates, lengths, and label codes from the files and documentation.
- Do not assume a generic tabular UCI loader can retrieve the original waveform archive.

Use WESAD primarily for evidence-linked explanations of observed changes and missing or revised measurements. Protocol labels may stratify evaluation. They must remain hidden from the explanation model unless a separately labeled task explicitly supplies them as context. Laboratory stress labels do not establish the cause of each local signal fluctuation.

### 5.3 PPG-DaLiA

Official dataset record: https://archive.ics.uci.edu/dataset/495/ppg+dalia

Download endpoint linked by UCI when checked: https://archive.ics.uci.edu/static/public/495/ppg%2Bdalia.zip

PPG-DaLiA contains 15 participants performing daily activities, with wrist PPG and motion measurements and chest signals. ECG-derived reference heart-rate information supports assessment of estimates during movement. UCI lists an approximately 2.7 GB archive and CC BY 4.0 licensing. [R4]

Acquisition requirements:

- Download the official archive resumably and preserve its README and license.
- Resolve exact field names, reference-window timing, activity codes, units, and synchronization from the archive. Do not guess label alignment from array length alone.
- Distinguish independent reference targets from runtime observations. Reference labels used by the evaluator must not leak into model context.
- Activity annotations may stratify test cases. Do not equate movement or activity with stress, sensor failure, or an invalid physiological observation.

This dataset provides a second operating condition: explanations must distinguish observed changes from uncertainty associated with motion and disagreements between sources.

### 5.4 Why these three sources

| Source | Role in this study | Ground truth available |
| --- | --- | --- |
| Synthetic benchmark | Controlled dependencies, revisions, and scaling | Exact generated values and dependency oracle |
| WESAD | Laboratory physiological monitoring | Recorded values, protocol metadata, and deliberately controlled replay revisions |
| PPG-DaLiA | Daily activity and motion interference | Recorded values, documented reference information, and deliberately controlled replay revisions |

The real datasets are complementary recordings, but use related wearable hardware and collection traditions. Do not describe them as covering all sensor domains. High sample counts do not create large independent participant cohorts.

### 5.5 Subject partitions

For each real dataset, naturally sort the verified available subject IDs and apply a fixed permutation using numpy.random.Generator(PCG64(20260928)). Assign five subjects to development and ten to held-out testing. Save the resulting IDs before inspecting test outcomes.

No LLM training is required in the core study. The development partition is for thresholds, prompts, synchronization checks, and pilot throughput. The test partition is for the locked experiment. All variants of one recording segment stay in the same partition.

Do not randomly split overlapping windows across partitions. If an optional predictor is trained later, create a separate subject-wise training/validation/test or nested cross-validation protocol and label it as an extension.

## 6. Streaming protocol and feature extraction

### 6.1 Time semantics

Every incoming item has both event time and ingestion time. Event time describes when the observation occurred. Ingestion time describes when the system learned it. A correction can arrive now while referring to an earlier window.

Use relative session time for datasets without authentic wall-clock timestamps. Preserve native sample indices and sampling metadata. Never assign invented calendar times as though they came from the recordings.

At simulated wall time t, expose only records whose ingestion time is at most t. Future recordings, later corrections, and reference targets remain unavailable to runtime components.

Historical queries use the version known at the requested knowledge time. Current queries use the currently accepted evidence for the requested event interval. Do not mark an old observation false simply because it is old: distinguish historically valid evidence from evidence that is too old to answer a current-state question.

### 6.2 Feature windows

Core defaults:

- Primary feature window: 30 seconds.
- Feature update interval: 5 seconds.
- Trailing comparison interval: 120 seconds, strictly preceding the target interval.
- Warm-up: enough preceding data to populate the target and comparison intervals.
- Exclude early windows with insufficient history using a recorded rule.

Use documented native rates and channel-specific processing. Avoid resampling all channels to the highest rate. Filtering must be causal or restricted to a fully observed completed window; never use future samples across the replay boundary.

Minimum features:

- EDA median, interquartile range, and change from the preceding interval.
- Cardiac estimate and explicit provenance, if the extraction quality is adequate.
- Respiration estimate and explicit provenance, if adequate.
- Acceleration magnitude variability.
- Missing fraction, clipping fraction, and simple measurable signal-quality indicators.

Implement tensor-compatible window extraction and numerical processing in PyTorch/CUDA where practical. Validate a small fixed sample against a trusted reference calculation. Keep decoder and data-loading time separate from GPU compute time.

Do not add an elaborate physiological model just to use the GPU. The generative inference is already the main GPU workload. If rate extraction is unreliable, retain directly verifiable numerical features rather than inventing heart-rate or respiratory-rate estimates.

Quality indicators are fallible measurements, not perfect truth. Motion by itself is an uncertainty cue. An explicit invalidation notice or a documented numerical inconsistency can justify stronger conclusions.

## 7. Data model and database

Use Neo4j Community as the primary property graph database. Pin the tested database and driver versions. Neo4j supports container deployment, but verify whether Docker is available in the actual RunPod environment. If nested Docker is unavailable, use a supported local server installation or an already available separate database service. Do not leave the core experiment dependent on an unavailable container daemon. [R9]

Use one reproducible graph schema and a storage interface that also supports the relational control.

| Node type | Purpose |
| --- | --- |
| Subject | Dataset-scoped subject identity |
| Sensor | Channel identity and measurement metadata |
| Observation | Immutable record or recording-window reference |
| FeatureVersion | Versioned computed value and its source window |
| ClaimVersion | LLM-proposed statement and machine-checkable semantics |
| ExplanationVersion | Generated response with links to claims |
| ReviewEvent | A human or simulated review action, explicitly identified |

Required relations include OBSERVED_BY, FOR_SUBJECT, DERIVED_FROM, SUPPORTS, CONTRADICTS, DEPENDS_ON, SUPERSEDES, CONTAINS, and REVIEWED_BY_EVENT. State the edge direction in the schema. Define DEPENDS_ON from a dependent item to the item it requires; reverse traversal finds potentially affected descendants.

Minimum record fields:

```json
{
  "record_id": "wesad/S02/window_000120/eda_median/v1",
  "dataset_id": "wesad",
  "subject_id": "S02",
  "session_id": "session_1",
  "event_start_seconds": 120.0,
  "event_end_seconds": 150.0,
  "ingested_at_seconds": 151.0,
  "version": 1,
  "record_type": "feature",
  "quantity": "eda_median",
  "value": 1.25,
  "unit": "unit_from_dataset_metadata",
  "quality_state": "observed",
  "source_ids": ["source_window_identifier"],
  "supersedes_id": null,
  "extractor_version": "git_commit_and_config_hash"
}
```

The example is schematic. It is not an actual WESAD observation. Replace placeholder units using verified metadata.

Maintain immutable versions. Never silently overwrite a value that an earlier explanation cited. Distinguish evidence status from claim status:

- Evidence: available, superseded, explicitly invalidated, or missing.
- Claim: pending, supported, contradicted, unsupported, or needs_review.
- Freshness: a separate query-relative property.

Keep generation candidates separate from accepted graph facts. An LLM may propose a relation; it may not declare that relation verified merely by assigning a confidence score.

Store raw waveforms outside the graph, with hashes and sample-range references. Store features, events, and dependencies in the graph. Index dataset, subject, session, event interval, ingestion time, record ID, and version.

## 8. Generative component and runtime validation

### 8.1 Model and output contract

Primary model: Qwen/Qwen3-8B, pinned to an exact model revision. Use a GPU inference server such as vLLM. The model card documents vLLM deployment and a non-thinking mode suitable for bounded-output generation. [R7]

Use the same generator, output schema, context limit, sampling settings, and query wording across conditions. Suggested starting limits are 4,096 input tokens and 512 output tokens. Measure truncation in development; increase the output limit consistently if necessary before freezing the protocol.

Start with non-thinking mode, temperature 0.7, top_p 0.8, top_k 20, and generation seed 20260928. These are initial configuration choices consistent with the model card's non-thinking guidance, not optimized settings. Any development change must be applied consistently, documented, and frozen. Save the server's effective settings because a requested seed does not guarantee identical results across different batching or hardware configurations.

Use structured decoding where supported by the pinned inference stack. Structured JSON is a format constraint and does not ensure factual correctness. [R8]

Require a small list of claims plus a short explanation:

```json
{
  "claims": [
    {
      "claim_id": "candidate_1",
      "claim_type": "numeric_observation",
      "subject_id": "dataset_scoped_subject",
      "quantity": "eda_median",
      "event_start_seconds": 120.0,
      "event_end_seconds": 150.0,
      "operator": "approximately_equal",
      "value": 1.25,
      "unit": "verified_unit",
      "evidence_ids": ["feature_version_id"],
      "depends_on_claim_ids": [],
      "sentence": "The recorded window has an EDA median of 1.25 in the reported units."
    }
  ],
  "answer_status": "answered",
  "explanation": "Short explanation using only the listed claims.",
  "unresolved_evidence_ids": []
}
```

Support numeric_observation, trend, comparison, evidence_conflict, missing_evidence, and revision_effect claim types. Use descriptive variable names throughout implementation. Keep free-form clinical or causal interpretation outside the core output contract.

No benchmark template may supply the expected answer or the hidden fault label to the generator. Questions should permit answered, partially_answered, and insufficient_evidence responses.

### 8.2 Validation checks

Runtime checks may use only currently ingested observations and published processing rules. They check:

- Evidence identifiers exist and belong to the correct dataset, subject, and session.
- Cited event intervals match the statement.
- Units and numerical values agree within predeclared tolerances.
- Trend and comparison statements use the required target and comparison values.
- Explicitly invalidated or superseded evidence is not presented as current support.
- Required dependencies exist and are currently supported.
- A relation labeled causal is not inferred from an ordinary observational association.

Start with a numerical tolerance of max(1e-6, 0.01 * abs(reference_value)) for direct numerical reporting, then add quantity-specific tolerances only if justified on development data. Log tolerances in configuration. Do not use this tolerance as a clinical threshold.

Unsupported interpretive claims are marked unresolved rather than declared false. Valid reference IDs are necessary but not sufficient for support. A citation to an unrelated value does not validate a statement.

Keep raw candidate output, validation decisions, repair prompts, repaired output, and final displayed output. Allow at most one repair generation per query in the core study. Apply the same repair allowance to checked conditions. Record all calls and count repair cost in latency and GPU time.

Prevent prose escaping validation: score the claim fields and the associated natural-language sentences. Preserve the full explanation for a separate fidelity audit. If the prose says more than the structured fields justify, count it as a discrepancy; do not score only the JSON and ignore contradictory prose.

## 9. Temporal revision algorithm

When a new version or invalidation arrives:

1. Validate and append the incoming event.
2. Link it to the superseded record, preserving the old version.
3. Find claims and features that directly depend on the changed record.
4. Traverse reverse dependencies to enumerate potentially affected items.
5. Recompute affected derived values and support predicates in dependency order.
6. Retain claims that still have adequate independent support.
7. Mark genuinely affected explanations as needing review immediately.
8. Regenerate or retract those explanations within the configured processing budget.
9. Store the new explanation version and its difference from the earlier version.

Do not blindly delete every reachable item. An OR-supported claim can remain supported if another valid source is sufficient. For AND-supported comparisons, all required operands must remain valid. Store the support expression explicitly.

Core generated dependency structures should be acyclic. Reject or mark proposed cycles for review; record cycle handling rather than letting traversal loop indefinitely.

A stale observation may still answer a historical question. A current-state question requires evidence inside its stated freshness window. Set query-specific freshness requirements in the task manifest, rather than one arbitrary expiry time for every kind of fact.

Useful pseudocode:

```python
def apply_revision(revision_event, evidence_store, dependency_index):
    changed_record = evidence_store.append_revision(revision_event)
    affected_identifiers = dependency_index.reverse_reachable(changed_record.previous_id)
    ordered_identifiers = dependency_index.dependency_order(affected_identifiers)
    changed_claims = []
    for identifier in ordered_identifiers:
        previous_state = evidence_store.get_support_state(identifier)
        current_state = recompute_support_from_available_evidence(identifier, evidence_store)
        evidence_store.append_support_assessment(identifier, current_state)
        if materially_changed(previous_state, current_state):
            changed_claims.append(identifier)
    return schedule_affected_explanations(changed_claims, evidence_store)
```

This pseudocode defines behavior. It is not a completed implementation or a claim of novelty.

## 10. Experimental conditions

Implement five conditions using the same underlying input stream and generator.

| ID | Condition | Required behavior |
| --- | --- | --- |
| B0 | Recent structured context | The LLM receives recent available observations with IDs and timestamps; no post-generation semantic verification |
| B1 | Checked flat evidence | Indexed tabular records, timestamps, version selection, identical direct claim checks, and direct-reference invalidation; no transitive dependency maintenance |
| B2 | Temporal graph without propagation | Graph storage and the same direct checks; direct references update, but transitive revision propagation is disabled |
| M1 | Full temporal evidence graph | Direct checks plus explicit dependency maintenance, transitive revision, and affected-explanation repair |
| B3 | Full relational dependency tracking | Relational evidence and dependency tables with indexes and recursive traversal; logically equivalent checks and revision behavior to M1 |

B3 is a mandatory strong control. Give it appropriate indexes and recursive queries. Do not compare a tuned graph database with an intentionally inefficient full table scan and attribute the difference to graph structure.

Two evaluation tracks avoid confounding representation and evidence selection:

1. Matched-evidence track: conditions receive the same admissible evidence set and equivalent serialized content at each checkpoint. This isolates checking and maintenance behavior.
2. Systems track: M1 and B3 perform their own storage queries and updates under a common workload. Compare correctness and operational cost separately.

B0 can run a fresh answer when queried, but does not repair old displayed explanations automatically. B1 and B2 perform only direct-reference updates. M1 and B3 propagate through intermediate claims. Score fresh answers and persistent displayed explanations separately.

For logical maintenance tests, replay a common fixed candidate-claim fixture into every condition so that differing initial generation does not determine which errors can be corrected. For end-to-end tests, retain each condition's own LLM output and score it against the same query requirements. Report both tests separately.

A GraphRAG-style retrieval baseline can be added after the minimum study. B2 is a custom temporal-graph ablation; do not label it a reproduction of Microsoft GraphRAG or Graphiti.

## 11. Faults, questions, and reference answers

### 11.1 Four replay variants per base episode

| Variant | Intervention | Observable information |
| --- | --- | --- |
| Clean control | Normal data plus a benign revision or irrelevant update | No required adverse change |
| Channel fault | Dropout, clipping, or added disturbance in one channel | Raw evidence and derived quality indicators; hidden fault label stays private |
| Delayed evidence | Delay a feature packet or quality update and vary arrival order | Original event timestamps and actual arrival times |
| Correction | Issue a revised value, source invalidation, or corrected channel identity | Explicit later correction event linking old and new versions |

Split the channel-fault variant evenly between missingness and corruption within the selected cases. For the core run use one predeclared severity per fault family; add a severity sweep only after completion.

Example development choices are a 15-second channel dropout, a 60-second packet delay, and a feature correction large enough to cross a predeclared trend boundary. Treat these as experimental settings, not characteristics of the original datasets. Record the precise intervention per case.

Construct three checkpoints per replay: before intervention, after the faulty or delayed state is visible, and after correction or an equally timed benign update. The control uses the same checkpoint schedule.

Some faults are impossible to identify from available evidence. Separate observable faults from hidden faults. Before an explicit correction arrives, assess whether a response faithfully describes the information available and acknowledges observable uncertainty; do not demand knowledge of a hidden corruption label.

For real data, a deliberately altered feature record tests response to a controlled replay revision. It is not evidence that the original dataset supplied erroneous physiological measurements.

### 11.2 Question families

Use four families with numeric answers or auditable support requirements:

1. Current evidence: What changed in the target window relative to preceding observations?
2. Evidence sufficiency: Which available channels support the stated comparison, and which are missing or unresolved?
3. Conflict and timing: Which observations disagree or refer to different intervals?
4. Revision impact: Which previously displayed statements remain supported after a specified evidence update?

Create multiple phrasings on development data and hold out some phrasings for test. Fix the family and required answer slots in each case manifest. Do not generate gold answers with the same LLM being evaluated.

Reference answers come from independently computed values, task specifications, and the event/revision log. An evaluator must reconstruct the appropriate snapshot from immutable events rather than read the method's support-status column as gold truth.

### 11.3 Minimum and expanded sample sizes

Minimum study:

- 20 base episodes per benchmark source, 60 total.
- For each real dataset, two non-overlapping base episodes per held-out subject where feasible.
- For synthetic data, two base episodes per held-out virtual subject.
- Balance the four question families within each source.
- Four replay variants per base episode: 240 replay scenarios total.
- Three checkpoints per scenario: 720 query checkpoints total.
- Five methods: 3,600 initial generator calls before repairs.
- One fixed generation seed for the minimum run; save all outputs.

With at most one repair for each query in the four checked conditions, the hard maximum is 2,880 repair calls, or 6,480 total generator calls. Fixed-fixture database tests do not require generation. Additional neural audit calls, if used, require a separate reported budget.

Prefer separated episode contexts; if any source recordings overlap across selected episodes, document the overlap and retain subject-level statistical clustering. All replay variants remain paired.

Expanded study, only after the minimum is complete: 100 base episodes per source and three generation seeds, with cost estimated from the pilot. Additional seeds measure generation variability, not new independent participants.

Selection must be decided from data availability and predeclared observable strata. Do not select test episodes because a baseline LLM fails on them. Do not quietly skip malformed outputs or difficult cases.

## 12. Metrics and statistical analysis

### 12.1 Reliability and usefulness

For each method, source, replay variant, and checkpoint, report:

- Claim error rate: unsupported, contradicted, numerically wrong, wrong-subject, wrong-time, or unfaithful prose claims divided by emitted checkable claims. Report components as well as the aggregate.
- Case error rate: fraction of query checkpoints with at least one incorrect displayed claim.
- Valid evidence-reference rate: cited references that exist and support the associated statement, rather than merely existing.
- Required fact recall: supported required answer slots supplied divided by required answer slots answerable from currently available evidence.
- Useful answer coverage: fraction of eligible queries receiving the required supported content.
- Abstention and partial-answer rates, split by answerable and unanswerable queries.
- Parse failure, truncation, timeout, and repair rates.

If no checkable claims are emitted, claim error rate is undefined for that answer, not zero. Such an answer contributes to coverage, abstention, and case completion metrics. Also report fixed-denominator outcomes per query to prevent short or empty outputs from appearing superior.

Primary reliability reporting uses paired changes in case error rate together with required fact recall. Never present an error reduction alone if useful coverage materially falls.

Distinguish source faithfulness from physiological estimation accuracy. An explanation can faithfully repeat a poor sensor estimate. Where PPG-DaLiA reference alignment is verified, optionally report heart-rate estimation error separately and assess whether explanations appropriately qualify observable evidence problems. Do not count agreement with a corrupted runtime feature as proof of physiological truth, and do not use the hidden reference to make an otherwise uninformed runtime validator appear accurate.

### 12.2 Correction and explanation behavior

- Correction completeness: affected claims correctly revised, retracted, or requalified by the deadline divided by claims that require a change under the evaluator's snapshot.
- Residual incorrect display: affected incorrect statements still shown as supported after processing.
- Collateral revision rate: unaffected claims incorrectly changed or withdrawn.
- Time to flag: correction ingestion to marking the affected explanation unresolved.
- Time to repair: correction ingestion to an adequate revised explanation.
- Evidence intervention response: required answer changes following a relevant intervention.
- Irrelevant intervention stability: unaffected answer content retained after a matched irrelevant intervention.

Use two correction targets: explicit dependency fixtures for testing maintenance, and generated explanations for end-to-end testing. If a condition produced no affected claims, report the denominator and mark conditional correction completeness undefined; do not award a perfect score.

These are measures of evidence traceability and behavioral response. They are not a complete account of the LLM's internal neural reasoning.

### 12.3 Systems outcomes

Report:

- Raw samples processed and derived events ingested as different counts.
- Graph nodes, edges, active claims, and revision-chain lengths.
- Event-to-flag, event-to-repair, retrieval, generation, and database-update p50 and p95 times.
- Achieved events per second, completed explanations per second, queue size, and deadline-miss rate.
- GPU model, VRAM peak, utilization, total GPU wall time, input/output tokens, batch size, and concurrency.
- Host memory and database storage size.

Core soft targets are flagging within 1 second and repairing within 5 seconds after correction arrival at a stated offered load. They are targets to measure, not assumed capabilities. If missed, report achieved latency and avoid an unsupported real-time claim.

Run open-loop load tests with arrivals scheduled independently of completions. Sweep 1, 5, and 20 derived events per second after a pilot; reduce or increase the sweep only before the locked systems run. Record the change. Use a fixed explanation demand, initially one request per 20 events, plus affected-explanation repairs. Allow backlog to accumulate and report it; a closed-loop test alone hides overload.

Replay at 1x for a streaming demonstration and accelerate replay for throughput. Treat duplicated streams as a systems load test, not additional independent physiological evidence.

### 12.4 Analysis units and uncertainty

Calculate paired method differences within each base episode and aggregate within subjects. For the real datasets, use a subject-clustered paired bootstrap with 2,000 resamples and 95% intervals, keeping all variants and checkpoints together. For synthetic data, cluster by virtual subject. With ten held-out subjects per real dataset, emphasize effect sizes and the limited precision of the intervals.

Report each source separately. An optional macro-average gives equal weight to the three sources; do not pool all waveform samples as independent observations. Predeclare multiplicity handling for the small set of confirmatory contrasts, for example Holm adjustment if reporting hypothesis-test p-values. Label the remaining analyses exploratory.

Never use GPU repetitions, overlapping windows, repeated prompts, or duplicated streams to inflate the independent sample count.

## 13. Independent evaluation and fidelity checks

Implement runtime validation and benchmark evaluation as separate modules with different inputs. They may share schema definitions and unit conversions, but the evaluator reconstructs reference answers from immutable source and replay logs. Runtime code cannot import evaluator-only labels.

Before final runs, validate known cases including:

- Correct citation ID but incorrect numerical statement.
- Correct value for the wrong subject or time window.
- Superseded evidence used in a historical query where it remains appropriate.
- OR-supported claim retaining independent evidence after one source is invalidated.
- A changed intermediate feature affecting several downstream claims.
- A benign correction that should not trigger withdrawal.
- Free-form explanation text contradicting otherwise valid structured fields.
- Out-of-order arrivals and duplicate revisions.

Audit at least 60 sampled final explanations, stratified across methods and sources, for agreement between prose, structured claims, and evidence. A researcher's annotation audit is distinct from a study of dashboard users. If no human annotation is available, use a separately pinned GPU verifier for an auxiliary audit and explicitly label the result automated. Do not claim human-rated explanation quality.

Do not use the generating LLM as the sole evaluator. If a second model is used, retain its prompts, revision, outputs, and disagreements with exact checks.

## 14. Dashboard and reviewer interaction

Implement a small local dashboard after the minimum experiment is running. Recommended scope is a Streamlit application or a similarly lightweight existing interface with a graph viewer and time-series panel.

Required views:

- An issue queue sorted by explicit evidence problems and downstream impact.
- A local graph centered on the selected claim, rather than the entire graph.
- Source waveforms or feature values with time windows and version identifiers.
- Before/after explanation differences.
- A review action to reject evidence, accept a correction, or mark an interpretation unresolved.
- A visible revision history showing the consequence of the action.

Show only the information needed for review: statement, support, conflict, timing, and affected explanations. Keep implementation logs in a separate diagnostics view.

The core deliverable demonstrates human-in-the-loop functionality. It does not claim improved human accuracy or faster human decisions.

Optional review-budget experiment: use known faulty evidence to simulate a perfect reviewer and compare three issue rankings: downstream impact, uncertainty-only, and random. Evaluate 1, 3, and 5 review actions per episode. Give all policies the same oracle correction operation and budget. Label perfect-reviewer results as an upper bound, not a user-study result.

## 15. GPU execution and resource control

Preferred starting environment:

- One CUDA-capable RunPod GPU with approximately 48 GB VRAM or more.
- Qwen3-8B in BF16, subject to the measured memory fit.
- At least 32 GB host RAM where available for loading recordings and serving the database.
- At least 100 GB persistent working storage for model weights, archives, extracted data, and logs; check actual free space before download.
- Persistent outputs across interruption or pod restart.

These are planning choices, not a promise of availability, cost, or throughput. RunPod documents GPU selection and storage options; use current availability when executing. [R10]

Before any production experiment:

1. Record nvidia-smi output and CUDA/framework versions.
2. Assert torch.cuda.is_available().
3. Verify the model's parameters and inference tensors are on GPU.
4. Pin model revision, tokenizer revision, inference package version, database version, and configuration hashes.
5. Run 100 representative development requests and measure throughput, latency, VRAM, output length, and failure rate.
6. Estimate total duration from observed requests per second, including expected repair calls and database work.

Planning formula:

```text
estimated_seconds = initial_calls / observed_initial_calls_per_second
                  + expected_repair_calls / observed_repair_calls_per_second
                  + measured_preprocessing_and_analysis_seconds
```

Do not estimate completion using theoretical token throughput alone. Record the active hourly rate if cost is reported; do not invent a RunPod price.

If memory is tight, reduce batch concurrency and context length consistently before changing quantization. Any quantization change must apply uniformly to the methods being compared and be recorded. Avoid weight offloading to CPU in the experiment.

Use bounded outputs, cached feature extraction, batched inference across independent episodes, and resumable run manifests. Do not batch across future checkpoints in a way that leaks later evidence. A run is resumed by missing case identifiers, not restarted from scratch.

Measure batch-throughput and interactive-latency workloads separately. High batch throughput is not evidence of low single-request latency.

## 16. Repository organization and interfaces

Use a small Python package with clear module boundaries. The following are proposed paths to create, not files that already exist:

| Path | Responsibility |
| --- | --- |
| README.md | Setup and reproduction entry point |
| STATUS.md | Current progress and next command |
| DECISIONS.md | Dated deviations and resolved choices |
| pyproject.toml and lockfile | Pinned dependencies |
| configs/ | Models, methods, datasets, faults, and run budgets |
| src/temporal_evidence/data/ | Dataset adapters and immutable manifests |
| src/temporal_evidence/synthetic/ | The single synthetic benchmark generator |
| src/temporal_evidence/features/ | Windowed numerical extraction |
| src/temporal_evidence/replay/ | Arrival scheduling, revisions, and snapshots |
| src/temporal_evidence/storage/ | Graph and relational adapters |
| src/temporal_evidence/generation/ | Prompts, schemas, GPU client, repairs |
| src/temporal_evidence/validation/ | Runtime claim checking |
| src/temporal_evidence/evaluation/ | Independent oracle and metrics |
| src/temporal_evidence/analysis/ | Paired analysis and figures |
| src/temporal_evidence/dashboard/ | Review interface |
| tests/ | Meaningful correctness and leakage tests |
| artifacts/manifests/ | Data, split, query, and environment records |
| artifacts/runs/ | Raw immutable experimental outputs |
| artifacts/figures/ | Reproducible scientific plots |
| paper/ | Manuscript source and references |

Keep raw datasets out of git. Keep credentials out of configuration files. Prefer Parquet for tables and JSONL for event and generation logs. Use typed records and descriptive names. Avoid a large monolithic notebook as the only executable implementation.

Provide a CLI with commands equivalent to the following. These commands are target interfaces to implement; they are not claimed to run before the package is built.

```bash
python -m temporal_evidence.cli check-environment
python -m temporal_evidence.cli acquire-data --datasets wesad ppg_dalia
python -m temporal_evidence.cli generate-synthetic --config configs/synthetic.yaml
python -m temporal_evidence.cli prepare-features --config configs/minimum_study.yaml
python -m temporal_evidence.cli freeze-manifest --config configs/minimum_study.yaml
python -m temporal_evidence.cli validate-core --config configs/minimum_study.yaml
python -m temporal_evidence.cli pilot --config configs/pilot.yaml
python -m temporal_evidence.cli run --config configs/minimum_study.yaml --resume
python -m temporal_evidence.cli evaluate --run-manifest artifacts/manifests/minimum_run.json
python -m temporal_evidence.cli analyze --run-manifest artifacts/manifests/minimum_run.json
python -m temporal_evidence.cli benchmark-streaming --config configs/streaming.yaml
python -m temporal_evidence.cli dashboard
```

The manifest freeze command must separate development and test cases. Pilot and validation commands must not use the held-out outcomes to tune the method.

## 17. Implementation stages and completion gates

### Stage 0 Environment and acquisition

Deliver environment report, dataset access manifest, verified licenses, downloads or exact access blockers, and dataset inventories. Confirm GPU execution and database startup.

Gate: all three sources can produce at least one correctly timed development episode. If data access fails, continue synthetic and infrastructure work while recording the missing source. The full study remains incomplete until both real datasets are evaluated.

### Stage 1 Synthetic correctness

Implement the generator, event replay, immutable versions, exact query oracle, and revision logic. Implement both graph and relational storage interfaces.

Gate: temporal snapshots are reproducible, no future event is exposed, known revisions affect the correct claims, and alternate support survives where appropriate.

### Stage 2 GPU generation and baselines

Implement the five conditions, structured generation, direct checks, repair limits, and full logging. Validate free-text and structured-output consistency handling.

Gate: a fixed development fixture executes end to end on the GPU and produces inspectable outputs for every condition. Graph and full relational implementations agree on logical support for deterministic fixtures.

### Stage 3 Real data adapters

Implement WESAD and PPG-DaLiA adapters, documented synchronization, selected features, and replay variants. Verify source references can be resolved back to recording windows.

Gate: manually inspected development examples show correct subject identity, units, intervals, and revision timing. Reference targets and protocol labels do not leak into runtime evidence.

### Stage 4 Freeze and pilot

Create the subject splits and complete test manifest. Freeze prompts, thresholds, tolerances, versions, and requested cases. Run the development throughput pilot and calculate a time budget.

Gate: the minimum matrix has 3,600 planned initial calls plus explicitly bounded repairs, or a documented corrected count if an eligibility rule changes the manifest before testing. No reduction may eliminate a source or method silently.

### Stage 5 Locked experiments

Run all three sources and five conditions with paired cases. Save incremental outputs and resumable progress. Record missing and failed cases rather than deleting them.

Gate: every planned case is accounted for as completed or failed with a reason, and per-source denominators match the manifest.

### Stage 6 Analysis and interface

Produce reliability and correction metrics, clustered intervals, graph-versus-relational systems results, and a minimal dashboard. Audit sampled explanations.

Gate: figures and tables regenerate from raw run outputs; claims in the written findings match those outputs. Interface examples include a successful correction, a false alarm or limitation, and a case with surviving alternative support.

### Stage 7 Manuscript package

Write the paper using the completed evidence. Include a related-work comparison, method, three-source design, exact baselines, results, computational costs, and limitations. Build the PDF and check formatting against the conference requirements.

Gate: no placeholder results, no unexplained missing methods, no claim of a human study without one, and no claim that physiological monitoring validates aviation readiness.

## 18. Deadline execution strategy

The conference page checked on 2026-09-28 lists a full-paper deadline of 2026-09-30. It specifies anonymized submissions and regular papers of 12-20 pages excluding references and appendices. Verify the exact submission cutoff and timezone in the submission system before scheduling final upload. [R1]

Use the deadline as a prioritization constraint, not a reason to manufacture completeness.

Suggested order for approximately two days:

| Work period | Priority |
| --- | --- |
| First 4 hours | GPU check, downloads, event schema, synthetic generator, database startup |
| Next 6 hours | Core temporal logic, five conditions, real adapters, targeted tests |
| Next 4 hours | Freeze protocol, development pilot, run-duration estimate |
| Next 12 hours | Minimum experiment, early output integrity checks, manuscript methods draft |
| Next 8 hours | Analysis, systems measurements, figures, small dashboard |
| Remaining time | Results writing, references, PDF inspection, submission checks |

This schedule is an aspiration and must be replaced by pilot-based estimates. The useful deadline deliverable is the smallest completed and auditable study across all three sources.

If time becomes tight, remove expanded seeds, the second generator model, review-budget simulations, and elaborate dashboard features first. Keep the strong relational control, leakage checks, coverage metrics, and both real datasets. If the minimum cannot finish, produce a transparent progress package and completed results; do not describe incomplete runs as a completed three-source study.

## 19. Figures and tables for the paper

Generate figures using standard plotting tools from recorded results, with PDF/SVG export and a readable raster preview.

Minimum figures:

1. Architecture showing event ingestion, feature extraction, candidate claims, checking, revision propagation, and review.
2. One evidence subgraph before and after a correction, including an unaffected alternative support path.
3. Error and required-fact-recall comparison across the three sources.
4. Correction completeness and collateral revision comparison.
5. Offered load versus p95 latency and queue growth, including M1 and B3.

Minimum tables:

- Data inventory and evaluation counts.
- Method comparison with exactly which capabilities each condition has.
- Reliability and usefulness by source.
- Correction and systems outcomes with denominators and uncertainty.
- Hardware, model settings, token counts, and total compute.

Each figure and table must have a script and an input manifest. Do not manually transcribe performance numbers into the manuscript if they can be generated from analysis outputs.

## 20. Related work and positioning

Read the closest sources before making a novelty claim. Maintain a comparison table with task, temporal updates, evidence provenance, revision propagation, real physiological streams, human interface, and evaluation design.

Starting sources:

- GraphRAG demonstrates graph-based retrieval and summarization. [R5]
- Zep/Graphiti demonstrates dynamic temporal knowledge graphs for agent memory. [R6]
- Evidence-traceable temporal graphs have already been studied in a 2026 clinical-reasoning preprint. [R11]
- Chain-of-thought explanations can misrepresent factors driving a model's answer. [R12]
- A 2026 ACL Findings paper constructs semantic dependency graphs from model attribution for hallucination detection; this is a different, more internal interpretability approach. [R13]

Potential defensible contribution: a reproducible benchmark and implementation for propagation of evidence corrections into generated explanations of physiological streams, with exact synthetic dependencies, two real sources, paired reliability/usefulness evaluation, and a fair relational implementation control.

Do not write "the first" without a separate comprehensive literature check. Reassess the claim if related work already implements the same operation and evaluation.

## 21. Risks and predetermined responses

| Risk | Response |
| --- | --- |
| Graph and relational methods have equal reliability | Attribute the benefit to explicit dependencies and checking; report storage/runtime differences without inflating novelty |
| Most errors disappear with basic validation | Report that result; examine whether transitive revision still adds measurable value |
| Fault metadata leaks into runtime | Invalidate affected runs, fix the boundary, regenerate the locked outputs |
| Model abstains on most cases | Report coverage loss and revise only on development data before the final freeze |
| Prose makes unsupported statements despite valid JSON | Count the discrepancy and repair the validation/audit process |
| Motion is incorrectly treated as proof of sensor failure | Restore uncertainty semantics and re-evaluate affected claims |
| Real-time target is missed | Report achieved latency and sustained load; use streaming or near-real-time wording justified by measurements |
| Small participant count limits precision | Use subject-level analysis and describe the study as a focused experimental evaluation |
| Signal extraction becomes a separate research project | Retain simpler verifiable features and prioritize explanation reliability |
| Dataset access or license is unresolved | Record the exact blocker; do not relabel synthetic recordings as the missing dataset |

## 22. Final deliverables

- Executable, versioned research repository with setup instructions and a pinned environment.
- One reproducible synthetic benchmark generator.
- WESAD and PPG-DaLiA adapters and source manifests.
- Subject splits, frozen query manifests, fault schedules, and evidence schemas.
- Five experimental conditions and their precise capability definitions.
- Raw GPU generations, validation decisions, repairs, timings, and errors.
- Independent evaluation and statistical analysis scripts.
- Reproducible tables and scientific figures.
- A small evidence-graph review dashboard.
- An implementation report stating completed runs, findings, costs, and limitations.
- A conference manuscript draft and compiled PDF if the experiment reaches the writing stage.
- A resume command and STATUS.md describing any remaining work.

Completion means the evidence can be reproduced from the saved manifests and outputs. It does not require a positive result.

## 23. Source register

These are starting references and implementation sources checked or identified on 2026-09-28. Retrieve full bibliographic metadata before building the paper bibliography. Dataset files and software versions must be verified again at execution time.

- [R1] EAI BDCC 2026 call for papers. https://bdcc-conf.eai-conferences.org/2026/call-for-papers/
- [R2] WESAD UCI record. https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detection ; dataset DOI: https://doi.org/10.24432/C57K5T
- [R3] WESAD author page and original paper. https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html ; Schmidt et al., Introducing WESAD, a Multimodal Dataset for Wearable Stress and Affect Detection, ICMI 2018. https://doi.org/10.1145/3242969.3242985
- [R4] PPG-DaLiA UCI record. https://archive.ics.uci.edu/dataset/495/ppg+dalia ; dataset DOI: https://doi.org/10.24432/C53890
- [R5] Edge et al., From Local to Global: A Graph RAG Approach to Query-Focused Summarization. https://arxiv.org/abs/2404.16130
- [R6] Rasmussen et al., Zep: A Temporal Knowledge Graph Architecture for Agent Memory. https://arxiv.org/abs/2501.13956 ; implementation: https://github.com/getzep/graphiti
- [R7] Qwen3-8B model card. https://huggingface.co/Qwen/Qwen3-8B
- [R8] vLLM structured outputs documentation. https://docs.vllm.ai/en/latest/features/structured_outputs/
- [R9] Neo4j Docker operations documentation. https://neo4j.com/docs/operations-manual/current/docker/
- [R10] RunPod Pod selection documentation. https://docs.runpod.io/pods/choose-a-pod
- [R11] Ahmed et al., The Provenance Gap in Clinical AI: Evidence-Traceable Temporal Knowledge Graphs for Rare Disease Reasoning, 2026 preprint. https://arxiv.org/abs/2604.17114
- [R12] Turpin et al., Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting, NeurIPS 2023. https://arxiv.org/abs/2305.04388
- [R13] Hu et al., Detecting Hallucinations in Retrieval-Augmented Generation via Semantic-level Internal Reasoning Graph, Findings of ACL 2026. https://aclanthology.org/2026.findings-acl.1385/

## 24. Start instruction

Codex: implement this plan in stages, starting with repository inspection, GPU validation, and data acquisition. Establish the synthetic temporal-correction tests before running the full experiment. Complete the minimum study across the synthetic benchmark, WESAD, and PPG-DaLiA before expanding scope. Keep the GPU model, evidence access, and evaluation protocol comparable across methods. Return concrete files, commands, measured outcomes, and exact blockers. Do not stop at restating this plan.
