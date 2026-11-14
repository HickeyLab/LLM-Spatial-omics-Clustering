"""Scientific invariants for offline coarsening, classifiers and calibration."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reviewer47_offline", ROOT / "scripts/revision/reviewer47/offline.py")
offline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = offline
spec.loader.exec_module(offline)


def fixture(directory):
    bundle = directory / "bundle"
    bundle.mkdir()
    markers = [f"marker_{i:02d}" for i in range(47)]
    split = {f"region_{i}": ("train" if i < 4 else "calibration" if i < 6 else "test") for i in range(8)}
    keys = pd.DataFrame({"File_ID": np.repeat(list(split), 16), "ID": np.tile(np.arange(16).astype(str), 8)})
    rng = np.random.default_rng(42)
    raw = rng.normal(0, 2, (len(keys), 47))
    truth = (keys.ID.astype(int).to_numpy() // 2) % 2
    raw[:, 0] = 6 * (2 * truth - 1) + rng.normal(0, .1, len(raw))
    truth[keys.ID.eq("15").to_numpy()] = 21
    memberships = keys.copy()
    for method in offline.METHODS:
        memberships[method] = (keys.ID.astype(int) % 8).astype(str)
    reference = memberships.copy()
    reference["split"] = keys.File_ID.map(split)
    reference["truth_label_code"] = truth
    reference["truth_label"] = ["Noise" if x == 21 else f"label_{x}" for x in truth]
    train = reference.split.eq("train").to_numpy()
    views, _, _ = offline.cell_feature_views(raw, train)
    profiles = {"means": [], "fractions": []}
    for method in offline.METHODS:
        for cluster in sorted(memberships[method].unique()):
            mask = memberships[method].eq(cluster).to_numpy()
            for name, values in [("means", views["all_means"]), ("fractions", raw > 0)]:
                profiles[name].append({"method": method, "cluster_id": cluster, "n_cells": int(mask.sum()),
                                       **dict(zip(markers, values[mask].mean(0)))})
    h5ad = directory / "authoritative.h5ad"
    with h5py.File(h5ad, "w") as handle:
        handle.create_dataset("X", data=raw[:, :45])
        handle.create_dataset("var/_index", data=markers[:45], dtype=h5py.string_dtype())
        handle.create_dataset("obs/CD123", data=raw[:, 45])
        handle.create_dataset("obs/CDX2", data=raw[:, 46])
        handle.create_dataset("obs/ID", data=keys.ID.astype(int).to_numpy())
        handle.create_dataset("obs/File_ID", data=keys.File_ID.to_numpy(dtype=object), dtype=h5py.string_dtype())
    ontology = [f"label_{i}" for i in range(28)]
    ontology[21] = "Noise"
    protocol = {"markers": markers, "ontology": ontology, "n_cells": len(keys), "split": split,
                "measurement_source": {"sha256": offline.file_sha256(h5ad)}}
    (bundle / "protocol.json").write_text(json.dumps(protocol))
    memberships.to_csv(bundle / "memberships.csv.gz", index=False)
    reference.to_csv(bundle / "reference_cells.csv.gz", index=False)
    for name, filename in [("means", "profiles_means_z.csv"), ("fractions", "profiles_fractions.csv")]:
        pd.DataFrame(profiles[name]).to_csv(bundle / filename, index=False)
    predictions = []
    for method in offline.METHODS:
        for c in range(8):
            true = (c // 2) % 2
            labels = [true] * 4
            if c % 4 == 1:
                labels[3] = 1 - true
            elif c % 4 == 2:
                labels[2:] = [1 - true] * 2
            elif c % 4 == 3:
                labels[1:] = [1 - true] * 3
            for family, label in zip(offline.FAMILIES, labels):
                predictions.append({"method": method, "cluster_id": str(c), "arm": "all_means_fractions",
                                    "model_family": family, "pred_label_code": label})
    pd.DataFrame(predictions).to_csv(bundle / "cluster_predictions.csv", index=False)
    return bundle, h5ad, raw, reference


class WardTests(unittest.TestCase):
    def test_weighted_cost_and_conservation(self):
        maps, trace = offline.weighted_ward(["b", "a", "c"], [1, 3, 2], [[0], [2], [20]], targets=(1, 2))
        self.assertEqual(trace[0]["left_leaves"], ["a"])
        self.assertEqual(trace[0]["right_leaves"], ["b"])
        self.assertEqual(trace[0]["ward_cost"], 3.0)
        self.assertEqual(trace[0]["merged_n"], 4)
        self.assertEqual(trace[-1]["merged_n"], 6)
        for k, mapping in maps.items():
            self.assertEqual(set(mapping), {"a", "b", "c"})
            self.assertEqual(len(set(mapping.values())), k)

    def test_ties_and_input_order_are_deterministic(self):
        a = offline.weighted_ward(["c", "a", "b"], [1, 1, 1], [[0], [0], [0]], targets=(1, 2))
        b = offline.weighted_ward(["b", "c", "a"], [1, 1, 1], [[0], [0], [0]], targets=(1, 2))
        self.assertEqual(a, b)
        self.assertEqual(a[1][0]["left_leaves"], ["a"])
        self.assertEqual(a[1][0]["right_leaves"], ["b"])

    def test_invalid_profiles_rejected(self):
        for ids, counts, means in [(["a", "a"], [1, 2], [[0], [1]]),
                                   (["a", "b"], [0, 2], [[0], [1]]),
                                   (["a", "b"], [1, 2], [[np.nan], [1]])]:
            with self.assertRaises(ValueError):
                offline.weighted_ward(ids, counts, means, targets=(1,))

    def test_reference_labels_change_scores_not_the_tree(self):
        a = offline.weighted_ward(["a", "b", "c"], [2, 2, 2], [[0], [1], [10]], targets=(2,))
        b = offline.weighted_ward(["a", "b", "c"], [2, 2, 2], [[0], [1], [10]], targets=(2,))
        labels = np.array([0, 0, 1, 1, 1, 1])
        coarse = [a[0][2][x] for x in ["a", "a", "b", "b", "c", "c"]]
        self.assertEqual(a, b)
        self.assertNotEqual(offline.partition_metrics(labels, coarse)["purity"],
                            offline.partition_metrics([0, 1, 0, 1, 0, 1], coarse)["purity"])


class CalibrationTests(unittest.TestCase):
    def test_support_keeps_four_model_denominator_and_missing(self):
        scores = offline.agreement_scores([[1, 1, 1, -1], [0, 1, 2, 3], [np.nan] * 4])
        np.testing.assert_allclose(scores[0, :3], .75)
        self.assertTrue(np.isnan(scores[0, 3]))
        np.testing.assert_allclose(scores[1], .25)
        self.assertTrue(np.isnan(scores[2]).all())

    def test_fixed_partition_is_independent_of_labels(self):
        a = {str(i): offline.cluster_partition("leiden", str(i)) for i in range(100)}
        self.assertEqual(a, {str(i): offline.cluster_partition("leiden", str(i)) for i in range(100)})
        self.assertEqual(set(a.values()), {"development", "evaluation"})

    def test_missing_stays_in_planned_agreement_and_coverage(self):
        result = offline.binary_score_metrics([1, np.nan, .5], [True, False, False], [True, False, True])
        self.assertEqual(result["planned_cells"], 3)
        self.assertAlmostEqual(result["reference_agreement_planned"], 1 / 3)
        self.assertAlmostEqual(result["delivery_coverage"], 2 / 3)
        self.assertAlmostEqual(result["brier"], .125)
        rows = offline.risk_coverage([.5, .5, 1], [True, False, True], [True] * 3, [.5, .75, 1.1])
        self.assertEqual(rows[0]["retained_cells"], 3)
        self.assertEqual(rows[1]["retained_cells"], 1)
        self.assertTrue(np.isnan(rows[2]["risk"]))

    def test_calibrator_uses_development_only_and_constant_fallback(self):
        fn, receipt, constant = offline._fit_calibrator([.5, 1], [True, True], ["r0", "r1"])
        self.assertEqual(receipt["kind"], "constant")
        np.testing.assert_allclose(fn(np.array([.25, 1])), constant)
        fn, receipt, _ = offline._fit_calibrator([np.nan], [False], ["r0"])
        self.assertIsNone(fn)
        self.assertEqual(receipt["kind"], "unavailable")


class OfflineIntegrationTests(unittest.TestCase):
    def test_granularity_runs_and_cell_keys_are_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            b, _, _, _ = fixture(d)
            receipt = offline.run_granularity(b, d / "out", targets=(2, 4))
            self.assertEqual(receipt["new_annotation_calls"], 0)
            original = pd.read_csv(b / "memberships.csv.gz", dtype=str)
            for k in (2, 4):
                frame = pd.read_csv(d / f"out/assignments_K{k}.csv.gz", dtype=str)
                self.assertTrue(frame[offline.KEYS].equals(original[offline.KEYS]))
                for method in offline.METHODS:
                    self.assertEqual(frame[method].nunique(), k)
            with self.assertRaises(FileExistsError):
                offline.run_granularity(b, d / "out", targets=(2, 4))

    def test_assignments_and_calibration_split_are_sealed_before_labels(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            b, _, _, _ = fixture(d)
            original = offline.load_bundle
            for kind, runner, extra, seal in [
                    ("granularity", offline.run_granularity, {"targets": (2, 4)}, "coarsening_freeze.json"),
                    ("calibration", offline.run_agreement_calibration, {}, "calibration_split_freeze.json")]:
                out, calls = d / kind, []

                def checked_load(path, *, include_reference_labels=True):
                    calls.append(include_reference_labels)
                    if include_reference_labels:
                        self.assertTrue((out / seal).is_file())
                    result = original(path, include_reference_labels=include_reference_labels)
                    if not include_reference_labels:
                        self.assertNotIn("truth_label_code", result.reference)
                        self.assertNotIn("truth_label", result.reference)
                    return result

                with patch.object(offline, "load_bundle", checked_load):
                    runner(b, out, **extra)
                self.assertEqual(calls, [False, True])

    def test_calibration_runs_on_disjoint_clusters_and_regions(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            b, _, _, ref = fixture(d)
            # Deliberate missing accepted prediction stays missing, rather than Noise.
            frame = pd.read_csv(b / "cluster_predictions.csv")
            frame = frame.drop(frame.index[0])
            frame.to_csv(b / "cluster_predictions.csv", index=False)
            receipt = offline.run_agreement_calibration(b, d / "out")
            self.assertEqual(receipt["conditions"], 16)
            self.assertTrue(receipt["cluster_and_region_separation_verified"])
            split = pd.read_csv(d / "out/calibration_cluster_split.csv", dtype=str)
            self.assertFalse(split[["method", "cluster_id"]].duplicated().any())
            metrics = pd.read_csv(d / "out/calibration_metrics.csv")
            self.assertEqual(set(metrics.region), {"region_6", "region_7", "pooled"})
            equal = pd.read_csv(d / "out/calibration_equal_test_region_metrics.csv")
            self.assertEqual(len(equal), 4 * 4 * 3)

    def test_duplicate_keys_and_reordered_markers_fail(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            b, _, _, _ = fixture(d)
            p = b / "profiles_means_z.csv"
            frame = pd.read_csv(p)
            cols = list(frame.columns)
            cols[3], cols[4] = cols[4], cols[3]
            frame[cols].to_csv(p, index=False)
            with self.assertRaisesRegex(ValueError, "reordered"):
                offline.load_bundle(b)

    def test_baselines_fit_only_train_cells_and_never_test_labels(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            b, h5ad, raw, ref = fixture(d)
            seen = []
            original = offline.LogisticRegression.fit

            def recording_fit(model, x, y, **kwargs):
                seen.append((len(x), np.array(y)))
                return original(model, x, y, **kwargs)

            with patch.object(offline.LogisticRegression, "fit", recording_fit):
                receipt = offline.run_classical_baselines(b, d / "out", h5ad)
            self.assertEqual(receipt["training_cells"], 64)
            self.assertEqual(len(seen), 10)
            expected = ref.loc[ref.split.eq("train"), "truth_label_code"].to_numpy()
            for n, y in seen:
                self.assertEqual(n, 64)
                np.testing.assert_array_equal(y, expected)
            selected = json.loads((d / "out/classifier_models.json").read_text())
            self.assertEqual(len(selected), 8)
            self.assertTrue(all(v["selection_population"] == "two calibration regions only" for v in selected.values()))
            actual = pd.read_csv(d / "out/classifier_cluster_predictions.csv", dtype={"cluster_id": str})
            means = pd.read_csv(b / "profiles_means_z.csv", dtype={"cluster_id": str})
            markers = json.loads((b / "protocol.json").read_text())["markers"]
            query = np.rint(means[means.method.eq("leiden")].sort_values("cluster_id")[markers].to_numpy() * 1000) / 1000
            for classifier in ["nearest_centroid", "logistic_regression"]:
                prediction = offline.predict_saved_baseline(d / "out", "leiden", "all_means", classifier, query)
                saved = actual[actual.method.eq("leiden") & actual.arm.eq("all_means") & actual.classifier.eq(classifier)].sort_values("cluster_id")
                np.testing.assert_array_equal(prediction, saved.pred_label_code.to_numpy())

    def test_training_scaler_excludes_extreme_test_values(self):
        rng = np.random.default_rng(42)
        raw = rng.normal(size=(6, 47))
        changed = raw.copy()
        changed[4:] = 1e12
        train = np.array([1, 1, 1, 1, 0, 0], bool)
        _, c1, s1 = offline.cell_feature_views(raw, train)
        _, c2, s2 = offline.cell_feature_views(changed, train)
        np.testing.assert_array_equal(c1, c2)
        np.testing.assert_array_equal(s1, s2)

    def test_wrong_measurement_hash_blocks_before_fitting(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            b, h5ad, _, _ = fixture(d)
            with h5py.File(h5ad, "r+") as f:
                f["X"][0, 0] += 1
            with patch.object(offline.LogisticRegression, "fit", side_effect=AssertionError("must not fit")):
                with self.assertRaisesRegex(ValueError, "checksum"):
                    offline.run_classical_baselines(b, d / "out", h5ad)
            self.assertFalse((d / "out").exists())


if __name__ == "__main__":
    unittest.main()
