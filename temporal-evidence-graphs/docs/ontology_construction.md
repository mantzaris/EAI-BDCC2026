# Implemented ontology and construction

This is a fixed property-graph vocabulary. LLMs instantiate propositions inside it.
The domains below describe adapter behavior; they are not claims of OWL reasoning.

| Type / label | Meaning | Creation rule | Provenance | Status |
|---|---|---|---|---|
| subject / Subject | Dataset participant identity | with_entities: dataset/subject | record scope | administrative |
| sensor / Sensor | Session channel identity | with_entities: observation metadata.channel | recording channel | administrative |
| observation / Observation | Hashed recording window and sampling coordinates | adapter/extractor | recording hash and sample range | deterministic |
| feature / FeatureVersion | Numerical feature or explicit availability watch | extractor or watch subscription | source_ids, extractor and units | deterministic |
| claim / ClaimVersion | Generated bounded proposition and declared inputs | displayed_records; accepted flag for checked methods | raw candidate, query, claim fields | proposed/checked |
| explanation / ExplanationVersion | Immutable displayed text and member claims | generation or maintenance recomposition | case_id, previous version, withdrawn IDs | administrative |
| review / ReviewEvent | Recorded reviewer action | isolated dashboard action | action metadata and source_ids | administrative |
| assessment / SupportAssessment | Support outcome at a knowledge time | GraphStore.assess_many | record ID, known_at, trigger_id, state, value | validated outcome |
| placeholder / Record (no payload) | Unresolved referenced ID, if present | GraphStore MERGE of source endpoint | referencing record | administrative/unresolved |

| Relation | Domain → range | Meaning | Creation rule/provenance | Status |
|---|---|---|---|---|
| DEPENDS_ON | Record → Record/reference | Dependent to declared input; does not certify necessity | record.source_ids | deterministic or model proposal |
| DERIVED_FROM | feature → Record/reference | Feature extraction provenance | feature.source_ids | deterministic |
| SUPPORTS | Record → claim | Accepted-at-insertion citation/prerequisite mirror | accepted claim.source_ids | checked at insertion; not perpetual support |
| FOR_SUBJECT | Record → subject | Scope membership, not reasoning | with_entities and record_relations | administrative |
| OBSERVED_BY | observation → sensor | Recording channel association | observation.metadata.channel | deterministic |
| SUPERSEDES | Record → Record/reference | New immutable version to previous ID | supersedes_id | administrative versioning |
| CONTAINS | explanation → Record/reference | Display membership | explanation.source_ids | administrative |
| REVIEWED_BY_EVENT | Record → review | Item acted on by review event | review.source_ids | administrative |
| CONTRADICTS | Record → Record/reference | Revision triggered a contradicted assessment | assess_many(state=contradicted) | validated outcome; time in assessment |
| ASSESSED_AS | Record → assessment | Record has a time-indexed support assessment | GraphStore.assess_many | validated outcome |

`SUPPORTS` mirrors accepted claim sources at insertion. Later truth must be read
from time-indexed assessments or independently re-evaluated, never inferred from this edge.
`CONTRADICTS` has no edge timestamp; its associated assessment supplies trigger and time.
Neo4j assessment identity is (scope, record ID, knowledge time, trigger ID), not record ID alone.
SQLite stores equivalent assessment rows without separate ASSESSED_AS objects.
Raw rejected candidates remain in request artifacts; they are not all Neo4j ClaimVersions.
The claim wrapper interval is the query interval. The proposition's asserted interval is
in metadata.claim; the semantic analysis uses that field.
