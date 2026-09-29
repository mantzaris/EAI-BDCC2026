import numpy as np
from temporal_evidence.analysis.summarize import paired_interval,subject_values


def test_paired_bootstrap_resamples_subjects_not_query_rows():
    rows=[]
    for subject,difference in [("a",.2),("b",.4)]:
        for method,value in [("M1",difference),("B1",0)]:
            rows += [{"subject":subject,"method":method,"case_error":value} for _ in range(24)]
    report=paired_interval(rows,"M1","B1","case_error")
    assert report["subjects"]==2
    assert np.isclose(report["difference"],.3)
    assert np.allclose(report["ci95"],[.2,.4])


def test_undefined_conditional_correction_is_not_perfect_score():
    rows=[{"subject":"a","method":"M1","corrected":0,"correction_required":0}]
    assert subject_values(rows,"correction_completeness")=={"a":None}
    rows.append({**rows[0],"method":"B2"})
    report=paired_interval(rows,"M1","B2","correction_completeness")
    assert report["difference"] is None and report["subjects"]==0
