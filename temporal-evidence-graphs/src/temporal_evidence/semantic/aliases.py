"""Explicit normalization of names already defined in a case's numerical tests.

This reporting/replication rule changes no candidate, witness token or parent edge.
The original extension admission table and scores remain frozen.
"""
def canonical_case(case):
    return {**case,"propositions":{**case["propositions"],**{token:[[token]] for token in case["tests"]}}}
