# Related work and scope

Read before making contribution claims. These comparisons describe the evaluated
tasks, not every capability of the corresponding software. B2 is a custom ablation;
it is not a GraphRAG or Graphiti reproduction.

| Work | Task and representation | Temporal/provenance behavior | Evaluation relevant to this study | Boundary of the comparison |
|---|---|---|---|---|
| [Doyle, 1979](https://doi.org/10.1016/0004-3702(79)90008-0) | Maintaining reasons for program beliefs | Dependencies support belief revision and explanations | Foundational maintenance machinery | Dependency-directed revision is established; this work does not invent it |
| [Gupta et al., 1993](https://sigmodrecord.org/1993/06/03/maintaining-views-incrementally/) | Relational/deductive view maintenance | Updates account for alternative derivations and recursive views | Database maintenance algorithms | A capable relational implementation is a necessary control |
| [Green et al., 2007](https://www.cs.ucdavis.edu/~green/papers/pods07.pdf) | Provenance of relational queries | Algebraic representations combine contributing and alternative derivations | Relational algebra and Datalog semantics | Our finite AND/OR predicates do not replace general provenance semantics |
| [Edge et al., GraphRAG](https://arxiv.org/html/2404.16130v2) | Global summarization over text corpora | Entity/community graphs organize retrieved summaries | Two approximately million-token corpora; answer comprehensiveness/diversity | Our endpoint is maintenance of already displayed monitoring statements |
| [Rasmussen et al., Zep](https://arxiv.org/html/2501.13956v1) | Conversational agent memory | Bitemporal facts, source episodes, contradiction-based edge invalidation | Deep Memory Retrieval and LongMemEval | Dynamic graphs and fact invalidation are prior work; do not claim otherwise |
| [Ahmed et al., HEG-TKG](https://arxiv.org/html/2604.17114v2) | Rare-disease clinical evidence synthesis | Literature provenance and disease-stage temporal anchors | Citation audits, clinician ratings and injected-evidence counterfactuals | This is a 2026 preprint. Our controlled sensor replay is not clinical reasoning or a clinician study |
| [Turpin et al., 2023](https://arxiv.org/html/2305.04388v2) | Faithfulness of chain-of-thought explanations | Tests whether explanations disclose influential input factors | Input interventions reveal unmentioned influences | External evidence dependencies do not establish faithful internal neural reasoning |
| [Hu et al., 2026](https://aclanthology.org/2026.findings-acl.1385/) | Hallucination detection using internal attribution | Semantic dependency graphs derived from model attribution | RAGTruth and Dolly-15k | Our graph records external evidence and generated assertions, not neuron/token attribution |

The prospective contribution is an auditable correction-maintenance benchmark and
implementation: exact symbolic dependencies, waveform replay from one synthetic
source and two real sources, five matched conditions, paired error/usefulness
analysis, and a separate graph-versus-relational systems comparison. It is not a
claim of the first temporal graph, first evidence-linked explanation, or a new
general truth-maintenance algorithm. Interface functionality is a demonstration;
human performance is not evaluated. Physiological estimation accuracy remains
separate from faithfulness to the ingested recording features.
