# Temporal Evidence Graphs

Working project for a new paper for [EAI BDCC 2026](https://bdcc-conf.eai-conferences.org/2026/).
The title is provisional. The governing prospective protocol is
[Temporal_Evidence_Graphs_Codex_Research_Plan.md](Temporal_Evidence_Graphs_Codex_Research_Plan.md).

## Research question

> When an observation is corrected, becomes outdated, or fails a quality check,
> can a temporal evidence graph identify and repair the generated explanations
> that depend on it, while preserving useful answers and keeping latency low?

The initial direction is to use graph databases to build knowledge graphs with
temporal evidence and dependencies between observations and generated explanations.
The minimum study uses Neo4j Community and a strong indexed relational control,
with synthetic physiology, WESAD, and PPG-DaLiA. Five conditions distinguish fresh
generation, direct checking, and transitive maintenance.

## Project status

RunPod gateway and direct SSH access verified on 28 September 2026. See
[connection instructions and environment observations](docs/runpod.md).
Implementation is underway. [STATUS.md](STATUS.md) records completion gates,
commands, and remaining work; [DECISIONS.md](DECISIONS.md) records protocol choices.
No held-out model evaluation has run yet.

This directory contains the new paper's work within the shared repository. The
previous paper is in [`../congestion-onset-graphs/`](../congestion-onset-graphs/README.md).
