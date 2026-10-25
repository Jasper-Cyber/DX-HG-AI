"""Small deterministic I/O, download, hashing, and archive helpers."""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


class AcquisitionDeadline(RuntimeError):
    """Raised when the bounded acquisition window has elapsed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_canonical_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def download_file(url: str, destination: Path, deadline: float, timeout: int) -> dict[str, Any]:
    """Download with stdlib only, atomically, while enforcing a wall-clock deadline."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size:
        return {
            "url": url,
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
        }

    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "HeartGuardian-ML-MVP/1.0"})
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, temporary.open("wb") as output:
            while True:
                if time.monotonic() >= deadline:
                    raise AcquisitionDeadline(f"download deadline reached while fetching {url}")
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {"url": url, "bytes": size, "sha256": digest.hexdigest()}


def write_npz_deterministic(path: Path, **arrays: np.ndarray) -> None:
    """Write a compressed NPZ with sorted keys and fixed ZIP metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(arrays):
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, np.asanyarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, buffer.getvalue(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    os.replace(temporary, path)
