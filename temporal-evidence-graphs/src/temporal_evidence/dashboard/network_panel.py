"""Recorded views in the existing evidence-review application; no benchmark writes."""
import json
from pathlib import Path

from temporal_evidence.io import read_json, digest_object
from temporal_evidence.semantic.network_examples import make_views
from temporal_evidence.semantic.network_render import union_layout, render_bytes, node_label, edge_label

ROOT=Path("artifacts/analysis/review_views_v1")
CLASSIC=Path("artifacts/analysis/classic_network_v1")


def load_published(key, state="after"):
    """The publication renderer and UI load this exact serialized view object."""
    view=read_json(ROOT/key/(state+".json"));layout=read_json(ROOT/key/"layout.json")
    return view,layout


def load_classic(state="after"):
    return read_json(CLASSIC/(state+".json")),read_json(CLASSIC/"layout.json")


def classic_views(config, focus, expand, budget):
    from temporal_evidence.semantic.classic_example import focused_provenance
    from temporal_evidence.semantic.classic_analysis import annotate_view
    from temporal_evidence.semantic.export import read_export
    graph=read_export(config["export"]);analysis=read_json(CLASSIC/"analysis.json")
    return [annotate_view(v if expand else focused_provenance(v),graph,analysis)
            for v in make_views(config,focus_ids=[focus],expand=True,budget=budget)]


def show_recorded_views():
    import streamlit as st
    manifest=read_json(ROOT/"manifest.json")
    entries={e["key"]:e for e in manifest["examples"]}
    selected_key=st.sidebar.selectbox("Recorded case",list(entries),format_func=lambda k:entries[k]["title"])
    entry=entries[selected_key]
    config=read_json(entry["config_path"])
    baseline,_=load_published(entry["key"],"before")
    focus_options=[n["id"] for n in baseline["nodes"] if n["type"]=="claim"]
    names={n["id"]:node_label(n).split("\n")[0] for n in baseline["nodes"]}
    focus=st.sidebar.selectbox("Focus claim",focus_options,index=focus_options.index(config["focus_ids"][0]),format_func=lambda x:names[x])
    state=st.sidebar.radio("Recorded state",["Before revision","After maintenance"],index=1)
    style=st.sidebar.selectbox("Layout",["Structured","Classic network"] if config.get("program_case") else ["Structured"])
    classic=style=="Classic network"
    expand=st.sidebar.checkbox("Expand observation provenance",value=False if classic else config["expand_provenance"],key="provenance-"+style)
    budget=st.sidebar.slider("Maximum record nodes",1,40,20 if classic else config["budget"],key="budget-"+style)
    if classic:
        from temporal_evidence.semantic.classic_render import render_bytes as renderer,spring_layout
        if focus==config["focus_ids"][0] and not expand and budget==20:
            view,layout=load_classic("before" if state=="Before revision" else "after")
        else:
            scenes=st.cache_data(show_spinner=False)(classic_views)(config,focus,expand,budget)
            layout=st.cache_data(show_spinner=False)(spring_layout)(scenes)
            view=next(v for v in scenes if v["recorded_state"]==state)
    elif focus==config["focus_ids"][0] and expand==config["expand_provenance"] and budget==config["budget"]:
        view,layout=load_published(entry["key"],"before" if state=="Before revision" else "after")
    else:
        views=make_views(config,focus_ids=[focus],expand=expand,budget=budget)
        layout=union_layout(views,config["rankdir"])
        view=next(v for v in views if v["recorded_state"]==state)
    if not classic:renderer=render_bytes
    st.subheader(entry["title"])
    st.caption(f"Knowledge time {view['knowledge_time']:g} s · {state.lower()} · {len(view['nodes'])} record nodes. Event intervals appear in source details.")
    if view["budget"]["partial"]:
        st.warning(f"Partial view: {len(view['budget']['omitted_ids'])} required records omitted by the node budget. Increase the budget to inspect complete witnesses; this drawing does not show every route.")
    if view["context"]["omitted_provenance_ids"]:
        st.caption(f"{len(view['context']['omitted_provenance_ids'])} observation inputs are available through ‘Expand observation provenance’. Identity hubs, display containers and assessment nodes stay in details.")
    byid={n["id"]:n for n in view["nodes"]}
    labels={n["id"]:node_label(n).split("\n")[0] for n in view["nodes"]}
    groups=view["witness_groups"]
    group_ids={w["id"]:w for w in groups}
    def group_label(key):
        if key is None:return "None"
        w=group_ids[key]
        return f"{labels[w['owner']]} · W{w['index']} · AND inputs ({'complete' if w['complete'] else 'partial'})"
    route_key=st.selectbox("Highlight a witness route",[None]+list(group_ids),format_func=group_label)
    route=group_ids.get(route_key)
    options=[("node",n["id"]) for n in view["nodes"]]+[("edge",e["id"]) for e in view["edges"]]
    edges={e["id"]:e for e in view["edges"]}
    def option_label(item):
        kind,key=item
        if kind=="node":return "Node: "+labels[key]
        e=edges[key];return f"Edge: {labels[e['source']]} → {labels[e['target']]} · {e['type']}"
    selected=st.selectbox("Inspect a node or edge",options,format_func=option_label)
    highlight=route["id"] if route else selected[1]
    network,details=st.columns([2,1])
    with network:
        # Both modes reuse the paper's union coordinates/routes. The browser
        # scales the SVG without recalculating layout or evidence semantics.
        st.image(renderer(view,layout,"svg",highlight).decode(),width="stretch")
        if classic:
            st.caption("Every ellipse is a stored record. AND A/B jointly require their four inputs; OR A/B are alternative parent witnesses. ‘From’ means DERIVED_FROM; ‘revises’ means SUPERSEDES. Annotations describe the recorded before/after contrast.")
        else:
            st.caption("Green: claim. Blue: feature. Folded corner: observation. Orange outline: revised or adversely assessed. Dashed feature outline: historical version. Words state support and display status independently.")
            st.caption("Arrows point from dependents to inputs. Dashed ‘needs all’ arrows bundle the stored citations in an AND enclosure; witness alternatives are scoped to their owning claim.")
    with details:
        st.markdown("**Selected object**")
        if selected[0]=="node":
            n=byid[selected[1]];r=n["record"]
            st.write(r["metadata"].get("claim",{}).get("sentence") or r["metadata"].get("semantic_program",{}).get("sentence") or r["metadata"].get("sentence") or r["quantity"] or "Recorded observation")
            st.write({"Version":r["version"],"Value":r["value"],"Unit":r["unit"],"Asserted intervals":n["asserted_intervals"],
                      "Storage interval":[r["event_start_seconds"],r["event_end_seconds"]],
                      "Ingested":r["ingested_at_seconds"],"Availability":n["availability"],"Support":n["support_state"],"Display":n["display_state"]})
            st.json({"record_id":n["id"],"database_id":n["database_element_id"],"source_ids":r["source_ids"],"assessment_provenance":n["assessment"],"metadata":r["metadata"]},expanded=False)
            if classic:st.json({"ontology_class":n["ontology_class"],"equation_membership":n["equations"]},expanded=False)
        else:
            e=edges[selected[1]];st.write(e["meaning"]);st.json(e)
        if route:st.json(route,expanded=False)
    with st.expander("Scope, original citations and omitted context"):
        st.json({"scope":view["scope"],"case_id":view["case_id"],"view_hash":digest_object(view),"selection":config["selection"],
                 "derived_resolution_paths":view["derived_paths"],"omitted_context":view["context"],"budget":view["budget"]},expanded=False)
        if classic:st.json(view["equation_annotations"],expanded=False)
    st.download_button("Download this semantic view",json.dumps(view,indent=2),file_name=entry["key"]+".json",mime="application/json")
    st.download_button("Download network SVG",renderer(view,layout,"svg"),file_name=entry["key"]+".svg",mime="image/svg+xml")
    st.info("Recorded examples are read-only. Select Saved explanation or Dependency demonstration to make changes in the isolated review workspace.")
