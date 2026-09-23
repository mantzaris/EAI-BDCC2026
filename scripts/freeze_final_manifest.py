"""Metadata-only inventory and seal. Never decodes measurement arrays or predictions."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess


def record(path):
    p=Path(path);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def main():
    p=argparse.ArgumentParser();p.add_argument('--seal',action='store_true');args=p.parse_args()
    file=Path('configs/final_test_manifest.json')
    if args.seal:
        m=json.loads(file.read_text());pre=Path('results/final_test/preflight/complete.json')
        r=json.loads(pre.read_text());assert r['passed'] and not r['test_access']
        m.update(sealed=True,implementation_commit=r['protocol_commit'],sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 graph_operator_sha256=r['graph_operator_sha256'])
        for path in (pre,Path('results/final_test/preflight/checks.json')):m['files'][str(path)]=record(path)
    else:
        assert not file.exists()
        c=json.loads(Path('configs/onset_graph_study.json').read_text())
        path='results/onset_graph/study01/main/models_with_nulls.json';meta=json.loads(Path(path).read_text())
        families={k:[k] for k in ('A_G','R_union','A_mono')}
        families.update({k:[r['key'] for r in f['replicates']] for k,f in meta['families'].items()})
        assert len(families)==17 and sum(map(len,families.values()))==45
        for f in meta['families'].values():assert [r['seed'] for r in f['replicates']]==[20261001,20261002,20261003]
        assert meta['strong_aggregate']=='B' and meta['expanded']=='E'
        art='artifacts/onset_graph/study01/main'
        checkpoints=[art+'/'+n+'.pt.gz' for n in ('anchor','refreshed','dependency')]
        checkpoints += [r['checkpoint'] for f in meta['families'].values() for r in f['replicates']]
        source=sorted(str(p) for p in Path('src').rglob('*.py'))+['scripts/run_final_test.py','scripts/final_test_budget.py','scripts/run_onset_graph.py','scripts/run_residual_gpu.py']
        needed=source+checkpoints+[path,'configs/onset_graph_study.json','manifests/final_test/split_metadata.json',
            'data/raw/pems-bay.h5','data/processed/pilot_inputs.npz','results/onset_graph/study01/main/complete_costs.json',
            'results/onset_graph/study01/main/validation_raw_predictions.csv.gz','results/onset_graph/study01/main/validation_calibrated_predictions.csv.gz']
        files={p:record(p) for p in needed}
        prior=json.loads(Path('manifests/onset_graph/artifacts.json').read_text())['files']
        for p in checkpoints:assert files[p]==prior[p],p
        m=dict(version=1,sealed=False,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            starting_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            configuration='configs/onset_graph_study.json',model_metadata=path,artifact_directory=art,
            source_files=source,files=files,families=families,required_checkpoints=checkpoints,
            correction_seeds=c['correction']['seeds'],rewiring_seeds=c['graph']['null_seeds'],
            graph_keys=['distance','dependency','self','distance_rewire_20261004','distance_rewire_20261005'],
            graph_hash_serialization='CUDA-computed operator, contiguous float64 little-endian bytes copied to host for SHA256',
            split_metadata='manifests/final_test/split_metadata.json',designated_split='test',
            exposure=dict(train='Previously used for fitting and choices',validation='All36days previously exposed; exploratory',
                          test='No prior measurement/prediction/outcome access found in guards, executed modes, or result manifests; timestamp metadata only'),
            endpoints=dict(primary='raw onset Brier',secondary='all-time Brier'),primary_contrasts=[['C','B'],['D','C'],['E','D'],['E','B']],
            required_secondary=['B','R_union'],bootstrap=c['bootstrap'],practical=c['practical'],
            calibration='Frozen maps and strict thresholds from main model metadata, no fitting or tie noise',
            ensemble=False,seed_summary='mean of seed-specific losses; seed SD descriptive; uncertainty conditional on fitted models',
            tolerances=dict(prediction_max_absolute=1e-10,metric_max_absolute=1e-12,labels_and_origin_identity='exact'),
            resource=dict(device='NVIDIA RTX 6000 Ada Generation',prior_gpu_seconds=997.8225433584303,
                          max_new_gpu_seconds=1800,project_provisional_seconds=86400,max_allocated_bytes=32000000000,
                          cpu_scientific_fallback=False,optional_budget_extension=False),
            output_policy='Private raw speeds excluded. Derived labels/masks/predictions follow existing compact artifact policy; governing measurement terms remain unresolved.')
    file.write_text(json.dumps(m,indent=2)+'\n')


if __name__=='__main__':main()
