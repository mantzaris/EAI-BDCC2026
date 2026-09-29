import numpy as np
from temporal_evidence.analysis.summarize import paired_interval,subject_values


def test_paired_bootstrap_resamples_subjects_not_query_rows():
    rows=[]
    for subject,difference in [("a",.2),("b",.4)]:
        for method,value in [("M1",difference),("B1",0)]:
            rows += [{"subject":subject,"episode_id":f"{subject}-{index//12}","method":method,"case_error":value} for index in range(24)]
    report=paired_interval(rows,"M1","B1","case_error")
    assert report["subjects"]==2
    assert np.isclose(report["difference"],.3)
    assert np.allclose(report["ci95"],[.2,.4])


def test_undefined_conditional_correction_is_not_perfect_score():
    rows=[{"subject":"a","episode_id":"a-0","method":"M1","corrected":0,"correction_required":0}]
    assert subject_values(rows,"correction_completeness")=={"a":None}
    rows.append({**rows[0],"method":"B2"})
    report=paired_interval(rows,"M1","B2","correction_completeness")
    assert report["difference"] is None and report["subjects"]==0


def test_paired_ratios_give_equal_weight_to_episodes_with_unequal_denominators():
    rows = [{"subject":"a","episode_id":episode,"method":method,"corrected":n,"correction_required":d}
            for episode,method,n,d in [("a-0","M1",9,10),("a-0","B2",1,2),
                                       ("a-1","M1",1,1),("a-1","B2",9,10)]]
    report = paired_interval(rows,"M1","B2","correction_completeness")
    assert np.isclose(report["difference"],.25)
    assert report["eligible_episodes"] == 2 and report["subjects"] == 1


def test_conditional_pairing_never_compares_different_episodes():
    rows = [{"subject":"a","episode_id":episode,"method":method,"corrected":n,"correction_required":d}
            for episode,method,n,d in [("a-0","M1",1,1),("a-0","B2",0,0),
                                       ("a-1","M1",0,0),("a-1","B2",0,1)]]
    report = paired_interval(rows,"M1","B2","correction_completeness")
    assert report["difference"] is None
    assert report["eligible_episodes"] == 0 and report["excluded_episodes"] == 2
    assert report["subjects"] == 0 and report["excluded_subjects"] == 1
