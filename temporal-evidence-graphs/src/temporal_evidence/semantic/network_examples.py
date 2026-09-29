"""Deterministically select saved database cases and publish shared review views."""
from pathlib import Path

from temporal_evidence.io import read_json, write_json, digest_file, digest_object
from temporal_evidence.semantic.export import read_export
from temporal_evidence.semantic.review_view import build_view, validate_view
from temporal_evidence.semantic.network_render import union_layout, save_network

ROOT=Path("artifacts/analysis/review_views_v1")
RUN=Path("artifacts/runs/structure_study_v1")
FIGURES=Path("artifacts/figures/semantic_analysis_v1")


def structural_selection():
    cases={c["case_id"]:c for c in read_json(RUN/"cases.json")}
    eligible=[]
    for path in sorted((RUN/"core/candidates").glob("*.json")):
        candidate=read_json(path);case=cases[candidate["case_id"]]
        if case["regime"]!="alternative":continue
        claims={c["claim_id"]:c for c in candidate["accepted"]}
        replay=next(r for r in read_json(RUN/"replay"/(case["case_id"]+"-generated.json")) if r["condition"]=="route_loss" and r["method"]=="M1")
        for c in claims.values():
            if c["proposition"]!="answer" or len(c["witnesses"])<2 or not replay["root_preserved"] or not replay["required_change_ids"]:continue
            if not all(len(w)==1 and w[0] in claims for w in c["witnesses"]):continue
            decision=next(d for d in candidate["decisions"] if d["claim_id"]==c["claim_id"])
            if not decision.get("complete_witness_family"):continue
            selected=set();features=set();agenda=[c["claim_id"]]
            while agenda:
                cid=agenda.pop()
                if cid in selected:continue
                selected.add(cid)
                for w in claims[cid]["witnesses"]:
                    for token in w:
                        if token in case["tests"]:features.add(case["tests"][token]["source_id"])
                        else:agenda.append(token)
            eligible.append({"nodes_before_expansion":len(selected)+len(features),"case_id":case["case_id"],"root":c["claim_id"],
                "realized_depth":replay["realized_depth"],"intended_depth":case["intended_depth"]})
    eligible.sort(key=lambda r:(r["nodes_before_expansion"],r["case_id"],r["root"]))
    return {"population":"240 primary GPU-generated candidates; no normalized replication or compiled fixture",
        "eligibility":"Admitted answer with >=2 complete alternative witnesses, each a singleton declared parent; at least one claim withdrawn and the answer retained under M1 primary-route loss.",
        "selection_rule":"Smallest complete claim/feature ancestor closure before provenance/version expansion, then lexical case ID and root ID.",
        "eligible_count":len(eligible),"eligible":eligible,"selected":eligible[0]},cases[eligible[0]["case_id"]]


def configurations():
    representative=read_json("artifacts/analysis/semantic_analysis_v1/representative_cores/wesad_median.json")
    selection,case=structural_selection();cid=case["case_id"]
    rp=RUN/"replay"/(cid+"-generated.json")
    replay=next(r for r in read_json(rp) if r["condition"]=="route_loss" and r["method"]=="M1")
    graphpath=ROOT/"exports"/(replay["scope"].replace("/","__")+".json.gz")
    claim=next(n for n in representative["before"]["nodes"] if n["claim"] and n["claim"]["claim_type"]=="trend")
    return [
        {"key":"wesad_revision","title":"WESAD S11 · EDA correction","case_id":representative["case_id"],
         "export":"artifacts/analysis/semantic_analysis_v1/exports/minimum_v1__wesad-S11-e0__correction__M1.json.gz",
         "focus_ids":[claim["id"]],"times":{"Before revision":representative["before"]["knowledge_time"],"After maintenance":representative["after"]["knowledge_time"]},
         "expand_provenance":True,"budget":16,"rankdir":"TB","figure":"real_revision_network",
         "selection":{"rule":"Existing median-size eligible WESAD correction core, lexical tie-break; unchanged selection.","eligible_count":representative["eligible"],"source":"artifacts/analysis/semantic_analysis_v1/representative_cores/wesad_median.json"}},
        {"key":"structural_alternatives","title":"PPG-DaLiA S1 · generated alternative witnesses","case_id":cid,"export":str(graphpath),
         "focus_ids":[cid+"/claim/"+selection["selected"]["root"]],"times":{"Before revision":case["knowledge_time"]+.01,"After maintenance":replay["knowledge_time"]+.01},
         "expand_provenance":False,"budget":18,"rankdir":"TB","figure":"structural_witness_network","program_case":case,"selection":selection,
         "candidate_path":str(RUN/"core/candidates"/(cid+".json")),"replay_path":str(rp)}]


def make_views(config, *, focus_ids=None, expand=None, budget=None):
    graph=read_export(config["export"])
    source={"export_path":config["export"],"export_sha256":digest_file(config["export"]),"selection":config["selection"]}
    for field in ("candidate_path","replay_path"):
        if field in config:source[field]={"path":config[field],"sha256":digest_file(config[field])}
    views=[]
    for name,t in sorted(config["times"].items(),key=lambda x:x[1]):
        view=build_view(graph,config["case_id"],t,focus_ids or config["focus_ids"],
            budget=budget or config["budget"],expand_provenance=config["expand_provenance"] if expand is None else expand,
            program_case=config.get("program_case"),baseline_time=min(config["times"].values()),source=source)
        view["recorded_state"]=name;validate_view(view,graph);views.append(view)
    return views


def run():
    ROOT.mkdir(parents=True,exist_ok=True)
    configs=configurations();entries=[]
    for config in configs:
        views=make_views(config);layout=union_layout(views,config["rankdir"])
        directory=ROOT/config["key"];directory.mkdir(exist_ok=True)
        for label,view in zip(("before","after"),views):write_json(directory/(label+".json"),view)
        write_json(directory/"layout.json",layout);write_json(directory/"config.json",config)
        manifest=save_network(views[-1],layout,FIGURES/config["figure"])
        # Snapshot previews use the same union positions; no future record is
        # drawn before ingestion even though a comparison reserves its space.
        for label,view in zip(("before","after"),views):save_network(view,layout,directory/label)
        entries.append({"key":config["key"],"title":config["title"],"view_path":str(directory/"after.json"),"config_path":str(directory/"config.json"),
                        "figure":config["figure"],"view_sha256":digest_object(views[-1]),"nodes":len(views[-1]["nodes"]),"edges":len(views[-1]["edges"]),
                        "selection":config["selection"],"layout_path":str(directory/"layout.json")})
    write_json(ROOT/"manifest.json",{"format":"review_graph_v1","examples":entries,"new_gpu_calls":0,
        "source_hashes":{str(p.relative_to(Path.cwd())):digest_file(p) for p in [Path(__file__).resolve(),Path(__file__).resolve().with_name("review_view.py"),Path(__file__).resolve().with_name("network_render.py")]}})
    a,b=configs;case=b["program_case"]
    revised=next(r for r in read_json(b["replay_path"]) if r["condition"]=="route_loss" and r["method"]=="M1")["revisions"][0]
    macros={"ViewRealBefore":min(a["times"].values()),"ViewRealAfter":max(a["times"].values()),
        "ViewRealEligible":a["selection"]["eligible_count"],"ViewRealNodes":entries[0]["nodes"],
        "ViewStructEligible":b["selection"]["eligible_count"],"ViewStructNodes":entries[1]["nodes"],
        "ViewStructBefore":min(b["times"].values()),"ViewStructAfter":max(b["times"].values()),
        "ViewStructDepth":b["selection"]["selected"]["realized_depth"],"ViewStructRequested":case["intended_depth"],
        "ViewRouteAInterval":"--".join(f"{x:g}" for x in case["tests"]["A1"]["interval"]),
        "ViewRouteBInterval":"--".join(f"{x:g}" for x in case["tests"]["B1"]["interval"]),
        "ViewRouteOld":f"{case['tests']['A1']['initial_value']:.5g}","ViewRouteNew":f"{revised['value']:.5g}",
        "ViewRouteThreshold":f"{case['tests']['A1']['threshold']:.5g}"}
    out=Path("paper/generated/review_views");out.mkdir(parents=True,exist_ok=True)
    (out/"macros.tex").write_text("\n".join(r"\newcommand{\%s}{%s}"%(k,v) for k,v in macros.items())+"\n")
    write_json(out/"manifest.json",{"inputs":{str(ROOT/"manifest.json"):digest_file(ROOT/"manifest.json")},
                                   "macros_sha256":digest_file(out/"macros.tex")})
    print([(e["key"],e["nodes"],e["edges"]) for e in entries])


if __name__=="__main__":run()
