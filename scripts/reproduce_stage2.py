"""Reproduce CPU-only Stage 2 in a new directory, preserving all historical results."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, help='New empty reproduction directory')
    args = parser.parse_args()
    root = Path.cwd(); target = Path(args.directory).resolve()
    target.mkdir(parents=True, exist_ok=False)
    sha = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
    archive = subprocess.check_output(['git','archive','--format=tar',sha])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        for member in stream.getmembers():
            if member.name.startswith(('results/stage2/', 'manifests/stage2/')): continue
            if member.isfile():
                path = target/member.name
                if target not in path.resolve().parents: raise ValueError('Unsafe archive path')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(stream.extractfile(member).read())
    (target/'data/processed').mkdir(parents=True)
    (target/'data/raw').symlink_to(root/'data/raw', target_is_directory=True)
    (target/'data/processed/pilot_inputs.npz').symlink_to(root/'data/processed/pilot_inputs.npz')
    (target/'results/stage2').mkdir(parents=True)
    (target/'manifests/stage2').mkdir(parents=True)
    env = dict(os.environ, PYTHONPATH=str(target/'src'), OPENBLAS_NUM_THREADS='4', OMP_NUM_THREADS='4', CUDA_VISIBLE_DEVICES='')
    jobs = []; started = time.perf_counter()
    for script in ('stage2_compare.py','stage2_inner_diagnosis.py','stage2_repair.py','stage2_enclosures.py',
                   'stage2_tightening.py','stage2_support_and_metrics.py','stage2_cost_audit.py','build_stage2_figures.py'):
        before = time.perf_counter()
        with (target/'results/stage2'/('reproduce_'+script+'.log')).open('w') as log:
            result = subprocess.run(['python3',str(target/'scripts'/script)], cwd=target, env=env,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=900)
        jobs.append(dict(script=script, returncode=result.returncode, elapsed_seconds=time.perf_counter()-before))
        print(script, result.returncode, flush=True)
        if result.returncode: raise RuntimeError('Reproduction failed; see preserved log in '+str(target))
    import numpy as np
    import pandas as pd
    differences = {}
    for filename in ('matched_predictions.csv','simulator_predictions.csv','tightening_widths.csv'):
        original = pd.read_csv(root/'results/stage2'/filename)
        reproduced = pd.read_csv(target/'results/stage2'/filename)
        columns = ['probability','calibrated_probability'] if 'predictions' in filename else ['mean_radius','unresolved']
        delta = max(float(np.max(np.abs(original[c].to_numpy()-reproduced[c].to_numpy()))) for c in columns)
        differences[filename] = delta
        if delta > 1e-7: raise ArithmeticError('Scientific reproduction discrepancy: '+filename)
    record = dict(source_sha=sha, cpu_wall_seconds=time.perf_counter()-started, gpu_seconds=0, jobs=jobs,
                  maximum_differences=differences, cuda_disabled=True, complete=True, test_access=False,
                  directory=str(target), note='Fresh directory copied from committed source; original data linked read-only by convention; all new artifacts local to reproduction directory.')
    (root/'manifests/stage2/reproduction.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__ == '__main__': main()
