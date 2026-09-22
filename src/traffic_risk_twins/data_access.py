"""Size-limited acquisition and provenance. Raw measurement files are never published."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def download(url, target, max_bytes=200_000_000):
    target = Path(target)
    if target.exists():
        raise FileExistsError('Raw layer is append-only: '+str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix+'.partial')
    row = dict(url=url, path=str(target), retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    size = 0
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'traffic-risk-twins/0.1'})
        with urllib.request.urlopen(req, timeout=60) as response, partial.open('xb') as out:
            row['content_type'] = response.headers.get('Content-Type')
            while True:
                block = response.read(1 << 20)
                if not block:
                    break
                size += len(block)
                if size > max_bytes:
                    raise ValueError('Download exceeds file cap')
                out.write(block)
        partial.rename(target)
        row.update(bytes=size, sha256=sha256(target), status='retrieved')
    except Exception as exc:
        row.update(status='failed', error=str(exc), bytes_received=size)
    return row


def save_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
