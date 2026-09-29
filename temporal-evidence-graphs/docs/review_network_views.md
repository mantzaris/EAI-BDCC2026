# Auditable review networks

The paper and dashboard share `review_graph_v1` JSON objects. They are bounded
views of actual Neo4j records, not illustrative networks or new reasoning graphs.
The current revision uses no new inference. Run commands from this project root.

## Selection and database provenance

| Network | Actual database scope | Selection |
|---|---|---|
| WESAD S11, episode 0, correction, M1 | `minimum_v1/wesad-S11-e0/correction/M1` | Existing median-size eligible WESAD core, lexical tie-breaking; preserved from the semantic analysis |
| PPG-DaLiA S1, episode 0, generated program, M1 route loss | `structure_study_v1/ppg_dalia-S1-e0-d2-alternative/generated/route_loss/M1` | Smallest complete claim/feature ancestor closure among 87 eligible primary generated programs, then lexical case/root ID |

Structural eligibility requires an admitted answer with at least two complete
alternative witnesses, each containing one declared parent, at least one required
withdrawal, and a retained root under M1 primary-route loss. The selected program
has requested and realized depth two. This is a controlled numerical program on
prepared real features, not naturally occurring waveform reasoning. The primary
240-case candidates and replays supply selection; the normalization replication
and compiled fixtures are excluded. `network_examples.structural_selection()`
records all eligible cases, selection rules and source hashes.

Both graphs were exported from the retained RunPod Neo4j Community instance.
The selected WESAD database contains 193 nodes/531 edges; its fresh read-only
export matches the existing analysis export exactly, including five verified
claim-to-feature-to-observation paths. The selected structural scope contains
26 nodes/83 edges. The paper views contain 7 records/8 edges and 12 records/11
edges, respectively. `artifacts/analysis/review_views_v1/live_database_validation.json`
records counts, hashes and verification time. Export manifests contain exact
Cypher, database element IDs, source scope and knowledge times.

On the existing pod, re-export without touching benchmark records:

```sh
cd /workspace/temporal-evidence-graphs
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.export --prefix minimum_v1/wesad-S11-e0/correction/M1 --directory /tmp/teg_review_reexport/wesad
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.export --prefix structure_study_v1/ppg_dalia-S1-e0-d2-alternative/generated/route_loss/M1 --directory /tmp/teg_review_reexport/structure
```

The exporter uses the existing adapter and loopback Bolt connection. Fresh export
timestamps vary. Neo4j element IDs identify objects within this retained instance;
immutable Record IDs are the cross-instance comparison keys. No database rebuild
or new paid resource was needed.

## Transformation and invariants

`semantic/review_view.py` selects a scope, focus claim and knowledge time. It
follows immutable claim inputs, optionally expands feature provenance, and includes
known versions of the selected evidence identities. Ingestion time controls record
visibility; assessment knowledge time controls support-state visibility. Asserted
intervals and storage-wrapper intervals are distinct attributes. A current query
can resolve a cited identity to a new version without changing the stored citation.
The resolution sidecar records the original citation and every reverse traversal
of a stored `SUPERSEDES` edge. Historical queries resolve at their stated time.

Every visible stored node carries its Record ID and database element ID; every
stored edge preserves its exact ID, direction, relation type and meaning. Claims,
features and observations use different fills. Outline/badge words encode revised,
historical, supported, contradicted, ambiguous or withdrawn states independently.
A historical available feature remains available. `SUPPORTS` means admission-time
support, not a fresh current-validity verdict. Latest tied assessment outcomes are
all retained; conflicting states are marked ambiguous. Display membership comes
from saved explanation versions, not a chosen assessment tie-break. Evaluation
reference truth is never drawn from these outcome flags.

The view budget counts stored record nodes. It prefers a complete witness closure
when it fits, then adds remaining prerequisites in deterministic order. Omitted
IDs and incomplete witness groups are explicit, with a partial-view warning and
expansion control. Observation provenance excluded by the focused structural view
is separately enumerated. Identity hubs, sensor membership, explanation containers,
assessment nodes, review events and reverse `SUPPORTS` mirrors stay in metadata.
The drawing is not a claim of completeness beyond its declared selection.

Witness metadata is an OR over sets of jointly required inputs. The renderer can
group a disjoint multi-feature AND witness into an enclosure: each row is a stored
feature, each row port maps to its full ID, and a dashed labeled bundle maps to
all original `DEPENDS_ON` edges. The enclosure and bundle are rendering constructs,
not stored junction nodes or model-generated links. Witness IDs are scoped to
their owning claim; the root's W1 and a parent's W1 are different groups.

`validate_view()` verifies stored identity/direction, visibility, witness omission
and continuous derived paths. Rendering changes presentation only. A bounded view
cannot prove that omitted context contains no additional route or contradiction.

## Shared layout, labels and interaction

`semantic/network_render.py` produces labeled DOT from the typed view. Graphviz
`dot` uses connectivity, deterministic input order and measured labels to lay out
the union of both recorded snapshots. The layout stores node coordinates, routed
splines and edge-label positions; `neato -n2` reuses them at each time. Future
records do not appear in the earlier view. Invisible canvas anchors are declared
layout-only objects. A deterministic annotation-spacing pass saves both original
and adjusted label positions. There is no random seed. Reproduction records the
Graphviz version, node/rank separation, fonts and layout parameters; exact pixels
may differ across Graphviz/font versions. Coordinates do not measure similarity.

Every visible edge has a path label. `cites`, `requires` and `needs` map to stored
`DEPENDS_ON` edges; `derived from` maps to `DERIVED_FROM`; `supersedes` maps to
`SUPERSEDES`. Arrows point from dependents to inputs or new versions to old ones.
Dashed `needs all` bundles enumerate their stored edges. Current-version shortcuts
remain in the derived-path detail panel, not silently drawn as stored relations.

The existing Streamlit app defaults to **Recorded network views**. Controls select
case, time, focus, witness highlight, node/edge details, provenance expansion and
record budget. Selectboxes, rather than direct node clicks, drive inspection.
The detail panel exposes full text, exact values, units, both interval meanings,
versions, source IDs and assessment provenance. The UI renders server-generated
SVG with the same fixed layout as the paper. JSON and SVG downloads recover the
view. Automated tests compare the unhighlighted SVG bytes and view hashes between
the dashboard loader and publication exports. Screenshots in
`artifacts/analysis/review_views_v1/dashboard/` show the running browser interface.
Existing review actions remain in the isolated `review/` workspace, using Neo4j or
the strong SQLite control; recorded benchmark cases are read-only.

## Classic ontology-instance mode

Figure 4 adds a spatial network of the same admitted
`ppg_dalia-S1-e0-d2-alternative` case; Figures 1–3 are preserved. The selection
remains the smallest witness-complete eligible primary generated case among 87,
with lexical tie-breaking. Knowledge times are 2301.01 and 2331.01 s, spanning
the recorded primary-route correction at 2331.0 s. This is a controlled
structural task over real PPG-DaLiA measurements, with realized depth two.

The after view contains **14 individually drawn stored records and 18 stored
edges**: three ClaimVersion instances, nine FeatureVersion instances (eight
inputs plus the revised A1), and two EDA Observation windows. Eight primitive
citations, two parent citations, seven DERIVED_FROM relations and one SUPERSEDES
relation are drawn separately. `AND A/B` and `OR A/B` map to DEPENDS_ON; `from`
maps to DERIVED_FROM; `revises` maps to new-to-old SUPERSEDES. Each AND edge belongs
to its owner's single four-input witness; the root has two singleton-parent
alternatives. There are no bundled edges or visual junction nodes. The two motion
windows and their provenance edges are expandable, yielding 16 records/20 edges.
Subject/sensor, explanation, assessment and SUPPORTS context retains the same
explicit filters as the structured view. Current-version paths stay in sidecars.

`classic_analysis.py` independently computes annotations before rendering.
The existing runtime witness evaluator supplies support; the event/task oracle
supplies required changes. A truth-table audit checks each admitted witness.
Each primitive predicate checks dataset, subject, session, interval, quantity,
unit, current visible version, availability and its exact numerical comparator.
A1's EDA median is 5.374855999999999 µS before and 4.214302 µS after, against
`>= 4.74108975 µS`; its availability stays true. CA/CB/R support changes from
true/true/true to false/true/true. Assessment outcomes never supply the oracle.

The unchanged core rule selects current display members, declared claim ancestors
and resolved feature versions. Structural explanations lack the original
`metadata.case_id`; an explicit explanation logical-ID selector instantiates the
same rule. The after core has 11 nodes. CA remains a declared ancestor of displayed
R even though CA itself is withdrawn. Old A1 and the two observation windows are
review context, not current-core members. Stars encode this distinction.

The full export has 26 nodes/83 edges (24 Record objects plus two assessments).
The theorem projection has 13 claim/feature nodes and ten claim DEPENDS_ON edges;
provenance, membership, supersession and SUPPORTS mirrors do not create dependency
paths. U contains both A1 versions; reverse reachability R contains U, CA and the
root. Only CA changes support (B). The independent required set A and recorded
B2 schedule D also contain only CA, so exposure is 0/1 = 0. All these revision
sets are visible in the printed view; the analysis separately reports full-scope
and visible counts. The full database scheduler also reaches an explanation
container; its administrative membership is excluded from theorem reachability.

`classic_example.py` extracts the typed views, joins these precomputed annotations
and exports the figure. `classic_render.py` consumes them without evaluating
support. NetworkX spring positioning uses a sorted undirected simple union only
for coordinates: seed 20260929, 500 iterations, k=0.60, no edge weights. The
renderer preserves the original typed directed edges. A global rotation, ellipse
separation and routed arrows fit the figure; coordinates and label positions are
saved, including visibility-path detours where necessary. Font sizes remain
9.2/9 points on the 12.2 cm publication canvas. Expanded views grow the canvas
instead of shrinking labels. NetworkX, Matplotlib and SciPy versions and optimizer
parameters are recorded. Both recorded states reuse the union coordinates.
Retrospective truth-transition annotations are identified as such; future records
never appear in the earlier snapshot.

In the existing dashboard, select PPG-DaLiA and **Layout → Classic network**.
The default view loads the paper's exact serialized object and coordinates.
Time/focus, route highlighting, object details, budget and expansion controls
remain available; **Structured** retains the previous renderer. Equation
memberships and full/visible sets appear in details. The unhighlighted SVG
is byte-identical to the publication export. A browser screenshot and DOM/hash
record are saved under `artifacts/analysis/classic_network_v1/`.

## Reproduce

Install Graphviz (`dot`, `neato`) and DejaVu Sans, plus the documented Python/LaTeX
dependencies. To regenerate only the two networks and their shared view objects:

```sh
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.network_examples
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_review_views.py tests/test_review.py
PYTHONPATH=src .venv/bin/python -m temporal_evidence.cli dashboard
```

Use [semantic_reproduction.md](semantic_reproduction.md) for the complete figure,
analysis and single-PDF build. `paper/build.sh` compiles only the authoritative
paper. No historical supplement is a build or reading dependency.

Each example directory under `artifacts/analysis/review_views_v1/` contains config,
before/after JSON, shared layout, vector/PNG/DOT exports and manifests. Each paper
network manifest under `artifacts/figures/semantic_analysis_v1/` includes source
hashes, full record/edge IDs, hidden relation classes, witness groups, derived
paths, labels, row-port mappings and layout positions. The registry and generated
LaTeX macros link the manuscript's selection/timing numbers to these objects.

The interface demonstrates inspectability. There is no human-performance study,
new latency advantage or new model evaluation. All original semantic scores,
primary/normalized structural outcomes and the zero adequate streaming replacements
remain separate and unchanged.

Optional browser-evidence reproduction uses Node 22+ and an already running Chrome
DevTools endpoint. Start the dashboard and browser in separate terminals:

```sh
PYTHONPATH=src .venv/bin/streamlit run src/temporal_evidence/dashboard/app.py --server.headless true --server.address 127.0.0.1 --server.port 18501 --browser.gatherUsageStats false
google-chrome --headless --disable-gpu --disable-background-networking --no-first-run --no-default-browser-check --user-data-dir=/tmp/teg_review_browser_reproduction --remote-debugging-port=19222 http://127.0.0.1:18501
```

Then, from the project root, run `node scripts/capture_review_dashboard.mjs`.
For the classic mode, run `node scripts/capture_classic_dashboard.mjs`.
This saves the two screenshots, DOM text and a version/hash validation record.
`TEG_REVIEW_CDP` can select a different local DevTools URL. Stop these validation
processes when finished. Browser capture is optional for rebuilding the paper;
the committed record documents the completed end-to-end UI check.
