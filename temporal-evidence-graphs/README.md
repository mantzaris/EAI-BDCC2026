# Temporal Evidence Graphs

Working project for a new paper for [EAI BDCC 2026](https://bdcc-conf.eai-conferences.org/2026/).
The title is provisional; the concrete research plan is forthcoming.

## Research question

> When an observation is corrected, becomes outdated, or fails a quality check,
> can a temporal evidence graph identify and repair the generated explanations
> that depend on it, while preserving useful answers and keeping latency low?

The initial direction is to use graph databases to build knowledge graphs with
temporal evidence and dependencies between observations and generated explanations.
Database selection, graph schema, repair methods, datasets, baselines, and evaluation
protocols will follow the research plan.

## Project status

RunPod gateway and direct SSH access verified on 28 September 2026. See
[connection instructions and environment observations](docs/runpod.md).
Implementation and experiments await the research plan.

This directory contains the new paper's work within the shared repository. The
previous paper is in [`../congestion-onset-graphs/`](../congestion-onset-graphs/README.md).
