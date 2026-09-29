# Semantic revision: reproduction

Run from temporal-evidence-graphs/. Saved prepared events, candidates, database
exports and replays suffice for all scoring, figures and PDF builds. The
following commands perform no neural inference and do not modify minimum_v1.

## Analysis and the single paper

Use the existing .venv, or create a Python 3.10+ environment and install
requirements-dashboard.lock. Install latexmk, pdfLaTeX and Poppler system
utilities, Graphviz (`dot` and `neato`) and DejaVu Sans fonts. The official LLNCS template is in paper/template/.

    PYTHONPATH=src .venv/bin/python -m pytest -q --junitxml=artifacts/analysis/review_views_v1/pytest.xml
    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.analyze
    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.structural_analysis
    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.alias_analysis
    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.publication
    MPLCONFIGDIR=.local/matplotlib PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.figures
    bash paper/build.sh
    PYTHONPATH=src .venv/bin/python scripts/check_semantic_manuscripts.py

Outputs:

- paper/semantic_structure_revision.pdf: main paper plus references.
- paper/archive/minimum_v1/temporal_evidence_maintenance.pdf: unchanged original.
- THEORY_RESULTS_CHANGES.md and paper/generated/semantic/: generated results.
- artifacts/manifests/semantic_manuscript_validation.json: final page counts/checks.

The old scripts/check_manuscript.py validates the archived 23-page format.
Use the new checker for the revision. Do not rerun the old publication generator
as part of this workflow: its frozen tables remain reproducibility artifacts.
The prior two-document submission is historical material under
`paper/archive/semantic_revision_8c3d3d3/`; it is not built or required by the
current paper. Only `paper/semantic_structure_revision.pdf` is a submission output.
The saved pre-inference gate is historical evidence; final validation checks it
without overwriting its timestamp.

## Rebuild only the classic-network addition

The existing graphs and result plots need not be redrawn. Preserve Figures 1–3
byte-for-byte while rebuilding the new figure, its equation annotations and paper:

```sh
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.classic_example
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.analyze
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.publication
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.figures --manifest-only
PYTHONPATH=src .venv/bin/python -m pytest -q --junitxml=artifacts/analysis/review_views_v1/pytest.xml
bash paper/build.sh
PYTHONPATH=src .venv/bin/python scripts/check_semantic_manuscripts.py
```

`classic_example` reads the retained Neo4j export, candidate and replay without
changing them. `analyze` refreshes descriptive-analysis/code hashes; original
scores are unchanged. `figures --manifest-only` refreshes the six-figure index.
The full figure command above also includes the classic mode automatically.

`artifacts/analysis/classic_network_v1/` contains the independent equation analysis,
before/after typed views, predicate evaluations, witness lists, full/visible sets,
layout, manifests and UI evidence. `paper/generated/classic_network/` supplies
case-derived numbers and the instantiated witness expression. The new figure is
`artifacts/figures/semantic_analysis_v1/ontology_instance_network.{pdf,svg,png}`.
Its manifest records every graphical object's stored ID, relation filter, source
hash, annotation and coordinate. No new model generation or database replay is
needed. The optional browser capture uses the same local setup documented in
[review_network_views.md](review_network_views.md).

## Actual Neo4j exports

Published exports came from the retained RunPod Neo4j instance, not reconstructed
or random graphs. Manifests contain Cypher, scope names, timestamps, element IDs,
hashes and count/path checks. On the existing pod, these commands independently
re-export the relevant scopes to temporary locations:

    cd /workspace/temporal-evidence-graphs
    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.export --prefix minimum_v1/ --directory /tmp/teg_reexport/minimum
    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.export --prefix structure_study_v1/synthetic-V1001-e0-d4-alternative/ --directory /tmp/teg_reexport/structure_synthetic
    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.export --prefix structure_study_v1/wesad-S2-e0-d4-alternative/ --directory /tmp/teg_reexport/structure_wesad
    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.export --prefix structure_study_v1/ppg_dalia-S1-e0-d4-alternative/ --directory /tmp/teg_reexport/structure_ppg

Connection instructions are in [runpod.md](runpod.md). The read-only exporter
uses the recorded local bolt://127.0.0.1:7687 service. Export timestamps vary;
element IDs are instance-specific. Counts and semantic IDs are reproducible
comparisons. Any fresh materialization must use isolated scopes and be labelled
as a reconstructed database instance in its manifest.

## Structural inference and replay provenance

The study is archived under artifacts/runs/structure_study_v1/.
selection.json hashes the 240 cases and protocol_initial.md.
pilot_amendment.json prospectively records pilot v2. core/frozen.json hashes
the runtime, prompt, schema and configuration. core_launch.json records a
31.2-minute estimate from pilot v2; actual core generation took 17.2 minutes.
The pilots used 21 and 19 calls, and the core used 325 of its 480-call cap.
There was no post-correction generation.

Original execution commands on the existing RTX 5090 pod:

    PYTHONPATH=src .venv/bin/python scripts/serve_structure_model.py

After the local API and CUDA placement check were ready, in a second shell:

    PYTHONPATH=src .venv/bin/python scripts/run_structure_study.py

After the independently documented admission-table omission was found:

    PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.alias_replication

These provenance commands are not needed to recompute the paper. They write
completion/resource manifests and must not run over the frozen archive. For
execution replication, use a separate checkout/artifact root and an isolated
Neo4j instance/scope, preserving the supplied selection, source hashes, prompt
and schema. Cached candidates suffice for database replay. New candidates
require the pinned GPU deployment: BF16, zero CPU offload/swap, context 12,288,
four concurrent sequences and seed 20260929. The analysis commands create no
paid resource and perform no CPU neural inference.

## Artifact map and semantic conventions

Within artifacts/analysis/semantic_analysis_v1/:

- exports/: all 480 actual original B2/M1 scopes, including assessments;
  93,047 nodes and 256,517 relations.
- structure_exports/: 48 actual extension scopes across three sources,
  fixture/model origins, four updates and both graph methods.
- proposition_scores.json.gz: raw text, canonical propositions, independent
  witnesses, grounding and unique required-slot matches.
- semantic_*, contract_crosswalk*, temporal_*: new scores and old/new crosswalk,
  denominators and subject uncertainty.
- storage_by_scope*, active_graph_by_snapshot.json, core_by_snapshot*,
  construction_origins_by_scope.csv, construction_origin_uncertainty.json,
  relation_type_mixing.csv, active_relation_mixing.csv and degree distributions:
  separate full, active and semantic-core measurements.
- revision_exposure*: simultaneous revision batches, older-version roots,
  direct/reachable IDs, independently changed predicates and exposure.
- structural_*: exact/generated programs, realized depth, independent
  truth-table witness scoring and 9,600 matched replay cells.
- primitive_alias_*: the separate 4,800-cell admission-normalization replication,
  with unchanged candidate text and parent links.
- representative_cores/: core nodes/edges, omitted-object sidecars and witness
  IDs. Median and maximum-impact rules select the same cases in both real sources;
  both labels are retained without pretending they are different examples.
- assessment_temporal_audit.json: all original assessments sharing a record and
  knowledge timestamp. Conflicting outcomes are retained together and marked
  ambiguous; element IDs are not treated as an undocumented event sequence.

Figure PDF/SVG/PNG files are in artifacts/figures/semantic_analysis_v1/.
The two paper networks and dashboard load shared views/layouts from
artifacts/analysis/review_views_v1/. Stored citations stay attached to their
original versions; current-version resolution is an explicit derived-path sidecar.
Dashed AND bundles enumerate their stored edges. SUPPORTS mirrors and FOR_SUBJECT
hubs are excluded from dependency degree. Proposed, admitted and displayed
relations are separately tabulated. See [review_network_views.md](review_network_views.md)
for selection rules, actual selected-scope export commands, view manifests and UI validation.

Precision scores emitted bounded propositions; recall matches each answerable
requirement once. Empty output has precision NA and recall zero when answerable.
Participant identities are scoped to dataset. Temporal points are discrete
observations; no smooth recovery curve or finite replacement time is invented.
Original strict-contract scores and zero adequate systems replacements remain
unchanged.
