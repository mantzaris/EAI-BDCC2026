from temporal_evidence.io import append_journal,read_journal,journal_paths


def test_segmented_request_journal_keeps_order_and_resume_history(tmp_path):
    path=tmp_path/"requests.jsonl"
    entries=[{"case_id":"case-a","event":"started"},{"case_id":"case-a","event":"finished"},
             {"case_id":"case-b","event":"started"}]
    for entry in entries:
        append_journal(path,entry,segment_bytes=1)
    assert len(journal_paths(path))==3
    assert read_journal(path)==entries
    append_journal(path,{"case_id":"case-b","event":"finished"},segment_bytes=1)
    assert read_journal(path)[-1]["case_id"]=="case-b"
