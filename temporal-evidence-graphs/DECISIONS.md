# Protocol decisions

## 2026-09-28 — Initial execution

- User authorized implementation and direct pushes to `main`. No branches.
- Minimum study only: exactly synthetic_physiology_streams_v1, WESAD, and
  PPG-DaLiA; B0, B1, B2, M1, B3; 20 test episodes per source and four variants.
- Available GPU is RTX 5090, 32,607 MiB VRAM. Test BF16 Qwen3-8B at reduced
  concurrency before considering any quantization; no CPU model offload.
- Available disk is an approximately 75 GiB container overlay, below the suggested
  100 GB persistent allocation. Store original archives plus selected synchronized
  recording files, monitor free space, and copy manifests and experimental outputs
  to the local repository incrementally. Persistence across pod deletion is not
  assumed. Do not create another paid resource.
- Docker and Java are absent. Install Neo4j Community as a local tar distribution
  with a dedicated Java runtime. Bind research services to loopback.
- Freeze all selected subjects before inspecting test outcomes. Keep test waveforms
  separate from development tuning; structural inventories may include both splits.
- Progress percentages estimate completion of the plan's gates, not scientific
  success or percentage of generator calls. Track actual call counts separately.

## 2026-09-28 — Acquisition and runtime repairs

- WESAD's author HTML retains a commented-out obsolete archive link. Resolve only
  active links. HTTP/1.1 avoids a pod-side HTTP/2 download failure.
- WESAD downloaded locally; original archive and synchronized recordings are hashed.
  Slow pod transfers motivate local host-side numerical feature extraction. Neural
  generation remains exclusively on the pod GPU. Numerical extraction is not a
  trained model; compare a fixed sample with CUDA calculations before freezing.
- Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218` downloaded through
  parallel resumable byte ranges, independently of inference installation.
- Reuse the pod's existing PyTorch 2.8.0+cu128 and CUDA libraries through a Python
  3.12 virtual environment with system site packages. This replaces the initial
  unfinished Python 3.11 environment, avoiding redundant CUDA downloads. Record
  the entire resolved environment and test GPU placement before any generation.
- The generated explanation is required to concatenate its claim sentences.
  Checked methods retain only supported claim sentences after the bounded repair.
  Keep original paragraph output and discrepancies for evaluation. Lexical checks
  are limited; a separately pinned GPU model will perform the required auxiliary
  fidelity audit. No human annotation is claimed.
- UCI's PPG-DaLiA packaged and legacy archive downloads stalled repeatedly. Use the
  unchanged original archive linked from the authors' PPG-DaLiA page, and record
  both the UCI CC BY 4.0 statement and the author's non-commercial research terms.
- Select two episodes at 25% and 75% of each recording's common channel duration,
  rounded down to the 5-second update grid. Require at least 600 seconds; all
  acquired recordings satisfy this. Selection uses duration, not model failures,
  protocol labels, or held-out outcomes. Target windows are 30 seconds and comparison
  windows are the strictly preceding 120 seconds. Prepare seven 5-second updates
  ending at each target time, with four paired replay variants.
- Native wrist EDA is reported in uS and wrist acceleration in recorded 1/64g
  units. Synthetic units are explicitly marked. Spectral pulse/respiration frequency
  estimates require concentration >= 0.5; these are simple recording summaries,
  not validated physiological truth or a replacement for reference heart rates.
- WESAD's extracted synchronized pickles were verified and removed as redundant
  cache copies after preparation; the original hashed archive is retained. Adapters
  support direct reading from that archive. This recovered 12.88 GiB of local disk.
- Use pip for the system-site-packages overlay: uv's installer redownloaded existing
  CUDA dependencies. The tested final environment will be recorded before freezing.
