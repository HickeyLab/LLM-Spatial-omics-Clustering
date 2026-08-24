"""Acquire the final-figure B004 OME-TIFF pairs from HuBMAP.

The final-source notebooks need eight B004 expression/mask pairs for
image-native PIXIE.  The source H5AD stores the matching HuBMAP dataset UUID
in ``File_ID``.  This module therefore validates the declared B004 IDs against
the H5AD, downloads only those paired OME-TIFFs, and records a cache manifest.

Transfers are intentionally opt-in: the complete source set is about 46 GiB.
Every request carries a normal user agent because the HuBMAP asset host rejects
anonymous default clients, and interrupted objects resume only when their
recorded remote identity still matches.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HUBMAP_ASSET_BASE_URL = "https://assets.hubmapconsortium.org"
HUBMAP_TIFF_MANIFEST_SCHEMA = "final_figures.hubmap_tiff_download.v1"
HUBMAP_REQUEST_USER_AGENT = "LLM-Spatial-omics-Clustering/1.0 (HuBMAP TIFF downloader)"
DEFAULT_DOWNLOAD_RESERVE_BYTES = 1024**3
DEFAULT_TIMEOUT_SECONDS = 60
DOWNLOAD_CHUNK_BYTES = 4 * 1024**2

_FILE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_CONTENT_RANGE_PATTERN = re.compile(r"^bytes\s+(\d+)-(\d+)/(\d+)$", re.IGNORECASE)

TIFF_OBJECTS: Mapping[str, tuple[str, str]] = {
    "expression": (
        "reg001_expr.ome.tif",
        "ometiff-pyramids/pipeline_output/expr/reg001_expr.ome.tif",
    ),
    "mask": (
        "reg001_mask.ome.tif",
        "ometiff-pyramids/pipeline_output/mask/reg001_mask.ome.tif",
    ),
}


class HubMAPTiffDownloadError(RuntimeError):
    """Raised when a HuBMAP TIFF transfer cannot meet its source contract."""


@dataclass(frozen=True)
class HubMAPDataset:
    """One B004 dataset, as mapped in the supplied HuBMAP ID workbook."""

    file_id: str
    hubmap_id: str
    lab_dataset_id: str
    tissue_location: str


# Source: the supplied ``HuBMAP IDs.xlsx`` workbook.  File_ID is the UUID used
# by the source H5AD and the public HuBMAP asset service.
B004_HUBMAP_DATASETS: tuple[HubMAPDataset, ...] = (
    HubMAPDataset(
        "2e65eeef2dd18bee2a0baf1cec6d35a1",
        "HBM784.TKZX.992",
        "B004-A-304-SmallIntestine-Ileum-CODEX",
        "Ileum",
    ),
    HubMAPDataset(
        "5318485b16983482401c3be24b6c42ad",
        "HBM433.ZLWP.627",
        "B004-A-408-SmallIntestine-Jejunum-CODEX",
        "Proximal-Jejunum",
    ),
    HubMAPDataset(
        "63d000170e475af142f6e8673de5eb0f",
        "HBM538.PGFT.538",
        "B004-A-004-LargeIntestine-Sigmoid-CODEX",
        "Sigmoid",
    ),
    HubMAPDataset(
        "768b7adb649959b6a4e354867595032d",
        "HBM889.KDGM.632",
        "B004-A-104-LargeIntestine-Transverse-CODEX",
        "Transverse",
    ),
    HubMAPDataset(
        "76d3efd17b6fc83aaac13e961824c5ae",
        "HBM657.JVPV.825",
        "B004-A-204-LargeIntestine-Ascending-CODEX",
        "Ascending",
    ),
    HubMAPDataset(
        "8da8f27977d946b8c912d42c8827b55c",
        "HBM776.SDCW.837",
        "B004-A-404-SmallIntestine-MidJejunum-CODEX",
        "Mid-Jejunum",
    ),
    HubMAPDataset(
        "ae422532f260b3d6fc662aae69b05d33",
        "HBM946.GRVG.379",
        "B004-A-008-LargeIntestine-Descending-CODEX",
        "Descending",
    ),
    HubMAPDataset(
        "dceadbb36871071f30c308ca091fbdc8",
        "HBM842.LQDP.877",
        "B004-A-504-SmallIntestine-Duodenum-CODEX",
        "Duodenum",
    ),
)
B004_FILE_IDS = tuple(dataset.file_id for dataset in B004_HUBMAP_DATASETS)
_B004_BY_FILE_ID = {dataset.file_id: dataset for dataset in B004_HUBMAP_DATASETS}


@dataclass(frozen=True)
class RemoteTiffObject:
    """A verified remote TIFF object and its immutable transfer identity."""

    file_id: str
    kind: str
    filename: str
    url: str
    size_bytes: int
    etag: str | None
    last_modified: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "kind": self.kind,
            "filename": self.filename,
            "url": self.url,
            "size_bytes": self.size_bytes,
            "etag": self.etag,
            "last_modified": self.last_modified,
        }


@dataclass(frozen=True)
class HubMAPTiffDownloadPlan:
    """The bounded TIFF transfer required to cache the PIXIE inputs."""

    h5ad_path: Path
    tiff_root: Path
    file_ids: tuple[str, ...]
    objects: tuple[RemoteTiffObject, ...]
    bytes_missing: int
    bytes_available: int
    reserve_bytes: int

    @property
    def required_free_bytes(self) -> int:
        return self.bytes_missing + (self.reserve_bytes if self.bytes_missing else 0)

    @property
    def has_sufficient_space(self) -> bool:
        return self.bytes_available >= self.required_free_bytes

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": HUBMAP_TIFF_MANIFEST_SCHEMA,
            "h5ad_path": str(self.h5ad_path),
            "tiff_root": str(self.tiff_root),
            "file_ids": list(self.file_ids),
            "object_count": len(self.objects),
            "bytes_missing": self.bytes_missing,
            "bytes_available": self.bytes_available,
            "reserve_bytes": self.reserve_bytes,
            "required_free_bytes": self.required_free_bytes,
            "has_sufficient_space": self.has_sufficient_space,
            "objects": [remote.as_dict() for remote in self.objects],
        }


@dataclass(frozen=True)
class HubMAPTiffDownloadResult:
    """Completed acquisition receipt for the paired HuBMAP TIFF inputs."""

    plan: HubMAPTiffDownloadPlan
    manifest_path: Path
    downloaded_objects: int
    resumed_objects: int
    reused_objects: int
    bytes_transferred: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": HUBMAP_TIFF_MANIFEST_SCHEMA,
            "tiff_root": str(self.plan.tiff_root),
            "manifest_path": str(self.manifest_path),
            "downloaded_objects": self.downloaded_objects,
            "resumed_objects": self.resumed_objects,
            "reused_objects": self.reused_objects,
            "bytes_transferred": self.bytes_transferred,
            "objects": [remote.as_dict() for remote in self.plan.objects],
        }

    def summary(self) -> str:
        return (
            "HuBMAP TIFF acquisition complete: "
            f"{self.downloaded_objects} downloaded, {self.resumed_objects} resumed, "
            f"{self.reused_objects} reused; manifest={self.manifest_path}"
        )


def _as_gib(value: int) -> str:
    return f"{value / 1024**3:.2f} GiB"


def _normalise_file_ids(file_ids: Sequence[str] | None) -> tuple[str, ...]:
    requested = B004_FILE_IDS if file_ids is None else tuple(str(value).strip() for value in file_ids)
    if not requested:
        raise HubMAPTiffDownloadError("No HuBMAP File_ID values were requested")
    if len(set(requested)) != len(requested):
        raise HubMAPTiffDownloadError("HuBMAP File_ID values must be unique")
    invalid = [file_id for file_id in requested if not _FILE_ID_PATTERN.fullmatch(file_id)]
    if invalid:
        raise HubMAPTiffDownloadError(f"Invalid HuBMAP File_ID values: {invalid}")
    unknown = sorted(set(requested).difference(_B004_BY_FILE_ID))
    if unknown:
        raise HubMAPTiffDownloadError(
            "The final TIFF downloader is deliberately limited to the declared B004 cohort; "
            f"unknown File_ID values: {unknown}"
        )
    return requested


def hubmap_tiff_url(file_id: str, kind: str) -> str:
    """Return the public HuBMAP OME-TIFF asset URL for one declared B004 FOV."""

    _normalise_file_ids((file_id,))
    try:
        _, remote_path = TIFF_OBJECTS[kind]
    except KeyError as exc:
        raise HubMAPTiffDownloadError(f"Unknown TIFF object kind: {kind!r}") from exc
    return f"{HUBMAP_ASSET_BASE_URL}/{file_id}/{remote_path}"


def validate_b004_h5ad_file_ids(
    h5ad_path: str | Path,
    *,
    file_ids: Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Confirm that the requested B004 UUIDs occur in the declared source H5AD."""

    requested = _normalise_file_ids(file_ids)
    source = Path(h5ad_path).expanduser().resolve()
    if not source.is_file():
        raise HubMAPTiffDownloadError(f"Source H5AD is missing: {source}")
    try:
        import anndata as ad
    except ImportError as exc:  # pragma: no cover - environment guard
        raise HubMAPTiffDownloadError("H5AD validation requires anndata") from exc
    dataset = ad.read_h5ad(source, backed="r")
    try:
        if "File_ID" not in dataset.obs.columns:
            raise HubMAPTiffDownloadError("Source H5AD has no File_ID observation column")
        observed = {str(value) for value in dataset.obs["File_ID"]}
    finally:
        dataset.file.close()
    missing = sorted(set(requested).difference(observed))
    if missing:
        raise HubMAPTiffDownloadError(
            "Declared HuBMAP TIFF IDs are absent from the source H5AD: " + ", ".join(missing)
        )
    return requested


def _response_status(response: Any) -> int:
    status = getattr(response, "status", None)
    if status is None:
        status = response.getcode()
    return int(status)


def _total_size_from_headers(headers: Mapping[str, str], status: int, *, label: str) -> int:
    content_range = str(headers.get("Content-Range") or "")
    match = _CONTENT_RANGE_PATTERN.fullmatch(content_range)
    if match:
        return int(match.group(3))
    content_length = headers.get("Content-Length")
    if status == 200 and content_length and str(content_length).isdigit():
        return int(content_length)
    raise HubMAPTiffDownloadError(f"HuBMAP did not return a usable size for {label}")


def _probe_remote_object(file_id: str, kind: str, *, timeout_seconds: int) -> RemoteTiffObject:
    filename, _ = TIFF_OBJECTS[kind]
    url = hubmap_tiff_url(file_id, kind)
    request = Request(
        url,
        headers={"Range": "bytes=0-0", "User-Agent": HUBMAP_REQUEST_USER_AGENT},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = _response_status(response)
            if status not in {200, 206}:
                raise HubMAPTiffDownloadError(f"HuBMAP returned HTTP {status} while probing {url}")
            size_bytes = _total_size_from_headers(response.headers, status, label=url)
            response.read(1)
            return RemoteTiffObject(
                file_id=file_id,
                kind=kind,
                filename=filename,
                url=url,
                size_bytes=size_bytes,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )
    except HTTPError as exc:
        raise HubMAPTiffDownloadError(f"HuBMAP rejected {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise HubMAPTiffDownloadError(f"Unable to reach HuBMAP for {url}: {exc.reason}") from exc


def _target_path(tiff_root: Path, remote: RemoteTiffObject) -> Path:
    return tiff_root / remote.file_id / remote.filename


def _partial_path(target: Path) -> Path:
    return target.with_name(f"{target.name}.part")


def _partial_manifest_path(target: Path) -> Path:
    return target.with_name(f"{target.name}.part.json")


def _cache_receipt_path(target: Path) -> Path:
    return target.with_name(f"{target.name}.hubmap.json")


def _partial_payload(remote: RemoteTiffObject) -> dict[str, Any]:
    return {
        "schema": HUBMAP_TIFF_MANIFEST_SCHEMA,
        "url": remote.url,
        "size_bytes": remote.size_bytes,
        "etag": remote.etag,
        "last_modified": remote.last_modified,
    }


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            json.dump(dict(payload), handle, indent=2, sort_keys=True)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_json_mapping(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HubMAPTiffDownloadError(f"Cannot read {label}: {path}") from exc
    if not isinstance(payload, Mapping):
        raise HubMAPTiffDownloadError(f"{label} must contain a JSON object: {path}")
    return payload


def _validate_partial_manifest(target: Path, remote: RemoteTiffObject) -> None:
    metadata_path = _partial_manifest_path(target)
    payload = _read_json_mapping(metadata_path, label="partial HuBMAP TIFF metadata")
    expected = _partial_payload(remote)
    observed = {key: payload.get(key) for key in expected}
    if observed != expected:
        raise HubMAPTiffDownloadError(
            "Refusing to resume a TIFF partial whose HuBMAP identity changed: " f"{target}"
        )


def _validate_cache_receipt(target: Path, remote: RemoteTiffObject) -> None:
    metadata_path = _cache_receipt_path(target)
    payload = _read_json_mapping(metadata_path, label="HuBMAP TIFF cache receipt")
    expected = _partial_payload(remote)
    observed = {key: payload.get(key) for key in expected}
    if observed != expected:
        raise HubMAPTiffDownloadError(
            "Refusing a TIFF cache entry whose HuBMAP identity is absent or changed: " f"{target}"
        )


def validate_hubmap_tiff_cache(
    tiff_root: str | Path,
    *,
    file_ids: Sequence[str] | None = None,
) -> tuple[Path, ...]:
    """Require HuBMAP receipts for every TIFF used by the declared B004 cohort.

    This offline check is used immediately before image-native PIXIE processing.
    It makes the cache provenance contract hold even when a notebook cell is run
    out of order: TIFFs placed directly in the cache without HuBMAP receipts are
    rejected rather than treated as source inputs.
    """

    destination = Path(tiff_root).expanduser().resolve()
    requested = _normalise_file_ids(file_ids)
    targets: list[Path] = []
    for file_id in requested:
        for kind, (filename, _) in TIFF_OBJECTS.items():
            target = destination / file_id / filename
            if not target.is_file():
                raise HubMAPTiffDownloadError(f"HuBMAP TIFF cache entry is missing: {target}")
            payload = _read_json_mapping(
                _cache_receipt_path(target), label="HuBMAP TIFF cache receipt"
            )
            expected_url = hubmap_tiff_url(file_id, kind)
            size_bytes = payload.get("size_bytes")
            if (
                payload.get("schema") != HUBMAP_TIFF_MANIFEST_SCHEMA
                or payload.get("url") != expected_url
                or not isinstance(size_bytes, int)
                or isinstance(size_bytes, bool)
                or target.stat().st_size != size_bytes
            ):
                raise HubMAPTiffDownloadError(
                    "Refusing a TIFF cache entry without a valid HuBMAP receipt: " f"{target}"
                )
            targets.append(target)
    return tuple(targets)


def _cache_missing_bytes(tiff_root: Path, remote: RemoteTiffObject) -> int:
    target = _target_path(tiff_root, remote)
    partial = _partial_path(target)
    if target.exists():
        if not target.is_file():
            raise HubMAPTiffDownloadError(f"Expected a file at {target}, found another filesystem object")
        if target.stat().st_size != remote.size_bytes:
            raise HubMAPTiffDownloadError(
                f"Existing TIFF has an unexpected size and will not be overwritten: {target}"
            )
        _validate_cache_receipt(target, remote)
        return 0
    if not partial.exists():
        return remote.size_bytes
    if not partial.is_file():
        raise HubMAPTiffDownloadError(f"Expected a partial file at {partial}, found another filesystem object")
    partial_size = partial.stat().st_size
    if partial_size > remote.size_bytes:
        raise HubMAPTiffDownloadError(f"Partial TIFF is larger than its HuBMAP source: {partial}")
    if partial_size:
        _validate_partial_manifest(target, remote)
    return remote.size_bytes - partial_size


def _nearest_existing_directory(path: Path) -> Path:
    candidate = path
    while not candidate.exists():
        if candidate == candidate.parent:
            raise HubMAPTiffDownloadError(f"Cannot locate a filesystem for destination: {path}")
        candidate = candidate.parent
    if not candidate.is_dir():
        raise HubMAPTiffDownloadError(f"Destination parent is not a directory: {candidate}")
    return candidate


def plan_hubmap_tiff_download(
    *,
    h5ad_path: str | Path,
    tiff_root: str | Path,
    file_ids: Sequence[str] | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    reserve_bytes: int = DEFAULT_DOWNLOAD_RESERVE_BYTES,
) -> HubMAPTiffDownloadPlan:
    """Inspect the exact HuBMAP TIFF transfer without downloading image bytes."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if reserve_bytes < 0:
        raise ValueError("reserve_bytes cannot be negative")
    source = Path(h5ad_path).expanduser().resolve()
    requested = validate_b004_h5ad_file_ids(source, file_ids=file_ids)
    destination = Path(tiff_root).expanduser().resolve()
    objects = tuple(
        _probe_remote_object(file_id, kind, timeout_seconds=timeout_seconds)
        for file_id in requested
        for kind in TIFF_OBJECTS
    )
    missing = sum(_cache_missing_bytes(destination, remote) for remote in objects)
    free_bytes = shutil.disk_usage(_nearest_existing_directory(destination)).free
    return HubMAPTiffDownloadPlan(
        h5ad_path=source,
        tiff_root=destination,
        file_ids=requested,
        objects=objects,
        bytes_missing=missing,
        bytes_available=int(free_bytes),
        reserve_bytes=reserve_bytes,
    )


def _validate_download_response(response: Any, remote: RemoteTiffObject, *, start: int) -> None:
    status = _response_status(response)
    if status == 206:
        content_range = str(response.headers.get("Content-Range") or "")
        match = _CONTENT_RANGE_PATTERN.fullmatch(content_range)
        if not match:
            raise HubMAPTiffDownloadError(f"HuBMAP returned an invalid range for {remote.url}")
        observed_start, _, observed_total = (int(value) for value in match.groups())
        if observed_start != start or observed_total != remote.size_bytes:
            raise HubMAPTiffDownloadError(f"HuBMAP range identity changed during download: {remote.url}")
    elif status == 200 and start == 0:
        total = _total_size_from_headers(response.headers, status, label=remote.url)
        if total != remote.size_bytes:
            raise HubMAPTiffDownloadError(f"HuBMAP object size changed during download: {remote.url}")
    else:
        raise HubMAPTiffDownloadError(
            f"HuBMAP did not honor the requested resume range for {remote.url} (HTTP {status})"
        )
    observed_etag = response.headers.get("ETag")
    if remote.etag and observed_etag and observed_etag != remote.etag:
        raise HubMAPTiffDownloadError(f"HuBMAP object ETag changed during download: {remote.url}")


def _download_remote_object(
    tiff_root: Path,
    remote: RemoteTiffObject,
    *,
    timeout_seconds: int,
) -> tuple[str, int]:
    """Download one object atomically, preserving a resumable partial on interruption."""

    target = _target_path(tiff_root, remote)
    partial = _partial_path(target)
    partial_metadata = _partial_manifest_path(target)
    if target.exists():
        if not target.is_file() or target.stat().st_size != remote.size_bytes:
            raise HubMAPTiffDownloadError(
                f"Existing TIFF has an unexpected size and will not be overwritten: {target}"
            )
        _validate_cache_receipt(target, remote)
        return "reused", 0
    if partial.exists() and not partial.is_file():
        raise HubMAPTiffDownloadError(f"Expected a partial file at {partial}, found another filesystem object")
    start = partial.stat().st_size if partial.exists() else 0
    if start > remote.size_bytes:
        raise HubMAPTiffDownloadError(f"Partial TIFF is larger than its HuBMAP source: {partial}")
    if start:
        _validate_partial_manifest(target, remote)
    elif partial_metadata.exists():
        _validate_partial_manifest(target, remote)
    if start == remote.size_bytes:
        _write_json_atomic(_cache_receipt_path(target), _partial_payload(remote))
        partial.replace(target)
        partial_metadata.unlink(missing_ok=True)
        return "resumed", 0

    target.parent.mkdir(parents=True, exist_ok=True)
    if not partial_metadata.exists():
        _write_json_atomic(partial_metadata, _partial_payload(remote))
    request = Request(
        remote.url,
        headers={
            "Range": f"bytes={start}-",
            "User-Agent": HUBMAP_REQUEST_USER_AGENT,
        },
    )
    transferred = 0
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            _validate_download_response(response, remote, start=start)
            mode = "ab" if partial.exists() else "xb"
            with partial.open(mode) as handle:
                remaining = remote.size_bytes - start
                while True:
                    block = response.read(min(DOWNLOAD_CHUNK_BYTES, remaining))
                    if not block:
                        break
                    if len(block) > remaining:
                        raise HubMAPTiffDownloadError(f"HuBMAP sent too many bytes for {remote.url}")
                    handle.write(block)
                    transferred += len(block)
                    remaining -= len(block)
    except HTTPError as exc:
        raise HubMAPTiffDownloadError(f"HuBMAP rejected {remote.url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise HubMAPTiffDownloadError(f"Unable to reach HuBMAP for {remote.url}: {exc.reason}") from exc
    if partial.stat().st_size != remote.size_bytes:
        raise HubMAPTiffDownloadError(
            f"Incomplete HuBMAP TIFF download left resumable partial {partial}: "
            f"expected {remote.size_bytes} bytes, found {partial.stat().st_size}"
        )
    if target.exists():
        raise HubMAPTiffDownloadError(f"Refusing to overwrite a TIFF that appeared during download: {target}")
    _write_json_atomic(_cache_receipt_path(target), _partial_payload(remote))
    partial.replace(target)
    partial_metadata.unlink(missing_ok=True)
    return ("resumed" if start else "downloaded"), transferred


def _write_completion_manifest(
    plan: HubMAPTiffDownloadPlan,
    *,
    statuses: Mapping[str, str],
) -> Path:
    manifest = plan.tiff_root / "hubmap_tiff_manifest.json"
    objects = []
    for remote in plan.objects:
        dataset = _B004_BY_FILE_ID[remote.file_id]
        target = _target_path(plan.tiff_root, remote)
        objects.append(
            {
                **remote.as_dict(),
                "hubmap_id": dataset.hubmap_id,
                "lab_dataset_id": dataset.lab_dataset_id,
                "tissue_location": dataset.tissue_location,
                "cache_path": str(target.relative_to(plan.tiff_root)),
                "local_size_bytes": target.stat().st_size,
                "status": statuses[str(target)],
            }
        )
    _write_json_atomic(
        manifest,
        {
            "schema": HUBMAP_TIFF_MANIFEST_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "h5ad_path": str(plan.h5ad_path),
            "file_ids": list(plan.file_ids),
            "objects": objects,
        },
    )
    return manifest


def download_b004_hubmap_tiff_pairs(
    *,
    h5ad_path: str | Path,
    tiff_root: str | Path,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    reserve_bytes: int = DEFAULT_DOWNLOAD_RESERVE_BYTES,
) -> HubMAPTiffDownloadResult:
    """Download the validated B004 TIFF pairs from HuBMAP after disk preflight."""

    plan = plan_hubmap_tiff_download(
        h5ad_path=h5ad_path,
        tiff_root=tiff_root,
        timeout_seconds=timeout_seconds,
        reserve_bytes=reserve_bytes,
    )
    if not plan.has_sufficient_space:
        raise HubMAPTiffDownloadError(
            "Insufficient free disk for HuBMAP TIFF acquisition: "
            f"need {_as_gib(plan.required_free_bytes)} including reserve, "
            f"have {_as_gib(plan.bytes_available)}."
        )

    statuses: dict[str, str] = {}
    transferred = 0
    for remote in plan.objects:
        status, object_bytes = _download_remote_object(
            plan.tiff_root,
            remote,
            timeout_seconds=timeout_seconds,
        )
        statuses[str(_target_path(plan.tiff_root, remote))] = status
        transferred += object_bytes
    manifest = _write_completion_manifest(plan, statuses=statuses)
    values = tuple(statuses.values())
    return HubMAPTiffDownloadResult(
        plan=plan,
        manifest_path=manifest,
        downloaded_objects=values.count("downloaded"),
        resumed_objects=values.count("resumed"),
        reused_objects=values.count("reused"),
        bytes_transferred=transferred,
    )


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download B004 HuBMAP OME-TIFF pairs.")
    parser.add_argument("--h5ad", required=True, help="Checksum-verified Duke record 505 H5AD")
    parser.add_argument("--tiff-root", required=True, help="Destination cache for paired OME-TIFF files")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--reserve-gib", type=float, default=1.0)
    args = parser.parse_args(argv)
    reserve_bytes = int(args.reserve_gib * 1024**3)
    result = download_b004_hubmap_tiff_pairs(
        h5ad_path=args.h5ad,
        tiff_root=args.tiff_root,
        timeout_seconds=args.timeout_seconds,
        reserve_bytes=reserve_bytes,
    )
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - command-line entrypoint
    raise SystemExit(_main())
