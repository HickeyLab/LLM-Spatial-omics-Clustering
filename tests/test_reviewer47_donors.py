"""External donor admission refuses incomplete, mismatched or unbound evidence."""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts.revision.reviewer47 import donors


class DonorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.markers = [f"m{i}" for i in range(47)]
        self.keys = [("A", "1"), ("A", "2"), ("B", "3")]

    def artifact(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, dict):
            path.write_text(json.dumps(value))
        elif isinstance(value, str):
            path.write_text(value)
        else:
            path.write_bytes(value)
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def fixture(self, sweeps=2):
        protocol = {"actual_sweeps": sweeps, "dmh_iter": 5, "n_markers": 47,
                    "requested_clusters": 300, "sampling_seeds": [42, 43],
                    "n_cells": 3, "n_regions": 2, "beta_rounds_per_sweep": 5,
                    "donor": "B005", "marker_columns": self.markers,
                    "reference_labels_supplied_to_fit": False}
        contract = {"donor": "B005", "expected_sweeps": sweeps, "markers": self.markers,
                    "dmh_iter": 5, "required_seeds": [42, 43], "primary_seed": 42,
                    "artifact_root": str(self.root)}
        selection = {"donor": "B005", "reference_labels_used": False, "markers": self.markers,
                     "expected_n_cells": 3, "regions": ["A", "B"], "mapping_verified": True,
                     "source_h5ad_sha256": "a" * 64}
        buf = io.BytesIO()
        np.savez_compressed(buf, y=np.arange(141).reshape(3, 47), counts=np.array([2, 1]))
        selection_artifact = self.artifact("selection.json", selection)
        protocol["selection_sha256"] = selection_artifact["sha256"]
        files = {"protocol": self.artifact("protocol.json", protocol),
                 "selection": selection_artifact,
                 "inputs": self.artifact("inputs.npz", buf.getvalue()),
                 "cell_keys": self.artifact("cell_keys.csv", "File_ID,ID\nA,1\nA,2\nB,3\n")}
        contract.update(selection_sha256=files["selection"]["sha256"], source_h5ad_sha256="a" * 64)
        labels = np.array([1, 1, 2])
        beta = np.ones((300, 2))
        chains = {}
        for seed in [42, 43]:
            traces = []
            for sweep in range(1, sweeps + 1):
                buf = io.BytesIO()
                np.savez_compressed(buf, labels=labels, beta=beta)
                traces.append({**self.artifact(f"seed{seed}/trace{sweep}.npz", buf.getvalue()), "sweep": sweep})
            state = {"seed": seed, "sweeps_completed": sweeps,
                     "protocol_sha256": files["protocol"]["sha256"],
                     "numpy_rng": {"engine": "MT19937", "keys": [0] * 624,
                                   "position": 0, "has_gauss": 0, "cached_gaussian": 0.0}}
            buf = io.BytesIO()
            np.savez_compressed(buf, metadata=np.frombuffer(json.dumps(state).encode(), dtype=np.uint8),
                                x=np.array([[1, 1], [2, 0]]), beta=beta,
                                n_cache=np.bincount(labels, minlength=300),
                                ybar_cache=np.zeros((300, 47)), sumsqr_cache=np.zeros((300, 47)))
            chains[str(seed)] = {"status": "complete", "sweeps_completed": sweeps, "job_id": str(seed),
                "scheduler_evidence": self.artifact(f"seed{seed}/accounting.json", {"job_id": str(seed), "state": "COMPLETED", "exit_code": "0:0"}),
                "assignments": self.artifact(f"seed{seed}/assignments.csv", "File_ID,ID,spatialsort_cluster\nA,1,1\nA,2,1\nB,3,2\n"),
                "checkpoint": self.artifact(f"seed{seed}/checkpoint.npz", buf.getvalue()), "traces": traces}
        receipt = {"schema": donors.HANDOFF_SCHEMA, "producer_thread_id": donors.PRODUCER_THREAD_ID,
                   "donor": "B005", "files": files, "chains": chains}
        return receipt, contract

    def test_complete_50_is_admitted_only_as_explicit_50_contract(self):
        receipt, contract = self.fixture(50)
        result = donors.admit_spatialsort_handoff(receipt, contract)
        self.assertTrue(result["passed"])
        self.assertEqual(result["chains"]["42"]["sweeps"], 50)
        self.assertFalse(result["automatic_launch"])
        contract["expected_sweeps"] = 100
        with self.assertRaisesRegex(donors.DonorAdmissionError, "actual_sweeps"):
            donors.admit_spatialsort_handoff(receipt, contract)

    def test_missing_or_incomplete_seed_and_scheduler_fail(self):
        receipt, contract = self.fixture()
        for field, value in [("status", "running"), ("sweeps_completed", 1)]:
            changed = copy.deepcopy(receipt)
            changed["chains"]["43"][field] = value
            with self.assertRaises(donors.DonorAdmissionError):
                donors.admit_spatialsort_handoff(changed, contract)
        receipt["chains"]["42"]["scheduler_evidence"] = self.artifact("timeout.json", {"job_id": "42", "state": "TIMEOUT", "exit_code": "0:0"})
        with self.assertRaisesRegex(donors.DonorAdmissionError, "scheduler"):
            donors.admit_spatialsort_handoff(receipt, contract)

    def test_missing_trace_and_wrong_assignment_join_fail(self):
        receipt, contract = self.fixture()
        changed = copy.deepcopy(receipt)
        changed["chains"]["42"]["traces"].pop()
        with self.assertRaisesRegex(donors.DonorAdmissionError, "every expected"):
            donors.admit_spatialsort_handoff(changed, contract)
        receipt["chains"]["42"]["assignments"] = self.artifact("wrong.csv", "File_ID,ID,spatialsort_cluster\nA,2,1\nA,1,1\nB,3,2\n")
        with self.assertRaisesRegex(donors.DonorAdmissionError, "exact input order"):
            donors.admit_spatialsort_handoff(receipt, contract)

    def test_hash_mismatch_and_export_path_escape_fail(self):
        receipt, contract = self.fixture()
        receipt["files"]["protocol"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(donors.DonorAdmissionError, "hash mismatch"):
            donors.admit_spatialsort_handoff(receipt, contract)
        receipt, contract = self.fixture()
        contract["artifact_root"] = str(self.root / "different")
        with self.assertRaisesRegex(donors.DonorAdmissionError, "escapes"):
            donors.admit_spatialsort_handoff(receipt, contract)

    def test_dry_inspection_never_admits(self):
        receipt, contract = self.fixture()
        self.assertFalse(donors.admit_spatialsort_handoff(receipt, contract, verify_files=False)["admitted_for_annotation"])

    def test_frozen_selection_and_source_hashes_are_required(self):
        receipt, contract = self.fixture()
        for name in ("selection_sha256", "source_h5ad_sha256"):
            changed = copy.deepcopy(contract)
            changed[name] = "b" * 64
            with self.assertRaisesRegex(donors.DonorAdmissionError, "frozen hash"):
                donors.admit_spatialsort_handoff(receipt, changed)
            changed.pop(name)
            with self.assertRaisesRegex(donors.DonorAdmissionError, "explicit approved"):
                donors.admit_spatialsort_handoff(receipt, changed)

    def test_marker_order_missing_values_and_duplicate_keys_fail(self):
        for markers in [self.markers[:-1], self.markers[::-1], self.markers[:-1] + ["m0"]]:
            with self.assertRaises(donors.DonorAdmissionError):
                donors.validate_measurements(self.keys, np.ones((3, 47)), markers, self.markers)
        values = np.ones((3, 47))
        values[0, 0] = np.nan
        with self.assertRaises(donors.DonorAdmissionError):
            donors.validate_measurements(self.keys, values, self.markers, self.markers)
        with self.assertRaisesRegex(donors.DonorAdmissionError, "Duplicate"):
            donors.canonical_keys(self.keys + [self.keys[0]])

    def test_common_population_is_intersection_not_imputed_coverage(self):
        result = donors.common_verified_population({"leiden": self.keys, "pixie": self.keys[:2]}, self.keys)
        self.assertEqual(result["common_cells"], 2)
        self.assertAlmostEqual(result["coverage"], 2 / 3)

    def test_projection_requires_exact_new_cohort_binding(self):
        vocabulary = [f"n{i}" for i in range(28)]
        target = [f"t{i}" for i in range(23)]
        mapping = {n: target[i % 23] for i, n in enumerate(vocabulary)}
        with self.assertRaisesRegex(donors.DonorAdmissionError, "exact donor cells"):
            donors.project_native_predictions(vocabulary, mapping, native_vocabulary=vocabulary,
                target_vocabulary=target, cohort_key_sha256="new", approved_cohort_key_sha256="old")
        out = donors.project_native_predictions(vocabulary, mapping, native_vocabulary=vocabulary,
            target_vocabulary=target, cohort_key_sha256="new", approved_cohort_key_sha256="new")
        self.assertEqual(len(out), 28)
        self.assertEqual(vocabulary[0], "n0")

    def test_observer_never_assumes_submission_or_completion(self):
        self.artifact("request.json", {"actual_sweeps": 50, "dmh_iter": 5, "n_markers": 47,
            "sampling_seeds": [42, 43], "requested_clusters": 300, "execution_status": "not_submitted",
            "beta_rounds_per_sweep": 5})
        without = donors.observe_external_campaign(self.root, self.markers)
        self.assertEqual(without["status"], "waiting_protocol_confirmation")
        contract = {"expected_sweeps": 50, "dmh_iter": 5, "required_seeds": [42, 43]}
        with_contract = donors.observe_external_campaign(self.root, self.markers, contract)
        self.assertEqual(with_contract["status"], "awaiting_completion")
        self.assertFalse(with_contract["admitted_for_annotation"])
        self.assertEqual(with_contract["jobs_submitted"], 0)

    def test_dataless_files_are_not_read_or_marked_verified(self):
        path = self.root / "dataless.json"
        path.write_text("{}")
        real = path.stat()
        class Info:
            st_flags = donors._DATALESS_FLAG
            st_size, st_mode = real.st_size, real.st_mode
        with patch.object(Path, "stat", return_value=Info()):
            with self.assertRaisesRegex(donors.DonorAdmissionError, "Dataless"):
                donors._safe_read(path)


if __name__ == "__main__":
    unittest.main()
