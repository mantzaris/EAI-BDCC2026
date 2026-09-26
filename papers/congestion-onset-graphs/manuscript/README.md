# Comparative conference draft

[Compiled PDF](graph_representations_draft.pdf) and [main source](main.tex) target EAI BDCC2026. This is an anonymous draft for human scientific review, not a submitted or submission-ready paper. The original test set has now been evaluated under the [committed final protocol](../reports/FINAL_TEST_PROTOCOL.md).

```sh
# From papers/congestion-onset-graphs; only renders saved CUDA statistics.
python3 scripts/render_final_manuscript.py
make -C manuscript
# Document-only preservation and transcription checks for the editorial revision.
python3 scripts/validate_editorial_revision.py
```

The PDF uses the unmodified class and bibliography style from the conference-linked official kit. No margins, geometry or font family are changed. Computer Modern uses its default encoding and embedded vector glyphs where available. The original class omits running heads/page numbers. [Publication audit](../reports/FINAL_PUBLICATION_AUDIT.md) records official URLs, current instructions, kit hashes and series/template ambiguities.

The paper has four vector figures, three main tables and a per-seed appendix. PNG previews and SVG exports accompany the figures. [Generated traceability](generated/claim_traceability.json) maps numerical macros and tables to saved numerical results. [Prose traceability](generated/prose_traceability.json) maps the remaining quantitative statements and design constants. These exports perform no new scientific computation. The final numerical analysis ran on CUDA before writing.

The [editorial revision note](EDITORIAL_REVISION.md) records the Figure 1 input/path repair, Figure 2 legend relocation, condensed text and cost table, and page inspection. The original prose traceability remains a historical record; [editorial checks](generated/editorial_checks.json) add current rounded prose values at full source precision and verify unchanged plot coordinates. The historical detailed [cost table](generated/costs.tex) is retained; the paper formats the already saved means in a compact table. Rendering now writes only manuscript assets, never scientific result files.

Do not upload the identified repository directly as an anonymous review artifact without an authorship/anonymity review. Authorship/affiliations are deliberately not invented. The source includes an AI-assistance disclosure. Human scientific approval, measurement analysis/publication/redistribution terms, upstream processing provenance, and final portal/publisher production rules remain prerequisites. Figure descriptions are provided in ALT_TEXT.md; the local PDF is not fully tagged.

The original template files in template/ remain byte-for-byte identical to the official linked kit, including their notices. Raw measurements are excluded. Bibliography entries cite primary sources; sources that remained inaccessible are qualified in the publication audit rather than reconstructed from guesses.
