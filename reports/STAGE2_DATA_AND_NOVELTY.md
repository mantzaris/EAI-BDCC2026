# Stage 2 data and novelty decisions

Evidence checked September 23, 2026 UTC. Public availability, benchmark software
behavior, measurement provenance, and redistribution rights are separate questions.
No account was registered, no person contacted, and no measurement dataset downloaded
in Stage 2. Existing PEMS-BAY files were reused. Test outcomes remain untouched.

## Data evidence and remaining limits

The [originating DCRNN repository](https://github.com/liyaguang/DCRNN) still links
its HDF releases and requests citation of Li et al., ICLR 2018. Its preprocessing
[window-generation script](https://raw.githubusercontent.com/liyaguang/DCRNN/master/scripts/generate_training_data.py)
loads the released HDF and creates historical/future windows with calendar inputs;
it does not document the complete construction of that HDF from detector records.
The project uses its own 60/20/20 complete-day protocol, not the authors' different
benchmark split or training stack. Raw files are not distributed in Git.

The [DCRNN paper](https://arxiv.org/html/1707.01926v3), §4, describes PeMS speed,
five-minute aggregation, normalization, and road-distance graph construction.
Its stated January–May span conflicts with the six-month released HDF, whose actual
timestamps end June 30. We retain the measured axes and hashes, not the paper's
date typo. The paper excludes missing values in evaluation but does not establish
an upstream imputation history or measurement-quality mask for every released cell.

A useful new check is the originating
[DCRNN supervisor](https://raw.githubusercontent.com/liyaguang/DCRNN/master/model/dcrnn_supervisor.py):
training sets `null_val = 0.` and evaluation explicitly passes zero as the null
value to masked speed metrics. The [metric implementation](https://raw.githubusercontent.com/liyaguang/DCRNN/master/lib/metrics.py)
masks equality to that sentinel. This supports interpreting zeros as unavailable
for benchmark scoring. It does **not** establish the physical meaning of each zero
or identify upstream-filled nonzero values. Stage 2 retains Stage 1's explicit
unknown-indicator lower/upper event bounds, so this evidence does not retrospectively
change labels or eligibility. No future speed is filled into an observed label.

The official [Caltrans PeMS source description](https://dot.ca.gov/programs/traffic-operations/mpr/pems-source)
states that archival PeMS use requires an account and describes changes in speed
computation between PeMS versions. Thus released speed should not be equated with
unprocessed direct detector truth. A Caltrans technical-report search record
also describes `% Observed` as distinct from imputed lane points; the full PDF
exceeded the Stage 2 small-document read cap and was not fully inspected. The HDF
does not contain such quality fields. No claim is made about which imputation
algorithm, PeMS version, lane aggregation, or future information influenced a
particular PEMS-BAY nonzero measurement.

The [Caltrans conditions](https://dot.ca.gov/conditions-of-use), ownership section,
generally describe site information as public domain while retaining exceptions
for copyrighted/third-party material and separate agreements. The
[PeMS-specific conditions link](https://pems.dot.ca.gov/?dnode=Help&content=help_tou)
again returned the unauthenticated site rather than a conclusive dataset agreement.
The Stage 1 Zenodo derivative's CC BY 4.0 declaration remains evidence about that
deposit, not proof of its depositor's rights over all underlying measurements.
DCRNN's MIT software license is likewise not automatically a measurement license.

No actual new prohibition on this bounded local analysis was identified. Nevertheless,
source-account terms and underlying redistribution rights remain unresolved. Keep
raw HDF, graph, coordinates, residual banks, and model input archives private.
Any later direct PeMS acquisition or released-data claim would need the actual
applicable agreement and quality lineage; do not bypass its account requirement.
This stage provides no open-data legal conclusion.

`manifests/stage2/source_evidence.json` records public URLs, UTC retrieval times,
status, bytes and SHA-256. The small acquisition script stores documents under
ignored `data/source_evidence/stage2/`. Successful archived evidence is 761,711
bytes. Including the discarded capped 8,000,001-byte PDF attempt, actual document
reads total **8,761,712 bytes** for that batch. One subsequently followed public
author-PDF link added 4,739,295 bytes, for **13,501,007 bytes** of Stage 2 document
reads overall, still far below the 12 GB project download limit. That PDF could
not be parsed. The manifests explicitly include both failed document attempts;
no measurement download is hidden by them.

## Focused prior-work comparison

The comparison below states surviving differences, not claims of first discovery.
No mathematical result is introduced solely to rescue a submission narrative.

| Closest primary result | What is already established | What this project would still need |
|---|---|---|
| [Elfverson, Hellman and Målqvist, failure probability MLMC](https://arxiv.org/html/1408.6856v1), Assumption 3 and refinement algorithm | Refine samples near a threshold until an error bound determines the indicator; combine with multilevel probability estimation | A useful specific graph-error construction or substantive information result. Label-selective simulation and MC allocation are not new. |
| [Elfverson et al., adaptive multilevel subset simulation](https://arxiv.org/html/2208.05392v2) | Adaptive resolution with error control and required subset relations | Any claim about count events must specify its own finite terminal model and assumptions; no rare-event convergence/cost theorem is established here. |
| [Schaub et al., graph partitions and cluster synchronization](https://arxiv.org/html/1608.04283v2), §II–III | Equitable quotient identities and invariant clustered dynamics, including nonlinear settings | An off-manifold quantitative enclosure can differ in object and norm; that difference alone does not establish novelty. |
| [Coogan and Arcak, HSCC 2015](https://coogan.ece.gatech.edu/papers/pdf/coogan2015hscc.pdf), Theorem 1, Corollary 1 and §3.3 | Rectangular reachable-set enclosures for mixed-monotone discrete-time systems, with tight corner bounds for monotone systems and a traffic example | Our two-lag recurrence can be augmented into a monotone state system. General rectangle propagation and event-safe abstraction are established. Only a useful graph-specific computational tradeoff could add something. |
| [Yu et al., learning coarse graph dynamics](https://arxiv.org/html/2405.09324v2) | Graph memory/closure through Mori–Zwanzig analysis | The matched information test separates representation from learner within a simple family; graph memory itself is not new. |

Coogan–Arcak is an additional primary comparison beyond Stage 1. Their state-space
box partition differs from our node aggregation, and their corner evaluation acts
in the original state dimension. The current work has a k-dimensional center but
still pays for n-dimensional conditioning and forcing; the single tightening also
costs O(N*n*k). These distinctions might support an engineering comparison, but
there is no demonstrated benefit to turn them into a contribution. The tightening
is a straightforward retention of signed residual cancellation and row weights.

Two Stage 1 literature gaps remain. The
[Couthures et al. 2026 publisher record](https://www.sciencedirect.com/science/article/pii/S1751570X26000804)
and [author HAL record](https://hal.science/hal-05636985v1) concern equitable
partitions, local synchronization and quotient stability for nonlinear interactions.
The publisher full text failed. The web reader initially saw a HAL challenge,
but ordinary HTTP retrieval subsequently returned the public metadata and PDF link.
The linked 4.74 MB response started with a PDF header but had no readable trailer;
pdftotext could not read its xref table. The content/parse failure is preserved in
`manifests/stage2/couthures_fulltext.json`. No challenge was solved or restriction
bypassed. Metadata access is resolved; the full assumptions/structural residual
comparison remains open.
The [2026 Sensors crowd coarse-to-fine paper](https://www.mdpi.com/1424-8220/26/13/4094)
has a [PubMed record](https://pubmed.ncbi.nlm.nih.gov/42451336/), but publisher XML
access failed and PMC served a browser challenge. Its abstract-level predictive
refinement comparison is not a completed theorem audit. Neither paper is ruled out.

The original traffic-heterogeneity motivation, conditional Gaussian identities,
Matheron's rule, ordinary MC variance, calibration, and conditional-variance
decompositions remain established background. The local-history comparison is a
finite-model predictive experiment; it does not estimate the Bayes information-loss
term or a causal effect of sensor arrangement.

## Three possible directions and decision

1. **Retained-information result with a competitive predictive model:** A is a
   strong clean predictor, but B and C show no point improvement. Broad uncertainty
   and a single learner/frozen selector limit a negative claim. The planned positive
   retained-identity contribution has not passed its gate.
2. **Competitive stochastic model plus theory/computation:** the one repair is
   informative, but remains 27% worse than A by raw Brier; the numerical acceleration
   fails even after a substantial algebraic tightening. Novelty is unresolved.
3. **Bounded negative study:** there is concrete evidence of a confounded initial
   comparison, state-dependent residual bias, and radius inflation from independent
   maxima. These are useful reproducible diagnostics. One small, already-exposed
   validation panel does not yet establish a broad negative law or a submission-ready
   study; ordinary implementation checks are not theoretical novelty.

**Recommendation: stop the current submission-oriented method campaign.** Retain
the reusable software and negative evidence. A later reframe would need an
independent substantive question, quality/terms resolution, and an appropriate
validation design, not more samples or another speculative repair. This evidence
does not justify scheduling Stage 3 now.
