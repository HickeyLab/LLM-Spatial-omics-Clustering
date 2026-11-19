"""Offline native Astra Batch preparation, admission and submission bookkeeping.

This module deliberately has no HTTP client, credential lookup, credit-purchase
path or live-generation function. An explicit native model is supplied by the
caller; a native dated model ID is never inferred from an OpenRouter slug.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SOURCE_MODEL = "openai/gpt-6-astra"
NATIVE_MODEL_PATTERN = re.compile(r"gpt-6-astra(?:-\d{4}-?\d{2}-?\d{2})?\Z")
SHA256_PATTERN = re.compile(r"[a-f0-9]{64}\Z")
OUTPUT_TOKENS = 32768
ENDPOINT = "/v1/chat/completions"
COMPLETION_WINDOW = "24h"


class AdmissionError(ValueError):
    """A frozen request or admission record is invalid."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_PATTERN.fullmatch(value))


def _native_model(value: Any) -> str:
    if not isinstance(value, str) or not NATIVE_MODEL_PATTERN.fullmatch(value):
        raise AdmissionError("An explicit native Astra model ID is required.")
    return value


def _messages(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) != 2:
        raise AdmissionError("The frozen system/user message pair is required.")
    for message, role in zip(value, ("system", "user")):
        if (not isinstance(message, dict) or set(message) != {"role", "content"}
                or message["role"] != role
                or not isinstance(message["content"], str) or not message["content"]):
            raise AdmissionError("Message roles, content and fields must remain frozen.")
    return deepcopy(value)


def _frozen_common(body: Mapping[str, Any]) -> dict[str, Any]:
    if type(body.get("seed")) is not int or body["seed"] != 42:
        raise AdmissionError("The frozen seed is 42; it cannot be silently omitted.")
    if body.get("response_format") != {"type": "json_object"}:
        raise AdmissionError("The frozen JSON-object response format is required.")
    return {"messages": _messages(body.get("messages")), "seed": 42,
            "response_format": {"type": "json_object"}}


def adapt_astra_request(source: Mapping[str, Any], *, native_model: str) -> dict[str, Any]:
    """Translate only wire names/routing; this does not admit or submit a model."""
    model = _native_model(native_model)
    if not isinstance(source, Mapping):
        raise AdmissionError("The source request must be an object.")
    allowed = {"model", "messages", "max_tokens", "reasoning", "response_format", "seed", "provider"}
    if set(source) - allowed:
        raise AdmissionError("Unexpected source fields would change the frozen contract.")
    if source.get("model") != SOURCE_MODEL:
        raise AdmissionError("The source request is not the frozen Astra model.")
    if source.get("reasoning") != {"effort": "high"}:
        raise AdmissionError("Astra reasoning must remain high.")
    if type(source.get("max_tokens")) is not int or source["max_tokens"] != OUTPUT_TOKENS:
        raise AdmissionError("The frozen combined output ceiling is 32768.")
    if "provider" in source and not isinstance(source["provider"], dict):
        raise AdmissionError("Invalid OpenRouter routing envelope.")
    result = _frozen_common(source)
    result.update(model=model, reasoning_effort="high", max_completion_tokens=OUTPUT_TOKENS)
    return result


def validate_native_request(body: Mapping[str, Any]) -> None:
    if not isinstance(body, Mapping):
        raise AdmissionError("The native request must be an object.")
    expected = {"model", "messages", "max_completion_tokens", "reasoning_effort", "response_format", "seed"}
    if set(body) != expected:
        raise AdmissionError("Native request fields must match the frozen contract exactly.")
    _native_model(body.get("model"))
    _frozen_common(body)
    if body.get("reasoning_effort") != "high":
        raise AdmissionError("Astra reasoning must remain high.")
    if type(body.get("max_completion_tokens")) is not int or body["max_completion_tokens"] != OUTPUT_TOKENS:
        raise AdmissionError("Native output ceiling must preserve reasoning plus visible output.")


def semantic_contract(body: Mapping[str, Any], *, interface: str) -> dict[str, Any]:
    """Hash model-visible inputs/settings; transport and aliases are separate gates."""
    if interface == "openrouter":
        native = adapt_astra_request(body, native_model="gpt-6-astra")
    elif interface == "openai":
        validate_native_request(body)
        native = deepcopy(dict(body))
    else:
        raise AdmissionError("Unknown interface.")
    return {"model_family": "gpt-6-astra", "provider": "openai",
            **{key: native[key] for key in ("messages", "seed", "response_format", "reasoning_effort", "max_completion_tokens")},
            "tools": "omitted", "temperature": "omitted", "top_p": "omitted"}


def adaptation_receipt(source: Mapping[str, Any], native: Mapping[str, Any]) -> dict[str, Any]:
    old = semantic_contract(source, interface="openrouter")
    new = semantic_contract(native, interface="openai")
    return {"schema": "reviewer47.native_astra_translation.v1",
            "source_canonical_sha256": sha256_json(source),
            "native_canonical_sha256": sha256_json(native),
            "source_messages_sha256": sha256_json(source["messages"]),
            "native_messages_sha256": sha256_json(native["messages"]),
            "source_contract_sha256": sha256_json(old),
            "native_contract_sha256": sha256_json(new),
            "model_visible_contract_exact": old == new,
            "model_binding_admitted": False, "execution_enabled": False}


def model_admission_issues(binding: Mapping[str, Any], *, native_model: str) -> list[str]:
    """An evidence-backed binding is required; family-name similarity is not proof."""
    issues = []
    _native_model(native_model)
    if binding.get("admitted") is not True:
        issues.append("native_model_not_admitted")
    if binding.get("native_model") != native_model:
        issues.append("native_model_binding_mismatch")
    inventory = binding.get("supported_native_model_ids", [])
    if not isinstance(inventory, list) or native_model not in inventory:
        issues.append("native_model_not_in_verified_inventory")
    if binding.get("provider") != "openai":
        issues.append("provider_not_openai")
    if not _sha(binding.get("evidence_sha256")):
        issues.append("missing_model_admission_evidence")
    parameter_list = binding.get("supported_parameters", [])
    supported = set(parameter_list) if isinstance(parameter_list, list) and all(isinstance(x, str) for x in parameter_list) else set()
    required = {"reasoning_effort", "seed", "max_completion_tokens", "response_format"}
    if not required <= supported:
        issues.append("frozen_native_parameters_not_admitted")
    return issues


def reuse_decision(source: Mapping[str, Any], native: Mapping[str, Any], *,
                   accepted: Mapping[str, Any], model_binding: Mapping[str, Any],
                   condition: Mapping[str, Any]) -> dict[str, Any]:
    """Conservatively reuse one accepted *same-condition* answer, never another arm."""
    proof = adaptation_receipt(source, native)
    issues = model_admission_issues(model_binding, native_model=native["model"])
    if not proof["model_visible_contract_exact"]:
        issues.append("model_visible_contract_changed")
    if accepted.get("status") != "accepted":
        issues.append("source_output_not_accepted")
    if accepted.get("condition") != dict(condition) or not condition:
        issues.append("scientific_condition_mismatch")
    if not isinstance(accepted.get("provider"), str) or accepted["provider"].lower() != "openai":
        issues.append("accepted_provider_mismatch")
    if accepted.get("source_model") != SOURCE_MODEL:
        issues.append("accepted_model_mismatch")
    if not _sha(accepted.get("response_sha256")):
        issues.append("missing_accepted_response_hash")
    if accepted.get("source_body_sha256") != sha256_json(source):
        issues.append("accepted_request_hash_mismatch")
    if model_binding.get("canonical_equivalence_verified") is not True:
        issues.append("snapshot_equivalence_unverified")
    if (not model_binding.get("source_canonical_model")
            or accepted.get("canonical_model") != model_binding.get("source_canonical_model")):
        issues.append("canonical_snapshot_mapping_mismatch")
    return {**proof, "schema": "reviewer47.native_astra_reuse.v1",
            "reusable": not issues, "issues": issues,
            "scientific_condition_sha256": sha256_json(condition),
            "accepted_response_sha256": accepted.get("response_sha256"),
            "execution_enabled": False}


def make_batch_jsonl(records: Sequence[Mapping[str, Any]], *, native_model: str) -> tuple[bytes, dict[str, Any]]:
    """records contain custom_id and source_body; no credential is accepted."""
    if not records:
        raise AdmissionError("An empty Batch file cannot be prepared.")
    if len(records) > 50000:
        raise AdmissionError("Native Batch files permit at most 50000 request items.")
    ids = []
    lines = []
    translations = []
    for record in records:
        if set(record) != {"custom_id", "source_body"}:
            raise AdmissionError("Unexpected Batch input-record fields.")
        request_id = record["custom_id"]
        if (not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", request_id)
                or request_id in ids):
            raise AdmissionError("Batch request IDs must be unique, nonempty safe identifiers.")
        ids.append(request_id)
        body = adapt_astra_request(record["source_body"], native_model=native_model)
        lines.append(canonical_bytes({"custom_id": request_id, "method": "POST", "url": ENDPOINT, "body": body}))
        translations.append({"custom_id": request_id, **adaptation_receipt(record["source_body"], body)})
    data = b"\n".join(lines) + b"\n"
    if len(data) > 200000000:
        raise AdmissionError("Native Batch file exceeds the conservative 200 MB limit.")
    return data, {"schema": "reviewer47.native_astra_batch.v1", "endpoint": ENDPOINT,
                  "completion_window": COMPLETION_WINDOW, "native_model": native_model,
                  "request_ids": ids, "request_count": len(ids),
                  "input_file_sha256": hashlib.sha256(data).hexdigest(),
                  "translation_proofs": translations, "payment_source": "existing_openai_api_balance",
                  "execution_enabled": False, "jobs_submitted": 0}


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise AdmissionError(f"Missing or invalid {name} timestamp.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdmissionError(f"Invalid {name} timestamp.") from exc
    if result.tzinfo is None:
        raise AdmissionError(f"{name} timestamp needs an explicit timezone.")
    return result.astimezone(timezone.utc)


def _money(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise AdmissionError(f"Invalid {name} amount.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise AdmissionError(f"Invalid {name} amount.") from exc
    if not result.is_finite() or result < 0:
        raise AdmissionError(f"Invalid {name} amount.")
    return result


def credit_preflight(snapshot: Mapping[str, Any], *, reservation_usd: Any,
                     now: datetime | None = None, safety_fraction: Any = "0.20",
                     max_snapshot_age_seconds: int = 900) -> dict[str, Any]:
    """Assess existing credits of *any* source, without implying a hard billing cap.

    Snapshot fields: verified, organization_id, project_id,
    credential_organization_id, credential_project_id, existing_balance_usd,
    pending_usage_usd, other_reservations_usd, observed_at, and either expires_at
    or no_expiration_before_completion=True. No key value belongs in this record.
    A 48-hour validity guard covers the 24-hour Batch window plus billing margin.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise AdmissionError("The preflight clock needs an explicit timezone.")
    now = now.astimezone(timezone.utc)
    reservation = _money(reservation_usd, "reservation")
    safety = _money(safety_fraction, "safety fraction")
    if reservation <= 0 or safety < Decimal("0.20"):
        raise AdmissionError("A positive reservation and at least 20% credit headroom are required.")
    balance = _money(snapshot.get("existing_balance_usd"), "existing balance")
    pending = _money(snapshot.get("pending_usage_usd", "0"), "pending usage")
    elsewhere = _money(snapshot.get("other_reservations_usd", "0"), "other reservations")
    observed = _timestamp(snapshot.get("observed_at"), "observation")
    issues = []
    if snapshot.get("verified") is not True:
        issues.append("credit_snapshot_unverified")
    for key in ("organization_id", "project_id"):
        if not isinstance(snapshot.get(key), str) or not snapshot[key]:
            issues.append("missing_" + key)
        if snapshot.get("credential_" + key) != snapshot.get(key):
            issues.append("credential_" + key + "_mismatch")
    age = (now - observed).total_seconds()
    if age < 0 or age > max_snapshot_age_seconds:
        issues.append("credit_snapshot_not_fresh")
    valid_through = now + timedelta(hours=48)
    if snapshot.get("expires_at") is not None:
        if _timestamp(snapshot["expires_at"], "credit expiry") < valid_through:
            issues.append("credits_expire_before_safety_window")
    elif snapshot.get("no_expiration_before_completion") is not True:
        issues.append("credit_expiry_not_verified")
    usable = balance - pending - elsewhere
    required = reservation * (Decimal(1) + safety)
    if usable < required:
        issues.append("insufficient_existing_credit_headroom")
    return {"schema": "reviewer47.native_astra_credit_preflight.v1", "visibility": "private_financial_preflight", "passed": not issues,
            "issues": issues, "payment_source": "existing_openai_api_balance",
            "credit_source_restricted": False, "organization_sha256": sha256_json(snapshot.get("organization_id")),
            "project_sha256": sha256_json(snapshot.get("project_id")),
            "observed_at": observed.isoformat(), "checked_at": now.isoformat(),
            "credit_validity_required_through": valid_through.isoformat(),
            "existing_balance_usd": str(balance), "pending_usage_usd": str(pending),
            "other_reservations_usd": str(elsewhere), "usable_existing_balance_usd": str(usable),
            "reservation_usd": str(reservation), "required_with_headroom_usd": str(required),
            "provider_enforced_credit_only": False,
            "caveat": "Existing balance can be consumed by other account activity; OpenAI documents no per-request credits-only selector.",
            "new_credit_purchase_authorized": False, "billing_changes_authorized": False,
            "execution_enabled": False}


_SECRET_KEYS = {"api_key", "apikey", "authorization", "token", "access_token", "refresh_token", "client_secret", "secret", "password", "continuation_token", "continuationtoken"}
_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")


def sanitize_for_receipt(value: Any) -> Any:
    """Redact credentials/checkpoints in receipts, never in model-input bodies."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
            result[key] = "[REDACTED]" if normalized in _SECRET_KEYS or normalized.endswith("_api_key") else sanitize_for_receipt(item)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize_for_receipt(x) for x in value]
    if isinstance(value, str):
        return _BEARER_PATTERN.sub("Bearer [REDACTED]", _KEY_PATTERN.sub("[REDACTED]", value))
    return value


def public_credit_admission(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Publication-safe admission proof without account balance or routing IDs."""
    keys = ("schema", "passed", "issues", "payment_source", "credit_source_restricted",
            "checked_at", "reservation_usd", "required_with_headroom_usd",
            "provider_enforced_credit_only", "new_credit_purchase_authorized",
            "billing_changes_authorized", "execution_enabled")
    return {"visibility": "public_admission_summary", **sanitize_for_receipt({key: receipt[key] for key in keys if key in receipt})}


def new_submission_record(manifest: Mapping[str, Any]) -> dict[str, Any]:
    ids = manifest.get("request_ids")
    if (not _sha(manifest.get("input_file_sha256")) or not isinstance(ids, list)
            or not ids or any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids))):
        raise AdmissionError("Invalid sealed Batch manifest.")
    return {"schema": "reviewer47.native_astra_submission.v1", "state": "planned",
            "input_file_sha256": manifest["input_file_sha256"], "request_ids": list(ids),
            "attempts": 0, "batch_id": None, "execution_enabled": False,
            "launch_authorization_id": None, "events": []}


def begin_submission(record: Mapping[str, Any], *, execution_enabled: bool = False,
                     launch_authorization_id: str | None = None,
                     certificate_sha256: str | None = None,
                     credit_receipt: Mapping[str, Any] | None = None,
                     model_admitted: bool = False, now: datetime | None = None) -> dict[str, Any]:
    """Persist the returned pending record *before* an external POST is attempted.

    This function performs no POST. A crash after persistence requires provider
    reconciliation; merely seeing no receipt is never grounds for another POST.
    The live executor must verify the certificate contents and persist this
    transition atomically under its ledger lock. A supplied digest alone is not
    an independent authorization verifier or a security boundary.
    """
    if record.get("state") != "planned" or record.get("attempts") != 0:
        raise AdmissionError("Submission already attempted; reconcile instead of resubmitting.")
    if not execution_enabled or not launch_authorization_id or not _sha(certificate_sha256):
        raise AdmissionError("Execution requires a sealed certificate and separate launch authorization.")
    if not model_admitted or not credit_receipt or credit_receipt.get("passed") is not True:
        raise AdmissionError("Model and existing-credit admission must pass.")
    if credit_receipt.get("payment_source") != "existing_openai_api_balance":
        raise AdmissionError("Incorrect funding route.")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise AdmissionError("The launch clock needs an explicit timezone.")
    checked = _timestamp(credit_receipt.get("checked_at"), "credit check")
    if not 0 <= (now - checked).total_seconds() <= 900:
        raise AdmissionError("The credit preflight must be refreshed before submission.")
    if _timestamp(credit_receipt.get("credit_validity_required_through"), "credit validity") < now + timedelta(hours=24):
        raise AdmissionError("The credit validity window no longer covers Batch completion.")
    result = deepcopy(dict(record))
    result.update(state="submission_pending", attempts=1, execution_enabled=True,
                  launch_authorization_id=launch_authorization_id, certificate_sha256=certificate_sha256)
    result["events"].append({"event": "submission_pending", "input_file_sha256": result["input_file_sha256"]})
    return result


def mark_ambiguous(record: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    if record.get("state") not in {"submission_pending", "ambiguous"}:
        raise AdmissionError("Only an unacknowledged submission can be ambiguous.")
    result = deepcopy(dict(record))
    result["state"] = "ambiguous"
    result["events"].append({"event": "ambiguous", "reason": sanitize_for_receipt(reason)})
    return result


def acknowledge_batch(record: Mapping[str, Any], *, batch_id: str,
                      input_file_sha256: str, request_ids: Sequence[str]) -> dict[str, Any]:
    if record.get("state") not in {"submission_pending", "ambiguous", "submitted"}:
        raise AdmissionError("A Batch cannot be acknowledged before an attempt.")
    if not isinstance(batch_id, str) or not re.fullmatch(r"batch[-_][A-Za-z0-9_-]+", batch_id):
        raise AdmissionError("Invalid native Batch identifier.")
    if record.get("input_file_sha256") != input_file_sha256 or list(request_ids) != record.get("request_ids"):
        raise AdmissionError("Provider receipt does not match the sealed submission.")
    if record.get("batch_id") not in {None, batch_id}:
        raise AdmissionError("A different Batch is already recorded; investigate duplication.")
    result = deepcopy(dict(record))
    if result.get("state") == "submitted":
        return result
    result.update(state="submitted", batch_id=batch_id)
    result["events"].append({"event": "submitted", "batch_id": batch_id})
    return result


def reconcile_submission(record: Mapping[str, Any], *, matches: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if record.get("state") not in {"submission_pending", "ambiguous"}:
        raise AdmissionError("Reconciliation is only for unacknowledged submissions.")
    exact = [x for x in matches if x.get("input_file_sha256") == record.get("input_file_sha256")
             and x.get("request_ids") == record.get("request_ids")]
    if len(exact) == 1:
        item = exact[0]
        return acknowledge_batch(record, batch_id=item["batch_id"],
                                 input_file_sha256=item["input_file_sha256"], request_ids=item["request_ids"])
    reason = "No positive provider match; absence does not prove no paid submission." if not exact else "Multiple provider matches; possible duplicate paid submission."
    return mark_ambiguous(record, reason=reason)


def validate_batch_result_envelope(item: Mapping[str, Any], *, expected_custom_id: str,
                                   expected_native_model: str | None = None) -> dict[str, Any]:
    """Check the native envelope; the caller still applies the strict label parser."""
    if item.get("custom_id") != expected_custom_id or item.get("error") is not None:
        raise AdmissionError("Native Batch item identity/error check failed.")
    response = item.get("response")
    if not isinstance(response, dict) or response.get("status_code") != 200:
        raise AdmissionError("Native Batch item did not return HTTP 200.")
    body = response.get("body")
    if not isinstance(body, dict) or not isinstance(body.get("id"), str):
        raise AdmissionError("Missing native generation receipt.")
    _native_model(body.get("model"))
    if expected_native_model is not None and body.get("model") != expected_native_model:
        raise AdmissionError("The native completion model does not match admission.")
    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise AdmissionError("Expected one native completion.")
    choice = choices[0]
    if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
        raise AdmissionError("Malformed native completion message.")
    message = choice["message"]
    if (choice.get("finish_reason") != "stop" or message.get("refusal")
            or not isinstance(message.get("content"), str) or not message["content"].strip()):
        raise AdmissionError("Nonterminal, refused or empty native completion.")
    usage = body.get("usage")
    if not isinstance(usage, dict):
        raise AdmissionError("Missing native token accounting.")
    for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if type(usage.get(name)) is not int or usage[name] < 0:
            raise AdmissionError("Invalid native token accounting.")
    if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
        raise AdmissionError("Native token totals do not reconcile.")
    if usage["completion_tokens"] > OUTPUT_TOKENS:
        raise AdmissionError("The provider exceeded the frozen combined output ceiling.")
    details = usage.get("completion_tokens_details") or {}
    if not isinstance(details, dict):
        raise AdmissionError("Malformed native completion-token details.")
    reasoning = details.get("reasoning_tokens", 0)
    if type(reasoning) is not int or not 0 <= reasoning <= usage["completion_tokens"]:
        raise AdmissionError("Reasoning tokens are part of completion tokens, not an extra charge.")
    return {"custom_id": expected_custom_id, "generation_id": body["id"],
            "provider_request_id": response.get("request_id"), "model": body.get("model"),
            "system_fingerprint": body.get("system_fingerprint"), "content": message["content"],
            "usage": deepcopy(usage), "reasoning_tokens_already_in_completion": True,
            "requires_strict_label_validation": True}
