from pathlib import Path
from temporal_evidence.study import make_cases,episode_rows,query_evidence
from temporal_evidence.io import read_json,digest_object


def test_exact_minimum_counts_and_subject_separation():
    cases=make_cases("test")
    assert len(cases)==3600 and len({c["case_id"] for c in cases})==3600
    assert sum(c["method"]!="B0" for c in cases)==2880
    development={(row["dataset"],row["subject"]) for row in episode_rows("development")}
    test={(row["dataset"],row["subject"]) for row in episode_rows("test")}
    assert not development & test
    for source in ("synthetic","wesad","ppg_dalia"):
        assert sum(c["dataset"]==source for c in cases)==1200
        assert sum(row[0]==source for row in test)==10


def test_matched_evidence_and_delayed_packets_development_only():
    cases=[case for case in make_cases("development") if case["variant"]=="delayed"][:15]
    fingerprints={}
    for case in cases:
        episode=read_json(case["episode_path"])
        query,evidence,events=query_evidence(case,episode)
        assert all(r.ingested_at_seconds<=query.knowledge_time for r in evidence)
        target_eda=[r for r in evidence if r.quantity=="eda_median" and r.event_end_seconds==query.event_end_seconds]
        assert bool(target_eda)==(case["checkpoint"]==2)
        fingerprint=digest_object([r.to_dict() for r in evidence])
        fingerprints.setdefault(case["checkpoint"],set()).add(fingerprint)
    assert all(len(values)==1 for values in fingerprints.values())


def test_no_source_overlap_between_episode_contexts():
    by_subject={}
    for split in ("development","test"):
        for row in episode_rows(split):
            by_subject.setdefault((row["dataset"],row["subject"]),[]).append((row["start"]-120,row["end"]))
    for intervals in by_subject.values():
        first,second=sorted(intervals)
        assert first[1]<=second[0]
