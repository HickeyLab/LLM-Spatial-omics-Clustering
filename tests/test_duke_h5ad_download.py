"""Focused tests for the Duke H5AD acquisition contract."""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from llm_spatial_omics_clustering import duke_h5ad


class _Response:
    status = 200

    def __init__(self, payload: bytes):
        self.payload = BytesIO(payload)
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int = -1) -> bytes:
        return self.payload.read(size)


class DukeH5ADDownloadTests(unittest.TestCase):
    def test_repository_contract_identifies_the_ground_truth_member(self) -> None:
        self.assertEqual(duke_h5ad.DUKE_RECORD_URL, "https://research.repository.duke.edu/record/505")
        self.assertEqual(
            duke_h5ad.DUKE_H5AD_MEMBER,
            "CODEX_annotated/20260130_HuBMAP_experted_annotated.h5ad",
        )
        self.assertEqual(
            duke_h5ad.DUKE_H5AD_SHA256,
            "5d0a59d1e7866dee5a3a06772c3c80ce7328ba6420bc140708be5ec451b8a49",
        )

    def test_download_extracts_only_the_declared_member_and_writes_receipt(self) -> None:
        payload = b"synthetic h5ad payload"
        archive_buffer = BytesIO()
        with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(duke_h5ad.DUKE_H5AD_MEMBER, payload)
        archive_bytes = archive_buffer.getvalue()

        constants = {
            "DUKE_ARCHIVE_SIZE_BYTES": len(archive_bytes),
            "DUKE_ARCHIVE_MD5": hashlib.md5(archive_bytes).hexdigest(),
            "DUKE_H5AD_SIZE_BYTES": len(payload),
            "DUKE_H5AD_SHA256": hashlib.sha256(payload).hexdigest(),
        }
        with TemporaryDirectory() as temporary:
            with patch.multiple(duke_h5ad, **constants):
                with patch.object(duke_h5ad, "urlopen", return_value=_Response(archive_bytes)):
                    result = duke_h5ad.download_duke_h5ad(Path(temporary))
            self.assertEqual(result.path.read_bytes(), payload)
            self.assertTrue(result.manifest_path.is_file())
            self.assertFalse(result.h5ad_reused)
            self.assertEqual(result.bytes_transferred, len(archive_bytes))

            with patch.multiple(duke_h5ad, **constants):
                reused = duke_h5ad.download_duke_h5ad(Path(temporary))
            self.assertTrue(reused.h5ad_reused)
            self.assertEqual(reused.bytes_transferred, 0)


if __name__ == "__main__":
    unittest.main()
