"""Descriptive ontology of the implemented adapters, not ontology learning."""
from pathlib import Path
from temporal_evidence.io import write_json

TYPES = ("subject", "sensor", "observation", "feature", "claim", "explanation", "review", "assessment", "placeholder")
RECORDS = TYPES[:7]
NODE_RULES = [
    ("subject", "Subject", "Dataset participant identity", "with_entities: dataset/subject", "record scope", "administrative"),
    ("sensor", "Sensor", "Session channel identity", "with_entities: observation metadata.channel", "recording channel", "administrative"),
    ("observation", "Observation", "Hashed recording window and sampling coordinates", "adapter/extractor", "recording hash and sample range", "deterministic"),
    ("feature", "FeatureVersion", "Numerical feature or explicit availability watch", "extractor or watch subscription", "source_ids, extractor and units", "deterministic"),
    ("claim", "ClaimVersion", "Generated bounded proposition and declared inputs", "displayed_records; accepted flag for checked methods", "raw candidate, query, claim fields", "proposed/checked"),
    ("explanation", "ExplanationVersion", "Immutable displayed text and member claims", "generation or maintenance recomposition", "case_id, previous version, withdrawn IDs", "administrative"),
    ("review", "ReviewEvent", "Recorded reviewer action", "isolated dashboard action", "action metadata and source_ids", "administrative"),
    ("assessment", "SupportAssessment", "Support outcome at a knowledge time", "GraphStore.assess_many", "record ID, known_at, trigger_id, state, value", "validated outcome"),
    ("placeholder", "Record (no payload)", "Unresolved referenced ID, if present", "GraphStore MERGE of source endpoint", "referencing record", "administrative/unresolved"),
]
# Broad adapter domains are deliberate: the frozen adapter does not enforce a
# narrower ontology. Additional semantic restrictions are checked separately.
RELATIONS = {
 "DEPENDS_ON": (RECORDS, RECORDS+("placeholder",), "Dependent to declared input; does not certify necessity", "record.source_ids", "deterministic or model proposal"),
 "DERIVED_FROM": (("feature",), RECORDS+("placeholder",), "Feature extraction provenance", "feature.source_ids", "deterministic"),
 "SUPPORTS": (RECORDS+("placeholder",), ("claim",), "Accepted-at-insertion citation/prerequisite mirror", "accepted claim.source_ids", "checked at insertion; not perpetual support"),
 "FOR_SUBJECT": (RECORDS[1:], ("subject",), "Scope membership, not reasoning", "with_entities and record_relations", "administrative"),
 "OBSERVED_BY": (("observation",), ("sensor",), "Recording channel association", "observation.metadata.channel", "deterministic"),
 "SUPERSEDES": (RECORDS, RECORDS+("placeholder",), "New immutable version to previous ID", "supersedes_id", "administrative versioning"),
 "CONTAINS": (("explanation",), RECORDS+("placeholder",), "Display membership", "explanation.source_ids", "administrative"),
 "REVIEWED_BY_EVENT": (RECORDS+("placeholder",), ("review",), "Item acted on by review event", "review.source_ids", "administrative"),
 "CONTRADICTS": (RECORDS, RECORDS, "Revision triggered a contradicted assessment", "assess_many(state=contradicted)", "validated outcome; time in assessment"),
 "ASSESSED_AS": (RECORDS, ("assessment",), "Record has a time-indexed support assessment", "GraphStore.assess_many", "validated outcome"),
}


def kind(node):
    p = node["properties"]
    return "assessment" if "SupportAssessment" in node["labels"] else p.get("kind", "placeholder")


def node_origin(node):
    k = kind(node)
    if k == "claim": return "model_proposal_persisted"
    if k == "assessment": return "support_evaluation"
    if k in {"subject", "sensor", "explanation", "review", "placeholder"}: return "administrative"
    return "recording_or_availability_construction"


def edge_origin(edge, nodes):
    typ = edge["type"]; source = kind(nodes[edge["source"]]); target = kind(nodes[edge["target"]])
    if typ in {"ASSESSED_AS", "CONTRADICTS"}: return "support_evaluation"
    if typ == "SUPPORTS": return "accepted_citation_mirror"
    if typ == "DEPENDS_ON" and source == "claim":
        return "declared_parent" if target == "claim" else "model_evidence_citation"
    if typ in {"DEPENDS_ON", "DERIVED_FROM", "OBSERVED_BY"} and source in {"feature", "observation"}:
        return "deterministic_provenance"
    return "administrative"


def validate_export(graph):
    nodes = {n["id"]: n for n in graph["nodes"]}
    errors = []
    for e in graph["edges"]:
        if e["source"] not in nodes or e["target"] not in nodes:
            errors.append([e["id"], "missing_endpoint"]); continue
        if e["type"] not in RELATIONS:
            errors.append([e["id"], "unknown_relation"]); continue
        dom, ran, *_ = RELATIONS[e["type"]]
        if kind(nodes[e["source"]]) not in dom or kind(nodes[e["target"]]) not in ran:
            errors.append([e["id"], "domain_range"])
    return errors


def document():
    output = Path("artifacts/analysis/semantic_analysis_v1"); output.mkdir(parents=True, exist_ok=True)
    write_json(output/"ontology.json", {"types": NODE_RULES, "relations": RELATIONS,
        "constraint_scope": "descriptive adapter domains, immutable IDs and acyclic source_ids; no OWL/SHACL engine"})
    lines = ["# Implemented ontology and construction", "",
        "This is a fixed property-graph vocabulary. LLMs instantiate propositions inside it.",
        "The domains below describe adapter behavior; they are not claims of OWL reasoning.", "",
        "| Type / label | Meaning | Creation rule | Provenance | Status |",
        "|---|---|---|---|---|"]
    for k, label, meaning, rule, provenance, status in NODE_RULES:
        lines.append(f"| {k} / {label} | {meaning} | {rule} | {provenance} | {status} |")
    lines += ["", "| Relation | Domain → range | Meaning | Creation rule/provenance | Status |", "|---|---|---|---|---|"]
    for relation, (domain, ran, meaning, rule, status) in RELATIONS.items():
        d = "Record" if len(domain)>4 else ", ".join(domain)
        r = "Record/reference" if len(ran)>4 else ", ".join(ran)
        lines.append(f"| {relation} | {d} → {r} | {meaning} | {rule} | {status} |")
    lines += ["", "`SUPPORTS` mirrors accepted claim sources at insertion. Later truth must be read",
        "from time-indexed assessments or independently re-evaluated, never inferred from this edge.",
        "`CONTRADICTS` has no edge timestamp; its associated assessment supplies trigger and time.",
        "Neo4j assessment identity is (scope, record ID, knowledge time, trigger ID), not record ID alone.",
        "SQLite stores equivalent assessment rows without separate ASSESSED_AS objects.",
        "Raw rejected candidates remain in request artifacts; they are not all Neo4j ClaimVersions.",
        "The claim wrapper interval is the query interval. The proposition's asserted interval is",
        "in metadata.claim; the semantic analysis uses that field.", ""]
    Path("docs/ontology_construction.md").write_text("\n".join(lines))


if __name__ == "__main__": document()
