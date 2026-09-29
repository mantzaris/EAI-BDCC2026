"""Generate design diagrams and inventory tables from recorded inputs."""
from pathlib import Path
from collections import Counter
import os
os.environ.setdefault("MPLCONFIGDIR", ".local/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from temporal_evidence.io import read_json, write_json, digest_file
from temporal_evidence.synthetic.fixtures import correction_fixture


def save(figure, name):
    target = Path("artifacts/figures")
    target.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "svg", "png"):
        figure.savefig(target/f"{name}.{extension}", bbox_inches="tight", dpi=200)
    plt.close(figure)


def architecture():
    figure, ax = plt.subplots(figsize=(8, 3.5))
    ax.set(xlim=(-.55, 8.15), ylim=(-.4, 3.8))
    ax.axis("off")
    boxes = {
        "source": (0, 2.7, "Immutable\nrecordings"),
        "features": (2.1, 2.7, "Windowed\nfeatures"),
        "store": (4.2, 2.7, "Evidence\nversions"),
        "maintenance": (6.3, 2.7, "Revision\npropagation"),
        "question": (0, 1.35, "Scoped\nquestion"),
        "generator": (2.1, 1.35, "CUDA claims\n(candidates)"),
        "check": (4.2, 1.35, "Validate\n+ one repair"),
        "display": (6.3, 1.35, "Displayed\ntext versions"),
        "oracle": (1.05, 0, "Independent\nevaluation"),
        "review": (5.25, 0, "Review actions\n+ history"),
    }
    width, height = 1.65, .75
    for key, (x, y, label) in boxes.items():
        face = "#e7f1f6" if key not in {"oracle", "review"} else "#f1f1f1"
        patch = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.035",
                              facecolor=face, edgecolor="#345266", linewidth=1,
                              linestyle="--" if key in {"oracle", "review"} else "-")
        ax.add_patch(patch)
        ax.text(x+width/2, y+height/2, label, ha="center", va="center", fontsize=11.5)
    def edge(a, b, start="right", end="left", label=None):
        x, y, _ = boxes[a]; u, v, _ = boxes[b]
        points = {"right": (x+width, y+height/2), "bottom": (x+width/2, y), "top": (x+width/2, y+height)}
        targets = {"left": (u, v+height/2), "bottom": (u+width/2, v), "top": (u+width/2, v+height)}
        p, q = points[start], targets[end]
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12, color="#4c6470", linewidth=1.1))
        if label:
            ax.text((p[0]+q[0])/2+.06, (p[1]+q[1])/2, label, fontsize=9, ha="left", va="center")
    for a, b in [("source", "features"), ("features", "store"), ("store", "maintenance"),
                 ("question", "generator"), ("generator", "check"), ("check", "display")]:
        edge(a, b)
    edge("maintenance", "display", "bottom", "top")
    edge("store", "check", "bottom", "top")
    edge("store", "generator", "bottom", "top")
    ax.plot([0, -.4, -.4, .85], [3.075, 3.075, .375, .375], color="#4c6470", linewidth=1.1)
    ax.add_patch(FancyArrowPatch((.85, .375), (1.05, .375), arrowstyle="-|>", mutation_scale=12, color="#4c6470"))
    edge("display", "review", "bottom", "top")
    save(figure, "architecture")


def symbolic_graph(core):
    records, revision = correction_fixture()
    records = {r.record_id: r for r in records}
    assessments = core["symbolic_modes"]["correction"]["M1"]["assessments"]
    positions = {"a": (0, 1.9), "b": (0, .6), "alternative": (0, -1),
                 "difference": (1.8, 1.7), "direct_claim": (3.6, 2.7),
                 "downstream_claim": (3.6, 1.35), "or_claim": (3.6, -.05), "unaffected": (3.6, -1.45)}
    names = {"a": "Target a", "b": "Prior b", "alternative": "Other", "difference": "a − b",
             "direct_claim": "Direct", "downstream_claim": "Indirect",
             "or_claim": "OR claim", "unaffected": "Baseline"}
    figure, axes = plt.subplots(1, 2, figsize=(6.8, 4.3))
    figure.subplots_adjust(wspace=.17)
    for after, ax in enumerate(axes):
        ax.set(xlim=(-.95, 4.65), ylim=(-2.05, 3.3)); ax.axis("off")
        ax.set_title("After correction" if after else "Before correction", fontsize=13, pad=15)
        patches = {}
        for identifier, (x, y) in positions.items():
            record = records[identifier]
            state = assessments.get(identifier, {}).get("state", "supported") if after else "supported"
            value = revision.value if after and identifier == "a" else assessments.get(identifier, {}).get("value", record.value) if after and identifier == "difference" else record.value
            label = f"{names[identifier]}\n{value:g}"
            if record.record_type == "claim":
                label += "\nretain" if state == "supported" else "\nwithdraw"
            color = "#f6d9cd" if state != "supported" else "#dcece7" if record.record_type == "claim" else "#e8edf2"
            width = 1.65 if record.record_type == "claim" else 1.05 if identifier == "difference" else 1.45
            height = 1.0 if record.record_type == "claim" else .72
            patch = FancyBboxPatch((x-width/2,y-height/2),width,height,boxstyle="round,pad=.02",
                                  facecolor=color,edgecolor="#60717a",linewidth=.8,zorder=3)
            ax.add_patch(patch)
            ax.text(x, y, label, ha="center", va="center", fontsize=11,zorder=4)
            patches[identifier] = patch
        for identifier, position in positions.items():
            for dependency in records[identifier].source_ids:
                if dependency in positions:
                    ax.add_patch(FancyArrowPatch(position, positions[dependency], patchA=patches[identifier],
                        patchB=patches[dependency], arrowstyle="->", mutation_scale=13, color="#8a9194", linewidth=1,
                        shrinkA=3, shrinkB=3, zorder=2))
    save(figure, "symbolic_correction")


def design_tables():
    directory = Path("paper/generated"); directory.mkdir(parents=True, exist_ok=True)
    inputs = ["artifacts/manifests/minimum_run.json", "artifacts/manifests/core_validation.json"]
    frozen = read_json(inputs[0])
    lines = [r"\begin{tabular}{lrrrrr}", r"\toprule",
             r"Source & Dev/test subjects & Test episodes & Scenarios & Cases & Raw values \\", r"\midrule"]
    inventory = []
    names = {"synthetic": "Synthetic", "wesad": "WESAD", "ppg_dalia": "PPG-DaLiA"}
    for source in ("synthetic", "wesad", "ppg_dalia"):
        path = f"artifacts/manifests/{source}_episodes.json"; inputs.append(path)
        episodes = read_json(path)
        test = [r for r in episodes if r["split"] == "test"]
        prepared = [read_json(r["path"]) for r in test]
        inputs.extend(r["path"] for r in test)
        row = {"dataset": source, "development_subjects": len({r["subject"] for r in episodes if r["split"] == "development"}),
               "test_subjects": len({r["subject"] for r in test}), "test_episodes": len(test), "scenarios": len(test)*4,
               "cases": sum(c["dataset"] == source for c in frozen["cases"]),
               "raw_scalar_values_processed": sum(p["raw_samples_processed"] for p in prepared),
               "unique_original_scalar_values": sum(p["unique_source_scalar_samples"] for p in prepared),
               "derived_records_ingested_per_method": sum(len(v["events"]) for p in prepared for v in p["variants"].values())}
        inventory.append(row)
        lines.append(f"{names[source]} & {row['development_subjects']}/{row['test_subjects']} & {len(test)} & {row['scenarios']} & {row['cases']:,} & {row['raw_scalar_values_processed']:,} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (directory/"inventory_table.tex").write_text("\n".join(lines)+"\n")
    methods = [
        ("B0", "Indexed records", "No", "No", "No"),
        ("B1", "Indexed records", "Yes", "Direct", "One"),
        ("B2", "Neo4j", "Yes", "Direct", "One"),
        ("M1", "Neo4j", "Yes", "Full", "One"),
        ("B3", "SQLite + recursion", "Yes", "Full", "One"),
    ]
    lines = [r"\begin{tabular}{lllll}", r"\toprule", r"ID & Storage & Checks & Maintenance & Repair allowance \\", r"\midrule"]
    lines.extend(" & ".join(row)+r" \\" for row in methods)
    lines += [r"\bottomrule", r"\end{tabular}"]
    (directory/"method_table.tex").write_text("\n".join(lines)+"\n")
    write_json("artifacts/analysis/design_inventory.json", inventory)
    return inputs


def generate():
    plt.rcParams.update({"pdf.fonttype": 42, "svg.fonttype": "none", "font.family": "DejaVu Sans"})
    inputs = design_tables()
    architecture()
    symbolic_graph(read_json("artifacts/manifests/core_validation.json"))
    write_json("artifacts/figures/design_manifest.json", {
        "inputs": {path: digest_file(path) for path in inputs},
        "script": "src/temporal_evidence/analysis/design_figures.py",
        "script_sha256": digest_file(__file__),
        "outputs": ["architecture", "symbolic_correction", "paper/generated/inventory_table.tex", "paper/generated/method_table.tex"],
        "scope": "design schematic and exact symbolic fixture, separate from held-out physiological outcomes"})


if __name__ == "__main__":
    generate()
