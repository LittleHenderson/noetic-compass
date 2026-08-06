from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TEST_DIR = Path(__file__).resolve().parent
for candidate in (SRC, TEST_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2 import (  # noqa: E402
    ArtifactRef,
    SchemaValidationError,
    StrictJSONError,
    WORKER_AUTHORIZATION_MEDIA_TYPE,
    WORKER_TERMINAL_RECEIPT_MEDIA_TYPE,
    WorkerAuthorizationArtifact,
    WorkerTerminalReceiptArtifact,
    build_worker_authorization,
    canonical_sha256,
    load_worker_authorization,
    load_worker_terminal_receipt,
    replay_worker_authorization_for_terminal,
    sha256_bytes,
)
from cas_harness_v2.preregistration import PreregistrationChain  # noqa: E402
from test_research_control_kernel import Fixture, artifact_ref, encode  # noqa: E402


AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "authentication": "NOT_PROVIDED",
    "durable_one_use": "NOT_PROVIDED",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}


class WorkerProtocolFixture:
    def __init__(self) -> None:
        research = Fixture()
        self.base = research.loaded
        self.chain = PreregistrationChain(self.base)
        self.base_json = json.loads(self.base.raw_bytes)
        self.run_nonce = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
        self.output_bytes = b"exact worker output bytes\n"
        identities = self.base_json["identities"]
        self.authorization = {
            "schema_version": "cas_harness_v2.worker_authorization.v1",
            "authorization_id": "worker-auth-h2-001",
            "freshness": {
                "issued_at": "2026-08-05T08:30:00Z",
                "expires_at": "2026-08-05T09:30:00Z",
                "semantic": "FRESHNESS_ONLY",
                "trust": "NOT_TRUSTED",
            },
            "preregistration_binding": {
                "base_artifact": artifact_ref(
                    self.base.preregistration_id,
                    self.base.raw_bytes,
                    "application/vnd.cas-harness.preregistration+json",
                ),
                "pre_outcome_chain_sha256": self.chain.chain_sha256,
                "claim_id": self.base.claim_id,
                "claim_record_sha256": self.base.claim_record_sha256,
                "protected_design_sha256": self.base.protected_design_sha256,
            },
            "identity_binding": {
                "model_canonical_sha256": canonical_sha256(identities["model"]),
                "code_canonical_sha256": canonical_sha256(identities["code"]),
                "environment_canonical_sha256": canonical_sha256(
                    identities["environment"]
                ),
                "combined_canonical_sha256": canonical_sha256(identities),
            },
            "required_design": {
                "controls": [
                    {
                        "control_id": row["control_id"],
                        "canonical_sha256": canonical_sha256(row),
                    }
                    for row in self.base_json["controls"]
                ],
                "falsifiers": [
                    {
                        "falsifier_id": row["falsifier_id"],
                        "canonical_sha256": canonical_sha256(row),
                    }
                    for row in self.base_json["falsifiers"]
                ],
            },
            "execution_mapping": {
                "fleet_id": "fleet-research-01",
                "job_id": "job-h2-001",
                "audit_id": "audit-h2-001",
                "assigned_worker_id": "worker-research-01",
                "layer_start": 7,
                "layer_end": 8,
                "shard_id": "shard-layers-07-08",
                "assigned_methods": ["projector-readout-v1", "matched-control-v1"],
                "expected_outputs": ["raw-outcomes"],
                "lease_model": {
                    "model_id": identities["model"]["model_id"],
                    "model_revision": identities["model"]["revision"],
                    "model_artifact_manifest_path": "C:\\research\\model-manifest.json",
                    "model_artifact_manifest_sha256": "d" * 64,
                    "execution_mode": "external_probe_command",
                },
            },
            "nonce_binding": {
                "run_nonce": {
                    "value_b64url": self.run_nonce,
                    "profile": "CALLER_DECLARED_CSPRNG_256_BIT",
                    "structural_assurance": "LENGTH_AND_ENCODING_ONLY",
                },
                "durable_enforcement": "EXTERNAL_REQUIRED_NOT_PROVIDED",
            },
            "authority": deepcopy(AUTHORITY),
            "governance": deepcopy(self.base_json["governance"]),
        }
        self.authorization_raw = encode(self.authorization)
        self.loaded_authorization = load_worker_authorization(
            self.authorization_raw, chain=self.chain
        )
        self.receipt = {
            "schema_version": "cas_harness_v2.worker_terminal_receipt.v1",
            "receipt_id": "worker-receipt-h2-001",
            "authorization": artifact_ref(
                self.authorization["authorization_id"],
                self.authorization_raw,
                WORKER_AUTHORIZATION_MEDIA_TYPE,
            ),
            "freshness": {
                "worker_started_at": "2026-08-05T08:35:00Z",
                "terminal_at": "2026-08-05T09:20:00Z",
                "semantic": "FRESHNESS_ONLY",
                "trust": "NOT_TRUSTED",
            },
            "preregistration_binding": deepcopy(
                self.authorization["preregistration_binding"]
            ),
            "identity_binding": deepcopy(self.authorization["identity_binding"]),
            "required_design": deepcopy(self.authorization["required_design"]),
            "execution_mapping": deepcopy(self.authorization["execution_mapping"]),
            "nonce_binding": deepcopy(self.authorization["nonce_binding"]),
            "terminal": {
                "status": "COMPLETED",
                "produced_output_effect": "DECLARED_OUTPUTS_NOT_SCIENTIFICALLY_ASSESSED",
                "produced_outputs": [
                    {
                        "output_name": "raw-outcomes",
                        "artifact": artifact_ref(
                            "worker-output-shard-00",
                            self.output_bytes,
                            "application/jsonl",
                        ),
                    }
                ],
                "missing_outputs": [],
                "error": None,
            },
            "authority": deepcopy(AUTHORITY),
            "governance": deepcopy(self.authorization["governance"]),
        }

    def load_authorization(self, value: dict | None = None) -> WorkerAuthorizationArtifact:
        return load_worker_authorization(
            encode(self.authorization if value is None else value), chain=self.chain
        )

    def load_receipt(self, value: dict | None = None) -> WorkerTerminalReceiptArtifact:
        return load_worker_terminal_receipt(
            encode(self.receipt if value is None else value),
            authorization=self.loaded_authorization,
            chain=self.chain,
        )


class WorkerAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = WorkerProtocolFixture()

    def test_exact_authorization_loads_and_exposes_bound_refs(self) -> None:
        loaded = self.fx.loaded_authorization
        self.assertIsInstance(loaded, WorkerAuthorizationArtifact)
        self.assertEqual(loaded.raw_bytes, self.fx.authorization_raw)
        self.assertEqual(loaded.sha256, sha256_bytes(self.fx.authorization_raw))
        self.assertEqual(loaded.byte_length, len(self.fx.authorization_raw))
        self.assertTrue(loaded.artifact_ref.verify_bytes(self.fx.authorization_raw))
        self.assertEqual(loaded.artifact_ref.media_type, WORKER_AUTHORIZATION_MEDIA_TYPE)
        self.assertEqual(loaded.run_nonce_b64url, self.fx.run_nonce)
        self.assertIn(self.fx.base.preregistration_id, {ref.artifact_id for ref in loaded.artifact_refs})
        with self.assertRaises(FrozenInstanceError):
            loaded.authorization_id = "changed"  # type: ignore[misc]

    def test_builder_constructs_exact_limited_carrier_from_external_nonce(self) -> None:
        built = build_worker_authorization(
            chain=self.fx.chain,
            authorization_id=self.fx.authorization["authorization_id"],
            issued_at=self.fx.authorization["freshness"]["issued_at"],
            expires_at=self.fx.authorization["freshness"]["expires_at"],
            execution_mapping=self.fx.authorization["execution_mapping"],
            run_nonce=bytes(range(32)),
        )
        self.assertEqual(built.raw_bytes, self.fx.authorization_raw)
        self.assertEqual(built, self.fx.loaded_authorization)
        self.assertEqual(
            built.payload["nonce_binding"]["durable_enforcement"],
            "EXTERNAL_REQUIRED_NOT_PROVIDED",
        )
        self.assertEqual(built.payload["authority"], AUTHORITY)

    def test_builder_rejects_non_exact_nonce_before_constructing_carrier(self) -> None:
        kwargs = {
            "chain": self.fx.chain,
            "authorization_id": self.fx.authorization["authorization_id"],
            "issued_at": self.fx.authorization["freshness"]["issued_at"],
            "expires_at": self.fx.authorization["freshness"]["expires_at"],
            "execution_mapping": self.fx.authorization["execution_mapping"],
        }
        for nonce in (b"short", b"X" * 33, "X" * 32):
            with self.subTest(nonce=nonce):
                with self.assertRaises(SchemaValidationError):
                    build_worker_authorization(run_nonce=nonce, **kwargs)  # type: ignore[arg-type]

    def test_terminal_replay_loader_reads_exact_prior_bytes_after_outcome_seal(self) -> None:
        terminal = self.fx.load_receipt()
        self.fx.chain.record_outcome_access(
            accessed_at=terminal.terminal_at,
            execution_completed_at=terminal.terminal_at,
            receipt=terminal.outcome_access_receipt_ref,
        )
        with self.assertRaises(SchemaValidationError):
            load_worker_authorization(self.fx.authorization_raw, chain=self.fx.chain)
        replayed = replay_worker_authorization_for_terminal(
            self.fx.authorization_raw,
            chain=self.fx.chain,
        )
        self.assertEqual(replayed, self.fx.loaded_authorization)

    def test_mutable_input_is_snapshotted(self) -> None:
        raw = bytearray(self.fx.authorization_raw)
        loaded = load_worker_authorization(raw, chain=self.fx.chain)
        raw[0] = ord("[")
        self.assertEqual(loaded.raw_bytes, self.fx.authorization_raw)

    def test_duplicate_or_extra_json_fields_are_rejected(self) -> None:
        duplicate = self.fx.authorization_raw.replace(
            b'"authorization_id":',
            b'"authorization_id":"forged","authorization_id":',
            1,
        )
        with self.assertRaises(StrictJSONError):
            load_worker_authorization(duplicate, chain=self.fx.chain)
        value = deepcopy(self.fx.authorization)
        value["unexpected"] = True
        with self.assertRaisesRegex(SchemaValidationError, "forbidden extra"):
            self.fx.load_authorization(value)

    def test_every_preregistration_binding_is_exact(self) -> None:
        mutations = {
            "base_artifact": lambda value: value["base_artifact"].__setitem__("sha256", "A" * 64),
            "pre_outcome_chain_sha256": lambda value: value.__setitem__("pre_outcome_chain_sha256", "A" * 64),
            "claim_id": lambda value: value.__setitem__("claim_id", "other-claim"),
            "claim_record_sha256": lambda value: value.__setitem__("claim_record_sha256", "B" * 64),
            "protected_design_sha256": lambda value: value.__setitem__("protected_design_sha256", "C" * 64),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                value = deepcopy(self.fx.authorization)
                mutate(value["preregistration_binding"])
                with self.assertRaises(SchemaValidationError):
                    self.fx.load_authorization(value)

    def test_model_code_environment_and_combined_identities_are_exact(self) -> None:
        for field in self.fx.authorization["identity_binding"]:
            with self.subTest(field=field):
                value = deepcopy(self.fx.authorization)
                value["identity_binding"][field] = "D" * 64
                with self.assertRaisesRegex(SchemaValidationError, "identity_binding"):
                    self.fx.load_authorization(value)

    def test_controls_and_falsifiers_reject_omission_reorder_extra_and_substitution(self) -> None:
        mutations = []
        omitted = deepcopy(self.fx.authorization)
        omitted["required_design"]["controls"].pop()
        mutations.append(omitted)
        reordered = deepcopy(self.fx.authorization)
        reordered["required_design"]["controls"].reverse()
        mutations.append(reordered)
        extra = deepcopy(self.fx.authorization)
        extra["required_design"]["falsifiers"].append(
            {"falsifier_id": "invented", "canonical_sha256": "E" * 64}
        )
        mutations.append(extra)
        substituted = deepcopy(self.fx.authorization)
        substituted["required_design"]["controls"][0]["canonical_sha256"] = "F" * 64
        mutations.append(substituted)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaisesRegex(SchemaValidationError, "required_design"):
                    self.fx.load_authorization(value)

    def test_execution_mapping_rejects_coercion_invalid_range_and_duplicate_lists(self) -> None:
        coerced = deepcopy(self.fx.authorization)
        coerced["execution_mapping"]["layer_start"] = "7"
        invalid_range = deepcopy(self.fx.authorization)
        invalid_range["execution_mapping"]["layer_end"] = 6
        duplicate_method = deepcopy(self.fx.authorization)
        duplicate_method["execution_mapping"]["assigned_methods"].append(
            duplicate_method["execution_mapping"]["assigned_methods"][0]
        )
        duplicate_output = deepcopy(self.fx.authorization)
        duplicate_output["execution_mapping"]["expected_outputs"].append("raw-outcomes")
        for value in (coerced, invalid_range, duplicate_method, duplicate_output):
            with self.assertRaises(SchemaValidationError):
                self.fx.load_authorization(value)

    def test_live_lease_model_is_complete_canonical_and_preregistered(self) -> None:
        mutations = {
            "model_id": "other/model",
            "model_revision": "f" * 40,
            "model_artifact_manifest_path": "relative/manifest.json",
            "model_artifact_manifest_sha256": "D" * 64,
            "execution_mode": "synthetic_fixture",
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                value = deepcopy(self.fx.authorization)
                value["execution_mapping"]["lease_model"][field] = replacement
                with self.assertRaises(SchemaValidationError):
                    self.fx.load_authorization(value)

    def test_run_nonce_requires_canonical_32_byte_base64url_and_fixed_caveat(self) -> None:
        for field, replacement in (
            ("value_b64url", "abc"),
            ("value_b64url", self.fx.run_nonce + "="),
            ("profile", "SERVER_AUTHENTICATED"),
            ("structural_assurance", "RANDOMNESS_PROVEN"),
        ):
            with self.subTest(field=field):
                value = deepcopy(self.fx.authorization)
                value["nonce_binding"]["run_nonce"][field] = replacement
                with self.assertRaises(SchemaValidationError):
                    self.fx.load_authorization(value)

    def test_authorization_has_no_future_callback_nonce_and_no_durable_claim(self) -> None:
        callback_added = deepcopy(self.fx.authorization)
        callback_added["nonce_binding"]["callback_nonce_record"] = {"nonce_id": "future"}
        promoted = deepcopy(self.fx.authorization)
        promoted["nonce_binding"]["durable_enforcement"] = "PROVIDED"
        for value in (callback_added, promoted):
            with self.assertRaises(SchemaValidationError):
                self.fx.load_authorization(value)

    def test_freshness_is_application_only_and_ordered(self) -> None:
        for field, replacement in (
            ("semantic", "TRUSTED_TIME"),
            ("trust", "TRUSTED"),
            ("issued_at", "2026-08-05T07:59:59Z"),
            ("expires_at", "2026-08-05T08:00:00Z"),
        ):
            with self.subTest(field=field):
                value = deepcopy(self.fx.authorization)
                value["freshness"][field] = replacement
                with self.assertRaises(SchemaValidationError):
                    self.fx.load_authorization(value)

    def test_authority_and_governance_cannot_be_promoted(self) -> None:
        authority = deepcopy(self.fx.authorization)
        authority["authority"]["authentication"] = "PROVIDED"
        governance = deepcopy(self.fx.authorization)
        governance["governance"]["product_claim_status"] = "LICENSED"
        for value in (authority, governance):
            with self.assertRaises(SchemaValidationError):
                self.fx.load_authorization(value)

    def test_post_outcome_chain_rejects_authorization(self) -> None:
        receipt_bytes = b"preexisting receipt\n"
        self.fx.chain.record_outcome_access(
            accessed_at="2026-08-05T09:20:00Z",
            execution_completed_at="2026-08-05T09:10:00Z",
            receipt=ArtifactRef(**artifact_ref("preexisting-receipt", receipt_bytes)),
        )
        with self.assertRaisesRegex(SchemaValidationError, "pre-outcome"):
            load_worker_authorization(self.fx.authorization_raw, chain=self.fx.chain)


class WorkerTerminalReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = WorkerProtocolFixture()

    def test_completed_receipt_loads_and_exposes_outcome_access_ref(self) -> None:
        loaded = self.fx.load_receipt()
        raw = encode(self.fx.receipt)
        self.assertIsInstance(loaded, WorkerTerminalReceiptArtifact)
        self.assertEqual(loaded.terminal_status, "COMPLETED")
        self.assertEqual(loaded.raw_bytes, raw)
        self.assertEqual(len(loaded.outcome_artifact_refs), 1)
        self.assertTrue(loaded.outcome_artifact_refs[0].verify_bytes(self.fx.output_bytes))
        self.assertTrue(loaded.artifact_ref.verify_bytes(raw))
        self.assertEqual(
            loaded.outcome_access_receipt_ref.media_type,
            WORKER_TERMINAL_RECEIPT_MEDIA_TYPE,
        )
        event = self.fx.chain.record_outcome_access(
            accessed_at="2026-08-05T09:25:00Z",
            execution_completed_at=loaded.terminal_at,
            receipt=loaded.outcome_access_receipt_ref,
        )
        self.assertEqual(event.receipt, loaded.artifact_ref)

    def test_failed_receipt_requires_typed_error_and_complete_missing_partition(self) -> None:
        value = deepcopy(self.fx.receipt)
        value["receipt_id"] = "worker-receipt-h2-failed"
        value["terminal"] = {
            "status": "FAILED",
            "produced_output_effect": "QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY",
            "produced_outputs": [],
            "missing_outputs": ["raw-outcomes"],
            "error": {
                "code": "cuda-oom",
                "category": "RESOURCE_EXHAUSTED",
                "message": "The research worker exhausted its assigned device memory.",
                "retryable": True,
            },
        }
        loaded = self.fx.load_receipt(value)
        self.assertEqual(loaded.terminal_status, "FAILED")
        self.assertEqual(loaded.outcome_artifact_refs, ())

    def test_failed_receipt_preserves_ordered_quarantined_partial_outputs(self) -> None:
        authorization_value = deepcopy(self.fx.authorization)
        authorization_value["authorization_id"] = "worker-auth-h2-partial"
        authorization_value["execution_mapping"]["expected_outputs"] = [
            "raw-outcomes",
            "diagnostic-trace",
        ]
        authorization_raw = encode(authorization_value)
        authorization = load_worker_authorization(
            authorization_raw,
            chain=self.fx.chain,
        )
        value = deepcopy(self.fx.receipt)
        value["receipt_id"] = "worker-receipt-h2-partial"
        value["authorization"] = artifact_ref(
            authorization_value["authorization_id"],
            authorization_raw,
            WORKER_AUTHORIZATION_MEDIA_TYPE,
        )
        value["execution_mapping"] = deepcopy(
            authorization_value["execution_mapping"]
        )
        value["terminal"] = {
            "status": "FAILED",
            "produced_output_effect": "QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY",
            "produced_outputs": [
                {
                    "output_name": "raw-outcomes",
                    "artifact": artifact_ref(
                        "worker-output-partial-00",
                        self.fx.output_bytes,
                        "application/jsonl",
                    ),
                }
            ],
            "missing_outputs": ["diagnostic-trace"],
            "error": {
                "code": "postprocess-failed",
                "category": "EXECUTION_FAILED",
                "message": "The diagnostic trace failed after raw output capture.",
                "retryable": False,
            },
        }
        loaded = load_worker_terminal_receipt(
            encode(value),
            authorization=authorization,
            chain=self.fx.chain,
        )
        self.assertEqual(loaded.terminal_status, "FAILED")
        self.assertEqual(len(loaded.outcome_artifact_refs), 1)
        self.assertTrue(loaded.outcome_artifact_refs[0].verify_bytes(self.fx.output_bytes))

    def test_receipt_rejects_wrong_authorization_bytes_or_coercion(self) -> None:
        wrong = deepcopy(self.fx.receipt)
        wrong["authorization"]["sha256"] = "A" * 64
        with self.assertRaisesRegex(SchemaValidationError, "authorization"):
            self.fx.load_receipt(wrong)
        coerced = deepcopy(self.fx.receipt)
        coerced["authorization"]["byte_length"] = str(
            coerced["authorization"]["byte_length"]
        )
        with self.assertRaises(SchemaValidationError):
            self.fx.load_receipt(coerced)

    def test_terminal_rejects_transport_callback_nonce_field(self) -> None:
        value = deepcopy(self.fx.receipt)
        value["callback_nonce_record"] = {
            "nonce_id": "future-transport-attempt",
            "sha256": "A" * 64,
        }
        with self.assertRaisesRegex(SchemaValidationError, "forbidden extra"):
            self.fx.load_receipt(value)

    def test_every_repeated_binding_rejects_replay_shaped_substitution(self) -> None:
        mutations = {
            "preregistration_binding": lambda value: value["preregistration_binding"].__setitem__("claim_id", "old-claim"),
            "identity_binding": lambda value: value["identity_binding"].__setitem__("model_canonical_sha256", "B" * 64),
            "required_design": lambda value: value["required_design"]["controls"].pop(),
            "execution_mapping": lambda value: value["execution_mapping"].__setitem__("job_id", "old-job"),
            "nonce_binding": lambda value: value["nonce_binding"]["run_nonce"].__setitem__("value_b64url", base64.urlsafe_b64encode(b"Z" * 32).decode().rstrip("=")),
            "authority": lambda value: value["authority"].__setitem__("scope", "PRODUCT"),
            "governance": lambda value: value["governance"].__setitem__("disclosure_status", "PUBLIC"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                value = deepcopy(self.fx.receipt)
                mutate(value)
                with self.assertRaisesRegex(SchemaValidationError, "does not exactly match"):
                    self.fx.load_receipt(value)

    def test_completed_receipt_rejects_missing_extra_or_relabelled_outputs(self) -> None:
        missing = deepcopy(self.fx.receipt)
        missing["terminal"]["produced_outputs"] = []
        relabelled = deepcopy(self.fx.receipt)
        relabelled["terminal"]["produced_outputs"][0]["output_name"] = "other-output"
        extra = deepcopy(self.fx.receipt)
        extra["terminal"]["produced_outputs"].append(
            deepcopy(extra["terminal"]["produced_outputs"][0])
        )
        for value in (missing, relabelled, extra):
            with self.assertRaises(SchemaValidationError):
                self.fx.load_receipt(value)

    def test_completed_receipt_rejects_error_and_failed_receipt_rejects_bad_partition(self) -> None:
        completed_with_error = deepcopy(self.fx.receipt)
        completed_with_error["terminal"]["error"] = {
            "code": "invented",
            "category": "INTERNAL_ERROR",
            "message": "invented",
            "retryable": False,
        }
        failed_with_output = deepcopy(self.fx.receipt)
        failed_with_output["terminal"]["status"] = "FAILED"
        failed_with_output["terminal"]["missing_outputs"] = ["raw-outcomes"]
        failed_with_output["terminal"][
            "produced_output_effect"
        ] = "QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY"
        failed_with_output["terminal"]["error"] = {
            "code": "worker-failed",
            "category": "EXECUTION_FAILED",
            "message": "worker failed",
            "retryable": False,
        }
        promoted_effect = deepcopy(self.fx.receipt)
        promoted_effect["terminal"]["produced_output_effect"] = "SCIENTIFICALLY_VALIDATED"
        failed_unquarantined = deepcopy(self.fx.receipt)
        failed_unquarantined["terminal"] = {
            "status": "FAILED",
            "produced_output_effect": "DECLARED_OUTPUTS_NOT_SCIENTIFICALLY_ASSESSED",
            "produced_outputs": [],
            "missing_outputs": ["raw-outcomes"],
            "error": {
                "code": "worker-failed",
                "category": "EXECUTION_FAILED",
                "message": "worker failed",
                "retryable": False,
            },
        }
        for value in (
            completed_with_error,
            failed_with_output,
            promoted_effect,
            failed_unquarantined,
        ):
            with self.assertRaises(SchemaValidationError):
                self.fx.load_receipt(value)

    def test_failed_receipt_rejects_null_partial_or_untyped_error(self) -> None:
        cases = []
        for error in (
            None,
            {"code": "failed", "category": "EXECUTION_FAILED", "message": "failed"},
            {
                "code": "failed",
                "category": "UNKNOWN",
                "message": "failed",
                "retryable": False,
            },
        ):
            value = deepcopy(self.fx.receipt)
            value["terminal"] = {
                "status": "FAILED",
                "produced_output_effect": "QUARANTINED_PARTIAL_NEGATIVE_EVIDENCE_ONLY",
                "produced_outputs": [],
                "missing_outputs": ["raw-outcomes"],
                "error": error,
            }
            cases.append(value)
        for value in cases:
            with self.assertRaises(SchemaValidationError):
                self.fx.load_receipt(value)

    def test_receipt_application_time_must_stay_in_declared_window(self) -> None:
        cases = []
        for field, replacement in (
            ("worker_started_at", "2026-08-05T08:20:00Z"),
            ("terminal_at", "2026-08-05T08:34:59Z"),
            ("terminal_at", "2026-08-05T09:30:01Z"),
            ("semantic", "TRUSTED_TIME"),
            ("trust", "TRUSTED"),
        ):
            value = deepcopy(self.fx.receipt)
            value["freshness"][field] = replacement
            cases.append(value)
        for value in cases:
            with self.assertRaises(SchemaValidationError):
                self.fx.load_receipt(value)

    def test_receipt_id_and_outcomes_cannot_shadow_bound_artifacts(self) -> None:
        receipt_collision = deepcopy(self.fx.receipt)
        receipt_collision["receipt_id"] = self.fx.authorization["authorization_id"]
        output_collision = deepcopy(self.fx.receipt)
        output_collision["terminal"]["produced_outputs"][0]["artifact"]["artifact_id"] = "model-weights"
        for value in (receipt_collision, output_collision):
            with self.assertRaises(SchemaValidationError):
                self.fx.load_receipt(value)

    def test_terminal_replays_after_exact_outcome_access_seal_only(self) -> None:
        loaded = self.fx.load_receipt()
        self.fx.chain.record_outcome_access(
            accessed_at="2026-08-05T09:25:00Z",
            execution_completed_at=loaded.terminal_at,
            receipt=loaded.outcome_access_receipt_ref,
        )
        replayed = load_worker_terminal_receipt(
            loaded.raw_bytes,
            authorization=self.fx.authorization_raw,
            chain=self.fx.chain,
        )
        self.assertEqual(replayed, loaded)
        with self.assertRaisesRegex(SchemaValidationError, "pre-outcome"):
            load_worker_authorization(
                self.fx.authorization_raw,
                chain=self.fx.chain,
            )

        for wrong_receipt, wrong_completion in ((True, False), (False, True)):
            with self.subTest(
                wrong_receipt=wrong_receipt,
                wrong_completion=wrong_completion,
            ):
                other = WorkerProtocolFixture()
                other_loaded = other.load_receipt()
                receipt_ref = (
                    ArtifactRef(
                        **artifact_ref(
                            "wrong-terminal-receipt",
                            b"different terminal bytes\n",
                            WORKER_TERMINAL_RECEIPT_MEDIA_TYPE,
                        )
                    )
                    if wrong_receipt
                    else other_loaded.outcome_access_receipt_ref
                )
                other.chain.record_outcome_access(
                    accessed_at="2026-08-05T09:25:00Z",
                    execution_completed_at=(
                        "2026-08-05T09:19:59Z"
                        if wrong_completion
                        else other_loaded.terminal_at
                    ),
                    receipt=receipt_ref,
                )
                with self.assertRaisesRegex(
                    SchemaValidationError,
                    "sealed outcome-access",
                ):
                    load_worker_terminal_receipt(
                        other_loaded.raw_bytes,
                        authorization=other.authorization_raw,
                        chain=other.chain,
                    )

    def test_forged_authorization_dataclass_is_replayed_and_rejected(self) -> None:
        forged = replace(self.fx.loaded_authorization, expires_at="2027-08-05T09:30:00Z")
        with self.assertRaisesRegex(SchemaValidationError, "exact-byte loader replay"):
            load_worker_terminal_receipt(
                encode(self.fx.receipt), authorization=forged, chain=self.fx.chain
            )

    def test_exact_receipt_replay_is_deterministic_not_durable_replay_protection(self) -> None:
        first = self.fx.load_receipt()
        second = self.fx.load_receipt()
        self.assertEqual(first, second)
        self.assertEqual(first.payload["authority"]["durable_one_use"], "NOT_PROVIDED")


if __name__ == "__main__":
    unittest.main()
