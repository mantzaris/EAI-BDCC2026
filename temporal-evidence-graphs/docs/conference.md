# Conference format verification

The [official call for papers](https://bdcc-conf.eai-conferences.org/2026/call-for-papers/)
was checked on 2026-09-28 and rechecked on 2026-09-29. It lists 30 September 2026 for full-paper submissions,
anonymized English PDFs, and 12–20 regular-paper pages excluding references and
appendices. It links the Springer author kit and requests descriptive figure text.
The precise submission cutoff/timezone is not exposed by the public JavaScript
submission landing page and remains unverified; no submission has been attempted.

The official [LaTeX ZIP](https://help.eai-conferences.org/wp-content/uploads/sites/88/2021/04/Springer_Latex_Template.zip)
contains `llncs.cls` and `splncs04.bst`; these are retained under `paper/template/`
with their documentation. ZIP SHA-256:
`f0127c19b212cdd76e3f3d5bb363f0e22c58cba6fe600a81c05b101035f4fe5c`.

The conference asks authors to disclose substantive LLM assistance. The manuscript
discloses implementation/writing assistance, distinguishes GPU experiment models,
and reserves scientific accountability for the human authors. No authorship, human
annotation, or user study will be attributed to an automated system.

The completed draft has **20 main pages, one reference page, and two appendix
pages**. The official class and text dimensions are retained. All fonts are
embedded, references resolve, and the final log has no overflowing boxes. There
are five figures and fourteen tables, with descriptive captions and separate
[figure descriptions](../paper/figure_descriptions.md). The PDF is not tagged;
these checks do not certify full PDF accessibility. Anonymous author metadata and
the 189-word abstract are verified by
[check_manuscript.py](../scripts/check_manuscript.py); its
[saved validation](../artifacts/manifests/manuscript_validation.json) records
the exact PDF and source hashes. Rendered figures and tables were inspected.
No conference upload has been attempted.
