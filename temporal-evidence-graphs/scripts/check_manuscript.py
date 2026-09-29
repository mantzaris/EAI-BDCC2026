"""Verify generated inputs and the compiled conference manuscript.

Run from the project root after paper/build.sh. Visual inspection and scientific
author review remain separate from these mechanical checks.
"""
from pathlib import Path
import re
import subprocess
from temporal_evidence.io import read_json, write_json, digest_file, utc_now


def command(*args):
    return subprocess.check_output(args, text=True)


def main():
    generated = read_json("paper/generated/manifest.json")
    for group in ("inputs", "tex_files"):
        for path, expected in generated[group].items():
            assert digest_file(path) == expected, f"Stale generated input: {path}"
    assert digest_file(generated["script"]) == generated["script_sha256"]
    publication = read_json("artifacts/analysis/publication.json")
    assert publication["complete"] and publication["integrity"]["passed"]
    for path in Path("artifacts/figures").glob("*manifest.json"):
        if path.name not in ("minimum_v1_manifest.json", "streaming_manifest.json", "design_manifest.json"):
            continue
        record = read_json(path)
        if "input" in record:
            assert digest_file(record["input"]) == record["sha256"], path
        for source, expected in record.get("inputs", {}).items():
            assert digest_file(source) == expected, source
        if "script" in record:
            assert digest_file(record["script"]) == record["script_sha256"], path
    pdf = Path("paper/temporal_evidence_maintenance.pdf")
    info = command("pdfinfo", str(pdf))
    fonts = command("pdffonts", str(pdf))
    text = command("pdftotext", "-layout", str(pdf), "-")
    log = Path("paper/build/main.log").read_text()
    auxiliary = Path("paper/build/main.aux").read_text()
    references_page = int(re.search(r"\\newlabel\{page:references\}\{\{[^}]*\}\{(\d+)\}", auxiliary).group(1))
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    assert 12 <= references_page - 1 <= 20, "Main text must have 12--20 pages"
    assert re.search(r"^Author:\s+Anonymous\s*$", info, re.M)
    assert "Anonymous Authors" in text
    assert not re.search(r"TODO|TBD|PLACEHOLDER|INSERT RESULTS?", text)
    assert "??" not in text and "undefined references" not in log and "undefined citations" not in log
    assert not re.search(r"Overfull \\[hv]box", log), "Fix overflowing text or floats"
    font_rows = fonts.splitlines()[2:]
    assert font_rows and all(row.split()[-5] == "yes" for row in font_rows)
    assert len(re.findall(r"\\newlabel\{fig:", auxiliary)) == 5
    assert len(re.findall(r"\\newlabel\{tab:", auxiliary)) == 14
    abstract_words = len(Path("paper/generated/abstract.tex").read_text().split())
    assert 150 <= abstract_words <= 250
    report = {"passed": True, "checked_at": utc_now(), "pdf": str(pdf),
              "pdf_sha256": digest_file(pdf), "total_pages": pages,
              "main_pages_including_acknowledgements": references_page - 1,
              "references_start_page": references_page, "abstract_words": abstract_words,
              "figures": 5, "tables": 14, "fonts_embedded": True,
              "anonymous_author_metadata": True, "overfull_boxes": 0,
              "unresolved_references": 0, "generated_inputs_match": True,
              "conference_source": "https://bdcc-conf.eai-conferences.org/2026/call-for-papers/",
              "limitations": "Mechanical validation does not constitute author scientific review, human annotation, PDF accessibility certification, or submission",
              "source_files": {str(path): digest_file(path) for path in
                               [Path("paper/main.tex"), Path("paper/references.bib"),
                                Path("paper/figure_descriptions.md"), *Path("paper/sections").glob("*.tex")]},
              "script_sha256": digest_file(__file__)}
    write_json("artifacts/manifests/manuscript_validation.json", report)
    print(f"Manuscript passed: {references_page-1} main pages, {pages} total, all fonts embedded")


if __name__ == "__main__":
    main()
