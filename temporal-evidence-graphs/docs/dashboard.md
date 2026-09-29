# Evidence review dashboard

From the project directory:

```sh
.venv/bin/python -m pip install -r requirements-dashboard.txt
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli dashboard
```

Open <http://127.0.0.1:8501>. The app binds to loopback. It performs no model
inference and requires no model weights. The opening **Recorded network views** page reproduces the WESAD S11 correction
and PPG-DaLiA S1 generated alternative-witness program from the paper. Select a
case, before/after state and focus claim; select a node or edge to inspect exact
values, asserted and storage intervals, immutable IDs, full claim text and
assessment provenance. A witness selector highlights its stored route. Increase
the record budget or expand observation provenance to reveal omitted context.
The same typed view and fixed Graphviz layout produce the paper vectors and
Streamlit SVG. There is no direct node-click handler: selection uses controls.
Recorded examples are read-only; [view semantics and reproduction](review_network_views.md)
document their exported database sources. Graphviz (`dot`, `neato`) and DejaVu
Sans must be installed on the host.

For **Dependency demonstration** and **Saved explanation**, the default local SQLite review store
uses full dependency semantics; the optional Neo4j backend uses its own `review/`
scope. Set `TEG_REVIEW_BACKEND=neo4j` and `TEG_REVIEW_NEO4J` to a loopback Bolt URI
to use that backend. `TEG_REVIEW_DB` selects an alternate local review database.

Select **Dependency demonstration** in the workspace control. It is available without recordings or experimental
outputs. Select feature `a`, choose **Accept correction**, enter `4`, add a reason,
and apply the review. The direct and downstream old statements are withdrawn;
the independent OR statement and earlier-value statement remain. Accepting a
correction back to `2` restores the original supported content in another
immutable explanation version. **Reject evidence** creates an invalidated feature
version. **Mark interpretation unresolved** creates a claim revision and removes
it from the current supported text.

The issue queue orders explicit missing, invalidated, and contradicted evidence
before other entries, then sorts by downstream claim count. Selecting an item
shows its local dependency graph. Feature panels expose numerical values,
observation intervals, ingestion times, units and version identifiers. The revision
history shows old and current text and records the review reason. Review events
can be downloaded as JSON. Technical state is confined to the diagnostics tab.

The **Saved explanation** view imports an M1 or B3 output and its visible evidence
into the review workspace. Actions append versions there; the saved experiment
and evaluation artifacts are unchanged. The current implementation demonstrates
conservative retraction/restoration. It does not generate a fresh replacement
number in the interface or infer that a reviewer-supplied correction is true.

Three scripted examples are generated with:

```sh
PYTHONPATH=src .venv/bin/python scripts/make_review_examples.py
```

They demonstrate a successful correction, surviving alternative support, and a
deliberately mistaken rejection that removes valid information. The records label
the actor `automated_demonstration`. They establish interface functionality, not
human decision accuracy, annotation quality, or review-speed improvements.
