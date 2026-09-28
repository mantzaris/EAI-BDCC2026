"""Read only original, hashed synchronized recordings; never expose labels."""
from __future__ import annotations

import pickle
import re
from pathlib import Path
import numpy as np

from temporal_evidence.io import digest_file, read_json, write_json

RATES = {"chest": {"ACC":700,"ECG":700,"EDA":700,"EMG":700,"Resp":700,"TEMP":700},
         "wrist": {"ACC":32,"BVP":64,"EDA":4,"TEMP":4}}
UNITS = {"eda":"uS", "motion":"1/64g", "cardiac":"recorded_BVP_unit", "respiration":"recorded_RESP_unit"}


def natural_key(value):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def inventory(dataset):
    paths = sorted(Path(f"data/raw/{dataset}/recordings").rglob("S*.pkl"), key=lambda p:natural_key(p.stem))
    if len(paths) != 15 or len({p.stem for p in paths}) != 15:
        raise ValueError(f"Expected 15 unique {dataset} participants, found {len(paths)}")
    subjects = [path.stem for path in paths]
    permutation = np.random.Generator(np.random.PCG64(20260928)).permutation(len(subjects))
    development = [subjects[int(i)] for i in permutation[:5]]
    test = [subjects[int(i)] for i in permutation[5:]]
    split = {"seed":20260928,"generator":"numpy.random.Generator(PCG64)","sorted_ids":subjects,
             "development":development,"test":test}
    split_path = Path(f"artifacts/manifests/{dataset}_split.json")
    if split_path.exists() and read_json(split_path) != split:
        raise ValueError("Refusing to alter an existing subject split")
    write_json(split_path, split)
    # Only array structure is inventoried; outcomes are not inspected for selection.
    entries = []
    for path in paths:
        with path.open("rb") as stream:
            original = pickle.load(stream, encoding="latin1")
        content = original.get("data", original)
        identity = str(content.get("subject", path.stem))
        if identity != path.stem:
            raise ValueError(f"Subject mismatch: {path.stem} versus {identity}")
        channels = []
        for location, values in content["signal"].items():
            for channel, array in values.items():
                rate = RATES[location].get(channel, 700 if location == "chest" else None)
                if rate is None:
                    raise ValueError(f"Undocumented sampling rate {location}/{channel}")
                channels.append({"location":location,"name":channel,"shape":list(array.shape),
                                 "rate_hz":rate,"duration_seconds":len(array)/rate,
                                 "excluded_dummy":dataset=="ppg_dalia" and location=="chest" and channel.upper() in {"EDA","EMG","TEMP"}})
        entries.append({"subject":path.stem,"path":str(path),"sha256":digest_file(path),
                        "split":"development" if path.stem in development else "test", "channels":channels,
                        "non_runtime_fields":[key for key in content if key not in {"subject","signal"}]})
    manifest = {"dataset":dataset,"synchronization":"Author-provided synchronized pickle; relative session seconds",
                "wrist_units":UNITS,"reference_targets_in_runtime":False,"subjects":entries}
    write_json(f"artifacts/manifests/{dataset}_inventory.json", manifest)
    return manifest


def load_signals(dataset, entry):
    path = Path(entry["path"])
    if dataset == "synthetic":
        with np.load(path) as data:
            signals = {name: data[name].copy() for name in data.files}
        units = {"eda":"synthetic_uS","motion":"synthetic_g","cardiac":"synthetic_amplitude","respiration":"synthetic_amplitude"}
        return signals, entry["rates"], units
    # Paths come from the acquisition inventory of the official archives, never from model output.
    with path.open("rb") as stream:
        original = pickle.load(stream, encoding="latin1")
    content = original.get("data", original)
    wrist, chest = content["signal"]["wrist"], content["signal"]["chest"]
    respiration = chest.get("Resp", chest.get("RESP"))
    if respiration is None:
        raise ValueError("Documented respiration channel absent")
    signals = {"eda":np.asarray(wrist["EDA"]).reshape(-1), "motion":np.asarray(wrist["ACC"]),
               "cardiac":np.asarray(wrist["BVP"]).reshape(-1), "respiration":np.asarray(respiration).reshape(-1)}
    return signals, {"eda":4,"motion":32,"cardiac":64,"respiration":700}, UNITS.copy()


def aligned_reference_interval(index):
    """PPG-DaLiA README III.3: 8-second windows with a 2-second shift."""
    return 2*index, 2*index+8
