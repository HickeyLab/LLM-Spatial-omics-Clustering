"""Mock-only tests for launch gates, durable POST evidence and strict collection."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/revision"))
from reviewer47 import native_astra as n
from reviewer47 import transport as t

NOW = datetime(2026, 11, 10, 23, 0, tzinfo=timezone.utc)
KEY = "unit-test-credential-never-persist"


def json_bytes(value):
    return n.canonical_bytes(value) + b"\n"


def response(value, status=200):
    return t.HttpResponse(status, {}, json_bytes(value))


def result(rid="case-1", content='{"a":[{"i":0,"l":7}]}'):
    return {"custom_id": rid, "error": None,
            "response": {"status_code": 200, "request_id": "req-native", "body": {
                "id": "chatcmpl-native", "model": "gpt-6-astra",
                "choices": [{"finish_reason": "stop", "message": {"content": content, "refusal": None}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 12, "total_tokens": 32,
                          "completion_tokens_details": {"reasoning_tokens": 8}}}}}


class Fixture:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.ledger = self.root / "ledger"
        self.protocol = {"protocol_id": "unit-test-protocol", "execution": {
            "inference_enabled": True, "automatic_launch": False,
            "purchase_credits": False, "openai_credit_cap_usd": "10.00"},
            "models": {"openai": {"native_model_candidate": "gpt-6-astra", "provider": "openai",
                "transport": "openai_native_batch", "endpoint": n.ENDPOINT, "effort": "high",
                "max_completion_tokens": 32768, "seed": 42, "funding": "existing_openai_api_balance",
                "model_binding_admitted": True, "input_usd_per_million": "5.00", "output_usd_per_million": "25.00"}}}
        source = {"model": "openai/gpt-6-astra", "messages": [
            {"role": "system", "content": "Frozen instructions"},
            {"role": "user", "content": '{"x":[[1,2]]}'}],
            "max_tokens": 32768, "reasoning": {"effort": "high"},
            "seed": 42, "response_format": {"type": "json_object"}}
        self.raw, self.manifest = n.make_batch_jsonl([{"custom_id": "case-1", "source_body": source}], native_model="gpt-6-astra")
        self.manifest["records"] = [{"custom_id": "case-1", "cohort": "B004", "method": "leiden",
                                    "arm": "all_means", "model_family": "openai", "expected_n": 1}]
        body = json.loads(self.raw)["body"]
        self.manifest["records"][0].update(input_bound_method=t.INPUT_BOUND_METHOD,
            input_token_upper_bound=len(n.canonical_bytes(body)) + t.FRAMING_TOKEN_ALLOWANCE,
            native_body_sha256=n.sha256_json(body))
        self.binding = {"admitted": True, "native_model": "gpt-6-astra", "provider": "openai",
            "supported_native_model_ids": ["gpt-6-astra"], "evidence_sha256": "a" * 64,
            "supported_parameters": ["reasoning_effort", "seed", "max_completion_tokens", "response_format"]}
        self.snapshot = {"verified": True, "organization_id": "org-test", "project_id": "proj-test",
            "credential_organization_id": "org-test", "credential_project_id": "proj-test",
            "existing_balance_usd": "100.00", "pending_usage_usd": "3.00", "other_reservations_usd": "4.00",
            "observed_at": NOW.isoformat(), "expires_at": (NOW + timedelta(days=5)).isoformat()}
        self.price_evidence = b"Offline fixture of reviewed OpenAI Batch rates: input 5 output 25 USD per million."
        self.pricing = {"admitted": True, "verified": True, "native_model": "gpt-6-astra", "provider": "openai",
            "transport": "openai_native_batch", "currency": "USD", "input_usd_per_million": "5.00",
            "output_usd_per_million": "25.00", "verified_at": NOW.isoformat(),
            "source_url": "https://developers.openai.com/api/docs/models/gpt-6-astra",
            "source_evidence_sha256": hashlib.sha256(self.price_evidence).hexdigest()}
        self.certificate = {"passed": True, "status": "passed", "native_model": "gpt-6-astra",
            "credit_reservation_usd": "5.00", "checked_at": NOW.isoformat(),
            "expires_at": (NOW + timedelta(minutes=15)).isoformat(),
            "strict_parser_sha256": hashlib.sha256(t.STRICT_PARSER_PATH.read_bytes()).hexdigest()}
        self.authorization = {"explicit_user_launch": True, "inference_enabled": True,
            "authorization_id": "user-launch-1", "protocol_id": "unit-test-protocol",
            "issued_at": NOW.isoformat(), "expires_at": (NOW + timedelta(minutes=15)).isoformat(),
            "credit_cap_usd": "10.00", "ledger_directory": str(self.ledger),
            "scientific_scope": {"model_families": ["openai"], "transport": "openai_native_batch",
                "cohorts": ["B004"], "methods": ["leiden"], "arms": ["all_means"], "request_ids": ["case-1"]}}
        self.paths = {name + "_path": self.root / (name + ".json") for name in (
            "protocol", "manifest", "certificate", "authorization", "credit_snapshot", "model_binding", "pricing")}
        self.paths["pricing_evidence_path"] = self.root / "pricing-source.txt"
        self.paths.update(jsonl_path=self.root / "native.jsonl", ledger_dir=self.ledger)
        self.save()

    def save(self):
        self.paths["jsonl_path"].write_bytes(self.raw)
        self.paths["pricing_evidence_path"].write_bytes(self.price_evidence)
        for name, value in (("protocol", self.protocol), ("manifest", self.manifest),
                            ("credit_snapshot", self.snapshot), ("model_binding", self.binding), ("pricing", self.pricing)):
            self.paths[name + "_path"].write_bytes(json_bytes(value))
            self.certificate[name + "_sha256"] = hashlib.sha256(json_bytes(value)).hexdigest()
        self.certificate["native_jsonl_sha256"] = hashlib.sha256(self.raw).hexdigest()
        self.certificate["pricing_evidence_sha256"] = hashlib.sha256(self.price_evidence).hexdigest()
        self.paths["certificate_path"].write_bytes(json_bytes(self.certificate))
        self.authorization["certificate_sha256"] = hashlib.sha256(json_bytes(self.certificate)).hexdigest()
        self.paths["authorization_path"].write_bytes(json_bytes(self.authorization))

    def record(self):
        return json.loads((self.ledger / "submission.json").read_text())


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = Fixture(self.temp.name)
        self.calls = []
        self.client = t.NativeOpenAIClient(KEY, "org-test", "proj-test", http=self.http)

    def http(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        self.assertEqual(headers["Authorization"], "Bearer " + KEY)
        ledger = self.f.record()  # Evidence is already durable at the mock POST.
        if url.endswith("/files"):
            self.assertEqual(ledger["state"], "upload_pending")
            self.assertEqual(ledger["upload_attempts"], 1)
            self.assertIn(self.f.raw, body)
            return response({"id": "file-test", "purpose": "batch"})
        self.assertTrue(url.endswith("/batches"))
        self.assertEqual(ledger["state"], "batch_submission_pending")
        self.assertEqual(ledger["batch_attempts"], 1)
        value = json.loads(body)
        self.assertEqual(value["completion_window"], "24h")
        return response({"id": "batch-test", "input_file_id": "file-test", "endpoint": n.ENDPOINT,
                         "metadata": value["metadata"]})

    def inspect(self):
        return t.inspect_launch(client=self.client, now=NOW, **self.f.paths)

    def submit(self):
        return t.submit_native_batch(client=self.client, now=NOW, **self.f.paths)

    def test_inspection_has_no_http_or_writes(self):
        self.assertTrue(self.inspect()["passed"])
        self.assertEqual(self.calls, [])
        self.assertFalse(self.f.ledger.exists())

    def test_actual_checked_in_protocol_is_disabled(self):
        self.f.paths["protocol_path"] = ROOT / "configs/reviewer_annotation47_credit_batch_v1.json"
        with self.assertRaisesRegex(n.AdmissionError, "disabled"):
            self.submit()
        self.assertEqual(self.calls, [])
        self.assertFalse(self.f.ledger.exists())

    def test_explicit_authorization_not_key_presence_required(self):
        self.f.authorization["explicit_user_launch"] = False; self.f.save()
        with self.assertRaisesRegex(n.AdmissionError, "explicit user"):
            self.submit()
        self.assertEqual(self.calls, [])

    def test_exact_certificate_hash_binding(self):
        for name in ("protocol", "manifest", "model_binding", "credit_snapshot", "pricing"):
            with self.subTest(name=name):
                self.f.save()
                path = self.f.paths[name + "_path"]
                path.write_bytes(path.read_bytes() + b" ")
                with self.assertRaisesRegex(n.AdmissionError, "hash mismatch"):
                    self.submit()
        self.assertEqual(self.calls, [])

    def test_recomputed_reservation_covers_full_output_and_conservative_input(self):
        from decimal import Decimal
        admission = self.inspect()
        charge = admission["per_request_reservations"][0]
        self.assertEqual(charge["combined_output_token_upper_bound"], 32768)
        self.assertGreater(Decimal(admission["recomputed_maximum_charge_usd"]), Decimal("0.8192"))
        body = json.loads(self.f.raw)["body"]
        expected = (Decimal(len(n.canonical_bytes(body)) + 4096) * 5 + Decimal(32768) * 25) / Decimal(1000000)
        self.assertEqual(Decimal(admission["recomputed_maximum_charge_usd"]), expected)

    def test_resigned_low_reservation_and_caps_cannot_bypass_request_math(self):
        self.f.certificate["credit_reservation_usd"] = "0.01"
        self.f.authorization["credit_cap_usd"] = "0.02"
        self.f.protocol["execution"]["openai_credit_cap_usd"] = "0.02"
        self.f.save()  # Rebind every artifact exactly; hashes alone cannot admit it.
        with self.assertRaisesRegex(n.AdmissionError, "recomputed maximum"):
            self.submit()
        self.assertEqual(self.calls, [])
        self.assertFalse(self.f.ledger.exists())

    def test_missing_understated_or_mismatched_input_bounds_rejected(self):
        for key, value in (("input_token_upper_bound", 1), ("input_token_upper_bound", True),
                           ("input_bound_method", "estimate"), ("native_body_sha256", "a" * 64)):
            with self.subTest(key=key, value=value):
                old = deepcopy(self.f.manifest["records"][0])
                self.f.manifest["records"][0][key] = value; self.f.save()
                with self.assertRaisesRegex(n.AdmissionError, "input token bound"):
                    self.submit()
                self.f.manifest["records"][0] = old
        self.assertEqual(self.calls, [])

    def test_zero_negative_or_unverified_prices_rejected_even_when_resealed(self):
        cases = [("input_usd_per_million", "0"), ("output_usd_per_million", "0"),
                 ("output_usd_per_million", "-1"), ("verified", False), ("admitted", False)]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                old = deepcopy(self.f.pricing)
                self.f.pricing[key] = value
                if key.endswith("_per_million"):
                    self.f.protocol["models"]["openai"][key] = value
                self.f.save()
                with self.assertRaises(n.AdmissionError): self.submit()
                self.f.pricing = old
                for rate in ("input_usd_per_million", "output_usd_per_million"):
                    self.f.protocol["models"]["openai"][rate] = old[rate]
        self.assertEqual(self.calls, [])

    def test_pricing_route_source_snapshot_and_rate_mismatch_rejected(self):
        for key, value in (("transport", "openrouter_batch"), ("native_model", "other"),
                           ("source_url", "https://openai.com.attacker.test/pricing"),
                           ("source_evidence_sha256", "b" * 64),
                           ("verified_at", (NOW - timedelta(hours=25)).isoformat()),
                           ("output_usd_per_million", "0.01")):
            with self.subTest(key=key):
                old = deepcopy(self.f.pricing); self.f.pricing[key] = value; self.f.save()
                with self.assertRaises(n.AdmissionError): self.submit()
                self.f.pricing = old
        self.assertEqual(self.calls, [])

    def test_modified_archived_pricing_evidence_is_rejected(self):
        self.f.paths["pricing_evidence_path"].write_bytes(b"unbound rates")
        with self.assertRaisesRegex(n.AdmissionError, "pricing source evidence hash"):
            self.submit()
        self.assertEqual(self.calls, [])

    def test_jsonl_tampering_rejected(self):
        self.f.paths["jsonl_path"].write_bytes(self.f.raw + b"\n")
        with self.assertRaisesRegex(n.AdmissionError, "JSONL hash"):
            self.submit()
        self.assertEqual(self.calls, [])

    def test_bound_parser_must_match(self):
        self.f.certificate["strict_parser_sha256"] = "a" * 64; self.f.save()
        with self.assertRaisesRegex(n.AdmissionError, "parser"):
            self.submit()

    def test_frozen_model_settings_must_match(self):
        self.f.protocol["models"]["openai"]["effort"] = "max"; self.f.save()
        with self.assertRaisesRegex(n.AdmissionError, "settings"):
            self.submit()

    def test_native_binding_must_be_admitted(self):
        self.f.binding["admitted"] = False; self.f.save()
        with self.assertRaisesRegex(n.AdmissionError, "admission failed"):
            self.submit()

    def test_scope_cannot_expand_model_or_arm(self):
        for key, value in (("model_families", ["openai", "google"]), ("arms", ["other"]), ("request_ids", ["wrong"])):
            with self.subTest(key=key):
                old = deepcopy(self.f.authorization["scientific_scope"])
                self.f.authorization["scientific_scope"][key] = value; self.f.save()
                with self.assertRaises(n.AdmissionError):
                    self.submit()
                self.f.authorization["scientific_scope"] = old

    def test_all_caps_and_credit_headroom_enforced(self):
        cases = [("cap", "4.99"), ("balance", "12.99"), ("pending", "96.00"), ("expiry", NOW.isoformat()),
                 ("stale", (NOW - timedelta(minutes=16)).isoformat())]
        for key, value in cases:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                self.f = Fixture(directory)
                if key == "cap": self.f.authorization["credit_cap_usd"] = value
                elif key == "balance": self.f.snapshot["existing_balance_usd"] = value
                elif key == "pending": self.f.snapshot["pending_usage_usd"] = value
                elif key == "expiry": self.f.snapshot["expires_at"] = value
                else: self.f.snapshot["observed_at"] = value
                self.f.save()
                with self.assertRaises(n.AdmissionError): self.submit()
        self.assertEqual(self.calls, [])

    def test_different_account_and_ledger_rejected(self):
        self.client.project_id = "proj-other"
        with self.assertRaisesRegex(n.AdmissionError, "routing"):
            self.submit()
        self.client.project_id = "proj-test"
        self.f.paths["ledger_dir"] = self.f.root / "other-ledger"
        with self.assertRaisesRegex(n.AdmissionError, "ledger"):
            self.submit()

    def test_expired_launch_rejected(self):
        self.f.authorization["expires_at"] = NOW.isoformat(); self.f.save()
        with self.assertRaisesRegex(n.AdmissionError, "Expired"):
            self.submit()

    def test_duplicate_ids_and_changed_request_settings_rejected(self):
        for duplicate in (True, False):
            with self.subTest(duplicate=duplicate):
                f = Fixture(self.temp.name)
                self.f = f
                row = json.loads(f.raw)
                if duplicate: f.raw += f.raw
                else:
                    row["body"]["seed"] = 43; f.raw = json_bytes(row)
                f.manifest["input_file_sha256"] = hashlib.sha256(f.raw).hexdigest()
                f.save()
                with self.assertRaises(n.AdmissionError): self.submit()

    def test_atomic_pending_then_single_upload_batch_and_idempotent_receipt(self):
        receipt = self.submit()
        self.assertEqual(receipt["state"], "submitted")
        self.assertEqual(receipt["batch_id"], "batch-test")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.submit(), receipt)
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn(KEY, (self.f.ledger / "submission.json").read_text())

    def test_ambiguous_batch_timeout_blocks_all_post_retries_and_redacts_key(self):
        original = self.client._http
        def timeout(method, url, headers, body):
            if url.endswith("/batches"):
                self.calls.append((method, url, headers, body))
                self.assertEqual(self.f.record()["state"], "batch_submission_pending")
                raise TimeoutError("timeout with " + KEY)
            return original(method, url, headers, body)
        self.client._http = timeout
        with self.assertRaisesRegex(t.TransportError, "reconciliation") as raised:
            self.submit()
        self.assertNotIn(KEY, str(raised.exception))
        self.assertEqual(self.f.record()["state"], "ambiguous")
        self.assertNotIn(KEY, (self.f.ledger / "submission.json").read_text())
        with self.assertRaisesRegex(n.AdmissionError, "reconcile"):
            self.submit()
        self.assertEqual(len(self.calls), 2)

    def test_upload_http_error_is_not_retried(self):
        self.client._http = lambda *args: response({"error": "denied"}, 429)
        with self.assertRaises(t.TransportError): self.submit()
        self.assertEqual(self.f.record()["state"], "ambiguous")
        with self.assertRaises(n.AdmissionError): self.submit()
        self.assertEqual(self.f.record()["upload_attempts"], 1)

    def test_positive_full_inventory_reconciles_without_post(self):
        self.submit()
        record = self.f.record(); record["state"] = "ambiguous"; record["batch_id"] = None
        t._atomic(self.f.ledger / "submission.json", record)
        before = len(self.calls)
        def inventory(method, url, headers, body):
            self.assertEqual(method, "GET")
            return response({"data": [{"id": "batch-test", "input_file_id": "file-test",
                "endpoint": n.ENDPOINT, "metadata": record["metadata"]}], "has_more": False})
        self.client._http = inventory
        answer = t.reconcile_native_batch(ledger_dir=self.f.ledger, client=self.client)
        self.assertEqual(answer["state"], "submitted")
        self.assertEqual(answer["batch_id"], "batch-test")
        self.assertEqual(len(self.calls), before)

    def test_no_inventory_match_never_resets_to_planned(self):
        self.submit()
        record = self.f.record(); record["state"] = "ambiguous"; record["batch_id"] = None
        t._atomic(self.f.ledger / "submission.json", record)
        self.client._http = lambda *args: response({"data": [], "has_more": False})
        answer = t.reconcile_native_batch(ledger_dir=self.f.ledger, client=self.client)
        self.assertEqual(answer["state"], "ambiguous")
        with self.assertRaises(n.AdmissionError): self.submit()


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.f = Fixture(self.temp.name)
        self.output = json_bytes(result())
        self.calls = []
        self.metadata = {k: "a" * 64 for k in ("protocol_sha256", "manifest_sha256", "native_jsonl_sha256", "certificate_sha256")}
        self.batch = {"id": "batch-test", "endpoint": n.ENDPOINT, "status": "completed", "output_file_id": "file-output",
                      "input_file_id": "file-input", "metadata": self.metadata}
        self.client = t.NativeOpenAIClient(KEY, "org-test", "proj-test", http=self.http)

    def http(self, method, url, headers, body):
        self.calls.append((method, url))
        self.assertEqual(method, "GET")
        if url.endswith("/batches/batch-test"): return response(self.batch)
        return t.HttpResponse(200, {}, self.output)

    def collect(self):
        return t.collect_native_batch(client=self.client, batch_id="batch-test", manifest=self.f.manifest,
            strict_parser_sha256=self.f.certificate["strict_parser_sha256"],
            expected_metadata=self.metadata, expected_input_file_id="file-input")

    def test_exact_join_and_strict_labels_are_accepted_get_only(self):
        answer = self.collect()
        self.assertEqual(answer["accepted_request_count"], 1)
        self.assertEqual(answer["results"][0]["labels"], [7])
        self.assertEqual(answer["new_generation_calls"], 0)
        self.assertFalse(self.f.ledger.exists())
        self.assertTrue(answer["results"][0]["evidence"]["reasoning_tokens_already_in_completion"])

    def test_duplicate_returned_ids_invalidate_entire_item(self):
        self.output += self.output
        answer = self.collect()
        self.assertEqual(answer["accepted_request_count"], 0)
        self.assertEqual(answer["results"][0]["status"], "invalid")
        self.assertEqual(answer["results"][0]["labels"], [None])
        self.assertEqual(answer["planned_predictions"], 1)

    def test_invalid_labels_truncation_refusal_and_wrong_native_model_stay_missing(self):
        for change in ("duplicate-key", "bad-label", "wrong-type", "truncated", "refusal", "model"):
            with self.subTest(change=change):
                item = result(); body = item["response"]["body"]
                if change == "duplicate-key": body["choices"][0]["message"]["content"] = '{"a":[],"a":[]}'
                elif change == "bad-label": body["choices"][0]["message"]["content"] = '{"a":[{"i":0,"l":28}]}'
                elif change == "wrong-type": body["choices"][0]["message"]["content"] = '{"a":[{"i":0,"l":true}]}'
                elif change == "truncated": body["choices"][0]["finish_reason"] = "length"
                elif change == "refusal": body["choices"][0]["message"]["refusal"] = "refused"
                else: body["model"] = "gpt-6.1-sol"
                self.output = json_bytes(item)
                answer = self.collect()
                self.assertEqual(answer["accepted_request_count"], 0)
                self.assertEqual(answer["results"][0]["labels"], [None])
                self.assertEqual(answer["results"][0]["attempt_evidence"][0]["usage"]["completion_tokens"], 12)

    def test_collection_requires_exact_submitted_file_and_metadata(self):
        self.batch["input_file_id"] = "file-unrelated"
        with self.assertRaisesRegex(n.AdmissionError, "identity"):
            self.collect()
        self.batch["input_file_id"] = "file-input"
        self.batch["metadata"] = {}
        with self.assertRaisesRegex(n.AdmissionError, "identity"):
            self.collect()

    def test_missing_unknown_and_malformed_output_do_not_shrink_denominator(self):
        self.output = b'{"x":NaN}\n' + json_bytes(result("unknown"))
        answer = self.collect()
        self.assertEqual(answer["planned_predictions"], 1)
        self.assertEqual(answer["accepted_predictions"], 0)
        self.assertEqual(len(answer["collection_errors"]), 2)

    def test_inflight_batch_is_not_reported_completed(self):
        self.batch.update(status="in_progress", output_file_id=None)
        answer = self.collect()
        self.assertFalse(answer["provider_terminal"])
        self.assertEqual(answer["results"][0]["status"], "missing")

    def test_secret_in_response_withheld_and_read_only_inventory(self):
        self.output = KEY.encode()
        with self.assertRaisesRegex(t.TransportError, "credential"):
            self.collect()
        self.client._http = lambda *args: response({"data": []})
        self.assertEqual(self.client.list_models(), {"data": []})


if __name__ == "__main__":
    unittest.main()
