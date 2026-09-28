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
