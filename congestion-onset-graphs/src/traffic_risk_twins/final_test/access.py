"""Explicit committed-manifest authorization; older development guards stay intact."""
import datetime
import re
import subprocess
from pathlib import Path
import h5py
import numpy as np
import torch
from ..residual_gpu.data import PilotData, sha256, to_cuda, valid
from ..onset_graph.io import read, save


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def verify_files(manifest):
    for filename, record in manifest['files'].items():
        path = Path(filename)
        if not path.is_file() or path.stat().st_size != record['bytes'] or sha256(path) != record['sha256']:
            raise ValueError('Frozen artifact mismatch: ' + filename)


def committed_manifest(path, revision):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Full protocol commit required')
    contents = subprocess.check_output(['git', 'show', revision + ':' + str(path)])
    if contents != Path(path).read_bytes():
        raise ValueError('Manifest differs from designated commit')
    # The executable tree must also be committed and unchanged.
    manifest = read(path)
    for filename in manifest['source_files']:
        if subprocess.check_output(['git', 'show', revision + ':' + filename]) != Path(filename).read_bytes():
            raise ValueError('Uncommitted evaluator/dependency: ' + filename)
    return manifest


class FinalData(PilotData):
    def fit_feature_transform(self):
        raise RuntimeError('Fitting is disabled in final evaluation')

    def load_final(self, manifest, protocol_commit, receipt):
        if not manifest['sealed']:
            raise PermissionError('Unsealed manifest cannot authorize test access')
        frozen = read(manifest['split_metadata'])['test']
        actual = self.splits['test']
        for key in ('days', 'rows', 'origins'):
            if list(actual[key]) != frozen[key]:
                raise ValueError('Test split metadata differs: ' + key)
        assert self.loaded == [], 'Final reader never mixes development measurements'
        save(receipt, dict(first_authorized_test_read_utc=utc(), protocol_commit=protocol_commit,
                           implementation_commit=manifest['implementation_commit'],
                           manifest_sha256=sha256('configs/final_test_manifest.json'),
                           historical_test_exposure=manifest['exposure'], purpose='Frozen inference only'))
        rows = actual['rows']
        groups = np.split(rows, np.flatnonzero(np.diff(rows) != 1) + 1)
        with h5py.File(self.config['raw_file'], 'r') as stream:
            for group in groups:
                if len(group):
                    lo, hi = int(group[0]), int(group[-1]) + 1
                    self.raw[lo:hi] = to_cuda(stream['speed/block0_values'][lo:hi], torch.float64)
                    self.io_records.append(dict(split='test', first_row=lo, last_row_exclusive=hi))
        self.loaded.append('test')
        self.mask = valid(self.raw)
        allowed = torch.zeros(len(self.raw), device='cuda', dtype=torch.bool)
        allowed[to_cuda(rows, torch.long)] = True
        assert torch.isnan(self.raw[~allowed]).all(), 'Outside-test values must remain inaccessible'
        origins = to_cuda(actual['origins'], torch.long)
        for offset in range(-11, 7):
            assert allowed[origins + offset].all()
        return actual['origins']
