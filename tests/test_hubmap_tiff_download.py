import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from llm_spatial_omics_clustering.final_figures_runtime import hubmap


class _FakeResponse:
    def __init__(self, payload: bytes, *, headers: dict[str, str], status: int = 206):
        self._payload = payload
        self.headers = headers
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._payload)
        value, self._payload = self._payload[:size], self._payload[size:]
        return value


class HubMAPTiffDownloadTests(unittest.TestCase):
    def test_b004_mapping_matches_the_hubmap_id_workbook(self):
        self.assertEqual(len(hubmap.B004_HUBMAP_DATASETS), 8)
        self.assertEqual(len(set(hubmap.B004_FILE_IDS)), 8)
        transverse = next(
            item for item in hubmap.B004_HUBMAP_DATASETS if item.tissue_location == "Transverse"
        )
        self.assertEqual(transverse.file_id, "768b7adb649959b6a4e354867595032d")
        self.assertEqual(transverse.hubmap_id, "HBM889.KDGM.632")

    def test_asset_urls_target_the_paired_ome_tiff_layout(self):
        file_id = hubmap.B004_FILE_IDS[0]
        self.assertEqual(
            hubmap.hubmap_tiff_url(file_id, "expression"),
            "https://assets.hubmapconsortium.org/"
            f"{file_id}/ometiff-pyramids/pipeline_output/expr/reg001_expr.ome.tif",
        )
        self.assertEqual(
            hubmap.hubmap_tiff_url(file_id, "mask"),
            "https://assets.hubmapconsortium.org/"
            f"{file_id}/ometiff-pyramids/pipeline_output/mask/reg001_mask.ome.tif",
        )

    def test_probe_uses_a_user_agent_and_a_one_byte_range(self):
        observed = {}

        def fake_urlopen(request, timeout):
            observed["headers"] = dict(request.header_items())
            observed["timeout"] = timeout
            return _FakeResponse(
                b"x",
                headers={"Content-Range": "bytes 0-0/13", "ETag": '"example"'},
            )

        with patch.object(hubmap, "urlopen", side_effect=fake_urlopen):
            remote = hubmap._probe_remote_object(
                hubmap.B004_FILE_IDS[0], "expression", timeout_seconds=17
            )
        headers = {key.casefold(): value for key, value in observed["headers"].items()}
        self.assertEqual(headers["range"], "bytes=0-0")
        self.assertIn("llm-spatial-omics-clustering", headers["user-agent"].casefold())
        self.assertEqual(observed["timeout"], 17)
        self.assertEqual(remote.size_bytes, 13)

    def test_resumable_download_appends_only_the_missing_range(self):
        remote = hubmap.RemoteTiffObject(
            file_id=hubmap.B004_FILE_IDS[0],
            kind="expression",
            filename="reg001_expr.ome.tif",
            url="https://assets.hubmapconsortium.org/example.tif",
            size_bytes=4,
            etag='"example"',
            last_modified=None,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / remote.file_id / remote.filename
            target.parent.mkdir(parents=True)
            partial = hubmap._partial_path(target)
            partial.write_bytes(b"ab")
            hubmap._write_json_atomic(
                hubmap._partial_manifest_path(target), hubmap._partial_payload(remote)
            )

            def fake_urlopen(request, timeout):
                headers = {key.casefold(): value for key, value in request.header_items()}
                self.assertEqual(headers["range"], "bytes=2-")
                return _FakeResponse(
                    b"cd",
                    headers={
                        "Content-Range": "bytes 2-3/4",
                        "ETag": '"example"',
                    },
                )

            with patch.object(hubmap, "urlopen", side_effect=fake_urlopen):
                status, transferred = hubmap._download_remote_object(
                    root, remote, timeout_seconds=17
                )
            self.assertEqual(status, "resumed")
            self.assertEqual(transferred, 2)
            self.assertEqual(target.read_bytes(), b"abcd")
            self.assertFalse(partial.exists())
            self.assertFalse(hubmap._partial_manifest_path(target).exists())
            self.assertEqual(
                hubmap._read_json_mapping(
                    hubmap._cache_receipt_path(target), label="HuBMAP TIFF cache receipt"
                ),
                hubmap._partial_payload(remote),
            )

    def test_unproven_complete_tiff_is_not_accepted_as_an_input_cache(self):
        remote = hubmap.RemoteTiffObject(
            file_id=hubmap.B004_FILE_IDS[0],
            kind="expression",
            filename="reg001_expr.ome.tif",
            url="https://assets.hubmapconsortium.org/example.tif",
            size_bytes=4,
            etag='"example"',
            last_modified=None,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / remote.file_id / remote.filename
            target.parent.mkdir(parents=True)
            target.write_bytes(b"abcd")
            with self.assertRaisesRegex(hubmap.HubMAPTiffDownloadError, "cache receipt"):
                hubmap._cache_missing_bytes(root, remote)

    def test_identified_hubmap_cache_is_reused_without_downloading(self):
        remote = hubmap.RemoteTiffObject(
            file_id=hubmap.B004_FILE_IDS[0],
            kind="expression",
            filename="reg001_expr.ome.tif",
            url="https://assets.hubmapconsortium.org/example.tif",
            size_bytes=4,
            etag='"example"',
            last_modified=None,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / remote.file_id / remote.filename
            target.parent.mkdir(parents=True)
            target.write_bytes(b"abcd")
            hubmap._write_json_atomic(
                hubmap._cache_receipt_path(target), hubmap._partial_payload(remote)
            )
            self.assertEqual(hubmap._cache_missing_bytes(root, remote), 0)
            self.assertEqual(
                hubmap._download_remote_object(root, remote, timeout_seconds=17),
                ("reused", 0),
            )

    def test_cache_validation_requires_a_receipt_for_each_tiff(self):
        file_id = hubmap.B004_FILE_IDS[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(
                hubmap,
                "TIFF_OBJECTS",
                {"expression": hubmap.TIFF_OBJECTS["expression"]},
            ):
                filename, _ = hubmap.TIFF_OBJECTS["expression"]
                target = root / file_id / filename
                target.parent.mkdir(parents=True)
                target.write_bytes(b"abcd")
                with self.assertRaisesRegex(hubmap.HubMAPTiffDownloadError, "cache receipt"):
                    hubmap.validate_hubmap_tiff_cache(root, file_ids=(file_id,))
                hubmap._write_json_atomic(
                    hubmap._cache_receipt_path(target),
                    {
                        "schema": hubmap.HUBMAP_TIFF_MANIFEST_SCHEMA,
                        "url": hubmap.hubmap_tiff_url(file_id, "expression"),
                        "size_bytes": 4,
                        "etag": '"example"',
                        "last_modified": None,
                    },
                )
                self.assertEqual(
                    hubmap.validate_hubmap_tiff_cache(root, file_ids=(file_id,)),
                    (target.resolve(),),
                )

    def test_plan_exposes_free_space_preflight(self):
        remote = hubmap.RemoteTiffObject(
            file_id=hubmap.B004_FILE_IDS[0],
            kind="expression",
            filename="reg001_expr.ome.tif",
            url="https://assets.hubmapconsortium.org/example.tif",
            size_bytes=100,
            etag=None,
            last_modified=None,
        )
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(hubmap, "validate_b004_h5ad_file_ids", return_value=(remote.file_id,)):
                def fake_probe(file_id, kind, *, timeout_seconds):
                    filename, _ = hubmap.TIFF_OBJECTS[kind]
                    return hubmap.RemoteTiffObject(
                        file_id=file_id,
                        kind=kind,
                        filename=filename,
                        url=f"https://assets.hubmapconsortium.org/{kind}.tif",
                        size_bytes=100,
                        etag=None,
                        last_modified=None,
                    )

                with patch.object(hubmap, "_probe_remote_object", side_effect=fake_probe):
                    with patch.object(
                        hubmap.shutil,
                        "disk_usage",
                        return_value=SimpleNamespace(free=50),
                    ):
                        plan = hubmap.plan_hubmap_tiff_download(
                            h5ad_path=Path(temporary) / "source.h5ad",
                            tiff_root=Path(temporary) / "tiff",
                            file_ids=(remote.file_id,),
                            reserve_bytes=1,
                        )
        self.assertEqual(plan.bytes_missing, 200)
        self.assertEqual(plan.required_free_bytes, 201)
        self.assertFalse(plan.has_sufficient_space)

    def test_command_line_entrypoint_always_runs_hubmap_acquisition(self):
        result = SimpleNamespace(as_dict=lambda: {"source": "hubmap"})
        with patch.object(hubmap, "download_b004_hubmap_tiff_pairs", return_value=result) as download:
            with redirect_stdout(StringIO()):
                exit_code = hubmap._main(["--h5ad", "source.h5ad", "--tiff-root", "cache"])
        self.assertEqual(exit_code, 0)
        download.assert_called_once_with(
            h5ad_path="source.h5ad",
            tiff_root="cache",
            timeout_seconds=hubmap.DEFAULT_TIMEOUT_SECONDS,
            reserve_bytes=hubmap.DEFAULT_DOWNLOAD_RESERVE_BYTES,
        )


if __name__ == "__main__":
    unittest.main()
