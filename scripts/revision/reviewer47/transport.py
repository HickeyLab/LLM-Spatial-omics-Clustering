"""Guarded native OpenAI Batch transport; importing this module makes no calls.

The current checked-in protocol has inference_enabled=false and cannot submit.
There is no automatic launch hook, credential lookup, POST retry, billing change,
or paid fallback. The caller supplies its key and linked organization/project.

Public API: NativeOpenAIClient(api_key, organization_id, project_id, http=None),
inspect_launch(...), submit_native_batch(...), reconcile_native_batch(...), and
collect_native_batch(...). The injected HTTP callable takes (method, url, headers,
body) and returns HttpResponse. GET methods are read-only; POST methods are private
and reached only after inspect_launch passes and pending evidence is durable.

Launch artifacts are strict JSON. The certificate requires passed=true,
status='passed', checked_at/expires_at, native_model, credit_reservation_usd, and
SHA256 fields protocol_sha256, native_jsonl_sha256, manifest_sha256,
model_binding_sha256, credit_snapshot_sha256, pricing_sha256,
pricing_evidence_sha256, strict_parser_sha256. These bind the
*exact file bytes*, not just a path. A separate authorization file requires
explicit_user_launch=true, inference_enabled=true, authorization_id, protocol_id,
certificate_sha256, issued_at/expires_at, credit_cap_usd, ledger_directory, and
scientific_scope={model_families:['openai'], transport:'openai_native_batch',
cohorts:[...], methods:[...], arms:[...], request_ids:[...]}. The manifest must
contain matching request_ids and records with custom_id/cohort/method/arm,
model_family='openai', expected_n (1..75), native_body_sha256,
input_bound_method='utf8_body_bytes_plus_4096', input_token_upper_bound. The latter
must cover len(canonical UTF8 request body)+4096 framing tokens for every request.
pricing_path is an admitted/verified positive USD native Batch rate record with
native_model/provider/transport, input_usd_per_million/output_usd_per_million,
verified_at/source_url/source_evidence_sha256. pricing_evidence_path contains the
archived official source bytes. The certificate binds both files, and the rates
must equal the protocol's pinned rates. The executor independently sums those
input bounds plus the full 32768 combined output ceiling before credit admission.
One authorization covers one exact
native JSONL file; it cannot authorize another model or request set.

Certificates and authorization records are locally reviewed admission artifacts,
not cryptographic signatures. A caller able to rewrite all of them is trusted.
Existing account credits have no per-request credits-only server selector; the
fresh account snapshot, reservations and 20% headroom are local admission checks.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable, Mapping
import urllib.error
import urllib.parse
import urllib.request
import uuid

from . import native_astra as native

BASE_URL = "https://api.openai.com/v1"
STRICT_PARSER_PATH = Path(__file__).resolve().parents[3] / "src/llm_spatial_omics_clustering/revision/annotation47_results.py"
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_PROVIDER_ID = re.compile(r"(?:batch|file)[-_][A-Za-z0-9_-]+\Z")
INPUT_BOUND_METHOD = "utf8_body_bytes_plus_4096"
FRAMING_TOKEN_ALLOWANCE = 4096


def conservative_input_token_bound(body: Mapping[str, Any]) -> int:
    """Reserve one token per body UTF8 byte plus a 4096-token framing margin.

    This intentionally counts routing/scalar JSON overhead as input too; it is
    an upper reservation bound rather than a tokenizer-based usage forecast.
    """
    native.validate_native_request(body)
    return len(native.canonical_bytes(body)) + FRAMING_TOKEN_ALLOWANCE


class TransportError(RuntimeError):
    """Sanitized transport failure; an attempted POST must be reconciled."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


def _strict(text: str) -> Any:
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise native.AdmissionError("Duplicate JSON key.")
            value[key] = item
        return value
    def invalid(_):
        raise native.AdmissionError("Nonfinite JSON value.")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def _artifact(path: str | Path) -> tuple[Any, str]:
    data = Path(path).read_bytes()
    return _strict(data.decode("utf-8")), hashlib.sha256(data).hexdigest()


def _utc(now: datetime | None) -> datetime:
    result = now or datetime.now(timezone.utc)
    if result.tzinfo is None:
        raise native.AdmissionError("The launch clock requires an explicit timezone.")
    return result.astimezone(timezone.utc)


def _window(value, start, end, now, *, fresh=False):
    first = native._timestamp(value.get(start), start)
    last = native._timestamp(value.get(end), end)
    if not first <= now < last or (fresh and (now - first).total_seconds() > 900):
        raise native.AdmissionError("Expired, future or stale admission artifact.")


def _urllib_http(method, url, headers, body):
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    # urllib performs no application-level retry. Redirects are forbidden so that
    # authorization headers cannot be forwarded to a different service.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=120) as response:
            return HttpResponse(response.status, dict(response.headers), response.read())
    except urllib.error.HTTPError as exc:
        return HttpResponse(exc.code, dict(exc.headers), exc.read())


class NativeOpenAIClient:
    """Fixed-host HTTP client; keys are supplied by callers and never persisted."""

    def __init__(self, api_key: str, organization_id: str, project_id: str,
                 http: Callable | None = None):
        if not all(isinstance(x, str) and x and "\n" not in x and "\r" not in x
                   for x in (api_key, organization_id, project_id)):
            raise native.AdmissionError("Explicit key and linked organization/project are required.")
        self._key = api_key
        self.organization_id = organization_id
        self.project_id = project_id
        self._http = http or _urllib_http

    def _safe(self, value):
        if isinstance(value, str):
            return native.sanitize_for_receipt(value.replace(self._key, "[REDACTED]"))
        if isinstance(value, dict):
            return {k: self._safe(v) for k, v in native.sanitize_for_receipt(value).items()}
        if isinstance(value, list):
            return [self._safe(x) for x in value]
        return value

    def _request(self, method, path, body=None, content_type="application/json", *, raw=False):
        if not path.startswith("/") or ".." in path or "://" in path:
            raise native.AdmissionError("Invalid fixed-host API path.")
        headers = {"Authorization": "Bearer " + self._key,
                   "OpenAI-Organization": self.organization_id, "OpenAI-Project": self.project_id}
        if body is not None:
            headers["Content-Type"] = content_type
        try:
            response = self._http(method, BASE_URL + path, headers, body)
        except Exception as exc:
            raise TransportError(self._safe(str(exc))) from None
        if not isinstance(response, HttpResponse) or not isinstance(response.body, bytes):
            raise TransportError("Malformed HTTP response; reconcile any pending POST.")
        if not 200 <= response.status < 300:
            raise TransportError("HTTP " + str(response.status) + ": " + self._safe(response.body.decode("utf-8", errors="replace")[:2000]))
        if self._key.encode() in response.body:
            raise TransportError("Provider response contained a credential; response withheld.")
        if raw:
            return response.body
        try:
            value = _strict(response.body.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise TransportError("Provider response is not strict JSON.") from None
        if not isinstance(value, dict):
            raise TransportError("Provider response must be a JSON object.")
        return value

    @staticmethod
    def _provider_id(value, prefix):
        if not isinstance(value, str) or not _PROVIDER_ID.fullmatch(value) or not value.startswith(prefix):
            raise native.AdmissionError("Invalid native provider identifier.")
        return value

    def list_models(self):
        return self._request("GET", "/models")

    def get_batch(self, batch_id):
        return self._request("GET", "/batches/" + self._provider_id(batch_id, "batch"))

    def list_batches(self, *, after=None):
        suffix = "?limit=100"
        if after is not None:
            suffix += "&after=" + urllib.parse.quote(self._provider_id(after, "batch"), safe="")
        return self._request("GET", "/batches" + suffix)

    def get_file_content(self, file_id):
        return self._request("GET", "/files/" + self._provider_id(file_id, "file") + "/content", raw=True)

    def _upload(self, raw: bytes):
        boundary = "reviewer47_" + uuid.uuid4().hex
        data = (("--" + boundary + '\r\nContent-Disposition: form-data; name="purpose"\r\n\r\nbatch\r\n'
                 + "--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="requests.jsonl"\r\n'
                 + "Content-Type: application/jsonl\r\n\r\n").encode() + raw
                + ("\r\n--" + boundary + "--\r\n").encode())
        return self._request("POST", "/files", data, "multipart/form-data; boundary=" + boundary)

    def _submit(self, value):
        return self._request("POST", "/batches", native.canonical_bytes(value))


def inspect_launch(*, protocol_path, jsonl_path, manifest_path, certificate_path,
                   authorization_path, credit_snapshot_path, model_binding_path,
                   pricing_path, pricing_evidence_path,
                   ledger_dir, client: NativeOpenAIClient, now=None) -> dict[str, Any]:
    """Verify all offline gates without network or writes; raise on any failure."""
    now = _utc(now)
    paths = {"protocol": protocol_path, "manifest": manifest_path, "certificate": certificate_path,
             "authorization": authorization_path, "credit_snapshot": credit_snapshot_path,
             "model_binding": model_binding_path, "pricing": pricing_path}
    artifacts = {name: _artifact(path) for name, path in paths.items()}
    protocol, manifest, cert, auth, snapshot, binding, pricing = (artifacts[x][0] for x in paths)
    if any(not isinstance(x, dict) for x in (protocol, manifest, cert, auth, snapshot, binding, pricing)):
        raise native.AdmissionError("Launch artifacts must be JSON objects.")
    execution = protocol.get("execution", {})
    if execution.get("inference_enabled") is not True or execution.get("automatic_launch") is not False:
        raise native.AdmissionError("Protocol inference is disabled; a newly sealed launch is required.")
    if execution.get("purchase_credits") is not False:
        raise native.AdmissionError("This executor cannot purchase credits.")
    if auth.get("explicit_user_launch") is not True or auth.get("inference_enabled") is not True:
        raise native.AdmissionError("Separate explicit user launch authorization is required.")
    if not isinstance(auth.get("authorization_id"), str) or not auth["authorization_id"]:
        raise native.AdmissionError("Missing launch authorization identifier.")
    if cert.get("passed") is not True or cert.get("status") != "passed":
        raise native.AdmissionError("A passed sealed certificate is required.")
    _window(cert, "checked_at", "expires_at", now, fresh=True)
    _window(auth, "issued_at", "expires_at", now)
    for name in ("protocol", "manifest", "model_binding", "credit_snapshot", "pricing"):
        if cert.get(name + "_sha256") != artifacts[name][1]:
            raise native.AdmissionError("Certificate artifact hash mismatch: " + name)
    if auth.get("certificate_sha256") != artifacts["certificate"][1] or auth.get("protocol_id") != protocol.get("protocol_id"):
        raise native.AdmissionError("Authorization does not bind this exact certificate/protocol.")
    target = Path(ledger_dir).expanduser().absolute()
    if str(target) != auth.get("ledger_directory") or target != target.resolve() or target == Path(target.anchor):
        raise native.AdmissionError("The authorization must bind a nonsymlink ledger directory.")
    raw = Path(jsonl_path).read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    if raw_sha != cert.get("native_jsonl_sha256") or manifest.get("input_file_sha256") != raw_sha:
        raise native.AdmissionError("Exact native JSONL hash mismatch.")
    if hashlib.sha256(STRICT_PARSER_PATH.read_bytes()).hexdigest() != cert.get("strict_parser_sha256"):
        raise native.AdmissionError("Strict result parser differs from the sealed version.")
    model = cert.get("native_model")
    native._native_model(model)
    issues = native.model_admission_issues(binding, native_model=model)
    if issues:
        raise native.AdmissionError("Native model binding admission failed: " + ",".join(issues))
    config = protocol.get("models", {}).get("openai", {})
    required = {"provider": "openai", "transport": "openai_native_batch", "endpoint": native.ENDPOINT,
                "effort": "high", "max_completion_tokens": 32768, "seed": 42,
                "funding": "existing_openai_api_balance", "model_binding_admitted": True}
    if any(config.get(k) != v for k, v in required.items()) or config.get("native_model_candidate") != model:
        raise native.AdmissionError("Enabled runtime model settings differ from the admitted binding.")
    pricing_evidence_sha = hashlib.sha256(Path(pricing_evidence_path).read_bytes()).hexdigest()
    if cert.get("pricing_evidence_sha256") != pricing_evidence_sha or pricing.get("source_evidence_sha256") != pricing_evidence_sha:
        raise native.AdmissionError("Pinned pricing source evidence hash mismatch.")
    if pricing.get("verified") is not True or pricing.get("admitted") is not True:
        raise native.AdmissionError("Pricing rates require verified admission evidence.")
    for key, value in {"native_model": model, "provider": "openai", "transport": "openai_native_batch", "currency": "USD"}.items():
        if pricing.get(key) != value:
            raise native.AdmissionError("Pricing evidence belongs to a different model or transport.")
    source_url = urllib.parse.urlparse(pricing.get("source_url", ""))
    if source_url.scheme != "https" or not source_url.hostname or not (source_url.hostname == "openai.com" or source_url.hostname.endswith(".openai.com")):
        raise native.AdmissionError("Pricing evidence must identify an official HTTPS OpenAI source.")
    verified_at = native._timestamp(pricing.get("verified_at"), "pricing verification")
    if not 0 <= (now - verified_at).total_seconds() <= 86400:
        raise native.AdmissionError("Pricing verification must be refreshed within 24 hours.")
    rates = {}
    for key in ("input_usd_per_million", "output_usd_per_million"):
        rate = native._money(pricing.get(key), key)
        if rate <= 0 or rate != native._money(config.get(key), "pinned " + key):
            raise native.AdmissionError("Verified pricing must be positive and match the protocol's pinned rates.")
        rates[key] = rate
    rows = [_strict(line.decode("utf-8")) for line in raw.splitlines() if line.strip()]
    if not rows or len(rows) > 50000 or len(raw) > 200000000:
        raise native.AdmissionError("Invalid Batch input size.")
    ids = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"custom_id", "method", "url", "body"}:
            raise native.AdmissionError("Malformed native Batch envelope.")
        rid = row["custom_id"]
        if not isinstance(rid, str) or not _ID.fullmatch(rid) or rid in ids:
            raise native.AdmissionError("Duplicate or malformed native request ID.")
        if row["method"] != "POST" or row["url"] != native.ENDPOINT or not isinstance(row["body"], dict) or row["body"].get("model") != model:
            raise native.AdmissionError("Only the admitted native Astra endpoint is permitted.")
        native.validate_native_request(row["body"])
        ids.append(rid)
    if manifest.get("request_ids") != ids or manifest.get("request_count") != len(ids):
        raise native.AdmissionError("Manifest request identity/order mismatch.")
    if manifest.get("native_model") != model or manifest.get("endpoint") != native.ENDPOINT or manifest.get("completion_window") != "24h":
        raise native.AdmissionError("Manifest native model/window mismatch.")
    scope = auth.get("scientific_scope", {})
    if scope.get("model_families") != ["openai"] or scope.get("transport") != "openai_native_batch" or scope.get("request_ids") != ids:
        raise native.AdmissionError("Authorization is not for this exact native Astra request set.")
    records = manifest.get("records")
    if not isinstance(records, list) or any(not isinstance(r, dict) for r in records) or len(records) != len(ids) or [r.get("custom_id") for r in records] != ids:
        raise native.AdmissionError("Scientific scope records are incomplete.")
    for record in records:
        if record.get("model_family") != "openai" or type(record.get("expected_n")) is not int or not 0 < record["expected_n"] <= 75:
            raise native.AdmissionError("Invalid native scientific record.")
        if any(record.get(k) not in scope.get(k + "s", []) for k in ("cohort", "method", "arm")):
            raise native.AdmissionError("Scientific condition lies outside launch authorization.")
    costs = []
    for row, record in zip(rows, records):
        body = row["body"]
        minimum_input_bound = conservative_input_token_bound(body)
        bound = record.get("input_token_upper_bound")
        if (record.get("input_bound_method") != INPUT_BOUND_METHOD
                or type(bound) is not int or bound < minimum_input_bound
                or record.get("native_body_sha256") != native.sha256_json(body)):
            raise native.AdmissionError("Missing, understated or mismatched sealed per-request input token bound.")
        cost = (Decimal(bound) * rates["input_usd_per_million"]
                + Decimal(native.OUTPUT_TOKENS) * rates["output_usd_per_million"]) / Decimal(1000000)
        costs.append({"custom_id": row["custom_id"], "input_token_upper_bound": bound,
                      "combined_output_token_upper_bound": native.OUTPUT_TOKENS,
                      "maximum_charge_usd": str(cost)})
    recomputed_reservation = sum((Decimal(item["maximum_charge_usd"]) for item in costs), Decimal(0))
    reservation = native._money(cert.get("credit_reservation_usd"), "reservation")
    if reservation < recomputed_reservation:
        raise native.AdmissionError("Sealed credit reservation is below the recomputed maximum request charges.")
    if reservation <= 0 or reservation > native._money(auth.get("credit_cap_usd"), "authorization cap") or reservation > native._money(execution.get("openai_credit_cap_usd"), "protocol cap"):
        raise native.AdmissionError("Credit reservation exceeds the approved native credit cap.")
    credit = native.credit_preflight(snapshot, reservation_usd=reservation, now=now)
    if not credit["passed"]:
        raise native.AdmissionError("Credit admission failed: " + ",".join(credit["issues"]))
    if snapshot.get("organization_id") != client.organization_id or snapshot.get("project_id") != client.project_id:
        raise native.AdmissionError("Client routing differs from the linked credit account.")
    return {"passed": True, "raw_jsonl": raw, "protocol_id": protocol["protocol_id"], "manifest": manifest,
            "native_model": model, "credit_preflight": credit, "authorization_id": auth["authorization_id"],
            "recomputed_maximum_charge_usd": str(recomputed_reservation), "per_request_reservations": costs,
            "pricing_evidence_sha256": pricing_evidence_sha,
            "hashes": {name: value[1] for name, value in artifacts.items()}, "native_jsonl_sha256": raw_sha,
            "checked_at": now.isoformat(), "ledger_directory": str(target)}


def _atomic(path: Path, value):
    if path.is_symlink():
        raise native.AdmissionError("Refusing a symlink ledger file.")
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(native.canonical_bytes(value) + b"\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _locked(directory: Path):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory != directory.resolve():
        raise native.AdmissionError("Refusing a symlink ledger directory.")
    fd = os.open(directory / ".ledger.lock", os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield directory / "submission.json"
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)


def _metadata(admission):
    return {"protocol_sha256": admission["hashes"]["protocol"],
            "manifest_sha256": admission["hashes"]["manifest"],
            "native_jsonl_sha256": admission["native_jsonl_sha256"],
            "certificate_sha256": admission["hashes"]["certificate"]}


def submit_native_batch(*, client: NativeOpenAIClient, now=None, **artifact_paths):
    """One guarded upload/create attempt, with durable evidence before each POST.

    A timeout, crash, malformed response or HTTP rejection after POST leaves an
    ambiguous record and blocks automatic resubmission. Calling again for an
    acknowledged batch returns its existing receipt without another POST.
    """
    admission = inspect_launch(client=client, now=now, **artifact_paths)
    with _locked(Path(admission["ledger_directory"])) as path:
        metadata = _metadata(admission)
        if path.exists():
            record, _ = _artifact(path)
            if record.get("metadata") != metadata or record.get("authorization_id") != admission["authorization_id"]:
                raise native.AdmissionError("Ledger belongs to a different sealed launch.")
            if record.get("state") == "submitted":
                return deepcopy(record)
            raise native.AdmissionError("A prior POST is pending or ambiguous; reconcile, never resubmit.")
        record = {"schema": "reviewer47.native_transport.v1", "state": "upload_pending", "metadata": metadata,
                  "authorization_id": admission["authorization_id"], "request_ids": admission["manifest"]["request_ids"],
                  "native_model": admission["native_model"], "credit_reservation_usd": admission["credit_preflight"]["reservation_usd"],
                  "recomputed_maximum_charge_usd": admission["recomputed_maximum_charge_usd"],
                  "per_request_reservations": admission["per_request_reservations"],
                  "pricing_evidence_sha256": admission["pricing_evidence_sha256"],
                  "upload_attempts": 1, "batch_attempts": 0, "batch_id": None, "input_file_id": None,
                  "events": [{"state": "upload_pending", "at": admission["checked_at"]}]}
        _atomic(path, record)
        try:
            upload = client._upload(admission["raw_jsonl"])
            file_id = client._provider_id(upload.get("id"), "file")
            if upload.get("purpose") != "batch":
                raise TransportError("Uploaded file receipt has the wrong purpose.")
            record.update(state="batch_submission_pending", input_file_id=file_id, batch_attempts=1)
            record["events"].append({"state": "batch_submission_pending", "input_file_id": file_id})
            _atomic(path, record)
            receipt = client._submit({"input_file_id": file_id, "endpoint": native.ENDPOINT,
                                      "completion_window": "24h", "metadata": metadata})
            batch_id = client._provider_id(receipt.get("id"), "batch")
            if receipt.get("input_file_id") != file_id or receipt.get("endpoint") != native.ENDPOINT or receipt.get("metadata") != metadata:
                raise TransportError("Native Batch acknowledgement does not match sealed inputs.")
            record.update(state="submitted", batch_id=batch_id)
            record["events"].append({"state": "submitted", "batch_id": batch_id})
            _atomic(path, record)
            return deepcopy(record)
        except Exception as exc:
            record["state"] = "ambiguous"
            record["events"].append({"state": "ambiguous", "reason": client._safe(str(exc))})
            _atomic(path, record)
            raise TransportError("POST outcome requires reconciliation; no automatic resubmission. " + client._safe(str(exc))) from None


def reconcile_native_batch(*, ledger_dir, client: NativeOpenAIClient, max_pages=20):
    """Read-only provider reconciliation; absence never permits another POST."""
    if type(max_pages) is not int or not 1 <= max_pages <= 100:
        raise native.AdmissionError("Invalid reconciliation page bound.")
    directory = Path(ledger_dir).absolute()
    if not (directory / "submission.json").is_file():
        raise native.AdmissionError("Reconciliation requires an existing submission ledger.")
    with _locked(directory) as path:
        record, _ = _artifact(path)
        if record.get("state") == "submitted":
            return record
        if record.get("batch_attempts") != 1 or not record.get("input_file_id"):
            raise native.AdmissionError("No recorded Batch attempt can be reconciled; preserve ambiguous upload.")
        matches = []
        after = None
        complete = False
        for _ in range(max_pages):
            page = client.list_batches(after=after)
            items = page.get("data")
            if not isinstance(items, list):
                raise TransportError("Malformed Batch inventory.")
            for item in items:
                if isinstance(item, dict) and item.get("metadata") == record["metadata"] and item.get("input_file_id") == record["input_file_id"] and item.get("endpoint") == native.ENDPOINT:
                    client._provider_id(item.get("id"), "batch")
                    matches.append(item["id"])
            if page.get("has_more") is False:
                complete = True; break
            if page.get("has_more") is not True or not items or page.get("last_id") == after:
                raise TransportError("Incomplete or malformed Batch pagination.")
            after = client._provider_id(page.get("last_id"), "batch")
        matches = sorted(set(matches))
        if complete and len(matches) == 1:
            record.update(state="submitted", batch_id=matches[0])
            record["events"].append({"state": "submitted", "source": "positive_provider_reconciliation", "batch_id": matches[0]})
        else:
            record["state"] = "ambiguous"
            record["events"].append({"state": "ambiguous", "source": "provider_reconciliation",
                                     "matches": matches, "inventory_complete": complete,
                                     "absence_is_not_non_submission": True})
        _atomic(path, record)
        return deepcopy(record)


def _parser(expected_sha256):
    if hashlib.sha256(STRICT_PARSER_PATH.read_bytes()).hexdigest() != expected_sha256:
        raise native.AdmissionError("Strict parser hash changed; collection is blocked.")
    spec = importlib.util.spec_from_file_location("reviewer47_frozen_result_parser", STRICT_PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_native_batch(*, client: NativeOpenAIClient, batch_id: str, manifest: Mapping,
                         strict_parser_sha256: str, expected_metadata: Mapping,
                         expected_input_file_id: str):
    """GET-only collection; preserve valid items, and count invalid/missing as missing.

    This returns evidence without writing or retrying generations. Duplicate
    custom IDs are rejected as a whole item even if their labels agree.
    """
    parser = _parser(strict_parser_sha256)
    ids = manifest.get("request_ids")
    records = manifest.get("records")
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)) or not isinstance(records, list) or any(not isinstance(r, dict) for r in records) or [r.get("custom_id") for r in records] != ids:
        raise native.AdmissionError("Collection requires exact unique scientific manifest IDs.")
    metadata_keys = {"protocol_sha256", "manifest_sha256", "native_jsonl_sha256", "certificate_sha256"}
    if not isinstance(expected_metadata, Mapping) or set(expected_metadata) != metadata_keys or any(not native._sha(x) for x in expected_metadata.values()):
        raise native.AdmissionError("Collection requires the sealed submission metadata receipt.")
    client._provider_id(expected_input_file_id, "file")
    for r in records:
        if type(r.get("expected_n")) is not int or not 0 < r["expected_n"] <= 75:
            raise native.AdmissionError("Invalid scientific query count.")
    native._native_model(manifest.get("native_model"))
    batch = client.get_batch(batch_id)
    if batch.get("id") != batch_id or batch.get("input_file_id") != expected_input_file_id or batch.get("endpoint") != native.ENDPOINT or batch.get("metadata") != dict(expected_metadata):
        raise native.AdmissionError("Batch collection identity differs from the submission receipt.")
    candidates = {rid: [] for rid in ids}
    errors, file_hashes = [], {}
    for key in ("output_file_id", "error_file_id"):
        if not batch.get(key):
            continue
        raw = client.get_file_content(batch[key])
        file_hashes[key] = hashlib.sha256(raw).hexdigest()
        for lineno, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = parser.strict_json(line.decode("utf-8"))
                rid = item.get("custom_id") if isinstance(item, dict) else None
                if rid not in candidates:
                    raise ValueError("Unknown or missing custom_id")
                candidates[rid].append((item, hashlib.sha256(line).hexdigest()))
            except (ValueError, UnicodeError, TypeError) as exc:
                errors.append({"file": key, "line": lineno, "issue": client._safe(str(exc)), "raw_sha256": hashlib.sha256(line).hexdigest()})
    results = []
    for record in records:
        rid, count = record["custom_id"], record["expected_n"]
        result = {"custom_id": rid, "status": "missing", "labels": [None] * count,
                  "planned_predictions": count, "accepted_predictions": 0}
        values = candidates[rid]
        # Accounting evidence is retained even when scientific acceptance fails.
        # Reasoning tokens remain part of completion_tokens, not a second charge.
        result["attempt_evidence"] = []
        for item, raw_sha in values:
            response = item.get("response") if isinstance(item.get("response"), dict) else {}
            body = response.get("body") if isinstance(response.get("body"), dict) else {}
            choices = body.get("choices")
            first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
            result["attempt_evidence"].append(client._safe({"raw_sha256": raw_sha,
                "provider_request_id": response.get("request_id"), "http_status": response.get("status_code"),
                "generation_id": body.get("id"), "model": body.get("model"), "usage": body.get("usage"),
                "finish_reason": first.get("finish_reason"), "error": item.get("error")}))
        if len(values) > 1:
            result.update(status="invalid", issue="Duplicate returned custom_id", raw_sha256=[x[1] for x in values])
        elif len(values) == 1:
            item, raw_sha = values[0]
            result["raw_sha256"] = raw_sha
            try:
                evidence = native.validate_batch_result_envelope(item, expected_custom_id=rid, expected_native_model=manifest["native_model"])
                labels = parser.parse_labels(evidence.pop("content"), count)
                result.update(status="accepted", labels=labels, accepted_predictions=count, evidence=evidence)
            except (ValueError, TypeError, KeyError) as exc:
                result.update(status="invalid", issue=client._safe(str(exc)))
        results.append(result)
    return {"schema": "reviewer47.native_collection.v1", "batch_id": batch_id,
            "provider_status": batch.get("status"), "provider_terminal": batch.get("status") in {"completed", "failed", "expired", "cancelled"},
            "file_sha256": file_hashes, "strict_parser_sha256": strict_parser_sha256,
            "request_count": len(ids), "accepted_request_count": sum(r["status"] == "accepted" for r in results),
            "planned_predictions": sum(r["planned_predictions"] for r in results),
            "accepted_predictions": sum(r["accepted_predictions"] for r in results),
            "results": results, "collection_errors": errors, "new_generation_calls": 0}
