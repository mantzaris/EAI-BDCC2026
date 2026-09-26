# EAI BDCC research papers

Each paper has a self-contained directory under `papers/`. Code, configurations,
results, reports, manuscript sources and local private data stay with that paper.

| Paper | Project | Manuscript |
|---|---|---|
| Graph Representations for Congestion Onset Prediction: A Controlled Comparative Study | [papers/congestion-onset-graphs](papers/congestion-onset-graphs/README.md) | [LaTeX](papers/congestion-onset-graphs/manuscript/main.tex), [PDF](papers/congestion-onset-graphs/manuscript/graph_representations_draft.pdf) |

Compile the existing paper from the repository root:

```sh
make -C papers/congestion-onset-graphs/manuscript
```

Run its other documented commands from its project directory:

```sh
cd papers/congestion-onset-graphs
```

A second paper can be created at `papers/<descriptive-paper-name>/`, beside
`congestion-onset-graphs/`, with its own code, dependencies and manuscript.
The repository remains on one shared Git history; do not initialize a nested
repository. The root [license](LICENSE) and ignore rules remain shared.

The existing paper was relocated on 25 September 2026. Historical report paths,
artifact manifests and commands are relative to its project directory unless
they explicitly refer to a Git revision or a recorded remote environment.
Older commits retain the original repository-root layout. Scientific artifacts,
private data and pre-existing manuscript edits were preserved; this reorganization
does not run or authorize experiments.
