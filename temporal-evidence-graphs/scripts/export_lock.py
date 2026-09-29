"""Pin the installed dependency closure of the tested application, including CUDA.

Run inside the pod environment after successful GPU/database verification.
The matching full environment snapshot is retained separately.
"""
from importlib import metadata
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

selected={}
pending=[("temporal-evidence",{"gpu","dashboard"})]
while pending:
    name,extras=pending.pop()
    name=canonicalize_name(name)
    if name in selected:
        continue
    distribution=metadata.distribution(name)
    selected[name]=distribution.version
    for value in distribution.requires or []:
        requirement=Requirement(value)
        if requirement.marker and not any(requirement.marker.evaluate({"extra":extra}) for extra in (extras|{""})):
            continue
        pending.append((requirement.name,set(requirement.extras)))
lines=["# Exact installed dependency closure; Python 3.12, Linux x86_64, CUDA 12.8.",
       "# Generated after actual GPU and database tests; see artifacts/manifests/requirements.actual.txt.",
       "--extra-index-url https://download.pytorch.org/whl/cu128"]
lines += [f"{name}=={version}" for name,version in sorted(selected.items()) if name!="temporal-evidence"]
Path("requirements.lock").write_text("\n".join(lines)+"\n")
print(f"Pinned {len(lines)-3} tested packages")
