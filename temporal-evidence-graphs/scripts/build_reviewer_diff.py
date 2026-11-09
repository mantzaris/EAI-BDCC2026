"""Make a marked, side-by-side PDF against the untouched original submission.

Run from the project root with PyMuPDF in the tooling environment, for example:
  PYTHONPATH=/tmp/teg-pdf-diff-tools python3 scripts/build_reviewer_diff.py
This tool does not change either input PDF or any manuscript source.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import hashlib
import json
import re
import unicodedata

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
RED = (0.72, 0.10, 0.13)
BLUE = (0.05, 0.27, 0.76)
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class Word:
    text: str
    boxes: list


def words(document):
    result = []
    for number, page in enumerate(document):
        raw = [w for w in page.get_text("words", sort=True)
               if number == 0 or w[3] > 105]  # Ignore repeated running heads.
        i = 0
        while i < len(raw):
            word = raw[i]
            value = unicodedata.normalize("NFKC", word[4]).replace("\u00ad", "")
            boxes = [(number, fitz.Rect(word[:4]))]
            # Normalize line-break hyphenation, retaining both highlight boxes.
            if (value.endswith("-") and i + 1 < len(raw)
                    and raw[i + 1][1] > word[1] + 2
                    and raw[i + 1][4][:1].islower()):
                i += 1
                value = value[:-1] + unicodedata.normalize("NFKC", raw[i][4])
                boxes.append((number, fitz.Rect(raw[i][:4])))
            result.append(Word(value, boxes))
            i += 1
    return result


def highlight(document, tokens, changed, color, deleted):
    by_page = defaultdict(list)
    for index in changed:
        for page, box in tokens[index].boxes:
            by_page[page].append(box)
    for number, boxes in by_page.items():
        page = document[number]
        fills, strokes = page.new_shape(), page.new_shape()
        for box in boxes:
            fills.draw_rect(box)
            y = (box.y0 + box.y1) / 2 if deleted else box.y1 - 1
            strokes.draw_line((box.x0, y), (box.x1, y))
        fills.finish(color=None, fill=color, fill_opacity=0.12)
        fills.commit(overlay=False)
        strokes.finish(color=color, width=0.45)
        strokes.commit()


def form_positions(page):
    """Locate figure form objects in the pdfTeX page content stream."""
    forms = {x[1]: fitz.Rect(x[3]) for x in page.get_xobjects() if x[2] == 0}
    source = page.read_contents().decode("latin1")
    while re.search(r"\((?:\\.|[^\\()])*\)", source):
        source = re.sub(r"\((?:\\.|[^\\()])*\)", " ", source)
    source = re.sub(r"<[^<>]*>", " ", source)
    tokens = re.findall(r"/[A-Za-z0-9]+|[-+]?(?:\d*\.\d+|\d+)|[A-Za-z*']+", source)
    matrix = fitz.Matrix(1, 0, 0, 1, 0, 0)
    stack, operands, result = [], [], []
    for token in tokens:
        if token.startswith("/"):
            operands.append(token[1:])
            continue
        try:
            operands.append(float(token))
            continue
        except ValueError:
            pass
        if token == "q":
            stack.append(fitz.Matrix(matrix))
        elif token == "Q" and stack:
            matrix = stack.pop()
        elif token == "cm":
            matrix = fitz.Matrix(*operands[-6:]) * matrix
        elif token == "Do" and operands and operands[-1] in forms:
            box = forms[operands[-1]] * matrix * page.transformation_matrix
            result.append(box & page.rect)
        operands = []
    return result


def figure_assets(source_path):
    source = source_path.read_text()
    names = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", source)
    result = []
    for name in names:
        choices = [PAPER / name, ROOT / "artifacts/figures" / name]
        match = next((p for p in choices if p.exists()), None)
        if match is None:
            raise FileNotFoundError(name)
        result.append(match)
    return result


def frame_changed_figures(document, assets, other_assets, color):
    positions = [(i, box) for i, page in enumerate(document) for box in form_positions(page)]
    if len(positions) != len(assets):
        raise ValueError(f"Figure count mismatch: {len(positions)} forms vs {len(assets)} assets")
    other_hashes = {digest(p) for p in other_assets}
    count = 0
    for asset, (number, box) in zip(assets, positions):
        if digest(asset) not in other_hashes:
            document[number].draw_rect(box, color=color, width=1)
            count += 1
    return count


def text(page, x, y, value, size=11, color=(0.12, 0.15, 0.20)):
    page.insert_font(fontname="review", fontfile=str(FONT))
    page.insert_text((x, y), value, fontname="review", fontsize=size, color=color)


def main():
    old_path = PAPER / "semantic_structure_revision.pdf"
    new_path = PAPER / "semantic_structure_revision_camera_ready.pdf"
    old_hash, new_hash = digest(old_path), digest(new_path)
    old, new = fitz.open(old_path), fitz.open(new_path)
    a, b = words(old), words(new)
    matcher = SequenceMatcher(None, [w.text for w in a], [w.text for w in b], autojunk=False)
    removed, added = [], []
    for operation, i, j, k, l in matcher.get_opcodes():
        if operation in {"delete", "replace"}:
            removed.extend(range(i, j))
        if operation in {"insert", "replace"}:
            added.extend(range(k, l))
    highlight(old, a, removed, RED, True)
    highlight(new, b, added, BLUE, False)
    old_assets = figure_assets(PAPER / "main.tex")
    new_assets = figure_assets(PAPER / "main_camera_ready.tex")
    old_figures = frame_changed_figures(old, old_assets, new_assets, RED)
    new_figures = frame_changed_figures(new, new_assets, old_assets, BLUE)

    output = fitz.open()
    cover = output.new_page(width=612, height=792)
    for y, value, size in [
        (65, "EAI BDCC 2026", 13),
        (105, "Original submission / revised paper", 20),
        (138, "Marked comparison — for review, not conference upload.", 11),
        (190, f"Left: original submission ({len(old)} pages).", 12),
        (215, f"Right: revised camera-ready manuscript ({len(new)} pages).", 12),
        (265, "Red shading and strike-through: deleted or replaced words.", 11),
        (290, "Blue shading and underline: added or replacement words.", 11),
        (315, "Colored figure frames: removed/replaced or added figure assets.", 11),
        (365, "Words are matched across the complete documents.", 11),
        (390, "Pages are paired by page number; passages can move between pages.", 11),
        (415, "Relocated wording may appear as a deletion and an addition.", 11),
        (440, "Running heads and line-break hyphenation are ignored.", 11),
        (465, "Equations, tables, figures and page layouts retain their PDF appearance.", 11),
        (530, "Use the separate clean camera-ready PDF for submission.", 12),
        (600, "Original SHA-256: " + old_hash[:24], 9),
        (620, "Revised SHA-256: " + new_hash[:24], 9),
    ]:
        text(cover, 48, y, value, size)
    outline = [[1, "Comparison guide", 1]]
    for i in range(max(len(old), len(new))):
        page = output.new_page(width=1284, height=852)
        text(page, 24, 25, f"ORIGINAL SUBMISSION — page {i + 1}", 12, RED)
        text(page, 660, 25, f"REVISED PAPER — page {i + 1}", 12, BLUE)
        for document, x in [(old, 18), (new, 654)]:
            if i < len(document):
                page.show_pdf_page(fitz.Rect(x, 38, x + 612, 830), document, i)
            else:
                text(page, x + 50, 130, "No corresponding source page.", 12)
        page.draw_line((642, 38), (642, 830), color=(0.75, 0.77, 0.8), width=.5)
        text(page, 24, 843, "Red: removed/replaced. Blue: added/replacement. Page pairing is positional.", 9)
        outline.append([1, f"Original / revised page {i + 1}", i + 2])
    output.set_toc(outline)
    output.set_metadata({"title": "Original submission / revised paper: marked comparison",
                         "author": new.metadata.get("author", ""),
                         "subject": "Review copy, not for conference submission"})
    target = PAPER / "semantic_structure_revision_camera_ready_diff.pdf"
    output.save(target, garbage=4, deflate=True)
    output.close()
    # Reopen after garbage collection, which may renumber in-memory xrefs.
    with fitz.open(target) as checked:
        assert len(checked) == max(len(old), len(new)) + 1
        for page in checked:
            assert page.get_text().strip()
            page.get_pixmap(matrix=fitz.Matrix(.25, .25))
    assert digest(old_path) == old_hash and digest(new_path) == new_hash
    print(json.dumps({"output": str(target.relative_to(ROOT)),
                      "old_words": len(a), "new_words": len(b),
                      "deleted_or_replaced_words": len(removed), "added_or_replacement_words": len(added),
                      "old_changed_figures": old_figures, "new_changed_figures": new_figures,
                      "input_pdfs_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
