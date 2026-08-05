from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import cas_core_v8.compatibility as compatibility_module
import cas_core_v8.runtime_gate as runtime_gate_module

from cas_core_v8 import (
    ACTION_DESCRIPTOR_VERSION,
    AdmissionStatus,
    ArtifactIdentity,
    CompilationAssessment,
    CompatibilityError,
    CompilerValidationReceipt,
    LegacySourceEnvelope,
    LicenseStatus,
    NO_MODEL_IDENTITY_SHA256,
    RecordRegistry,
    RegistryError,
    RegistryRecord,
    ResearchBoundary,
    RuntimeActionDescriptor,
    RuntimeEffectClass,
    RuntimeOperation,
    RuntimeTarget,
    assess_compilation_for_action,
    canonical_json_sha256,
    claim_is_licensed,
    compile_legacy_expression,
    evaluate_runtime_gate,
    sha256_hex,
)


COMPILER = (
    ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)
COHERENCE = ROOT / "docs" / "working" / "project_coherence"
CLAIM_LEDGER = COHERENCE / "CLAIM_LEDGER_v0.1.json"
THEOREM_LEDGER = COHERENCE / "THEOREM_LEDGER_v0.1.json"
CLAIM_SCHEMA = COHERENCE / "CLAIM_RECORD.schema.json"
THEOREM_SCHEMA = COHERENCE / "THEOREM_RECORD.schema.json"


def _raw_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _claim_record(
    *,
    record_id: str = "CLM-TEST",
    version: str = "0.1",
    licensed: bool = False,
) -> dict[str, object]:
    return {
        "id": record_id,
        "version": version,
        "title": "Bounded test claim",
        "statement_kind": "PRODUCT_CLAIM",
        "claim_text": "A bounded fixture statement.",
        "source_refs": ["SRC-TEST"],
        "scope": {
            "population": "test fixture",
            "models": [],
            "architectures": [],
            "contexts": ["unit test"],
            "time_window": "2026-08-04",
        },
        "controls": ["negative control"],
        "falsifier": "fixture failure",
        "uncertainty": "test-only uncertainty",
        "evidence_packets": ["packet:test"] if licensed else [],
        "review_state": "REVIEWED" if licensed else "IN_REVIEW",
        "product_claim_status": "LICENSED" if licensed else "NOT LICENSED",
        "admission_ring": 3 if licensed else 4,
        "disclosure_status": "HELD",
        "theorem_refs": [],
        "reviewers": ["fixture reviewer"],
        "last_reviewed_at": "2026-08-04T00:00:00Z" if licensed else None,
        "notes": ["Test data is not authority."],
    }


def _write_claim_ledger(path: Path, records: list[dict[str, object]]) -> str:
    payload = {
        "schema_version": "project_coherence_claim_ledger.v0.1",
        "record_schema": "CLAIM_RECORD.schema.json",
        "document_status": "TEST / OPEN / NOT FROZEN",
        "as_of": "2026-08-04",
        "completeness": "TEST_ONLY",
        "records": records,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return _raw_sha256(path)


def _load_claim_fixture(path: Path, digest: str) -> RecordRegistry:
    return RecordRegistry.load(
        path,
        kind="claim",
        expected_raw_sha256=digest,
        expected_schema_raw_sha256=_raw_sha256(CLAIM_SCHEMA),
        schema_path=CLAIM_SCHEMA,
    )


def _rebuild_action(
    action: RuntimeActionDescriptor, **changes: object
) -> RuntimeActionDescriptor:
    values: dict[str, object] = {
        "descriptor_version": action.descriptor_version,
        "operation": action.operation,
        "target": action.target,
        "effect_class": action.effect_class,
        "source_sha256": action.source_sha256,
        "compilation_result_sha256": action.compilation_result_sha256,
        "model_identity_sha256": action.model_identity_sha256,
        "environment_identity_sha256": action.environment_identity_sha256,
        "claim_id": action.claim_id,
        "claim_version": action.claim_version,
        "boundary": action.boundary,
    }
    values.update(changes)
    payload = {
        "descriptor_version": values["descriptor_version"],
        "operation": values["operation"].value,
        "target": values["target"].value,
        "effect_class": values["effect_class"].value,
        "source_sha256": values["source_sha256"],
        "compilation_result_sha256": values["compilation_result_sha256"],
        "model_identity_sha256": values["model_identity_sha256"],
        "environment_identity_sha256": values["environment_identity_sha256"],
        "claim_id": values["claim_id"],
        "claim_version": values["claim_version"],
        "boundary": values["boundary"].to_dict(),
    }
    return RuntimeActionDescriptor(
        **values,
        action_sha256=canonical_json_sha256(payload),
    )


class RegistryTests(unittest.TestCase):
    def test_current_ledgers_and_exact_schema_bytes_are_bound(self) -> None:
        claims = RecordRegistry.load(
            CLAIM_LEDGER,
            kind="claim",
            expected_raw_sha256=_raw_sha256(CLAIM_LEDGER),
            expected_schema_raw_sha256=_raw_sha256(CLAIM_SCHEMA),
        )
        record = claims.resolve("CLM-CAS-OHM-PHYSICAL-TELEMETRY", version="0.1")
        self.assertEqual(record.payload["product_claim_status"], "NOT LICENSED")
        self.assertEqual(claims.pinned_raw_sha256, claims.identity.raw_sha256)
        self.assertEqual(
            claims.pinned_schema_raw_sha256, claims.schema_identity.raw_sha256
        )
        self.assertEqual(
            claims.schema_document_sha256,
            canonical_json_sha256(claims.schema_document),
        )
        self.assertEqual(claims.ledger_bytes, CLAIM_LEDGER.read_bytes())
        self.assertEqual(claims.schema_bytes, CLAIM_SCHEMA.read_bytes())
        self.assertTrue(claims.verify_raw_bindings())
        theorems = RecordRegistry.load(
            THEOREM_LEDGER,
            kind="theorem",
            expected_raw_sha256=_raw_sha256(THEOREM_LEDGER),
            expected_schema_raw_sha256=_raw_sha256(THEOREM_SCHEMA),
        )
        self.assertGreater(len(theorems.records), 0)
        self.assertTrue(all(record.kind == "theorem" for record in theorems.records))

    def test_both_ledger_and_schema_trust_pins_are_mandatory(self) -> None:
        with self.assertRaises(TypeError):
            RecordRegistry.load(  # type: ignore[call-arg]
                CLAIM_LEDGER,
                kind="claim",
                expected_raw_sha256=_raw_sha256(CLAIM_LEDGER),
            )
        with self.assertRaisesRegex(RegistryError, "E-REGISTRY-HASH"):
            RecordRegistry.load(
                CLAIM_LEDGER,
                kind="claim",
                expected_raw_sha256="0" * 64,
                expected_schema_raw_sha256=_raw_sha256(CLAIM_SCHEMA),
            )
        with self.assertRaisesRegex(RegistryError, "SCHEMA-HASH"):
            RecordRegistry.load(
                CLAIM_LEDGER,
                kind="claim",
                expected_raw_sha256=_raw_sha256(CLAIM_LEDGER),
                expected_schema_raw_sha256="0" * 64,
            )

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.json"
            path.write_text(
                '{"schema_version":"x","records":[],"records":[]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RegistryError, "DUPLICATE-KEY"):
                RecordRegistry.load(
                    path,
                    kind="claim",
                    expected_raw_sha256=_raw_sha256(path),
                    expected_schema_raw_sha256=_raw_sha256(CLAIM_SCHEMA),
                    schema_path=CLAIM_SCHEMA,
                )

    def test_ambiguous_versions_require_an_exact_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "claims.json"
            digest = _write_claim_ledger(
                path, [_claim_record(version="0.1"), _claim_record(version="0.2")]
            )
            registry = _load_claim_fixture(path, digest)
            with self.assertRaisesRegex(RegistryError, "AMBIGUOUS"):
                registry.resolve("CLM-TEST")

    def test_records_are_recursively_immutable_after_hash_verification(self) -> None:
        registry = RecordRegistry.load(
            CLAIM_LEDGER,
            kind="claim",
            expected_raw_sha256=_raw_sha256(CLAIM_LEDGER),
            expected_schema_raw_sha256=_raw_sha256(CLAIM_SCHEMA),
        )
        record = registry.resolve("CLM-CAS-OHM-PHYSICAL-TELEMETRY", version="0.1")
        original_record_hash = record.record_sha256
        with self.assertRaises(TypeError):
            record.payload["product_claim_status"] = "LICENSED"  # type: ignore[index]
        with self.assertRaises(TypeError):
            record.payload["scope"]["population"] = "mutated"  # type: ignore[index]
        with self.assertRaises(TypeError):
            record.payload["source_refs"][0] = "SRC-MUTATED"  # type: ignore[index]
        self.assertEqual(record.record_sha256, original_record_hash)

    def test_full_schema_rejects_missing_extra_and_bad_typed_fields(self) -> None:
        cases: list[tuple[dict[str, object], str]] = []
        missing = _claim_record()
        missing.pop("title")
        cases.append((missing, "REQUIRED"))
        extra = _claim_record()
        extra["invented_authority"] = True
        cases.append((extra, "ADDITIONAL-PROPERTY"))
        bad_reviewer = _claim_record(licensed=True)
        bad_reviewer["reviewers"] = [None]
        cases.append((bad_reviewer, "TYPE"))
        bad_date = _claim_record(licensed=True)
        bad_date["last_reviewed_at"] = "not-a-date"
        cases.append((bad_date, "DATETIME"))
        float_ring = _claim_record()
        float_ring["admission_ring"] = 4.0
        cases.append((float_ring, "RING"))

        for index, (record, code) in enumerate(cases):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / f"bad-{index}.json"
                digest = _write_claim_ledger(path, [record])
                with self.assertRaisesRegex(RegistryError, code):
                    _load_claim_fixture(path, digest)

    def test_noncanonical_schema_version_is_rejected_even_when_hash_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "claims.json"
            _write_claim_ledger(path, [_claim_record()])
            data = json.loads(path.read_text(encoding="utf-8"))
            data["schema_version"] = "caller_invented.v9"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(RegistryError, "E-REGISTRY-SCHEMA"):
                _load_claim_fixture(path, _raw_sha256(path))

    def test_direct_record_and_registry_constructors_enforce_the_full_contract(self) -> None:
        payload = _claim_record()
        record = RegistryRecord(
            kind="claim",
            record_id="CLM-TEST",
            version="0.1",
            payload=payload,
            record_sha256=canonical_json_sha256(payload),
        )
        invalid_payload = dict(payload)
        invalid_payload.pop("title")
        with self.assertRaisesRegex(RegistryError, "REQUIRED"):
            RegistryRecord(
                kind="claim",
                record_id="CLM-TEST",
                version="0.1",
                payload=invalid_payload,
                record_sha256=canonical_json_sha256(invalid_payload),
            )
        with self.assertRaisesRegex(RegistryError, "ID"):
            replace(record, kind="theorem")

        registry = RecordRegistry.load(
            CLAIM_LEDGER,
            kind="claim",
            expected_raw_sha256=_raw_sha256(CLAIM_LEDGER),
            expected_schema_raw_sha256=_raw_sha256(CLAIM_SCHEMA),
        )
        with self.assertRaisesRegex(RegistryError, "ROOT-SCHEMA"):
            replace(registry, header={"as_of": "2026-08-04"})
        with self.assertRaisesRegex(RegistryError, "DUPLICATE-RECORD"):
            replace(registry, records=(registry.records[0], registry.records[0]))
        with self.assertRaisesRegex(RegistryError, "E-REGISTRY-SCHEMA"):
            replace(registry, schema_version="caller.v9")

        valid_header_change = dict(registry.header)
        valid_header_change["completeness"] = "CALLER_REPLACED"
        with self.assertRaisesRegex(RegistryError, "RAW-BINDING"):
            replace(registry, header=valid_header_change)
        with self.assertRaisesRegex(RegistryError, "RAW-BINDING"):
            replace(registry, records=())

        weakened_schema = json.loads(registry.schema_bytes.decode("utf-8"))
        weakened_schema["properties"]["title"] = {"type": "string"}
        with self.assertRaisesRegex(RegistryError, "SCHEMA-RAW-BINDING"):
            replace(
                registry,
                schema_document=weakened_schema,
                schema_document_sha256=canonical_json_sha256(weakened_schema),
            )

    def test_artifact_identity_variant_cannot_stand_in_for_raw_identity(self) -> None:
        registry = RecordRegistry.load(
            CLAIM_LEDGER,
            kind="claim",
            expected_raw_sha256=_raw_sha256(CLAIM_LEDGER),
            expected_schema_raw_sha256=_raw_sha256(CLAIM_SCHEMA),
        )

        class ArtifactIdentityVariant(ArtifactIdentity):
            def __eq__(self, other: object) -> bool:
                return True

        variant = object.__new__(ArtifactIdentityVariant)
        for name in (
            "raw_sha256",
            "raw_bytes",
            "canonical_lf_sha256",
            "canonical_lf_bytes",
            "crlf_sequences",
            "lone_lf_sequences",
            "lone_cr_sequences",
        ):
            object.__setattr__(variant, name, getattr(registry.identity, name))
        with self.assertRaisesRegex(RegistryError, "E-REGISTRY-IDENTITY"):
            replace(registry, identity=variant)

    def test_registry_rejects_unicode_control_and_format_characters(self) -> None:
        payload = _claim_record()
        payload["title"] = "Invisible\u200dseparator"
        with self.assertRaisesRegex(RegistryError, "E-REGISTRY-TEXT"):
            RegistryRecord(
                kind="claim",
                record_id="CLM-TEST",
                version="0.1",
                payload=payload,
                record_sha256="0" * 64,
            )


class RuntimeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compilation = compile_legacy_expression(
            LegacySourceEnvelope.bind("C1"), compiler_path=COMPILER
        )
        cls.action = RuntimeActionDescriptor.bind(cls.compilation)
        cls.receipt = CompilerValidationReceipt.from_compatibility(cls.compilation)
        cls.assessment = assess_compilation_for_action(cls.compilation, cls.action)

    def test_action_descriptor_digest_binds_every_required_action_component(self) -> None:
        payload = self.action.payload_without_digest()
        self.assertEqual(
            set(payload),
            {
                "descriptor_version",
                "operation",
                "target",
                "effect_class",
                "source_sha256",
                "compilation_result_sha256",
                "model_identity_sha256",
                "environment_identity_sha256",
                "claim_id",
                "claim_version",
                "boundary",
            },
        )
        self.assertEqual(self.action.descriptor_version, ACTION_DESCRIPTOR_VERSION)
        self.assertEqual(self.action.model_identity_sha256, NO_MODEL_IDENTITY_SHA256)
        self.assertEqual(
            self.action.environment_identity_sha256,
            self.compilation.execution_profile_sha256,
        )
        self.assertEqual(
            self.action.action_sha256, canonical_json_sha256(payload)
        )

    def test_internal_assessment_can_pass_structure_but_never_authorizes(self) -> None:
        decision = evaluate_runtime_gate(self.assessment)
        self.assertTrue(decision.structurally_admissible)
        self.assertFalse(decision.authorization_granted)
        self.assertFalse(decision.allowed)
        self.assertIn("STRUCTURAL_PASS_RING4_PURE_LOCAL_COMPUTE", decision.codes)
        self.assertIn("AUTHORIZATION_NOT_GRANTED_RING4_RESEARCH", decision.codes)
        self.assertFalse(any(code.startswith("ALLOW") for code in decision.codes))
        self.assertEqual(decision.boundary.to_dict()["license_status"], "NOT LICENSED")

    def test_receipt_and_self_hashed_action_assertions_are_not_authorization(self) -> None:
        decision = evaluate_runtime_gate(self.receipt, self.action)
        self.assertFalse(decision.structurally_admissible)
        self.assertFalse(decision.authorization_granted)
        self.assertIn("DENY_STRUCTURAL_RECEIPT_NOT_AUTHORIZATION", decision.codes)
        self.assertFalse(any(code.startswith("ALLOW") for code in decision.codes))

    def test_assessment_copy_passes_structure_only_after_fresh_replay(self) -> None:
        caller_copy = replace(self.assessment)
        self.assertTrue(caller_copy.verify_self_digest())
        with patch.object(
            compatibility_module,
            "_run_isolated_worker",
            wraps=compatibility_module._run_isolated_worker,
        ) as worker:
            decision = evaluate_runtime_gate(caller_copy)
        self.assertEqual(worker.call_count, 2)
        self.assertTrue(decision.structurally_admissible)
        self.assertFalse(decision.authorization_granted)

    def test_compilation_copy_is_assessed_only_after_fresh_replay(self) -> None:
        caller_copy = replace(self.compilation)
        with patch.object(
            compatibility_module,
            "_run_isolated_worker",
            wraps=compatibility_module._run_isolated_worker,
        ) as worker:
            assessment = assess_compilation_for_action(caller_copy, self.action)
        self.assertEqual(worker.call_count, 2)
        self.assertTrue(assessment.structurally_admissible)

    def test_replaced_compilation_cannot_pass_when_replay_differs(self) -> None:
        forged_artifact = dict(self.compilation.legacy_artifact)
        forged_artifact["valid"] = False
        replaced_compilation = replace(
            self.compilation,
            legacy_artifact=forged_artifact,
            legacy_artifact_sha256=canonical_json_sha256(forged_artifact),
        )
        with self.assertRaisesRegex(CompatibilityError, "REPLAY-MISMATCH"):
            assess_compilation_for_action(replaced_compilation, self.action)

    def test_decision_fails_closed_when_fresh_replay_cannot_run(self) -> None:
        with patch.object(
            compatibility_module,
            "_run_isolated_worker",
            side_effect=CompatibilityError("E-TEST-REPLAY", "forced test failure"),
        ):
            decision = evaluate_runtime_gate(self.assessment)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_COMPILATION_REPLAY_FAILED", decision.codes)
        self.assertFalse(decision.authorization_granted)

    def test_process_local_issuance_markers_are_absent(self) -> None:
        self.assertFalse(hasattr(compatibility_module, "_COMPILATION_ISSUANCE_TOKEN"))
        self.assertFalse(hasattr(runtime_gate_module, "_ASSESSMENT_ISSUANCE_TOKEN"))

    def test_registry_and_receipt_variants_are_not_exact_evidence_types(self) -> None:
        class RegistryVariant(RecordRegistry):
            def __eq__(self, other: object) -> bool:
                return True

        registry_variant = object.__new__(RegistryVariant)
        decision = evaluate_runtime_gate(None, claim_registry=registry_variant)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_UNKNOWN_CLAIM_REGISTRY", decision.codes)

        class ReceiptVariant(CompilerValidationReceipt):
            def __eq__(self, other: object) -> bool:
                return True

        receipt_variant = object.__new__(ReceiptVariant)
        decision = evaluate_runtime_gate(receipt_variant, self.action)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_UNKNOWN_STRUCTURAL_EVIDENCE", decision.codes)

        class AssessmentVariant(CompilationAssessment):
            def __eq__(self, other: object) -> bool:
                return True

        assessment_variant = object.__new__(AssessmentVariant)
        decision = evaluate_runtime_gate(assessment_variant, self.action)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_UNKNOWN_STRUCTURAL_EVIDENCE", decision.codes)

        class ActionVariant(RuntimeActionDescriptor):
            def __eq__(self, other: object) -> bool:
                return True

        action_variant = object.__new__(ActionVariant)
        decision = evaluate_runtime_gate(None, action_variant)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_UNKNOWN_ACTION_DESCRIPTOR", decision.codes)

    def test_boundary_subclass_is_rejected_across_core_artifacts(self) -> None:
        class BoundaryVariant(ResearchBoundary):
            def __eq__(self, other: object) -> bool:
                return True

        boundary = object.__new__(BoundaryVariant)
        object.__setattr__(boundary, "admission_ring", 3)
        object.__setattr__(boundary, "status", AdmissionStatus.ACCEPT)
        object.__setattr__(boundary, "license_status", LicenseStatus.LICENSED)
        object.__setattr__(boundary, "public_disclosure_authorized", True)

        with self.assertRaisesRegex(CompatibilityError, "Ring 4"):
            replace(self.compilation, boundary=boundary)
        with self.assertRaisesRegex(ValueError, "Ring 4"):
            _rebuild_action(self.action, boundary=boundary)

        registry = RecordRegistry.load(
            CLAIM_LEDGER,
            kind="claim",
            expected_raw_sha256=_raw_sha256(CLAIM_LEDGER),
            expected_schema_raw_sha256=_raw_sha256(CLAIM_SCHEMA),
        )
        with self.assertRaisesRegex(RegistryError, "E-REGISTRY-BOUNDARY"):
            replace(registry, boundary=boundary)

    def test_bound_model_environment_and_action_mismatches_fail_structure(self) -> None:
        cases = (
            (
                _rebuild_action(self.action, model_identity_sha256="0" * 64),
                "DENY_UNBOUND_OR_UNEXPECTED_MODEL_IDENTITY",
            ),
            (
                _rebuild_action(self.action, environment_identity_sha256="0" * 64),
                "DENY_ACTION_ENVIRONMENT_MISMATCH",
            ),
            (
                _rebuild_action(self.action, source_sha256="0" * 64),
                "DENY_ACTION_SOURCE_MISMATCH",
            ),
            (
                _rebuild_action(self.action, compilation_result_sha256="0" * 64),
                "DENY_ACTION_RESULT_MISMATCH",
            ),
        )
        for action, code in cases:
            with self.subTest(code=code):
                assessment = assess_compilation_for_action(self.compilation, action)
                decision = evaluate_runtime_gate(assessment)
                self.assertFalse(decision.structurally_admissible)
                self.assertIn(code, decision.codes)
                self.assertFalse(decision.authorization_granted)

    def test_assessment_is_bound_to_the_exact_passed_action(self) -> None:
        other = _rebuild_action(
            self.action, operation=RuntimeOperation.MODEL_INFERENCE
        )
        decision = evaluate_runtime_gate(self.assessment, other)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_ACTION_ASSESSMENT_MISMATCH", decision.codes)

    def test_claim_bearing_action_has_no_path_even_for_descriptively_licensed_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "claims.json"
            digest = _write_claim_ledger(
                path, [_claim_record(record_id="CLM-TEST-LICENSED", licensed=True)]
            )
            registry = _load_claim_fixture(path, digest)
            record = registry.resolve("CLM-TEST-LICENSED", version="0.1")
            self.assertTrue(claim_is_licensed(record))
            action = RuntimeActionDescriptor.bind(
                self.compilation,
                operation=RuntimeOperation.PUBLISH_CLAIM,
                target=RuntimeTarget.PUBLIC_CLAIM_SURFACE,
                effect_class=RuntimeEffectClass.CLAIM_BEARING,
                claim_id="CLM-TEST-LICENSED",
                claim_version="0.1",
            )
            assessment = assess_compilation_for_action(self.compilation, action)
            decision = evaluate_runtime_gate(
                assessment, claim_registry=registry
            )
        self.assertFalse(decision.structurally_admissible)
        self.assertFalse(decision.authorization_granted)
        self.assertIn("DENY_CLAIM_BEARING_ACTION_NOT_AUTHORIZED", decision.codes)
        self.assertFalse(any(code.startswith("ALLOW") for code in decision.codes))

    def test_external_side_effect_is_categorically_rejected(self) -> None:
        action = RuntimeActionDescriptor.bind(
            self.compilation,
            target=RuntimeTarget.EXTERNAL_SYSTEM,
            effect_class=RuntimeEffectClass.EXTERNAL_SIDE_EFFECT,
        )
        assessment = assess_compilation_for_action(self.compilation, action)
        decision = evaluate_runtime_gate(assessment)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_EXTERNAL_SIDE_EFFECT_NOT_AUTHORIZED", decision.codes)
        self.assertFalse(decision.authorization_granted)

    def test_missing_assessment_fails_closed(self) -> None:
        decision = evaluate_runtime_gate(None, self.action)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_MISSING_COMPILATION_ASSESSMENT", decision.codes)
        self.assertFalse(decision.authorization_granted)

    def test_self_consistent_forged_receipt_profile_remains_only_an_assertion(self) -> None:
        forged = replace(
            self.receipt,
            semantic_profile="invented v8 profile",
            receipt_sha256="0" * 64,
        )
        forged = replace(
            forged,
            receipt_sha256=canonical_json_sha256(forged.payload_without_digest()),
        )
        self.assertTrue(forged.verify_self_digest())
        decision = evaluate_runtime_gate(forged, self.action)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_STRUCTURAL_RECEIPT_NOT_AUTHORIZATION", decision.codes)
        self.assertFalse(decision.authorization_granted)

    def test_corrupt_receipt_is_diagnosed_and_still_cannot_authorize(self) -> None:
        corrupt = replace(self.receipt, receipt_sha256="0" * 64)
        decision = evaluate_runtime_gate(corrupt, self.action)
        self.assertFalse(decision.structurally_admissible)
        self.assertIn("DENY_CORRUPT_COMPILER_VALIDATION", decision.codes)
        self.assertFalse(decision.authorization_granted)


if __name__ == "__main__":
    unittest.main()
