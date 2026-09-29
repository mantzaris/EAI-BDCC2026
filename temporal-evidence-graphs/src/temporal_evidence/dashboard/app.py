"""Run with the dashboard CLI or streamlit run from the project directory."""
from pathlib import Path
import json
import os
import pandas as pd
import streamlit as st
from temporal_evidence.dashboard.review import ReviewWorkspace

st.set_page_config(page_title="Evidence review", page_icon="◈", layout="wide")
st.title("Evidence review")
st.caption("Trace a statement to its evidence, review a change, and inspect the revised explanation.")

with st.sidebar:
    st.subheader("Review workspace")
    mode = st.radio("Example", ["Dependency demonstration", "Saved explanation"])
    case_path = None
    identifier = "symbolic"
    if mode == "Saved explanation":
        directories = sorted(p for p in Path("artifacts/runs").glob("*") if (p/"cases").is_dir())
        if not directories:
            st.info("No saved cases are available in this checkout yet.")
            st.stop()
        preferred = next((i for i,p in enumerate(directories) if p.name == "minimum_v1"), len(directories)-1)
        run = st.selectbox("Run", directories, format_func=lambda p: p.name, index=preferred)
        cases = sorted(p for p in (run/"cases").glob("*.json") if p.stem.endswith(("-M1", "-B3")))
        source = st.selectbox("Source", ["synthetic", "wesad", "ppg_dalia"])
        cases = [p for p in cases if p.stem.startswith(source+"-")]
        if not cases:
            st.info("This run has no saved explanations for the selected source.")
            st.stop()
        case_path = st.selectbox("Explanation", cases, format_func=lambda p: p.stem)
        identifier = f"{run.name}/{case_path.stem}"
    st.caption("Changes are saved in this review workspace. Benchmark outputs remain immutable.")

workspace = ReviewWorkspace(identifier, path=os.environ.get("TEG_REVIEW_DB", ".local/review.sqlite"),
                            backend=os.environ.get("TEG_REVIEW_BACKEND", "sqlite"),
                            uri=os.environ.get("TEG_REVIEW_NEO4J", "bolt://127.0.0.1:7687"))
try:
    if case_path:
        workspace.seed_case(case_path)
    else:
        workspace.seed_symbolic()
        st.info("Constructed example: correcting target a from 2 to 4 withdraws two old statements. Independent support keeps the OR statement valid.")

    queue = workspace.queue()
    states = workspace.states()
    history = workspace.history()
    columns = st.columns(3)
    columns[0].metric("Statements needing attention", sum(state != "supported" for state in states.values()))
    columns[1].metric("Supported statements", sum(state == "supported" for state in states.values()))
    columns[2].metric("Explanation versions", len(history))

    review_tab, history_tab, diagnostics_tab = st.tabs(["Review", "Revision history", "Diagnostics"])
    with review_tab:
        st.subheader("Issue queue")
        st.caption("Explicit evidence problems first, then the number of dependent statements.")
        if queue:
            st.dataframe(pd.DataFrame(queue).rename(columns={"statement": "Statement or quantity", "state": "Status",
                         "affected_claims": "Dependent statements", "record_id": "Version ID"})
                         [["Statement or quantity", "Status", "Dependent statements", "Version ID"]],
                         hide_index=True, width="stretch")
            options = [row["record_id"] for row in queue]
            record_id = st.selectbox("Inspect a statement or measurement", options)
            record = workspace.records()[record_id]
            left, right = st.columns([1.3, 1])
            with left:
                st.subheader("Local evidence graph")
                st.graphviz_chart(workspace.neighborhood_dot(record_id), width="stretch")
                st.caption("Arrows point toward required evidence. AND requires all operands; OR can retain independent support.")
            with right:
                st.subheader("Review action")
                actions = {"Reject evidence": "reject_evidence", "Accept correction": "accept_correction"} if record.record_type == "feature" else {"Mark interpretation unresolved": "mark_unresolved"}
                # Select outside the form so correction fields update immediately.
                action_label = st.selectbox("Action", list(actions))
                with st.form("review_action"):
                    corrected = st.number_input("Corrected value", value=float(record.value or 0), format="%.6f") if actions[action_label] == "accept_correction" else None
                    rationale = st.text_area("Reason for this review")
                    applied = st.form_submit_button("Apply review")
                if applied:
                    try:
                        workspace.act(actions[action_label], record_id, rationale, corrected)
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))

        st.subheader("Feature values and versions")
        features = [r for r in workspace.records().values() if r.record_type == "feature"]
        quantities = sorted({r.quantity for r in features})
        if quantities:
            quantity = st.selectbox("Quantity", quantities)
            selected = [r for r in features if r.quantity == quantity]
            frame = pd.DataFrame([{"Knowledge time (s)": r.ingested_at_seconds, "Value": r.value,
                                   "Series": f"{r.logical_id} [{r.event_start_seconds:g}, {r.event_end_seconds:g}]",
                                   "Version": r.version, "Unit": r.unit, "Status": r.evidence_state,
                                   "Version ID": r.record_id} for r in selected])
            st.line_chart(frame, x="Knowledge time (s)", y="Value", color="Series")
            st.dataframe(frame, hide_index=True, width="stretch")
        st.subheader("Explanation change")
        if history:
            before, after = st.columns(2)
            before.markdown("**Original displayed explanation**")
            before.write(history[0].metadata["display"]["explanation"] or "No supported statements.")
            after.markdown("**Current displayed explanation**")
            after.write(history[-1].metadata["display"]["explanation"] or "No supported statements.")
        else:
            st.info("The selected case has no displayed explanation.")

    with history_tab:
        for record in reversed(history):
            with st.expander(f"Version {record.version} · knowledge time {record.ingested_at_seconds:g}s", expanded=record == history[-1]):
                st.write(record.metadata["display"]["explanation"] or "No supported statements.")
                st.caption(record.record_id)
        reviews = sorted((r for r in workspace.records().values() if r.record_type == "review"), key=lambda r: r.ingested_at_seconds)
        for event in reversed(reviews):
            st.markdown(f"**{event.metadata['action'].replace('_', ' ').capitalize()}** — {event.metadata['rationale']}")
            st.caption(f"{event.metadata['wall_time']} · {len(event.metadata['changed_explanation_ids'])} changed explanation(s)")
        st.download_button("Download review history", json.dumps([r.to_dict() for r in reviews], indent=2),
                           file_name="review-history.json", mime="application/json")
    with diagnostics_tab:
        st.json({"workspace": workspace.scope, "backend": os.environ.get("TEG_REVIEW_BACKEND", "sqlite"),
                 "record_count": len(workspace.records()), "source_case": str(case_path) if case_path else "exact symbolic fixture",
                 "claims": states, "neural_inference": "none in this interface"})
finally:
    workspace.close()
