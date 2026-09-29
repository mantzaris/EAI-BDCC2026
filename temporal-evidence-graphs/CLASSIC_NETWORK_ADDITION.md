# Classic ontology-instance network — completed

The single [paper](paper/semantic_structure_revision.pdf) has **20 main pages
plus one reference page**, six figures, eight numbered equations and two
propositions. The new Figure 4 is on page 16; its worked equations and numerical
example are on page 15. Figures 1–3 and both existing result-plot assets are
preserved byte-for-byte. The official template is unchanged.

## Case and computed result

The figure uses the admitted GPU-generated program
`ppg_dalia-S1-e0-d2-alternative`, participant S1 episode 0, requested/realized
depth two. It retains the existing deterministic selection from 87 eligible
programs. The actual Neo4j scope is
`structure_study_v1/ppg_dalia-S1-e0-d2-alternative/generated/route_loss/M1`.
Its export has 26 nodes and 83 edges. The drawing has **14 individually visible
stored records and 18 individually labeled directed edges**. Two omitted motion
windows remain expandable in the dashboard. This is a controlled task over real
measurements, not a naturally occurring waveform reasoning graph.

At the recorded correction at 2331.0 s, A1's EDA median changes from
5.374855999999999 to 4.214302 µS, against the admissible `>= 4.74108975 µS`
threshold. The snapshot comparison is 2301.01 → 2331.01 s. Availability remains
true. Each route requires four feature tests; the root admits either route.
Support of CA/CB/R changes **true/true/true → false/true/true**.

The full theorem projection contains 13 claim/feature nodes and ten dependency
edges. U contains both A1 versions; R contains those versions, CA and the root.
Only CA is in B, the actual support-change set. The independent required-change
set A and recorded B2 schedule D both contain CA, so **exposure is 0/1 = 0**.
Direct/full outcomes agree. Full-scope sets are computed before selecting the
14-node drawing; their visible intersections are exported explicitly.

The existing core definition gives eleven current-core nodes. Withdrawn CA
remains a declared ancestor of the displayed root, while old A1 and the two EDA
windows are review context. Stars, type fills, revision outlines and support
transitions make these distinctions visible without changing support semantics.

## Implementation and reproduction

- `semantic/classic_analysis.py`: existing witness support, independent oracle,
  predicate evaluations, core membership, locality sets and recorded schedules.
- `semantic/classic_example.py`: extraction/annotation joins, manifests and
  generated LaTeX values/expression.
- `semantic/classic_render.py`: seeded spring union layout, ellipse separation,
  individually routed/labeled edges, PDF/SVG/PNG. No evidence evaluation occurs
  in the renderer. An undirected simple graph is used only for positioning.
- Existing dashboard: select PPG-DaLiA, then **Layout → Classic network**.
  Structured mode remains available. Both modes share typed objects, state/focus,
  witness highlights and source-detail controls. The classic paper SVG and
  unhighlighted dashboard SVG are identical; both recorded states reuse positions.

[Reproduction commands](docs/semantic_reproduction.md#rebuild-only-the-classic-network-addition)
build the addition without redrawing existing figures or running inference.
[View documentation](docs/review_network_views.md#classic-ontology-instance-mode)
gives exact filters, class/relation meanings, layout parameters and interaction.
The [figure PDF](artifacts/figures/semantic_analysis_v1/ontology_instance_network.pdf)
also has SVG/PNG siblings and a full manifest. Equation analysis, views, layout,
source hashes, before/after exports and browser evidence are in
`artifacts/analysis/classic_network_v1/`.

## Validation and bounds

All 76 tests pass, including six new focused checks for stored identity/time,
program witness integrity, independent required changes, core/context distinctions,
wrong-subject/value rejection, exact dashboard/publication equality and UI
truncation/expansion. The single-paper validator checks 529 unique actual export
scopes, retained live count/path evidence, frozen runtime/input hashes, exact
annotation regeneration, embedded fonts and resolved references. The new labels
are at least nine points at final printed size. All pages were reviewed, with
normal-size inspection of the new network and adjacent equations/results.

The retained live database checks and source export were reused; this addition
made no database mutation. It performed **zero new GPU calls** and no CPU inference.
Original semantic score files, frozen candidates/replays and all five previous
figure triplets are unchanged; `preservation.json` records the comparison with
`100fa39`. The graph remains a bounded review view, and this implementation adds
no human-performance or real-time-benefit claim. No conference submission occurred.
