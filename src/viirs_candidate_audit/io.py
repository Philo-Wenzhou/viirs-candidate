"""Input, download, provenance, and configuration helpers."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow
import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def software_environment() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "pyarrow": pyarrow.__version__,
    }


def write_manifest(
    data_path: str | Path,
    manifest_path: str | Path,
    data_config: dict[str, Any],
) -> dict[str, Any]:
    data_path = Path(data_path)
    manifest = {
        "schema_version": 1,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": data_config["url"],
        "landing_page": data_config["landing_page"],
        "data_doi": data_config["data_doi"],
        "paper_doi": data_config["paper_doi"],
        "license": data_config["license"],
        "local_filename": data_path.name,
        "bytes": data_path.stat().st_size,
        "sha256": sha256_file(data_path),
        "software": software_environment(),
    }
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def download_data(
    data_config: dict[str, Any],
    destination: str | Path,
    manifest_path: str | Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Download the declared source file without any synthetic fallback."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = str(data_config.get("sha256", "")).lower()

    if destination.exists() and not overwrite:
        actual = sha256_file(destination)
        if expected and actual != expected:
            raise ValueError(
                f"Existing file checksum mismatch: expected {expected}, got {actual}. "
                "Delete or explicitly overwrite the file after investigating."
            )
        return write_manifest(destination, manifest_path, data_config)

    temporary = destination.with_suffix(destination.suffix + ".part")
    if temporary.exists():
        temporary.unlink()
    try:
        request = urllib.request.Request(
            data_config["url"], headers={"User-Agent": "viirs-candidate-audit/0.1"}
        )
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        actual = sha256_file(temporary)
        if expected and actual != expected:
            raise ValueError(f"Downloaded checksum mismatch: expected {expected}, got {actual}")
        os.replace(temporary, destination)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return write_manifest(destination, manifest_path, data_config)


def read_source(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Source file not found: {path}. Run the download command; no synthetic fallback is used."
        )
    if "synthetic" in path.name.lower():
        raise ValueError("Synthetic files are not accepted by the empirical analysis command.")
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, low_memory=False)
    raise ValueError(f"Unsupported source format: {path.suffix}")

