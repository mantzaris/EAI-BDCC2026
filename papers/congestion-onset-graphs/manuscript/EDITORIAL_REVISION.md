# Focused editorial revision, 24 September 2026

Based on reviewed delivery `09af231f3d8407ff5342f5b91292d8c4f18b76eb`. Local and fetched remote main both pointed to that commit. No applicable AGENTS.md was present. The only starting working-tree change was a regenerated manuscript PDF: its extracted text was identical to the committed PDF. The original local PDF is preserved in the ignored local file `manuscript/build/pre-editorial-user.pdf` (SHA256 `c0b87b1766789ff8709c3b6ccf2f5c070ddeb095d65831f19f85a76f39dffcc2`) and a temporary backup. No unrelated source edit was present.

## Changes

- Figure 1 now distinguishes the frozen anchor A_G from the separately refitted R_union comparator and its own prediction. Every correction receives aggregate features and p_A_G. Local histories supply C/D/E/F and construct S; M uses regional summaries. The arms are explicitly alternatives evaluated separately. Initial summaries and S require all-sensor ingestion. Box labels are deliberately wrapped, arrows follow separated paths, and the final probability box is wholly inside the figure. Rendered text extents are checked against box padding on every export.
- Figure 2 has a shared legend below both panels, outside their data regions. Every marker, interval endpoint, color, pointwise/adjusted distinction, validation/test label, axis direction and unit is preserved. The renderer checks that the legend cannot cover a data panel.
- Figures 3 and 4 were inspected and their exports retained byte-for-byte. Figure 3's caption now accurately distinguishes D-C (also primary) from the additional secondary null/internal contrasts. Figure descriptions and Figure 1's embedded alternative text match the corrected structure.
- The abstract and introduction lead with the comparative contribution and regional event motivation. Representative scores replace the abstract's score list. Methods retain the target, masks, graph definitions, projection assumptions, chronological roles, exposed validation, frozen test, all seeds and fitted-model uncertainty. Closure and replay discussion are shorter, with precise technical-artifact references.
- Table 2 explicitly labels endpoint, raw/calibrated scores and onset alarms. Table 3 displays saved mean complete inference times in two compact columns; the unchanged detailed table and underlying repeats/fitting records remain available. Correction timings include the shared anchor. No latency, communication or memory benefit is inferred.
- Results use descriptive model names and consistent rounded prose while retaining full precision in the evidence. Discussion consolidates limitations and preserves the unfavorable C result, uncertain R_union comparison, uncertain primary graph contrasts, E's secondary null advantage and higher FPR, unsigned F, sparse support and provenance concerns. The factual AI disclosure remains; internal draft-status statements were removed. Submission remains anonymous.

## Validation

The revised [PDF](graph_representations_draft.pdf) has **16 total pages**, down from 17. Main text and AI disclosure end on page 15; references begin on page 15 and continue on page 16; the per-seed appendix is on page 16. The official class, bibliography style, fonts and margins are unchanged. Four figures, three main tables and the complete per-seed appendix remain.

Every rendered page was inspected. Figures 1 and 2 were inspected as standalone exports and within the compiled pages 5 and 11, including text fit, arrow routing, the complete output box and unobstructed intervals. Figures 3 and 4 remain legible on pages 12 and 13. Table headings, equation/citation numbering, captions, anonymity and page breaks were checked. The final LaTeX log has no overfull boxes, undefined references/citations or LaTeX warnings. Template-default underfull spacing is not a scientific or overflow failure.

Reproduction uses only saved results:

```sh
python3 scripts/render_final_manuscript.py
make -C manuscript
python3 scripts/validate_editorial_revision.py
```

The [document check receipt](generated/editorial_checks.json) verifies full-precision source values for rounded prose and macros, unchanged coordinates/intervals/styles in all three numerical figures against the reviewed renderer, unmodified historical reports/results/protocols/checkpoints/scientific code, and unchanged detailed cost/score/seed exports. The [historical prose record](generated/prose_traceability.json) remains intact; the editorial receipt supplements it for the revised wording. No scientific regression suite was rerun because no scientific behavior changed.

## Scope and remaining prerequisites

No new experiment, fitting, inference, metric calculation, resampling, test evaluation, timing campaign or GPU job occurred. New GPU time is zero; the existing cumulative ledger remains **1,033.325936070 seconds**. Test results remain the completed authorized evaluation, not a fresh or untouched test. No experiment was launched or left running.

No editorial or figure defect remains identified after inspection. The substantive prerequisites in the unchanged [publication audit](../reports/FINAL_PUBLICATION_AUDIT.md) remain: upstream preprocessing and measurement-use/publication/redistribution documentation, author scientific review, final publisher/template convention and accessible production. Public availability is not treated as permission or as an identified prohibition. The PDF supplies figure descriptions but is not fully tagged. No separate supplement upload or submission action is assumed.
