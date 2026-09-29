"""Prospective case construction and immutable protocol freezing."""
from dataclasses import asdict
from pathlib import Path
import yaml
from temporal_evidence.io import digest_file,digest_object,read_json,write_json,utc_now
from temporal_evidence.schema import Query,Record
from temporal_evidence.replay.temporal import admissible_evidence

METHODS=("B0","B1","B2","M1","B3")
VARIANTS=("clean","channel_fault","delayed","correction")
DISPLAY_QUANTITIES={"eda_median","eda_iqr","eda_missing_fraction","eda_clipping_fraction",
                    "acceleration_magnitude_sd","pulse_frequency_bpm","respiration_frequency_per_min"}
QUESTIONS={
 "development":{
  "current_evidence":"Report the target EDA median and its difference from the preceding 120-second EDA median (target minus earlier).",
  "evidence_sufficiency":"Report the target EDA median and EDA missing fraction. State which requested value is unavailable instead of guessing.",
  "conflict_timing":"Compare the EDA medians in the target and preceding 120-second intervals: report the target median and the difference. Different intervals alone do not establish sensor conflict.",
  "revision_impact":"Report the target EDA median, marking it revised only if an explicit revision is visible, and report target acceleration magnitude variability. State any missing requested evidence."},
 "test":{
  "current_evidence":"For the requested window, give the EDA median and the signed change from the median over the immediately preceding 120 seconds.",
  "evidence_sufficiency":"Which requested measurements are available? Give the window's EDA median and its missing-sample fraction, identifying unavailable values explicitly.",
  "conflict_timing":"Describe the EDA median for this window and its difference from the earlier 120-second interval. Distinguish a change across intervals from a disagreement between simultaneous sensors.",
  "revision_impact":"Using the currently available versions, give the EDA median (identify an explicit revision if present) and acceleration magnitude variability for the target window. Identify missing evidence without inventing values."}}


def load_config(path="configs/minimum_study.yaml"):
    return yaml.safe_load(Path(path).read_text())


def episode_rows(split):
    rows=[]
    for dataset in ("synthetic","wesad","ppg_dalia"):
        rows.extend(row for row in read_json(f"artifacts/manifests/{dataset}_episodes.json") if row["split"]==split)
    return rows


def make_cases(split):
    cases=[]
    for episode in episode_rows(split):
        for variant in VARIANTS:
            for checkpoint,offset in enumerate((1,31,91)):
                for method in METHODS:
                    cases.append({"case_id":f"{episode['episode_id']}-{variant}-c{checkpoint}-{method}",
                                  "episode_id":episode["episode_id"],"dataset":episode["dataset"],"subject":episode["subject"],
                                  "family":episode["family"],"split":split,"variant":variant,"checkpoint":checkpoint,
                                  "method":method,"knowledge_time":episode["end"]+offset,
                                  "episode_path":episode["path"],"episode_sha256":episode["sha256"]})
    return cases


def query_evidence(case,episode):
    query=Query(case["dataset"],case["subject"],"session_1",episode["start"],episode["end"],case["knowledge_time"],
                family=case["family"],question=QUESTIONS[case["split"]][case["family"]])
    events=[Record.from_dict(item) for item in episode["variants"][case["variant"]]["events"]]
    evidence=[r for r in admissible_evidence(events,query)
              if ((r.event_start_seconds,r.event_end_seconds)==(episode["start"],episode["end"]) and r.quantity in DISPLAY_QUANTITIES)
              or (r.quantity=="eda_median" and r.event_end_seconds==episode["start"] and r.event_start_seconds==episode["start"]-120)]
    return query,evidence,events


def protocol_files():
    files=list(Path("configs").glob("*.yaml"))+[Path("pyproject.toml")]
    for part in ["data","features","generation","replay","storage","validation","synthetic","evaluation"]:
        files.extend(Path(f"src/temporal_evidence/{part}").glob("*.py"))
    files += [Path(f"src/temporal_evidence/{name}.py") for name in ["schema","study","experiment","io"]]
    return {str(path):digest_file(path) for path in sorted(files)}


def freeze(config_path="configs/minimum_study.yaml"):
    destination=Path("artifacts/manifests/minimum_run.json")
    if destination.exists():
        raise FileExistsError("A frozen manifest already exists; do not overwrite it")
    config=load_config(config_path)
    environment=read_json("artifacts/manifests/environment.json")
    core=read_json("artifacts/manifests/core_validation.json")
    pilot=read_json("artifacts/manifests/pilot.json")
    model=read_json("artifacts/manifests/model.json")
    assert core["passed"] and core["real_neo4j"]
    assert pilot["initial_cases"]>=100 and pilot["all_methods_produced_output"]
    assert pilot["config_sha256"]==digest_file(config_path)
    assert model["status"]=="downloaded" and model["revision"]==config["model"]["revision"]
    cases=make_cases("test")
    assert len(cases)==3600 and len({case["case_id"] for case in cases})==3600
    assert all(sum(case["dataset"]==source for case in cases)==1200 for source in config["datasets"])
    for row in episode_rows("test"):
        assert digest_file(row["path"])==row["sha256"]
    frozen={"run_id":"minimum_v1","frozen_at":utc_now(),"config":config,"config_sha256":digest_file(config_path),
            "source_hashes":protocol_files(),"model":model,"environment":environment,"cases":cases,
            "initial_calls":len(cases),"maximum_repair_calls":sum(case["method"]!="B0" for case in cases),
            "principal_contrasts":[["M1","B2","correction"],["M1","B1","case_error_and_fact_recall"]],
            "systems_contrast":["M1","B3"],"uncertainty":"2000 paired subject-cluster bootstrap resamples; pointwise 95% intervals; no p-values"}
    frozen["protocol_hash"]=digest_object(frozen)
    write_json(destination,frozen)
    write_json("artifacts/manifests/development_cases.json",make_cases("development"))
    return frozen


def verify_frozen(manifest):
    for path,expected in manifest["source_hashes"].items():
        if digest_file(path)!=expected:
            raise ValueError(f"Frozen runtime source changed: {path}")
    for path,expected in {(c["episode_path"],c["episode_sha256"]) for c in manifest["cases"]}:
        if digest_file(path)!=expected:
            raise ValueError(f"Frozen episode changed: {path}")
