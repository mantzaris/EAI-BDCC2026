# Final frozen test evaluation and manuscript handoff

The authorized held-out evaluation is complete. **Test data have now been evaluated.** No checkpoint, transform, graph, seed, shrinkage coefficient, calibrator, alarm threshold, target or eligibility rule was fitted or selected using test outcomes. All 17 frozen families and 45 individual predictors were retained, with raw and frozen-calibrated outputs. The original experimental implementation is unchanged after exposure.

The strongest defensible finding is a controlled, task-specific comparison: the tested local-history correction C remains worse than aggregate correction B; graph differences depend on representation, period, topology control and alarm criterion; the aggregate refit R_union is a strong competitor. E has favorable secondary comparisons against both trained rewired graphs on test, but no favorable primary graph contrast excludes zero with the main three-day multiplicity adjustment, and E increases false alarms. Neither universal graph usefulness nor zero information value of local measurements follows.

**Recommendation:** review this comparative manuscript and resolve measurement-use/publication provenance with the human authors before submission. Do not retune against this now-exposed test period. No new experiment, full campaign or conference submission is scheduled.

## Freeze, access history and execution

Started on clean main at `c1f0a2173c2e24ca87a2b7f35ca8887258a876c2`, verified expected origin, fetched and found no later work. No applicable AGENTS.md or unrelated changes were found. Historical source guards and execution records show training/validation access only. All validation days were exposed. The earlier residual pilot's onset endpoint was secondary; its favorable exploratory result motivated the subsequent primary onset comparison. That history is preserved, not relabeled. This audit cannot establish what happened in unrecorded activity outside the repository.

| Revision | Role |
|---|---|
| `48e31b66745d577105c5aa8f2b8b2e6690fafd0b` | Historical main-study GPU fitting and null construction |
| `70e03d050022e294340712071c0d8a261fb04438` | Historical evaluation/replay |
| `541723f5c858cb852742b7080e59e0a391b37779` | Historical supplementary analysis/costs |
| `c1d33c8b6f435fa04b29bda8739de65027b4e6e6` | New evaluator implementation and development-only CUDA preflight |
| `ceb99eaa23d70a37b82f8d4148505a4d13f2b908` | Committed final sealed protocol; test evaluation and replay source |

The [protocol](FINAL_TEST_PROTOCOL.md) and [sealed manifest](../configs/final_test_manifest.json) were committed and pushed before access. The manifest hashes every required checkpoint, source dependency, original config, model metadata and split membership; the development preflight adds exact graph-operator hashes. No required checkpoint was missing. D's self control is the existing matched C, not an omitted arm. Original sklearn trees remain unrecoverable and are not reconstructed from saved 128-panel predictions.

The first authorized test measurement read was **2026-09-23 23:26:43.338128 UTC**, recorded before the value slice was loaded. The sealed manifest SHA256 is `45a3051c79772c71b525535f40cb21ed67f472d05f6451291da7326466f6d0d6`. See [access receipt](../results/final_test/evaluate/test_access_started.json). Only rows 41766 through 52115 were loaded; outside-test measurement buffers remained NaN and all history/future offsets were checked inside the designated split. Older runners still reject test access; the new final entry point rejects fitting, unsealed/uncommitted manifests, incompatible hashes, graph mismatch and output overwrite.

Before exposure, all 45 raw and 45 calibrated validation prediction vectors replayed exactly, with exact origins, labels, masks and coverage. Additional checks passed for bounded probabilities, exact zero-alpha baseline recovery, frozen cutoffs, corrupted-hash rejection and test-row isolation. Existing masking/permutation/projection/null tests were preserved; unrelated historical suites were not rerun. The focused CUDA checks cover changed behavior. Syntax checks were CPU-only parsing.

The test run completed once. The authorized identical replay produced **maximum prediction difference 0**, exact origins/labels/masks, and maximum numeric metric difference **2.220446049250313e-16** for both raw and calibrated summaries, including interval endpoints. This is below the frozen 1e-12 metric tolerance and 1e-10 prediction tolerance. Predictions replay exactly; all metric leaves are not bitwise identical. No post-exposure executable correction, model change, failure, retry or incomplete GPU job occurred. The first HTTPS push lacked a cached credential; the already-authenticated GitHub CLI helper completed the push. No credentials were printed or committed.

## Population, target and paired comparability

Private PEMS-BAY source: 52,116 timestamps by 325 ordered sensors, recorded mph, naive timestamps. Original 108 complete training days run Jan1-Apr19 excluding incomplete Mar12; validation Apr20-May25 has 36 days; test May26-Jun30 has 36 days. Test permitted rows begin May26 01:30 and end Jun30 23:55. Windows are 12 history frames and six future frames at five-minute resolution, entirely contained with the original 90-minute boundary embargo.

The event is at least 48 sensors at/below half their original training 85th-percentile free speed for three consecutive future frames within the horizon. Onset excludes currently or possibly active sustained events in the last three frames. Nonfinite/nonpositive entries are unknown. Future lower/upper event bounds must agree and coverage must reach .95; no imputed future label is called observed.

| Support | Exposed validation | Frozen test |
|---|---:|---:|
| Timestamp-eligible origins | 10,315 | 10,333 |
| Observed eligible all-time origins | 10,309 | 10,327 |
| Coverage exclusions / ambiguous labels | 6 / 0 | 6 / 0 |
| All-time positives | 1,478 | 1,147 |
| Onset origins / positives | 8,981 / 289 | 9,315 / 260 |
| Onset positive groups / event days | 47 / 26 | 45 / 25 |
| Eligible calendar days | 36 | 36 |
| Onset prevalence | 3.217904% | 2.791197% |

All 45 predictors use identical eligible origins, labels, weights, horizon and onset convention. Predictions are saved for all timestamp-eligible origins with masks, not filtered by model outcome. There are 9,055 test onset negatives. Six missing-coverage exclusions remain in the saved origin table with explicit flags. Groups start after gaps of at least 30 minutes among positive origins; they are forecast groups, not annotated incidents. All-time test groups number 42, distinct from onset groups.

Aggregate X contains 1,158 entries including histories of regional means/counts and variance/min/max/severe fractions, plus calendar terms. All summaries read every sensor. C/D/E/F add full local histories, deviations, changes and masks; M adds no measurements; S compresses graph-dependent detail after all-sensor ingestion. C versus B changes the learner and representation and cannot identify learner-independent information value.

A_G fitted on 5,173 early examples; R_union refitted the same selected tree specification and transform on 7,070 examples, the exact union of anchor and correction fitting origins at stride three. The correction period has no exclusions, so the before/after eligibility stride conventions produce the same correction-origin membership. This addresses both older-label and sampling-density differences from A_T. All new study choices predate test, and all correction arms share the same anchor, periods, two-setting allowance and three seeds. Calibration has a separate out-of-sample block with 30 onset positives in five groups on four days; uncertainty about its generalization is substantial.

## Complete family results

Brier means are means of seed-specific losses, not an ensemble. The three single controls have one fitted model; all corrections retain seeds 20261001/02/03. Rewired suffixes identify graph seeds, not a selected model seed. F remains secondary. [Raw metrics](../results/final_test/evaluate/raw_metrics.json), [calibrated metrics](../results/final_test/evaluate/calibrated_metrics.json), [compact CSV](../results/final_test/metrics.csv), and [paired tables](../results/final_test/paired_metrics.json) preserve full precision and all endpoints.

| Family | Raw onset | Calibrated onset | Raw all-time | Calibrated all-time |
|---|---:|---:|---:|---:|
| A_G | 0.01601791 | 0.01396522 | 0.02059717 | 0.01874450 |
| R_union | 0.01424653 | 0.01286379 | 0.01852450 | 0.01711608 |
| A_mono | 0.01467430 | 0.01380663 | 0.01920143 | 0.01870011 |
| B | 0.01521217 | 0.01398557 | 0.01973628 | 0.01922781 |
| K | 0.01535468 | 0.01412396 | 0.01993481 | 0.01959974 |
| C | 0.01537152 | 0.01406380 | 0.01984603 | 0.01907078 |
| D | 0.01515125 | 0.01398913 | 0.01979407 | 0.01948944 |
| M | 0.01511645 | 0.01381308 | 0.01978037 | 0.01964400 |
| S | 0.01523637 | 0.01386031 | 0.01983368 | 0.01949294 |
| E | 0.01504381 | 0.01399043 | 0.01972944 | 0.01959173 |
| F | 0.01537736 | 0.01418040 | 0.01986209 | 0.01915787 |
| E_internal | 0.01526266 | 0.01392469 | 0.01990271 | 0.01941816 |
| D_rewire_20261004 | 0.01510286 | 0.01393059 | 0.01978108 | 0.01952195 |
| D_rewire_20261005 | 0.01517650 | 0.01390328 | 0.01979625 | 0.01939791 |
| E_self | 0.01515765 | 0.01393890 | 0.01981216 | 0.01956556 |
| E_rewire_20261004 | 0.01523239 | 0.01412470 | 0.01979810 | 0.01949095 |
| E_rewire_20261005 | 0.01529299 | 0.01398541 | 0.01995155 | 0.01949264 |

## Registered paired conclusions

Negative differences favor the first arm. The four raw onset contrasts use 2,000 paired calendar resamples, seed20261007, three-day blocks primary, one-day sensitivity, and Bonferroni family-four percentile intervals. Calendar gaps are not joined. Model pairing and seed-specific losses stay together. Intervals condition on these fitted models and do not represent all training or selection uncertainty.

| Raw onset contrast | Difference | Relative reduction | Three-day95% | Family-four adjusted |
|---|---:|---:|---|---|
| C-B | +0.000159350 | -1.0475% | [+0.000064606, +0.000210683] | [+0.000052175, +0.000231482] |
| D-C | -0.000220269 | +1.4330% | [-0.000364011, -0.000006268] | [-0.000436443, +0.000026764] |
| E-D | -0.000107439 | +0.7091% | [-0.000204401, -0.000012342] | [-0.000231802, +0.000007286] |
| E-B | -0.000168358 | +1.1067% | [-0.000267411, -0.000011634] | [-0.000295981, +0.000024522] |

C-B is adverse in both periods and all three test seeds. D-C reverses to a favorable test point; E-D retains its favorable point but its adjusted exclusion of zero does not persist; E-B reverses to favorable in point estimate. The one-day adjusted sensitivity favors D-C and E-B, while the main three-day assessment remains inconclusive. This block-length sensitivity is reported, not selected away. E-D and E-B improve in two test seeds and worsen in the third. No interval crossing zero is treated as equivalence.

E's test onset differences exceed the earlier practical Brier scales (.0001/1% for local, .00005/.5% for graph), but do not resolve the primary statistical uncertainty or alarm tradeoff. R_union remains better than every main family in raw and calibrated point Brier for both endpoints. Secondary B-R_union is +.000965639, three-day95% [-.000008094,+.002534749]; it does not prove a difference or equivalence. In validation B-R_union was +.000002482, also uncertain. The final table never compares full-test scores directly with the historical 128-origin .02646 baseline.

F's previously lowest validation correction onset point does not persist: test F-B is +.000165198, pointwise95% [+.000017685,+.000264557]. No new F tuning, selection or nulls follow this observation. Full one-day and three-day all-time/calibrated contrasts remain in the artifacts.

## Topology evidence and limitations

D versus rewiring04 is +.000048385 [+.000010822,+.000085444]; D versus rewiring05 is -.000025255 [-.000128782,+.000053399]. The distance graph does not beat both nulls. E versus E_self is -.000113838 [-.000431331,+.000137538], uncertain. E versus E_internal is -.000218848 [-.000318563,-.000060988]. E versus rewiring04 is -.000188583 [-.000270451,-.000069169], and versus rewiring05 -.000249180 [-.000412320,-.000047005]. These favorable real-versus-rewired E directions hold in all three test seeds but were not consistent across validation. They are descriptive secondary pointwise results, outside the four primary contrasts.

Nulls preserve per-node indegree/outdegree, edge count, each source row's weight multiset and diagonal fallbacks. They change geometry and regional mixing: cross-region edges increase from1,130 to2,228. They are two fixed nonuniform null samples, not a random sample of every admissible graph. E's result can reflect regional mixing as well as neighbor identity. It supports neither causal propagation nor a claim that models ignore topology. No new intervention was added. F uses unsigned residual association weights; its unfavorable test result does not invalidate all learned-adjacency methods.

## Alarms, calibration and loss contributions

Strict frozen alarms use p>cutoff at the training 5% onset FPR target, without jitter or test threshold choice. The calibration transform leaves the observed alarm decisions unchanged for every retained model in the saved raw/calibrated metric records. Achieved test rates, not a guaranteed nominal target, are reported below. Intervals are paired-family day-block summaries, not binomial independent-origin intervals.

| Family | Recall | Three-day95% | FPR | Three-day95% | Mean false-alarm groups |
|---|---:|---|---:|---|---:|
| A_G | 93.4615% | [89.24%, 97.18%] | 4.8702% | [3.06%, 6.47%] | 76.00 |
| R_union | 96.1538% | [92.11%, 99.54%] | 5.2899% | [3.34%, 7.21%] | 80.00 |
| B | 92.8205% | [84.81%, 99.20%] | 5.9746% | [4.16%, 7.57%] | 73.67 |
| C | 93.2051% | [85.71%, 99.24%] | 6.3206% | [4.52%, 7.94%] | 83.00 |
| D | 92.8205% | [84.81%, 99.20%] | 6.6888% | [4.86%, 8.36%] | 81.33 |
| M | 92.4359% | [84.81%, 98.57%] | 4.9402% | [3.26%, 6.39%] | 69.00 |
| S | 92.8205% | [85.34%, 98.75%] | 5.0653% | [3.33%, 6.50%] | 71.33 |
| E | 92.8205% | [84.81%, 99.20%] | 7.1158% | [5.29%, 8.67%] | 77.67 |
| F | 92.6923% | [84.48%, 99.14%] | 6.3906% | [4.60%, 8.04%] | 80.67 |

E raises mean onset FPR from B's5.974600% to7.115774%, beyond the one-percentage-point tolerance, at the same92.820513% recall. R_union gives96.153846% recall and5.289895% FPR and detects all45positive groups. B/C/D/E detect43.33groups on average; F42.67. False-alarm groups need not rank models like FP origins, because longer clusters can contain many false alarms. Every exact TP/FP, group count and frozen cutoff is retained per seed.

Frozen calibration improves test onset Brier for all main arms, unlike the validation result. E's calibrated onset .013990432 is slightly worse in point estimate than B .013985574. Calibration remains a separately labeled learned map with sparse independent support; it is not proof of faithful trajectories or transportable alarm rates. Raw onset zero fractions B/C/D/E/F are86.612990%/86.044015%/85.779209%/84.168903%/86.362498%. M/S seed01 have exact zero cutoffs. Their tied mass is reported, not perturbed.

Test onset Brier event/non-event contributions are B .005452906/.009759259 and E .005595648/.009448160. E's total improvement comes from less non-event loss despite more event loss. For every arm/endpoint the CUDA evaluation verifies the established clipped correction identity relative to A_G. Its alignment and magnitude terms, exact identity error, reliability bins, clipping and tie fractions are stored under diagnostics. These are descriptive calculations, not new mathematical results.

## Resources, evidence preservation and reproduction

Single NVIDIA RTX6000 Ada Generation, reported total50,876,841,984bytes; driver570.124.06; Python3.12.3; PyTorch2.8.0+cu128; CUDA12.8; numpy2.1.2, pandas2.3.2, h5py3.14.0. The maximum active allocation was1,655,385,088bytes, reserved2,090,860,544bytes, below32billion. The evaluation host peak was1,419,080KiB RSS. Host parsing/serialization/rendering is not a CPU scientific fallback.

| Job | Charged GPU-job wall seconds | Test values accessed |
|---|---:|---|
| Development preflight | 10.131780632 | No |
| Frozen evaluation | 13.085067276 | Yes, designated interval |
| Identical replay | 12.286544804 | Yes, same frozen computation |
| New total | **35.503392711** | |
| Prior cumulative | 997.822543358 | |
| Project cumulative | **1,033.325936070** | |

Stage cap1,800seconds; provisional project cap86,400seconds. No failed/open GPU jobs. Total new CUDA event span27.850404297seconds includes host gaps and is not an active-kernel total. The ledger includes process startup, verification, serialization and shutdown. [Persistent ledger](../results/final_test/compute_ledger.jsonl) and [reconciled summary](../manifests/final_test/compute_summary.json) preserve cumulative usage. No resource rental, new data download, training, calibration fit, cost campaign or information-budget extension occurred.

Existing 128-origin full inference cost means range about.202-.209seconds, with overlapping repeat ranges; no speedup claim follows. See [historical cost summary](../results/final_test/evaluate/historical_cost_summary.json) and the manuscript cost table. That workload includes warm-cache history parsing, transfers, transforms, summaries, predictor and output transfer, with restore/graph setup separate, and uses the first seed. It does not include future-label preparation. Payload sizes are serialization specifications, not measured communication or storage savings.

Use the commands in FINAL_TEST_PROTOCOL.md at the designated source revision and original private file hashes. Completed evaluation directories deliberately cannot be overwritten; forensic reproduction uses a new checkout containing the same frozen manifest and the archived output receipts. No new run is requested by this report. Main checkpoints survive the Pod session in the versioned artifacts/onset_graph/study01/main directory. Raw measurements, secrets, environments and large caches are excluded. No experiment remains running.

## Manuscript and remaining prerequisites

[Compiled draft](../manuscript/graph_representations_draft.pdf), [source](../manuscript/main.tex), [rendering script](../scripts/render_final_manuscript.py), [quantitative traceability](../manuscript/generated/claim_traceability.json), and [author/source audit](FINAL_PUBLICATION_AUDIT.md) accompany this handoff. The manuscript includes four figures, three main tables and a full per-seed appendix. It uses the official linked unmodified template, anonymous author line and AI-assistance disclosure. References and test/validation numbers are linked to primary literature and saved artifacts. Numerical analysis ended before writing; CPU work only rendered existing statistics and compiled documents.

Remaining prerequisites are human authorship/affiliation and scientific approval, exact measurement analysis/publication/redistribution terms and upstream processing version, and final publisher/portal requirements including accessible typesetting and proceedings-series/template ambiguity. Missing documentation is not reported as a discovered prohibition. Public DCRNN access and its MIT software license do not establish measurement rights. No third party was contacted, account registered, restriction bypassed, raw data redistributed, or paper submitted.

Reproduction and passing checks establish computational fidelity. They do not establish predictive adequacy, equivalence, a novel theorem or a deployment benefit. The comparative draft preserves these boundaries and the historical failed simulator, direct-feature, enclosure and prior residual studies.
