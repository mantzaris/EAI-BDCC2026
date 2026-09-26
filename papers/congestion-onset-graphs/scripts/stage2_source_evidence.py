"""Archive small public primary-source evidence; no account or raw data downloads."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

SOURCES = {
    'dcrnn_readme': 'https://raw.githubusercontent.com/liyaguang/DCRNN/master/README.md',
    'dcrnn_generate': 'https://raw.githubusercontent.com/liyaguang/DCRNN/master/scripts/generate_training_data.py',
    'dcrnn_supervisor': 'https://raw.githubusercontent.com/liyaguang/DCRNN/master/model/dcrnn_supervisor.py',
    'dcrnn_metrics': 'https://raw.githubusercontent.com/liyaguang/DCRNN/master/lib/metrics.py',
    'caltrans_conditions': 'https://dot.ca.gov/conditions-of-use',
    'caltrans_pems_source': 'https://dot.ca.gov/programs/traffic-operations/mpr/pems-source',
    'pems_conditions_link': 'https://pems.dot.ca.gov/?dnode=Help&content=help_tou',
    'caltrans_quality_report.pdf': 'https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/final-reports/ca22-task3253-a11y.pdf',
    'coogan2015.pdf': 'https://coogan.ece.gatech.edu/papers/pdf/coogan2015hscc.pdf',
    'couthures_hal': 'https://hal.science/hal-05636985v1',
}


def main():
    directory = Path('data/source_evidence/stage2'); directory.mkdir(parents=True, exist_ok=True)
    target = Path('manifests/stage2/source_evidence.json')
    if target.exists(): raise FileExistsError('Preserve original evidence; choose a new manifest')
    records = []; total = 0
    for name, url in SOURCES.items():
        row = dict(name=name, url=url, retrieval_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        try:
            with urllib.request.urlopen(url, timeout=25) as response:
                data = response.read(8_000_001)
                row['bytes_received'] = len(data)
                total += len(data)
                if len(data) > 8_000_000 or total > 12_000_000:
                    raise ValueError('Small evidence download ceiling exceeded')
                (directory/name).write_bytes(data)
                row.update(status=response.status, final_url=response.url, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                row['access_challenge'] = any(s in data[:100000].lower() for s in (b'anubis', b'recaptcha', b'oh noes'))
        except Exception as error:
            row['error'] = str(error)
        records.append(row); print(name, row.get('status', row.get('error')), flush=True)
    target.write_text(json.dumps(dict(records=records, downloaded_bytes=total,
        raw_data_downloaded=False, accounts_registered=False, third_parties_contacted=False), indent=2)+'\n')


if __name__ == '__main__': main()
