"""Reproducible Figure 3 LLM-annotation benchmark.

Figure 3 deliberately imports the selected clustering assignments from the
Figure 2 contract. In particular, its PIXIE input is the image-native,
TIFF-derived 50-cell-cluster result rather than the historical table-only
MiniSom adaptation.

Every panel that depends on an LLM calls :func:`require_api_keys` before
loading data, creating marker summaries, reading cached model responses, or
writing a panel. This makes the placeholder-key notebook safe by construction:
Panel A can render locally, while Panels B--L cannot render until the relevant
provider keys are inserted.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from itertools import permutations
import json
from pathlib import Path
import re
import shutil
import time
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

import numpy as np
import pandas as pd
import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PANEL_KEYS = tuple(f"panel_{letter}" for letter in "abcdefghijkl")


class Figure03ValidationError(ValueError):
    """Raised when a Figure 3 input violates its declared contract."""


class Figure03CredentialError(RuntimeError):
    """Raised when an LLM-dependent panel still has placeholder credentials."""


class Figure03APIError(RuntimeError):
    """Raised when a provider response cannot be obtained or validated."""


@dataclass(frozen=True)
class Figure03Inputs:
    """Validated B004 marker inputs and separate non-Noise evaluation cells."""

    marker_cells: pd.DataFrame
    cells: pd.DataFrame
    expression: np.ndarray
    expression_sha256: str
    marker_names: tuple[str, ...]
    cluster_counts: dict[str, int]
    source_cell_count: int
    evaluation_cell_count: int
    figure_02_config_path: Path
    data_root: Path


@dataclass(frozen=True)
class AnnotationResult:
    """One validated cluster-label mapping and its local response-cache path."""

    provider: str
    condition: str
    method: str
    marker_state: str
    requested_model_id: str
    returned_model_id: str
    annotations: dict[str, str]
    cache_path: Path
    cache_hit: bool
    cache_contract_sha256: str
    annotation_sha256: str
    prompt_sha256: str
    marker_summary_sha256: str


def load_figure_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load and minimally validate the tracked Figure 3 configuration."""
    path = Path(config_path) if config_path else REPOSITORY_ROOT / "configs/figure_03.yaml"
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or int(config.get("figure", -1)) != 3:
        raise Figure03ValidationError(f"Invalid Figure 3 configuration: {path}")
    panels = config.get("panels")
    if not isinstance(panels, dict) or not set(PANEL_KEYS).issubset(panels):
        raise Figure03ValidationError(f"Figure 3 configuration does not define Panels A--L: {path}")
    return config


def _resolve_repository_root(repository_root: str | Path | None) -> Path:
    return Path(repository_root).expanduser().resolve() if repository_root else REPOSITORY_ROOT


def _resolve_config_path(
    repository_root: Path,
    config_path: str | Path | None,
) -> Path:
    if config_path is None:
        return repository_root / "configs/figure_03.yaml"
    path = Path(config_path).expanduser()
    return (repository_root / path).resolve() if not path.is_absolute() else path.resolve()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(payload: str) -> str:
    return _sha256_bytes(payload.encode("utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataframe_fingerprint(frame: pd.DataFrame) -> str:
    values = pd.util.hash_pandas_object(frame, index=False).to_numpy(dtype=np.uint64)
    return _sha256_bytes(values.tobytes())


def _json_dump(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _is_placeholder_key(value: object) -> bool:
    text = "" if value is None else str(value).strip()
    if not text:
        return True
    upper = text.upper()
    placeholder_fragments = (
        "PASTE_",
        "PLACEHOLDER",
        "YOUR_API_KEY",
        "INSERT_API_KEY",
        "REPLACE_ME",
        "<API",
    )
    return any(fragment in upper for fragment in placeholder_fragments)


def require_api_keys(
    api_keys: Mapping[str, str],
    required_providers: Sequence[str],
    config: Mapping[str, Any] | None = None,
) -> None:
    """Refuse an LLM panel before any work if a required key is a placeholder."""
    config = dict(config or load_figure_config())
    missing: list[str] = []
    for provider in required_providers:
        if provider not in config["providers"]:
            raise Figure03ValidationError(f"Unknown provider in panel contract: {provider!r}")
        if _is_placeholder_key(api_keys.get(provider)):
            env_name = str(config["providers"][provider]["api_key_name"])
            missing.append(f"{provider} ({env_name})")
    if missing:
        joined = ", ".join(missing)
        raise Figure03CredentialError(
            "Figure 3 LLM execution is intentionally disabled. Replace the placeholder "
            f"API key(s) for: {joined}. No panel or cache file was generated."
        )


def _load_figure03_inputs_cached(
    repository_root_string: str,
    config_path_string: str,
) -> Figure03Inputs:
    repository_root = Path(repository_root_string)
    config_path = Path(config_path_string)
    config = load_figure_config(config_path)

    dependency = config["figure_02_dependency"]
    figure_02_config_path = (repository_root / dependency["config_path"]).resolve()

    from llm_spatial_omics_clustering.figure_02 import (
        load_b004_h5ad,
        load_figure_config as load_figure_02_config,
        load_method_assignments,
        resolve_data_root,
    )

    figure_02_config = load_figure_02_config(figure_02_config_path)
    data_root = resolve_data_root(figure_02_config)
    figure_02_data = load_b004_h5ad(figure_02_config, data_root=data_root)
    assignments = load_method_assignments(
        figure_02_data,
        figure_02_config,
        data_root=data_root,
    )

    expected_methods = dependency["expected_methods"]
    if set(assignments) != set(expected_methods):
        raise Figure03ValidationError(
            "Figure 2 assignment methods differ from the Figure 3 contract: "
            f"observed={sorted(assignments)}, expected={sorted(expected_methods)}"
        )

    truth_column = str(config["evaluation"]["truth_column"])
    required_cell_columns = {"File_ID", "ID", truth_column, "x", "y"}
    if missing := required_cell_columns.difference(figure_02_data.cells.columns):
        raise Figure03ValidationError(f"Figure 2 B004 cells are missing: {sorted(missing)}")

    source_cells = figure_02_data.cells.copy()
    source_cell_count = int(len(source_cells))
    expected_source = int(config["evaluation"]["expected_source_cells"])
    if source_cell_count != expected_source:
        raise Figure03ValidationError(
            f"Figure 3 received {source_cell_count:,} Figure 2 cells; expected {expected_source:,}"
        )

    # Marker summaries must use every B004 cell. Reference labels are used only
    # later to form the non-Noise evaluation table, never to filter or rank the
    # marker inputs supplied to an LLM.
    source_cells = source_cells.reset_index(drop=True)
    marker_cells = source_cells.loc[
        :,
        ["File_ID", "ID", truth_column, "x", "y"],
    ].copy()
    marker_cells = marker_cells.rename(columns={truth_column: "truth_raw"})
    source_keys = marker_cells[["File_ID", "ID"]].copy()
    cluster_counts: dict[str, int] = {}
    for method, method_contract in expected_methods.items():
        table = assignments[method].loc[:, ["File_ID", "ID", "cluster"]].copy()
        column = f"cluster_{method}"
        table = table.rename(columns={"cluster": column})
        marker_cells = marker_cells.merge(
            table,
            on=["File_ID", "ID"],
            how="left",
            validate="one_to_one",
            sort=False,
        )
        if marker_cells[column].isna().any():
            raise Figure03ValidationError(f"Figure 3 has missing {method} assignments")
        if not marker_cells[["File_ID", "ID"]].equals(source_keys):
            raise Figure03ValidationError(
                f"Joining {method} assignments changed the H5AD cell row order"
            )
        marker_cells[column] = pd.to_numeric(
            marker_cells[column],
            errors="raise",
        ).astype(np.int64)
        observed = int(marker_cells[column].nunique())
        expected = int(method_contract["expected_clusters"])
        if observed != expected:
            raise Figure03ValidationError(
                f"Figure 3 {method} has {observed} clusters; expected {expected}"
            )
        cluster_counts[method] = observed

    # Reuse the exact harmonization map already used for Figure 2 evaluation.
    harmonization = dict(figure_02_config["panel_e"]["evaluation"]["harmonization_map"])
    excluded = set(str(label) for label in config["evaluation"]["excluded_labels"])
    marker_cells["truth_raw"] = marker_cells["truth_raw"].astype(str)
    marker_cells["truth"] = marker_cells["truth_raw"].replace(harmonization)
    keep_mask = ~marker_cells["truth_raw"].isin(excluded)
    cells = marker_cells.loc[keep_mask].copy()
    cells = cells.reset_index(drop=True)

    expected_evaluation = int(config["evaluation"]["expected_evaluation_cells"])
    if len(cells) != expected_evaluation:
        raise Figure03ValidationError(
            f"Figure 3 retained {len(cells):,} non-Noise cells; expected {expected_evaluation:,}"
        )
    observed_labels = set(cells["truth"].unique())
    allowed_labels = set(str(label) for label in config["evaluation"]["allowed_labels"])
    if observed_labels != allowed_labels:
        raise Figure03ValidationError(
            "Figure 3 harmonized truth differs from its allowed vocabulary: "
            f"missing={sorted(allowed_labels - observed_labels)}, "
            f"unexpected={sorted(observed_labels - allowed_labels)}"
        )

    # Figure 2 Panel I freezes the 45 H5AD-X protein markers. Select them by
    # name from Figure 2's 48-feature matrix so the three obs-only features
    # (CD123, Hoechst1, CDX2) cannot leak into LLM marker summaries.
    marker_names = tuple(str(name) for name in figure_02_config["panel_i"]["marker_order"])
    feature_names = tuple(str(name) for name in figure_02_data.marker_names)
    if not set(marker_names).issubset(feature_names):
        missing = sorted(set(marker_names) - set(feature_names))
        raise Figure03ValidationError(f"Figure 2 features lack H5AD-X markers: {missing}")
    marker_indices = [feature_names.index(name) for name in marker_names]
    expression = np.asarray(
        figure_02_data.features[:, marker_indices],
        dtype=np.float32,
    )
    if expression.shape != (expected_source, len(marker_names)):
        raise Figure03ValidationError(
            f"Figure 3 marker matrix has shape {expression.shape}; "
            f"expected {(expected_source, len(marker_names))}"
        )
    if not np.isfinite(expression).all():
        raise Figure03ValidationError("Figure 3 marker matrix contains non-finite values")

    return Figure03Inputs(
        marker_cells=marker_cells,
        cells=cells,
        expression=expression,
        expression_sha256=_sha256_bytes(expression.tobytes()),
        marker_names=marker_names,
        cluster_counts=cluster_counts,
        source_cell_count=source_cell_count,
        evaluation_cell_count=int(len(cells)),
        figure_02_config_path=figure_02_config_path,
        data_root=Path(data_root),
    )


def load_figure03_inputs(
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> Figure03Inputs:
    """Load Figure 2 clusters and H5AD marker inputs under the Figure 3 contract."""
    root = _resolve_repository_root(repository_root)
    path = _resolve_config_path(root, config_path)
    return _load_figure03_inputs_cached(str(root), str(path))


def _marker_parameters(
    config: Mapping[str, Any],
    method: str,
    marker_state: str,
) -> dict[str, float | int]:
    summaries = config["marker_summaries"]
    if marker_state == "default":
        source = summaries["default"]
    elif marker_state == "optimized":
        source = summaries["optimized"][method]
    else:
        raise Figure03ValidationError(f"Unknown marker-summary state: {marker_state!r}")
    return {
        "expression_threshold": float(source["expression_threshold"]),
        "fraction_threshold": float(source["fraction_threshold"]),
        "mean_expression_threshold": float(source["mean_expression_threshold"]),
        "maximum_markers": int(source["maximum_markers"]),
        "fallback_minimum_markers": int(source["fallback_minimum_markers"]),
    }


def summarize_cluster_markers(
    inputs: Figure03Inputs,
    method: str,
    parameters: Mapping[str, float | int],
) -> dict[str, list[str]]:
    """Create ranked marker lists using the attached Methods' strict thresholds."""
    cluster_column = f"cluster_{method}"
    if cluster_column not in inputs.marker_cells:
        raise Figure03ValidationError(f"Unknown Figure 2 clustering method: {method!r}")

    clusters = inputs.marker_cells[cluster_column].to_numpy(dtype=np.int64)
    marker_names = list(inputs.marker_names)
    expression_frame = pd.DataFrame(inputs.expression, columns=marker_names)
    expression_frame.insert(0, "_cluster", clusters)

    means = expression_frame.groupby("_cluster", sort=True)[marker_names].mean()
    positive = pd.DataFrame(
        inputs.expression > float(parameters["expression_threshold"]),
        columns=marker_names,
    )
    positive.insert(0, "_cluster", clusters)
    fractions = positive.groupby("_cluster", sort=True)[marker_names].mean()

    summaries: dict[str, list[str]] = {}
    max_markers = int(parameters["maximum_markers"])
    fallback_minimum = int(parameters["fallback_minimum_markers"])
    fraction_threshold = float(parameters["fraction_threshold"])
    mean_threshold = float(parameters["mean_expression_threshold"])
    for cluster in means.index:
        cluster_means = means.loc[cluster]
        retained_mask = (
            fractions.loc[cluster].gt(fraction_threshold)
            & cluster_means.gt(mean_threshold)
        )
        retained = cluster_means.loc[retained_mask].sort_values(
            ascending=False,
            kind="mergesort",
        )
        if retained.empty:
            selected = cluster_means.sort_values(
                ascending=False,
                kind="mergesort",
            ).head(fallback_minimum)
        else:
            # Historical behavior does not pad a nonempty short list.
            selected = retained.head(max_markers)
        summaries[str(int(cluster))] = [str(marker) for marker in selected.index]

    expected_clusters = int(inputs.cluster_counts[method])
    if len(summaries) != expected_clusters:
        raise Figure03ValidationError(
            f"{method} marker summaries cover {len(summaries)} clusters; "
            f"expected {expected_clusters}"
        )
    return summaries


def _marker_summary_cache(
    inputs: Figure03Inputs,
    config: Mapping[str, Any],
    repository_root: Path,
    method: str,
    marker_state: str,
) -> tuple[dict[str, list[str]], Path, str]:
    parameters = _marker_parameters(config, method, marker_state)
    cache_directory = repository_root / config["prompt"]["cache_directory"]
    path = cache_directory / "marker_summaries" / f"{method}_{marker_state}.json"
    assignment_hash = _dataframe_fingerprint(
        inputs.marker_cells[["File_ID", "ID", f"cluster_{method}"]]
    )
    contract = {
        "method": method,
        "marker_state": marker_state,
        "parameters": parameters,
        "assignment_sha256": assignment_hash,
        "expression_sha256": inputs.expression_sha256,
        "marker_names": list(inputs.marker_names),
        "marker_summary_cells": inputs.source_cell_count,
    }
    contract_hash = _sha256_text(json.dumps(contract, sort_keys=True))

    if path.is_file():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("contract_sha256") == contract_hash:
            summaries = {
                str(key): [str(marker) for marker in value]
                for key, value in cached["markers"].items()
            }
            summary_hash = _sha256_text(json.dumps(summaries, sort_keys=True))
            return summaries, path, summary_hash

    summaries = summarize_cluster_markers(inputs, method, parameters)
    summary_hash = _sha256_text(json.dumps(summaries, sort_keys=True))
    _json_dump(
        path,
        {
            "contract_sha256": contract_hash,
            "summary_sha256": summary_hash,
            "contract": contract,
            "markers": summaries,
        },
    )
    return summaries, path, summary_hash


def build_annotation_prompt(
    repository_root: Path,
    config: Mapping[str, Any],
    method: str,
    marker_summaries: Mapping[str, Sequence[str]],
) -> str:
    """Fill the version-controlled cluster-annotation prompt template."""
    template_path = repository_root / config["prompt"]["template_path"]
    template = template_path.read_text(encoding="utf-8")
    method_label = str(
        config["figure_02_dependency"]["expected_methods"][method]["label"]
    )
    cluster_payload = [
        {
            "cluster_id": str(cluster_id),
            "markers": [str(marker) for marker in markers],
            "clustering_method": method_label,
        }
        for cluster_id, markers in sorted(
            marker_summaries.items(),
            key=lambda item: int(item[0]),
        )
    ]
    return template.format(
        allowed_labels_json=json.dumps(config["evaluation"]["allowed_labels"]),
        method_label=method_label,
        cluster_payload_json=json.dumps(cluster_payload, separators=(",", ":")),
    )


def _post_json(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout_seconds: float,
    *,
    max_attempts: int = 4,
) -> dict[str, Any]:
    """POST JSON with bounded retries for transient transport/server failures."""
    if max_attempts < 1:
        raise Figure03ValidationError("max_attempts must be at least 1")
    retryable_statuses = {429, 500, 502, 503, 504}
    body = ""
    for attempt in range(max_attempts):
        request = urllib_request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **dict(headers)},
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
            break
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code not in retryable_statuses or attempt == max_attempts - 1:
                raise Figure03APIError(
                    f"Provider request failed with HTTP {exc.code}: {detail[:1000]}"
                ) from exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = float(retry_after) if retry_after is not None else 2**attempt
            except ValueError:
                delay = float(2**attempt)
            time.sleep(min(max(delay, 0.0), 30.0))
        except urllib_error.URLError as exc:
            if attempt == max_attempts - 1:
                raise Figure03APIError(f"Provider request failed: {exc}") from exc
            time.sleep(float(2**attempt))
    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise Figure03APIError("Provider returned a non-JSON HTTP response") from exc
    if not isinstance(result, dict):
        raise Figure03APIError("Provider returned an unexpected top-level response")
    return result


def _extract_openai_text(response: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(str(content["text"]))
    if not parts:
        raise Figure03APIError("OpenAI response contained no output_text block")
    return "\n".join(parts)


def _extract_anthropic_text(response: Mapping[str, Any]) -> str:
    parts = [
        str(block["text"])
        for block in response.get("content", [])
        if block.get("type") == "text" and block.get("text")
    ]
    if not parts:
        raise Figure03APIError("Anthropic response contained no text block")
    return "\n".join(parts)


def _extract_gemini_text(response: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for candidate in response.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if part.get("text"):
                parts.append(str(part["text"]))
    if not parts:
        raise Figure03APIError("Gemini response contained no candidate text")
    return "\n".join(parts)


def _extract_deepseek_text(response: Mapping[str, Any]) -> str:
    try:
        text = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise Figure03APIError("DeepSeek response contained no assistant content") from exc
    if not text:
        raise Figure03APIError("DeepSeek response assistant content was empty")
    return str(text)


def _returned_model_id(provider: str, response: Mapping[str, Any]) -> str:
    """Extract the model/version reported by the provider response."""
    field = "modelVersion" if provider == "gemini" else "model"
    value = response.get(field)
    if value is None or not str(value).strip():
        raise Figure03APIError(
            f"{provider} response did not report its served model in {field!r}"
        )
    return str(value)


def _invoke_provider(
    provider: str,
    condition: str,
    prompt: str,
    api_key: str,
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], str, str]:
    """Invoke one configured provider and return response, text, and served model."""
    provider_config = config["providers"][provider]
    condition_config = provider_config["conditions"][condition]
    model_id = str(condition_config["model_id"])
    temperature = float(config["prompt"]["temperature"])
    max_output_tokens = int(config["prompt"]["max_output_tokens"])
    timeout = float(config["prompt"]["request_timeout_seconds"])

    if provider == "openai":
        payload = {
            "model": model_id,
            "input": prompt,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "reasoning": {"effort": str(condition_config["reasoning_effort"])},
            "text": {"format": {"type": "json_object"}},
            "store": False,
        }
        response = _post_json(
            str(provider_config["endpoint"]),
            payload,
            {"Authorization": f"Bearer {api_key}"},
            timeout,
        )
        return response, _extract_openai_text(response), _returned_model_id(
            provider,
            response,
        )

    if provider == "anthropic":
        payload: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"effort": str(condition_config["effort"])},
        }
        if condition_config["thinking_mode"] == "adaptive":
            payload["thinking"] = {"type": "adaptive"}
        response = _post_json(
            str(provider_config["endpoint"]),
            payload,
            {
                "x-api-key": api_key,
                "anthropic-version": str(provider_config["anthropic_version"]),
            },
            timeout,
        )
        return response, _extract_anthropic_text(response), _returned_model_id(
            provider,
            response,
        )

    if provider == "gemini":
        url = str(provider_config["endpoint_template"]).format(model=model_id)
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
                "thinkingConfig": {
                    "thinkingLevel": str(condition_config["thinking_level"])
                },
            },
        }
        response = _post_json(url, payload, {"x-goog-api-key": api_key}, timeout)
        return response, _extract_gemini_text(response), _returned_model_id(
            provider,
            response,
        )

    if provider == "deepseek":
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        if bool(condition_config.get("temperature_supported", True)):
            payload["temperature"] = temperature
        if condition_config.get("thinking_type") is not None:
            payload["thinking"] = {"type": str(condition_config["thinking_type"])}
        if condition_config.get("reasoning_effort") is not None:
            payload["reasoning_effort"] = str(condition_config["reasoning_effort"])
        response = _post_json(
            str(provider_config["endpoint"]),
            payload,
            {"Authorization": f"Bearer {api_key}"},
            timeout,
        )
        return response, _extract_deepseek_text(response), _returned_model_id(
            provider,
            response,
        )

    raise Figure03ValidationError(f"No provider adapter is configured for {provider!r}")


def _parse_annotation_object(
    text: str,
    expected_clusters: Sequence[str],
    allowed_labels: Sequence[str],
) -> dict[str, str]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        first = cleaned.find("{")
        last = cleaned.rfind("}")
        if first < 0 or last <= first:
            raise Figure03APIError("Model output did not contain a JSON object")
        try:
            payload = json.loads(cleaned[first : last + 1])
        except json.JSONDecodeError as exc:
            raise Figure03APIError("Model output contained invalid JSON") from exc
    if not isinstance(payload, dict):
        raise Figure03APIError("Model output must be a JSON object")

    annotations = {str(key): str(value) for key, value in payload.items()}
    expected = set(str(cluster) for cluster in expected_clusters)
    observed = set(annotations)
    if observed != expected:
        raise Figure03APIError(
            "Model output cluster keys differ from the prompt: "
            f"missing={sorted(expected - observed)}, unexpected={sorted(observed - expected)}"
        )
    allowed = set(str(label) for label in allowed_labels)
    invalid = {cluster: label for cluster, label in annotations.items() if label not in allowed}
    if invalid:
        preview = dict(list(invalid.items())[:10])
        raise Figure03APIError(f"Model returned labels outside the allowed vocabulary: {preview}")
    return dict(sorted(annotations.items(), key=lambda item: int(item[0])))


def _strip_reasoning_fields(value: Any) -> Any:
    """Remove provider reasoning payloads while retaining response provenance."""
    dropped = object()
    sensitive_keys = {
        "encryptedcontent",
        "reasoning",
        "reasoningcontent",
        "reasoningdetails",
        "redactedthinking",
        "signature",
        "thinking",
        "thoughtsignature",
    }
    sensitive_types = {"reasoning", "thinking", "redacted_thinking"}

    def clean(item: Any) -> Any:
        if isinstance(item, dict):
            item_type = str(item.get("type", "")).lower()
            if item_type in sensitive_types or item.get("thought") is True:
                return dropped
            cleaned: dict[str, Any] = {}
            for key, child in item.items():
                normalized = re.sub(r"[^a-z]", "", str(key).lower())
                if normalized in sensitive_keys or str(key).lower() == "thought":
                    continue
                cleaned_child = clean(child)
                if cleaned_child is not dropped:
                    cleaned[str(key)] = cleaned_child
            return cleaned
        if isinstance(item, list):
            cleaned_items = [clean(child) for child in item]
            return [child for child in cleaned_items if child is not dropped]
        return item

    cleaned_value = clean(value)
    return {} if cleaned_value is dropped else cleaned_value


def _provider_request_contract(
    provider: str,
    condition: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Return every configured setting that can change a provider request."""
    provider_config = config["providers"][provider]
    return {
        "endpoint": provider_config.get("endpoint"),
        "endpoint_template": provider_config.get("endpoint_template"),
        "anthropic_version": provider_config.get("anthropic_version"),
        "condition": dict(provider_config["conditions"][condition]),
        "temperature": float(config["prompt"]["temperature"]),
        "max_output_tokens": int(config["prompt"]["max_output_tokens"]),
        "request_timeout_seconds": float(config["prompt"]["request_timeout_seconds"]),
    }


def _archive_existing_cache(cache_path: Path) -> Path | None:
    """Preserve the previous response before replacing a cache entry."""
    if not cache_path.is_file():
        return None
    history_directory = cache_path.parent / "history"
    history_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    digest = _sha256_file(cache_path)[:16]
    archive_path = history_directory / f"{cache_path.stem}_{timestamp}_{digest}.json"
    shutil.copy2(cache_path, archive_path)
    return archive_path


def _require_provider_generation_available(
    provider: str,
    config: Mapping[str, Any],
) -> None:
    """Block a fresh call when the historical provider/model is unavailable."""
    provider_config = config["providers"][provider]
    status = str(provider_config.get("generation_status", "available"))
    if status == "available":
        return
    retired_on = provider_config.get("retired_on")
    suffix = f" on {retired_on}" if retired_on else ""
    raise Figure03ValidationError(
        f"Fresh {provider} generation is disabled because the configured historical "
        f"model contract is {status}{suffix}. Supply a contract-matched historical "
        "cache, or make an explicit author-approved model migration; the notebook "
        "will not silently substitute a newer model."
    )


def ensure_annotation(
    inputs: Figure03Inputs,
    config: Mapping[str, Any],
    repository_root: Path,
    api_keys: Mapping[str, str],
    *,
    provider: str,
    condition: str,
    method: str,
    marker_state: str = "optimized",
    force_refresh: bool = False,
) -> AnnotationResult:
    """Load or create one validated annotation mapping after credential gating."""
    require_api_keys(api_keys, [provider], config)
    marker_summaries, marker_path, marker_hash = _marker_summary_cache(
        inputs,
        config,
        repository_root,
        method,
        marker_state,
    )
    prompt = build_annotation_prompt(repository_root, config, method, marker_summaries)
    prompt_hash = _sha256_text(prompt)
    condition_config = config["providers"][provider]["conditions"][condition]
    requested_model_id = str(condition_config["model_id"])
    cache_root = repository_root / config["prompt"]["cache_directory"]
    cache_path = (
        cache_root
        / "llm_annotations"
        / f"{provider}_{condition}_{method}_{marker_state}.json"
    )
    cache_contract = {
        "provider": provider,
        "condition": condition,
        "method": method,
        "marker_state": marker_state,
        "requested_model_id": requested_model_id,
        "provider_request_contract": _provider_request_contract(
            provider,
            condition,
            config,
        ),
        "prompt_sha256": prompt_hash,
        "marker_summary_sha256": marker_hash,
        "allowed_labels": list(config["evaluation"]["allowed_labels"]),
    }
    cache_contract_hash = _sha256_text(json.dumps(cache_contract, sort_keys=True))

    if cache_path.is_file() and not force_refresh:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("cache_contract_sha256") == cache_contract_hash:
            annotations = _parse_annotation_object(
                json.dumps(cached["annotations"]),
                marker_summaries.keys(),
                config["evaluation"]["allowed_labels"],
            )
            return AnnotationResult(
                provider=provider,
                condition=condition,
                method=method,
                marker_state=marker_state,
                requested_model_id=requested_model_id,
                returned_model_id=str(cached["returned_model_id"]),
                annotations=annotations,
                cache_path=cache_path,
                cache_hit=True,
                cache_contract_sha256=cache_contract_hash,
                annotation_sha256=_sha256_text(
                    json.dumps(annotations, sort_keys=True)
                ),
                prompt_sha256=prompt_hash,
                marker_summary_sha256=marker_hash,
            )

    # A retired historical model may still be reproduced from an exact cache,
    # but it must never be replaced silently by a currently served model.
    _require_provider_generation_available(provider, config)
    response, text, returned_model_id = _invoke_provider(
        provider,
        condition,
        prompt,
        str(api_keys[provider]),
        config,
    )
    annotations = _parse_annotation_object(
        text,
        marker_summaries.keys(),
        config["evaluation"]["allowed_labels"],
    )
    annotation_hash = _sha256_text(json.dumps(annotations, sort_keys=True))
    archived_cache = _archive_existing_cache(cache_path)
    _json_dump(
        cache_path,
        {
            "cache_contract_sha256": cache_contract_hash,
            "cache_contract": cache_contract,
            "requested_model_id": requested_model_id,
            "returned_model_id": returned_model_id,
            "marker_summary_path": str(marker_path.relative_to(repository_root)),
            "annotation_sha256": annotation_hash,
            "annotations": annotations,
            "provider_response": _strip_reasoning_fields(response),
            "replaced_cache_archive": (
                str(archived_cache.relative_to(repository_root))
                if archived_cache is not None
                else None
            ),
        },
    )
    return AnnotationResult(
        provider=provider,
        condition=condition,
        method=method,
        marker_state=marker_state,
        requested_model_id=requested_model_id,
        returned_model_id=returned_model_id,
        annotations=annotations,
        cache_path=cache_path,
        cache_hit=False,
        cache_contract_sha256=cache_contract_hash,
        annotation_sha256=annotation_hash,
        prompt_sha256=prompt_hash,
        marker_summary_sha256=marker_hash,
    )


def ensure_annotations(
    inputs: Figure03Inputs,
    config: Mapping[str, Any],
    repository_root: Path,
    api_keys: Mapping[str, str],
    *,
    providers: Sequence[str],
    conditions: Sequence[str],
    methods: Sequence[str],
    marker_states: Sequence[str] = ("optimized",),
    force_refresh: bool = False,
) -> dict[tuple[str, str, str, str], AnnotationResult]:
    """Load or call the complete requested provider-condition-method grid."""
    require_api_keys(api_keys, providers, config)
    results: dict[tuple[str, str, str, str], AnnotationResult] = {}
    requested_grid = [
        (provider, condition, method, marker_state)
        for marker_state in marker_states
        for condition in conditions
        for provider in providers
        for method in methods
    ]
    # Check every retired-provider cache before making any paid request to an
    # active provider. If a historical cache is absent, the grid fails locally
    # without incurring partial-run API charges.
    requested_grid.sort(
        key=lambda item: (
            config["providers"][item[0]].get("generation_status", "available")
            == "available"
        )
    )
    for provider, condition, method, marker_state in requested_grid:
        key = (provider, condition, method, marker_state)
        results[key] = ensure_annotation(
            inputs,
            config,
            repository_root,
            api_keys,
            provider=provider,
            condition=condition,
            method=method,
            marker_state=marker_state,
            force_refresh=force_refresh,
        )
    return results


def _annotation_series(
    cells: pd.DataFrame,
    method: str,
    annotations: Mapping[str, str],
) -> pd.Series:
    cluster_column = f"cluster_{method}"
    mapping = {int(cluster): str(label) for cluster, label in annotations.items()}
    predicted = cells[cluster_column].map(mapping)
    if predicted.isna().any():
        missing = sorted(cells.loc[predicted.isna(), cluster_column].unique().tolist())
        raise Figure03ValidationError(
            f"{method} annotation mapping misses cluster IDs: {missing[:20]}"
        )
    return predicted.astype(str)


def _majority_reference_series(cells: pd.DataFrame, method: str) -> pd.Series:
    cluster_column = f"cluster_{method}"
    majority = cells.groupby(cluster_column, sort=True)["truth"].agg(
        lambda labels: labels.value_counts(sort=True).index[0]
    )
    predicted = cells[cluster_column].map(majority)
    if predicted.isna().any():
        raise Figure03ValidationError(f"No majority reference label for a {method} cluster")
    return predicted.astype(str)


def _cell_metric(
    cells: pd.DataFrame,
    method: str,
    annotations: Mapping[str, str],
) -> tuple[float, float, float]:
    predicted = _annotation_series(cells, method, annotations)
    majority = _majority_reference_series(cells, method)
    accuracy = float(predicted.eq(cells["truth"]).mean())
    upper_bound = float(majority.eq(cells["truth"]).mean())
    pct_upper_bound = 100.0 * accuracy / upper_bound
    return accuracy, upper_bound, pct_upper_bound


def _cluster_metric(
    cells: pd.DataFrame,
    method: str,
    annotations: Mapping[str, str],
) -> tuple[float, float, float]:
    cluster_column = f"cluster_{method}"
    predicted = _annotation_series(cells, method, annotations)
    majority = _majority_reference_series(cells, method)
    work = cells[[cluster_column, "truth"]].copy()
    work["_model_correct"] = predicted.eq(work["truth"]).to_numpy()
    work["_upper_correct"] = majority.eq(work["truth"]).to_numpy()
    accuracy = float(work.groupby(cluster_column, sort=True)["_model_correct"].mean().mean())
    upper_bound = float(work.groupby(cluster_column, sort=True)["_upper_correct"].mean().mean())
    pct_upper_bound = 100.0 * accuracy / upper_bound
    return accuracy, upper_bound, pct_upper_bound


def metric_for_level(
    cells: pd.DataFrame,
    method: str,
    annotations: Mapping[str, str],
    level: str,
) -> tuple[float, float, float]:
    if level == "cell":
        return _cell_metric(cells, method, annotations)
    if level == "cluster":
        return _cluster_metric(cells, method, annotations)
    raise Figure03ValidationError(f"Unknown annotation metric level: {level!r}")


def _consensus_annotations_with_priority(
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    config: Mapping[str, Any],
    *,
    method: str,
    priority: Sequence[str],
    condition: str = "reasoning",
    marker_state: str = "optimized",
) -> dict[str, str]:
    providers = [str(provider) for provider in config["provider_display_order"]]
    maps = {
        provider: results[(provider, condition, method, marker_state)].annotations
        for provider in providers
    }
    cluster_ids = set(next(iter(maps.values())))
    if any(set(mapping) != cluster_ids for mapping in maps.values()):
        raise Figure03ValidationError(f"Consensus inputs disagree on {method} cluster IDs")
    priority = [str(provider) for provider in priority]
    if set(priority) != set(providers) or len(priority) != len(providers):
        raise Figure03ValidationError(
            f"Consensus priority for {method} must contain every provider exactly once"
        )
    consensus: dict[str, str] = {}
    for cluster in sorted(cluster_ids, key=int):
        votes = {provider: maps[provider][cluster] for provider in providers}
        counts = Counter(votes.values())
        highest = max(counts.values())
        winners = {label for label, count in counts.items() if count == highest}
        consensus[cluster] = next(
            votes[provider] for provider in priority if votes[provider] in winners
        )
    return consensus


def _consensus_annotations(
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    config: Mapping[str, Any],
    *,
    method: str,
    condition: str = "reasoning",
    marker_state: str = "optimized",
) -> dict[str, str]:
    """Reproduce the Methods-specified, retrospectively selected tie priority."""
    return _consensus_annotations_with_priority(
        results,
        config,
        method=method,
        priority=config["consensus"]["tie_priority"][method],
        condition=condition,
        marker_state=marker_state,
    )


def _consensus_tie_sensitivity_table(
    inputs: Figure03Inputs,
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    config: Mapping[str, Any],
    *,
    level: str,
    condition: str,
    methods: Sequence[str],
) -> pd.DataFrame:
    """Score every provider priority to disclose retrospective tie tuning."""
    providers = tuple(str(provider) for provider in config["provider_display_order"])
    rows: list[dict[str, Any]] = []
    for method in methods:
        selected = tuple(
            str(provider)
            for provider in config["consensus"]["tie_priority"][method]
        )
        for priority in permutations(providers):
            annotations = _consensus_annotations_with_priority(
                results,
                config,
                method=method,
                priority=priority,
                condition=condition,
            )
            accuracy, upper_bound, pct_upper_bound = metric_for_level(
                inputs.cells,
                method,
                annotations,
                level,
            )
            rows.append(
                {
                    "method": method,
                    "priority_order": " > ".join(priority),
                    "selected_historical_order": priority == selected,
                    "annotation_accuracy": accuracy,
                    "upper_bound_accuracy": upper_bound,
                    "pct_upper_bound": pct_upper_bound,
                    "annotation_sha256": _sha256_text(
                        json.dumps(annotations, sort_keys=True)
                    ),
                }
            )
    return pd.DataFrame(rows)


def _annotation_provenance(
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    repository_root: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(results):
        result = results[key]
        rows.append(
            {
                "provider": result.provider,
                "condition": result.condition,
                "method": result.method,
                "marker_state": result.marker_state,
                "requested_model_id": result.requested_model_id,
                "returned_model_id": result.returned_model_id,
                "cache_path": str(result.cache_path.relative_to(repository_root)),
                "cache_sha256": _sha256_file(result.cache_path),
                "cache_hit": bool(result.cache_hit),
                "cache_contract_sha256": result.cache_contract_sha256,
                "annotation_sha256": result.annotation_sha256,
                "prompt_sha256": result.prompt_sha256,
                "marker_summary_sha256": result.marker_summary_sha256,
            }
        )
    return rows


def _panel_output_paths(
    repository_root: Path,
    panel: Mapping[str, Any],
) -> dict[str, Path]:
    output_directory = repository_root / "outputs/figure_03"
    stem = str(panel["output_stem"])
    return {
        "png": output_directory / f"{stem}.png",
        "pdf": output_directory / f"{stem}.pdf",
        "csv": output_directory / f"{stem}.csv",
        "provenance": output_directory / f"{stem}_provenance.json",
    }


def _write_panel_provenance(
    path: Path,
    *,
    panel_key: str,
    config_path: Path,
    inputs: Figure03Inputs | None,
    annotation_results: Mapping[tuple[str, str, str, str], AnnotationResult] | None,
    repository_root: Path,
    extra: Mapping[str, Any] | None = None,
) -> Path:
    payload: dict[str, Any] = {
        "figure": 3,
        "panel": panel_key.removeprefix("panel_").upper(),
        "config_path": str(config_path.relative_to(repository_root)),
        "config_sha256": _sha256_file(config_path),
    }
    if inputs is not None:
        payload.update(
            {
                "figure_02_config_path": str(
                    inputs.figure_02_config_path.relative_to(repository_root)
                ),
                "figure_02_config_sha256": _sha256_file(inputs.figure_02_config_path),
                "source_cell_count": inputs.source_cell_count,
                "evaluation_cell_count": inputs.evaluation_cell_count,
                "cluster_counts": inputs.cluster_counts,
                "marker_count": len(inputs.marker_names),
                "expression_sha256": inputs.expression_sha256,
            }
        )
    if annotation_results is not None:
        payload["llm_annotations"] = _annotation_provenance(
            annotation_results,
            repository_root,
        )
    if extra:
        payload.update(dict(extra))
    return _json_dump(path, payload)


def _save_figure(fig: Any, paths: Mapping[str, Path]) -> None:
    paths["png"].parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(paths["png"], dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(paths["pdf"], bbox_inches="tight", facecolor="white")


def render_panel_a(paths: Mapping[str, Path], config: Mapping[str, Any]) -> None:
    """Render the Figure 2 -> marker summary -> LLM -> evaluation workflow."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(13.0, 3.8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 4)
    ax.axis("off")

    boxes = [
        (0.35, 1.25, 2.1, 1.45, "Figure 2 clusters", "FlowSOM · Leiden\nSpatialSort · TIFF PIXIE"),
        (2.9, 1.25, 2.1, 1.45, "45-marker H5AD X", "Cluster mean +\npositive fraction"),
        (5.45, 1.25, 2.1, 1.45, "Marker summaries", "Default or optimized\nranked marker lists"),
        (8.0, 1.25, 2.1, 1.45, "LLM annotation", "4 providers ×\n2 prompt conditions"),
        (10.55, 1.25, 2.1, 1.45, "Evaluation", "Cell / cluster accuracy\nupper bound · consensus"),
    ]
    fills = ["#E8EEF7", "#E8EEF7", "#FFF1D6", "#FCE7D7", "#E8F3E7"]
    for (x, y, width, height, title, detail), fill in zip(boxes, fills):
        patch = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            linewidth=1.2,
            edgecolor="#243042",
            facecolor=fill,
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, y + height * 0.67, title, ha="center", va="center", fontsize=12)
        ax.text(
            x + width / 2,
            y + height * 0.31,
            detail,
            ha="center",
            va="center",
            fontsize=9,
            color="#4B5563",
        )
    for left, right in zip(boxes[:-1], boxes[1:]):
        start = (left[0] + left[2], left[1] + left[3] / 2)
        end = (right[0], right[1] + right[3] / 2)
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=13,
                linewidth=1.2,
                color="#243042",
            )
        )

    ax.text(
        0.03,
        3.75,
        "A",
        fontsize=31,
        va="top",
        ha="left",
    )
    ax.text(
        6.5,
        3.55,
        str(config["panels"]["panel_a"]["title"]),
        fontsize=16,
        ha="center",
        va="top",
    )
    ax.text(
        6.5,
        0.55,
        "220,082-cell marker summaries · 209,587-cell non-Noise evaluation · exact File_ID + ID joins",
        fontsize=10,
        ha="center",
        color="#4B5563",
    )
    _save_figure(fig, paths)
    plt.close(fig)


def _holm_adjust(p_values: Sequence[float]) -> np.ndarray:
    raw = np.asarray(p_values, dtype=float)
    order = np.argsort(raw)
    adjusted = np.empty_like(raw)
    running_max = 0.0
    total = len(raw)
    for rank, index in enumerate(order):
        candidate = min(1.0, (total - rank) * raw[index])
        running_max = max(running_max, candidate)
        adjusted[index] = running_max
    return adjusted


def paired_significance_table(
    table: pd.DataFrame,
    state_order: Sequence[str],
    method_order: Sequence[str],
) -> pd.DataFrame:
    """Run paired two-sided Wilcoxon tests with Holm correction."""
    from scipy.stats import wilcoxon

    if len(state_order) != 2:
        raise Figure03ValidationError("Paired significance requires exactly two states")
    rows: list[dict[str, Any]] = []
    for method in method_order:
        subset = table.loc[table["method"].eq(method)].pivot(
            index="region",
            columns="state",
            values="pct_upper_bound",
        )
        subset = subset.loc[:, list(state_order)].dropna()
        try:
            result = wilcoxon(
                subset[state_order[0]].to_numpy(dtype=float),
                subset[state_order[1]].to_numpy(dtype=float),
                alternative="two-sided",
            )
            statistic = float(result.statistic)
            p_value = float(result.pvalue)
        except ValueError:
            statistic = 0.0
            p_value = 1.0
        rows.append(
            {
                "method": method,
                "n_regions": int(len(subset)),
                "wilcoxon_statistic": statistic,
                "p_value": p_value,
            }
        )
    stats = pd.DataFrame(rows)
    stats["p_holm"] = _holm_adjust(stats["p_value"].tolist())
    stats["significance"] = stats["p_holm"].map(
        lambda p: "**" if p < 0.01 else ("*" if p < 0.05 else "ns")
    )
    return stats


def render_paired_boxplot(
    table: pd.DataFrame,
    stats: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
    *,
    panel_key: str,
    state_order: Sequence[str],
    state_labels: Mapping[str, str],
    state_colors: Mapping[str, str],
    y_limits: tuple[float, float] = (35.0, 100.0),
) -> None:
    """Render paired eight-region box/strip comparisons for B, D, or E."""
    import matplotlib.pyplot as plt

    panel = config["panels"][panel_key]
    method_order = [str(method) for method in config["figure_02_dependency"]["method_display_order"]]
    method_labels = {
        method: str(config["figure_02_dependency"]["expected_methods"][method]["label"])
        for method in method_order
    }
    region_colors = {
        str(region): str(color) for region, color in config["style"]["region_colors"].items()
    }
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig, ax = plt.subplots(figsize=(6.9, 4.6))
    centers = np.arange(len(method_order), dtype=float) * 1.35 + 1.0
    offsets = {state_order[0]: -0.22, state_order[1]: 0.22}
    region_order = sorted(table["region"].astype(str).unique())
    jitter = np.linspace(-0.035, 0.035, len(region_order))

    for method_index, method in enumerate(method_order):
        method_table = table.loc[table["method"].eq(method)]
        pivot = method_table.pivot(index="region", columns="state", values="pct_upper_bound")
        pivot.index = pivot.index.astype(str)
        pivot = pivot.loc[region_order, list(state_order)]
        for state in state_order:
            position = centers[method_index] + offsets[state]
            values = pivot[state].to_numpy(dtype=float)
            box = ax.boxplot(
                [values],
                positions=[position],
                widths=0.37,
                patch_artist=True,
                showfliers=False,
                manage_ticks=False,
                medianprops={"color": "#111827", "linewidth": 1.25},
                boxprops={"edgecolor": "#111827", "linewidth": 1.0},
                whiskerprops={"color": "#111827", "linewidth": 1.0},
                capprops={"color": "#111827", "linewidth": 1.0},
            )
            box["boxes"][0].set_facecolor(state_colors[state])
        for region_index, region in enumerate(region_order):
            xs = [centers[method_index] + offsets[state] + jitter[region_index] for state in state_order]
            ys = [float(pivot.loc[region, state]) for state in state_order]
            ax.plot(xs, ys, color="#CBD5E1", linewidth=0.7, zorder=1)
            ax.scatter(
                xs,
                ys,
                color=region_colors[region],
                s=20,
                edgecolors="none",
                zorder=3,
            )

        significance = str(
            stats.loc[stats["method"].eq(method), "significance"].iloc[0]
        )
        method_max = float(
            method_table["pct_upper_bound"].max()
        )
        y = min(y_limits[1] - 3.0, method_max + 3.0)
        x_left = centers[method_index] + offsets[state_order[0]]
        x_right = centers[method_index] + offsets[state_order[1]]
        ax.plot(
            [x_left, x_left, x_right, x_right],
            [y, y + 0.8, y + 0.8, y],
            color="#111827",
            linewidth=0.9,
        )
        ax.text((x_left + x_right) / 2, y + 1.05, significance, ha="center", va="bottom")

    ax.set_xlim(centers[0] - 0.65, centers[-1] + 0.65)
    ax.set_ylim(*y_limits)
    ax.set_xticks(centers)
    ax.set_xticklabels([method_labels[method] for method in method_order], fontsize=10)
    ax.set_xlabel("Clustering Method", fontsize=11)
    ax.set_ylabel(str(panel.get("y_axis_label", "Upper Bound Purity (%)")), fontsize=11)
    ax.set_title(str(panel["title"]), fontsize=12, pad=8)
    ax.grid(axis="y", linestyle="--", linewidth=0.7, color="#D1D5DB", alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=state_colors[state], edgecolor="#111827")
        for state in state_order
    ]
    ax.legend(
        handles,
        [state_labels[state] for state in state_order],
        frameon=False,
        loc="lower right",
        fontsize=9,
    )
    fig.text(0.015, 0.97, panel_key[-1].upper(), fontsize=29, ha="left", va="top")
    bottom = 0.16
    if panel.get("condition_caveat"):
        fig.text(
            0.50,
            0.015,
            str(panel["condition_caveat"]),
            fontsize=6.6,
            ha="center",
        )
        bottom = 0.22
    fig.subplots_adjust(left=0.14, right=0.98, bottom=bottom, top=0.88)
    _save_figure(fig, paths)
    plt.close(fig)


def render_panel_c(
    table: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
) -> None:
    """Render Ground Truth, before, and after target-cell spatial maps."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    panel = config["panels"]["panel_c"]
    target = str(panel["target_cell_type"])
    columns = [
        ("Ground Truth", "truth"),
        ("Before Protein Marker Optimization", "pred_before"),
        ("After Protein Marker Optimization", "pred_after"),
    ]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.0))
    for axis, (title, column) in zip(axes, columns):
        if column == "truth":
            is_target = table["truth"].eq(target)
        else:
            # Reproduce the legacy callout definition: blue cells are true
            # target cells recovered by the annotation, not all cells merely
            # predicted as the target (which would include false positives).
            is_target = table["truth"].eq(target) & table[column].eq(target)
        axis.scatter(
            table.loc[~is_target, "x"],
            table.loc[~is_target, "y"],
            s=1.0,
            color=str(panel["other_color"]),
            alpha=0.45,
            edgecolors="none",
            rasterized=True,
        )
        axis.scatter(
            table.loc[is_target, "x"],
            table.loc[is_target, "y"],
            s=2.0,
            color=str(panel["target_color"]),
            alpha=0.9,
            edgecolors="none",
            rasterized=True,
        )
        axis.set_title(title, fontsize=10, pad=7)
        axis.set_aspect("equal")
        axis.invert_yaxis()
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_color("#9CA3AF")
            spine.set_linewidth(0.6)
    handles = [
        Patch(facecolor=str(panel["target_color"]), edgecolor="#374151", label=f"{target} cells"),
        Patch(facecolor=str(panel["other_color"]), edgecolor="#6B7280", label="Other cells"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, fontsize=9)
    fig.text(0.012, 0.96, "C", fontsize=29, ha="left", va="top")
    fig.subplots_adjust(left=0.05, right=0.99, bottom=0.16, top=0.88, wspace=0.18)
    _save_figure(fig, paths)
    plt.close(fig)


def render_llm_method_heatmap(
    table: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
    *,
    panel_key: str,
) -> None:
    """Render the 4-by-4 provider/method heatmaps for Panels F and G."""
    import matplotlib.pyplot as plt

    panel = config["panels"][panel_key]
    providers = [str(provider) for provider in config["provider_display_order"]]
    methods = [str(method) for method in config["figure_02_dependency"]["method_display_order"]]
    provider_labels = {
        provider: str(config["providers"][provider]["label"]) for provider in providers
    }
    method_labels = {
        method: str(config["figure_02_dependency"]["expected_methods"][method]["label"])
        for method in methods
    }
    pivot = table.pivot(index="provider", columns="method", values="pct_upper_bound")
    matrix = pivot.loc[providers, methods].to_numpy(dtype=float)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig, ax = plt.subplots(figsize=(5.2, 4.5))
    image = ax.imshow(
        matrix,
        cmap=str(config["style"]["heatmap_cmap"]),
        vmin=40.0,
        vmax=100.0,
        aspect="auto",
    )
    ax.set_xticks(np.arange(len(methods)))
    ax.set_xticklabels([method_labels[method] for method in methods], fontsize=9)
    ax.set_yticks(np.arange(len(providers)))
    ax.set_yticklabels([provider_labels[provider] for provider in providers], fontsize=9)
    ax.set_xlabel("Clustering Method", fontsize=10)
    ax.set_ylabel("LLM", fontsize=10)
    ax.set_title(str(panel["title"]), fontsize=11, pad=9)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            color = "white" if value < 62.0 or value > 78.0 else "#111827"
            ax.text(
                column,
                row,
                f"{value:.1f}%",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="semibold",
                color=color,
            )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.045, pad=0.04)
    colorbar.set_label("Upper Bound Purity (%)", fontsize=9)
    fig.text(0.015, 0.97, panel_key[-1].upper(), fontsize=29, ha="left", va="top")
    fig.subplots_adjust(left=0.22, right=0.91, bottom=0.16, top=0.87)
    _save_figure(fig, paths)
    plt.close(fig)


def render_cell_type_heatmap(
    table: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
    *,
    panel_key: str,
    value_column: str,
    colorbar_label: str,
) -> None:
    """Render Leiden provider-by-cell-type heatmaps with reference counts."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    panel = config["panels"][panel_key]
    providers = [str(provider) for provider in config["provider_display_order"]]
    provider_labels = {
        provider: str(config["providers"][provider]["label"]) for provider in providers
    }
    cell_order = (
        table.groupby("cell_type", as_index=False)[value_column]
        .mean()
        .sort_values(value_column, ascending=False, kind="mergesort")["cell_type"]
        .tolist()
    )
    pivot = table.pivot(index="cell_type", columns="provider", values=value_column)
    matrix = pivot.loc[cell_order, providers].to_numpy(dtype=float)
    counts = (
        table.drop_duplicates("cell_type")
        .set_index("cell_type")
        .loc[cell_order, "cell_count"]
        .to_numpy(dtype=float)
    )

    figure_height = max(6.0, 0.31 * len(cell_order) + 1.6)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig = plt.figure(figsize=(7.4, figure_height))
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=(4.0, 1.55),
        height_ratios=(0.06, 1.0),
        wspace=0.04,
        hspace=0.09,
    )
    color_ax = fig.add_subplot(grid[0, 0])
    fig.add_subplot(grid[0, 1]).axis("off")
    heat_ax = fig.add_subplot(grid[1, 0])
    count_ax = fig.add_subplot(grid[1, 1], sharey=heat_ax)

    image = heat_ax.imshow(
        matrix,
        cmap=str(config["style"]["heatmap_cmap"]),
        vmin=0.0,
        vmax=100.0,
        aspect="auto",
    )
    heat_ax.set_xticks(np.arange(len(providers)))
    heat_ax.set_xticklabels([provider_labels[p] for p in providers], fontsize=9)
    heat_ax.set_yticks(np.arange(len(cell_order)))
    heat_ax.set_yticklabels(cell_order, fontsize=8.5)
    heat_ax.set_xlabel("LLM", fontsize=10)
    heat_ax.set_ylabel("Cell Type", fontsize=10)
    heat_ax.set_title(str(panel["title"]), fontsize=11, pad=7)

    colorbar = fig.colorbar(image, cax=color_ax, orientation="horizontal")
    colorbar.set_label(colorbar_label, fontsize=9)
    colorbar.set_ticks(np.linspace(0.0, 100.0, 6))
    color_ax.xaxis.set_ticks_position("top")
    color_ax.xaxis.set_label_position("top")

    y = np.arange(len(cell_order))
    count_ax.barh(y, counts, height=0.74, color=str(config["style"]["count_bar_color"]))
    count_ax.set_xlabel("Cell Count", fontsize=9)
    count_ax.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: "0" if value == 0 else f"{value / 1000:.0f}k")
    )
    count_ax.tick_params(axis="y", left=False, labelleft=False)
    count_ax.grid(axis="x", linestyle="--", linewidth=0.6, alpha=0.35)
    count_ax.set_axisbelow(True)
    count_ax.spines["top"].set_visible(False)
    count_ax.spines["right"].set_visible(False)
    count_ax.set_ylim(heat_ax.get_ylim())
    fig.text(0.015, 0.98, panel_key[-1].upper(), fontsize=29, ha="left", va="top")
    fig.subplots_adjust(left=0.28, right=0.98, bottom=0.10, top=0.90)
    _save_figure(fig, paths)
    plt.close(fig)


def render_grouped_bars(
    table: pd.DataFrame,
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
    *,
    panel_key: str,
) -> None:
    """Render reasoning-provider and four-model-consensus comparisons."""
    import matplotlib.pyplot as plt

    panel = config["panels"][panel_key]
    methods = [
        str(method) for method in config["figure_02_dependency"]["grouped_bar_method_order"]
    ]
    series = [str(provider) for provider in config["provider_display_order"]] + ["consensus"]
    labels = {
        **{
            provider: str(config["providers"][provider]["label"])
            for provider in config["provider_display_order"]
        },
        "consensus": "Historical Vote*",
    }
    colors = {str(key): str(value) for key, value in config["style"]["provider_colors"].items()}
    pivot = table.pivot(index="method", columns="series", values="pct_upper_bound")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    x = np.arange(len(methods), dtype=float)
    width = 0.15
    offsets = (np.arange(len(series)) - (len(series) - 1) / 2.0) * width
    for index, series_key in enumerate(series):
        values = pivot.loc[methods, series_key].to_numpy(dtype=float)
        ax.bar(
            x + offsets[index],
            values,
            width=width,
            color=colors[series_key],
            edgecolor="#111827",
            linewidth=0.45,
            label=labels[series_key],
        )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            str(config["figure_02_dependency"]["expected_methods"][method]["label"])
            for method in methods
        ],
        fontsize=9,
    )
    ax.set_ylabel("Accuracy (%)", fontsize=10)
    ax.set_xlabel("Clustering Method", fontsize=10)
    ax.set_title(str(panel["title"]), fontsize=11, pad=8)
    ax.set_ylim(0.0, 100.0)
    ax.grid(axis="y", color="#D1D5DB", linewidth=0.7, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        ncol=5,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.16),
        fontsize=8.5,
    )
    fig.text(0.015, 0.97, panel_key[-1].upper(), fontsize=29, ha="left", va="top")
    fig.text(
        0.50,
        0.015,
        "* Tie priority selected on these evaluation labels; exploratory. "
        "All 24 orders are exported.",
        fontsize=6.8,
        ha="center",
    )
    fig.subplots_adjust(left=0.11, right=0.99, bottom=0.22, top=0.80)
    _save_figure(fig, paths)
    plt.close(fig)


def _load_cell_type_color_map(
    inputs: Figure03Inputs,
    repository_root: Path,
    config: Mapping[str, Any],
) -> dict[str, str]:
    """Load the tracked 20-class Figure 3 palette without gray fallbacks."""
    path = repository_root / str(config["style"]["cell_type_color_map_path"])
    table = pd.read_csv(path, usecols=["cell_type", "color_hex"])
    if table["cell_type"].duplicated().any():
        duplicates = sorted(
            table.loc[table["cell_type"].duplicated(keep=False), "cell_type"]
            .astype(str)
            .unique()
        )
        raise Figure03ValidationError(
            f"Figure 3 color map contains duplicate labels: {duplicates}"
        )
    color_map = dict(
        zip(
            table["cell_type"].astype(str),
            table["color_hex"].astype(str),
            strict=True,
        )
    )
    expected = set(str(label) for label in inputs.cells["truth"].unique())
    observed = set(color_map)
    if observed != expected:
        raise Figure03ValidationError(
            "Figure 3 color map does not exactly cover the evaluation vocabulary: "
            f"missing={sorted(expected - observed)}, unexpected={sorted(observed - expected)}"
        )
    invalid = {
        label: color
        for label, color in color_map.items()
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None
    }
    if invalid:
        raise Figure03ValidationError(f"Figure 3 color map has invalid colors: {invalid}")
    return color_map


def _search_spatial_examples(
    cells: pd.DataFrame,
    panel: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select deterministic low/high square windows containing roughly 1,000 cells."""
    target = int(panel["target_cells"])
    tolerance = int(panel["cell_tolerance"])
    minimum = target - tolerance
    maximum = target + tolerance
    samples_per_file = int(panel["candidate_centers_per_file"])
    scales = [float(scale) for scale in panel["radius_scale_factors"]]
    rng_low = np.random.default_rng(int(panel["random_seed"]))
    rng_high = np.random.default_rng(int(panel["random_seed"]) + 1)

    def candidates(rng: np.random.Generator, low: bool) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for file_id in cells["File_ID"].drop_duplicates().astype(str):
            region = cells.loc[cells["File_ID"].astype(str).eq(file_id)].copy()
            if len(region) < minimum:
                continue
            coords = region[["x", "y"]].to_numpy(dtype=float)
            n_centers = min(samples_per_file, len(region))
            center_indices = rng.choice(len(region), size=n_centers, replace=False)
            for center_index in center_indices:
                center_x, center_y = coords[center_index]
                distances = np.maximum(
                    np.abs(coords[:, 0] - center_x),
                    np.abs(coords[:, 1] - center_y),
                )
                base = float(np.partition(distances, min(target - 1, len(distances) - 1))[
                    min(target - 1, len(distances) - 1)
                ])
                for scale in scales:
                    half_side = base * scale
                    mask = (
                        (coords[:, 0] >= center_x - half_side)
                        & (coords[:, 0] <= center_x + half_side)
                        & (coords[:, 1] >= center_y - half_side)
                        & (coords[:, 1] <= center_y + half_side)
                    )
                    count = int(mask.sum())
                    if count < minimum or count > maximum:
                        continue
                    window = region.loc[mask].copy()
                    agreement = float(window["agreement_fraction"].mean())
                    count_score = 1.0 - abs(count - target) / max(1, tolerance)
                    score = (
                        ((1.0 - agreement) if low else agreement) * 0.85
                        + count_score * 0.15
                    )
                    found.append(
                        {
                            "score": score,
                            "file_id": file_id,
                            "center_x": float(center_x),
                            "center_y": float(center_y),
                            "half_side": float(half_side),
                            "n_cells": count,
                            "agreement": agreement,
                            "window": window,
                        }
                    )
        return sorted(found, key=lambda item: item["score"], reverse=True)

    low_candidates = candidates(rng_low, True)
    high_candidates = candidates(rng_high, False)
    if not low_candidates or not high_candidates:
        raise Figure03ValidationError("Panel L could not find valid 900--1,100-cell windows")

    selected_low = low_candidates[0]
    selected_high = next(
        (
            candidate
            for candidate in high_candidates
            if candidate["file_id"] != selected_low["file_id"]
        ),
        high_candidates[0],
    )
    if selected_high["agreement"] <= selected_low["agreement"]:
        raise Figure03ValidationError("Panel L high-agreement example is not more concordant")

    metadata_rows = []
    for name, item in (("Low Agreement", selected_low), ("High Agreement", selected_high)):
        metadata_rows.append(
            {
                "example": name,
                "File_ID": item["file_id"],
                "x_min": item["center_x"] - item["half_side"],
                "x_max": item["center_x"] + item["half_side"],
                "y_min": item["center_y"] - item["half_side"],
                "y_max": item["center_y"] + item["half_side"],
                "n_cells": item["n_cells"],
                "mean_agreement_fraction": item["agreement"],
            }
        )
    examples = pd.concat(
        [
            selected_low["window"].assign(example="Low Agreement"),
            selected_high["window"].assign(example="High Agreement"),
        ],
        ignore_index=True,
    )
    return examples, pd.DataFrame(metadata_rows)


def render_panel_l(
    cells: pd.DataFrame,
    examples: pd.DataFrame,
    metadata: pd.DataFrame,
    color_map: Mapping[str, str],
    paths: Mapping[str, Path],
    config: Mapping[str, Any],
) -> None:
    """Render whole-tissue callouts plus six annotation zooms for low/high examples."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import ConnectionPatch, Rectangle

    panel = config["panels"]["panel_l"]
    columns = [
        ("Ground Truth", "truth"),
        ("GPT", "pred_openai"),
        ("Gemini", "pred_gemini"),
        ("Claude", "pred_anthropic"),
        ("DeepSeek", "pred_deepseek"),
        ("Historical Vote*", "pred_consensus"),
    ]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
    fig = plt.figure(figsize=(13.2, 4.4))
    grid = fig.add_gridspec(2, 7, width_ratios=[1.05, 1, 1, 1, 1, 1, 1], hspace=0.10, wspace=0.06)
    axes = [[fig.add_subplot(grid[row, column]) for column in range(7)] for row in range(2)]

    for row, example_name in enumerate(("Low Agreement", "High Agreement")):
        meta = metadata.loc[metadata["example"].eq(example_name)].iloc[0]
        full = cells.loc[cells["File_ID"].astype(str).eq(str(meta["File_ID"]))].copy()
        zoom = examples.loc[examples["example"].eq(example_name)].copy()
        whole_ax = axes[row][0]
        for label in sorted(full["truth"].unique()):
            subset = full.loc[full["truth"].eq(label)]
            whole_ax.scatter(
                subset["x"],
                subset["y"],
                s=1.0,
                color=color_map.get(label, "#BDBDBD"),
                alpha=0.75,
                edgecolors="none",
                rasterized=True,
            )
        rectangle = Rectangle(
            (float(meta["x_min"]), float(meta["y_min"])),
            float(meta["x_max"] - meta["x_min"]),
            float(meta["y_max"] - meta["y_min"]),
            linewidth=0.8,
            edgecolor="#111827",
            facecolor="none",
        )
        whole_ax.add_patch(rectangle)
        whole_ax.set_aspect("equal")
        whole_ax.invert_yaxis()
        whole_ax.set_xticks([])
        whole_ax.set_yticks([])
        for spine in whole_ax.spines.values():
            spine.set_color("#9CA3AF")
            spine.set_linewidth(0.5)

        for column_index, (title, label_column) in enumerate(columns, start=1):
            axis = axes[row][column_index]
            for label in sorted(zoom[label_column].unique()):
                subset = zoom.loc[zoom[label_column].eq(label)]
                axis.scatter(
                    subset["x"],
                    subset["y"],
                    s=5.0,
                    color=color_map.get(label, "#BDBDBD"),
                    alpha=0.85,
                    edgecolors="none",
                    rasterized=True,
                )
            axis.set_xlim(float(meta["x_min"]), float(meta["x_max"]))
            axis.set_ylim(float(meta["y_min"]), float(meta["y_max"]))
            axis.set_aspect("equal")
            axis.invert_yaxis()
            axis.set_xticks([])
            axis.set_yticks([])
            if row == 0:
                axis.set_title(title, fontsize=9, pad=5)
            for spine in axis.spines.values():
                spine.set_color("#9CA3AF")
                spine.set_linewidth(0.5)

        ground_truth_ax = axes[row][1]
        whole_ax.add_artist(
            ConnectionPatch(
                xyA=(float(meta["x_max"]), float(meta["y_min"])),
                xyB=(0, 1),
                coordsA="data",
                coordsB="axes fraction",
                axesA=whole_ax,
                axesB=ground_truth_ax,
                color="#111827",
                linewidth=0.6,
            )
        )
        whole_ax.add_artist(
            ConnectionPatch(
                xyA=(float(meta["x_max"]), float(meta["y_max"])),
                xyB=(0, 0),
                coordsA="data",
                coordsB="axes fraction",
                axesA=whole_ax,
                axesB=ground_truth_ax,
                color="#111827",
                linewidth=0.6,
            )
        )
        fig.text(0.015, 0.70 if row == 0 else 0.285, example_name, fontsize=10, va="center")

    fig.suptitle(str(panel["title"]), fontsize=12, y=0.98)
    fig.text(0.005, 0.98, "L", fontsize=29, ha="left", va="top")
    fig.text(
        0.67,
        0.015,
        "* Tie priority selected on evaluation labels; exploratory.",
        fontsize=6.8,
        ha="center",
    )
    fig.subplots_adjust(left=0.10, right=0.995, top=0.88, bottom=0.08)
    _save_figure(fig, paths)
    plt.close(fig)


def _run_context(
    repository_root: str | Path | None,
    config_path: str | Path | None,
) -> tuple[Path, Path, dict[str, Any]]:
    root = _resolve_repository_root(repository_root)
    path = _resolve_config_path(root, config_path)
    return root, path, load_figure_config(path)


def run_panel_a(
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Render Panel A, the only Figure 3 panel that does not require an API key."""
    root, path, config = _run_context(repository_root, config_path)
    panel = config["panels"]["panel_a"]
    paths = _panel_output_paths(root, panel)
    render_panel_a(paths, config)
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_a",
        config_path=path,
        inputs=None,
        annotation_results=None,
        repository_root=root,
        extra={
            "description": "Workflow schematic only; no biological result is computed.",
            "figure_02_dependency": config["figure_02_dependency"],
        },
    )
    return {
        key: paths[key]
        for key in ("png", "pdf", "provenance")
    }


def run_panel_b(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel B's regional before/after marker-optimization comparison."""
    root, path, config = _run_context(repository_root, config_path)
    panel = config["panels"]["panel_b"]
    provider = str(panel["annotation_provider"])
    condition = str(panel["annotation_condition"])
    require_api_keys(api_keys, [provider], config)

    inputs = load_figure03_inputs(root, path)
    methods = [str(method) for method in config["figure_02_dependency"]["method_display_order"]]
    marker_states = [str(state) for state in panel["states"]]
    results = ensure_annotations(
        inputs,
        config,
        root,
        api_keys,
        providers=[provider],
        conditions=[condition],
        methods=methods,
        marker_states=marker_states,
        force_refresh=force_refresh,
    )

    rows: list[dict[str, Any]] = []
    for method in methods:
        for file_id, region in inputs.cells.groupby("File_ID", sort=True):
            for marker_state in marker_states:
                annotations = results[
                    (provider, condition, method, marker_state)
                ].annotations
                accuracy, upper_bound, pct_upper_bound = _cell_metric(
                    region,
                    method,
                    annotations,
                )
                rows.append(
                    {
                        "region": str(file_id),
                        "method": method,
                        "state": marker_state,
                        "n_cells": int(len(region)),
                        "annotation_accuracy": accuracy,
                        "upper_bound_accuracy": upper_bound,
                        "pct_upper_bound": pct_upper_bound,
                    }
                )
    table = pd.DataFrame(rows)
    stats = paired_significance_table(table, marker_states, methods)
    paths = _panel_output_paths(root, panel)
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(paths["csv"], index=False)
    stats_path = paths["csv"].with_name(f"{paths['csv'].stem}_stats.csv")
    stats.to_csv(stats_path, index=False)
    render_paired_boxplot(
        table,
        stats,
        paths,
        config,
        panel_key="panel_b",
        state_order=marker_states,
        state_labels={"default": "Before", "optimized": "After"},
        state_colors={
            "default": str(config["style"]["before_color"]),
            "optimized": str(config["style"]["after_color"]),
        },
        y_limits=(35.0, 100.0),
    )
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_b",
        config_path=path,
        inputs=inputs,
        annotation_results=results,
        repository_root=root,
        extra={
            "metric": "100 * regional cell-level annotation accuracy / regional clustering upper bound",
            "stats_csv": str(stats_path.relative_to(root)),
            "annotation_provider": provider,
            "annotation_condition": condition,
        },
    )
    return {**paths, "stats_csv": stats_path}


def run_panel_c(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel C's target-cell Ground Truth / before / after maps."""
    root, path, config = _run_context(repository_root, config_path)
    panel = config["panels"]["panel_c"]
    provider = str(panel["annotation_provider"])
    condition = str(panel["annotation_condition"])
    method = str(panel["method"])
    require_api_keys(api_keys, [provider], config)

    inputs = load_figure03_inputs(root, path)
    region_contract = panel["region"]
    table = inputs.marker_cells.loc[
        inputs.marker_cells["File_ID"].astype(str).eq(str(region_contract["file_id"]))
        & inputs.marker_cells["x"].between(
            float(region_contract["x_min"]),
            float(region_contract["x_max"]),
        )
        & inputs.marker_cells["y"].between(
            float(region_contract["y_min"]),
            float(region_contract["y_max"]),
        )
    ].copy()
    if table.empty:
        raise Figure03ValidationError("Panel C fixed spatial window contains no cells")
    target = str(panel["target_cell_type"])
    observed_contract = {
        "expected_region_cells": int(len(table)),
        "expected_target_cells": int(table["truth"].eq(target).sum()),
        "expected_noise_background_cells": int(table["truth_raw"].eq("Noise").sum()),
    }
    expected_contract = {
        key: int(panel[key])
        for key in (
            "expected_region_cells",
            "expected_target_cells",
            "expected_noise_background_cells",
        )
    }
    if observed_contract != expected_contract:
        raise Figure03ValidationError(
            "Panel C fixed spatial-window counts drifted: "
            f"observed={observed_contract}, expected={expected_contract}"
        )
    results = ensure_annotations(
        inputs,
        config,
        root,
        api_keys,
        providers=[provider],
        conditions=[condition],
        methods=[method],
        marker_states=["default", "optimized"],
        force_refresh=force_refresh,
    )
    table["pred_before"] = _annotation_series(
        table,
        method,
        results[(provider, condition, method, "default")].annotations,
    )
    table["pred_after"] = _annotation_series(
        table,
        method,
        results[(provider, condition, method, "optimized")].annotations,
    )
    paths = _panel_output_paths(root, panel)
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(paths["csv"], index=False)
    render_panel_c(table, paths, config)
    target_counts = {
        "ground_truth": int(table["truth"].eq(target).sum()),
        "before_correctly_recovered": int(
            (table["truth"].eq(target) & table["pred_before"].eq(target)).sum()
        ),
        "after_correctly_recovered": int(
            (table["truth"].eq(target) & table["pred_after"].eq(target)).sum()
        ),
        "before_predicted_total": int(table["pred_before"].eq(target).sum()),
        "after_predicted_total": int(table["pred_after"].eq(target).sum()),
    }
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_c",
        config_path=path,
        inputs=inputs,
        annotation_results=results,
        repository_root=root,
        extra={
            "method": method,
            "target_cell_type": target,
            "fixed_region": dict(region_contract),
            "region_cells": int(len(table)),
            "region_noise_background_cells": int(table["truth_raw"].eq("Noise").sum()),
            "target_counts": target_counts,
            "highlight_definition": (
                "ground truth highlights every true target cell; prediction panels "
                "highlight only true target cells correctly recovered"
            ),
        },
    )
    return paths


def _reasoning_comparison_table(
    inputs: Figure03Inputs,
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    config: Mapping[str, Any],
    *,
    level: str,
) -> pd.DataFrame:
    providers = [str(provider) for provider in config["provider_display_order"]]
    methods = [str(method) for method in config["figure_02_dependency"]["method_display_order"]]
    conditions = ("non_reasoning", "reasoning")
    rows: list[dict[str, Any]] = []
    for method in methods:
        for file_id, region in inputs.cells.groupby("File_ID", sort=True):
            for condition in conditions:
                accuracies: list[float] = []
                upper_bounds: list[float] = []
                for provider in providers:
                    annotations = results[
                        (provider, condition, method, "optimized")
                    ].annotations
                    accuracy, upper_bound, _ = metric_for_level(
                        region,
                        method,
                        annotations,
                        level,
                    )
                    accuracies.append(accuracy)
                    upper_bounds.append(upper_bound)
                if not np.allclose(upper_bounds, upper_bounds[0]):
                    raise Figure03ValidationError(
                        f"{method} {file_id} upper bound changed across providers"
                    )
                mean_accuracy = float(np.mean(accuracies))
                upper_bound = float(upper_bounds[0])
                rows.append(
                    {
                        "region": str(file_id),
                        "method": method,
                        "state": condition,
                        "n_cells": int(len(region)),
                        "mean_annotation_accuracy": mean_accuracy,
                        "upper_bound_accuracy": upper_bound,
                        "pct_upper_bound": 100.0 * mean_accuracy / upper_bound,
                    }
                )
    return pd.DataFrame(rows)


def _run_reasoning_comparison_panel(
    panel_key: str,
    api_keys: Mapping[str, str],
    repository_root: str | Path | None,
    config_path: str | Path | None,
    *,
    force_refresh: bool,
) -> dict[str, Path]:
    root, path, config = _run_context(repository_root, config_path)
    panel = config["panels"][panel_key]
    providers = [str(provider) for provider in config["provider_display_order"]]
    methods = [str(method) for method in config["figure_02_dependency"]["method_display_order"]]
    conditions = [str(state) for state in panel["states"]]
    require_api_keys(api_keys, providers, config)

    inputs = load_figure03_inputs(root, path)
    results = ensure_annotations(
        inputs,
        config,
        root,
        api_keys,
        providers=providers,
        conditions=conditions,
        methods=methods,
        marker_states=["optimized"],
        force_refresh=force_refresh,
    )
    level = str(panel["metric_level"])
    table = _reasoning_comparison_table(inputs, results, config, level=level)
    stats = paired_significance_table(table, conditions, methods)
    paths = _panel_output_paths(root, panel)
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(paths["csv"], index=False)
    stats_path = paths["csv"].with_name(f"{paths['csv'].stem}_stats.csv")
    stats.to_csv(stats_path, index=False)
    render_paired_boxplot(
        table,
        stats,
        paths,
        config,
        panel_key=panel_key,
        state_order=conditions,
        state_labels={
            "non_reasoning": "Non-Reasoning*",
            "reasoning": "Reasoning",
        },
        state_colors={
            "non_reasoning": str(config["style"]["non_reasoning_color"]),
            "reasoning": str(config["style"]["reasoning_color"]),
        },
        y_limits=(35.0, 90.0),
    )
    _write_panel_provenance(
        paths["provenance"],
        panel_key=panel_key,
        config_path=path,
        inputs=inputs,
        annotation_results=results,
        repository_root=root,
        extra={
            "metric_level": level,
            "metric": (
                "100 * mean of four providers' regional annotation accuracy / "
                "regional clustering upper bound"
            ),
            "stats_csv": str(stats_path.relative_to(root)),
        },
    )
    return {**paths, "stats_csv": stats_path}


def run_panel_d(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel D's cell-level reasoning comparison."""
    return _run_reasoning_comparison_panel(
        "panel_d",
        api_keys,
        repository_root,
        config_path,
        force_refresh=force_refresh,
    )


def run_panel_e(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel E's cluster-level reasoning comparison."""
    return _run_reasoning_comparison_panel(
        "panel_e",
        api_keys,
        repository_root,
        config_path,
        force_refresh=force_refresh,
    )


def _llm_method_table(
    inputs: Figure03Inputs,
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    config: Mapping[str, Any],
    *,
    condition: str,
    level: str,
) -> pd.DataFrame:
    providers = [str(provider) for provider in config["provider_display_order"]]
    methods = [str(method) for method in config["figure_02_dependency"]["method_display_order"]]
    rows: list[dict[str, Any]] = []
    for provider in providers:
        for method in methods:
            accuracy, upper_bound, pct_upper_bound = metric_for_level(
                inputs.cells,
                method,
                results[(provider, condition, method, "optimized")].annotations,
                level,
            )
            rows.append(
                {
                    "provider": provider,
                    "method": method,
                    "annotation_accuracy": accuracy,
                    "upper_bound_accuracy": upper_bound,
                    "pct_upper_bound": pct_upper_bound,
                }
            )
    return pd.DataFrame(rows)


def _run_llm_method_heatmap_panel(
    panel_key: str,
    api_keys: Mapping[str, str],
    repository_root: str | Path | None,
    config_path: str | Path | None,
    *,
    force_refresh: bool,
) -> dict[str, Path]:
    root, path, config = _run_context(repository_root, config_path)
    panel = config["panels"][panel_key]
    providers = [str(provider) for provider in config["provider_display_order"]]
    methods = [str(method) for method in config["figure_02_dependency"]["method_display_order"]]
    condition = str(panel["condition"])
    require_api_keys(api_keys, providers, config)

    inputs = load_figure03_inputs(root, path)
    results = ensure_annotations(
        inputs,
        config,
        root,
        api_keys,
        providers=providers,
        conditions=[condition],
        methods=methods,
        marker_states=["optimized"],
        force_refresh=force_refresh,
    )
    level = str(panel["metric_level"])
    table = _llm_method_table(
        inputs,
        results,
        config,
        condition=condition,
        level=level,
    )
    paths = _panel_output_paths(root, panel)
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(paths["csv"], index=False)
    render_llm_method_heatmap(table, paths, config, panel_key=panel_key)
    _write_panel_provenance(
        paths["provenance"],
        panel_key=panel_key,
        config_path=path,
        inputs=inputs,
        annotation_results=results,
        repository_root=root,
        extra={
            "metric_level": level,
            "condition": condition,
            "metric": "100 * annotation accuracy / clustering upper bound",
        },
    )
    return paths


def run_panel_f(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel F's cell-level provider-by-method heatmap."""
    return _run_llm_method_heatmap_panel(
        "panel_f",
        api_keys,
        repository_root,
        config_path,
        force_refresh=force_refresh,
    )


def run_panel_g(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel G's cluster-level provider-by-method heatmap."""
    return _run_llm_method_heatmap_panel(
        "panel_g",
        api_keys,
        repository_root,
        config_path,
        force_refresh=force_refresh,
    )


def _cell_type_accuracy_table(
    inputs: Figure03Inputs,
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    config: Mapping[str, Any],
    *,
    method: str,
    condition: str,
) -> pd.DataFrame:
    providers = [str(provider) for provider in config["provider_display_order"]]
    majority = _majority_reference_series(inputs.cells, method)
    predictions = {
        provider: _annotation_series(
            inputs.cells,
            method,
            results[(provider, condition, method, "optimized")].annotations,
        )
        for provider in providers
    }
    rows: list[dict[str, Any]] = []
    for cell_type in sorted(inputs.cells["truth"].unique()):
        mask = inputs.cells["truth"].eq(cell_type)
        count = int(mask.sum())
        upper_accuracy = float(majority.loc[mask].eq(cell_type).mean())
        for provider in providers:
            absolute_accuracy = float(predictions[provider].loc[mask].eq(cell_type).mean())
            if upper_accuracy > 0.0:
                pct_upper_bound = 100.0 * absolute_accuracy / upper_accuracy
            else:
                pct_upper_bound = 0.0 if absolute_accuracy == 0.0 else float("inf")
            rows.append(
                {
                    "cell_type": str(cell_type),
                    "provider": provider,
                    "cell_count": count,
                    "absolute_accuracy": absolute_accuracy,
                    "absolute_accuracy_pct": 100.0 * absolute_accuracy,
                    "upper_bound_accuracy": upper_accuracy,
                    "pct_upper_bound": pct_upper_bound,
                    # Preserve the raw ratio in CSV; cap only the color scale.
                    "pct_upper_bound_plot": float(np.clip(pct_upper_bound, 0.0, 100.0)),
                }
            )
    return pd.DataFrame(rows)


def _run_cell_type_panel(
    panel_key: str,
    api_keys: Mapping[str, str],
    repository_root: str | Path | None,
    config_path: str | Path | None,
    *,
    force_refresh: bool,
) -> dict[str, Path]:
    root, path, config = _run_context(repository_root, config_path)
    panel = config["panels"][panel_key]
    providers = [str(provider) for provider in config["provider_display_order"]]
    method = str(panel["method"])
    condition = str(panel["condition"])
    require_api_keys(api_keys, providers, config)

    inputs = load_figure03_inputs(root, path)
    results = ensure_annotations(
        inputs,
        config,
        root,
        api_keys,
        providers=providers,
        conditions=[condition],
        methods=[method],
        marker_states=["optimized"],
        force_refresh=force_refresh,
    )
    table = _cell_type_accuracy_table(
        inputs,
        results,
        config,
        method=method,
        condition=condition,
    )
    paths = _panel_output_paths(root, panel)
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(paths["csv"], index=False)
    if panel_key == "panel_h":
        render_cell_type_heatmap(
            table,
            paths,
            config,
            panel_key=panel_key,
            value_column="absolute_accuracy_pct",
            colorbar_label="Annotation Purity (%)",
        )
    else:
        render_cell_type_heatmap(
            table,
            paths,
            config,
            panel_key=panel_key,
            value_column="pct_upper_bound_plot",
            colorbar_label="Upper-Bound Purity (%)",
        )
    raw_ratios = table["pct_upper_bound"].to_numpy(dtype=float)
    raw_over_100 = int((np.isfinite(raw_ratios) & (raw_ratios > 100.0)).sum())
    _write_panel_provenance(
        paths["provenance"],
        panel_key=panel_key,
        config_path=path,
        inputs=inputs,
        annotation_results=results,
        repository_root=root,
        extra={
            "method": method,
            "condition": condition,
            "metric": str(panel["metric"]),
            "ratios_above_100_percent": raw_over_100,
            "plot_color_scale": [0.0, 100.0],
        },
    )
    return paths


def run_panel_h(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel H's absolute Leiden cell-type annotation heatmap."""
    return _run_cell_type_panel(
        "panel_h",
        api_keys,
        repository_root,
        config_path,
        force_refresh=force_refresh,
    )


def run_panel_i(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel I's upper-bound-normalized Leiden cell-type heatmap."""
    return _run_cell_type_panel(
        "panel_i",
        api_keys,
        repository_root,
        config_path,
        force_refresh=force_refresh,
    )


def _reasoning_consensus_table(
    inputs: Figure03Inputs,
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    config: Mapping[str, Any],
    *,
    level: str,
    condition: str,
) -> pd.DataFrame:
    providers = [str(provider) for provider in config["provider_display_order"]]
    methods = [
        str(method) for method in config["figure_02_dependency"]["grouped_bar_method_order"]
    ]
    rows: list[dict[str, Any]] = []
    for method in methods:
        for provider in providers:
            accuracy, upper_bound, pct_upper_bound = metric_for_level(
                inputs.cells,
                method,
                results[(provider, condition, method, "optimized")].annotations,
                level,
            )
            rows.append(
                {
                    "method": method,
                    "series": provider,
                    "annotation_accuracy": accuracy,
                    "upper_bound_accuracy": upper_bound,
                    "pct_upper_bound": pct_upper_bound,
                }
            )
        consensus = _consensus_annotations(
            results,
            config,
            method=method,
            condition=condition,
        )
        accuracy, upper_bound, pct_upper_bound = metric_for_level(
            inputs.cells,
            method,
            consensus,
            level,
        )
        rows.append(
            {
                "method": method,
                "series": "consensus",
                "annotation_accuracy": accuracy,
                "upper_bound_accuracy": upper_bound,
                "pct_upper_bound": pct_upper_bound,
            }
        )
    return pd.DataFrame(rows)


def _run_reasoning_consensus_panel(
    panel_key: str,
    api_keys: Mapping[str, str],
    repository_root: str | Path | None,
    config_path: str | Path | None,
    *,
    force_refresh: bool,
) -> dict[str, Path]:
    root, path, config = _run_context(repository_root, config_path)
    panel = config["panels"][panel_key]
    providers = [str(provider) for provider in config["provider_display_order"]]
    methods = [
        str(method) for method in config["figure_02_dependency"]["grouped_bar_method_order"]
    ]
    condition = str(panel["condition"])
    require_api_keys(api_keys, providers, config)

    inputs = load_figure03_inputs(root, path)
    results = ensure_annotations(
        inputs,
        config,
        root,
        api_keys,
        providers=providers,
        conditions=[condition],
        methods=methods,
        marker_states=["optimized"],
        force_refresh=force_refresh,
    )
    level = str(panel["metric_level"])
    table = _reasoning_consensus_table(
        inputs,
        results,
        config,
        level=level,
        condition=condition,
    )
    paths = _panel_output_paths(root, panel)
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(paths["csv"], index=False)
    sensitivity = _consensus_tie_sensitivity_table(
        inputs,
        results,
        config,
        level=level,
        condition=condition,
        methods=methods,
    )
    sensitivity_path = paths["csv"].with_name(
        f"{paths['csv'].stem}_tie_order_sensitivity.csv"
    )
    sensitivity.to_csv(sensitivity_path, index=False)
    render_grouped_bars(table, paths, config, panel_key=panel_key)
    _write_panel_provenance(
        paths["provenance"],
        panel_key=panel_key,
        config_path=path,
        inputs=inputs,
        annotation_results=results,
        repository_root=root,
        extra={
            "metric_level": level,
            "condition": condition,
            "consensus_tie_priority": config["consensus"]["tie_priority"],
            "consensus_status": config["consensus"]["status"],
            "tie_break_selected_on_evaluation_labels": bool(
                config["consensus"]["tie_break_selected_on_evaluation_labels"]
            ),
            "tie_order_sensitivity_csv": str(
                sensitivity_path.relative_to(root)
            ),
            "tie_order_sensitivity_rows": int(len(sensitivity)),
        },
    )
    return {**paths, "tie_order_sensitivity_csv": sensitivity_path}


def run_panel_j(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel J's cell-level reasoning-provider/consensus bars."""
    return _run_reasoning_consensus_panel(
        "panel_j",
        api_keys,
        repository_root,
        config_path,
        force_refresh=force_refresh,
    )


def run_panel_k(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel K's cluster-level reasoning-provider/consensus bars."""
    return _run_reasoning_consensus_panel(
        "panel_k",
        api_keys,
        repository_root,
        config_path,
        force_refresh=force_refresh,
    )


def _spatial_agreement_cells(
    inputs: Figure03Inputs,
    results: Mapping[tuple[str, str, str, str], AnnotationResult],
    config: Mapping[str, Any],
    *,
    method: str,
    condition: str,
) -> pd.DataFrame:
    """Attach four LLM votes and agreement to the complete spatial cohort."""
    providers = [str(provider) for provider in config["provider_display_order"]]
    cells = inputs.marker_cells.copy()
    for provider in providers:
        cells[f"pred_{provider}"] = _annotation_series(
            cells,
            method,
            results[(provider, condition, method, "optimized")].annotations,
        )
    consensus = _consensus_annotations(
        results,
        config,
        method=method,
        condition=condition,
    )
    cells["pred_consensus"] = _annotation_series(cells, method, consensus)

    cluster_column = f"cluster_{method}"
    vote_agreement_by_cluster: dict[int, float] = {}
    for cluster_id in sorted(cells[cluster_column].unique()):
        cluster_key = str(int(cluster_id))
        votes = [
            results[(provider, condition, method, "optimized")].annotations[cluster_key]
            for provider in providers
        ]
        vote_agreement_by_cluster[int(cluster_id)] = (
            max(Counter(votes).values()) / len(votes)
        )
    cells["agreement_fraction"] = (
        cells[cluster_column].map(vote_agreement_by_cluster).astype(float)
    )
    return cells


def run_panel_l(
    api_keys: Mapping[str, str],
    repository_root: str | Path | None = None,
    config_path: str | Path | None = None,
    *,
    force_refresh: bool = False,
) -> dict[str, Path]:
    """Generate Panel L's low/high spatial LLM-annotation agreement maps."""
    root, path, config = _run_context(repository_root, config_path)
    panel = config["panels"]["panel_l"]
    providers = [str(provider) for provider in config["provider_display_order"]]
    method = str(panel["method"])
    condition = str(panel["condition"])
    require_api_keys(api_keys, providers, config)

    inputs = load_figure03_inputs(root, path)
    results = ensure_annotations(
        inputs,
        config,
        root,
        api_keys,
        providers=providers,
        conditions=[condition],
        methods=[method],
        marker_states=["optimized"],
        force_refresh=force_refresh,
    )
    # Select examples using agreement among the four independent LLM votes.
    # The helper starts from every source cell; reference-based Noise filtering
    # and the derived historical vote cannot affect eligibility or the score.
    cells = _spatial_agreement_cells(
        inputs,
        results,
        config,
        method=method,
        condition=condition,
    )

    examples, metadata = _search_spatial_examples(cells, panel)
    color_map = _load_cell_type_color_map(inputs, root, config)
    paths = _panel_output_paths(root, panel)
    paths["csv"].parent.mkdir(parents=True, exist_ok=True)
    examples.to_csv(paths["csv"], index=False)
    metadata_path = paths["csv"].with_name(f"{paths['csv'].stem}_metadata.csv")
    metadata.to_csv(metadata_path, index=False)
    sensitivity = _consensus_tie_sensitivity_table(
        inputs,
        results,
        config,
        level="cell",
        condition=condition,
        methods=[method],
    )
    sensitivity_path = paths["csv"].with_name(
        f"{paths['csv'].stem}_tie_order_sensitivity.csv"
    )
    sensitivity.to_csv(sensitivity_path, index=False)
    render_panel_l(cells, examples, metadata, color_map, paths, config)
    _write_panel_provenance(
        paths["provenance"],
        panel_key="panel_l",
        config_path=path,
        inputs=inputs,
        annotation_results=results,
        repository_root=root,
        extra={
            "method": method,
            "condition": condition,
            "consensus_tie_priority": config["consensus"]["tie_priority"][method],
            "consensus_status": config["consensus"]["status"],
            "tie_break_selected_on_evaluation_labels": bool(
                config["consensus"]["tie_break_selected_on_evaluation_labels"]
            ),
            "tie_order_sensitivity_csv": str(
                sensitivity_path.relative_to(root)
            ),
            "spatial_agreement_definition": (
                "per-cell modal vote fraction across the four independent LLM "
                "annotations over all B004 cells; reference labels and consensus "
                "excluded from selection"
            ),
            "metadata_csv": str(metadata_path.relative_to(root)),
            "selection_contract": {
                key: panel[key]
                for key in (
                    "target_cells",
                    "cell_tolerance",
                    "random_seed",
                    "candidate_centers_per_file",
                    "radius_scale_factors",
                )
            },
        },
    )
    return {
        **paths,
        "metadata_csv": metadata_path,
        "tie_order_sensitivity_csv": sensitivity_path,
    }
