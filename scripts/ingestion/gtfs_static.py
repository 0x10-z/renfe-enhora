"""Download and cache Renfe GTFS static data."""
import logging
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import requests
import urllib3

from scripts.config import CACHE_DIR, GTFS_CACHE_HOURS, REQUEST_TIMEOUT, ServiceConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
log = logging.getLogger(__name__)


def get_gtfs_dir(service: ServiceConfig) -> Path:
    """
    Return path to the extracted GTFS directory for the given service.
    Downloads and extracts only when the cache is stale (>GTFS_CACHE_HOURS old).
    """
    cache_dir = CACHE_DIR / service.cache_subdir
    cache_dir.mkdir(parents=True, exist_ok=True)

    zip_path = cache_dir / "fomento_transit.zip"
    gtfs_dir = cache_dir / "gtfs"

    if _is_fresh(zip_path, GTFS_CACHE_HOURS):
        log.info(f"[{service.label}] GTFS cache is fresh — skipping download")
        return gtfs_dir

    log.info(f"[{service.label}] Downloading GTFS static data…")
    _download(service.gtfs_url, zip_path)
    _extract(zip_path, gtfs_dir)
    return gtfs_dir


def _download(url: str, dest: Path) -> None:
    resp = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        verify=False,  # Renfe SSL cert issues (known since Dec 2025)
        stream=True,
    )
    resp.raise_for_status()

    size = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            size += len(chunk)

    log.info(f"GTFS downloaded: {size / 1024:.0f} KB → {dest.name}")


def _extract(zip_path: Path, dest: Path) -> None:
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    log.info("Extracting GTFS…")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)

    files = [f.name for f in dest.iterdir()]
    log.info(f"Extracted {len(files)} files: {', '.join(files[:8])}")


def _is_fresh(path: Path, max_age_hours: int) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(hours=max_age_hours)
