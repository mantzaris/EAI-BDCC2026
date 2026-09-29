"""Check the prose revision without rerunning or rewriting experimental analysis.

The comparison uses the completed c62001f paper as its immutable baseline. The
report describes mechanical preservation checks, not an automated proof that two
texts have the same scientific meaning. That comparison also requires review.
"""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import subprocess
import tempfile

PROJECT=Path(__file__).resolve().parents[1]
REPO=PROJECT.parent
PREFIX=PROJECT.name+'/'
BASE='c62001f'
OUT=PROJECT/'paper/prose_revision/validation.json'
PROSE_FILES={'paper/generated/semantic/'+n+'.tex' for n in ('abstract','worked_example','temporal_denominators')}


def command(*args,cwd=PROJECT):
    return subprocess.check_output(args,cwd=cwd,text=True)


def old_bytes(path):
    return subprocess.check_output(['git','show',BASE+':'+PREFIX+path],cwd=REPO)


def digest(data):return sha256(data).hexdigest()


def read_sources(baseline=False):
    found={}
    def visit(path):
        if path in found:return
        text=(old_bytes(path).decode() if baseline else (PROJECT/path).read_text())
        found[path]=text
        for name in re.findall(r'\\input\{([^}]+)\}',text):
            visit('paper/'+name+('' if name.endswith('.tex') else '.tex'))
    visit('paper/main.tex')
    return found


def word_count(sources):
    with tempfile.TemporaryDirectory(prefix='teg_prose_count_') as temp:
        for name,text in sources.items():
            target=Path(temp)/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
        output=command('texcount','-inc','-sum','main.tex',cwd=Path(temp)/'paper').split('Sum of files:')[-1]
    body=int(re.search(r'Words in text: (\d+)',output).group(1))
    captions=int(re.search(r'Words outside text \(captions, etc.\): (\d+)',output).group(1))
    return {'body':body,'captions':captions,'prose':body+captions}


def punctuation(sources):
    text='\n'.join(sources.values())
    text=re.sub(r'(?m)^%.*','',text)
    text=re.sub(r'\\begin\{(equation|tabularx?)\}.*?\\end\{\1\}','',text,flags=re.S)
    text=re.sub(r'\$.*?\$|\\\[.*?\\\]','',text,flags=re.S)
    # Remove technical command arguments, including label names with colons.
    text=re.sub(r'\\[A-Za-z]+(?:\[[^]]*\])?\{[^{}]*\}','',text)
    return {'semicolons':text.count(';'),'colons':text.count(':'),'sentence_dashes':len(re.findall(r'---|—|\s[–-]\s',text))}


def main():
    os.chdir(PROJECT)
    before=read_sources(True);after=read_sources()
    assert before.keys()==after.keys(),'Manuscript inputs changed'
    checks={}
    patterns={
        'equations':r'\\begin\{equation\}.*?\\end\{equation\}',
        'proposition_statements':r'\\begin\{proposition\}.*?\\end\{proposition\}',
        'section_structure':r'\\(?:section|subsection|paragraph)\{[^}]*\}',
        'figure_inclusions':r'\\includegraphics(?:\[[^]]*\])?\{[^}]*\}',
    }
    for label,pattern in patterns.items():
        total=0
        for name in before:
            old,new=re.findall(pattern,before[name],re.S),re.findall(pattern,after[name],re.S)
            assert old==new,(label,name)
            total+=len(old)
        checks[label]={'unchanged':True,'count':total}
    for label,pattern in (
        ('numerical_literals',r'(?<![A-Za-z])\d+(?:[.,]\d+)*'),
        ('result_macro_uses',r'\\(?:Sem|View|Classic|Systems)[A-Za-z]+'),
        ('citations',r'\\cite\{[^}]+\}')):
        total=0
        for name in before:
            a,b=Counter(re.findall(pattern,before[name])),Counter(re.findall(pattern,after[name]))
            assert a==b,(label,name,a-b,b-a)
            total+=sum(a.values())
        checks[label]={'unchanged':True,'count':total}
    unchanged={}
    for name in after:
        if name.startswith('paper/generated/') and name not in PROSE_FILES:
            assert before[name]==after[name],('generated mathematics/table/macros changed',name)
            unchanged[name]=digest(after[name].encode())
    for name in ('paper/main.tex','paper/references.bib'):
        assert old_bytes(name)==Path(name).read_bytes(),name
    assert not command('git','diff','--name-only',BASE,'--','paper/template','artifacts'), 'Template or experimental artifacts changed'
    assert not command('git','ls-files','--others','--exclude-standard','--','artifacts').strip(), 'New experimental artifacts'
    assert command('git','diff','--name-only',BASE,'--','src').splitlines()==[PREFIX+'src/temporal_evidence/semantic/publication.py']
    manifest=json.loads(Path('paper/generated/semantic/manifest.json').read_text())
    for group in ('inputs','generated_tex','generated_docs'):
        for path,expected in manifest[group].items():assert digest(Path(path).read_bytes())==expected,path
    assert manifest['script_sha256']==digest(Path('src/temporal_evidence/semantic/publication.py').read_bytes())
    old_count,new_count=word_count(before),word_count(after)
    percent=100*(new_count['prose']/old_count['prose']-1)
    assert abs(percent)<=5,percent
    pdf='paper/semantic_structure_revision.pdf'
    info=command('pdfinfo',pdf);pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
    aux=Path('paper/build/main.aux').read_text()
    refs=int(re.search(r'\\newlabel\{page:references\}\{\{[^}]*\}\{(\d+)\}',aux).group(1))
    assert (refs-1,pages-refs+1)==(20,1),(refs,pages)
    log=Path('paper/build/main.log').read_text()
    assert not re.search(r'Overfull \\[hv]box|Float too large|undefined references|undefined citations',log)
    text=command('pdftotext',pdf,'-')
    assert '??' not in text
    fonts=command('pdffonts',pdf).splitlines()[2:]
    assert fonts and all(line.split()[-5]=='yes' for line in fonts)
    assert not re.search(r'\bsupplement(?:ary)?\b',text,re.I)
    report={'passed':True,'baseline_commit':command('git','rev-parse',BASE).strip(),
        'checked_at':datetime.now(timezone.utc).isoformat(),'main_pages':refs-1,'reference_pages':pages-refs+1,
        'pdf':pdf,'pdf_sha256':digest(Path(pdf).read_bytes()),'before_words':old_count,'after_words':new_count,
        'prose_word_change_percent':round(percent,3),
        'word_count_definition':'TeXcount body text plus captions; excludes headers, equations, table cells, figure labels and references; macros are not expanded.',
        'punctuation_before':punctuation(before),'punctuation_after':punctuation(after),
        'preservation_checks':checks,'unchanged_generated_files':unchanged,
        'template_unchanged':True,'experimental_artifact_tree_unchanged':True,'inference_calls':0,
        'fonts_embedded':True,'overfull_boxes':0,'oversized_floats':0,'unresolved_references':0,
        'source_hashes':{name:digest(text.encode()) for name,text in after.items()},
        'generator_sha256':manifest['script_sha256'],'checker_sha256':digest(Path(__file__).read_bytes()),
        'manual_review':'Scientific meaning and final PDF pages reviewed separately in PROSE_REVISION.md and paper/semantic_visual_review.md.'}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(f'Passed: {refs-1} main + {pages-refs+1} reference pages; prose {old_count["prose"]} -> {new_count["prose"]} ({percent:+.2f}%).')
    print('Equations, propositions, numbers, citations, figures, generated result tables and all experimental artifacts unchanged.')


if __name__=='__main__':main()
