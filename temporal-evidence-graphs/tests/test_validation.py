from dataclasses import replace
from temporal_evidence.generation.contract import Answer, Claim
from temporal_evidence.schema import Query
from temporal_evidence.synthetic.fixtures import record
from temporal_evidence.validation.checker import validate, safe_display
from temporal_evidence.generation.prompts import messages


def fixture(value=2, sentence="EDA is 2 synthetic_unit."):
    claim = Claim(claim_id="c", claim_type="numeric_observation", subject_id="V101", quantity="eda_median",
                  event_start_seconds=0, event_end_seconds=10, operator="approximately_equal", value=value,
                  unit="synthetic_unit", evidence_ids=["a"], depends_on_claim_ids=[], sentence=sentence)
    answer = Answer(claims=[claim], answer_status="answered", explanation=sentence, unresolved_evidence_ids=[])
    return answer, {"a": record("a", 2)}, Query("synthetic", "V101", "symbolic", 0, 10, 10)


def test_correct_id_wrong_number():
    answer, records, query = fixture(20, "EDA is 20 synthetic_unit.")
    checks, _ = validate(answer, records, query)
    assert "wrong_numeric_value_or_interval" in checks[0].reasons
    assert safe_display(answer, checks)["answer_status"] == "insufficient_evidence"


def test_valid_structure_contradicted_by_sentence():
    answer, records, query = fixture(2, "EDA is 20 synthetic_unit.")
    checks, _ = validate(answer, records, query)
    assert "sentence_numeric_discrepancy" in checks[0].reasons


def test_extra_paragraph_interpretation_detected():
    answer, records, query = fixture()
    answer.explanation += " This proves stress."
    checks, paragraph = validate(answer, records, query)
    assert checks[0].state == "supported"
    assert paragraph == ["explanation_not_equal_to_claim_sentences"]
    assert "stress" not in safe_display(answer, checks)["explanation"]


def test_wrong_subject_and_window():
    answer, records, query = fixture()
    answer.claims[0].subject_id = "another"
    answer.claims[0].event_start_seconds = 1
    checks, _ = validate(answer, records, query)
    assert {"wrong_subject", "wrong_time"} <= set(checks[0].reasons)


def test_future_reference_not_visible():
    answer, records, query = fixture()
    records["a"] = replace(records["a"], ingested_at_seconds=11)
    checks, _ = validate(answer, records, query)
    assert "missing_reference" in checks[0].reasons


def test_prompt_allowlist_excludes_evaluator_metadata():
    _, records, query = fixture()
    evidence = replace(records["a"], metadata={"fault_label":"secret", "protocol_label":2, "gold_value":100})
    serialized = str(messages(query, [evidence]))
    assert all(word not in serialized for word in ("secret", "protocol_label", "gold_value"))


def test_dependency_cycle_or_forward_reference_fails():
    answer, records, query = fixture()
    answer.claims[0].depends_on_claim_ids = ["c"]
    checks, _ = validate(answer, records, query)
    assert "unsupported_or_cyclic_dependency" in checks[0].reasons
