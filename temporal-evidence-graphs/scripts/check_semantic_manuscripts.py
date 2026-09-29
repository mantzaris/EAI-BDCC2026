"""Validate the single paper, frozen studies and shared database review views."""
from collections import Counter
from pathlib import Path
import ast
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zlib
from temporal_evidence.io import read_json,write_json,digest_file,digest_object,utc_now
from temporal_evidence.study import verify_frozen
from temporal_evidence.semantic.export import read_export
from temporal_evidence.semantic.ontology import validate_export
from temporal_evidence.semantic.projection import records
from temporal_evidence.semantic.review_view import validate_view
from temporal_evidence.semantic.network_examples import make_views
from temporal_evidence.semantic.network_render import drawing_objects,render_bytes
from temporal_evidence.dashboard.network_panel import load_published

DATA=Path("artifacts/analysis/semantic_analysis_v1")
RUN=Path("artifacts/runs/structure_study_v1")
VIEWS=Path("artifacts/analysis/review_views_v1")
FIGURES=Path("artifacts/figures/semantic_analysis_v1")

def hashes(values):
    for path,expected in values.items():assert digest_file(path)==expected,("stale input",path)

def command(*args):return subprocess.check_output(args,text=True)

def pdf_link_present(path,target):
    # pdfTeX may place remote-link actions in compressed PDF object streams.
    raw=Path(path).read_bytes();chunks=[raw]
    for stream in re.findall(rb"stream\r?\n(.*?)\r?\nendstream",raw,re.S):
        try:chunks.append(zlib.decompress(stream))
        except zlib.error:pass
    return any(target.encode() in chunk or target.encode("utf-16be") in chunk for chunk in chunks)

def pdf_check(filename,stem):
    info=command("pdfinfo",filename);text=command("pdftotext","-layout",filename,"-")
    log=Path("paper/build",stem+".log").read_text()
    fonts=command("pdffonts",filename).splitlines()[2:]
    assert fonts and all(r.split()[-5]=="yes" for r in fonts)
    assert not re.search(r"Overfull \\[hv]box|undefined references|undefined citations",log)
    assert "??" not in text and not re.search(r"\b(?:TODO|TBD|INSERT RESULTS)\b",text)
    pages=int(re.search(r"^Pages:\s+(\d+)",info,re.M).group(1))
    return {"pdf":filename,"sha256":digest_file(filename),"pages":pages,"fonts_embedded":True,
        "overfull_boxes":0,"unresolved_references":0}

def review_views_check():
    registry=read_json(VIEWS/"manifest.json");hashes(registry["source_hashes"])
    assert registry["new_gpu_calls"]==0
    generated=read_json("paper/generated/review_views/manifest.json")
    hashes(generated["inputs"])
    assert digest_file("paper/generated/review_views/macros.tex")==generated["macros_sha256"]
    live=read_json(VIEWS/"live_database_validation.json")
    real=read_json(VIEWS/"live_wesad/manifest.json")["scopes"][0]
    structural=read_json(VIEWS/"exports/manifest.json")["scopes"][0]
    assert live["read_only"] and live["inference_calls"]==0
    assert live["real_sha256"]==real["sha256"] and live["structural_sha256"]==structural["sha256"]
    assert digest_file(DATA/"exports"/real["file"])==real["sha256"]
    assert live["live_export_equal_to_published_source"]
    assert (real["nodes"],real["edges"])==(live["real_nodes"],live["real_edges"])
    assert [structural["nodes"],structural["edges"]]==live["structural_counts_verified"]
    # Networks are included at \textwidth in the unmodified official template.
    cls=Path("paper/template/llncs.cls").read_text()
    width_cm=float(re.search(r"\\setlength\{\\textwidth\}\{([\d.]+)cm\}",cls).group(1))
    results=[]
    for entry in registry["examples"]:
        config=read_json(entry["config_path"]);graph=read_export(config["export"])
        before,view=make_views(config)
        ui,layout=load_published(entry["key"])
        assert digest_object(view)==digest_object(ui)==entry["view_sha256"]
        assert layout["union_view_hashes"]==[digest_object(before),digest_object(view)]
        for state,obj in (("before",before),("after",view)):
            assert digest_object(obj)==digest_object(read_json(VIEWS/entry["key"]/(state+".json")))
            validate_view(obj,graph)
            assert not obj["budget"]["partial"] and not obj["budget"]["incomplete_witness_groups"]
        source=view["source"]
        assert source["export_sha256"]==digest_file(config["export"])
        for key in ("candidate_path","replay_path"):
            if key in source:assert digest_file(source[key]["path"])==source[key]["sha256"]
        base=FIGURES/config["figure"]
        manifest=read_json(base.with_suffix(".manifest.json"))
        assert manifest["view_sha256"]==digest_object(view)
        assert render_bytes(ui,layout,"svg")==base.with_suffix(".svg").read_bytes()
        drawing=drawing_objects(view)
        assert manifest["drawing_objects"]==json.loads(json.dumps(drawing))
        covered=set()
        for edge in drawing["edges"]:
            assert edge["label"]
            covered.update(edge["witness_edge_ids"])
            if not edge["directly_stored"]:
                assert edge["type"]=="WITNESS_INPUT_BUNDLE"
                assert edge["witness_group"] in {w["id"] for w in view["witness_groups"]}
        assert covered=={e["id"] for e in view["edges"]}
        info=command("pdfinfo",str(base.with_suffix(".pdf")))
        width=float(re.search(r"Page size:\s+([\d.]+) x",info).group(1))
        min_font=layout["edge_font_size"]*(width_cm/2.54*72)/width
        assert min_font>=9,(config["figure"],min_font)
        results.append({"key":entry["key"],"scope":view["scope"],"nodes":len(view["nodes"]),"edges":len(view["edges"]),
            "view_sha256":digest_object(view),"svg_matches_dashboard":True,"minimum_printed_font_points":round(min_font,2),
            "knowledge_times":[before["knowledge_time"],view["knowledge_time"]]})
    return results

def classic_network_check():
    from temporal_evidence.semantic.classic_example import prepare, ROOT, FIGURE
    from temporal_evidence.semantic.classic_render import render_bytes as classic_render
    from temporal_evidence.dashboard.network_panel import load_classic
    manifest=read_json(ROOT/'manifest.json')
    for key in ('source_hashes','code_hashes','figure_hashes'):hashes(manifest[key])
    assert manifest==read_json(FIGURE.with_suffix('.manifest.json'))
    assert manifest['new_gpu_calls']==0 and not manifest['visible_derived_edges']
    assert digest_file(ROOT/'analysis.json')==manifest['analysis_sha256']
    config,analysis,views=prepare()
    assert digest_object(analysis)==digest_object(read_json(ROOT/'analysis.json'))
    graph=read_export(config['export']);layout=read_json(ROOT/'layout.json')
    assert layout==manifest['layout']
    assert not layout['node_collisions'] and not layout['routing_issues']
    assert layout['edge_node_intersections']==layout['label_collisions']==0
    for label,view in zip(('before','after'),views):
        ui,positions=load_classic(label)
        validate_view(ui,graph)
        assert digest_object(view)==digest_object(ui)==manifest['views'][label]['sha256']
        assert classic_render(ui,positions,'svg')==(ROOT/(label+'.svg')).read_bytes()
    assert classic_render(views[-1],layout,'svg')==FIGURE.with_suffix('.svg').read_bytes()
    assert 10<=len(views[-1]['nodes'])<=20
    assert all(e['directly_stored'] for e in views[-1]['edges'])
    assert set(manifest['selected_record_ids'])=={n['id'] for n in views[-1]['nodes']}
    assert set(manifest['stored_edge_ids'])=={e['id'] for e in views[-1]['edges']}
    generated=read_json('paper/generated/classic_network/manifest.json')
    for key in ('inputs','generated_tex'):hashes(generated[key])
    width=float(re.search(r'Page size:\s+([\d.]+) x',command('pdfinfo',str(FIGURE.with_suffix('.pdf')))).group(1))
    printed_font=min(layout['font_size'],layout['edge_font_size'])*(12.2/2.54*72)/width
    assert printed_font>=9-1e-5
    browser=read_json(ROOT/'dashboard_validation.json');hashes(browser['artifacts'])
    assert browser['script_sha256']==digest_file('scripts/capture_classic_dashboard.mjs')
    assert browser['view_sha256']==digest_file(ROOT/'after.json') and browser['noException']
    assert browser['record_nodes']==len(views[-1]['nodes'])
    return {'case':manifest['case_id'],'scope':manifest['scope'],
        'nodes':len(views[-1]['nodes']),'edges':len(views[-1]['edges']),
        'support':analysis['support'],'set_counts':{k:len(v) for k,v in analysis['sets'].items()},
        'exposure':analysis['exposure'],'minimum_printed_font_points':round(printed_font,2),
        'svg_matches_dashboard':True,'manifest_sha256':digest_file(ROOT/'manifest.json'),
        'browser_validation_sha256':digest_file(ROOT/'dashboard_validation.json')}

def main():
    minimum=read_json("artifacts/manifests/minimum_run.json");verify_frozen(minimum)
    selection=read_json(RUN/"selection.json")
    assert digest_file(RUN/"cases.json")==selection["cases_sha256"]
    assert digest_file(RUN/"protocol_initial.md")==selection["protocol_sha256"]
    core=read_json(RUN/"core/frozen.json");hashes(core["sources"])
    assert core["cases_sha256"]==selection["cases_sha256"]
    placement=read_json(RUN/"gpu_placement.json")
    assert placement["parameter_devices"]==placement["first_forward_tensor_devices"]==["cuda:0"]
    assert placement["dtypes"]==["torch.bfloat16"]
    gates=read_json(RUN/"pre_inference_gates.json");launch=read_json(RUN/"core_launch.json")
    assert gates["passed"] and gates["completed_at"]<launch["started_at"]
    journal=[json.loads(s) for s in (RUN/"core/requests.jsonl").read_text().splitlines()]
    phases=Counter((r["case_id"],r["phase"],r["event"]) for r in journal)
    assert len(phases)==len(journal) and all(n==1 for n in phases.values())
    finished=[r for r in journal if r["event"]=="finished"];assert len(finished)<=480
    assert all((r["case_id"],r["phase"],"started") in phases for r in finished)
    assert all(r["phase"] in {"initial","repair"} for r in finished)
    complete=read_json(RUN/"core/completion.json");assert len(finished)==complete["calls"]==325
    assert sum(r["phase"]=="initial" for r in finished)==complete["cases"]==240
    assert sum(r["phase"]=="repair" for r in finished)==complete["repairs"]==85
    for name,key in (("prompt_tokens","input_tokens"),("completion_tokens","output_tokens")):
        assert sum(r["response"]["usage"][name] for r in finished)==complete[key]
    assert all(not r.get("error") for r in finished)
    structural=read_json(DATA/"structural_summary.json")
    assert structural["eligible_direct_prediction_groups"]==structural["direct_prediction_agreement"]
    alias=read_json(DATA/"primitive_alias_summary.json")
    assert alias["eligible_prediction_groups"]==alias["prediction_agreement"]
    assert alias["completion"]["new_gpu_calls"]==0
    for name in ("scoring.py","structural_analysis.py"):
        tree=ast.parse(Path("src/temporal_evidence/semantic",name).read_text())
        imports=[n.module or "" for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        assert not any("storage" in p or "validation" in p or "evaluation.exact" in p for p in imports)
    assessments=scopes=paths=0;unique_scopes=set()
    manifests=[DATA/"exports/manifest.json",*sorted((DATA/"structure_exports").glob("*/manifest.json")),
        VIEWS/"exports/manifest.json",VIEWS/"live_wesad/manifest.json"]
    for mp in manifests:
        manifest=read_json(mp);assert manifest["instance"]=="actual retained Neo4j Community instance"
        for item in manifest["scopes"]:
            p=mp.parent/item["file"];assert digest_file(p)==item["sha256"]
            g=read_export(p);assert not validate_export(g)
            assert (len(g["nodes"]),len(g["edges"]))==(item["nodes"],item["edges"])
            rs=records(g)
            for n in g["nodes"]:
                if n["semantic_type"]!="assessment":continue
                a=n["properties"];assert a["scope"]==item["scope"]
                assert a["id"] in rs and rs[a["id"]]["ingested_at_seconds"]<=a["known_at"]
                if a["trigger_id"] in rs:assert rs[a["trigger_id"]]["ingested_at_seconds"]<=a["known_at"]
                assessments+=1
            ids={n["properties"].get("id"):n["id"] for n in g["nodes"] if n["semantic_type"]!="assessment"}
            edges={(e["source"],e["type"],e["target"]) for e in g["edges"]}
            for triple in g["representative_stored_paths"]:
                assert (ids[triple["claim"]],"DEPENDS_ON",ids[triple["feature"]]) in edges
                assert (ids[triple["feature"]],"DERIVED_FROM",ids[triple["observation"]]) in edges
                paths+=1
            scopes+=1
            unique_scopes.add(item["scope"])
    hashes(read_json(DATA/"analysis_manifest.json")["source_hashes"])
    pub=read_json("paper/generated/semantic/manifest.json")
    for key in ("inputs","generated_tex","generated_docs"):hashes(pub[key])
    assert digest_file("src/temporal_evidence/semantic/publication.py")==pub["script_sha256"]
    figure=read_json("artifacts/figures/semantic_analysis_v1/manifest.json")
    hashes(figure["inputs"]);assert figure["complete_main_set"]
    assert digest_file("src/temporal_evidence/semantic/figures.py")==figure["script_sha256"]
    for name in figure["figures"]:
        for ext in ("pdf","svg"):assert Path("artifacts/figures/semantic_analysis_v1",name+"."+ext).stat().st_size>1000
    views=review_views_check();classic=classic_network_check()
    mainpdf=pdf_check("paper/semantic_structure_revision.pdf","main")
    assert sorted(p.name for p in Path("paper").glob("*.pdf"))==["semantic_structure_revision.pdf"]
    assert not pdf_link_present(mainpdf["pdf"],"semantic_structure_supplement.pdf")
    assert not re.search(r"\bsupplement(?:ary)?\b",command("pdftotext",mainpdf["pdf"],"-"),re.I)
    assert "supplement" not in Path("paper/build.sh").read_text().lower()
    aux=Path("paper/build/main.aux").read_text()
    refs=int(re.search(r"\\newlabel\{page:references\}\{\{[^}]*\}\{(\d+)\}",aux).group(1))
    assert 18<=refs-1<=20,(refs-1,"main-page target and conference limit")
    assert len(re.findall(r"\\newlabel\{fig:",aux))==6
    assert len(re.findall(r"\\newlabel\{eq:",aux))==8
    assert sum(p.read_text().count(r"\begin{proposition}") for p in Path("paper/sections").glob("*.tex"))==2
    abstract_words=len(Path("paper/generated/semantic/abstract.tex").read_text().split())
    assert 150<=abstract_words<=250
    test_suite=ET.parse(VIEWS/"pytest.xml").getroot().find("testsuite")
    assert int(test_suite.attrib["errors"])==int(test_suite.attrib["failures"])==0
    browser=read_json(VIEWS/"dashboard/validation.json")
    hashes(browser["artifacts"])
    assert browser["script_sha256"]==digest_file("scripts/capture_review_dashboard.mjs")
    assert browser["view_registry_sha256"]==digest_file(VIEWS/"manifest.json")
    assert len(browser["cases"])==2 and all(c["noException"] and c["assertedAndStorageIntervals"] for c in browser["cases"])
    report={"passed":True,"checked_at":utc_now(),"main":mainpdf,"single_submission_pdf":True,
        "main_pages":refs-1,"reference_pages":mainpdf["pages"]-refs+1,"figures":6,"central_equations":8,"propositions":2,
        "abstract_source_words":abstract_words,"verified_actual_export_scopes":scopes,"verified_stored_paths":paths,
        "unique_actual_export_scopes":len(unique_scopes),"shared_review_views":views,"classic_network":classic,"revision_gpu_calls":0,
        "tests_passed":int(test_suite.attrib["tests"]),"pytest_report_sha256":digest_file(VIEWS/"pytest.xml"),
        "browser_validation_sha256":digest_file(VIEWS/"dashboard/validation.json"),
        "assessment_times_checked":assessments,"original_protocol_hash":minimum["protocol_hash"],
        "core_cases":240,"core_calls":325,"primary_replay_cells":9600,"separate_corrected_replay_cells":4800,
        "gpu_placement_verified":True,"frozen_sources_and_inputs_unchanged":True,
        "generated_inputs_match":True,"independent_oracle_import_check":True,
        "no_supplementary_document_dependency":True,
        "script_sha256":digest_file(__file__),
        "visual_review":"Recorded separately in paper/semantic_visual_review.md; mechanical checks do not imply conference submission."}
    write_json("artifacts/manifests/semantic_manuscript_validation.json",report)
    print(f"Passed: one PDF, {refs-1} main + {mainpdf['pages']-refs+1} reference pages; {len(unique_scopes)} unique export scopes and one fresh real-data duplicate check.")

if __name__=="__main__":main()
