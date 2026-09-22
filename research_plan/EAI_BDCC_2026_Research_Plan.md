# When Averages Hide Congestion

## A bounded research plan for aggregation-aware traffic risk forecasting

Prepared on September 22, 2026. Hardware assumption: one NVIDIA RTX 6000 Ada Generation with 48 GB VRAM. This is a research design and evidence review. No training, dataset download, or GPU experiment has been executed for this plan.

### 1. Recommendation and scope

Build a small probabilistic traffic forecasting twin that receives compressed sensor histories, reconstructs a distribution of unresolved local conditions, and estimates the probability of a sustained congestion episode. Its central question is when a fixed resource budget should buy additional local measurements rather than additional simulations.

The proposed mathematical contribution is a **graph-dependent enclosure for coarse rollouts**, with an explicit term for differences in how nodes within an aggregate connect to other aggregates. This enclosure determines whether a scenario's event label is already fixed. Only ambiguous scenarios require full graph evaluation. Selective refinement itself is established prior work. The potential contribution is the particular graph construction, its dependence on aggregation, and its measurable implications for the information-versus-computation tradeoff.

Use **PEMS-BAY speed observations for the primary outcome study**. Use a bounded portion of **LargeST for a real-data ingestion and graph-scale engineering experiment**, with its flow measurements identified separately from speed. Use a small traffic mechanism model only for controlled counterfactuals. Do not make power-grid experiments part of the minimum study.

This is deliberately a predictive, sensor-level twin prototype. Its finest state describes sensor locations, not individual vehicles. It is synchronized through historical replay. It is not a deployed operational twin, a validated vehicle simulator, or evidence that observed congestion was caused by an endogenous cascade.

**Proposed contribution statements, conditional on successful results**

1. We derive a graph aggregation error enclosure that separates within-block state variation, differences in inter-block connections, and local forcing variation. It provides a scenario-level certificate for sustained threshold events without assuming that event severity has a continuous density.
2. We construct an observation-conditioned forecasting pipeline that chooses retained detail and rollout resolution from a finite set of measured resource configurations. Exact event evaluation within the specified stochastic model separates numerical sampling error from loss of observational information.
3. We evaluate aggregation ambiguity and the resulting accuracy-resource tradeoff on chronologically held-out traffic observations, accompanied by a reproducible streaming and graph-scale experiment. Real outcomes, controlled mechanisms, and computational scaling have distinct evidential roles.

These are proposed claims, not results. Novelty is provisional. The first claim needs a focused comparison with selective refinement and graph abstraction literature before being advertised as a new theorem.

**Modest fallback.** Retain the real-data task, the proved enclosure, the aggregation-ambiguity experiment, and ordinary vectorized Monte Carlo. If refinement does not save time, publish its measured failure region and the conditions under which retaining local detail is more useful than increasing sample count. This fallback is defensible only if the bound or the resulting empirical finding is substantive. A generic benchmark with no theoretical distinction is not an adequate substitute.

### 2. Conference facts and unresolved details

The official [2026 CFP](https://bdcc-conf.eai-conferences.org/2026/call-for-papers/) currently lists September 30, 2026 for full papers, October 20 for notification, November 20 for camera-ready, and December 3-4 in Coimbatore, India. It specifies 12-20 pages of main content, excluding references, appendices and acknowledgments, anonymized English submissions, and the Springer LNICST Authors' Kit. Submission uses Confy+. The camera-ready requires PDF and source ZIP. It labels the event hybrid. [C1]

**Unresolved:** remote author eligibility, live versus recorded presentation, presentation duration, virtual registration charges, the deadline time zone, and the threshold/rate for extra-page fees. The CFP mentions extra-page charges without resolving the charging basis. No specific remote presentation procedure was verified. The website also contains stale 2024 dates and unrelated conference material. Use its explicit 2026 CFP dates for planning, while treating the unresolved details as matters for the organizers. Do not infer remote publication eligibility solely from the word hybrid.

The current CFP points to an LNICST template even though its publication section names the EAI SICC series. Follow the supplied author-kit link, retain the downloaded class and instructions, and check the resulting template before drafting. The ZIP itself could not be inspected during this review. Do not substitute an ICAART, ICISSP, IEEE, generic LNCS, or previous-year template. [C1]

Plan to freeze a 14-page main text on September 29. References and a short proof supplement can be additional pages under the stated content rule, but the financial page policy remains unresolved. Do not submit or contact organizers automatically under this planning request.

### 3. Candidate contributions and domain choice

Scores below are judgments from 1 to 5, where 5 is best. Completion safety is higher when risk is lower. They are not measured quantities.

| Candidate | Novelty potential | Theory | Real-data feasibility | GPU benefit | Big-data relevance | Completion safety |
|---|---:|---:|---:|---:|---:|---:|
| A. Graph aggregation enclosures plus conditional scenario forecasting | 3 | 4 | 4 | 3 | 4 | 4 |
| B. Learned risk closure with an adaptive GNN and memory | 2 | 3 | 4 | 4 | 4 | 2 |
| C. Adaptive importance sampling for simulated power-grid cascades | 2 | 4 | 2 | 4 | 3 | 2 |

Select A. B has strong existing competitors and a difficult architecture-versus-information confound. C makes simulation scientifically attractive but fails to supply observed cascade outcomes on the present schedule. GPU benefit for A is uncertain because small graphs can be faster on CPUs.

| Domain | What is actually observable | Main limitation | Decision |
|---|---|---|---|
| Road traffic | Local speed or flow histories and subsequent measured network conditions | Incident causes and causal propagation are not established by sensor correlations | Primary domain |
| Power networks | Rich pre-outage states and explicit simulated cascade severity in PowerGraph | Simulation outcomes are not observed blackouts | Exclude from minimum study |
| Service/queue networks | Potentially useful arrivals, queues and response times | No suitably licensed, connected incident-level trace was verified in this review | Do not add a data acquisition project |

### 4. Closest literature and the exact novelty boundary

The table contains twelve close or method-defining studies. Sources are primary papers, publisher pages, author repositories, or author-hosted manuscripts. Publication status is stated only where verified. Do not cite a later indexing timestamp as a paper's publication date.

| Study | What it already establishes or implements | Additional claim this study would need |
|---|---|---|
| Yu, Harlim, Huang and Li, *Learning coarse-grained dynamics on graph*, Physica D 481, 134801, 2025 [L1] | Uses Mori-Zwanzig reasoning to design graph memory closures, including a connection between interaction hops and message-passing depth | A computable bound for an event functional under observation compression, rather than a new claim that graph memory matters |
| Tezzele et al., *Adaptive Planning for Risk-Aware Predictive Digital Twins*, Springer chapter, first online November 2025; 2024 preprint [L2] | Risk-aware planning using probabilistic transition uncertainty and a digital-twin decision framework | Explicit treatment of unresolved local observations and their cost relative to scenario evaluation |
| Sevak et al., *Physics-Informed Graph Neural Jump ODEs for Cascading Failure Prediction in Power Grids*, March 2026 preprint [L3] | Graph/continuous/jump dynamics and physical regularization for simulated grid failures and severity | Event-preserving aggregation bounds and real observed forecast outcomes in traffic; no claim of inventing graph cascade prediction |
| *A Two-Stage Coarse-to-Fine Framework for Sparse Crowd Density Prediction in Digital Twin-Based Safety Monitoring*, Sensors 26(13), 4094, June 2026 [L4] | A predictive twin component exploiting sparse congestion through coarse-to-fine processing | A mathematically justified graph event enclosure, coupled exact-model estimates, and a separately varied information budget. Abstract-level verification only; full-text comparison remains a gate |
| Elfverson, Hellman and Malqvist, *A Multilevel Monte Carlo Method for Computing Failure Probabilities*, SIAM/ASA JUQ, 2016; 2014 preprint [L5] | Selective refinement and cost/error analysis for threshold probabilities | Derive the graph-specific state and topology defect rather than assume a generic accuracy hierarchy |
| Elfverson et al., *Adaptive Multilevel Subset Simulation with Selective Refinement*, SIAM/ASA JUQ, 2024 [L6] | Uses error estimators and different resolutions while preserving required event nesting | A finite graph count-event construction that tolerates atoms in severity, plus a real-data information budget. Selective refinement and rare-event acceleration are already theirs and others' |
| Peherstorfer, Willcox and Gunzburger, *Optimal Model Management for Multifidelity Monte Carlo Estimation*, SISC, 2016 [L7] | Allocates computation among correlated models using costs and variance information | Incorporate a separately chosen observation representation and the graph certificate. Cost-optimal control variates are background |
| Kramer et al., *Multifidelity probability estimation via fusion of estimators*, 2019 preprint [L8] | Low-fidelity proposals, importance sampling, and unbiased fusion with variance analysis | No competing importance-sampling theorem is proposed here. The distinct object is loss of local information and graph enclosure |
| Geroliminis and Sun, *Properties of a well-defined macroscopic fundamental diagram for urban traffic*, Transportation Research B, 2011 [L9] | Empirical and modeling analysis linking spatial heterogeneity to aggregate traffic behavior | Quantify event forecast loss under explicit sensor retention and finite computational budgets. The motivating observation is established |
| Li et al., *Diffusion Convolutional Recurrent Neural Network*, ICLR 2018 [L10] | Graph-temporal forecasting on measured traffic, with public speed datasets and road-distance graphs | Risk and information-resource evaluation, not a claim of a new graph forecasting architecture |
| Liu et al., *LargeST*, NeurIPS 2023 Datasets and Benchmarks [L11] | A substantially larger traffic benchmark with metadata and accuracy/efficiency comparisons | A targeted streaming compression and conditional scenario workload with explicitly separated real-data and synthetic scale evidence |
| Duffield, Lund and Thorup, *Priority sampling for estimation of arbitrary subset sums*, JACM 2007; author preprint [L12] | Bounded samples and unbiased subset-sum estimates from weighted streams | Dependence-sensitive event preservation. An unbiased estimate of an aggregate sum is not generally an unbiased estimate of a nonlinear cascade probability |

**Assessment.** The broad idea of averages hiding congestion is established. So are memory closures, uncertainty-aware twins, Monte Carlo, GPU batching, control variates, and refinement near event boundaries. The plausible new object is the explicit graph defect matrix in Section 7 and its consequences for a sustained count event under a separately defined information representation.

The search does not prove this construction is absent from positive-system abstraction, equitable partition, approximate lumpability, or reachability literature. Reserve two hours on September 23 for those exact comparisons and the full Sensors paper. If an equivalent result exists, attribute it, narrow the claimed contribution to a demonstrably new decision rule or observation theorem, or abandon the theoretical-novelty claim. Do not present the conditional-variance identity below as the new theorem.

### 5. Data selection and feasibility audit

**Primary data: PEMS-BAY.** The originating DCRNN repository supplies speed data links, sensor coordinates, and graph construction information. A separately deposited CSV/adjacency archive on Zenodo gives a convenient reproducible mirror, not an originating author release. That mirror lists PEMS-BAY.csv at 85.7 MB and its adjacency file at 1.7 MB. [D1, D2]

Published benchmark metadata reports 325 sensors, 52,116 five-minute frames, and 2,369 graph edges. That is 16,937,700 sensor-time values, approximately 67.75 MB as a dense float32 speed matrix. The LargeST comparison reports January-June 2017; other descriptions disagree about the end month. Read the actual timestamps and report them, including timezone and gaps, rather than copying a date range from a secondary description. [L11]

Observed severe-event labels are **derived from future recorded speeds**, not provided incident or cascade annotations. Local speed histories are available. Vehicle density, flows, routing decisions and incident causes must not be invented. Road-distance adjacency supports a predictive neighborhood; it is not a verified causal network. Count exact edges again after removing self loops or changing direction conventions.

**License/access limitation.** The source repository and its public download links were verified. The repository's software license is not automatically a license for the underlying measurements. A dataset-specific license could not be conclusively extracted from the retrieved PEMS-BAY sources. The mirror's retrieved page has a license heading without visible license text. Resolve source terms on day one, record them, and publish retrieval instructions rather than redistribute the data until this is settled. Public download is not itself an open-license finding.

**LargeST engineering companion.** The author release provides five annual raw flow HDF5 files for 2017-2021, metadata and a road-distance adjacency. Its paper explicitly licenses data CC BY-NC 4.0 and code MIT. The author-linked Kaggle listing shows the 2017 file around 7.23 GB. Budget approximately 7-10 GB for one raw year, with exact bytes measured after download; do not fetch all five years. Kaggle API use normally needs account credentials. [D3, L11]

The published CA graph has 8,600 nodes and 201,363 edges; SD has 716 nodes. Use actual subgraphs with 716, 2,352, 3,834 and 8,600 nodes for engineering scaling if accessible. The complete five-year release contains about 4.52 billion sensor-time positions. This study must report only the fraction actually processed. The author preprocessing aggregates five-minute flow data to 15 minutes for some benchmark experiments. Retain five-minute data for ingestion measurements and state any resampling explicitly. [L11, D3]

LargeST is a flow dataset in this release. It cannot replace speed-based congestion labels without changing the target. If PEMS-BAY terms or access fail, a single prespecified switch to LargeST SD is allowed: forecast sustained high-flow episodes above a training-derived threshold, call the target throughput extremes, and revise all congestion claims. This preserves real observational evaluation, but does not establish traffic congestion or cascades. No additional domain is added.

**Rejected cascade source: PowerGraph.** The author repository links a graph-level archive of approximately 2.7 GB uncompressed and identifies CC BY 4.0. It supplies bus/edge attributes, triggering outages, simulated demand not served, and final failure explanation masks for IEEE and UK systems. The labels are produced by Cascades, a physics-based simulator. Final masks are labels, never forecast inputs. There is no chronological observed-blackout validation in those graph-level samples. [D4]

| Candidate | Measurement and connectivity | Outcome evidence | Access, size and terms | Use |
|---|---|---|---|---|
| PEMS-BAY | Five-minute local speeds, coordinates, road-distance adjacency | Future observed speeds; derive sustained congestion labels | Public source links; roughly 87 MB for the mirror's speed-plus-graph files; dataset terms need confirmation | Primary outcome study |
| LargeST | Multi-year local flows with metadata and adjacency | Observed flow extremes; no verified congestion/incident labels | Author-linked Kaggle; one annual raw file about 7.23 GB; CC BY-NC 4.0 data | Bounded engineering scale; declared fallback target if needed |
| PowerGraph | Simulated grid operating states and network attributes | Explicit simulation-derived cascade severity | Public Figshare source; graph subset about 2.7 GB uncompressed; CC BY 4.0 | Excluded from minimum study |

**Day-one manifest.** Record source URL, retrieval date, license text/URL, file hash and bytes, dimensions, actual timestamps, sensor ordering, graph construction, duplicate rows, invalid values, masks and coverage per day. Never infer the number of independent events from the number of matrix entries.

### 6. Prediction task, states, observations and reconstruction

#### 6.1 Observable target and notation

Use a 60-minute observed history, sampled every five minutes, to forecast a sustained congestion episode within the next 30 minutes. There are L=12 input frames and H=6 future frames. Start with the whole 325-sensor graph. A secondary analysis can use a small, training-fixed set of connected regions if whole-network events are too scarce under the prespecified event rule.

| Symbol | Meaning | Dimension or unit |
|---|---|---|
| n, m | Number of sensors and directed graph edges | Counts |
| t, h, L, H | Observation index, forecast offset, history and horizon | Five-minute steps |
| v_i,t, v_i,free | Observed speed and training-only reference free speed | mph, with conversion documented |
| s_i,t | Normalized congestion intensity | Unitless, in (0,1) after clipping |
| x_i,t, y_i,t | Fine predictive state and recorded transformed observation | Unitless log odds |
| W | Fixed nonnegative neighborhood weights, rows sum to one | n by n, dimensionless |
| R_t,S | Information transmitted/retained for a sensor set S | Numeric summaries, selected histories and masks |
| A_S | Linear observation-compression operator on transformed history | d_S by nL |
| Sigma, Omega | Prior history covariance and measurement/quantization covariance | Squared log-odds units |
| B_a, k, P | Computational graph blocks, their number, and block-to-node lifting | Partition and n by k matrix |
| z_h, r_h | Coarse state and certified error radius | k-vectors in log-odds units |
| Y_t, p_S, q_S | Observed event, population conditional probability, fitted-model probability | Binary or unitless probability |
| N, alpha | Scenario count and fraction requiring fine evaluation | Count and proportion |

Define v_i,free as the 85th percentile of valid training speed at sensor i. Set s_i,t=clip(1-v_i,t/v_i,free, epsilon, 1-epsilon), epsilon=0.001, and y_i,t=log(s_i,t/(1-s_i,t)). Fix these transforms before validation. The primary low-speed threshold is s>=0.5, equivalently y>=0. Predictions can be converted back with v_i,free[1-sigmoid(x_i)]. This transformation caps modeled speeds at the reference free speed, so report ordinary speed MAE against both raw and identically capped observations. Do not interpret that cap as a physical speed limit.

The physical observation story is y_i,t=x_i,t+epsilon_i,t when a mask M_i,t=1. Missingness has distribution P(M|observed history, operating regime), which is not assumed independent of congestion. Measurement variance is not identifiable from this dataset alone. The **primary model sets epsilon=0 on valid measurements and targets the recorded process**, with explicit handling of missing observations. Sensitivity runs add known artificial noise or missingness; they are not a calibration of real sensor error.

The finest state is relative to the proposed spatial aggregation. It is not a claim to recover microscopic vehicle positions from loop detectors.

#### 6.2 Retained information and aggregation

Partition sensors into approximately 16 fixed geographic/graph blocks using metadata and training-only information. For each five-minute frame retain each block's mean transformed observation, count of valid observations, and selected sensor values. Include time-of-day and day-of-week. Keep the last L frames, not just one current mean. Means over missing data use only valid sensors and the mask changes the row of A_S.

Thus R_t,S=(A_S vec(y_t-L+1:t), masks, calendar information). The linear operator uses block means in transformed coordinates. It does not imply arithmetic-mean speed is preserved. Baselines with extra raw-speed statistics receive extra information and must be labeled accordingly. A 30-minute temporal averaging ablation replaces six successive readings by their average, so temporal smoothing is measured separately from spatial compression.

Choose nested retained sensor fractions 0%, 5%, 15%, 30%, and 100%, with ceiling rounding. The default local set is selected once from training data. Rank sensors by uncertainty times finite-horizon influence under the fitted dynamics, and enforce one-per-block coverage where possible. A simple score uses column sums of powers of a nonnegative Lipschitz matrix, weighted by training frequency near the event threshold. This is a heuristic, not a proven optimal feature selector. Compare it with random retention and selection by local variance at 15%.

The selector must not inspect current discarded local values. Fixed selection makes that restriction easy to audit. All sensors can still be read at the edge to compute block summaries; their acquisition and aggregation cost remains in the accounting. Do not claim reduced sensor ingestion from this design.

#### 6.3 Conditional reconstruction

Fit a Gaussian working distribution for the transformed history X=vec(x_t-L+1:t), conditional on calendar features, with mean mu and covariance Sigma=UU^T+diag(d), d_i>0. Start with factor rank 16. Fit on training days using masked estimation or a documented training-only imputation procedure. Gaussianity is a working approximation whose conditional coverage must be checked.

With R=A_S X+e and e~Normal(0,Omega), the conditional Gaussian is

    mu_R = mu + Sigma A_S^T (A_S Sigma A_S^T + Omega)^(-1)(R-A_S mu)
    Sigma_R = Sigma - Sigma A_S^T (A_S Sigma A_S^T + Omega)^(-1) A_S Sigma.

For the primary recorded-process study, use Omega=0 for exact retained observations, remove linearly redundant rows, and solve on the independent constraint subspace. Do not silently add a ridge that changes exact constraints into noisy constraints. Numerical stabilization, if needed, must be reported as a change in the observation model.

Matheron's conditional simulation gives independent samples without MCMC: draw X0~Normal(mu,Sigma), draw e0~Normal(0,Omega), and set

    Xsample = X0 + Sigma A_S^T (A_S Sigma A_S^T + Omega)^(-1)(R-A_S X0-e0).

Cache factorizations for fixed masks and retention patterns. Use low-rank plus diagonal algebra rather than a dense nL by nL covariance. Preserving linear constraints and cross-sensor covariance is preferable to arbitrary sensor shuffling. This construction samples plausible transformed sensor fields under a statistical model; it does not enforce vehicle conservation or identify the unique physical hidden state.

Measure reconstruction errors on deliberately hidden valid sensors, coverage at 50/80/95%, pairwise residual correlations, spatial patterns, and performance near congestion thresholds. Report these separately from future forecast accuracy. Failure here limits all downstream risk claims, however small the Monte Carlo error becomes.

#### 6.4 Fine dynamics and process uncertainty

Use one small transparent graph process:

    x_(t+1) = a0 x_t + a1 x_(t-1) + beta W x_t
              + gamma ReLU(W x_t - theta 1) + b(t) + xi_t.

All four dynamic coefficients are nonnegative, theta is a scalar in log-odds units, b(t) is a sensor-specific seasonal intercept, and W is fixed. The state can be any finite real log odds. The inverse transform keeps speed in its modeled range. Fit coefficients by constrained regression, or projected gradient descent, with one-step loss and a small 30-minute rollout loss. Limit complexity to a few thousand seasonal parameters and a rank-16 residual model. No GNN is needed for the proposed certificate.

Use a0+a1+beta+gamma<=0.98 as the initial stability-constrained family. Test a relaxed family <=1.05 on validation only if the stable family fails. Short-horizon enclosures remain valid for the relaxed family, but widths may grow. A failed fit is evidence against this model, not a reason to force a monotone model to win.

The stochastic vector xi is sampled by drawing **entire training residual sequences**, each containing all sensors over H successive steps, within a prespecified broad regime such as weekday/weekend and morning/midday/evening. Construct the bank using out-of-fold training predictions when possible. Draw different rollout residual blocks independently with replacement. Within a rollout, the complete block preserves observed spatial and temporal dependence. Treat the fitted residual bank as fixed when reporting simulation uncertainty. Its finite size and regime misspecification are model uncertainty, not additional independent real events.

Fit no future input from test outcomes. b(t+h) uses known calendar time. Unobserved incidents enter the residual approximation; unexpected distribution shifts remain a limitation. Condition residual blocks on current residual history only if that dependence can be estimated on training data and validated. The first version uses coarse regimes and reports residual autocorrelation.

The aggregate point forecast applies the same expression on a quotient graph. Its omitted variation is bounded in Section 7. A separately fitted aggregate GRU or autoregression with the full retained history is an essential baseline for effective closure/memory. Detailed models are not presumed superior to well-specified coarse models.

#### 6.5 Event, severity and target probability

Let c_h=n^(-1) sum_i 1{x_i,t+h>=0} be the fraction of sensors below half their reference free speed. Define sustained severity

    J = max over h=1,...,H-2 of min(c_h, c_(h+1), c_(h+2)).

The event is Y=1{J>=q}, using three consecutive five-minute frames. Choose q=max(0.10, the training 90th percentile of J), round up to an attainable sensor fraction, and freeze it. This defines an uncommon high-severity episode relative to training, not a universal traffic safety standard.

The population target is p_S(R)=P(Y_observed=1 | R_t,S=R). The simulator computes q_S(R)=P_fitted(J>=q | R). These are different objects. Observational calibration evaluates their agreement; the mathematical certificate below concerns q_S only.

For warning evaluation, restrict primary onset forecasts to times with no currently active sustained event. Group consecutive positive target periods into episodes and merge gaps shorter than 30 minutes. Also report all-time risk prediction separately. Never claim warning lead time for a model evaluated only after an episode has begun.

### 7. Proposed theorem and proof

**Status:** the following construction is proposed here and has an auditable mathematical proof. Its originality relative to the complete graph abstraction literature is not established. The result specializes a standard enclosure argument to a graph quotient with explicit structural defects. Monte Carlo unbiasedness is a consequence, not the novel theorem.

Let B_1,...,B_k be a computational partition, independent of the observation-compression partition. Define P_i,a=1 when i belongs to B_a. For i in B_a, let w_i,b=sum_(j in B_b) W_i,j. Define

    Wbar_a,b = mean_(i in B_a) w_i,b
    D_a,b = max_(i in B_a) |w_i,b - Wbar_a,b|.

Wbar and D are nonnegative k by k matrices. D is a computable measure of variation in outgoing neighborhood composition inside each block, using the row convention for W stated above. It is not ordinary variance of sensor readings.

For a given random scenario, suppose |x_i,h-z_a,h|<=r_a,h for each i in B_a. For the complete forcing f_i,h=b_i(t+h)+xi_i,h, choose fbar_a,h and delta_a,h satisfying |f_i,h-fbar_a,h|<=delta_a,h. Block mean and maximum deviation suffice.

Evolve the coarse point trajectory by

    z_(h+1) = a0 z_h + a1 z_(h-1) + beta Wbar z_h
              + gamma ReLU(Wbar z_h-theta 1) + fbar_h.

Define the radius recurrence, componentwise, as

    e_h = (Wbar + D) r_h + D |z_h|
    r_(h+1) = a0 r_h + a1 r_(h-1) + (beta+gamma)e_h + delta_h.

Initialize r_-1 and r_0 by the maximum absolute deviations of the sampled last two fine states from their block means.

**Proposition.** In exact arithmetic, for every finite sampled initial history and forcing sequence, these radii enclose the corresponding fine trajectory for all h<=H. The claim requires W>=0 and nonnegative dynamic coefficients but does not require Gaussian process noise, independent sensors, a continuous severity distribution, or asymptotic sample sizes.

**Proof.** For i in B_a,

    (W x_h)_i - (Wbar z_h)_a
      = sum_b sum_(j in B_b) W_i,j (x_j,h-z_b,h)
        + sum_b (w_i,b-Wbar_a,b) z_b,h.

The absolute first term is at most sum_b w_i,b r_b,h, which is at most sum_b (Wbar_a,b+D_a,b)r_b,h. The second term is at most sum_b D_a,b |z_b,h|. Their sum is e_a,h. ReLU is 1-Lipschitz. The direct state terms contribute a0 r_a,h+a1 r_a,h-1; the neighbor terms contribute at most (beta+gamma)e_a,h; the forcing contributes delta_a,h. This establishes the recurrence. Induction from the two initial radii proves the assertion.

Define lower and upper congestion fractions

    c_h^- = (1/n) sum_a |B_a| 1{z_a,h-r_a,h>=0}
    c_h^+ = (1/n) sum_a |B_a| 1{z_a,h+r_a,h>=0}.

Apply the same max-of-min sustained functional to obtain J^- and J^+. Monotonicity of indicator, min and max yields J^-<=J<=J^+. Therefore J^->=q certifies an event, and J^+<q certifies a non-event. Otherwise evaluate the fine model using the **same** initial sample and residual sequence. Equality belongs to the event by definition and must be implemented consistently.

At singleton resolution, D=0, the initial radius and forcing deviation are zero, and the coarse system equals the fine system. The construction therefore has an exact finite terminal level, unlike an assumption of an indefinitely improving approximate surrogate.

**Why the structural term matters.** A partition with identical block-level neighbor weights has D=0, but unresolved state and forcing variation can still matter. Conversely, even small state variation can become difficult to enclose when D|z| is large. This supplies an operational reason to split a block based on interaction structure, rather than only on sensor variance.

The bound depends on the chosen origin of the transformed state because of |z|. Centering by a fixed training mean is allowed only if its induced forcing change is included in f. Evaluate this sensitivity. Do not claim the displayed bound is coordinate invariant or the tightest possible enclosure.

**Algorithmic consequence.** Offline, build a small hierarchy by splitting blocks with large training-average radius contribution and structural defect. At runtime, use the cheapest partition that the pilot predicts will meet the latency target. In the minimum version, use one coarse partition and the fine graph. Adding a second intermediate partition is optional. More subdivisions do not automatically produce nested numerical enclosures; intersect valid old and new bounds if nesting is needed, or simply use each valid certificate independently.

**Falsifiable predictions and proof obligations**

| Claim or assumption | Check that could refute it or limit it |
|---|---|
| Enclosure formula is correctly implemented | Compare every coarse interval with coupled fine trajectories on random, near-threshold and adversarial small graphs; any violation blocks certified claims |
| Structural defect has practical value | Compare equal-size geographic and defect-aware partitions; if ambiguity/cost does not improve, withdraw the partition-benefit claim |
| Cheap certification is useful | Measure unresolved fraction and complete pipeline cost; if nearly every sample is unresolved, the method should lose to fine MC |
| Conditional reconstructions are adequate | Hidden-sensor coverage, residual dependence and held-out threshold behavior |
| Retained detail is valuable | Paired held-out event scores versus a strong aggregate-memory and variance/extreme baseline |
| Sampling helps under the fitted model | Independent repeated estimates should show the predicted Monte Carlo variance decline; persistent outcome miscalibration can remain |

**Floating-point qualification.** The proposition is an exact-arithmetic statement. A numerical implementation needs outward rounding or an explicit forward-error allowance for dot products, reductions, ReLU and radius updates. Use FP64 for the small coarse enclosure if affordable, disable reduced-precision matrix products for the reference path, and add computed rounding bounds such as gamma_m=sum-error factor m*u/(1-m*u) times absolute summands. An arbitrary tolerance plus passing tests is not a proof of numerical certification. If a credible floating-point enclosure cannot be implemented, describe the bound as theoretical and use full fine evaluation wherever numerical certification is uncertain.

**Planning-stage arithmetic check.** A small NumPy CPU check of this recurrence on 200 random 12-node graphs with three blocks and six forecast steps found no enclosure violation. The two-cell worked example and the page, memory and GPU-budget arithmetic were also checked. These checks are not dataset experiments, tests of tightness near real event boundaries, proof of floating-point certification, or evidence of novelty.

### 8. Sampling, uncertainty and the budget decision

#### 8.1 Principal method: certified selective Monte Carlo

Sample initial histories independently from the fitted conditional Gaussian and residual sequences independently from the fixed regime-specific empirical bank. For each sample, return its certified event label or its coupled fine event label. The resulting Z_j is exactly the fitted-model event indicator in the mathematical construction.

    qhat_S = (1/N) sum_j Z_j
    E[qhat_S | fitted model, R] = q_S(R)
    Var(qhat_S | fitted model, R) = q_S(R)(1-q_S(R))/N.

This is ordinary Monte Carlo at the level of event statistics. It saves work per completed event evaluation if certificates are cheap. It does not reduce variance at equal sample count. At equal time it may permit more samples. All statements of exactness are relative to the specified predictive model.

Use fixed N chosen from an independent pilot. Report Wilson or exact binomial intervals for independent Bernoulli rollouts. With zero events, a one-sided 95% upper bound is 1-0.05^(1/N), approximately 3/N. Zero observations of an event are not evidence of zero risk. A 1e-5 risk cannot be estimated precisely from a few thousand ordinary samples.

Draws from an empirical residual bank can be independent conditional on that bank, even though the bank contains related historical windows. This does not make bank entries independent evidence about the real world. Model and real-data intervals must therefore remain separate.

Do not stop a sample batch as soon as an ordinary confidence interval looks favorable. Fixed sample counts avoid that problem. If there is a hard deadline, select N in advance using conservative pilot costs and finish all launched scenarios. If that cannot be done, return an explicit incomplete result or bounds for the unfinished indicators, not a mean over only fast-completing scenarios. Certification runtime is outcome dependent.

#### 8.2 Principal competitors

**Plain fine Monte Carlo.** Same conditional distributions, same event definition, same initial sample/forcing pairs where comparisons permit, all scenarios on the fine graph. Include vectorized CPU and GPU implementations.

**Two-level Monte Carlo.** Let Zc be the event of the coarse point trajectory and Zf the coupled fine event. Use independent sample sets for the two terms:

    qhat_2level = mean_(N0) Zc + mean_(N1)(Zf-Zc).

Both fine and coarse paths in a correction sample share the initial scenario and noise. Its expectation is q_S, regardless of coarse event bias. Its variance is V0/N0+V1/N1, where V0=Var(Zc), V1=Var(Zf-Zc). With measured costs c0 and c1, a continuous budget optimum is

    N_l = B_remaining * sqrt(V_l/c_l) / sum_j sqrt(V_j*c_j).

Estimate V_l on a disjoint pilot, impose minimum sample counts, round down/up within the budget, and report actual costs. This allocation is established multifidelity/MLMC mathematics. For uncertainty use independent replicate batches or bounded-variable intervals, not a binomial interval on the two-level sum. The finite estimate can lie outside [0,1]; retain it for unbiased-estimator diagnostics. Any clipping or calibration used for forecast metrics is a separate transformation and loses the unbiasedness claim.

Importance sampling is not part of the minimum study. This avoids learning a high-dimensional proposal on a short schedule. If added later, target the exact normalized conditional Gaussian times residual-bank probabilities, use a defensive mixture proposal with support everywhere the target has mass, freeze it before evaluation, and weight by target/proposal. Conditional residual-bank indices have explicit discrete probabilities. A self-normalized weighted estimate generally has finite-sample bias. No such method should be described as implemented in this paper unless separately validated.

#### 8.3 Where more simulation stops helping

Let I be the complete available sensor history, R_S a deterministic compression of I, p_I=P(Y=1|I), and p_S=P(Y=1|R_S). Assume simulator randomness is independent of the real outcome conditional on I, and the estimate is unbiased for q_S. Then the population Brier risk decomposes as

    E[(Y-qhat_S)^2]
      = E[p_I(1-p_I)]
        + E[(p_I-p_S)^2]
        + E[(p_S-q_S)^2]
        + E[Var(qhat_S | R_S)].

This follows by conditional expectation and orthogonality. It is **background**, not a new contribution. The terms are irreducible outcome uncertainty given I, information lost by compression, fitted conditional-model error, and Monte Carlo variance. Parameter estimation contributes to the fitted-model term when conditioning on a frozen training set. A biased surrogate or clipped estimator requires an additional bias treatment.

Increasing N changes only the last term. Adding selected observations changes the information target and may also change model error and cost. The ideal Bayes information-loss term cannot increase when genuinely additional information is retained, but a finite fitted model can perform worse. None of the first three terms is observable exactly from one held-out trajectory.

#### 8.4 Operational resource objective

For an information set S and computational partition P, let c_setup(S) include reconstruction setup, transfers and mask factorization. Let c_sample include conditional draws and forcing preparation, c_cert(P) the coarse enclosure, c_fine the fine correction, and alpha(S,P) the probability of being unresolved. Approximate amortized cost per scenario is

    c_total(S,P)=c_sample(S)+c_cert(P)+alpha(S,P)c_fine.

Batch compaction and small-kernel overhead must be added or measured directly. The crossover for selective refinement is c_cert + overhead < (1-alpha)c_fine, after cancelling truly shared sample-generation work. A faster coarse kernel alone does not establish this inequality.

Under budget B milliseconds, choose N from a conservative measured lookup of complete batch cost. For each of at most 10-15 candidate configurations, estimate validation Brier score using repeatable Monte Carlo seeds, bytes retained and p95 latency. Select the lowest validation score meeting the budget and memory ceiling. Freeze the configuration before test. Use 100 ms and 1,000 ms per forecast as engineering service targets, not claims that five-minute sensors require those deadlines.

The population design objective is information loss plus model error plus sampling variance, subject to bytes and measured compute. In practice, use held-out Brier risk as its observable proxy. Do not subtract the preceding decomposition's unidentifiable terms and claim to have measured them.

For a simple audit, estimate mean Monte Carlo variance across validation states. If doubling N can at best remove a component much smaller than the validation improvement from 5% additional sensors, retaining detail is the candidate to test. This is a decision heuristic with uncertainty, not a theorem about the true best sensor set. Compare selected configurations against the complete finite grid to report selection regret within that grid.

### 9. Algorithm and computational complexity

```text
OFFLINE
  Validate files, graph ordering, licenses, timestamps and masks.
  Create chronological training, validation and test partitions.
  Fit transforms, calendar effects, conditional history model and fine dynamics.
  Build training residual sequence banks.
  Choose nested retained sensor sets using training information only.
  Build coarse partitions and precompute quotient weights and structural defects.
  Measure complete pilot costs and ambiguity rates on validation inputs.
  Freeze model, information sets, thresholds, budgets and sample counts.

FORECAST(retained_history, configuration, random_stream)
  Condition the history distribution using only retained_history and masks.
  Draw the prespecified independent scenarios and their residual sequence indices.
  For each scenario batch:
    Initialize the coarse trajectory and initial error radii.
    Compute block forcing centers and deviations from the sampled sequence.
    Propagate coarse states and radii for six steps.
    Compute lower and upper sustained-event severity.
    Assign all certified positive and negative indicators.
    Compact unresolved scenario indices.
    Run the fine graph on those same initial states and forcing sequences.
    Complete all event indicators before updating the estimate.
  Return probability, Monte Carlo interval, sample count, unresolved fraction,
         latency components, bytes retained and provenance identifiers.
```

With n nodes, m graph edges, k blocks, e_P nonzero quotient/defect entries, H steps and N samples, fine dynamics cost O(NH(m+n)). Conditional low-rank sampling costs approximately O(N nL r) plus cached constraint solves, with r=16. A dense observation solve is O(d_S^3) setup and must not be hidden. Exploit the covariance structure and fixed masks, or reduce the conditioning history used by the Gaussian while keeping the aggregate baseline's full history.

The certificate path costs O(NH(e_P+k)), plus O(Nn) initial reductions and O(NHn) forcing preparation if all local residuals are gathered. Fine corrections cost O(alpha NH(m+n)). This O(NHn) floor is important, especially for sparse graphs. The method cannot have O(k)-only total cost when it reads or samples every local forcing entry.

An optional optimization is to precompute block centers and deviation bounds for each training residual sequence and each fixed computational partition. Combine residual and seasonal forcing bounds by the triangle inequality. Then gather full residual arrays only for unresolved scenarios. Count the offline preprocessing and bank storage, and verify that the reused bounds still enclose the exact chosen forcing. This can reduce repeated forcing work but cannot remove the cost of initial conditional reconstruction.

State memory can be O(batch_size*(nL+n+k)) with rolling buffers and streamed forcing. Storing every possible future for every forecast time is unnecessary. Peak memory and transfer volume must be measured, including sparse indexing and temporary tensors.

### 10. Real-data protocol and decisive experiments

#### 10.1 Chronological splits and missingness

Use the first 60% of complete calendar days for training, the next 20% for validation and the final 20% for test. Save exact dates after reading the file. All history and future labels of a window must lie within its split. Apply an additional 90-minute embargo around boundaries. No random split of overlapping windows is allowed.

Determine sensor-quality exclusions on training data only. Keep raw quality flags. Zero speed may mean a stopped queue or a dataset missing-value sentinel; resolve the actual file convention before labeling it. Never recode every zero as congestion or every zero as missing without evidence. Do not fill a missing label with a future/past interpolated speed and count it as an observation.

For deployment, causal last-value filling is allowed for one five-minute gap, followed by a training seasonal estimate plus a missing indicator. The conditional sampler should instead omit unavailable observation constraints. Outcome eligibility requires at least 95% observed sensors across the complete future horizon. For remaining unknown outcomes, compute lower/upper event labels by treating missing sensor indicators as 0/1. Use only unambiguous labels for the primary observed-outcome scores and report exclusion rates by time, speed regime and missingness. This is a complete-outcome estimand with possible selection bias, not an assumption that missingness is harmless.

Fix the whole-network threshold from training. Require at least 100 training episodes and 30 validation episodes before fitting elaborate models. Count test episodes once after freezing the design. Fewer than 30 test episodes, or fewer than 15 days containing events, is a reason to report exploratory estimates with wide intervals rather than strong tail-performance conclusions. Do not tune a threshold on test to manufacture more positives.

At day-one development, if the whole-network task has inadequate training events, allow one prespecified alternative: up to four metadata-defined connected regions, with training thresholds per region. Keep all regions from a day in the same split and uncertainty cluster. This is not four independent datasets. Record the decision before inspecting test outcomes.

#### 10.2 Aggregation ambiguity without cherry-picking

Construct matched pairs of forecast origins using only information available at prediction time. Match across different days, separated by at least 48 hours, with the same weekday/weekend category and time-of-day within 60 minutes. Use block-mean history distances scaled by training variation. Add two interpretable calipers: current network mean speed within 2 mph and current congested fraction within two percentage points.

Use a training-derived PCA representation of block histories if necessary, retaining 95% of training variance; still report maximum differences in the original block summaries. The initial normalized matching-distance caliper is 0.25. Feasibility can choose among 0.10, 0.25 and 0.50 on training/validation only, before test matching. Do not expand test tolerances after seeing outcomes.

Perform deterministic nearest matching without replacement and without consulting future labels, fine forecasts or local concentration scores. Retain every accepted pair. Report pair count, independent day count, outcome-discordance rate and residual differences in every matching variable. A matched observational pair is not an exact counterfactual.

For all pairs, relate outcome differences to prespecified local descriptors: fraction of severe neighboring pairs, maximum neighborhood-average intensity, and the retained-sensor model's risk difference. Control descriptively for residual macro differences. Report associations and predictive discrimination, not a causal effect of rearranging traffic.

Figure examples must be selected by a deterministic rule, such as the closest pair among outcome-discordant pairs with complete labels. State that rule and show the complete pair distribution elsewhere. Include a negative example where local detail does not change the forecast.

#### 10.3 Small controlled mechanism experiment

Implement a one-dimensional cell transmission model with one bottleneck and 20 cells, following the conservation-based traffic formulation in Daganzo's original work. [M1] This establishes possible mechanisms, not calibration to PEMS-BAY.

For cell i, density rho_i has units vehicles/km, cell length ell_i is km, capacity Q_i is vehicles/hour, and the time step Delta is hours. With free speed v_i and backward-wave speed w_i in km/hour and jam density rho_i,jam,

    sending_i = min(v_i*rho_i, Q_i)
    receiving_i = min(w_i*(rho_i,jam-rho_i), Q_i)
    flow_i,i+1 = min(sending_i, receiving_(i+1))
    rho_i,next = rho_i + Delta/ell_i * (flow_(i-1),i - flow_i,(i+1)).

Enforce the appropriate CFL condition, Delta*max(v_i,w_i)/ell_i<=1, nonnegative density, storage bounds, and conservation including external boundary queues. Use a 5- or 10-second internal step and report five-minute outputs. Initialize paired feasible density fields with identical total vehicles and identical histograms but different ordering relative to the bottleneck. Hold capacities, demand, boundary conditions and random forcing streams equal within pairs. Sample loads and bottleneck strengths from a prespecified grid; no fitting to produce dramatic examples.

Use at most 2,000 paired initial states across three load regimes. Split by complete initial-state pair and demand/bottleneck family. Do not treat outcomes from one disturbance family as independent replications. Report sustained queued length, maximum occupied fraction and admitted/exited vehicles. The Section 7 theorem is for the graph predictive model; it does not automatically certify this CTM. Do not claim it does without a separate derivation.

#### 10.4 Minimal baselines

| Baseline | Information and model | Purpose |
|---|---|---|
| Seasonal/persistence | Current regional level, calendar, and recent aggregate changes; a calibrated logistic or empirical event predictor | Establish a strong simple lower-cost reference |
| Aggregate memory | All L block-mean frames and masks; regularized autoregression or a small GRU | Test whether suitable temporal closure already resolves the problem |
| Aggregate plus heterogeneity | Same history plus within-block variance, minimum/maximum and current severe fraction; gradient-boosted classifier | Test whether cheap sufficient-looking statistics recover most benefit |
| Full-detail discriminative reference | Complete sensor history with a small graph-temporal model or matched-capacity classifier | Detect misspecification in the transparent stochastic dynamics |
| Fine Monte Carlo | The proposed conditional distribution and fine dynamics at each retained fraction | Hold model and information fixed while changing numerical evaluation |
| Certified selective MC | Same conditional law and fine event; use Section 7 | Principal computational method |
| Two-level MC | Same law with coupled coarse/fine correction | Credible variance-reduction competitor |

Use the same training dates, masks, event definition and validation budget. Allocate at most six prespecified hyperparameter settings per model family and three fitted seeds only for the finalist models. A weak aggregate baseline is not acceptable evidence for information loss. A full-detail reference has more information and should not be called an equal-information comparison.

Separate three comparisons: equal information and runtime, equal information and sample count, and equal transmitted bytes. Report raw and validation-calibrated probabilities separately. Use one shared calibration family, such as logistic calibration with regularization, fitted only on validation. A calibrated probability is no longer claimed to be the unbiased simulator probability.

#### 10.5 Metrics and intervals

Primary prediction metric: event Brier score. Primary detection metric: event recall at a false-alarm rate selected on validation, initially 5% of eligible non-event forecast origins. Freeze the threshold and report the actual achieved test false-alarm rate. Add precision-recall AUC, precision at that threshold, calibration intercept/slope, reliability curves, and prevalence. PR-AUC is interpreted together with its prevalence baseline.

Ordinary behavior: 15/30-minute speed MAE and median absolute error, separated from severe periods. Severity: absolute error in sustained congested fraction J, expressed in percentage points. Warning performance: lead time from the first qualifying pre-onset warning to observed onset, with one warning counted per episode and a stated matching window. Report undetected episodes rather than computing lead time only among successes without their denominator.

A certificate for a binary threshold does not certify numerical severity. Estimate severity on a prespecified audit subset using fine Monte Carlo for all methods, or refine whenever J^- differs from J^+. Include its additional compute. Never substitute the coarse midpoint J as an unbiased fine-severity estimate.

For observational score differences, bootstrap whole calendar days or multi-day blocks, preserving all sensors, regions and overlapping forecasts within a block. Resample paired method predictions together. Use episode groups for event recall summaries and report how correlated episodes within a day are handled. Monte Carlo intervals describe simulation noise at a fixed origin; these block intervals describe variability over observed periods. They are not interchangeable.

For 95% performance intervals, use 1,000 CPU bootstrap replicates. With only a few independent days or episodes, emphasize the counts and uncertainty rather than claiming significance from thousands of overlapping windows.

#### 10.6 Bounded experiment matrix

| Experiment | Prespecified configurations | Evidence produced |
|---|---|---|
| Observed-outcome comparison | Up to four predictive baseline families plus selected MC configurations; chronological test | Ordinary versus severe accuracy and calibration |
| Information curve | Retention 0%, 5%, 15%, 30%, 100%; fine MC; three N values 256, 1,024, 4,096 on a bounded origin panel | Information and sampling effects separated |
| Numerical efficiency | Fine MC, certified MC, two-level MC at 15% retention; two latency targets | Equal-model estimation error versus measured work |
| Certificate audit | 16/32/64 blocks plus singleton terminal graph; random and near-threshold inputs | Enclosure correctness, width and unresolved fractions |
| Retention ablation | Influence, random, and variance selection at 15% only | Whether the local selector adds value |
| Closure/missingness ablation | One reduced-history condition; one 10% spatially clustered mask condition | Robustness to memory removal and correlated missingness |
| Controlled mechanism | At most 2,000 paired CTM states, three load regimes | Exact equal-aggregate counterfactuals within a specified simulator |
| Engineering scale | One actual LargeST year, progressively larger real subgraphs; bounded forecast-origin panel | Bytes, processing rate, memory, p50/p95 latency and exact event agreement with fine computation |

Avoid the full Cartesian product. Run the information curve on at most 512 uniformly time-sampled validation origins initially. The test outcome study uses all eligible test origins for frozen finalist configurations. A numerical audit panel of at most 128 origins can oversample high-risk cases using a training-fitted score, with its selection rule and sampling weights recorded; it must not replace population outcome evaluation.

For numerical integration error, compute a fixed large fine-MC reference, initially 65,536 samples at each audit origin, and retain its own uncertainty. Compare repeated estimates against it with reference-error accounting. If the reference is too noisy for the desired claim, enlarge only the affected audit or weaken the claim. This reference estimates the fitted model, not true traffic risk.

**Main rejection rule.** If the augmented aggregate-memory baseline matches or exceeds the retained-detail method within useful uncertainty at comparable bytes/runtime, reject the prediction that local identity materially improves this task. If certified MC does not reduce complete time-to-error against competent fine MC or two-level MC, reject the computational-benefit claim. If the observational predictor is badly miscalibrated or worse than persistence, numerical speedup alone does not rescue the proposed empirical contribution.

### 11. Big-data pipeline and honest scale accounting

At five-minute cadence, 325 sensor readings correspond to about 1.08 sensor readings/second averaged over time. Even 8,600 correspond to about 28.7 readings/second. These native rates are not an extreme-velocity ingestion workload. The credible big-data aspects are archive volume, graph-wide state, constrained retained histories, many conditional scenario queries, and replay/catch-up processing.

For one non-leap year with a complete five-minute grid, 8,600*105,120 gives 904,032,000 sensor-time positions. Its speed/flow values alone require about 3.62 GB in float32. Serialized HDF5, indices, masks and metadata can be larger. This is a dimensional calculation, not a statement that all positions are valid or that this plan has processed them.

For PEMS-BAY, a 12-frame history plus six-frame target permits at most 52,116-12-6+1=52,099 windows before quality filtering and split boundaries. Window count does not multiply the number of independent observations. Likewise, 10,000 forecast origins times 4,096 scenarios times six steps times 325 sensors creates approximately 79.9 billion **simulated state updates**. Label these as computational work, never as new observed traffic data.

Use an append-only raw layer, chunked preprocessing, and arrays partitioned by day. CPU workers validate timestamps and quality, transform speeds, update block sums/counts and write columnar metadata or chunked arrays. Keep a ring buffer for recent selected histories. Pass pinned contiguous arrays to the GPU; retain model weights and reusable constraints on device. Avoid repeatedly parsing CSV during inference.

| Pipeline stage | Reads and retained state | Cost/saving to report |
|---|---|---|
| Sensor/edge ingestion | Reads every available sensor if computing global block summaries | No ingestion saving claimed |
| Edge summarization | Block means, counts, masks and fixed selected histories | O(n) work per frame, including transform cost |
| Transmission or central archive | Summaries plus selected values and their identifiers | Actual serialized bytes, including masks and metadata |
| Conditional reconstruction | Recreates sampled local fields from retained information | Setup, sampling, factorization and transfer costs |
| Scenario evaluation | Coarse certificate and unresolved fine trajectories | Computation saving conditional on measured ambiguity |
| Archival replay | Reads successive days with bounded memory | Cold and warm throughput separately |

With k_observation blocks and s retained sensors, an ideal numeric payload is roughly 4*(k_observation+s) bytes per frame before counts, masks, identifiers and protocol overhead. Compare with the full 4*n-byte value vector, then report actual files/wire encodings. Do not present the ideal formula as a measured compression ratio.

Run scale measurements on increasing actual observation spans, such as 7, 30 and up to 365 days, and on the actual available graph subsets. Record input bytes/second, valid sensor readings/second, completed scenarios/second, event labels/second, p50/p95 forecast latency, peak host RAM and VRAM. At larger graphs where only an uncalibrated stress process is run, event accuracy means agreement with its own fine computation, not observed traffic accuracy. Keep a separate panel for real held-out predictive performance.

Replaying the same day faster is a legitimate throughput stress test when labeled as replay. Cloning disconnected networks is optional engineering stress, not independent events, new traffic evidence or a demonstration of physical scale generalization. No database cluster, distributed training system, or Kubernetes deployment is needed for this paper.

### 12. RTX 6000 Ada implementation and resource budget

The hardware assumption matches NVIDIA's RTX 6000 Ada specification of 48 GB GDDR6 ECC. [H1] Assume 64 GB host RAM and at least 40 GB scratch capacity for planning; verify actual host resources on day one and reduce cache sizes if needed. Do not substitute RTX A6000, Quadro RTX 6000, or RTX PRO 6000 benchmark numbers.

Use a current stable PyTorch installation compatible with the actual installed NVIDIA driver, NumPy/SciPy, a columnar/chunked data reader, scikit-learn for small baselines, pytest, and Matplotlib. Pin versions only after the environment smoke test. Avoid migrating the original TensorFlow DCRNN stack just to recreate a baseline. A small independently implemented graph-temporal reference is sufficient if identified as such.

The GPU-parallel work is conditional linear algebra, independent scenario generation, sparse/dense graph products, trajectory stepping and event reductions. CPU work is file I/O, quality checks, calendar splits, metadata matching and bootstrap statistics. Likely bottlenecks are constraint solves, residual-bank gathers, small graph kernel launch overhead, and compaction when few unresolved scenarios remain.

**Starting tensor sizes, excluding temporary allocations**

| Object | Shape and dtype | Approximate storage |
|---|---|---:|
| Primary sampled histories | [1,024, 12, 325], float32 | 15.97 MB |
| Primary six-step forcing | [1,024, 6, 325], float32 | 7.99 MB |
| Primary coarse centers/radii | Two arrays [1,024, 32], float64 | 0.52 MB together |
| Large-graph sampled histories | [512, 12, 8,600], float32 | 211.35 MB |
| Large-graph six-step forcing | [512, 6, 8,600], float32 | 105.68 MB |
| Large graph scalar edge gather, if materialized | [512, 201,363], float32 | 412.39 MB |

Use batch sizes 256, 1,024 and 4,096 on PEMS-BAY in the pilot. Start with 128 or 512 for larger graphs. Stop growth at 32 GB allocated VRAM, leaving room for temporary buffers and libraries. Do not expand [batch, edges, channels] tensors unnecessarily. Sparse matrix products or edge-wise fused reductions are preferable for the large graph. At 325 nodes, dense multiplication may win despite doing more arithmetic; measure it.

Use FP32 for fitting and ordinary simulation initially. Use FP64 for covariance setup, numerical audit references, probability accumulators and coarse radius calculations when feasible. BF16/FP16 experiments are optional and must measure event-label flips, threshold-neighborhood errors and changes in calibration. The high throughput of tensor cores is not evidence that reduced precision is appropriate for event boundaries.

Benchmark eager vectorized GPU, compiled GPU if compilation amortizes, and a vectorized multicore CPU implementation using sparse BLAS or Numba as appropriate. Record CPU model and thread count. Warm up kernels and compilation separately. Synchronize around GPU timing or use CUDA events for device time, and use wall time for end-to-end latency. Include host-to-device transfers and conditional reconstruction in the service result. Report batch throughput and single-query latency separately.

Use named seed streams for data splitting, model fitting, conditional Gaussian draws, residual-bank indices and numerical repetitions. Key common random scenarios by forecast origin and scenario identifier so changing batch size or compaction does not change the coupled draw. Record commit, environment lock, model hash, configuration hash and input manifest for every result. Record whether sparse operations are deterministic under the chosen backend.

**24 GPU-hour provisional ceiling**

| Work package | Maximum planned GPU hours |
|---|---:|
| Smoke tests, cost pilot and precision audit | 2 |
| Conditional model and transparent dynamics fitting | 4 |
| Predictive baselines and limited tuning | 3 |
| Certificate/partition implementation audit | 1 |
| Frozen main prediction and information-curve evaluations | 5 |
| Repeated numerical estimates and fine reference panel | 2 |
| Controlled traffic mechanism experiment | 1 |
| Graph-scale and streaming companion measurements | 2 |
| Minimal retention/memory/missingness ablations | 1 |
| Reserve for a diagnosed failure, not extra exploration | 3 |
| **Total** | **24** |

These are allocation caps, not runtime estimates. After a 90-minute pilot, project full costs from measured training throughput, complete forecast times, unresolved fractions, disk rate and mask-cache behavior. A faster-than-needed job should stop; there is no requirement to consume its allocation.

An optional extension to 48 GPU-hours would add up to eight hours for a second chronological/seasonal replication, six for stronger conditional residual modeling, six for broader large-graph outcome validation if a valid target is available, and four for a tighter enclosure or extra numerical audit. Do not spend that extension on a second physical domain. It is not authorized by this planning task.

### 13. Figures, tables and talk example

Produce scientific plots from actual saved results. Use Matplotlib with vector PDF/SVG and readable embedded fonts, a blue/orange/gray palette, direct axis units and consistent notation. Supply alt text. Concept examples are explicitly illustrative. Do not generate synthetic photographs or empirical-looking plots without data.

| Figure | Required data and panels | Axes and uncertainty | Scientific claim |
|---|---|---|---|
| 1. Same aggregates, different local conditions | A deterministic controlled pair and the full observational matched-pair analysis | Local intensity by node/road position; distribution of future severity differences; matching residuals and day-bootstrap intervals | Aggregation can conceal relevant configurations; observational evidence is associative |
| 2. One held-out episode | Time series selected by a saved deterministic rule, including an aggregate baseline, retained-detail probabilities, observed congested fraction and missingness | Clock time or minutes to onset; probability and observed fraction in separate panels; narrow MC interval distinguished from model uncertainty | Whether warning precedes measured onset and how predictions differ |
| 3. Information versus simulation | Retention fractions crossed with sample counts, plus variance/extreme baseline | Bytes retained or sensor fraction on x; Brier score on y; independent day intervals; a second panel for MC variance versus N on log scales | More scenarios can reduce MC error without repairing a poor information representation |
| 4. Certificate and system tradeoff | Coupled fine/coarse audits and CPU/GPU timing logs across graph sizes | Error radius/actual error; unresolved fraction; RMSE versus total milliseconds; peak memory and throughput as small companion panels | The explicit graph bound is correct and pays for itself only in identifiable operating regions |
| Optional 5. Spatial observed episode | Sensor coordinates, speed observations and the fixed retained sensor set | Map or road-distance graph colored by observed speed at three timestamps; markers for retained sensors | Local structure and sensor retention, with no causal arrows |

Keep Figure 4 to four readable panels; put extra scaling plots in the supplement. Show both geographic and defect-aware partition results at equal block counts. Omit maps if spatial coordinates or road matching are unreliable.

Use three main tables: (1) data, split dates, valid observations and independent episode/day counts; (2) main event/ordinary metrics with paired uncertainty and actual false-alarm rates; (3) costs, bytes, numerical fidelity and configuration choices. Condense the literature comparison to prose or a supplementary table if needed to meet the main-text budget.

**A mathematical example for the talk**

Consider two traffic cells in a line, each with storage for 50 vehicles. In one minute, at most 20 vehicles can transfer between cells, the downstream exit serves five vehicles, and external demand is 20 vehicles. Let incoming=min(20,50-n1), transfer=min(n1,20,50-n2), and outgoing=min(n2,5). Update each cell by adding incoming flow and subtracting outgoing flow. This is an illustrative finite-volume queue calculation, not a calibration to a real road.

| Configuration | Initial cells (vehicles) | Mean | Population variance | Incoming, transfer, exit | Next cells |
|---|---|---:|---:|---|---|
| A | (40,10) | 25 | 225 | (10,20,5) | (30,25) |
| B | (10,40) | 25 | 225 | (20,10,5) | (20,45) |

Both initial states have identical mean, variance, minimum, maximum and histogram. Yet a next-step threshold of 42 vehicles in either cell is crossed only in B. The same external demand was offered to each system; the different admitted flow follows from local storage. Unadmitted demand remains in an external queue if modeling the complete system, preserving conservation.

If A and B are equally likely and the observer retains only permutation-invariant summaries, the best event probability is 1/2 and its Brier score is 1/4. Reading the downstream cell distinguishes these two deterministic cases. This simple Bayes calculation is illustrative background, not the paper's theorem. It explains why even mean-plus-variance can miss the location of stress.

### 14. Paper and talk structure

Suggested paper title: **When Averages Hide Congestion: Local Information and Simulation Budgets in Predictive Digital Twins**.

If the certificate yields the strongest result, use **Graph Aggregation Bounds for Congestion Risk in Predictive Digital Twins**. If the speedup fails, remove language suggesting successful acceleration. Do not use "cascade prediction" in the title unless its meaning is explicitly limited and the evidence supports it.

The 14-page main-text target below assumes the actual CFP-linked Springer LNICST layout. Reallocate after compiling the official class, without shrinking margins or fonts.

| Main-text component | Target pages |
|---|---:|
| Abstract and introduction | 1.5 |
| Related work and novelty boundary | 1.0 |
| Observation model, event task and retained information | 1.5 |
| Graph enclosure and proof | 2.5 |
| Sampling algorithm and resource decision | 1.5 |
| Data and evaluation protocol | 1.5 |
| Results, including figures and tables | 3.5 |
| Limitations and conclusion | 1.0 |
| **Main text total** | **14.0** |

Plan two to three additional pages of references and a compact supplement for floating-point details, complete configuration tables, missingness analysis and extra plots, subject to the confirmed venue instructions. Include a full main-text proof of the central proposition so the theory does not disappear into an appendix. Preserve anonymization, alt text and the venue's current disclosure requirements. The work here goes beyond copy editing; consult the CFP's AI-use guidance when preparing the manuscript. [C1]

**Ten-slide storyline**

1. Two roads can have the same average and different next outcomes. Use the two-cell example.
2. Define the real observed outcome and distinguish congestion from causal cascades.
3. Show what the edge retains and what the central twin no longer sees.
4. Explain conditional reconstruction as multiple plausible local fields.
5. Introduce the graph structural-defect term with one small block example.
6. Explain the event certificate and the fine-evaluation fallback.
7. Show the held-out episode and baseline comparison.
8. Show retained information versus scenario count.
9. Show actual CPU/GPU latency, ambiguity and memory, including failures.
10. State the supported conclusion, model limitations and next experiment.

Adapt to the organizer's confirmed presentation duration. This plan does not assume a live 10-minute slot has been granted.

### 15. Dated schedule and decision gates

| Date | Deliverable | Continue / simplify / stop rule |
|---|---|---|
| Sept 22 | CFP record, source inventory, local environment/resource inspection, data-access attempts | Do not launch a large run. Establish actual GPU identity, host memory, data terms and download feasibility |
| Sept 23 morning | Data manifest, chronological splits, missingness audit, training event counts | Continue if accessible real outcomes and adequate development events exist. One declared region/target fallback is allowed before test inspection |
| Sept 23 afternoon | Proof audit, closest-theorem comparison, exact small examples, first pilot | Continue only with a valid enclosure and plausible distinct claim. If the theorem is known, revise attribution/claim before experimentation |
| Sept 24 | Transparent model and aggregate baselines, reconstruction coverage, measured cost model | If the transparent model is materially worse than persistence or coverage is poor, simplify the uncertainty model or switch to the limited fallback. Cap repair at one day |
| Sept 25 | Frozen thresholds/models/configurations, completed certificate audit and initial observed-outcome run | No certified claim after any unexplained enclosure violation. Enable refinement only if full pipeline cost can plausibly beat fine MC |
| Sept 26 | Main information/resource curves, paired observed evaluation, numerical reference panel | If local detail gives no useful benefit, write the negative finding honestly. Stop extra architectures |
| Sept 27 | Bounded actual-data scale run, controlled mechanism and final uncertainty analysis | If scale access fails, state the smaller scope. Do not replace missing real evidence with replicated synthetic rows |
| Sept 28 | Complete paper in official template, four reproducible figures and three tables | Freeze experiments except corrections to diagnosed errors. Audit every claim against a saved result |
| Sept 29 | Final scientific and visual review, anonymized submission candidate, source archive | Target completion before the ambiguous deadline time zone becomes relevant |
| Sept 30 | Buffer for required corrections and user-controlled submission | No new research branches. Confirm actual submission receipt if the user separately requests submission |

**Practical gates.** Stop the high-fidelity acceleration branch if measured coarse overhead is larger than saved fine work across both latency targets. Simplify to one retained-detail fraction if the full grid projects above 24 GPU-hours. Stop the intended empirical paper if neither permitted traffic dataset yields usable observed outcomes. Stop claiming a theoretical contribution if the only remaining mathematics is standard Monte Carlo or conditional variance. A later submission is preferable to inventing results or disguising missing evidence.

### 16. Repository structure

Use a normal Python package with descriptive module and variable names. Keep analysis scripts thin and reusable algorithms in the package. Do not couple data downloading, training, scoring and plotting in one notebook.

| Path | Responsibility |
|---|---|
| README.md | Study question, exact reproduction commands and current limitations |
| pyproject.toml and environment.lock | Package definition and tested dependencies |
| configs/data_sources.yaml | Source links, permitted paths, date rules and download limits |
| configs/minimum_study.yaml | Frozen horizons, thresholds, retention sets and compute caps |
| configs/numerical_audit.yaml | Precision, test graphs and boundary cases |
| src/traffic_risk_twins/data_access.py | Verified downloads and manifest generation |
| src/traffic_risk_twins/observation_quality.py | Missingness, units, masks and timestamp validation |
| src/traffic_risk_twins/chronological_splits.py | Leakage-safe windows, embargoes and event groups |
| src/traffic_risk_twins/retained_information.py | Block summaries and fixed sensor selection |
| src/traffic_risk_twins/conditional_history.py | Low-rank Gaussian fitting and conditional simulation |
| src/traffic_risk_twins/graph_dynamics.py | Fine predictive process and CPU/GPU implementations |
| src/traffic_risk_twins/graph_enclosures.py | Quotient weights, structural defects and error radii |
| src/traffic_risk_twins/event_functionals.py | Sustained threshold events and severity |
| src/traffic_risk_twins/scenario_estimators.py | Fine, certified and two-level MC |
| src/traffic_risk_twins/resource_selection.py | Measured configuration grid and budget selection |
| src/traffic_risk_twins/observational_evaluation.py | Metrics, matched pairs and episode/day resampling |
| src/traffic_risk_twins/cell_transmission.py | Separate controlled mechanism experiment |
| scripts/run_data_audit.py | Data-only entry point |
| scripts/run_pilot.py | Bounded pilot and run-cost forecast |
| scripts/run_minimum_study.py | Frozen experiment matrix |
| scripts/build_paper_figures.py | Figures from saved numeric outputs only |
| tests/ | Mathematical invariants, leakage, conditioning and coupling checks |
| manifests/ | Source/derived dataset hashes and provenance |
| results/tables/ and results/figures/ | Generated CSV/Parquet and vector figures |
| reports/ | Feasibility, proof, pilot and final evidence reports |
| paper/ | Actual conference template, manuscript, bibliography and compiled PDF |

Ignore raw data, large caches and generated environments in git. Checkpoint run metadata and small results. If the project is backed by a repository, use its normal version control rather than duplicate the repository in another artifact store.

### 17. Ready-to-paste Codex implementation prompt

The following prompt authorizes bounded implementation and a pilot in the receiving session. It does not authorize this planning session to run experiments. It intentionally leaves the 24-hour full study behind a reviewable pilot report because current data access, event counts and throughput remain unknown.

```text
Act as my research software collaborator. Implement the minimum study in the
attached EAI_BDCC_2026_Research_Plan.md. Read the complete plan first, inspect
the existing repository and any applicable AGENTS.md, and preserve existing
work. Do not invent measured outcomes or silently change the research target.

Research objective
Measure when retaining local traffic sensor information improves sustained
congestion-risk forecasts more than increasing simulation count. Implement
the graph aggregation enclosure with structural-defect matrix D, and compare
certified selective Monte Carlo with competent fine Monte Carlo and a coupled
two-level Monte Carlo estimator. Novelty is provisional. Standard Monte Carlo,
conditional Gaussian identities, and conditional Brier decompositions are
background and must be cited as such.

Resources and authorization
- Use one NVIDIA RTX 6000 Ada Generation with 48 GB VRAM. Verify device name
  and memory. Do not assume RTX A6000, RTX PRO 6000, or multiple GPUs.
- Complete local implementation, data auditing, meaningful correctness checks,
  a small fitted baseline, and a pilot of at most 2 total GPU-hours.
- Count all fitting, warm-up, compilation, simulation and reruns against that
  pilot budget. Track wall time and CUDA device timing separately.
- The proposed 24 GPU-hour study is not yet authorized by this prompt. Stop
  before it and supply a concrete pilot report and frozen execution command.
- Limit initial downloads to 12 GB, processed/cache output to 20 GB, and active
  GPU allocation to 32 GB. Use chunked reads. Do not fetch all LargeST years.
- Do not contact people, submit a paper, create paid resources, or deploy a
  service. Do not rewrite git history or overwrite unrelated changes.

First deliverables
1. Create reports/FEASIBILITY_REPORT.md with GPU/host details, verified source
   and license evidence, actual file sizes, timestamps, masks, graph ordering,
   train/validation event counts and unresolved venue requirements.
2. Use originating DCRNN links for PEMS-BAY. Dataset license is unresolved in
   the plan: do not equate repository MIT licensing with raw-data terms. Record
   what you verify. Do not redistribute data without an applicable license.
3. If PEMS-BAY access/terms block use, follow the single LargeST SD alternative
   in the plan and explicitly rename the outcome throughput extremes. Do not
   relabel flow as speed or simulated cascades as real observations. If neither
   option is usable, finish reusable code and explain the specific data blocker.
4. Check the current BDCC 2026 CFP and official author-kit link. Preserve the
   actual downloaded template; do not substitute another conference's style.
   Do not claim specific remote presentation arrangements without evidence.

Implementation
- Use descriptive names and a package layout following the plan. Separate
  data access, conditioning, graph dynamics, enclosures, events, estimation,
  resource measurement and observational evaluation.
- Split by complete chronological days 60/20/20 with windows wholly inside
  splits and a 90-minute boundary embargo. Fit transformations, thresholds,
  priors, selection, calibration and partitions without test information.
- Implement explicit masks. Resolve zero/missing-value conventions. Exclude
  ambiguous future labels by bounded missing-indicator analysis, not imputation.
- Implement the low-rank-plus-diagonal conditional Gaussian and Matheron
  sampling. On exact constraints remove redundant rows; do not add unexplained
  noise. Verify aggregate/retained-value consistency numerically. Sample only
  from information actually supplied to the deployed function.
- Implement the stated transparent nonnegative graph recurrence, with full
  residual sequences sampled across all sensors. Preserve within-sequence
  spatial/temporal dependence and train-only residual-bank construction.
- Implement quotient weights, D, coarse trajectory, error radii and sustained
  event lower/upper bounds exactly as in the plan. Forcing reductions and
  initial radii are real costs. Do not assume the CTM satisfies this theorem.
- Treat floating-point certification separately from the exact-arithmetic
  proof. Implement outward/forward-error bounds or label numerical guarantees
  as empirical and fall back to fine computation where they are uncertain.
- Use common scenario identifiers and random streams for paired fine/coarse
  calculations. Refinement must reuse the same initial state and forcing.
- Fine MC and certified MC use fixed N and complete every launched scenario.
  Never average only scenarios that finished before a deadline.
- Implement two-level MC with an independent cheap sample and independent
  correction samples, and shared randomness within each correction pair.
  Estimate allocation variances/costs on an independent pilot. Retain raw
  estimates for unbiasedness checks and label any probability clipping.

Meaningful validation
- Check conservation, nonnegativity and CFL conditions in the separate CTM.
- Check the two-cell worked example exactly.
- Exhaust or densely cover small graph states near thresholds. Check every
  claimed coarse enclosure against its coupled fine trajectory. Include graph
  blocks with identical and very different external neighborhood weights.
- Verify singleton partitions recover the fine model and nonzero D is not
  silently ignored. Include missing constraints and all-observed histories.
- Verify no test observation or future outcome enters fitting or selection.
- Compare empirical conditional moments against analytic Gaussian moments.
- Verify fixed-scenario event agreement between fine and certified methods,
  and repeated two-level estimates against a small exactly enumerable case.
- Verify zero-event uncertainty and event-threshold equality conventions.
- Do not write superficial tests that only duplicate implementation formulas.

Pilot
Use at most 128 validation forecast origins, initially 256 and 1,024 scenarios,
retention 0%, 15%, 100%, and one coarse partition plus the fine graph. Fit only
what is needed for the pilot. Measure vectorized CPU, eager GPU and compiled
GPU only if compilation fits the cap. Separate warm-up and complete latency.
Record conditioning, residual gather, enclosure, compaction, fine evaluation,
transfer, host RAM and VRAM. Audit FP32 versus FP64 event boundaries.
Do not inspect test results to make development choices.

Outputs and acceptance criteria
- reports/PROOF_AUDIT.md explaining every assumption, nearest prior results,
  proof obligations and whether theoretical novelty remains plausible.
- reports/PILOT_REPORT.md with actual work completed, exact GPU time, costs,
  unresolved fraction, event counts, reconstruction coverage and model errors.
- A data manifest and frozen configuration file sufficient to reproduce the
  pilot, including seed streams, environment lock and source/commit hashes.
- Numerical CSV/Parquet results and two clearly labeled pilot figures generated
  from those results. No fabricated performance or decorative empirical plots.
- A projected full-run budget no greater than 24 GPU-hours, based on measured
  costs, plus one exact command that enforces the cap if I authorize it later.
- A clear continue/simplify/stop recommendation. Disable the acceleration
  claim if coarse overhead exceeds saved work; stop certified claims after an
  unexplained enclosure violation; stop real-outcome claims if data are unusable.
- Report whether the transparent model is competitive with persistence and
  aggregate-memory/heterogeneity baselines. More simulation cannot repair a
  failed conditional model.

Persist code and reports in the repository. If its existing workflow authorizes
commits, create a normal commit and report its SHA; otherwise leave a cleanly
described reviewable working diff. Do not push or create a remote just because
the plan contains a suggested repository layout. Stop with the pilot package,
not a purported completed paper or a background full-study process.
```

### 18. Sources and evidence limits

All links below were checked or located in the September 22, 2026 review. Some full-text pages or downloads were inaccessible. Those limitations are described where relevant. The review verified web evidence, not the integrity, content or successful download of the datasets themselves.

**Conference**

- [C1] [EAI BDCC 2026 official CFP, dates, submission guidelines and author-kit links](https://bdcc-conf.eai-conferences.org/2026/call-for-papers/). The exact linked template ZIP still requires download/inspection. The page includes old sections, so preserve its explicit 2026 details and resolve contradictions.

**Twelve-study comparison**

- [L1] Yu et al. [Published DOI](https://doi.org/10.1016/j.physd.2025.134801), [author preprint](https://arxiv.org/abs/2405.09324), [full text](https://arxiv.org/html/2405.09324v2).
- [L2] Tezzele et al. [Published chapter](https://link.springer.com/chapter/10.1007/978-981-96-9108-1_3), [2024 preprint](https://arxiv.org/abs/2407.20490).
- [L3] Sevak et al. [March 2026 preprint](https://arxiv.org/abs/2603.20838). Do not report it as verified peer-reviewed publication.
- [L4] [Sensors article and DOI](https://doi.org/10.3390/s26134094), [publisher page](https://www.mdpi.com/1424-8220/26/13/4094), [PubMed record](https://pubmed.ncbi.nlm.nih.gov/42451336/). Title, publication details and coarse-to-fine abstract were retrievable; full-text methodology could not be fully inspected.
- [L5] Elfverson et al. [Published DOI](https://doi.org/10.1137/140984294), [preprint/full text](https://arxiv.org/html/1408.6856v1).
- [L6] Elfverson et al. [Published DOI](https://doi.org/10.1137/22M1515240), [preprint/full text](https://arxiv.org/html/2208.05392v2).
- [L7] Peherstorfer et al. [Published DOI](https://doi.org/10.1137/15M1046472), [MIT author manuscript record](https://dspace.mit.edu/entities/publication/f104683d-44c4-40ec-bd06-47502c5c0bfd).
- [L8] Kramer et al. [Author preprint](https://arxiv.org/abs/1905.02679). This review uses the preprint and does not infer a final journal status.
- [L9] Geroliminis and Sun. [Published DOI](https://doi.org/10.1016/j.trb.2010.11.004), [EPFL manuscript](https://infoscience.epfl.ch/bitstreams/911cd085-6083-4c01-b8ba-ca2ae231910c/download).
- [L10] Li et al. [DCRNN paper](https://arxiv.org/abs/1707.01926), [author repository identifying ICLR 2018 publication](https://github.com/liyaguang/DCRNN).
- [L11] Liu et al. [LargeST full paper and dataset documentation](https://arxiv.org/html/2306.08259v2), [author repository identifying NeurIPS 2023 publication](https://github.com/liuxu77/LargeST).
- [L12] Duffield, Lund and Thorup. [Author preprint](https://arxiv.org/abs/cs/0509026), [author's publication list](https://nickduffield.net/papers/papers-by-subject/).

**Data and implementation sources**

- [D1] [Originating DCRNN repository and source data links](https://github.com/liyaguang/DCRNN). Raw measurement licensing requires separate verification.
- [D2] [PEMS-BAY and METR-LA CSV/adjacency mirror, Zenodo record 5724362](https://zenodo.org/records/5724362). This is a derivative deposit by Semin Kwak, not the original DCRNN author release.
- [D3] [LargeST author repository](https://github.com/liuxu77/LargeST), [author-linked dataset](https://www.kaggle.com/datasets/liuxu77/largest/data). Dataset CC BY-NC 4.0 is explicitly stated in the paper; code MIT.
- [D4] [PowerGraph author repository](https://github.com/PowerGraph-Datasets/PowerGraph-Graph), [dataset record](https://figshare.com/articles/dataset/PowerGraph/22820534), [NeurIPS 2024 publication](https://proceedings.neurips.cc/paper_files/paper/2024/hash/c7caf017cbbca1f4b368ffdc7bb8f319-Abstract-Datasets_and_Benchmarks_Track.html).
- [M1] Daganzo. [The Cell Transmission Model: Network Traffic, UC Berkeley author report](https://escholarship.org/uc/item/9pz309w7), [Part I author report](https://escholarship.org/uc/item/0b6612tk). These are source foundations for the controlled mechanism, not additional novelty competitors.
- [H1] [NVIDIA RTX 6000 Ada Generation official specifications](https://www.nvidia.com/en-us/products/workstations/rtx-6000/).

**What remains unknown before execution.** Actual dataset validity/terms at download time, independent episode counts, quality of conditional reconstructions, adequacy of monotone graph dynamics, enclosure tightness, GPU crossover, speedup, empirical novelty beyond the specific reviewed sources, and exact remote presentation procedures. None has been replaced by an expected result.
