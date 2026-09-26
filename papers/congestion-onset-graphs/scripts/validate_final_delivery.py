"""Metadata, transcription and document checks only; no scientific recomputation."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((ROOT/path).read_text())
def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

start=read('manifests/final_test/starting_state.json')
changed=[name for name,expected in start['historical_hashes'].items() if digest(name)!=expected]
assert changed==['README.md'] or set(changed)=={'README.md'},changed
manifest=read('configs/final_test_manifest.json')
for path,record in manifest['files'].items():
    assert (ROOT/path).stat().st_size==record['bytes'] and digest(path)==record['sha256'],path
source=manifest['implementation_commit'];protocol='ceb99eaa23d70a37b82f8d4148505a4d13f2b908'
assert subprocess.check_output(['git','show',protocol+':configs/final_test_manifest.json'],cwd=ROOT)==(ROOT/'configs/final_test_manifest.json').read_bytes()
for path in manifest['source_files']:
    assert subprocess.check_output(['git','show',protocol+':'+path],cwd=ROOT)==(ROOT/path).read_bytes()

trace=read('manuscript/generated/claim_traceability.json')
for r in trace['numeric_macros']:
    value=read(r['artifact'])
    for key in r['pointer'].strip('/').split('/'):value=value[key]
    assert value==r['value'],r
for r in trace['artifact_sources']:assert digest(r['path'])==r['sha256']

raw=read('results/final_test/evaluate/raw_metrics.json')
tex=(ROOT/'manuscript/main.tex').read_text()
# These literal numerical conclusions are formatted directly from GPU outputs.
literal=[]
def claim(value,fmt,artifact,pointer):
    text=format(value,fmt).replace('-0.','-.')
    if text.startswith('0.'):text=text[1:]
    assert text in tex,(text,pointer)
    literal.append(dict(text=text,value=value,artifact=artifact,pointer=pointer))
for contrast in ('C_minus_B','D_minus_C','E_minus_D','E_minus_B'):
    path='/paired/'+contrast+'_onset';r=raw['paired'][contrast+'_onset']
    claim(r['difference'],'.8f','results/final_test/evaluate/raw_metrics.json',path+'/difference')
    for j,v in enumerate(r['3']['bonferroni_family4']):claim(v,'.8f','results/final_test/evaluate/raw_metrics.json',path+'/3/bonferroni_family4/'+str(j))
for contrast in ('B_minus_R_union','D_minus_D_rewire_20261004','E_minus_E_rewire_20261004','E_minus_E_rewire_20261005'):
    path='/secondary_paired/'+contrast+'_onset';r=raw['secondary_paired'][contrast+'_onset']
    # Prose may express an improvement magnitude without a leading minus.
    value=r['difference'];text=format(value,'.8f').replace('-0.','-.');text=text[1:] if text.startswith('0.') else text
    assert text in tex or text.lstrip('-') in tex
    literal.append(dict(text=text,value=value,artifact='results/final_test/evaluate/raw_metrics.json',pointer=path+'/difference'))
for model in ('B','E'):
    for key in ('event_contribution','nonevent_contribution'):
        claim(raw['diagnostics'][model]['onset'][key],'.8f','results/final_test/evaluate/raw_metrics.json','/diagnostics/'+model+'/onset/'+key)

# Map remaining quantitative paragraphs to their exact original design/result sources.
sections={
 'Task and Observation Model':['configs/onset_graph_study.json','reports/STAGE1_DATA_AUDIT.md','manifests/final_test/split_metadata.json'],
 'Predictors and Graph Representations':['configs/onset_graph_study.json','results/onset_graph/study01/main/models_with_nulls.json','results/onset_graph/study01/main/null_graphs.json','src/traffic_risk_twins/onset_graph/graphs.py','src/traffic_risk_twins/onset_graph/models.py'],
 'Experimental Design':['configs/onset_graph_study.json','results/onset_graph/study01/main/split_manifest.json','results/onset_graph/study01/main/anchor_fits.json','results/final_test/preflight/complete.json','results/final_test/replay/complete.json'],
 'Results':['results/final_test/evaluate/raw_metrics.json','results/final_test/evaluate/calibrated_metrics.json','results/onset_graph/study01/main/validation_raw_metrics.json','results/onset_graph/study01/main/information_cost.json','results/final_test/evaluate/historical_cost_summary.json','manifests/final_test/compute_summary.json'],
 'Discussion and Limitations':['results/final_test/evaluate/raw_metrics.json','reports/FINAL_PUBLICATION_AUDIT.md']}
paragraphs=[];section=None
for paragraph in tex.split('\n\n'):
    match=re.search(r'\\section\{([^}]+)\}',paragraph)
    if match:section=match.group(1)
    if re.search(r'\d',paragraph) and section in sections:
        paragraphs.append(dict(paragraph=paragraph,section=section,source_artifacts=sections[section]))
(ROOT/'manuscript/generated/prose_traceability.json').write_text(json.dumps(dict(checked_literal_claims=literal,quantitative_paragraphs=paragraphs),indent=2)+'\n')

# All local report/manuscript Markdown links must resolve. Web links are in the primary-source audit.
link_checks=[]
for path in ['reports/FINAL_TEST_PROTOCOL.md','reports/FINAL_TEST_REPORT.md','reports/FINAL_PUBLICATION_AUDIT.md','manuscript/README.md']:
    for target in re.findall(r'\]\(([^)]+)\)',(ROOT/path).read_text()):
        if '://' in target or target.startswith('#'):continue
        clean=target.split('#')[0];assert (ROOT/path).parent.joinpath(clean).exists(),(path,target)
        link_checks.append(dict(file=path,target=target))
log=(ROOT/'manuscript/build/main.log').read_text()
assert 'Overfull' not in log and 'undefined' not in log and 'LaTeX Warning' not in log
assert tex.isascii()
info=subprocess.check_output(['pdfinfo','manuscript/graph_representations_draft.pdf'],cwd=ROOT,text=True)
assert 'Author:         \n' in info
usage=read('manifests/final_test/compute_summary.json');assert not usage['open_jobs'] and not usage['failed_jobs']
files={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
       for base in ('results/final_test/evaluate','results/final_test/replay','manuscript') for p in (ROOT/base).rglob('*') if p.is_file() and 'build' not in p.parts}
(ROOT/'manifests/final_test/delivery_checks.json').write_text(json.dumps(dict(
    historical_files_changed=changed,historical_reports_results_checkpoints_unchanged=True,
    scientific_source_unchanged_after_test=True,implementation_commit=source,protocol_commit=protocol,
    numeric_transcription_checks=len(trace['numeric_macros'])+len(literal),links=link_checks,
    no_latex_overflows_or_broken_references=True,anonymous_pdf_author=True,pdfinfo=info,
    no_cpu_scientific_checks=True,test_evaluated=True,files=files),indent=2)+'\n')
print('PASS historical preservation, frozen hashes, transcription, links, anonymous PDF and clean compilation')
