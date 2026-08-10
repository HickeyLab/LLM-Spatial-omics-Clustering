"""Download and verify the ground-truth H5AD from the Duke data repository.

The Duke record publishes the H5AD inside ``CODEX_annotated.zip`` rather than
as a standalone file. This module keeps that archive and the extracted H5AD
in a caller-provided local cache, verifies both identities, and records a
small provenance receipt. Neither data artifact belongs in Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile


DUKE_RECORD_URL = "https://research.repository.duke.edu/record/505"
DUKE_ARCHIVE_URL = "https://research.repository.duke.edu/record/505/files/CODEX_annotated.zip"
DUKE_ARCHIVE_FILENAME = "CODEX_annotated.zip"
DUKE_ARCHIVE_SIZE_BYTES = 2_205_666_065
DUKE_ARCHIVE_MD5 = "ff2bee7c6f127fccf4b657a7375e117b"

# The published archive uses ``experted`` in this member name. Preserve the
# exact member path so extraction is source-traceable.
DUKE_H5AD_MEMBER = "CODEX_annotated/20260130_HuBMAP_experted_annotated.h5ad"
DUKE_H5AD_FILENAME = "20260130_HuBMAP_experted_annotated.h5ad"
DUKE_H5AD_SIZE_BYTES = 105_036_338
DUKE_H5AD_SHA256 = "5d0a59d1e7866dee5a3a06772c3c80ce7328ba6420bc140708be5ec451b8a49"
DUKE_H5AD_DOWNLOAD_SCHEMA = "duke_research_repository_h5ad_download.v1"
DUKE_REQUEST_USER_AGENT = "LLM-Spatial-omics-Clustering/1.0 (Duke H5AD downloader)"
DOWNLOAD_CHUNK_BYTES = 4 * 1024 * 1024
_CONTENT_RANGE_PATTERN = re.compile(r"^bytes\s+(\d+)-(\d+)/(\d+)$", re.IGNORECASE)


class DukeH5ADDownloadError(RuntimeError):
    """Raised when the Duke archive or extracted H5AD fails its contract."""


@dataclass(frozen=True)
class DukeH5ADDownloadResult:
    """Receipt for one verified local Duke H5AD cache."""

    path: Path
    cache_root: Path
    archive_path: Path
    manifest_path: Path
    archive_reused: bool
    h5ad_reused: bool
    bytes_transferred: int

    def summary(self) -> str:
        state = "reused" if self.h5ad_reused else "downloaded and extracted"
        return f"Duke H5AD {state}: {self.path}"


def default_duke_h5ad_cache_root(repository_root: str | Path | None = None) -> Path:
    """Return the ignored repository-local cache used when no path is supplied."""

    root = (
        Path(repository_root).expanduser().resolve()
        if repository_root is not None
        else Path(__file__).resolve().parents[2]
    )
    return root / "data" / "raw" / "duke_research_repository"


def _hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(DOWNLOAD_CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_file(path: Path, *, size_bytes: int, digest: str, algorithm: str, label: str) -> None:
    if not path.is_file():
        raise DukeH5ADDownloadError(f"{label} does not exist: {path}")
    observed_size = path.stat().st_size
    if observed_size != size_bytes:
        raise DukeH5ADDownloadError(
            f"{label} has {observed_size} bytes; expected {size_bytes}: {path}"
        )
    observed_digest = _hash_file(path, algorithm)
    if observed_digest != digest:
        raise DukeH5ADDownloadError(
            f"{label} {algorithm.upper()} mismatch: observed={observed_digest}, expected={digest}"
        )


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _download_archive(archive_path: Path, *, timeout_seconds: int) -> tuple[bool, int]:
    """Download the large archive with resumable range requests."""

    partial_path = archive_path.with_name(f"{archive_path.name}.part")
    start = partial_path.stat().st_size if partial_path.exists() else 0
    if start > DUKE_ARCHIVE_SIZE_BYTES:
        raise DukeH5ADDownloadError(
            f"Partial Duke archive is larger than the published object: {partial_path}"
        )
    if start == DUKE_ARCHIVE_SIZE_BYTES:
        _validate_file(
            partial_path,
            size_bytes=DUKE_ARCHIVE_SIZE_BYTES,
            digest=DUKE_ARCHIVE_MD5,
            algorithm="md5",
            label="Duke archive",
        )
        partial_path.replace(archive_path)
        return False, 0

    headers = {"User-Agent": DUKE_REQUEST_USER_AGENT}
    if start:
        headers["Range"] = f"bytes={start}-"
    try:
        with urlopen(Request(DUKE_ARCHIVE_URL, headers=headers), timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 200))
            if start:
                if status != 206:
                    raise DukeH5ADDownloadError(
                        f"Duke archive did not honor resume range (HTTP {status})"
                    )
                content_range = str(response.headers.get("Content-Range", ""))
                match = _CONTENT_RANGE_PATTERN.fullmatch(content_range)
                if (
                    match is None
                    or int(match.group(1)) != start
                    or int(match.group(3)) != DUKE_ARCHIVE_SIZE_BYTES
                ):
                    raise DukeH5ADDownloadError(
                        f"Duke archive returned an invalid resume range: {content_range!r}"
                    )
            mode = "ab" if start else "wb"
            with partial_path.open(mode) as output:
                for block in iter(lambda: response.read(DOWNLOAD_CHUNK_BYTES), b""):
                    output.write(block)
    except (HTTPError, URLError, OSError) as exc:
        raise DukeH5ADDownloadError(f"Unable to download Duke archive: {exc}") from exc

    transferred = partial_path.stat().st_size - start
    _validate_file(
        partial_path,
        size_bytes=DUKE_ARCHIVE_SIZE_BYTES,
        digest=DUKE_ARCHIVE_MD5,
        algorithm="md5",
        label="Duke archive",
    )
    partial_path.replace(archive_path)
    return False, transferred


def _extract_h5ad(archive_path: Path, target_path: Path) -> None:
    """Extract only the declared H5AD member and verify its SHA-256."""

    temporary = target_path.with_name(f"{target_path.name}.part")
    if temporary.exists():
        raise DukeH5ADDownloadError(
            f"Refusing to overwrite an incomplete extracted H5AD; remove it first: {temporary}"
        )
    try:
        with zipfile.ZipFile(archive_path) as archive:
            try:
                info = archive.getinfo(DUKE_H5AD_MEMBER)
            except KeyError as exc:
                raise DukeH5ADDownloadError(
                    f"Duke archive is missing the declared member: {DUKE_H5AD_MEMBER}"
                ) from exc
            if info.file_size != DUKE_H5AD_SIZE_BYTES:
                raise DukeH5ADDownloadError(
                    f"Duke H5AD member has {info.file_size} bytes; expected {DUKE_H5AD_SIZE_BYTES}"
                )
            digest = hashlib.sha256()
            with archive.open(info, "r") as source, temporary.open("wb") as output:
                for block in iter(lambda: source.read(DOWNLOAD_CHUNK_BYTES), b""):
                    output.write(block)
                    digest.update(block)
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise DukeH5ADDownloadError(f"Unable to extract Duke H5AD: {exc}") from exc
    if temporary.stat().st_size != DUKE_H5AD_SIZE_BYTES:
        raise DukeH5ADDownloadError(f"Extracted Duke H5AD has the wrong size: {temporary}")
    if digest.hexdigest() != DUKE_H5AD_SHA256:
        raise DukeH5ADDownloadError(
            "Extracted Duke H5AD SHA-256 mismatch: "
            f"observed={digest.hexdigest()}, expected={DUKE_H5AD_SHA256}"
        )
    temporary.replace(target_path)


def download_duke_h5ad(
    cache_root: str | Path | None = None,
    *,
    timeout_seconds: int = 60,
) -> DukeH5ADDownloadResult:
    """Download, extract, verify, and receipt the Duke ground-truth H5AD."""

    root = (
        Path(cache_root).expanduser().resolve()
        if cache_root is not None
        else default_duke_h5ad_cache_root()
    )
    root.mkdir(parents=True, exist_ok=True)
    archive_path = root / DUKE_ARCHIVE_FILENAME
    target_path = root / DUKE_H5AD_FILENAME
    manifest_path = root / "duke_h5ad_manifest.json"

    if target_path.is_file():
        _validate_file(
            target_path,
            size_bytes=DUKE_H5AD_SIZE_BYTES,
            digest=DUKE_H5AD_SHA256,
            algorithm="sha256",
            label="Duke H5AD",
        )
        archive_reused = archive_path.is_file()
        if archive_reused:
            _validate_file(
                archive_path,
                size_bytes=DUKE_ARCHIVE_SIZE_BYTES,
                digest=DUKE_ARCHIVE_MD5,
                algorithm="md5",
                label="Duke archive",
            )
        bytes_transferred = 0
        h5ad_reused = True
    else:
        if archive_path.is_file():
            _validate_file(
                archive_path,
                size_bytes=DUKE_ARCHIVE_SIZE_BYTES,
                digest=DUKE_ARCHIVE_MD5,
                algorithm="md5",
                label="Duke archive",
            )
            archive_reused = True
            bytes_transferred = 0
        else:
            archive_reused, bytes_transferred = _download_archive(
                archive_path, timeout_seconds=timeout_seconds
            )
        _extract_h5ad(archive_path, target_path)
        h5ad_reused = False

    manifest = {
        "schema": DUKE_H5AD_DOWNLOAD_SCHEMA,
        "record_url": DUKE_RECORD_URL,
        "archive_url": DUKE_ARCHIVE_URL,
        "archive_filename": DUKE_ARCHIVE_FILENAME,
        "archive_size_bytes": DUKE_ARCHIVE_SIZE_BYTES,
        "archive_md5": DUKE_ARCHIVE_MD5,
        "archive_member": DUKE_H5AD_MEMBER,
        "h5ad_filename": DUKE_H5AD_FILENAME,
        "h5ad_size_bytes": DUKE_H5AD_SIZE_BYTES,
        "h5ad_sha256": DUKE_H5AD_SHA256,
        "h5ad_path": str(target_path),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json_atomic(manifest_path, manifest)
    return DukeH5ADDownloadResult(
        path=target_path,
        cache_root=root,
        archive_path=archive_path,
        manifest_path=manifest_path,
        archive_reused=archive_reused,
        h5ad_reused=h5ad_reused,
        bytes_transferred=bytes_transferred,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=default_duke_h5ad_cache_root(),
        help="Ignored local directory for the Duke archive, extracted H5AD, and receipt.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()
    print(download_duke_h5ad(args.cache_root, timeout_seconds=args.timeout_seconds).summary())


if __name__ == "__main__":
    main()
