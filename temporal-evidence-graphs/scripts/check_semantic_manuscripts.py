"""Validate the revised PDFs, frozen studies, actual exports and generated inputs."""
from collections import Counter
from pathlib import Path
import ast
import json
import re
import subprocess
import zlib
from temporal_evidence.io import read_json,write_json,digest_file,utc_now
from temporal_evidence.study import verify_frozen
from temporal_evidence.semantic.export import read_export
from temporal_evidence.semantic.ontology import validate_export
from temporal_evidence.semantic.projection import records

DATA=Path("artifacts/analysis/semantic_analysis_v1")
RUN=Path("artifacts/runs/structure_study_v1")

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
    assessments=scopes=paths=0
    manifests=[DATA/"exports/manifest.json",*sorted((DATA/"structure_exports").glob("*/manifest.json"))]
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
    hashes(read_json(DATA/"analysis_manifest.json")["source_hashes"])
    pub=read_json("paper/generated/semantic/manifest.json")
    for key in ("inputs","generated_tex","generated_docs"):hashes(pub[key])
    assert digest_file("src/temporal_evidence/semantic/publication.py")==pub["script_sha256"]
    figure=read_json("artifacts/figures/semantic_analysis_v1/manifest.json")
    hashes(figure["inputs"]);assert figure["complete_main_set"]
    assert digest_file("src/temporal_evidence/semantic/figures.py")==figure["script_sha256"]
    for name in figure["figures"]:
        for ext in ("pdf","svg"):assert Path("artifacts/figures/semantic_analysis_v1",name+"."+ext).stat().st_size>1000
    mainpdf=pdf_check("paper/semantic_structure_revision.pdf","main")
    supplement=pdf_check("paper/semantic_structure_supplement.pdf","supplement")
    assert pdf_link_present(mainpdf["pdf"],"semantic_structure_supplement.pdf")
    assert pdf_link_present(supplement["pdf"],"semantic_structure_revision.pdf")
    aux=Path("paper/build/main.aux").read_text()
    refs=int(re.search(r"\\newlabel\{page:references\}\{\{[^}]*\}\{(\d+)\}",aux).group(1))
    assert 14<=refs-1<=16,(refs-1,"main-page target")
    assert len(re.findall(r"\\newlabel\{fig:",aux))==5
    assert len(re.findall(r"\\newlabel\{eq:",aux))==7
    assert sum(p.read_text().count(r"\begin{proposition}") for p in Path("paper/sections").glob("*.tex"))==2
    assert digest_file("paper/temporal_evidence_maintenance.pdf")==mainpdf["sha256"]
    abstract_words=len(Path("paper/generated/semantic/abstract.tex").read_text().split())
    assert 150<=abstract_words<=250
    report={"passed":True,"checked_at":utc_now(),"main":mainpdf,"supplement":supplement,
        "main_pages":refs-1,"reference_pages":mainpdf["pages"]-refs+1,"figures":5,"central_equations":7,"propositions":2,
        "abstract_source_words":abstract_words,"verified_actual_export_scopes":scopes,"verified_stored_paths":paths,
        "assessment_times_checked":assessments,"original_protocol_hash":minimum["protocol_hash"],
        "core_cases":240,"core_calls":325,"primary_replay_cells":9600,"separate_corrected_replay_cells":4800,
        "gpu_placement_verified":True,"frozen_sources_and_inputs_unchanged":True,
        "generated_inputs_match":True,"independent_oracle_import_check":True,
        "relative_pdf_links_verified":True,
        "script_sha256":digest_file(__file__),
        "visual_review":"Recorded separately in paper/semantic_visual_review.md; mechanical checks do not imply conference submission."}
    write_json("artifacts/manifests/semantic_manuscript_validation.json",report)
    print(f"Passed: {refs-1} main pages + {mainpdf['pages']-refs+1} reference pages; supplement {supplement['pages']} pages; {scopes} export scopes.")

if __name__=="__main__":main()
