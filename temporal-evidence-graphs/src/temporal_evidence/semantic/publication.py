"""Generate every new manuscript result from immutable analysis artifacts."""
from collections import Counter
from pathlib import Path
import numpy as np
from temporal_evidence.io import read_json,write_json,digest_file
from temporal_evidence.semantic.ontology import NODE_RULES,RELATIONS
from temporal_evidence.semantic.statistics import cluster_mean,cluster_ratio

DATA=Path("artifacts/analysis/semantic_analysis_v1")
OUT=Path("paper/generated/semantic")
SOURCES={"synthetic":"Synthetic","wesad":"WESAD","ppg_dalia":"PPG-DaLiA"}

def tex(s):
    return str(s).replace("_",r"\_").replace("%",r"\%").replace("&",r"\&").replace("→",r"$\to$")

def ci(x,scale=100,digits=1):
    if x["mean"] is None:return "NA"
    return f"{scale*x['mean']:.{digits}f} [{scale*x['ci95'][0]:.{digits}f}, {scale*x['ci95'][1]:.{digits}f}]"

def table(name,header,rows,columns=None):
    columns=columns or "l"+"r"*(len(header)-1)
    body=[r"\begin{tabular}{"+columns+"}",r"\toprule"," & ".join(header)+r" \\",r"\midrule"]
    body += [" & ".join(map(str,row))+r" \\" for row in rows]
    body += [r"\bottomrule",r"\end{tabular}"]
    (OUT/(name+".tex")).write_text("\n".join(body)+"\n")

def write():
    OUT.mkdir(parents=True,exist_ok=True)
    recon=read_json(DATA/"reconfirmation.json");assert recon["passed"]
    sem=read_json(DATA/"semantic_summary.json");struct=read_json(DATA/"structural_summary.json")
    rows=read_json(DATA/"structural_replay_metrics.json");alias=read_json(DATA/"primitive_alias_summary.json")
    graphs=read_json(DATA/"structure_summary.json");storage=read_json(DATA/"storage_by_scope.json")
    cross=read_json(DATA/"contract_crosswalk_summary.json");core=read_json(DATA/"core_by_snapshot.json")
    active=read_json(DATA/"active_graph_by_snapshot.json")
    old=read_json("artifacts/analysis/publication.json")
    streaming=read_json("artifacts/analysis/streaming_v1/summary.json")
    get=lambda source,method,stage:next(r for r in sem if (r["dataset"],r["method"],r["stage"])==(source,method,stage))
    macros={"SemParentClaims":recon["reconfirmed"]["M1_claims_with_parent"],
        "SemDisplayedClaims":recon["reconfirmed"]["M1_claims"],
        "SemParentlessPercent":f"{100*(1-recon['reconfirmed']['M1_claims_with_parent']/recon['reconfirmed']['M1_claims']):.1f}",
        "SemExportScopes":recon["actual_export_scopes"],"SemVerifiedPaths":recon["verified_stored_paths"],
        "SemStorageNodes":f"{sum(r['nodes'] for r in storage):,}","SemStorageEdges":f"{sum(r['edges'] for r in storage):,}",
        "SemBackground":sum(r["contract_invalid_grounded_background"] for r in cross if r["method"]=="B0"),
        "SemInvalidGrounded":sum(r["contract_invalid_but_grounded"] for r in cross if r["method"]=="B0"),
        "SemContractInvalid":sum(r["contract_invalid"] for r in cross if r["method"]=="B0"),
        "SemRevisionBatches":sum(r["revision_batches"] for r in graphs),"SemEligibleBatches":sum(r["with_required_change"] for r in graphs),
        "SemNonzeroExposure":sum(r["with_nonzero_exposure"] for r in graphs),
        "SemLocalityViolations":sum(r["locality_violations"] for r in graphs),
        "SemCoreCalls":struct["completed"]["core"]["calls"],"SemCoreRepairs":struct["completed"]["core"]["repairs"],
        "SemCoreCases":struct["completed"]["core"]["cases"],"SemCoreRoots":struct["completed"]["core"]["adequate_answers"],
        "SemCoreMinutes":f"{struct['completed']['core']['invocation_wall_seconds']/60:.1f}",
        "SemReplayCells":f"{struct['completed']['replay']['cells']:,}",
        "SemPredictionGroups":struct["eligible_direct_prediction_groups"],"SemPredictionAgreement":struct["direct_prediction_agreement"],
        "SemParityGroups":f"{struct['database_parity_groups']:,}","SemSameSize":struct["same_record_count_different_exposure"],
        "SemRootOne":struct["realized_root_depth_counts"].get("1",0),"SemRootTwo":struct["realized_root_depth_counts"].get("2",0),
        "SemMissingRoots":struct["realized_root_depth_counts"].get("None",0),"SemAliasRoots":alias["completion"]["admissible_roots"],
        "SemAliasCells":f"{alias['completion']['cells']:,}","SemAliasRequired":next(r["required"] for r in alias["methods"] if r["method"]=="M1"),
        "SemAliasMissed":next(r["missed"] for r in alias["methods"] if r["method"]=="B2"),
        "SemUnknownPrimitive":struct["admission_rejection_reasons"]["unknown_proposition"]}
    macros["SemCoreSizeMin"]=f"{min(r['core_nodes']['mean'] for r in graphs):.1f}"
    macros["SemCoreSizeMax"]=f"{max(r['core_nodes']['mean'] for r in graphs):.1f}"
    macros["SemCoreRatioMin"]=f"{100*min(r['core_ratio']['mean'] for r in graphs):.1f}"
    macros["SemCoreRatioMax"]=f"{100*max(r['core_ratio']['mean'] for r in graphs):.1f}"
    assessment_audit=read_json(DATA/"assessment_temporal_audit.json")
    macros["SemAssessmentTies"]=assessment_audit["same_time_groups"]
    macros["SemAssessmentConflicts"]=assessment_audit["conflicting_state_groups"]
    for origin,label in (("fixture","Fixture"),("generated","Generated")):
        rs=[r for r in rows if r["origin"]==origin and r["method"]=="B2"]
        macros["Sem"+label+"Required"]=sum(r["required_changes"] for r in rs)
        macros["Sem"+label+"Missed"]=sum(r["missed_changes"] for r in rs)
        rts=[r for r in rows if r["origin"]==origin and r["method"]=="M1" and r["condition"]=="route_loss" and r["regime"]=="alternative" and r["root_count"]]
        macros["Sem"+label+"Alternative"]=len(rts)
        assert all(r["root_preserved"] for r in rts)
    for source,prefix in (("synthetic","Synthetic"),("wesad","Wesad"),("ppg_dalia","Ppg")):
        for stage,label in (("proposal","Raw"),("displayed","Display")):
            r=get(source,"M1",stage)
            for key,suffix in (("precision","P"),("recall","R")):macros["Sem"+prefix+label+suffix]=f"{100*r[key]['mean']:.1f}"
    cq=read_json(DATA/"competency_queries.json")
    macros["SemCompetencyWitnesses"]=sum(r["total"] for r in cq if r["question"]=="source_window")
    macros["SemCompetencyComparisons"]=sum(r["total"] for r in cq if r["question"]=="comparison_witness")
    (OUT/"macros.tex").write_text("\n".join(r"\newcommand{\%s}{%s}"%(k,v) for k,v in macros.items())+"\n")
    objects=[(r"\shortstack[l]{Subject / Sensor}","Identity and channel","deterministic"),
        ("Observation","Hashed sample window","deterministic"),
        ("FeatureVersion","Value or availability watch","deterministic"),
        ("ClaimVersion","Bounded proposition, references","model; checked"),
        ("ExplanationVersion","Text and display membership","administrative"),
        ("ReviewEvent","Recorded review action","administrative"),
        ("SupportAssessment","State, time and trigger","evaluation"),
        ("Record placeholder","Unresolved referenced ID","administrative")]
    table("object_table",["Stored object","Meaning","Construction"],objects,"lll")
    # Full construction tables use paragraph cells, preserving every adapter object.
    lines=[r"\begingroup\footnotesize\setlength{\tabcolsep}{3pt}",
        r"\begin{longtable}{>{\raggedright\arraybackslash}p{.16\textwidth}>{\raggedright\arraybackslash}p{.26\textwidth}>{\raggedright\arraybackslash}p{.28\textwidth}>{\raggedright\arraybackslash}p{.20\textwidth}}",
        r"\caption{Complete stored node vocabulary. Nodes have a type, not an edge domain/range.}\label{tab:fullnodes}\\",
        r"\toprule Type / label & Meaning & Creation and provenance & Status \\\midrule\endfirsthead",
        r"\toprule Type / label & Meaning & Creation and provenance & Status \\\midrule\endhead"]
    for k,label,meaning,rule,prov,status in NODE_RULES:
        short=label.replace("Version"," Version").replace("SupportAssessment","Support Assessment").replace("ReviewEvent","Review Event")
        lines.append(" & ".join(tex(t).replace(r"\_",r"\_\allowbreak{}").replace(".",r".\allowbreak{}").replace("/",r"/\allowbreak{}") for t in (short,meaning,rule+"; "+prov,status))+r" \\[3pt]")
    lines += [r"\bottomrule\end{longtable}\endgroup"]
    (OUT/"full_nodes.tex").write_text("\n".join(lines))
    lines=[r"\begingroup\footnotesize\setlength{\tabcolsep}{3pt}",
        r"\begin{longtable}{>{\raggedright\arraybackslash}p{.20\textwidth}>{\raggedright\arraybackslash}p{.20\textwidth}>{\raggedright\arraybackslash}p{.25\textwidth}>{\raggedright\arraybackslash}p{.25\textwidth}}",
        r"\caption{Complete relation vocabulary. R denotes any Record kind; P an unresolved placeholder. Assessment is not a Record kind.}\label{tab:fullrelations}\\",
        r"\toprule Relation & Domain $\to$ range & Meaning & Creation / status \\\midrule\endfirsthead",
        r"\toprule Relation & Domain $\to$ range & Meaning & Creation / status \\\midrule\endhead"]
    def domain(ds):
        if len(ds)>4:return "R/P" if "placeholder" in ds else "R"
        return ", ".join(ds)
    for rel,(dom,ran,meaning,rule,status) in RELATIONS.items():
        label=tex(rel).replace(r"\_",r"\_\allowbreak ")
        creation=tex(rule+"; "+status).replace(r"\_",r"\_\allowbreak{}").replace(".",r".\allowbreak{}").replace("=",r"=\allowbreak{}")
        lines.append(" & ".join((label,tex(domain(dom))+r" $\to$ "+tex(domain(ran)),tex(meaning),creation))+r" \\[3pt]")
    lines += [r"\bottomrule\end{longtable}\endgroup"]
    (OUT/"full_relations.tex").write_text("\n".join(lines))
    example=read_json(DATA/"representative_cores/wesad_median.json");ns=example["before"]["nodes"]
    fs=sorted((n for n in ns if n["type"]=="feature"),key=lambda n:n["interval"][0])
    c=next(n for n in ns if n["type"]=="claim" and n["claim"]["claim_type"]=="numeric_observation")
    revised=max((n for n in example["after"]["nodes"] if n["type"]=="feature"),key=lambda n:n["interval"][0])
    text=(r"In the saved WESAD S11 episode (Figure~\ref{fig:ontology}), the EDA window at "
        f"{fs[-1]['interval'][0]:g}--{fs[-1]['interval'][1]:g} s produces a median of "
        f"{fs[-1]['value']:.6f} "+r"$\mu$S. The model proposes "
        f"{c['value']:.6f} "+r"$\mu$S and cites that feature. The checker admits the bounded statement and insertion records both its "
        r"\texttt{DEPENDS\_ON} citation and the reverse \texttt{SUPPORTS} edge. A later feature version changes the median to "
        f"{revised['value']:.6f} "+r"$\mu$S, retaining the original observation hash and immutable claim citation. "
        "Re-evaluation changes the claim's current support without rewriting its history.\n")
    (OUT/"worked_example.tex").write_text(text)
    semrows=[]
    for source,label in SOURCES.items():
        for method,stage,name in (("B0","displayed","B0 display"),("M1","proposal","M1 raw"),("M1","displayed","M1 display")):
            r=get(source,method,stage)
            semrows.append([label,name,ci(r["precision"]),ci(r["recall"]),f"{r['matched']}/{r['answerable']}",r["empty"]])
    table("fidelity_table",["Source","State",r"$P$ [95\% CI]",r"$R$ [95\% CI]","Matched","Empty"],semrows,"llrrrr")
    graphrows=[]
    for source,label in SOURCES.items():
        g=next(r for r in graphs if r["dataset"]==source);rs=[r for r in core if r["dataset"]==source]
        graphrows.append([label,ci(cluster_mean(rs,"full_visible_nodes"),1),ci(cluster_mean([r for r in active if r["dataset"]==source],"nodes"),1),
            ci(g["core_nodes"],1),ci(g["core_ratio"]),f"{g['with_nonzero_exposure']}/{g['with_required_change']}"])
    table("graph_table",["Source","Stored","Active","Core",r"Core/stored (\%)",r"$\xi>0$"],graphrows)
    srows=[];outcome=[]
    for origin,label in (("fixture","Exact"),("generated","Generated")):
        for method in ("B0","B2","M1"):
            rs=[r for r in rows if r["origin"]==origin and r["method"]==method]
            n=sum(r["required_changes"] for r in rs);miss=sum(r["missed_changes"] for r in rs);corr=cluster_ratio(rs,"corrected","required_changes")
            srows.append([label,method,n,miss,sum(r["collateral"] for r in rs),ci(corr)])
            outcome.append({"origin":origin,"method":method,"required":n,"missed":miss,"correction":corr})
    table("structural_table",["Program","Method","Required","Missed","Collateral",r"Corrected \% [CI]"],srows,"llrrrr")
    write_json(DATA/"structural_method_summary.json",outcome)
    table("alias_table",["Method","Required","Missed","Collateral",r"Corrected \% [CI]"],
        [[r["method"],r["required"],r["missed"],r["collateral"],ci(r["correction"])] for r in alias["methods"]])
    stagerows=[]
    for r in struct["semantic_stages"]:
        stage={"proposal":"Raw","final_proposal":"Final","accepted_displayed":"Admitted"}[r["stage"]]
        stagerows.append([SOURCES[r["dataset"]],stage,r["claims"],ci(r["witness_precision"]),ci(r["traceable_root_recall"])])
    table("program_fidelity",["Source","Stage","Claims",r"Witness \% [CI]",r"Root \% [CI]"],stagerows,"llrrr")
    crows=[]
    for r in streaming["cells"]:
        crows.append([r["method"],r["offered_events_per_second"],f"{1000*r['event_to_flag']['p95']:.1f}",
            f"{r['event_to_generated_repair']['p95']:.1f}",f"{r['adequate_at_completion']}/{r['completed_explanations']}"])
    table("cost_table",["Method","Events/s","Flag p95 ms","Candidate p95 s","Adequate"],crows)
    table("crosswalk_table",["Source","Old invalid","Grounded now","Of these: background","Valid now false"],
        [[SOURCES[r["dataset"]],r["contract_invalid"],r["contract_invalid_but_grounded"],r["contract_invalid_grounded_background"],r["contract_valid_but_ungrounded"]] for r in cross if r["method"]=="B0"])
    cq=read_json(DATA/"competency_queries.json")
    table("competency_table",["Source","Competency question","Correct / eligible"],
        [[SOURCES[r["dataset"]],tex(r["question"]),f"{r['correct']}/{r['total']}"] for r in cq],"llr")
    temporal=read_json(DATA/"temporal_summary_all_variants.json")
    table("temporal_table",["Source","Position",r"$P$ [CI]",r"$R$ [CI]","Grounded / all","Matched / req."],
        [[SOURCES[r["dataset"]],r["position"],ci(r["precision"]),ci(r["recall"]),f"{r['grounded']}/{r['emitted']}",f"{r['matched']}/{r['answerable']}"] for r in temporal if r["method"]=="M1"],"llrrrr")
    descriptions=[];required=[]
    for source,label in SOURCES.items():
        group=[next(r for r in temporal if r["dataset"]==source and r["method"]=="M1" and r["position"]==phase) for phase in ("before","arrival","maintained")]
        descriptions.append(label+" "+"/".join(str(r["emitted"]) for r in group))
        required.append([r["answerable"] for r in group])
    assert all(x==required[0] for x in required)
    (OUT/"temporal_denominators.tex").write_text("Before/arrival/maintenance emitted-claim counts are "+"; ".join(descriptions)+". Answerable required-fact counts are "+"/".join(map(str,required[0]))+" per source. Precision excludes empty outputs; recall includes their zero coverage. These pooled denominators describe the sample, while reported percentages average episodes within subjects.\n")
    requestrows=[]
    for folder in ("pilot_v1","pilot_v2","core"):
        p=Path("artifacts/runs/structure_study_v1")/folder/"completion.json"
        if not p.exists():continue
        r=read_json(p)
        requestrows.append([folder.replace("_"," "),r["cases"],r["calls"],r["repairs"],r["adequate_answers"],f"{r['invocation_wall_seconds']/60:.2f}",f"{r['input_tokens']:,}",f"{r['output_tokens']:,}"])
    table("extension_requests",["Stage","Cases","Calls","Repairs","Roots","Minutes","Input tokens","Output tokens"],requestrows,"lrrrrrrr")
    abstract=r"""Generated explanations can remain plausible after their evidence changes.
We study a typed temporal property graph that separates recording provenance,
model-proposed propositions, declared prerequisites and time-indexed support.
A query-specific semantic projection preserves numerical witnesses and version
history while exposing the dependencies relevant to revision. A shared, labeled
network view makes immutable citations, changed versions and alternative
witnesses inspectable in the paper and review dashboard. Two conditional
results connect local support re-evaluation to transitive exposure: the fraction
of necessary changes excluded by direct-only scheduling. Re-analysis of synthetic,
WESAD and PPG-DaLiA experiments finds that only \SemParentClaims{} of
\SemDisplayedClaims{} displayed claims have parents; every eligible waveform
revision has zero transitive exposure. Independent semantic scoring separates
source grounding from target completeness: checked displays are fully grounded,
but subject-averaged required recall is \SemPpgDisplayR--\SemSyntheticDisplayR\%.
In \SemCoreCases{} controlled structural cases, exact and GPU-generated programs
expose necessary intermediate dependencies and surviving alternative witnesses.
Exposure predicts direct-maintenance misses in all \SemPredictionGroups{} eligible
replays; full maintenance agrees across Neo4j and an indexed relational control.
Generated answers realize evidence-to-answer depth one or two despite requests
up to four. These results identify when explicit semantic structure enables
selective revision, and show why storage size, path length and contract acceptance
alone cannot establish explanation fidelity or maintenance benefit.
"""
    (OUT/"abstract.tex").write_text(abstract)
    report=["# Theory and results revision", "",
        "Generated from semantic_analysis_v1 and structure_study_v1. The original minimum_v1 protocol, code, inputs and scores are unchanged.", "",
        "The paper defines a fixed typed ontology and its construction, a query-specific semantic projection, admissible AND/OR witnesses, conditional locality, and direct-maintenance exposure. Two propositions connect explicit dependencies to measured scheduling behavior. Actual Neo4j exports replace the symbolic network as the principal graph illustration.", "",
        "Grounding precision, unique required-fact recall and witness-query fidelity are independent of database support flags. Accurate background facts are distinguished from target completeness and the original contract. Empty answers retain zero useful coverage.", "",
        "| Result | Completed measurement |","|---|---|",
        f"| Original displayed parent links | {macros['SemParentClaims']} / {macros['SemDisplayedClaims']} claims |",
        f"| Original revision exposure | {macros['SemNonzeroExposure']} nonzero / {macros['SemEligibleBatches']} eligible batches; {macros['SemRevisionBatches']} total |",
        f"| Newly grounded old B0 contract errors | {macros['SemInvalidGrounded']} / {macros['SemContractInvalid']}; {macros['SemBackground']} labelled background |",
        f"| Core structural GPU study | {macros['SemCoreCases']} cases; {macros['SemCoreCalls']} calls including {macros['SemCoreRepairs']} repairs; {macros['SemCoreMinutes']} minutes |",
        f"| Original extension replay | {macros['SemReplayCells']} cells; {macros['SemCoreRoots']} admitted roots |",
        f"| Exact program direct misses | {macros['SemFixtureMissed']} / {macros['SemFixtureRequired']} required changes |",
        f"| Generated program direct misses | {macros['SemGeneratedMissed']} / {macros['SemGeneratedRequired']} required changes |",
        f"| Prediction agreement | {macros['SemPredictionAgreement']} / {macros['SemPredictionGroups']} eligible groups |",
        f"| Generated admitted root depth | depth 1: {macros['SemRootOne']}; depth 2: {macros['SemRootTwo']}; missing: {macros['SemMissingRoots']} |",
        f"| Separate normalization replication | {macros['SemAliasRoots']} roots; {macros['SemAliasCells']} CPU cells; direct misses {macros['SemAliasMissed']} / {macros['SemAliasRequired']}; no new GPU calls |",
        "| Full maintenance | Zero missed changes and zero collateral withdrawal; Neo4j/SQLite outcomes agree |",
        "| Original systems adequacy | 0 / 236 candidates adequate; no finite successful-replacement time observed |", "",
        "| Source | M1 raw grounding / recall (%) | M1 displayed grounding / recall (%) |","|---|---|---|"]
    for s,label in SOURCES.items():
        a=get(s,"M1","proposal");b=get(s,"M1","displayed")
        report.append(f"| {label} | {100*a['precision']['mean']:.2f} / {100*a['recall']['mean']:.2f} | {100*b['precision']['mean']:.2f} / {100*b['recall']['mean']:.2f} |")
    report += ["","Percentages average episodes within dataset-scoped participants; pooled counts and 95% intervals are supplied separately. Raw structural propositions are initially true by construction, but their witness families need not be sound or complete.", "",
        f"The assessment-time audit finds {macros['SemAssessmentTies']} tied record/time groups, including {macros['SemAssessmentConflicts']} with different recorded states. The projection retains every tied outcome and marks conflicts ambiguous; timestamps alone do not supply trigger order. This provenance finding changes no independent semantic score or frozen outcome.", "",
        "The post-core primitive-name admission omission is preserved in the original extension and corrected only in primitive_alias_replication. Normalization uses test definitions already supplied to the model and never inserts parent links. An analysis-only fix scopes repeated subject labels by dataset when pooling sources; original scores are untouched.", "",
        "Five main figures are supplied as PDF/SVG with source exports and layout maps. A single self-contained paper integrates relation construction, review-view semantics, assessment ambiguity and the admission sensitivity analysis. Exhaustive original tables and logs remain repository artifacts; historical PDFs are archived. Results concern explicit generated commitments, not internal neural state, learned ontology, clinical truth or universal graph-storage superiority.", "",
        "See [reproduction commands](docs/semantic_reproduction.md), [ontology construction](docs/ontology_construction.md), [main PDF](paper/semantic_structure_revision.pdf), and [review-view implementation](docs/review_network_views.md). Final page counts and checks are recorded in artifacts/manifests/semantic_manuscript_validation.json."]
    Path("THEORY_RESULTS_CHANGES.md").write_text("\n".join(report)+"\n")
    write_json(OUT/"manifest.json",{"complete":True,"script_sha256":digest_file(__file__),
        "inputs":{str(p):digest_file(p) for p in sorted(DATA.glob("*.json"))},
        "original_protocol_hash":old["protocol_hash"],"core_source_freeze":digest_file("artifacts/runs/structure_study_v1/core/frozen.json"),
        "macros":macros,"generated_docs":{"THEORY_RESULTS_CHANGES.md":digest_file("THEORY_RESULTS_CHANGES.md")},
        "generated_tex":{str(p):digest_file(p) for p in sorted(OUT.glob("*.tex"))}})

if __name__=="__main__":write()
