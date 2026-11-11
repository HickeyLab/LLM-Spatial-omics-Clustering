"""Native-credit Astra preparation must not change the scientific request."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "revision"))
from reviewer47 import native_astra as n

NOW = datetime(2026, 11, 10, 23, 0, tzinfo=timezone.utc)
H = "a" * 64


def source_body():
    return {"model": "openai/gpt-6-astra", "max_tokens": 32768,
            "reasoning": {"effort": "high"}, "seed": 42,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": "Return only the frozen JSON labels."},
                         {"role": "user", "content": '{"query_case_id":[0],"means":[[1000,-250]]}'}]}


def admitted_binding():
    return {"native_model": "gpt-6-astra", "admitted": True,
            "supported_native_model_ids": ["gpt-6-astra"], "provider": "openai",
            "supported_parameters": ["reasoning_effort", "seed", "max_completion_tokens", "response_format"],
            "source_canonical_model": "openai/gpt-6-astra-20260903",
            "canonical_equivalence_verified": True, "evidence_sha256": H}


def credit_snapshot():
    return {"verified": True, "organization_id": "org-example", "project_id": "proj-example",
            "credential_organization_id": "org-example", "credential_project_id": "proj-example",
            "existing_balance_usd": "200.00", "pending_usage_usd": "10.00",
            "other_reservations_usd": "5.00", "observed_at": NOW.isoformat(),
            "expires_at": (NOW + timedelta(days=10)).isoformat(),
            "credit_source": "previously_purchased"}


def passing_credit():
    return n.credit_preflight(credit_snapshot(), reservation_usd="60.00", now=NOW)


def batch_manifest():
    _, manifest = n.make_batch_jsonl([{"custom_id": "request-1", "source_body": source_body()}],
                                    native_model="gpt-6-astra")
    return manifest


def pending_record():
    return n.begin_submission(n.new_submission_record(batch_manifest()),
                              execution_enabled=True, launch_authorization_id="explicit-launch-1",
                              certificate_sha256=H, credit_receipt=passing_credit(),
                              model_admitted=True, now=NOW)


def result_item():
    return {"custom_id": "request-1", "error": None,
            "response": {"status_code": 200, "request_id": "req-provider-1", "body": {
                "id": "chatcmpl-example", "model": "gpt-6-astra", "system_fingerprint": "fp-example",
                "choices": [{"finish_reason": "stop", "message": {
                    "content": '{"a":[{"i":0,"l":7}]}', "refusal": None}}],
                "usage": {"prompt_tokens": 25, "completion_tokens": 13, "total_tokens": 38,
                          "completion_tokens_details": {"reasoning_tokens": 10}}}}}


class NativeRequestTests(unittest.TestCase):
    def test_exact_wire_translation_without_new_content(self):
        original = source_body()
        before = deepcopy(original)
        native = n.adapt_astra_request(original, native_model="gpt-6-astra")
        self.assertEqual(original, before)
        self.assertEqual(native["messages"], original["messages"])
        self.assertIsNot(native["messages"], original["messages"])
        self.assertEqual(native["reasoning_effort"], "high")
        self.assertEqual(native["max_completion_tokens"], 32768)
        self.assertEqual(native["seed"], 42)
        self.assertEqual(set(native), {"model", "messages", "reasoning_effort", "max_completion_tokens", "seed", "response_format"})
        proof = n.adaptation_receipt(original, native)
        self.assertTrue(proof["model_visible_contract_exact"])
        self.assertEqual(proof["source_messages_sha256"], proof["native_messages_sha256"])
        self.assertFalse(proof["execution_enabled"])

    def test_routing_metadata_only_can_be_removed(self):
        original = source_body()
        original["provider"] = {"only": ["openai"], "allow_fallbacks": False}
        self.assertNotIn("provider", n.adapt_astra_request(original, native_model="gpt-6-astra"))

    def test_frozen_setting_or_extra_field_changes_rejected(self):
        changes = {"seed": None, "max_tokens": 128000, "reasoning": {"effort": "max"},
                   "model": "openai/gpt-6.1-sol", "response_format": {"type": "text"},
                   "temperature": 0, "tools": [], "stream": False}
        for key, value in changes.items():
            with self.subTest(key=key):
                original = source_body(); original[key] = value
                with self.assertRaises(n.AdmissionError):
                    n.adapt_astra_request(original, native_model="gpt-6-astra")

    def test_no_added_agent_developer_or_tool_messages(self):
        for role in ("developer", "assistant", "tool"):
            original = source_body(); original["messages"][0]["role"] = role
            with self.subTest(role=role), self.assertRaises(n.AdmissionError):
                n.adapt_astra_request(original, native_model="gpt-6-astra")

    def test_native_binding_must_be_explicit(self):
        for value in (None, "openai/gpt-6-astra-20260903", "gpt-6.1-sol", "gpt-6-astra-pro"):
            with self.subTest(value=value), self.assertRaises(n.AdmissionError):
                n.adapt_astra_request(source_body(), native_model=value)

    def test_batch_jsonl_exact_envelope_unique_ids_no_live_execution(self):
        raw, manifest = n.make_batch_jsonl([
            {"custom_id": "request-1", "source_body": source_body()},
            {"custom_id": "request-2", "source_body": source_body()}], native_model="gpt-6-astra")
        rows = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual([x["custom_id"] for x in rows], ["request-1", "request-2"])
        self.assertTrue(all(x["method"] == "POST" and x["url"] == "/v1/chat/completions" for x in rows))
        self.assertEqual(manifest["completion_window"], "24h")
        self.assertEqual(manifest["jobs_submitted"], 0)
        self.assertFalse(manifest["execution_enabled"])
        duplicate = [{"custom_id": "same", "source_body": source_body()}] * 2
        with self.assertRaises(n.AdmissionError):
            n.make_batch_jsonl(duplicate, native_model="gpt-6-astra")


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.source = source_body()
        self.native = n.adapt_astra_request(self.source, native_model="gpt-6-astra")
        self.condition = {"cohort": "B004", "method": "leiden", "arm": "all_means", "group": 0}
        self.accepted = {"status": "accepted", "provider": "OpenAI", "source_model": "openai/gpt-6-astra",
                         "source_body_sha256": n.sha256_json(self.source), "response_sha256": H,
                         "canonical_model": "openai/gpt-6-astra-20260903", "condition": self.condition}

    def reuse(self, binding=None, accepted=None, native=None, condition=None):
        return n.reuse_decision(self.source, native or self.native, accepted=accepted or self.accepted,
                                model_binding=binding or admitted_binding(), condition=condition or self.condition)

    def test_same_condition_and_verified_binding_are_reusable(self):
        self.assertTrue(self.reuse()["reusable"])

    def test_alias_family_alone_is_not_snapshot_equivalence(self):
        for key, value in (("canonical_equivalence_verified", False), ("admitted", False),
                           ("evidence_sha256", None), ("supported_parameters", [])):
            binding = admitted_binding(); binding[key] = value
            with self.subTest(key=key):
                self.assertFalse(self.reuse(binding=binding)["reusable"])

    def test_changed_message_context_or_arm_prevents_reuse(self):
        native = deepcopy(self.native); native["messages"][1]["content"] += " "
        self.assertIn("model_visible_contract_changed", self.reuse(native=native)["issues"])
        other = {**self.condition, "arm": "selected_names"}
        self.assertIn("scientific_condition_mismatch", self.reuse(condition=other)["issues"])

    def test_unaccepted_or_hash_mismatched_output_not_reused(self):
        for key, value in (("status", "invalid"), ("provider", "Other"),
                           ("response_sha256", None), ("source_body_sha256", "b" * 64)):
            accepted = deepcopy(self.accepted); accepted[key] = value
            with self.subTest(key=key):
                self.assertFalse(self.reuse(accepted=accepted)["reusable"])


class CreditTests(unittest.TestCase):
    def test_any_existing_credit_source_admitted_no_pro_requirement(self):
        for source in ("purchased", "promotional", "subscription", "unspecified"):
            snapshot = credit_snapshot(); snapshot["credit_source"] = source
            receipt = n.credit_preflight(snapshot, reservation_usd="60", now=NOW)
            with self.subTest(source=source):
                self.assertTrue(receipt["passed"])
                self.assertEqual(receipt["required_with_headroom_usd"], "72.00")
                self.assertFalse(receipt["credit_source_restricted"])
                self.assertFalse(receipt["provider_enforced_credit_only"])
                self.assertFalse(receipt["new_credit_purchase_authorized"])

    def test_pending_shared_usage_and_other_reservations_reduce_headroom(self):
        snapshot = credit_snapshot(); snapshot.update(existing_balance_usd="100", pending_usage_usd="20", other_reservations_usd="20")
        receipt = n.credit_preflight(snapshot, reservation_usd="60", now=NOW)
        self.assertFalse(receipt["passed"])
        self.assertIn("insufficient_existing_credit_headroom", receipt["issues"])

    def test_expiring_unverified_stale_and_wrong_account_credits_block(self):
        cases = [("expires_at", (NOW + timedelta(hours=47)).isoformat(), "credits_expire_before_safety_window"),
                 ("verified", False, "credit_snapshot_unverified"),
                 ("observed_at", (NOW - timedelta(minutes=16)).isoformat(), "credit_snapshot_not_fresh"),
                 ("credential_project_id", "proj-other", "credential_project_id_mismatch"),
                 ("credential_organization_id", "org-other", "credential_organization_id_mismatch")]
        for key, value, issue in cases:
            snapshot = credit_snapshot(); snapshot[key] = value
            with self.subTest(key=key):
                self.assertIn(issue, n.credit_preflight(snapshot, reservation_usd="60", now=NOW)["issues"])

    def test_expiry_must_be_checked_but_verified_nonexpiring_credit_is_allowed(self):
        snapshot = credit_snapshot(); del snapshot["expires_at"]
        self.assertIn("credit_expiry_not_verified", n.credit_preflight(snapshot, reservation_usd="60", now=NOW)["issues"])
        snapshot["no_expiration_before_completion"] = True
        self.assertTrue(n.credit_preflight(snapshot, reservation_usd="60", now=NOW)["passed"])

    def test_invalid_money_and_missing_timezone_cannot_pass(self):
        for value in ("NaN", "Infinity", -1, True, None):
            with self.subTest(value=value), self.assertRaises(n.AdmissionError):
                n.credit_preflight(credit_snapshot(), reservation_usd=value, now=NOW)
        snapshot = credit_snapshot(); snapshot["observed_at"] = "2026-11-10T23:00:00"
        with self.assertRaises(n.AdmissionError):
            n.credit_preflight(snapshot, reservation_usd="60", now=NOW)

    def test_secret_redaction_does_not_redact_token_counts(self):
        sample = {"OPENAI_API_KEY": "not-for-output", "Authorization": "Bearer private-value",
                  "nested": {"continuationToken": "opaque-state", "completion_tokens": 20},
                  "error": "Request used sk-proj-abcdefghijk123456789"}
        clean = n.sanitize_for_receipt(sample)
        self.assertNotIn("not-for-output", json.dumps(clean))
        self.assertNotIn("private-value", json.dumps(clean))
        self.assertNotIn("opaque-state", json.dumps(clean))
        self.assertNotIn("sk-proj-", json.dumps(clean))
        self.assertEqual(clean["nested"]["completion_tokens"], 20)

    def test_public_admission_does_not_publish_account_balances(self):
        private = passing_credit()
        public = n.public_credit_admission(private)
        self.assertEqual(private["visibility"], "private_financial_preflight")
        self.assertEqual(public["visibility"], "public_admission_summary")
        self.assertTrue(public["passed"])
        for key in ("existing_balance_usd", "usable_existing_balance_usd", "pending_usage_usd",
                    "other_reservations_usd", "organization_sha256", "project_sha256"):
            self.assertNotIn(key, public)


class SubmissionTests(unittest.TestCase):
    def test_default_execution_and_missing_authorization_are_blocked(self):
        record = n.new_submission_record(batch_manifest())
        self.assertEqual(record["state"], "planned")
        self.assertFalse(record["execution_enabled"])
        with self.assertRaises(n.AdmissionError):
            n.begin_submission(record)

    def test_pending_state_must_be_persisted_and_cannot_be_resubmitted(self):
        record = pending_record()
        self.assertEqual(record["state"], "submission_pending")
        self.assertEqual(record["attempts"], 1)
        with self.assertRaises(n.AdmissionError):
            n.begin_submission(record, execution_enabled=True, launch_authorization_id="launch", certificate_sha256=H,
                               credit_receipt=passing_credit(), model_admitted=True, now=NOW)

    def test_ambiguous_submission_requires_positive_provider_reconciliation(self):
        record = n.mark_ambiguous(pending_record(), reason="HTTP timeout")
        no_match = n.reconcile_submission(record, matches=[])
        self.assertEqual(no_match["state"], "ambiguous")
        match = {"batch_id": "batch_example", "input_file_sha256": record["input_file_sha256"],
                 "request_ids": record["request_ids"]}
        reconciled = n.reconcile_submission(no_match, matches=[match])
        self.assertEqual(reconciled["state"], "submitted")
        self.assertEqual(reconciled["batch_id"], "batch_example")

    def test_duplicate_provider_matches_remain_ambiguous(self):
        record = pending_record()
        match = {"batch_id": "batch_one", "input_file_sha256": record["input_file_sha256"], "request_ids": record["request_ids"]}
        self.assertEqual(n.reconcile_submission(record, matches=[match, {**match, "batch_id": "batch_two"}])["state"], "ambiguous")

    def test_acknowledgement_is_idempotent_but_mismatched_receipt_fails(self):
        record = pending_record()
        args = {"batch_id": "batch_one", "input_file_sha256": record["input_file_sha256"], "request_ids": record["request_ids"]}
        ack = n.acknowledge_batch(record, **args)
        self.assertEqual(n.acknowledge_batch(ack, **args), ack)
        with self.assertRaises(n.AdmissionError):
            n.acknowledge_batch(ack, **{**args, "batch_id": "batch_other"})
        with self.assertRaises(n.AdmissionError):
            n.acknowledge_batch(record, **{**args, "request_ids": ["not-the-sealed-item"]})

    def test_launch_rechecks_credit_receipt_freshness(self):
        with self.assertRaises(n.AdmissionError):
            n.begin_submission(n.new_submission_record(batch_manifest()), execution_enabled=True,
                               launch_authorization_id="launch", certificate_sha256=H,
                               credit_receipt=passing_credit(), model_admitted=True, now=NOW + timedelta(minutes=16))


class NativeResultTests(unittest.TestCase):
    def test_native_accounting_preserves_generation_and_counts_reasoning_once(self):
        result = n.validate_batch_result_envelope(result_item(), expected_custom_id="request-1", expected_native_model="gpt-6-astra")
        self.assertEqual(result["generation_id"], "chatcmpl-example")
        self.assertEqual(result["usage"]["completion_tokens"], 13)
        self.assertTrue(result["reasoning_tokens_already_in_completion"])
        self.assertTrue(result["requires_strict_label_validation"])

    def test_truncation_refusal_wrong_identity_and_bad_accounting_rejected(self):
        item = result_item(); item["response"]["body"]["choices"][0]["finish_reason"] = "length"
        refusal = result_item(); refusal["response"]["body"]["choices"][0]["message"]["refusal"] = "refused"
        wrong = result_item(); wrong["custom_id"] = "other"
        counts = result_item(); counts["response"]["body"]["usage"]["total_tokens"] += 1
        reason = result_item(); reason["response"]["body"]["usage"]["completion_tokens_details"]["reasoning_tokens"] = 14
        model = result_item(); model["response"]["body"]["model"] = "gpt-6.1-sol"
        for name, bad in (("length", item), ("refusal", refusal), ("identity", wrong), ("counts", counts), ("reasoning", reason), ("model", model)):
            with self.subTest(name=name), self.assertRaises(n.AdmissionError):
                n.validate_batch_result_envelope(bad, expected_custom_id="request-1")


if __name__ == "__main__":
    unittest.main()
