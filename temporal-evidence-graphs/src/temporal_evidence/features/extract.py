from __future__ import annotations
import time
import numpy as np
from temporal_evidence.schema import Record


def summarize(array, channel, rate):
    values = np.asarray(array, dtype=np.float64)
    missing = float(1-np.isfinite(values).mean()) if values.size else 1.
    finite = values[np.isfinite(values)]
    if not len(finite):
        return {"missing_fraction":(missing,"fraction"),"clipping_fraction":(None,"fraction")}
    # Repeated extrema are a numerical quality cue, not an oracle sensor-failure label.
    clipping = float(max(np.mean(finite==finite.min()), np.mean(finite==finite.max())))
    result = {"missing_fraction":(missing,"fraction"),"clipping_fraction":(clipping,"fraction")}
    if channel == "eda":
        result.update(eda_median=(float(np.median(finite)),None),
                      eda_iqr=(float(np.quantile(finite,.75)-np.quantile(finite,.25)),None))
    elif channel == "motion":
        magnitude = np.sqrt(np.sum(values**2, axis=1))
        result["acceleration_magnitude_sd"] = (float(np.nanstd(magnitude)),None)
    else:
        result[f"{channel}_iqr"] = (float(np.quantile(finite,.75)-np.quantile(finite,.25)),None)
        quantity = "pulse_frequency_bpm" if channel == "cardiac" else "respiration_frequency_per_min"
        value, concentration = spectral_rate(values.reshape(-1),rate,(.67,3.0) if channel=="cardiac" else (.1,.6))
        result[quantity] = (value,"per_min")
        result[f"{channel}_spectral_concentration"] = (concentration,"fraction")
    return result


def spectral_rate(values, rate, band):
    if len(values)<rate*20 or not np.isfinite(values).all() or np.std(values)<1e-8:
        return None,0.
    centered = values-np.mean(values)
    spectrum = np.abs(np.fft.rfft(centered*np.hanning(len(values))))**2
    frequencies = np.fft.rfftfreq(len(values),1/rate)
    indices = np.flatnonzero((frequencies>=band[0]) & (frequencies<=band[1]))
    if not len(indices) or spectrum[indices].sum()==0:
        return None,0.
    best = indices[np.argmax(spectrum[indices])]
    concentration = float(spectrum[max(0,best-1):best+2].sum()/spectrum[indices].sum())
    return (float(frequencies[best]*60) if concentration>=.5 else None), min(concentration,1.)


def window_records(dataset, entry, signals, rates, units, start, end, ingestion=None, overrides=None):
    records = []
    elapsed = time.perf_counter()
    subject = entry["subject"]
    for channel, full_signal in signals.items():
        rate = rates[channel]
        first, stop = round(start*rate), round(end*rate)
        if stop>len(full_signal) or first<0:
            raise ValueError(f"Window outside {subject}/{channel}")
        window = (overrides or {}).get(channel, full_signal[first:stop])
        source_id = f"{dataset}/{subject}/{start:g}-{end:g}/{channel}/raw"
        common = dict(dataset_id=dataset,subject_id=subject,session_id="session_1",event_start_seconds=start,
                      event_end_seconds=end,ingested_at_seconds=end+1 if ingestion is None else ingestion)
        records.append(Record(record_id=source_id,logical_id=source_id,record_type="observation",**common,
                              metadata={"file_sha256":entry["sha256"],"path":entry["path"],"channel":channel,
                                        "sample_start":first,"sample_stop":stop,"rate_hz":rate}))
        for quantity,(value,unit) in summarize(window,channel,rate).items():
            name = f"{channel}_{quantity}" if quantity in {"missing_fraction","clipping_fraction"} else quantity
            logical = f"{dataset}/{subject}/{start:g}-{end:g}/{name}"
            records.append(Record(record_id=logical+"/v1",logical_id=logical,record_type="feature",**common,
                                  quantity=name,value=value,unit=unit or units[channel],source_ids=(source_id,),
                                  operator="measured",evidence_state="available" if value is not None else "missing",
                                  metadata={"extractor":"numpy_completed_window_v1","window_seconds":end-start}))
    return records, time.perf_counter()-elapsed
