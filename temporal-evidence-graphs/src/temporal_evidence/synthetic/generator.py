from pathlib import Path
import numpy as np

from temporal_evidence.io import digest_file, write_json

RATES = {"cardiac": 128, "respiration": 32, "eda": 8, "motion": 32}


def generate_subject(seed: int, duration=1800) -> tuple[dict, dict]:
    streams = np.random.SeedSequence(seed).spawn(4)
    waveform = np.random.default_rng(streams[0])
    # Movement is sampled independently of the latent physiological state.
    activity = np.random.default_rng(streams[1])
    controls = np.array([0, 0, .7, .7, -.3, -.3, .5, .5, 0, 0], dtype=float)
    controls += waveform.normal(0, .05, size=len(controls))
    knots = np.linspace(0, duration, len(controls))
    baseline_cardiac = float(waveform.uniform(60, 85))
    baseline_resp = float(waveform.uniform(11, 17))
    baseline_eda = float(waveform.uniform(.7, 2.5))
    signals = {}
    for channel, rate in RATES.items():
        times = np.arange(duration * rate) / rate
        latent = np.interp(times, knots, controls)
        if channel == "cardiac":
            frequency = (baseline_cardiac + 12 * latent) / 60
            phase = 2 * np.pi * np.cumsum(frequency) / rate
            signal = np.sin(phase) + .35 * np.sin(2 * phase) + waveform.normal(0, .03, len(times))
        elif channel == "respiration":
            frequency = (baseline_resp + 3 * latent) / 60
            phase = 2 * np.pi * np.cumsum(frequency) / rate
            signal = (1 + .2 * latent) * np.sin(phase) + waveform.normal(0, .02, len(times))
        elif channel == "eda":
            signal = baseline_eda + .6 * latent + .00005 * times + waveform.normal(0, .015, len(times))
            for onset in waveform.uniform(0, duration, 20):
                elapsed = times - onset
                response = np.where(elapsed >= 0, np.exp(-np.maximum(elapsed, 0) / 8) - np.exp(-np.maximum(elapsed, 0)), 0)
                signal += float(waveform.uniform(.03, .2)) * response
        else:
            moving = activity.integers(0, 2, size=(duration + 59) // 60)[(times // 60).astype(int)]
            signal = activity.normal(0, .01, (len(times), 3))
            signal[:, 2] += 1
            signal += moving[:, None] * np.sin(2 * np.pi * times[:, None] * np.array([1.2, .7, 1.7])) * .15
        signals[channel] = np.asarray(signal, dtype=np.float32)
    oracle = {"seed": seed, "duration_seconds": duration, "sampling_rates": RATES,
              "latent_control_values": controls.tolist(), "latent_control_times": knots.tolist(),
              "cardiac_baseline": baseline_cardiac, "respiration_baseline": baseline_resp,
              "eda_baseline": baseline_eda, "seed_streams": {
                  "waveforms": streams[0].state, "motion": streams[1].state,
                  "fault_placement": streams[2].state, "question_selection": streams[3].state},
              "generation_seed": 20260928}
    return signals, oracle


def generate_all():
    output = Path("data/raw/synthetic")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"benchmark_id": "synthetic_physiology_streams_v1", "subjects": []}
    for split, seeds in [("development", range(101, 111)), ("test", range(1001, 1011))]:
        for seed in seeds:
            subject = f"V{seed}"
            path = output / f"{subject}.npz"
            signals, oracle = generate_subject(seed)
            if not path.exists():
                np.savez_compressed(path, **signals)
            write_json(f"data/evaluator/synthetic/{subject}.json", oracle)
            manifest["subjects"].append({"subject": subject, "split": split, "seed": seed,
                                         "path": str(path), "sha256": digest_file(path),
                                         "duration_seconds": 1800, "rates": RATES})
    write_json("artifacts/manifests/synthetic.json", manifest)
    return manifest
