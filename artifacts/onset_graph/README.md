# Durable onset/graph checkpoints

All 187 compact `.pt.gz` files in `study01` are versioned derived artifacts, including unsuccessful tuning fits, selected replicates, learned association graphs and historical compact references. The [manifest](../../manifests/onset_graph/artifacts.json) gives file hashes and byte counts. Every file was copied locally and matched against the remote GPU copy. The main frozen anchor hash is `34f020d464c52bf64fff9c5b1a465404e652898948b0e42521a23229e32df2cb`.

Checkpoints contain learned parameters and transformations. Original distance adjacency and regional membership are reconstructed from the private verified `data/processed/pilot_inputs.npz`; raw observations remain in private `data/raw/pems-bay.h5`. Neither raw file is included here. No original missing sklearn artifact is reconstructed from saved probabilities. Prior A_T/B/C/D compact reference parameters live in `study01/references`; the new common anchor is `study01/main/anchor.pt.gz`, distinctly named.

Use the recorded CUDA environment (`environment.residual-gpu.lock`, PyTorch2.8.0+cu128 on RTX6000 Ada). `load_weights()` uses `weights_only=True`, maps to CUDA, and validates missing graph-buffer keys when rebuilding corrections. Baseline state contains bin cuts, tree values and fitted feature free speeds. Model metadata in `results/onset_graph/study01/main/models_with_nulls.json` contains each kind, alpha, calibration, cutoff, graph key and checkpoint path. Regenerate nulls from fixed seeds and the private original graph; load F from `dependency.pt.gz`. No Pod-only trained state is required.

The actual main replay job used source `70e03d050022e294340712071c0d8a261fb04438` and recovered all90 raw/calibrated prediction vectors exactly. The later supplementary source changes no prediction behavior. Completed markers are immutable, so a fresh-output replay should be prepared as follows **only under future compute authorization**:

```bash
ONSET_PYTHON=/workspace/EAI-BDCC2026-stage1/.venv/bin/python
ONSET_SHA=$(git rev-parse HEAD)
mkdir -p results/onset_graph/reload02/main artifacts/onset_graph/reload02/main
cp artifacts/onset_graph/study01/main/*.pt.gz artifacts/onset_graph/reload02/main/
cp results/onset_graph/study01/main/models_with_nulls.json results/onset_graph/reload02/main/
cp results/onset_graph/study01/main/validation_raw_predictions.csv.gz results/onset_graph/reload02/main/
cp results/onset_graph/study01/main/validation_calibrated_predictions.csv.gz results/onset_graph/reload02/main/
$ONSET_PYTHON scripts/onset_budget.py --reserve 180 --phase core --source-sha "$ONSET_SHA" -- \
  $ONSET_PYTHON scripts/run_onset_graph.py --mode replay --run-id reload02 --source-sha "$ONSET_SHA"
```

Keep the original `study01` paths because the immutable model metadata references those versioned files. Retain the existing compute ledger across checkouts; never reset it for replay. This documents the same tested reload code path, without deleting its completed historical marker. It reads validation only, with a forbidden-test guard. This command is documentation, not authorization or a scheduled job.
