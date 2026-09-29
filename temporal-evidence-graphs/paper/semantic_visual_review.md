# Single-paper PDF and dashboard review

Reviewed on 29 September 2026 from the actual compiled PDF, using Poppler page
rasterizations and direct image inspection. The official LLNCS class, font sizes
and page geometry are unchanged.

- Authoritative output: `paper/semantic_structure_revision.pdf`.
- 18 main pages, 1 reference page, 19 total; five figures and four tables.
- SHA-256: `b5f2e6759f96deae661b5e42cba6a47d135b37ff67724582f446dfb9ce29636f`.
- Eight numbered equations and two propositions; no external submission document.

All pages were reviewed in contact sheets, with full-size inspection of the
ontology/relations, projection/view equation, proofs, networks, semantic results,
structural table and bibliography. Final network pages 13 and 14 were inspected
again after adding explicit observation-version labels. Figure 2 uses seven stored
WESAD records and eight labeled relations; Figure 3 uses twelve stored PPG-DaLiA
program records and eleven relations, including eight citations represented by
two explicit AND bundles. The networks use topology-aware routing and sufficient
white space. No clipped arrowheads or colliding labels remain. Text stays legible
at normal page size: the minimum network fonts are 9.50 and 9.13 points after
scaling to the template's 12.2 cm text width. Claims, features and observations
have consistent colors/types; state words remain readable without color.

Every visible edge has a label, with stored directions and immutable citations
preserved. Supersession points new-to-old. AND enclosures/bundles have full row/edge
maps and are labeled as rendering constructs. Current-version resolution remains
a separately identified path sidecar. Assessment conflicts remain ambiguous;
availability and display membership are independent. The real case is shallow
and is not presented as a propagation advantage.

Figure 4 retains both grounding and required recall in two panels, with discrete
checkpoints and intervals; its denominators and fresh-answer table remain in the
paper. Figure 5 separates exact/generated population results. The structural
admission sensitivity result is in the main text, distinct from the primary run.
Network float pages appear within Results, before the remaining outcome discussion.
Table/equation widths fit, the bibliography resolves, all fonts are embedded, and
there are no overfull boxes or unresolved references. Ordinary underfull page/
reference spacing is retained. No caption, relative PDF link or build dependency
requires the historical supplement.

The running Streamlit interface was inspected through headless Chrome at a
1720×2050 viewport. Saved real/structural screenshots show the labeled networks,
focus/time controls, full text and asserted/storage interval details. AppTest
exercises case/state/focus selection, witness highlighting, edge inspection,
truncation warnings and provenance expansion. The unhighlighted dashboard SVG
is byte-identical to the publication renderer output for each shared view.

Mechanical checks: `artifacts/manifests/semantic_manuscript_validation.json`.
Browser evidence: `artifacts/analysis/review_views_v1/dashboard/validation.json`.
Test report: `artifacts/analysis/review_views_v1/pytest.xml` (70 passed).
Read-only live Neo4j checks verified the WESAD source (193 nodes/531 edges, five
stored paths) and the selected generated program (26 nodes/83 edges). Original
benchmark inputs, runtime and outcomes are unchanged. No new inference was run.
This is implementation/manuscript validation, not a human study or submission.
