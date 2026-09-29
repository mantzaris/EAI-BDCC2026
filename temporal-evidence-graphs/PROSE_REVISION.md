# Prose revision

This records the completed language edit at `9543daf`. The manuscript has since
been consolidated into [paper/main.tex](paper/main.tex) without changing the
rendered paper. The reproduction commands below describe the former multi-file
source structure. Use the [current build instructions](docs/semantic_reproduction.md)
for the complete source.

The authoritative [paper](paper/semantic_structure_revision.pdf) has been edited
throughout for clearer definitions, shorter sentences and more direct explanations.
The comparison baseline is the completed manuscript at `c62001f`.

## Length and presentation

The compiled paper retains **20 main pages and one reference page**. Approximate
prose increased from **5,500 to 5,634 words (+2.44%)**. TeXcount counts body text
and captions, excluding headings, equations, table cells, figure labels and
references. Macros are not expanded. Body text alone changed from 4,866 to 4,983
words; captions changed from 634 to 651.

The official template, fonts, margins, line spacing, figure dimensions and section
structure are unchanged. Paragraph boundaries and float pagination were adjusted
to keep explanations intact around the network pages. All six figure assets remain
byte-identical. The single-paper build remains authoritative.

## What changed

- Ontology construction now starts with what the vocabulary permits and who
  creates each kind of instance. Technical creation rules follow that explanation.
- The semantic core and review view explain original citations and successor
  versions before introducing the corresponding paths and metadata.
- The support, locality, exposure and evaluation equations have practical lead-ins
  and clearer explanations of the quantities they compute.
- Results state what changed and what the change means for retained information.
  Grounding, completeness, contract compliance and adequate replacement remain
  separate outcomes.
- Long sentences and compressed qualifications were split. Necessary terminology
  is introduced consistently. EDA, IQR and SD are expanded on introduction.
- The publication generator now preserves the revised abstract, WESAD example and
  temporal-denominator prose. Its `--prose-only` mode skips writes to analysis
  artifacts. Numerical generation is unchanged.

## Representative edits

**Ontology construction**

Before: “The ontology is fixed in code; the generator proposes instances inside it.”

After: “The ontology is fixed in code and specifies the allowed objects and
relationships. The generator proposes instances within this vocabulary.”

**Version inspection**

Before: “Original DEPENDS_ON edges remain intact; current-version resolution
retains its citation and reverse-supersession witnesses in an explicit derived-path
sidecar.”

After: “Original DEPENDS_ON edges remain intact. A separate derived path records
how a citation resolves to a newer version, preserving the citation and the
supersession edges traversed in reverse.”

**Revision locality**

Before: “R_delta is a candidate set; B_delta is the actual support-change set.”

After: “R_delta contains changed inputs and reachable dependents for re-evaluation.
B_delta contains only claims whose support actually changes.”

**Results interpretation**

Before: “The precision gain therefore includes rejection of correct useful
propositions, not merely successful repair.”

After: “Thus the precision gain partly comes from rejecting correct, useful
propositions.”

**Implementation cost**

Before: “The original runtime repeatedly constructs version maps; structural
replay evaluates the whole small program before scheduled writes.”

After: “The original runtime repeatedly builds version maps. Structural replay
evaluates the whole small program before writing scheduled updates.”

These excerpts normalize TeX markup and line breaks for readability.

## Preservation and validation

The [mechanical record](paper/prose_revision/validation.json) compares every active
manuscript input against the baseline. It confirms byte-identical numbered
equations, proposition statements, figure inclusions, generated result tables and
macros. Per-source checks preserve numerical literals, result-macro usage and
citations. The bibliography, template and entire experimental artifact tree are
unchanged. All fonts are embedded, with no overfull boxes, unresolved references
or dependency on another submission document.

Manual review checked the scientific meaning beyond these mechanical comparisons.
Candidate revision neighborhoods remain distinct from actual support changes.
Alternative witnesses can preserve support after an input changes. Required
changes and direct schedules retain their independent definitions and the
propositions retain their assumptions. Grounding remains separate from required
recall and from the original contract. Primary and normalized structural results
remain distinct, as do withdrawal and the original failure to produce adequate
replacements. The graph still represents external commitments rather than neural
computation.

The compiled pages were visually inspected, including equations, captions,
networks, result tables, page breaks and references. See
[paper/semantic_visual_review.md](paper/semantic_visual_review.md).
No inference, database replay, experimental scoring or implementation-test rerun
was needed. Publication tables regenerated from saved results remain identical.
Earlier scientific and dashboard validation records remain frozen.

## Reproduce this manuscript revision

From `temporal-evidence-graphs/`, using the existing environment:

```sh
PYTHONPATH=src .venv/bin/python -m temporal_evidence.semantic.publication --prose-only
bash paper/build.sh
PYTHONPATH=src .venv/bin/python scripts/check_prose_revision.py
```

The checker requires the `c62001f` Git revision, TeXcount and Poppler. It writes
only `paper/prose_revision/validation.json`. Full experimental reproduction
commands remain in [docs/semantic_reproduction.md](docs/semantic_reproduction.md).
