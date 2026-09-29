"""Build manuscript numbers only after every required run is accounted for.

All tables, numerical macros and plot inputs are derived from saved artifacts.
"""
from pathlib import Path
from collections import Counter, defaultdict
import os
os.environ.setdefault("MPLCONFIGDIR", ".local/matplotlib")
import numpy as np
from temporal_evidence.io import read_json, read_journal, write_json, digest_file
from temporal_evidence.analysis.systems import analyze_streaming, resource_summary
from temporal_evidence.analysis.design_figures import generate as design_figures
from temporal_evidence.analysis.integrity import audit_integrity
from temporal_evidence.analysis.audit_summary import summarize_audit
from temporal_evidence.analysis.contract_scope import summarize_scope

SOURCES = {"synthetic": "Synthetic", "wesad": "WESAD", "ppg_dalia": "PPG-DaLiA"}
METHODS = ("B0", "B1", "B2", "M1", "B3")
DIRECTORY = Path("paper/generated")


def number(value, digits=1):
    return "--" if value is None else f"{value:,.{digits}f}"


def percent(value):
    return "--" if value is None else number(100*value)


def fraction(metric):
    return f"{metric['numerator']:,}/{metric['denominator']:,}"


def usage_unavailable(rows):
    return sum(not all(key in row.get("response", {}).get("usage", {})
                       for key in ("prompt_tokens", "completion_tokens")) for row in rows)


def table(name, columns, header, rows):
    lines = [f"\\begin{{tabular}}{{{columns}}}", r"\toprule", " & ".join(header)+r" \\", r"\midrule"]
    lines.extend(" & ".join(str(value) for value in row)+r" \\" for row in rows)
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    (DIRECTORY/name).write_text("\n".join(lines)+"\n")


def streaming_figure(streaming):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":11,"pdf.fonttype":42,"svg.fonttype":"none"})
    figure, axes = plt.subplots(2, 2, figsize=(7.0, 4.8))
    for method, color, marker in [("M1", "#0072b2", "o"), ("B3", "#009e73", "s")]:
        cells = sorted((c for c in streaming["cells"] if c["method"] == method), key=lambda c:c["offered_events_per_second"])
        rates = [c["offered_events_per_second"] for c in cells]
        series = [([c["event_to_flag"]["p95"] for c in cells], "Flag p95 (s)"),
                  ([c["event_to_generated_repair"]["p95"] for c in cells], "Candidate p95 (s)"),
                  ([c["peak_event_backlog"] for c in cells], "Peak event backlog"),
                  ([c["peak_pending_explanations"] for c in cells], "Peak pending explanations")]
        for ax, (values, label) in zip(axes.flat, series):
            ax.plot(rates, values, marker=marker, color=color, label=method, linewidth=1.7)
            ax.set(xlabel="Offered events/s", ylabel=label, xticks=rates)
            ax.spines[["top","right"]].set_visible(False)
    axes[0,0].axhline(1,color="#888888",linestyle=":",linewidth=1)
    axes[0,0].set_yscale("log")
    axes[0,1].axhline(5,color="#888888",linestyle=":",linewidth=1)
    axes[0,0].legend(frameon=False)
    figure.tight_layout()
    for extension in ("pdf","svg","png"):
        figure.savefig(f"artifacts/figures/streaming.{extension}",bbox_inches="tight",dpi=200)
    plt.close(figure)


def generate():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    integrity = audit_integrity()
    frozen = read_json("artifacts/manifests/minimum_run.json")
    completion = read_json("artifacts/runs/minimum_v1/completion.json")
    assert completion["accounted_cases"] == completion["expected_cases"] == 3600
    assert completion["protocol_hash"] == frozen["protocol_hash"]
    summary = read_json("artifacts/analysis/minimum_v1/summary.json")
    metrics = read_json("artifacts/evaluation/minimum_v1/metrics.json")
    assert summary["cases"] == len(metrics) == 3600
    audit = read_json("artifacts/audit/minimum_v1/summary.json")
    assert audit["sampled"] == 60 and audit["total_calls"] == 64
    audit_details = summarize_audit()
    contract_scope = summarize_scope()
    core = read_json("artifacts/manifests/core_validation.json")
    assert core["passed"] and core["real_neo4j"]
    streaming = analyze_streaming()
    assert len(streaming["cells"]) == 6 and streaming["logical_parity"]
    assert sum(c["derived_events"] for c in streaming["cells"]) == 3120
    resources = resource_summary()
    stages = {row["stage"]:row for row in resources["stages"]}
    assert "automated_cuda_fidelity_audit" in stages
    database = read_json("artifacts/manifests/database_accounting.json")
    design_figures()
    streaming_figure(streaming)
    index = {(r["dataset"],r["method"]):r for r in summary["summary"]}
    repairs = sum(row["repair_calls"] for row in metrics)
    assert repairs <= frozen["maximum_repair_calls"]
    failures = sum(row["failed"] for row in metrics)
    truncations = sum(row["initial_truncation"] for row in metrics)
    dependency_counts = Counter()
    reasons = Counter()
    request_errors = Counter()
    dependency_only = Counter()
    main_usage_unavailable = 0
    for path in Path("artifacts/runs/minimum_v1/cases").glob("*.json"):
        output = read_json(path)
        main_usage_unavailable += usage_unavailable([output["initial"]] + ([output["repair"]] if output.get("repair") else []))
        for phase in ("initial","repair"):
            call = output.get(phase)
            if call and call.get("error"):
                error_type = call["error"].split(":",1)[0]
                request_errors[(output["case"]["dataset"],output["case"]["method"],phase,error_type)] += 1
        for claim in (output["display"] or {}).get("claims", []):
            dependency_counts[(output["case"]["method"], "claims")] += 1
            dependency_counts[(output["case"]["method"], "parent_claims")] += bool(claim["depends_on_claim_ids"])
        scored = read_json(Path("artifacts/evaluation/minimum_v1/cases")/path.name)
        for item in scored["persistent"]:
            if item["required_change"] and set(item["reasons"]) == {"dependency"}:
                key = (output["case"]["dataset"],output["case"]["method"])
                dependency_only[(*key,"required")] += 1
                dependency_only[(*key,"retained" if item["active"] else "withdrawn")] += 1
        for claim in scored["claims"]:
            for reason in claim["reasons"]:
                reasons[(output["case"]["dataset"],output["case"]["method"],reason)] += 1

    table("reliability_table.tex", "llrrrrr",
          ["Source","Method",r"Case err.\%",r"Claim err.\%",r"Recall\%",r"Coverage\%","Claims"],
          [[SOURCES[source],method,percent(r["case_error"]["value"]),percent(r["claim_error"]["value"]),
            percent(r["fact_recall"]["value"]),percent(r["useful_coverage"]["value"]),f"{r['claim_error']['denominator']:,}"]
           for source in SOURCES for method in METHODS for r in [index[(source,method)]]])
    table("correction_table.tex", "llrrrr",
          ["Source","Method",r"\shortstack{Corrected/\\required}",r"\shortstack{Complete\\(\%)}","Residual", r"\shortstack{Collateral/\\unaffected}"],
          [[SOURCES[source],method,fraction(r["correction_completeness"]),percent(r["correction_completeness"]["value"]),
            r["residual_incorrect"]["numerator"],fraction(r["collateral_revision"])]
           for source in SOURCES for method in METHODS for r in [index[(source,method)]]])
    labels = {"correction_completeness":"Correction", "case_error":"Case error", "fact_recall":"Fact recall"}
    table("contrasts_table.tex", "lllrrl",
          ["Source","Contrast","Outcome","N (S/E)",r"Difference (pp)",r"95\% interval (pp)"],
          [[SOURCES[r["dataset"]],f"{r['left']}--{r['right']}",labels[r["metric"]],f"{r['subjects']}/{r['eligible_episodes']}",
            number(None if r["difference"] is None else 100*r["difference"],2),
            "--" if r["ci95"] is None else "["+", ".join(number(100*v,2) for v in r["ci95"])+"]"]
           for r in summary["contrasts"] if r["principal"]])
    table("relational_contrasts_table.tex", "llrrl",
          ["Source","Outcome","N (S/E)",r"M1--B3 (pp)",r"95\% interval (pp)"],
          [[SOURCES[r["dataset"]],labels[r["metric"]],f"{r['subjects']}/{r['eligible_episodes']}",number(None if r["difference"] is None else 100*r["difference"],2),
            "--" if r["ci95"] is None else "["+", ".join(number(100*v,2) for v in r["ci95"])+"]"]
           for r in summary["contrasts"] if not r["principal"]])
    fixture_rows = []
    for method in METHODS:
        rows = [r for r in core["symbolic_scores"] if r["method"] == method]
        fixture_rows.append([method,f"{sum(r['corrected'] for r in rows)}/{sum(r['correction_required'] for r in rows)}",
                             sum(r["residual"] for r in rows),
                             f"{sum(r['collateral'] for r in rows)}/{sum(r['unaffected'] for r in rows)}"])
    table("fixture_table.tex","lrrr",["Method","Corrected/required","Residual","Collateral/unaffected"],fixture_rows)
    table("streaming_table.tex","rlrrrrrr",
          ["Events/s","Method",r"\shortstack{Flag p95\\(ms)}",r"\shortstack{Candidate\\p95 (s)}",r"\shortstack{Flag\\misses}",r"\shortstack{Repair\\misses}",r"\shortstack{Event\\Q}",r"\shortstack{Answer\\Q}"],
          [[c["offered_events_per_second"],c["method"],number(1000*c["event_to_flag"]["p95"]),
            number(c["event_to_generated_repair"]["p95"]),f"{c['flag_misses']}/{c['flag_denominator']}",
            f"{c['repair_misses']}/{c['repair_denominator']}",c["peak_event_backlog"],c["peak_pending_explanations"]]
           for c in sorted(streaming["cells"],key=lambda c:(c["offered_events_per_second"],c["method"]!="M1"))])
    table("staleness_table.tex","rlrrrr",
          ["Events/s","Method","Calls","Input adequate","Completion adequate","Became stale"],
          [[c["offered_events_per_second"],c["method"],c["completion_audited"],c["adequate_at_request"],
            c["adequate_at_completion"],c["adequate_then_stale"]] for c in streaming["cells"]])
    table("contract_scope_table.tex", "lrr", ["Source", "B0 contract-invalid claims", "Locally supported off-target facts"],
          [[SOURCES[row["dataset"]],row["contract_invalid"],row["off_target_locally_supported"]]
           for row in contract_scope["rows"] if row["method"] == "B0"])

    workload = [{"name":"Matched test", "calls":3600+repairs,
                 "usage_unavailable_requests":main_usage_unavailable,
                 "input_tokens":sum(r["input_tokens"] for r in metrics), "output_tokens":sum(r["output_tokens"] for r in metrics),
                 "seconds":stages["matched_held_out_run"]["wall_seconds"]}]
    for name in ("pilot_v1","pilot_v2","pilot_v3","pilot_v4"):
        path=Path(f"artifacts/runs/{name}")
        journal={(r["case_id"],r["phase"]):r for r in read_journal(path/"requests.jsonl") if r["event"]=="finished"}
        pilot=read_json(path/"summary.json")
        workload.append({"name":name.replace("_", " "),"calls":len(journal),
                         "usage_unavailable_requests":usage_unavailable(journal.values()),
                         "input_tokens":sum(r.get("response",{}).get("usage",{}).get("prompt_tokens",0) for r in journal.values()),
                         "output_tokens":sum(r.get("response",{}).get("usage",{}).get("completion_tokens",0) for r in journal.values()),
                         "seconds":pilot["batch_wall_seconds"]+sum(r["seconds"] for r in read_json(path/"interactive.json"))})
    workload += [{"name":"Systems test","calls":streaming["call_count"],
                  "usage_unavailable_requests":sum(c["usage_unavailable_requests"] for c in streaming["cells"]),
                  "input_tokens":sum(c["input_tokens"] for c in streaming["cells"]),
                  "output_tokens":sum(c["output_tokens"] for c in streaming["cells"]),
                  "seconds":stages["isolated_streaming_benchmark"]["wall_seconds"]},
                 {"name":"Automated audit","calls":audit["total_calls"],"input_tokens":audit["input_tokens"],
                  "usage_unavailable_requests":0,
                  "output_tokens":audit["output_tokens"],"seconds":stages["automated_cuda_fidelity_audit"]["wall_seconds"]}]
    # Preserve the failed smoke-test calls as real development cost too.
    for smoke in ("streaming_development_v1","streaming_development_v2"):
        journal=[]
        for path in Path(f"artifacts/streaming/{smoke}").glob("*/requests.jsonl"):
            journal += [r for r in read_journal(path) if r["event"]=="finished"]
        summaries=[read_json(p) for p in Path(f"artifacts/streaming/{smoke}").glob("*/summary.json")]
        workload.append({"name":smoke.replace("streaming_development_","Systems pilot "),"calls":len(journal),
                         "usage_unavailable_requests":usage_unavailable(journal),
                         "input_tokens":sum(r.get("response",{}).get("usage",{}).get("prompt_tokens",0) for r in journal),
                         "output_tokens":sum(r.get("response",{}).get("usage",{}).get("completion_tokens",0) for r in journal),
                         "seconds":sum(r["wall_seconds_including_drain"] for r in summaries)})
    table("cost_table.tex","lrrrrr",["Workload","Requests","No usage","Input tokens","Output tokens","Wall min"],
          [[r["name"],f"{r['calls']:,}",r["usage_unavailable_requests"],f"{r['input_tokens']:,}",f"{r['output_tokens']:,}",number(r["seconds"]/60)] for r in workload])
    hardware = frozen["environment"]
    model = frozen["config"]["model"]
    table("hardware_table.tex","ll",["Component","Recorded setting"],[
        ["GPU",hardware["gpu"].replace("NVIDIA GeForce ","")+f"; {hardware['gpu_memory_bytes']/2**30:.2f} GiB"],
        ["Primary model",r"Qwen3-8B; BF16; CUDA only"],
        ["Model revision",r"\texttt{"+model["revision"][:12]+"}"],
        ["Inference",f"vLLM {hardware['versions']['vllm']}; PyTorch {hardware['versions']['torch']}"],
        ["Database",f"Neo4j {hardware['database'][0]['versions'][0]}; SQLite {database['sqlite_version']} WAL"],
        ["Input / output limit",f"{model['max_input_tokens']:,} / {model['max_output_tokens']:,} tokens"],
        ["Batch concurrency / interactive",r"4 / 1"],
        ["CPU quota / memory limit",f"{int(hardware['cpu.max'].split()[0])/int(hardware['cpu.max'].split()[1]):.1f} CPU equivalents / {int(hardware['memory.max'])/10**9:.1f} GB"],
        ["Test GPU memory peak",number(stages["matched_held_out_run"]["peak_gpu_memory_mib"])+" MiB"],
        ["Test GPU utilization mean",number(stages["matched_held_out_run"]["mean_gpu_utilization_percent"])+r"\%"],
        ["Test host cgroup memory peak",number(stages["matched_held_out_run"]["peak_host_cgroup_memory_bytes"]/2**30)+" GiB"],
    ])
    table("failure_table.tex","llrrrrr",["Source","Method","Failed","Truncated","Repairs",r"Abstain\%",r"Valid refs\%"],
          [[SOURCES[source],method,r["failed"]["numerator"],r["initial_truncation"]["numerator"],r["repair_calls"]["numerator"],
            percent(r["abstained"]["value"]),percent(r["reference_validity"]["value"])]
           for source in SOURCES for method in METHODS for r in [index[(source,method)]]])

    final_pilot = read_json("artifacts/runs/pilot_v4/summary.json")
    macros = {"TotalInitial":"3,600", "TotalRepairs":f"{repairs:,}", "TotalRequests":f"{3600+repairs:,}",
              "PilotInteractivePFifty":number(final_pilot["interactive_p50"],2),
              "PilotInteractivePNinetyFive":number(final_pilot["interactive_p95"],2),
              "PilotBatchRate":number(final_pilot["initial_cases_per_second_including_repairs_and_database"],3),
              "TotalFailed":str(failures), "TotalTruncated":str(truncations),
              "TotalInitialErrors":str(sum(row["initial_parse_failure"] for row in metrics)),
              "ClientTimeouts":str(sum(row["timeout_calls"] for row in metrics)),
              "UsageUnavailable":str(sum(row["usage_unavailable_requests"] for row in workload)),
              "BaselineInvalidClaims":str(sum(row["contract_invalid"] for row in contract_scope["rows"] if row["method"] == "B0")),
              "OffTargetSupportedClaims":str(sum(row["off_target_locally_supported"] for row in contract_scope["rows"] if row["method"] == "B0")),
              "MainHours":number(stages["matched_held_out_run"]["wall_seconds"]/3600,2),
              "AuditFlagged":str(audit["flagged"]), "AuditParsed":str(audit["parsed"]),
              "AuditDisagreements":str(audit["disagreements_with_exact"]), "AuditCalibration":str(audit["calibration_correct"]),
              "GraphParentClaims":str(dependency_counts[("M1","parent_claims")]),
              "GraphTotalClaims":str(dependency_counts[("M1","claims")]),
              "SystemsCalls":str(streaming["call_count"]),
              "SystemsExplanations":str(sum(c["completed_explanations"] for c in streaming["cells"])),
              "SystemsAdequate":str(sum(c["adequate_at_request"] for c in streaming["cells"])),
              "SystemsWithoutDifference":str(sum(c["completed_explanations"]-c["difference_present"] for c in streaming["cells"])),
              "AuditAcceptedInvalid":str(sum(r["count"] for r in audit_details["cross_tabulation"] if not r["exact_all_claims_supported"] and r["automated_faithful"] is True)),
              "AuditFlaggedValid":str(sum(r["count"] for r in audit_details["cross_tabulation"] if r["exact_all_claims_supported"] and r["automated_faithful"] is False)),
              "GraphFlagMisses":str(sum(c["flag_misses"] for c in streaming["cells"] if c["method"]=="M1")),
              "GraphRepairMisses":str(sum(c["repair_misses"] for c in streaming["cells"] if c["method"]=="M1")),
              "SystemsRepairTargets":str(sum(c["repair_denominator"] for c in streaming["cells"] if c["method"]=="M1"))}
    assert all(key.isalpha() for key in macros), "LaTeX command names must contain letters only"
    (DIRECTORY/"macros.tex").write_text("% Generated from saved completed runs.\n"+"\n".join(
        "\\newcommand{\\"+key+"}{"+value+"}" for key,value in macros.items())+"\n")
    recalls=[index[(source,"M1")]["fact_recall"]["value"] for source in SOURCES]
    coverage=[index[(source,"M1")]["useful_coverage"]["value"] for source in SOURCES]
    checked=[index[(source,method)] for source in SOURCES for method in METHODS if method != "B0"]
    assert all(row["case_error"]["value"] == 0 and row["correction_completeness"]["value"] == 1 for row in checked)
    abstract = (
        "Monitoring explanations can remain visible after their supporting evidence changes. "
        "We evaluate explicit temporal dependencies for revising generated numerical explanations, "
        "separating direct checking, transitive maintenance, and storage implementation. "
        "A prospectively frozen study uses one synthetic benchmark, WESAD, and PPG-DaLiA: "
        "60 held-out episodes, four replay variants, three checkpoints, and five methods produce "
        f"3,600 initial requests and {repairs:,} bounded repairs. In common symbolic fixtures, "
        "full graph and indexed relational maintenance correct all four required claim changes; "
        "direct-only maintenance corrects two. In the waveform task, however, all checked methods have "
        "zero observed display violations under the strict query contract and correct every eligible old claim; "
        "transitive propagation adds no measured benefit. Contract violations include accurately stated "
        "off-target background facts, so these rates are not hallucination estimates. Full-graph "
        f"required-fact recall is {percent(min(recalls))}--{percent(max(recalls))}\\%, "
        f"and useful coverage is {percent(min(coverage))}--{percent(max(coverage))}\\%. "
        "A separate open-loop workload tests 1, 5, and 20 events/s. "
        f"The graph misses {macros['GraphFlagMisses']} of {macros['SystemsRepairTargets']} one-second flag targets "
        f"and {macros['GraphRepairMisses']} of {macros['SystemsRepairTargets']} five-second adequate-replacement targets. "
        f"None of the {macros['SystemsExplanations']} systems answers is complete. "
        "The results distinguish evidence withdrawal from useful regeneration and quantify implementation cost "
        "without treating graph storage as an intrinsic source of factuality.\n")
    (DIRECTORY/"abstract.tex").write_text(abstract)
    baseline_errors=[index[(source,"B0")]["case_error"]["value"] for source in SOURCES]
    (DIRECTORY/"reliability_findings.tex").write_text(
        "All checked methods have zero observed case and claim violations under the exact contract. "
        f"B0 case violation rates are {percent(min(baseline_errors))}--{percent(max(baseline_errors))}\\%. "
        f"M1 retains {percent(min(recalls))}--{percent(max(recalls))}\\% of answerable required facts, "
        f"but supplies all answerable slots for only {percent(min(coverage))}--{percent(max(coverage))}\\% "
        "of eligible queries. The checked controls have closely similar recall and coverage.\n")

    report = {"complete":True,"protocol_hash":frozen["protocol_hash"],"integrity":integrity,"macros":macros,"workloads":workload,
              "request_error_types":[{"dataset":key[0],"method":key[1],"phase":key[2],"error_type":key[3],"count":value}
                                     for key,value in sorted(request_errors.items())],
              "reason_components":[{"dataset":key[0],"method":key[1],"reason":key[2],"count":value} for key,value in sorted(reasons.items())],
              "generated_dependencies":[{"method":method,"claims":dependency_counts[(method,"claims")],
                                         "claims_with_parents":dependency_counts[(method,"parent_claims")]} for method in METHODS],
              "dependency_only_changes":[{"dataset":source,"method":method,
                  **{key:dependency_only[(source,method,key)] for key in ("required","withdrawn","retained")}}
                  for source in SOURCES for method in METHODS],
              "contract_scope":{key:value for key,value in contract_scope.items() if key not in ("claims","inputs")},
              "database_accounting":database,"resources":resources,"automated_audit":audit,
              "audit_details":audit_details,
              "notes":["Reason components overlap; they cannot be summed into an error total",
                       "Token totals sum returned usage only; calls without usage have unknown server-side token cost, not zero cost",
                       "Contract violations include off-target background facts that pass exact checks at their own stated interval; the post-hoc breakdown leaves all primary metrics unchanged",
                       "The saved metric named initial_parse_failure includes all initial request/format errors; request_error_types preserves their logged categories",
                       "Dependency-only changes are descriptive counts of initially valid persistent claims whose later sole exact-check error is a declared parent dependency; the edge's semantic necessity is not independently established",
                       "Claims requiring correction are conditional on initially generated content",
                       "All model families and sources retained, including failures and negative findings"]}
    write_json("artifacts/analysis/publication.json",report)
    inputs=["artifacts/analysis/minimum_v1/summary.json","artifacts/analysis/streaming_v1/summary.json",
            "artifacts/analysis/resources.json","artifacts/audit/minimum_v1/summary.json",
            "artifacts/manifests/minimum_run.json","artifacts/manifests/core_validation.json",
            "artifacts/manifests/database_accounting.json","artifacts/analysis/publication.json",
            "artifacts/analysis/minimum_v1/contract_scope.json"]
    write_json("paper/generated/manifest.json",{"inputs":{path:digest_file(path) for path in inputs},
               "script":str(Path(__file__).relative_to(Path.cwd())),"script_sha256":digest_file(__file__),
               "tex_files":{str(path):digest_file(path) for path in DIRECTORY.glob("*.tex")}})
    write_json("artifacts/figures/streaming_manifest.json",{"input":"artifacts/analysis/streaming_v1/summary.json",
               "sha256":digest_file("artifacts/analysis/streaming_v1/summary.json"),"script_sha256":digest_file(__file__)})
    return report


if __name__ == "__main__":
    generate()
