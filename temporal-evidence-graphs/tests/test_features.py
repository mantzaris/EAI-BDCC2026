import numpy as np
from temporal_evidence.features.extract import spectral_rate, summarize, window_records
from temporal_evidence.synthetic.generator import generate_subject
from temporal_evidence.data.adapters import aligned_reference_interval,signal_units


def test_frequency_of_known_signal():
    t = np.arange(30*128)/128
    rate,quality = spectral_rate(np.sin(2*np.pi*1.2*t),128,(.67,3))
    assert abs(rate-72)<1e-6 and quality>.99
    assert spectral_rate(np.full(100,np.nan),4,(.1,.6))[0] is None


def test_numeric_summary_and_missingness():
    result = summarize(np.array([1,2,3,4,np.nan]),"eda",4)
    assert result["eda_median"][0] == 2.5
    assert result["eda_iqr"][0] == 1.5
    assert abs(result["missing_fraction"][0]-.2)<1e-12


def test_completed_window_cannot_read_future_samples():
    base = np.ones(100)
    entry = {"subject":"V101","sha256":"fixture","path":"fixture"}
    a,_ = window_records("synthetic",entry,{"eda":base},{"eda":1},{"eda":"uS"},20,50)
    base[50:] = 1000
    b,_ = window_records("synthetic",entry,{"eda":base},{"eda":1},{"eda":"uS"},20,50)
    assert a == b


def test_synthetic_determinism_and_independent_namespace():
    first,oracle = generate_subject(101,duration=60)
    repeated,_ = generate_subject(101,duration=60)
    held_out,_ = generate_subject(1001,duration=60)
    assert all(np.array_equal(first[k],repeated[k]) for k in first)
    assert not np.array_equal(first["motion"],held_out["motion"])
    assert first["cardiac"].shape == (60*128,)


def test_reference_window_alignment():
    assert aligned_reference_interval(0) == (0,8)
    assert aligned_reference_interval(10) == (20,28)


def test_dataset_specific_synchronized_motion_units():
    assert signal_units("ppg_dalia")["motion"] == "g"
    assert signal_units("wesad")["motion"] == "1/64g"


def test_replay_fault_provenance_matches_separate_array(tmp_path,monkeypatch):
    from temporal_evidence.data.prepare import make_variants
    from temporal_evidence.features.extract import summarize
    from temporal_evidence.io import digest_file
    monkeypatch.chdir(tmp_path)
    signals={"eda":np.linspace(0,5,400)}
    entry={"subject":"V101","sha256":"original_hash","path":"original.npz"}
    variants,_=make_variants("synthetic",entry,signals,{"eda":1},{"eda":"uS"},200,0)
    events=variants["channel_fault"]["events"]
    feature=next(r for r in events if r["quantity"]=="eda_median" and r["version"]==2)
    observation=next(r for r in events if r["record_id"]==feature["source_ids"][0])
    meta=observation["metadata"]
    assert digest_file(meta["path"])==meta["file_sha256"]
    values=np.load(meta["path"])
    assert np.isnan(values[-15:]).all()
    assert summarize(values,"eda",1)["eda_median"][0]==feature["value"]
    assert not np.isnan(signals["eda"]).any()
