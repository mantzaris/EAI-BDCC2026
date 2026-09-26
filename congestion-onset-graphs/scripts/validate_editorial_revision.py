"""Check document transcription and plot preservation, without scientific recomputation.

Run after render_final_manuscript.py and make -C manuscript. The historical
validator and its delivery receipt remain unchanged. This check reads saved
statistics and inspects plotting coordinates, source bytes and PDF metadata.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = Path(subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip())
REVIEWED = '09af231f3d8407ff5342f5b91292d8c4f18b76eb'
RAW = 'results/final_test/evaluate/raw_metrics.json'


def read(path):
    return json.loads((ROOT / path).read_text())


def prior(path):
    return subprocess.check_output(['git', 'show', f'{REVIEWED}:{path}'], cwd=ROOT)


def pointer(document, path):
    for key in path.strip('/').split('/'):
        document = document[int(key)] if isinstance(document, list) else document[key]
    return document


tex = (ROOT / 'manuscript/main.tex').read_text()
assert tex.isascii()
assert tex.count(r'\includegraphics') == 4
assert r'\author{Anonymous submission}' in tex
trace = read('manuscript/generated/claim_traceability.json')
for record in trace['numeric_macros']:
    assert pointer(read(record['artifact']), record['pointer']) == record['value']
for record in trace['artifact_sources']:
    assert hashlib.sha256((ROOT / record['path']).read_bytes()).hexdigest() == record['sha256']

# Document-only rounding. Full source values and historical prose records survive.
raw = read(RAW)
literals = []


def literal(path, precision=7, magnitude=False):
    value = pointer(raw, path)
    display = format(abs(value) if magnitude else value, f'.{precision}f')
    display = display.replace('-0.', '-.')
    if display.startswith('0.'):
        display = display[1:]
    assert display in tex, (path, display)
    literals.append(dict(artifact=RAW, pointer=path, value=value, displayed=display))


for contrast in ('C_minus_B', 'D_minus_C', 'E_minus_D', 'E_minus_B'):
    base = '/paired/' + contrast + '_onset'
    literal(base + '/difference')
    for index in range(2):
        literal(base + '/3/bonferroni_family4/' + str(index))
for index in range(2):
    literal('/paired/D_minus_C_onset/3/pointwise_95/' + str(index))
for contrast in ('B_minus_R_union', 'D_minus_D_rewire_20261004',
                 'E_minus_E_rewire_20261004', 'E_minus_E_rewire_20261005'):
    base = '/secondary_paired/' + contrast + '_onset'
    literal(base + '/difference', magnitude=True)
    for index in range(2):
        literal(base + '/3/pointwise_95/' + str(index))
for model in ('B', 'E'):
    for component in ('event_contribution', 'nonevent_contribution'):
        literal(f'/diagnostics/{model}/onset/{component}', precision=5)
for model in ('B', 'C', 'D', 'E'):
    path = f'/diagnostics/{model}/onset/zero_fraction'
    value = pointer(raw, path)
    display = format(value, '.1%').replace('%', r'\%')
    assert display in tex
    literals.append(dict(artifact=RAW, pointer=path, value=value, displayed=display))

# Execute only the existing plotting statements, intercepting exports. No metric
# calculation, result writes, fitting, inference or bootstrap code is executed.
def plotted_coordinates(source):
    snippet = source[source.index('plt.rcParams.update'):source.index('# Conceptual')]
    tree = ast.parse(snippet)
    tree.body = [node for node in tree.body
                 if not isinstance(node, ast.FunctionDef) or node.name != 'export']
    figures = {}

    def capture(fig, name):
        axes = []
        for axis in fig.axes:
            axes.append(dict(
                xlim=list(axis.get_xlim()), ylim=list(axis.get_ylim()),
                xlabel=axis.get_xlabel(), ylabel=axis.get_ylabel(),
                title=axis.get_title(), tick_labels=[t.get_text() for t in axis.get_yticklabels()],
                lines=[dict(x=list(line.get_xdata()), y=list(line.get_ydata()),
                            color=line.get_color(), marker=line.get_marker(),
                            style=line.get_linestyle(), width=line.get_linewidth(),
                            alpha=line.get_alpha()) for line in axis.lines]))
        figures[name] = axes
        plt.close(fig)

    namespace = dict(plt=plt, FuncFormatter=FuncFormatter, export=capture,
                     raw=raw, cal=read('results/final_test/evaluate/calibrated_metrics.json'),
                     val=read('results/onset_graph/study01/main/validation_raw_metrics.json'),
                     null=read('results/onset_graph/study01/main/topology_metrics.json'))
    exec(compile(tree, '<plot-only preservation check>', 'exec'), namespace)
    return figures


old = plotted_coordinates(prior('scripts/render_final_manuscript.py').decode())
new = plotted_coordinates((ROOT / 'scripts/render_final_manuscript.py').read_text())
assert old == new, 'A plotted coordinate, interval, direction, label or style changed'
assert set(new) == {'effects', 'topology', 'alarms'}

# Compare historical blobs with the paper's current files, independent of its
# location within the repository. Older revisions used the repository root.
protected = ('results', 'manifests', 'configs', 'artifacts', 'src', 'tests')
historical_files = subprocess.check_output(
    ['git', 'ls-tree', '-r', '-z', REVIEWED, '--', *protected], cwd=REPOSITORY)
for entry in historical_files.split(b'\0'):
    if not entry:
        continue
    metadata, path = entry.split(b'\t', 1)
    _, kind, expected = metadata.split()
    assert kind == b'blob', path
    contents = (ROOT / path.decode()).read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(contents)).encode() + b'\0' + contents).hexdigest()
    assert actual == expected.decode(), path
historical_reports = subprocess.check_output(
    ['git', 'ls-tree', '-r', '--name-only', REVIEWED, '--', 'reports'], cwd=REPOSITORY, text=True).splitlines()
for path in historical_reports:
    assert prior(path) == (ROOT / path).read_bytes(), path
for name in ('llncs.cls', 'splncs04.bst'):
    path = 'manuscript/template/' + name
    assert prior(path) == (ROOT / path).read_bytes(), path
for name in ('costs.tex', 'numbers.tex', 'scores.tex', 'seeds.tex', 'prose_traceability.json'):
    path = 'manuscript/generated/' + name
    assert prior(path) == (ROOT / path).read_bytes(), path

log = (ROOT / 'manuscript/build/main.log').read_text()
assert not any(term in log for term in ('Overfull', 'undefined', 'LaTeX Warning'))
info = subprocess.check_output(['pdfinfo', 'manuscript/graph_representations_draft.pdf'], cwd=ROOT, text=True)
assert re.search(r'^Author:\s*$', info, re.M)
pdf_text = subprocess.check_output(['pdftotext', '-layout', 'manuscript/graph_representations_draft.pdf', '-'], cwd=ROOT, text=True)
pages = [page for page in pdf_text.split('\f') if page.strip()]
reference_page = next(i for i, page in enumerate(pages, 1) if re.search(r'^References\s*$', page, re.M))
appendix_page = next(i for i, page in enumerate(pages, 1) if 'Per-Seed Onset Results' in page)
receipt = dict(
    reviewed_delivery=REVIEWED, scope='CPU document and figure checks only; no new experiments',
    full_precision_macros_checked=len(trace['numeric_macros']), rounded_prose_claims=literals,
    identical_plot_coordinates_intervals_axes_styles=list(new),
    scientific_artifacts_and_historical_reports_unchanged=True, official_template_unchanged=True,
    original_detailed_costs_scores_seeds_and_prose_traceability_unchanged=True,
    total_pages=len(pages), main_text_ends_page=reference_page,
    references_start_page=reference_page, appendix_page=appendix_page,
    latex_no_overflows_or_unresolved_references=True, anonymous=True,
    pdf_sha256=hashlib.sha256((ROOT / 'manuscript/graph_representations_draft.pdf').read_bytes()).hexdigest(),
    visual_inspection_record='manuscript/EDITORIAL_REVISION.md')
(ROOT / 'manuscript/generated/editorial_checks.json').write_text(json.dumps(receipt, indent=2) + '\n')
for path in ('manuscript/README.md', 'manuscript/EDITORIAL_REVISION.md'):
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT / path).read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (ROOT / path).parent.joinpath(target.split('#')[0]).exists(), (path, target)
print(f'PASS: preserved plot data, {len(literals)} rounded prose claims, {len(pages)} pages, frozen science unchanged')
