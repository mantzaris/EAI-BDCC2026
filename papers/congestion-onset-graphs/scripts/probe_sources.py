"""Bounded, public source inspection. No credentials; measurements stay in data/."""
import datetime
import hashlib
import json
import pathlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor

SOURCES = {
    'dcrnn_readme': 'https://raw.githubusercontent.com/liyaguang/DCRNN/master/README.md',
    'dcrnn_metrics': 'https://raw.githubusercontent.com/liyaguang/DCRNN/master/lib/metrics.py',
    'dcrnn_drive': 'https://drive.google.com/drive/folders/10FOTa6HXPqX8Pf5WRoRwcFnW9BrNZEIX',
    'pems_terms': 'https://pems.dot.ca.gov/?dnode=Main&content=User_Agreement',
    'zenodo_metadata': 'https://zenodo.org/api/records/5724362',
    'largest_files': 'https://www.kaggle.com/api/v1/datasets/list/liuxu77/largest',
    'largest_readme': 'https://raw.githubusercontent.com/liuxu77/LargeST/main/README.md',
}

def probe(item):
    name, url = item
    row = dict(name=name, url=url, retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'research-feasibility/1.0'})
        with urllib.request.urlopen(request, timeout=40) as response:
            body = response.read(4_000_001)
            if len(body) > 4_000_000:
                raise ValueError('Metadata size cap exceeded')
            pathlib.Path('data/source_evidence').mkdir(parents=True, exist_ok=True)
            pathlib.Path('data/source_evidence', name).write_bytes(body)
            row.update(status=response.status, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                       content_type=response.headers.get('Content-Type'))
    except Exception as exc:
        row['error'] = str(exc)
    return row

if __name__ == '__main__':
    rows = list(ThreadPoolExecutor(4).map(probe, SOURCES.items()))
    pathlib.Path('manifests/source_access.json').write_text(json.dumps(rows, indent=2)+'\n')
    print(json.dumps(rows, indent=2))
