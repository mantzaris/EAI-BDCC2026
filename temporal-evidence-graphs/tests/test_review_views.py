"""Review semantics, provenance and renderer/UI parity, not expected pixels."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from temporal_evidence.io import read_json, digest_object
from temporal_evidence.semantic.export import read_export
from temporal_evidence.semantic.review_view import build_view, validate_view
from temporal_evidence.semantic.network_examples import configurations, make_views
from temporal_evidence.semantic.network_render import drawing_objects, render_bytes, node_label
from temporal_evidence.dashboard.network_panel import load_published


@pytest.fixture(scope="module")
def examples():
    return configurations()


def test_immutable_citations_and_version_resolution_are_separate(examples):
    config=examples[0];before,after=make_views(config)
    validate_view(after,read_export(config["export"]))
    old_edges={e["id"]:(e["source"],e["target"],e["type"]) for e in before["edges"]}
    for e in after["edges"]:
        if e["id"] in old_edges:assert old_edges[e["id"]]==(e["source"],e["target"],e["type"])
    assert after["derived_paths"]
    for p in after["derived_paths"]:
        assert not p["directly_stored"] and not p["visible_edge"]
        assert any(e["target"]==p["original_citation_id"] and e["source"]==p["source"] for e in after["edges"])
        assert p["target"]!=p["original_citation_id"]
    prior=[n for n in after["nodes"] if n["version_status"]=="historical version"]
    assert prior and all(n["availability"]=="available" for n in prior)


def test_no_future_record_or_assessment_leaks_into_a_view(examples):
    config=examples[0];before,after=make_views(config)
    before_ids={n["id"] for n in before["nodes"]}
    new=[n for n in after["nodes"] if n["record"]["ingested_at_seconds"]>before["knowledge_time"]]
    assert new and all(n["id"] not in before_ids for n in new)
    assert all(n["assessment"] is None or n["assessment"]["known_at"]<=before["knowledge_time"] for n in before["nodes"])
    with pytest.raises(ValueError,match="absent"):
        build_view(read_export(config["export"]),config["case_id"],before["knowledge_time"],[new[0]["id"]])


def test_conflicting_assessment_ties_remain_ambiguous(examples):
    config=examples[0];g=deepcopy(read_export(config["export"]));rid=config["focus_ids"][0]
    assessment=next(n for n in g["nodes"] if n["semantic_type"]=="assessment" and n["properties"]["id"]==rid)
    tied=deepcopy(assessment);tied["id"]+="-second-trigger";tied["properties"].update(state="supported",trigger_id="other-recorded-trigger")
    g["nodes"].append(tied)
    view=build_view(g,config["case_id"],max(config["times"].values()),[rid])
    n=next(n for n in view["nodes"] if n["id"]==rid)
    assert n["support_state"]=="ambiguous_same_time" and "ambiguous" in node_label(n)
    assert len(n["assessment"]["outcomes"])==2
    assert n["display_state"]=="withdrawn"  # Membership is independent of the tie.


def test_alternative_witness_groups_and_bundles_preserve_every_input(examples):
    before,after=make_views(examples[1]);drawing=drawing_objects(after)
    claims={n["id"]:n for n in after["nodes"] if n["type"]=="claim"}
    root=claims[after["focus_ids"][0]]
    assert root["support_state"]=="supported" and root["display_state"]=="displayed"
    assert any(n["display_state"]=="withdrawn" for n in claims.values())
    roots=[w for w in after["witness_groups"] if w["owner"]==root["id"]]
    assert len(roots)==2 and all(w["between"]=="OR" and w["complete"] for w in roots)
    stored={e["id"] for e in after["edges"]}
    covered=set()
    for edge in drawing["edges"]:
        assert edge["label"]
        assert set(edge["witness_edge_ids"])<=stored
        covered.update(edge["witness_edge_ids"])
        if edge["type"]=="WITNESS_INPUT_BUNDLE":
            assert not edge["directly_stored"]
            w=next(w for w in after["witness_groups"] if w["id"]==edge["witness_group"])
            assert set(edge["witness_edge_ids"])==set(w["stored_edge_ids"])
            assert all(i in drawing["ports"] for i in w["inputs"])
    assert covered==stored


def test_budget_marks_missing_witnesses_and_allows_expansion(examples):
    config=examples[1];small=make_views(config,budget=1)[-1];full=make_views(config,budget=40,expand=True)[-1]
    assert small["budget"]["partial"] and small["budget"]["incomplete_witness_groups"]
    assert all(not w["complete"] and w["omitted_inputs"] for w in small["witness_groups"])
    assert not full["budget"]["partial"] and not full["context"]["omitted_provenance_ids"]
    assert any(n["type"]=="observation" for n in full["nodes"])


def test_asserted_intervals_follow_propositions_not_storage_wrapper(examples):
    config=examples[1];view=make_views(config)[-1]
    byid={n["id"]:n for n in view["nodes"]}
    root=byid[view["focus_ids"][0]]
    tests=config["program_case"]["tests"]
    expected={tuple(t["interval"]) for t in tests.values()}
    assert {tuple(t) for t in root["asserted_intervals"]}==expected
    for n in byid.values():
        if n["type"]!="claim" or n==root:continue
        tokens={t for w in n["proposition_witnesses"] for t in w}
        assert {tuple(t) for t in n["asserted_intervals"]}=={tuple(tests[t]["interval"]) for t in tokens}
    assert len(root["asserted_intervals"])>1  # One wrapper cannot describe both witness windows.


@pytest.mark.parametrize("key",["wesad_revision","structural_alternatives"])
def test_dashboard_and_publication_share_semantics_and_fixed_layout(key):
    view,layout=load_published(key)
    config=read_json(Path("artifacts/analysis/review_views_v1")/key/"config.json")
    figure=Path("artifacts/figures/semantic_analysis_v1")/config["figure"]
    manifest=read_json(figure.with_suffix(".manifest.json"))
    assert digest_object(view)==manifest["view_sha256"]
    assert render_bytes(view,layout,"svg")==figure.with_suffix(".svg").read_bytes()
    assert digest_object(view)==digest_object(make_views(config)[-1])
    before,_=load_published(key,"before")
    assert layout["union_view_hashes"]==[digest_object(before),digest_object(view)]
    assert all(n["id"] in layout["nodes"] or n["id"] in drawing_objects(view)["ports"] for n in view["nodes"])


def test_dashboard_recorded_case_state_focus_budget_and_detail_controls():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file("src/temporal_evidence/dashboard/app.py",default_timeout=30).run()
    assert not app.exception
    app.sidebar.selectbox[0].select("structural_alternatives").run()
    assert not app.exception
    view,_=load_published("structural_alternatives")
    route=view["witness_groups"][0]
    next(s for s in app.selectbox if s.label=="Highlight a witness route").select(route["id"]).run()
    assert not app.exception
    edge=view["edges"][0]
    next(s for s in app.selectbox if s.label=="Inspect a node or edge").select(("edge",edge["id"])).run()
    assert not app.exception and any(edge["meaning"] in t.value for t in app.markdown)
    parent=next(n for n in view["nodes"] if n["type"]=="claim" and n["id"] not in view["focus_ids"])
    app.sidebar.selectbox[1].select(parent["id"]).run()
    assert not app.exception
    app.sidebar.selectbox[1].select(view["focus_ids"][0]).run()
    app.sidebar.radio[1].set_value("Before revision").run()
    assert not app.exception
    app.sidebar.slider[0].set_value(1).run()
    assert not app.exception and any("Partial view" in w.value for w in app.warning)
    app.sidebar.slider[0].set_value(40).run()
    app.sidebar.checkbox[0].check().run()
    assert not app.exception and not app.warning
