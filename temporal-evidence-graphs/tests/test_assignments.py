from collections import Counter,defaultdict
from temporal_evidence.data.prepare import episode_assignments


def test_balanced_seeded_question_and_fault_schedules_are_not_coupled():
    entries=[{"subject":f"V{seed}","split":"test"} for seed in range(1001,1011)]
    assignments=episode_assignments("synthetic",entries)
    assert assignments==episode_assignments("synthetic",entries)
    assert set(Counter(a["family"] for a in assignments.values()).values())=={5}
    assert Counter(a["fault_family"] for a in assignments.values())=={"missingness":10,"corruption":10}
    families=defaultdict(set)
    for item in assignments.values():families[item["family"]].add(item["fault_family"])
    assert all(len(values)==2 for values in families.values())
