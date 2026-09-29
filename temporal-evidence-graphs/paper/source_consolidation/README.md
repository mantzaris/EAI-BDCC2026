# Complete LaTeX source

`paper/main.tex` is the authoritative complete source. It contains the 20
previously included files and all 13 formatted bibliography entries. Source
comments retain provenance without creating build dependencies. The former
section files, generated TeX and bibliography database remain historical inputs.

Only the official class, standard TeX packages and six figure PDFs are external.
No Python generator or BibTeX pass is needed to build the manuscript:

```sh
bash paper/build.sh
.venv/bin/python scripts/check_consolidated_manuscript.py
```

Run these commands from `temporal-evidence-graphs/`. The validation script compares
the complete source with the recursively expanded source at `9543daf`, then builds
in a temporary directory with no former manuscript fragments or bibliography
files. It compares the old, published and isolated PDFs by text and by all page
pixels at 144 dpi. The report is `validation.json` in this directory.

The PDF retains 20 main pages and one reference page. All scientific content,
experimental artifacts and figure assets are unchanged. The only additional
typesetting tokens are three spaces preserving the former table-input boundaries.
