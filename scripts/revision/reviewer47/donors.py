"""Read-only admission of donor results produced by the separate SpatialSort chat.

This module has no scheduler, fitting, restart, cancellation or inference path.
The producer's declared protocol is compared with an explicit approved contract;
50 completed sweeps are never relabelled as 100. Merely observing a status file
does not admit results for annotation.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence

PRODUCER_THREAD_ID = "01a1c7cb-7c45-7a63-8297-8b4b7f7c3fed"
PRODUCER_THREAD_TITLE = "Run 47-marker SpatialSort on 5/6"
HANDOFF_SCHEMA = "reviewer47.spatialsort_handoff.v1"
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_JSON_BYTES = 8 * 1024 * 1024
_DATALESS_FLAG = getattr(stat, "SF_DATALESS", 0x40000000)


class DonorAdmissionError(ValueError):
    """An input is malformed or does not satisfy its frozen contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def _safe_read(path: Path, *, limit: int | None = None,
               timeout: float = DEFAULT_TIMEOUT_SECONDS) -> bytes:
    """Read in a bounded child, refusing known macOS dataless placeholders.

    The child performs only a fixed read operation; paths are arguments, never
    shell text. A timed-out read is unavailable evidence, not an empty file.
    """
    info = path.stat()
    if getattr(info, "st_flags", 0) & _DATALESS_FLAG:
        raise DonorAdmissionError(f"Dataless file requires hydration: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise DonorAdmissionError(f"Not a regular file: {path}")
    if limit is not None and info.st_size > limit:
        raise DonorAdmissionError(f"File exceeds bounded read limit: {path}")
    program = "import pathlib,sys;sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())"
    try:
        result = subprocess.run([sys.executable, "-c", program, str(path)],
                                capture_output=True, timeout=timeout, check=True)
    except subprocess.TimeoutExpired as error:
        raise DonorAdmissionError(f"Read timed out; evidence not verified: {path}") from error
    except subprocess.CalledProcessError as error:
        raise DonorAdmissionError(f"Read failed; evidence not verified: {path}") from error
    return result.stdout


def _parse_json(data: bytes) -> dict[str, Any]:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise DonorAdmissionError(f"Duplicate JSON key: {key}")
            value[key] = item
        return value
    value = json.loads(data, object_pairs_hook=unique,
                       parse_constant=lambda value: (_ for _ in ()).throw(
                           DonorAdmissionError(f"Non-finite JSON value: {value}")))
    if not isinstance(value, dict):
        raise DonorAdmissionError("Expected a JSON object")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    return _parse_json(_safe_read(path, limit=MAX_JSON_BYTES))


def file_observation(path: str | Path, *, verify_hash: bool = False,
                     timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Inspect a producer artifact without mutating it or silently hydrating it."""
    path = Path(path)
    observation: dict[str, Any] = {"path": str(path), "exists": path.exists(),
                                   "sha256_verified": False}
    if not observation["exists"]:
        observation["issue"] = "missing"
        return observation
    info = path.stat()
    observation.update(bytes=info.st_size, mtime_ns=info.st_mtime_ns,
                       dataless=bool(getattr(info, "st_flags", 0) & _DATALESS_FLAG))
    if verify_hash:
        try:
            data = _safe_read(path, timeout=timeout)
            observation.update(sha256=hashlib.sha256(data).hexdigest(), sha256_verified=True)
        except (DonorAdmissionError, OSError) as error:
            observation["issue"] = str(error)
    return observation


def validate_markers(markers: Sequence[str], expected_markers: Sequence[str]) -> None:
    if len(expected_markers) != 47 or len(set(expected_markers)) != 47:
        raise DonorAdmissionError("The expected marker contract must contain 47 unique markers")
    if list(markers) != list(expected_markers):
        raise DonorAdmissionError("Missing, extra, duplicate or reordered markers")


def canonical_keys(keys: Iterable[Mapping[str, Any] | Sequence[Any]]) -> list[tuple[str, str]]:
    result = []
    for row in keys:
        values = (row.get("File_ID"), row.get("ID")) if isinstance(row, Mapping) else tuple(row)
        if len(values) != 2 or any(v is None or isinstance(v, bool) or str(v) == "" for v in values):
            raise DonorAdmissionError("Every cell needs a nonempty File_ID and ID")
        result.append((str(values[0]), str(values[1])))
    if len(set(result)) != len(result):
        raise DonorAdmissionError("Duplicate cell keys")
    return result


def key_sha256(keys: Iterable[Mapping[str, Any] | Sequence[Any]]) -> str:
    return hashlib.sha256(_canonical(canonical_keys(keys))).hexdigest()


def validate_measurements(keys, values, markers, expected_markers) -> dict[str, Any]:
    """Validate all admitted cells and all 47 channels; never impute or drop rows."""
    import numpy as np
    validate_markers(markers, expected_markers)
    ordered_keys = canonical_keys(keys)
    matrix = np.asarray(values)
    if matrix.shape != (len(ordered_keys), 47) or not len(ordered_keys):
        raise DonorAdmissionError("Measurement shape does not match exact cell keys and 47 markers")
    if matrix.dtype.kind not in "fiu" or not np.isfinite(matrix).all():
        raise DonorAdmissionError("All 47 measurements must be finite numeric values")
    return {"passed": True, "n_cells": len(ordered_keys), "n_markers": 47,
            "cell_key_sha256": key_sha256(ordered_keys), "all_47_values_finite": True,
            "imputation_performed": False, "rows_dropped": 0}


def _compare_protocol(observed: Mapping[str, Any], contract: Mapping[str, Any]) -> list[str]:
    problems = []
    for name, expected in (("actual_sweeps", contract["expected_sweeps"]),
                           ("dmh_iter", contract.get("dmh_iter", 5)),
                           ("beta_rounds_per_sweep", contract.get("beta_rounds_per_sweep", 5)),
                           ("n_markers", 47), ("requested_clusters", contract.get("requested_clusters", 300))):
        if type(observed.get(name)) is not int or observed.get(name) != expected:
            problems.append(f"{name}: expected {expected}, observed {observed.get(name)!r}")
    required = contract.get("required_seeds", [42, 43])
    if observed.get("sampling_seeds") != list(required):
        problems.append("sampling_seeds do not match the approved external contract")
    if contract.get("primary_seed", 42) not in required:
        problems.append("The primary seed is absent from required_seeds")
    return problems


def observe_external_campaign(root: str | Path, expected_markers: Sequence[str],
                              approved_contract: Mapping[str, Any] | None = None,
                              *, verify_hashes: bool = False) -> dict[str, Any]:
    """Produce a compact dependency observation, not a completion certificate.

    Metadata and small selection/validation files can be inspected while the
    other chat prepares or runs its job. No scheduler absence or elapsed time is
    interpreted as scientific completion.
    """
    root = Path(root)
    result: dict[str, Any] = {"schema": "reviewer47.external_dependency.v1",
        "producer_thread_id": PRODUCER_THREAD_ID, "producer_thread_title": PRODUCER_THREAD_TITLE,
        "producer_root": str(root), "read_only": True, "automatic_launch": False,
        "jobs_submitted": 0, "annotation_calls": 0, "admitted_for_annotation": False,
        "status": "waiting_protocol_confirmation" if approved_contract is None else "awaiting_completion",
        "files": {}, "donors": {}, "issues": []}
    for name in ["request.json", "donors/source_validation.json", "donors/hubmap_donor_mapping.json",
                 "runner/source_provenance.json", "staging_manifest.json", "upload_receipt.json"]:
        result["files"][name] = file_observation(root / name, verify_hash=verify_hashes)
    request = None
    try:
        request = _load_json(root / "request.json")
        result["observed_protocol"] = {k: request.get(k) for k in
            ["actual_sweeps", "dmh_iter", "beta_rounds_per_sweep", "n_markers", "sampling_seeds", "requested_clusters",
             "execution_status", "source_input_status", "authorization"]}
        if approved_contract is not None:
            result["issues"].extend(_compare_protocol(request, approved_contract))
            if result["issues"]:
                result["status"] = "protocol_mismatch"
    except (OSError, ValueError, DonorAdmissionError) as error:
        result["issues"].append(str(error))
    validation = None
    try:
        validation = _load_json(root / "donors/source_validation.json")
    except (OSError, ValueError, DonorAdmissionError) as error:
        result["issues"].append(str(error))
    for donor in ("B005", "B006"):
        path = root / "donors" / f"{donor}_selection.json"
        record = {"selection": file_observation(path, verify_hash=verify_hashes),
                  "outputs_verified": False, "status": "awaiting_completed_handoff"}
        try:
            selection = _load_json(path)
            validate_markers(selection.get("markers", []), expected_markers)
            if selection.get("donor") != donor or selection.get("reference_labels_used") is not False:
                raise DonorAdmissionError("Donor selection identity or label-blind declaration is invalid")
            record.update(expected_n_cells=selection.get("expected_n_cells"),
                          regions=selection.get("regions"), source_h5ad=selection.get("source_h5ad"),
                          source_h5ad_sha256=selection.get("source_h5ad_sha256"),
                          mapping_verified_in_source_receipt=selection.get("mapping_verified") is True,
                          marker_order_matches=True)
            if validation:
                record["source_validation_report"] = validation.get("donors", {}).get(donor)
            preparation_path = root / donor / "input_preparation_receipt.json"
            record["preparation_receipt"] = file_observation(preparation_path, verify_hash=verify_hashes)
            if record["preparation_receipt"]["exists"]:
                preparation = _load_json(preparation_path)
                record["producer_preparation_status"] = preparation.get("status")
                record["preparation_source_hash_matches_selection"] = (
                    preparation.get("source_sha256") == selection.get("source_h5ad_sha256"))
                record["source_marker_sources"] = preparation.get("marker_sources", {})
                record["fitting_representation"] = preparation.get("transform")
            record["chains"] = {}
            for seed in (42, 43):
                paths = {"submission": root / donor / "submissions" / f"seed_{seed}.json",
                         "status": root / donor / "runs" / f"seed_{seed}" / "status.json"}
                record["chains"][str(seed)] = {
                    name: file_observation(path, verify_hash=verify_hashes) for name, path in paths.items()}
        except (OSError, ValueError, DonorAdmissionError) as error:
            record["issue"] = str(error)
        result["donors"][donor] = record
    result["completion_note"] = "Requires completed handoff, all expected traces, keyed assignments, checkpoint parity and scheduler accounting; this observation never launches or modifies the producer."
    return result


def _verified_bytes(artifact: Mapping[str, Any], artifact_root: Path) -> bytes:
    if not isinstance(artifact, Mapping) or not artifact.get("path") or len(artifact.get("sha256", "")) != 64:
        raise DonorAdmissionError("An artifact needs an explicit path and SHA256")
    path = Path(artifact["path"]).resolve()
    if not path.is_relative_to(artifact_root.resolve()):
        raise DonorAdmissionError("Handoff artifact escapes the approved export root")
    data = _safe_read(path, timeout=float(artifact.get("read_timeout_seconds", 30)))
    if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        raise DonorAdmissionError(f"Artifact hash mismatch: {artifact['path']}")
    return data


def _csv_rows(data: bytes, path: str) -> list[dict[str, str]]:
    if path.endswith(".gz"):
        data = gzip.decompress(data)
    return list(csv.DictReader(io.StringIO(data.decode())))


def admit_spatialsort_handoff(receipt: Mapping[str, Any], approved_contract: Mapping[str, Any],
                             *, verify_files: bool = True) -> dict[str, Any]:
    """Admit a locally exported, hash-bound producer handoff for annotation.

    Required files: protocol, selection, inputs (NPZ y/counts), cell_keys CSV.
    Each required seed needs assignments, checkpoint, every sweep trace and a
    hash-bound scheduler-evidence JSON with matching job/state/exit information.
    Calling with verify_files=False is an explicit dry inspection, never admission.
    """
    if receipt.get("schema") != HANDOFF_SCHEMA or receipt.get("producer_thread_id") != PRODUCER_THREAD_ID:
        raise DonorAdmissionError("Unknown handoff schema or producer thread")
    if type(approved_contract.get("expected_sweeps")) is not int or approved_contract["expected_sweeps"] <= 0:
        raise DonorAdmissionError("An explicit positive approved sweep count is required")
    if not approved_contract.get("artifact_root"):
        raise DonorAdmissionError("An explicit approved handoff artifact root is required")
    donor = receipt.get("donor")
    if donor not in ("B005", "B006") or donor != approved_contract.get("donor"):
        raise DonorAdmissionError("Handoff donor differs from the approved contract")
    if not verify_files:
        return {"passed": False, "admitted_for_annotation": False, "status": "unverified_dry_inspection",
                "donor": donor, "automatic_launch": False}
    import numpy as np
    artifact_root = Path(approved_contract["artifact_root"])
    verified = lambda item: _verified_bytes(item, artifact_root)
    files = receipt.get("files", {})
    if any(name not in files for name in ("protocol", "selection", "inputs", "cell_keys")):
        raise DonorAdmissionError("Handoff lacks a required protocol, selection, input or key artifact")
    protocol = _parse_json(verified(files["protocol"]))
    problems = _compare_protocol(protocol, approved_contract)
    if problems:
        raise DonorAdmissionError("; ".join(problems))
    selection = _parse_json(verified(files["selection"]))
    validate_markers(selection.get("markers", []), approved_contract["markers"])
    validate_markers(protocol.get("marker_columns", []), approved_contract["markers"])
    if selection.get("donor") != donor or selection.get("reference_labels_used") is not False:
        raise DonorAdmissionError("Selection must bind the correct donor without reference labels")
    if protocol.get("donor") != donor or protocol.get("reference_labels_supplied_to_fit") is not False:
        raise DonorAdmissionError("Protocol must bind the correct donor without reference labels")
    if protocol.get("selection_sha256") != files["selection"]["sha256"]:
        raise DonorAdmissionError("Protocol is not bound to its verified selection")
    for name in ("selection_sha256", "source_h5ad_sha256"):
        digest = approved_contract.get(name)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise DonorAdmissionError(f"An explicit approved {name} is required")
    if files["selection"]["sha256"] != approved_contract["selection_sha256"]:
        raise DonorAdmissionError("Selection differs from its approved frozen hash")
    if selection.get("source_h5ad_sha256") != approved_contract["source_h5ad_sha256"]:
        raise DonorAdmissionError("Source H5AD differs from its approved frozen hash")
    if selection.get("mapping_verified") is not True:
        raise DonorAdmissionError("Donor selection lacks verified label-blind source mapping")
    keys = canonical_keys(_csv_rows(verified(files["cell_keys"]), files["cell_keys"]["path"]))
    if len(keys) != protocol.get("n_cells") or len(keys) != selection.get("expected_n_cells"):
        raise DonorAdmissionError("Cell counts differ between protocol, selection and keyed inputs")
    if set(k[0] for k in keys) != set(selection.get("regions", [])):
        raise DonorAdmissionError("Cell regions differ from the label-blind donor selection")
    if len(set(selection["regions"])) != len(selection["regions"]):
        raise DonorAdmissionError("Duplicate selected regions")
    with np.load(io.BytesIO(verified(files["inputs"])), allow_pickle=False) as data:
        y, counts = data["y"].copy(), data["counts"].copy()
    validate_measurements(keys, y, selection["markers"], approved_contract["markers"])
    if counts.dtype.kind not in "iu" or counts.ndim != 1 or (counts <= 0).any() or int(counts.sum()) != len(keys):
        raise DonorAdmissionError("Invalid donor region counts")
    if len(counts) != protocol.get("n_regions") or len(counts) != len(selection["regions"]):
        raise DonorAdmissionError("Region count differs from protocol")
    # These counts also bind checkpoint row boundaries to exact key order.
    runs = []
    for name, group in __import__("itertools").groupby(keys, key=lambda row: row[0]):
        runs.append(sum(1 for _ in group))
    if runs != counts.tolist():
        raise DonorAdmissionError("Region-count boundaries do not match input cell-key order")
    target = approved_contract["expected_sweeps"]
    verified_chains = {}
    for seed in approved_contract.get("required_seeds", [42, 43]):
        chain = receipt.get("chains", {}).get(str(seed), {})
        if chain.get("status") != "complete" or type(chain.get("sweeps_completed")) is not int or chain.get("sweeps_completed") != target:
            raise DonorAdmissionError(f"Seed {seed} has not completed the approved sweep count")
        if any(name not in chain for name in ("scheduler_evidence", "assignments", "checkpoint")):
            raise DonorAdmissionError(f"Seed {seed} lacks a required completion artifact")
        scheduler = _parse_json(verified(chain["scheduler_evidence"]))
        code = scheduler.get("exit_code")
        successful_exit = (type(code) is int and code == 0) or code == "0:0"
        if not str(chain.get("job_id", "")).isdigit() or scheduler.get("job_id") != chain.get("job_id") or scheduler.get("state") != "COMPLETED" or not successful_exit:
            raise DonorAdmissionError(f"Seed {seed} scheduler accounting does not verify success")
        rows = _csv_rows(verified(chain["assignments"]), chain["assignments"]["path"])
        if canonical_keys(rows) != keys:
            raise DonorAdmissionError(f"Seed {seed} assignment keys differ from exact input order")
        try:
            labels = np.array([int(row["spatialsort_cluster"]) for row in rows], dtype=np.int64)
        except (ValueError, KeyError) as error:
            raise DonorAdmissionError("Assignments need integer SpatialSort labels") from error
        if (labels < 0).any() or (labels >= protocol["requested_clusters"]).any():
            raise DonorAdmissionError("Assignment labels are out of range")
        traces = chain.get("traces", [])
        if [trace.get("sweep") for trace in traces] != list(range(1, target + 1)):
            raise DonorAdmissionError(f"Seed {seed} must preserve every expected sweep trace")
        final_trace = None
        for trace in traces:
            raw = verified(trace)
            if trace["sweep"] == target:
                final_trace = raw
        with np.load(io.BytesIO(final_trace), allow_pickle=False) as data:
            if data["labels"].dtype.kind not in "iu" or not np.array_equal(data["labels"], labels) or data["beta"].shape != (protocol["requested_clusters"], 2) or not np.isfinite(data["beta"]).all():
                raise DonorAdmissionError("Final trace does not match assignments or finite beta")
            final_beta = data["beta"].copy()
        with np.load(io.BytesIO(verified(chain["checkpoint"])), allow_pickle=False) as data:
            state = _parse_json(data["metadata"].tobytes())
            if state.get("seed") != seed or state.get("sweeps_completed") != target:
                raise DonorAdmissionError("Checkpoint seed or sweep count differs")
            if state.get("protocol_sha256") != files["protocol"]["sha256"]:
                raise DonorAdmissionError("Checkpoint is not bound to the verified protocol")
            rng = state.get("numpy_rng")
            if not isinstance(rng, dict) or set(rng) != {"engine", "keys", "position", "has_gauss", "cached_gaussian"}:
                raise DonorAdmissionError("Checkpoint lacks complete RNG metadata")
            if (rng["engine"] != "MT19937" or not isinstance(rng["keys"], list)
                    or len(rng["keys"]) != 624
                    or any(type(v) is not int or not 0 <= v <= 2**32 - 1 for v in rng["keys"])
                    or type(rng["position"]) is not int or not 0 <= rng["position"] <= 624
                    or type(rng["has_gauss"]) is not int or rng["has_gauss"] not in (0, 1)
                    or type(rng["cached_gaussian"]) not in (int, float)
                    or not np.isfinite(rng["cached_gaussian"])):
                raise DonorAdmissionError("Checkpoint RNG state is invalid")
            x = data["x"]
            if x.dtype.kind not in "iu" or x.shape != (len(counts), int(counts.max())):
                raise DonorAdmissionError("Checkpoint label matrix has invalid shape or type")
            flat = np.concatenate([x[i, :n] for i, n in enumerate(counts)])
            if not np.array_equal(flat, labels) or not np.array_equal(data["beta"], final_beta):
                raise DonorAdmissionError("Checkpoint state differs from final trace")
            for name in ("n_cache", "ybar_cache", "sumsqr_cache"):
                expected_shape = (protocol["requested_clusters"],) if name == "n_cache" else (protocol["requested_clusters"], 47)
                if data[name].shape != expected_shape or not np.isfinite(data[name]).all():
                    raise DonorAdmissionError("Checkpoint contains non-finite caches")
            if not np.array_equal(data["n_cache"], np.bincount(labels, minlength=protocol["requested_clusters"])):
                raise DonorAdmissionError("Checkpoint class counts differ from assignments")
        verified_chains[str(seed)] = {"sweeps": target, "rows": len(labels),
                                    "occupied_clusters": len(np.unique(labels)), "verified": True}
    return {"passed": True, "admitted_for_annotation": True, "status": "verified_complete",
            "donor": donor, "n_cells": len(keys), "n_markers": 47,
            "primary_seed": approved_contract.get("primary_seed", 42), "chains": verified_chains,
            "cell_key_sha256": key_sha256(keys), "receipt_sha256": hashlib.sha256(_canonical(receipt)).hexdigest(),
            "automatic_launch": False, "jobs_submitted": 0, "annotation_calls": 0,
            "scope": "Keyed producer output admission; not convergence, biological correctness or mask-boundary validation"}


def common_verified_population(method_keys: Mapping[str, Iterable], eligible_keys: Iterable) -> dict[str, Any]:
    """Report exact comparable cells without treating partial matching as full validation."""
    eligible = set(canonical_keys(eligible_keys))
    if not eligible or not method_keys:
        raise DonorAdmissionError("A common-population audit needs eligible cells and methods")
    methods = {method: set(canonical_keys(keys)) for method, keys in method_keys.items()}
    common = set.intersection(eligible, *methods.values())
    ordered = sorted(common)
    return {"eligible_cells": len(eligible), "common_cells": len(common), "common_keys": ordered,
            "common_key_sha256": key_sha256(ordered), "coverage": len(common) / len(eligible),
            "method_cells": {name: len(keys & eligible) for name, keys in methods.items()},
            "scope": "Verified cell correspondence; does not establish segmentation-boundary accuracy"}


def project_native_predictions(labels: Sequence[str], mapping: Mapping[str, str | None], *,
                               native_vocabulary: Sequence[str], target_vocabulary: Sequence[str],
                               cohort_key_sha256: str, approved_cohort_key_sha256: str) -> list[str | None]:
    """Apply an explicitly cohort-bound projection, preserving native labels separately.

    None is an explicitly unresolved projection, never the valid Noise class.
    The old atlas projection cannot be silently inherited by a new H5AD cohort.
    """
    if len(native_vocabulary) != 28 or len(set(native_vocabulary)) != 28:
        raise DonorAdmissionError("The native vocabulary must contain 28 unique labels")
    if cohort_key_sha256 != approved_cohort_key_sha256 or not cohort_key_sha256:
        raise DonorAdmissionError("Projection is not approved for these exact donor cells")
    if set(mapping) != set(native_vocabulary):
        raise DonorAdmissionError("Projection must explicitly map every original label")
    target = set(target_vocabulary)
    if len(target_vocabulary) != 23 or len(target) != 23 or any(v is not None and v not in target for v in mapping.values()):
        raise DonorAdmissionError("Projection must use the approved 23-class vocabulary")
    if any(label not in mapping for label in labels):
        raise DonorAdmissionError("Prediction outside native label vocabulary")
    return [mapping[label] for label in labels]
