"""Verify the complete main.tex and its unchanged, independently buildable PDF.

The comparison baseline is the completed prose revision at 9543daf. A clean
temporary build receives only main.tex, llncs.cls and the six figure PDFs.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
BASE = "9543daf"
PREFIX = PROJECT.name + "/"
INPUT = re.compile(r"\\input\{([^}]+)\}")


def run(*args, cwd=PROJECT):
    return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.STDOUT)


def old(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{PREFIX}{path}"], cwd=PROJECT)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def normalize(text):
    # Ignore provenance comments and source-file whitespace, not TeX commands.
    # LaTeX's former input boundaries added a space after each generated table.
    text = text.replace("\\space% Preserve the former table-input boundary.", "")
    text = re.sub(r"(?<!\\)%[^\n]*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    source = (PROJECT / "paper/main.tex").read_text()
    assert not re.search(r"\\(?:input|include|bibliography|bibliographystyle)\s*\{", source)
    inlined = []

    def expand(text):
        def replace(match):
            path = "paper/" + match[1] + ("" if match[1].endswith(".tex") else ".tex")
            inlined.append(path)
            return expand(old(path).decode())
        return INPUT.sub(replace, text)

    expected = expand(old("paper/main.tex").decode())
    expected = re.sub(r"\\bibliographystyle\{[^}]+\}|\\bibliography\{[^}]+\}", "", expected)
    without_bibliography = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "", source, flags=re.S)
    assert normalize(expected) == normalize(without_bibliography), "Manuscript content changed"
    assert len(re.findall(r"\\bibitem\{", source)) == 13
    protected = ("artifacts", "src", "paper/sections", "paper/generated", "paper/template", "paper/references.bib")
    assert not run("git", "diff", "--name-only", BASE, "--", *protected), "Scientific inputs changed"
    assert not run("git", "ls-files", "--others", "--exclude-standard", "--", "artifacts").strip()

    pdf = PROJECT / "paper/semantic_structure_revision.pdf"
    figures = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", source)
    assert len(figures) == 6
    with tempfile.TemporaryDirectory(prefix="teg_complete_tex_") as name:
        temp = Path(name)
        before = temp / "before.pdf"
        before.write_bytes(old("paper/semantic_structure_revision.pdf"))
        paper = temp / "paper"
        paper.mkdir()
        shutil.copy(PROJECT / "paper/main.tex", paper / "main.tex")
        shutil.copy(PROJECT / "paper/template/llncs.cls", paper / "llncs.cls")
        for figure in figures:
            target = temp / "artifacts/figures" / figure
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(PROJECT / "artifacts/figures" / figure, target)
        for _ in range(2):
            run("pdflatex", "-recorder", "-interaction=nonstopmode", "-halt-on-error", "main.tex", cwd=paper)
        isolated = paper / "main.pdf"
        assert not list(paper.glob("*.bbl")), "Clean build unexpectedly used BibTeX"
        log = (paper / "main.log").read_text()
        assert not re.search(r"Overfull \\[hv]box|Float too large|undefined references|undefined citations", log)
        aux = (paper / "main.aux").read_text()
        refs = int(re.search(r"\\newlabel\{page:references\}\{\{[^}]*\}\{(\d+)\}", aux)[1])
        info = run("pdfinfo", str(isolated))
        pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1])
        assert (refs - 1, pages - refs + 1) == (20, 1)
        texts = [run("pdftotext", "-layout", str(p), "-") for p in (before, pdf, isolated)]
        assert texts[0] == texts[1], "Published layout differs from the baseline"
        assert texts[1] == texts[2], "Clean build differs from the published layout"
        fonts = run("pdffonts", str(isolated)).splitlines()[2:]
        assert fonts and all(line.split()[-5] == "yes" for line in fonts)
        renders = []
        for label, document in (("before", before), ("current", pdf), ("isolated", isolated)):
            directory = temp / label
            directory.mkdir()
            run("pdftoppm", "-r", "144", "-png", str(document), str(directory / "page"))
            hashes = [digest(p) for p in sorted(directory.glob("page-*.png"))]
            assert len(hashes) == pages
            renders.append(hashes)
        assert renders[0] == renders[1] == renders[2], "Rendered page pixels changed"

    report = {
        "passed": True,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": run("git", "rev-parse", BASE).strip(),
        "main_tex_sha256": digest(PROJECT / "paper/main.tex"),
        "pdf_sha256": digest(pdf),
        "checker_sha256": digest(__file__),
        "inlined_sources": inlined,
        "bibliography_entries": 13,
        "main_pages": 20,
        "reference_pages": 1,
        "manuscript_content_unchanged": True,
        "scientific_inputs_unchanged": True,
        "external_latex_content_inputs": 0,
        "preserved_table_boundary_spaces": 3,
        "clean_build_inputs": ["main.tex", "llncs.cls", *figures],
        "clean_build_command": "pdflatex -recorder -interaction=nonstopmode -halt-on-error main.tex (twice)",
        "rendered_text_equal": True,
        "rendered_pixels_equal": True,
        "comparison_dpi": 144,
        "page_image_sha256": renders[0],
        "fonts_embedded": True,
        "overfull_boxes": 0,
        "oversized_floats": 0,
        "unresolved_references": 0,
    }
    output = PROJECT / "paper/source_consolidation/validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("Passed: complete main.tex; 20 main + 1 reference pages; all 21 pages pixel-identical at 144 dpi.")
    print("Clean build needs only main.tex, the official class and six figure PDFs. Scientific inputs unchanged.")


if __name__ == "__main__":
    main()
