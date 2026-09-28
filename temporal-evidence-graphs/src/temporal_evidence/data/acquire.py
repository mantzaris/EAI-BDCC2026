"""Acquire original datasets; metadata and raw recordings remain separate."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from temporal_evidence.io import digest_file, utc_now, write_json

SOURCES = {
    "wesad": "https://ubi29.informatik.uni-siegen.de/usi/data_wesad.html",
    "ppg_dalia": "https://archive.ics.uci.edu/dataset/495/ppg+dalia",
}


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read().decode("utf-8", errors="replace")


def download(url: str, path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    subprocess.run(["curl", "--http1.1", "--fail", "--location", "--retry", "5", "--retry-delay", "3",
                    "--continue-at", "-", "--output", str(temporary), url], check=True)
    if path.suffix == ".zip" and not zipfile.is_zipfile(temporary):
        raise ValueError(f"Downloaded response is not a ZIP archive: {path}")
    temporary.rename(path)


def extract_selected(archive: Path, destination: Path) -> list[dict]:
    """Extract synchronized pickles and documentation; reject unsafe member paths."""
    files = []
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            name = Path(member.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError(f"Unsafe archive member: {member.filename}")
            if member.is_dir():
                continue
            lower = name.name.lower()
            if name.suffix.lower() == ".zip":
                if lower not in {"data.zip", "wesad.zip", "ppg_fieldstudy.zip"}:
                    continue
                nested = destination / name
                nested.parent.mkdir(parents=True, exist_ok=True)
                if not nested.exists():
                    with zipped.open(member) as source, nested.open("wb") as target:
                        shutil.copyfileobj(source, target)
                files.extend(extract_selected(nested, destination / name.stem))
                continue
            if not (name.suffix == ".pkl" or "readme" in lower or "license" in lower):
                continue
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with zipped.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
            files.append({"path": str(target), "bytes": target.stat().st_size,
                          "sha256": digest_file(target), "member": member.filename})
    return files


def acquire(dataset: str, local_archive: str | None = None, author_source: bool = False) -> dict:
    raw = Path("data/raw") / dataset
    manifest_directory = Path("artifacts/manifests/acquisition")
    manifest_directory.mkdir(parents=True, exist_ok=True)
    landing = fetch_text(SOURCES[dataset])
    (manifest_directory / f"{dataset}_source.html").write_text(landing)
    if author_source and dataset == "ppg_dalia":
        author_page = "https://ubi29.informatik.uni-siegen.de/usi/data_ppgdalia.html"
        landing = fetch_text(author_page)
        (manifest_directory / "ppg_dalia_author.html").write_text(landing)
    if dataset == "wesad" or author_source:
        visible_html = re.sub(r"<!--.*?-->", "", landing, flags=re.S)
        links = re.findall(r'href=[\"\']([^\"\']+)[\"\']', visible_html, flags=re.I)
        shares = [url for url in links if "sciebo.de/s/" in url]
        if len(shares) != 1:
            raise ValueError(f"Expected one original author archive link, found {shares}")
        url = shares[0].rstrip("/") + "/download"
        license_text = "Scientific, non-commercial use with credit to the owners; see saved author page."
    else:
        url = "https://archive.ics.uci.edu/static/public/495/ppg%2Bdalia.zip"
        license_text = "CC BY 4.0; see saved UCI record and https://creativecommons.org/licenses/by/4.0/"
    archive = Path(local_archive) if local_archive else raw / f"{dataset}.zip"
    if not local_archive:
        download(url, archive)
    result = {"dataset": dataset, "retrieved_at": utc_now(), "source_url": SOURCES[dataset],
              "resolved_archive_url": url, "archive": str(archive), "license": license_text,
              "archive_bytes": archive.stat().st_size, "archive_sha256": digest_file(archive)}
    if author_source:
        result["author_url"] = author_page
        result["acquisition_note"] = "Original author archive used after UCI packaged and legacy downloads stalled; UCI lists CC BY 4.0, author page states scientific non-commercial use with attribution."
    result["files"] = extract_selected(archive, raw / "recordings")
    write_json(manifest_directory / f"{dataset}.json", result)
    print(f"{dataset}: {len(result['files'])} selected files acquired", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", choices=tuple(SOURCES), required=True)
    parser.add_argument("--local-archive")
    parser.add_argument("--author-source", action="store_true")
    args = parser.parse_args()
    if args.local_archive and len(args.datasets) != 1:
        parser.error("--local-archive requires exactly one dataset")
    for dataset in args.datasets:
        acquire(dataset, args.local_archive, args.author_source)
