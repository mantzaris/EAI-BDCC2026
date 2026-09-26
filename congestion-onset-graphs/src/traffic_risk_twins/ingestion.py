"""Read source HDF5 axes separately; Stage 1 cannot load test measurement rows."""
import io
import pickle
import numpy as np
import pandas as pd
import h5py
from scipy.sparse.csgraph import connected_components
from .chronological_splits import split_days, development_guard
from .data_access import sha256, save_json
from .observation_quality import valid_mask, SpeedTransform
from .retained_information import spatial_partition
from .event_functionals import sustained_count, episode_counts


class NumpyGraphUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {('numpy.core.multiarray', '_reconstruct'), ('numpy', 'ndarray'), ('numpy', 'dtype'), ('_codecs','encode')}
        if (module, name) not in allowed:
            raise pickle.UnpicklingError('Unsupported graph pickle class: '+module+'.'+name)
        return super().find_class(module, name)


class PemsSource:
    def __init__(self, path):
        self.path = path
        with h5py.File(path, 'r') as f:
            self.timestamps = pd.DatetimeIndex(f['speed/axis1'][:].astype('datetime64[ns]'))
            self.sensors = f['speed/axis0'][:]
            self.shape = f['speed/block0_values'].shape
            if not np.array_equal(f['speed/block0_items'][:], self.sensors):
                raise ValueError('HDF value columns differ from sensor axis')
        self.splits = split_days(self.timestamps)

    def read(self, split):
        development_guard(split)
        rows = self.splits[split]['rows']
        values = np.full(self.shape, np.nan, dtype=np.float64)
        # Contiguous slices keep HDF I/O bounded and never touch test measurements.
        groups = np.split(rows, np.flatnonzero(np.diff(rows) != 1)+1)
        with h5py.File(self.path, 'r') as f:
            for group in groups:
                if len(group):
                    values[group[0]:group[-1]+1] = f['speed/block0_values'][group[0]:group[-1]+1]
        return values


def load_graph(path, sensors):
    with open(path, 'rb') as stream:
        ids, mapping, adjacency = NumpyGraphUnpickler(stream, encoding='latin1').load()
    ids = np.asarray(ids, dtype=str)
    if len(set(ids)) != len(ids) or set(ids) != set(np.asarray(sensors, dtype=str)):
        raise ValueError('Graph and measurement sensor sets differ')
    order = [int(mapping[str(s)]) for s in sensors]
    adjacency = np.asarray(adjacency, float)[np.ix_(order, order)]
    if not np.isfinite(adjacency).all() or (adjacency < 0).any():
        raise ValueError('Invalid graph weights')
    original_edges = int(np.count_nonzero(adjacency))
    loops = int(np.count_nonzero(np.diag(adjacency)))
    np.fill_diagonal(adjacency, 0)
    isolated = np.flatnonzero(adjacency.sum(axis=1) == 0)
    adjacency[isolated, isolated] = 1
    W = adjacency/adjacency.sum(axis=1, keepdims=True)
    return W, dict(source_edges_including_self=original_edges, source_self_loops=loops,
                   nonself_edges=original_edges-loops, isolated_rows_self_fallback=isolated.tolist(),
                   source_order_matches=bool(np.array_equal(ids,np.asarray(sensors,dtype=str))),
                   aligned_order_sha256=__import__('hashlib').sha256(np.asarray(sensors,dtype='<i8').tobytes()).hexdigest(),
                   convention='Row i aggregates neighbors j. Remove self loops; isolated rows get identity; normalize each row.')


def label_origins(state, mask, origins, threshold):
    severity_low, severity_high, coverage = [], [], []
    for start in range(0, len(origins), 512):
        ids = origins[start:start+512, None]+np.arange(1,7)
        future, observed = state[ids], mask[ids]
        severity_low.extend(sustained_count(((future >= 0)&observed).sum(axis=-1)).tolist())
        severity_high.extend(sustained_count(((future >= 0)|~observed).sum(axis=-1)).tolist())
        coverage.extend(observed.mean(axis=(1,2)).tolist())
    lo, hi = np.asarray(severity_low), np.asarray(severity_high)
    low, high = lo >= threshold, hi >= threshold
    eligible = (low == high)&(np.asarray(coverage) >= .95)
    current = []
    for o in origins:
        # Unknown current indicators are conservatively active for onset exclusion.
        current.append(bool(np.all((((state[o-2:o+1] >= 0)|~mask[o-2:o+1]).sum(axis=1)) >= threshold)))
    return dict(low=low, high=high, eligible=eligible, current_active=np.asarray(current),
                severity_low=lo, severity_high=hi, coverage=np.asarray(coverage))


def metadata_regions(coordinates, W):
    """Single declared alternative: largest connected component in each spatial quarter."""
    quarters = spatial_partition(coordinates, 4)
    regions = []
    for block in range(4):
        ids = np.flatnonzero(quarters == block)
        _, components = connected_components((W[np.ix_(ids,ids)]+W[np.ix_(ids,ids)].T)>0, directed=False)
        largest = np.argmax(np.bincount(components))
        regions.append(ids[components == largest])
    return regions


def audit_pems(root='data/raw', output='manifests/data_audit.json'):
    from pathlib import Path
    root = Path(root)
    source = PemsSource(root/'pems-bay.h5')
    train = source.read('train')
    validation = source.read('validation')
    mask_train, mask_validation = valid_mask(train), valid_mask(validation)
    transform = SpeedTransform.fit(train[source.splits['train']['rows']],mask_train[source.splits['train']['rows']])
    states = {'train':transform.forward(train,mask_train), 'validation':transform.forward(validation,mask_validation)}
    masks = {'train':mask_train, 'validation':mask_validation}
    W, graph = load_graph(root/'adj_mx_bay.pkl',source.sensors)
    coords = pd.read_csv(root/'graph_sensor_locations_bay.csv', header=None, index_col=0).loc[source.sensors].to_numpy()
    origins = source.splits['train']['origins']
    first = label_origins(states['train'],mask_train,origins,1)
    exact = (first['severity_low'] == first['severity_high'])&(first['coverage'] >= .95)
    threshold = int(np.ceil(max(.1*len(W),np.quantile(first['severity_low'][exact],.9))))
    report = dict(source_sha256=sha256(root/'pems-bay.h5'), dimensions=list(source.shape),
                  first_timestamp=str(source.timestamps[0]), last_timestamp=str(source.timestamps[-1]),
                  timezone='not stored; timestamps are naive; no timezone localization assumed',
                  duplicate_timestamps=int(source.timestamps.duplicated().sum()),
                  gap_after=[str(source.timestamps[i]) for i in np.flatnonzero(np.diff(source.timestamps.asi8) != 300_000_000_000)],
                  excluded_incomplete_days=source.splits['excluded_incomplete_days'],
                  units='mph: PeMS public speed legend and DCRNN speed task; no conversion',
                  graph=graph, zero_policy='unresolved zeros treated as unknown indicators, not declared stopped traffic or proven sentinels',
                  original_quality_flags='not present in HDF; upstream imputation provenance unavailable',
                  threshold_count=threshold, threshold_fraction=threshold/len(W), splits={},
                  test_measurements_read=False, test_events_inspected=False)
    for name in ('train','validation','test'):
        split = source.splits[name]
        item = dict(days=split['days'], complete_day_count=len(split['days']), retained_frames=len(split['rows']),
                    forecast_origins=len(split['origins']))
        if name != 'test':
            values = (train if name == 'train' else validation)[split['rows']]
            labels = label_origins(states[name],masks[name],split['origins'],threshold)
            positive = labels['low']&labels['eligible']
            item.update(zero_values=int((values == 0).sum()), nonfinite_values=int((~np.isfinite(values)).sum()),
                        negative_values=int((values < 0).sum()), valid_fraction=float(masks[name][split['rows']].mean()),
                        duplicate_value_rows=int(pd.DataFrame(values).duplicated().sum()),
                        positive_origins=int(positive.sum()), ambiguous_origins=int((labels['low'] != labels['high']).sum()),
                        eligible_origins=int(labels['eligible'].sum()), onset_eligible_origins=int((labels['eligible']&~labels['current_active']).sum()),
                        **episode_counts(source.timestamps[split['origins']],positive))
        report['splits'][name] = item
    insufficient = report['splits']['train']['episodes'] < 100 or report['splits']['validation']['episodes'] < 30
    report['region_alternative_applied'] = insufficient
    report['regions'] = []
    if insufficient:
        for j, region in enumerate(metadata_regions(coords,W)):
            tr = label_origins(states['train'][:,region],mask_train[:,region],origins,1)
            exact = (tr['severity_low'] == tr['severity_high'])&(tr['coverage'] >= .95)
            q = int(np.ceil(max(.1*len(region),np.quantile(tr['severity_low'][exact],.9))))
            row = dict(region=j, sensor_indices=region.tolist(), threshold_count=q, size=len(region))
            for name in ('train','validation'):
                oo = source.splits[name]['origins']
                labels = label_origins(states[name][:,region],masks[name][:,region],oo,q)
                row[name] = episode_counts(source.timestamps[oo],labels['low']&labels['eligible'])
                row[name]['positive_origins'] = int((labels['low']&labels['eligible']).sum())
            report['regions'].append(row)
    save_json(output,report)
    return report
