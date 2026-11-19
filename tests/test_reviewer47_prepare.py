"""Scientific and blinding invariants for the offline follow-up evidence builder."""
from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.revision.reviewer47 import prepare


def evidence():
    return {
        "query_case_ids": [0, 1],
        "marker_names": ["A", "B", "C", "D"],
        "mean_asinh_expression_z_thousandths": [[1200, -153, 0, 870], [-251, 2500, 9, -7]],
        "fraction_above_processed_zero": [[950, 200, 50, 600], [100, 997, 777, 200]],
        "label_vocabulary": ["L0", "L1", "Noise"],
    }


def assert_prepared_coverage(test, output):
    """Read-only validation of a completed preparation, never a scientific run."""
    output = Path(output)
    records = json.loads((output / "requests.json").read_text())
    manifest = json.loads((output / "manifest.json").read_text())
    test.assertEqual(len(records), 276)
    test.assertEqual(len({r["request_id"] for r in records}), len(records))
    test.assertEqual(manifest["request_items"], len(records))
    test.assertFalse(manifest["launch_ready"])
    test.assertEqual(manifest["paid_calls"], 0)
    conditions = {}
    for record in records:
        test.assertEqual(record["repeat"], 0)
        test.assertFalse(record["submission_allowed"])
        test.assertEqual(record["effort"], "high")
        key = (record["family"], record["method"], record["arm"])
        conditions.setdefault(key, []).append(record)
        body = json.loads((output / record["body_path"]).read_text())
        test.assertEqual(prepare.digest(body), record["body_sha256"])
        values = json.loads(body["messages"][1]["content"])
        prepare.assert_blinded(values, named=record["arm"] == "method_named")
        test.assertEqual(len(values["query_case_ids"]), record["expected_n"])
        test.assertEqual(body["reasoning"], {"effort": "high"})
    test.assertEqual(len(conditions), 69)
    expected = {(family, method, arm) for family in ("openai", "anthropic", "google", "deepseek")
                for method in prepare.METHOD_NAMES for arm in prepare.ARMS}
    expected.update(("anthropic", method, "method_named") for method in prepare.METHOD_NAMES)
    expected.add(("anthropic", "leiden", "neighborhood"))
    test.assertEqual(set(conditions), expected)
    for key, grouped in conditions.items():
        grouped.sort(key=lambda r: r["batch"])
        test.assertEqual([r["batch"] for r in grouped], [0, 1, 2, 3])
        cluster_ids = [c for r in grouped for c in r["cluster_ids"]]
        test.assertEqual(len(cluster_ids), len(set(cluster_ids)))
        test.assertEqual(sum(r["expected_n"] for r in grouped), len(cluster_ids))
        method = key[1]
        test.assertEqual(len(cluster_ids), {"leiden": 300, "flowsom": 299,
                                           "spatialsort": 229, "pixie_tiff": 300}[method])


class SelectionTests(unittest.TestCase):
    def test_tie_corrected_known_wilcoxon_and_selection_order(self):
        # Identical ranks tie: transformed mean breaks the first tie, marker
        # name breaks the second. Constant values do not become positive hits.
        x = np.array([[2., 4., 4., -2.], [2., 4., 4., -2.],
                      [0., 0., 0., -2.], [0., 0., 0., -2.]])
        labels = np.array(["a", "a", "b", "b"])
        means = np.array([x[:2].mean(0), x[2:].mean(0)])
        names, chosen, fallback, z = prepare.select_markers(x, labels, means, ["Z", "B", "A", "C"])
        self.assertEqual(names.tolist(), ["a", "b"])
        np.testing.assert_allclose(z[0], [np.sqrt(3)] * 3 + [0.], atol=1e-14)
        self.assertEqual(chosen[0], [2, 1, 0])
        self.assertFalse(fallback[0])
        self.assertTrue(fallback[1])
        self.assertEqual(chosen[1], [2])
        # A permutation of cells does not change the selected evidence.
        order = [3, 0, 2, 1]
        permuted = prepare.select_markers(x[order], labels[order], means, ["Z", "B", "A", "C"])
        self.assertEqual(permuted[1:3], (chosen, fallback))
        np.testing.assert_array_equal(permuted[3], z)

    def test_no_positive_hit_falls_back_to_one_mean_then_name(self):
        x = np.array([[2., 2., -5.], [2., 2., -5.]])
        _, chosen, fallback, z = prepare.select_markers(x, ["a", "a"], np.array([x.mean(0)]), ["B", "A", "C"])
        self.assertEqual(chosen, [[1]])
        self.assertEqual(fallback, [True])
        np.testing.assert_array_equal(z, np.zeros((1, 3)))

    def test_six_marker_cap_and_reference_labels_cannot_be_passed(self):
        markers = [f"M{j:02d}" for j in range(8)][::-1]
        x = np.vstack([np.ones((2, 8)), np.zeros((2, 8))])
        means = np.array([x[:2].mean(0), x[2:].mean(0)])
        _, chosen, _, _ = prepare.select_markers(x, ["a", "a", "b", "b"], means, markers)
        self.assertEqual([markers[j] for j in chosen[0]], sorted(markers)[:6])
        parameters = set(inspect.signature(prepare.select_markers).parameters)
        self.assertTrue(parameters.isdisjoint({"truth", "reference", "truth_label_code", "reference_labels"}))
        with self.assertRaises(TypeError):
            prepare.select_markers(x, ["a", "a", "b", "b"], means, markers,
                                   reference_labels=[0, 0, 1, 1])

    def test_bad_measurement_or_marker_join_rejected(self):
        for x, labels, means, markers in [
            ([[1., 2.]], ["a"], [[1., 2.]], ["A"]),
            ([[1.]], ["a", "b"], [[1.]], ["A"]),
            ([[float("nan")]], ["a"], [[1.]], ["A"]),
            ([[1.]], ["a"], [[1.], [2.]], ["A"]),
        ]:
            with self.subTest(x=x, labels=labels), self.assertRaises(ValueError):
                prepare.select_markers(x, labels, means, markers)


class PairedEvidenceTests(unittest.TestCase):
    def test_selected_numerical_values_are_exact_subset_of_the_original(self):
        base = evidence()
        original = deepcopy(base)
        selections = [[3, 0], [1, 2]]
        names = prepare.compact_evidence(base, selections, base["marker_names"], numerical=False)
        numerical = prepare.compact_evidence(base, selections, base["marker_names"], numerical=True)
        self.assertEqual(base, original)
        self.assertEqual(names["selected_marker_names"], [["D", "A"], ["B", "C"]])
        self.assertEqual(numerical["selected_mean_asinh_expression_z_thousandths"], [[870, 1200], [2500, 9]])
        numeric_only = numerical.pop("selected_mean_asinh_expression_z_thousandths")
        self.assertEqual(numeric_only, [[870, 1200], [2500, 9]])
        self.assertEqual(numerical, names)
        self.assertNotIn("mean_asinh_expression_z_thousandths", names)
        self.assertNotIn("fraction_above_processed_zero", names)
        with self.assertRaises(ValueError):
            prepare.compact_evidence(base, selections[:1], base["marker_names"], numerical=True)

    def test_nested_reference_and_method_fields_rejected(self):
        for forbidden in prepare.FORBIDDEN | {"clustering_method"}:
            values = evidence()
            values["nested"] = [{"payload": {forbidden: "hidden"}}]
            with self.subTest(field=forbidden), self.assertRaises(ValueError):
                prepare.assert_blinded(values)
        for method_name in prepare.METHOD_NAMES.values():
            values = evidence()
            values["description"] = f"These clusters came from {method_name}."
            with self.subTest(method=method_name), self.assertRaises(ValueError):
                prepare.assert_blinded(values)
        values = evidence()
        values["clustering_method"] = "Leiden"
        prepare.assert_blinded(values, named=True)

    def test_anonymous_ids_are_nonempty_bounded_integer_sequences(self):
        for ids in (None, [], [1, 0], [0, 0], [0, 2], ["0", "1"], [False, True], [0., 1.], list(range(76))):
            values = evidence()
            if ids is None:
                del values["query_case_ids"]
            else:
                values["query_case_ids"] = ids
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                prepare.assert_blinded(values)
        for n in (1, 75):
            values = evidence()
            values["query_case_ids"] = list(range(n))
            prepare.assert_blinded(values)


class NeighborhoodTests(unittest.TestCase):
    def test_self_exclusion_within_region_and_numeric_id_tie(self):
        keys = pd.DataFrame({"File_ID": ["A"] * 4 + ["B"] * 2,
                             "ID": ["10", "2", "30", "40", "1", "2"]})
        xy = np.array([[0., 0.], [1., 0.], [-1., 0.], [10., 0.], [0., 0.], [.01, 0.]])
        x = np.array([[10.], [20.], [30.], [40.], [900.], [800.]])
        labels = np.array([f"c{i}" for i in range(len(x))])
        names, values = prepare.neighborhood_profiles(x, keys, xy, labels, [0.], [1.], k=1)
        self.assertEqual(names.tolist(), labels.tolist())
        np.testing.assert_array_equal(values[:, 0], np.array([20, 10, 10, 20, 800, 900]) * 1000)
        # The tie at x=0 selects numeric ID 2 rather than ID 30, and points
        # in B remain in B despite closer coordinates in region A.
        order = [5, 2, 0, 4, 3, 1]
        perm_names, perm_values = prepare.neighborhood_profiles(
            x[order], keys.iloc[order].reset_index(drop=True), xy[order], labels[order], [0.], [1.], k=1)
        np.testing.assert_array_equal(perm_names, names)
        np.testing.assert_array_equal(perm_values, values)

    def test_duplicate_coordinates_exclude_self_and_keep_all_boundary_ties(self):
        keys = pd.DataFrame({"File_ID": ["A"] * 3, "ID": ["10", "2", "3"]})
        x = np.array([[10.], [2.], [3.]])
        xy = np.zeros((3, 2))
        labels = ["a", "b", "c"]
        _, values = prepare.neighborhood_profiles(x, keys, xy, labels, [0.], [1.], k=1)
        np.testing.assert_array_equal(values[:, 0], [2000, 3000, 2000])
        _, capped = prepare.neighborhood_profiles(x, keys, xy, labels, [0.], [1.], k=15)
        np.testing.assert_array_equal(capped[:, 0], [2500, 6500, 6000])
        # Cluster aggregation occurs before frozen training standardization.
        _, aggregate = prepare.neighborhood_profiles(x, keys, xy, ["a"] * 3, [.5], [2.], k=1)
        np.testing.assert_array_equal(aggregate, [[917]])

    def test_bad_coordinates_duplicate_keys_and_singleton_regions_rejected(self):
        keys = pd.DataFrame({"File_ID": ["A", "A"], "ID": ["1", "2"]})
        for bad_keys, xy in [
            (keys, np.zeros((2, 1))),
            (keys, np.array([[0., 0.], [float("nan"), 0.]])),
            (pd.concat([keys.iloc[:1], keys.iloc[:1]], ignore_index=True), np.zeros((2, 2))),
            (keys.assign(File_ID=["A", "B"]), np.zeros((2, 2))),
            (keys.iloc[:1], np.zeros((2, 2))),
        ]:
            with self.subTest(keys=bad_keys.to_dict()), self.assertRaises(ValueError):
                prepare.neighborhood_profiles(np.ones((2, 1)), bad_keys, xy, ["a", "b"], [0.], [1.])


class PreparationAdmissionTests(unittest.TestCase):
    def test_changed_grouping_repetition_effort_or_source_is_rejected_before_loading(self):
        from llm_spatial_omics_clustering.revision import annotation47_prepare as frozen

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bundle").mkdir()
            (root / "source").mkdir()
            (root / "bundle/protocol.json").write_text("{}")
            base = {"b004_bundle": "bundle", "clusters_per_request": 75, "repetitions": 1,
                    "models": {"openai": {"effort": "high"}}}
            changed = [{**base, "clusters_per_request": 74}, {**base, "repetitions": 2},
                       {**base, "models": {"openai": {"effort": "low"}}}, base]
            (root / "source/manifest.json").write_text(json.dumps({"source_h5ad_sha256": "wrong"}))
            for configuration in changed:
                config = root / "config.json"
                config.write_text(json.dumps(configuration))
                with self.subTest(config=configuration), patch.object(frozen, "load_inputs") as load:
                    with self.assertRaises(ValueError):
                        prepare.prepare_b004(root, root / "source", root / "missing.h5ad", root / "out", config)
                    load.assert_not_called()
                    self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
