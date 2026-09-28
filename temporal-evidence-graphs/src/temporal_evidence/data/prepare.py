"""Select episodes by recording duration, before any held-out generation."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import yaml

from temporal_evidence.data.adapters import load_signals
from temporal_evidence.features.extract import window_records
from temporal_evidence.io import digest_file, digest_object, read_json, write_json

FAMILIES = ["current_evidence","evidence_sufficiency","conflict_timing","revision_impact"]
QUANTITIES = {"eda_median","eda_iqr","acceleration_magnitude_sd","eda_missing_fraction",
              "eda_clipping_fraction","pulse_frequency_bpm","respiration_frequency_per_min"}


def revised(record, time, version, **changes):
    return replace(record,record_id=record.logical_id+f"/v{version}",version=version,
                   ingested_at_seconds=time,supersedes_id=record.record_id,**changes)


def make_variants(dataset, entry, signals, rates, units, end, index):
    start = end-30
    base, extraction_seconds = window_records(dataset,entry,signals,rates,units,start-120,start)
    updates=[]
    for update_end in np.arange(end-30,end+1,5):
        window, seconds=window_records(dataset,entry,signals,rates,units,float(update_end)-30,float(update_end))
        updates.extend(window)
        extraction_seconds += seconds
    original=base+updates
    target=[r for r in original if r.quantity=="eda_median" and r.event_end_seconds==end][0]
    target_features=[r for r in original if r.record_type=="feature" and r.event_end_seconds==end and r.quantity in QUANTITIES]
    initial=original
    variants={}
    for variant in ("clean","channel_fault","delayed","correction"):
        events=list(initial)
        oracle={"variant":variant,"intervention_subject":entry["subject"],"intervention_interval":[start,end]}
        if variant=="clean":
            # A benign same-value revision, followed by another same-value update.
            second=revised(target,end+31,2)
            events.extend([second,revised(second,end+91,3)])
            oracle["observable_fault"]=False
        elif variant=="delayed":
            # Packet delay is visible only through absence and arrival timestamps.
            events=[replace(r,ingested_at_seconds=end+61) if r.record_id==target.record_id else r for r in events]
            oracle.update(delay_seconds=60,observable_fault=True)
        elif variant=="correction":
            second=revised(target,end+31,2,value=None if target.value is None else target.value+.5)
            third=revised(second,end+91,3,value=target.value,evidence_state=target.evidence_state)
            events.extend([second,third])
            oracle.update(offset=.5,observable_fault=False,correction_disclosed_at=end+91)
        else:
            rate=rates["eda"]
            altered=np.array(signals["eda"][round(start*rate):round(end*rate)],dtype=float,copy=True)
            family="missingness" if index%2==0 else "corruption"
            if family=="missingness":
                altered[-15*rate:]=np.nan
            else:
                altered+=.5
            altered_records,seconds=window_records(dataset,entry,signals,rates,units,start,end,overrides={"eda":altered})
            extraction_seconds+=seconds
            altered_by_quantity={r.quantity:r for r in altered_records if r.record_type=="feature" and r.quantity.startswith("eda_")}
            for old in target_features:
                if old.quantity in altered_by_quantity:
                    changed=altered_by_quantity[old.quantity]
                    second=revised(old,end+31,2,value=changed.value,evidence_state=changed.evidence_state,
                                   metadata={**old.metadata,"derived_replay_window":True})
                    events.extend([second,revised(second,end+91,3,value=old.value,evidence_state=old.evidence_state)])
            oracle.update(fault_family=family,dropout_seconds=15 if family=="missingness" else 0,
                          offset=.5 if family=="corruption" else 0,observable_fault=family=="missingness")
        # Evaluator metadata never appears in a runtime event record.
        variants[variant]={"events":[r.to_dict() for r in events],"evaluator_only":oracle}
    return variants,extraction_seconds


def prepare(config_path="configs/minimum_study.yaml", datasets=None):
    config=yaml.safe_load(Path(config_path).read_text())
    directory=Path("artifacts/prepared")
    directory.mkdir(parents=True,exist_ok=True)
    inventories={}
    for dataset in datasets or config["datasets"]:
        path=f"artifacts/manifests/{'synthetic' if dataset=='synthetic' else dataset+'_inventory'}.json"
        inventories[dataset]=read_json(path)
    report=[]
    for dataset,inventory in inventories.items():
        for entry in inventory["subjects"]:
            signals,rates,units=load_signals(dataset,entry)
            duration=min(len(signals[channel])/rates[channel] for channel in signals)
            if duration<600:
                raise ValueError(f"Predeclared two-episode eligibility fails: {dataset}/{entry['subject']}")
            subject_position=[e["subject"] for e in inventory["subjects"] if e["split"]==entry["split"]].index(entry["subject"])
            for episode_index,fraction in enumerate(config["episode_fractions"]):
                end=float(5*np.floor(duration*fraction/5))
                episode_id=f"{dataset}-{entry['subject']}-e{episode_index}"
                variants,seconds=make_variants(dataset,entry,signals,rates,units,end,subject_position*2+episode_index)
                payload={"episode_id":episode_id,"dataset":dataset,"subject":entry["subject"],"split":entry["split"],
                         "family":FAMILIES[(subject_position*2+episode_index)%4],"start":end-30,"end":end,
                         "source_sha256":entry["sha256"],"variants":variants,"feature_extraction_seconds":seconds,
                         "sampling_rates":rates,"raw_samples_processed":sum(round(180*rates[c])*np.asarray(signals[c]).shape[-1]
                            if np.asarray(signals[c]).ndim==2 else round(180*rates[c]) for c in signals)}
                path=directory/f"{episode_id}.json"
                write_json(path,payload)
                report.append({key:payload[key] for key in ("episode_id","dataset","subject","split","family","start","end","feature_extraction_seconds")}
                              | {"path":str(path),"sha256":digest_file(path)})
            print(f"Prepared {dataset}/{entry['subject']} ({entry['split']})",flush=True)
    for dataset in inventories:
        write_json(f"artifacts/manifests/{dataset}_episodes.json",[row for row in report if row["dataset"]==dataset])
    return report
