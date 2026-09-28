"""Exact symbolic cases; these assertions are independent of generated claims."""
from dataclasses import replace
from temporal_evidence.schema import Record


def record(identifier, value=None, sources=(), kind="feature", time=10, **kwargs):
    return Record(record_id=identifier, logical_id=identifier, record_type=kind,
                  dataset_id="synthetic", subject_id="V101", session_id="symbolic",
                  event_start_seconds=0, event_end_seconds=10, ingested_at_seconds=time,
                  quantity="eda_median", unit="synthetic_unit", value=value,
                  source_ids=tuple(sources), **kwargs)


def correction_fixture():
    records = [
        record("a", 2), record("b", 1), record("alternative", 2),
        record("difference", 1, ("a", "b"), operator="difference"),
        record("direct_claim", 2, ("a",), kind="claim"),
        record("downstream_claim", 1, ("difference",), kind="claim"),
        record("or_claim", 2, ("a", "alternative"), kind="claim", support_mode="OR"),
        record("unaffected", 1, ("b",), kind="claim"),
        record("explanation", sources=("direct_claim", "downstream_claim", "or_claim", "unaffected"), kind="explanation"),
    ]
    revision = replace(records[0], record_id="a/v2", version=2, ingested_at_seconds=20,
                       supersedes_id="a", value=4)
    return records, revision
