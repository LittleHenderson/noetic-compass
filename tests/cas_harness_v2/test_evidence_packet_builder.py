from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TEST_DIR = Path(__file__).resolve().parent
for candidate in (SRC, TEST_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2 import (  # noqa: E402
    ArtifactByteRegistry,
    ArtifactRef,
    ControlResultInput,
    EVIDENCE_PACKET_EXECUTION_MANIFEST_SCHEMA,
    EvidencePacketBuildInputs,
    FalsifierResultInput,
    MetricResultInput,
    RetainedArtifactInput,
    RetainedFileArtifactInput,
    SchemaValidationError,
    SplitResultInput,
    WorkerAuthorizationArtifact,
    build_evidence_packet,
    build_worker_authorization,
    build_worker_terminal_receipt,
)
from cas_harness_v2.preregistration import PreregistrationChain  # noqa: E402
from cas_harness_v2 import artifacts as artifact_module  # noqa: E402
from test_research_control_kernel import Fixture, artifact_ref  # noqa: E402


def ref_value(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


class BuilderFixture:
    def __init__(self, *, terminal_status: str = "COMPLETED", seal: bool = True) -> None:
        research = Fixture()
        self.base = research.loaded
        self.chain = PreregistrationChain(self.base)
        model = self.base.payload["identities"]["model"]
        self.authorization = build_worker_authorization(
            chain=self.chain,
            authorization_id="builder-auth-h2-001",
            issued_at="2026-08-05T08:30:00Z",
            expires_at="2026-08-05T09:30:00Z",
            execution_mapping={
                "fleet_id": "fleet-research-01",
                "job_id": "job-builder-h2-001",
                "audit_id": "audit-builder-h2-001",
                "assigned_worker_id": "worker-builder-01",
                "layer_start": 7,
                "layer_end": 8,
                "shard_id": "shard-builder-07-08",
                "assigned_methods": ["projector-readout-v1", "matched-control-v1"],
                "expected_outputs": ["raw-outcomes"],
                "lease_model": {
                    "model_id": model["model_id"],
                    "model_revision": model["revision"],
                    "model_artifact_manifest_path": "C:\\research\\model-manifest.json",
                    "model_artifact_manifest_sha256": "d" * 64,
                    "execution_mode": "external_probe_command",
                },
            },
            run_nonce=bytes(range(32)),
        )
        self.output_raw = b"exact completed worker output bytes\n"
        self.output_ref = ArtifactRef(
            **artifact_ref(
                "builder-worker-output-00",
                self.output_raw,
                "application/jsonl",
            )
        )
        if terminal_status == "COMPLETED":
            produced_outputs = (
                {"output_name": "raw-outcomes", "artifact": ref_value(self.output_ref)},
            )
            missing_outputs: tuple[str, ...] = ()
            error = None
        else:
            produced_outputs = ()
            missing_outputs = ("raw-outcomes",)
            error = {
                "code": "fixture-execution-failed",
                "category": "EXECUTION_FAILED",
                "message": "Deliberate negative test failure.",
                "retryable": False,
            }
        self.terminal_receipt = build_worker_terminal_receipt(
            chain=self.chain,
            authorization=self.authorization,
            receipt_id="builder-terminal-h2-001",
            worker_started_at="2026-08-05T08:35:00Z",
            terminal_at="2026-08-05T09:20:00Z",
            terminal_status=terminal_status,
            produced_outputs=produced_outputs,
            missing_outputs=missing_outputs,
            error=error,
        )
        if seal:
            self.chain.record_outcome_access(
                accessed_at="2026-08-05T09:25:00Z",
                execution_completed_at=self.terminal_receipt.terminal_at,
                receipt=self.terminal_receipt.outcome_access_receipt_ref,
            )

        retained = [
            RetainedArtifactInput.from_reference(
                reference,
                research.blobs[reference.artifact_id],
            )
            for reference in self.base.artifact_refs
        ]
        if terminal_status == "COMPLETED":
            retained.append(
                RetainedArtifactInput.from_reference(self.output_ref, self.output_raw)
            )
        for artifact_id in (
            "builder-metric-primary-ba",
            "builder-control-matched-taxonomy",
            "builder-control-wrong-layer",
            "builder-control-clean-null",
            "builder-falsifier-surface-beats-hidden",
            "builder-split-confirmatory",
            "builder-split-replication",
            "builder-uncertainty-report",
            "builder-result-summary",
        ):
            retained.append(
                RetainedArtifactInput(
                    artifact_id=artifact_id,
                    raw_bytes=f"{artifact_id} exact bytes\n".encode("ascii"),
                )
            )
        self.inputs = EvidencePacketBuildInputs(
            packet_id="packet-builder-h2-001",
            created_at="2026-08-05T10:00:00Z",
            execution_manifest_id="builder-execution-manifest",
            retained_artifacts=tuple(retained),
            metrics=(
                MetricResultInput(
                    threshold_id="primary-ba",
                    value="0.80",
                    evidence_artifact_id="builder-metric-primary-ba",
                ),
            ),
            controls=tuple(
                ControlResultInput(
                    control_id=control_id,
                    outcome="PASS",
                    evidence_artifact_id=f"builder-control-{control_id}",
                )
                for control_id in ("matched-taxonomy", "wrong-layer", "clean-null")
            ),
            falsifiers=(
                FalsifierResultInput(
                    falsifier_id="surface-beats-hidden",
                    triggered=False,
                    evidence_artifact_id="builder-falsifier-surface-beats-hidden",
                ),
            ),
            split_results=tuple(
                SplitResultInput(
                    split_id=split_id,
                    groups=40,
                    enrolled_rows=164,
                    analyzed_rows=160,
                    missing_rows=2,
                    excluded_rows=2,
                    evidence_artifact_id=f"builder-split-{split_id}",
                )
                for split_id in ("confirmatory", "replication")
            ),
            uncertainty_artifact_id="builder-uncertainty-report",
            result_summary_artifact_id="builder-result-summary",
            limitations=("Fixture values are synthetic research observations.",),
        )

    def build(self, inputs: EvidencePacketBuildInputs | None = None):
        return build_evidence_packet(
            chain=self.chain,
            authorization=self.authorization,
            terminal_receipt=self.terminal_receipt,
            inputs=self.inputs if inputs is None else inputs,
        )


class EvidencePacketBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = BuilderFixture()

    def _replace_retained(self, artifact_id: str, replacement):
        retained = list(self.fx.inputs.retained_artifacts)
        index = next(
            index
            for index, item in enumerate(retained)
            if item.artifact_id == artifact_id
        )
        retained[index] = replacement
        return replace(self.fx.inputs, retained_artifacts=tuple(retained))

    def test_builder_round_trips_exact_typed_inputs_through_verifier(self) -> None:
        result = self.fx.build()
        assessment = result.assessment
        self.assertEqual(assessment.structural_completeness, "COMPLETE")
        self.assertEqual(assessment.preregistered_criteria, "REPORTED_CRITERIA_MET")
        self.assertEqual(assessment.scientific_eligibility, "NOT_ESTABLISHED")
        self.assertEqual(assessment.authenticated_execution, "UNAVAILABLE")
        self.assertEqual(assessment.independent_numerical_audit, "UNAVAILABLE")
        self.assertEqual(assessment.replication, "UNAVAILABLE")
        self.assertEqual(assessment.claim_language_review, "UNAVAILABLE")
        self.assertEqual(assessment.admission_ring, 4)
        self.assertEqual(assessment.product_claim_status, "NOT LICENSED")
        self.assertEqual(assessment.disclosure_status, "HELD")
        self.assertEqual(assessment.license_decision, "NONE")
        self.assertFalse(assessment.public_release_allowed)
        self.assertFalse(assessment.product_route_allowed)
        self.assertFalse(assessment.self_hash_is_authority)
        self.assertTrue(
            {
                "authenticated_execution_not_established",
                "independent_numerical_audit_not_authenticated",
                "replication_not_authenticated",
                "claim_language_review_not_authenticated",
                "external_scientific_review_not_established",
            }.issubset(assessment.blockers)
        )

    def test_builder_derives_execution_and_outcomes_from_protocol_carriers(self) -> None:
        result = self.fx.build()
        packet = result.packet.payload
        execution = packet["execution"]
        self.assertEqual(execution["run_id"], "job-builder-h2-001")
        self.assertEqual(execution["executor_identity"], "worker-builder-01")
        self.assertEqual(execution["started_at"], self.fx.terminal_receipt.worker_started_at)
        self.assertEqual(execution["completed_at"], self.fx.terminal_receipt.terminal_at)
        self.assertEqual(
            packet["outcome_artifacts"][0]["artifact_id"],
            self.fx.output_ref.artifact_id,
        )
        self.assertTrue(result.artifact_registry.verify(self.fx.output_ref))
        self.assertTrue(
            result.artifact_registry.verify(self.fx.terminal_receipt.artifact_ref)
        )

    def test_builder_accepts_mixed_exact_byte_and_file_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "worker-output.jsonl"
            output_path.write_bytes(self.fx.output_raw)
            file_input = RetainedFileArtifactInput.from_reference(
                self.fx.output_ref,
                output_path,
            )

            result = self.fx.build(
                self._replace_retained(self.fx.output_ref.artifact_id, file_input)
            )
            byte_backed_result = self.fx.build()

            self.assertEqual(file_input.path, output_path.absolute())
            self.assertEqual(file_input.artifact_ref, self.fx.output_ref)
            self.assertEqual(result.packet.raw_bytes, byte_backed_result.packet.raw_bytes)
            self.assertEqual(result.packet.sha256, byte_backed_result.packet.sha256)
            self.assertEqual(result.assessment, byte_backed_result.assessment)
            self.assertEqual(
                result.execution_manifest.raw_bytes,
                byte_backed_result.execution_manifest.raw_bytes,
            )
            self.assertTrue(result.artifact_registry.verify(self.fx.output_ref))
            self.assertTrue(
                result.artifact_registry.verify(self.fx.authorization.artifact_ref)
            )
            self.assertEqual(result.assessment.structural_completeness, "COMPLETE")
            self.assertNotIn(str(output_path).encode(), result.packet.raw_bytes)
            self.assertNotIn(
                str(output_path).encode(),
                result.execution_manifest.raw_bytes,
            )

    def test_file_source_mutation_fails_registration_and_later_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "worker-output.jsonl"
            output_path.write_bytes(self.fx.output_raw)
            file_input = RetainedFileArtifactInput.from_reference(
                self.fx.output_ref,
                output_path,
            )
            output_path.write_bytes(b"changed after capture with different bytes\n")
            with self.assertRaisesRegex(
                SchemaValidationError,
                "changed before registration",
            ):
                ArtifactByteRegistry(
                    {self.fx.output_ref.artifact_id: file_input.registry_source}
                )

            output_path.write_bytes(self.fx.output_raw)
            fresh_input = RetainedFileArtifactInput.from_reference(
                self.fx.output_ref,
                output_path,
            )
            registry = ArtifactByteRegistry(
                {self.fx.output_ref.artifact_id: fresh_input.registry_source}
            )
            output_path.write_bytes(
                b"X" * (len(self.fx.output_raw) - 1) + b"\n"
            )
            self.assertFalse(registry.verify(self.fx.output_ref))
            with self.assertRaisesRegex(
                SchemaValidationError,
                "do not match the bound identity",
            ):
                registry.require(self.fx.output_ref)

    def test_file_source_rejects_identical_byte_path_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_path = root / "worker-output.jsonl"
            replacement_path = root / "replacement.jsonl"
            output_path.write_bytes(self.fx.output_raw)
            file_input = RetainedFileArtifactInput.from_reference(
                self.fx.output_ref,
                output_path,
            )
            registry = ArtifactByteRegistry(
                {self.fx.output_ref.artifact_id: file_input.registry_source}
            )
            replacement_path.write_bytes(self.fx.output_raw)
            os.replace(replacement_path, output_path)

            self.assertFalse(registry.verify(self.fx.output_ref))
            with self.assertRaisesRegex(
                SchemaValidationError,
                "changed before registration",
            ):
                self.fx.build(
                    self._replace_retained(
                        self.fx.output_ref.artifact_id,
                        file_input,
                    )
                )

    def test_file_source_rejects_identical_ancestor_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            output_path = evidence_root / "worker-output.jsonl"
            output_path.write_bytes(self.fx.output_raw)
            file_input = RetainedFileArtifactInput.from_reference(
                self.fx.output_ref,
                output_path,
            )
            registry = ArtifactByteRegistry(
                {self.fx.output_ref.artifact_id: file_input.registry_source}
            )

            old_root = root / "evidence-old"
            evidence_root.rename(old_root)
            evidence_root.mkdir()
            output_path.write_bytes(self.fx.output_raw)

            self.assertFalse(registry.verify(self.fx.output_ref))

    def test_file_source_rejects_leaf_symlink_or_reparse_point(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.jsonl"
            link = root / "linked-output.jsonl"
            target.write_bytes(self.fx.output_raw)
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symbolic links are unavailable: {exc}")

            with self.assertRaisesRegex(
                SchemaValidationError,
                "symbolic link or reparse point",
            ):
                RetainedFileArtifactInput.from_reference(self.fx.output_ref, link)

    def test_file_source_rejects_ancestor_symlink_or_reparse_point(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_directory = root / "real-directory"
            linked_directory = root / "linked-directory"
            real_directory.mkdir()
            nested_target = real_directory / "nested.jsonl"
            nested_target.write_bytes(self.fx.output_raw)
            try:
                linked_directory.symlink_to(real_directory, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symbolic links are unavailable: {exc}")
            with self.assertRaisesRegex(
                SchemaValidationError,
                "symbolic link or reparse point",
            ):
                RetainedFileArtifactInput.from_reference(
                    self.fx.output_ref,
                    linked_directory / nested_target.name,
                )

    def test_file_source_rejects_hard_link_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.jsonl"
            alias = root / "alias.jsonl"
            target.write_bytes(self.fx.output_raw)
            try:
                os.link(target, alias)
            except OSError as exc:
                self.skipTest(f"hard links are unavailable: {exc}")

            with self.assertRaisesRegex(
                SchemaValidationError,
                "hard-link aliases",
            ):
                RetainedFileArtifactInput.from_reference(self.fx.output_ref, alias)

    def test_file_source_rejects_synthetic_windows_reparse_markers(self) -> None:
        identity = artifact_module._StableFileIdentity(  # type: ignore[attr-defined]
            device=1,
            inode=2,
            mode_type=stat.S_IFREG,
            link_count=1,
            byte_count=3,
            mtime_ns=4,
            ctime_ns=5,
            file_attributes=0,
            reparse_tag=0,
        )
        for marked in (
            replace(identity, file_attributes=0x400),
            replace(identity, reparse_tag=0xA000000C),
        ):
            with self.subTest(marked=marked):
                with self.assertRaisesRegex(
                    SchemaValidationError,
                    "reparse point",
                ):
                    artifact_module._validate_unique_regular_file(  # type: ignore[attr-defined]
                        marked
                    )

    def test_file_source_rejects_hash_length_and_nonregular_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "worker-output.jsonl"
            output_path.write_bytes(self.fx.output_raw)
            wrong_hash = replace(self.fx.output_ref, sha256="A" * 64)
            wrong_length = replace(
                self.fx.output_ref,
                byte_length=self.fx.output_ref.byte_length + 1,
            )
            for reference in (wrong_hash, wrong_length):
                with self.subTest(reference=reference):
                    with self.assertRaisesRegex(
                        SchemaValidationError,
                        "retained file does not match reference",
                    ):
                        RetainedFileArtifactInput.from_reference(
                            reference,
                            output_path,
                        )

            with self.assertRaisesRegex(
                SchemaValidationError,
                "regular file",
            ):
                RetainedFileArtifactInput.from_reference(
                    self.fx.output_ref,
                    Path(temporary),
                )

    def test_registry_accepts_only_exact_file_source_with_matching_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "worker-output.jsonl"
            output_path.write_bytes(self.fx.output_raw)
            file_input = RetainedFileArtifactInput.from_reference(
                self.fx.output_ref,
                output_path,
            )
            with self.assertRaisesRegex(
                SchemaValidationError,
                "different identifier",
            ):
                ArtifactByteRegistry({"different-artifact": file_input.registry_source})
            with self.assertRaisesRegex(
                SchemaValidationError,
                "bytes-like data or an exact file source",
            ):
                ArtifactByteRegistry(
                    {self.fx.output_ref.artifact_id: output_path}  # type: ignore[dict-item]
                )

    def test_mixed_inventory_still_rejects_duplicate_artifact_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "worker-output.jsonl"
            output_path.write_bytes(self.fx.output_raw)
            duplicate = RetainedFileArtifactInput.from_reference(
                self.fx.output_ref,
                output_path,
            )
            with self.assertRaisesRegex(SchemaValidationError, "duplicate identifiers"):
                replace(
                    self.fx.inputs,
                    retained_artifacts=(
                        *self.fx.inputs.retained_artifacts,
                        duplicate,
                    ),
                )

    def test_file_registry_verification_streams_without_path_read_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "worker-output.jsonl"
            output_path.write_bytes(self.fx.output_raw)
            with patch.object(
                Path,
                "read_bytes",
                side_effect=AssertionError("full-file read is forbidden"),
            ), patch.object(
                Path,
                "resolve",
                side_effect=AssertionError("link-following resolution is forbidden"),
            ):
                file_input = RetainedFileArtifactInput.from_reference(
                    self.fx.output_ref,
                    output_path,
                )
                registry = ArtifactByteRegistry(
                    {self.fx.output_ref.artifact_id: file_input.registry_source}
                )
                self.assertTrue(registry.verify(self.fx.output_ref))

    def test_execution_manifest_binds_authorization_receipt_and_limits_authority(self) -> None:
        result = self.fx.build()
        manifest = json.loads(result.execution_manifest.raw_bytes)
        self.assertEqual(
            manifest["schema_version"],
            EVIDENCE_PACKET_EXECUTION_MANIFEST_SCHEMA,
        )
        self.assertEqual(
            manifest["authorization"]["sha256"],
            self.fx.authorization.sha256,
        )
        self.assertEqual(
            manifest["terminal_receipt"]["sha256"],
            self.fx.terminal_receipt.sha256,
        )
        self.assertEqual(manifest["run"]["terminal_status"], "COMPLETED")
        self.assertEqual(manifest["assurance"]["scope"], "STRUCTURAL_BINDING_ONLY")
        self.assertEqual(manifest["assurance"]["authenticated_execution"], "NOT_ESTABLISHED")
        self.assertEqual(manifest["assurance"]["scientific_conclusion"], "NOT_ESTABLISHED")
        self.assertEqual(manifest["assurance"]["license"], "NOT_GRANTED")
        self.assertEqual(manifest["assurance"]["product_route"], "NOT_AUTHORIZED")
        self.assertEqual(manifest["assurance"]["disclosure"], "HELD")

    def test_builder_is_deterministic_for_identical_exact_inputs(self) -> None:
        first = self.fx.build()
        second = self.fx.build()
        self.assertEqual(first.packet.raw_bytes, second.packet.raw_bytes)
        self.assertEqual(first.packet.sha256, second.packet.sha256)
        self.assertEqual(
            first.execution_manifest.raw_bytes,
            second.execution_manifest.raw_bytes,
        )

    def test_negative_control_is_preserved_as_ineligible_not_rewritten(self) -> None:
        controls = list(self.fx.inputs.controls)
        controls[0] = replace(controls[0], outcome="FAIL")
        result = self.fx.build(replace(self.fx.inputs, controls=tuple(controls)))
        self.assertEqual(result.assessment.structural_completeness, "COMPLETE")
        self.assertEqual(
            result.assessment.preregistered_criteria,
            "REPORTED_CRITERIA_NOT_MET",
        )
        self.assertEqual(result.assessment.scientific_eligibility, "INELIGIBLE")
        self.assertIn(
            "control_fail:matched-taxonomy",
            result.assessment.blockers,
        )
        self.assertEqual(
            result.packet.payload["scientific_evidence"]["controls"][0]["outcome"],
            "FAIL",
        )

    def test_builder_rejects_unsealed_chain(self) -> None:
        fixture = BuilderFixture(seal=False)
        with self.assertRaisesRegex(SchemaValidationError, "sealed outcome-access"):
            fixture.build()

    def test_builder_rejects_failed_terminal_receipt(self) -> None:
        fixture = BuilderFixture(terminal_status="FAILED")
        with self.assertRaisesRegex(SchemaValidationError, "COMPLETED terminal receipt"):
            fixture.build()

    def test_builder_rejects_forged_authorization_projection(self) -> None:
        forged = replace(self.fx.authorization, sha256="A" * 64)
        self.assertIsInstance(forged, WorkerAuthorizationArtifact)
        with self.assertRaisesRegex(SchemaValidationError, "fresh exact-byte replay"):
            build_evidence_packet(
                chain=self.fx.chain,
                authorization=forged,
                terminal_receipt=self.fx.terminal_receipt,
                inputs=self.fx.inputs,
            )

    def test_builder_rejects_incomplete_or_extra_artifact_inventory(self) -> None:
        missing = replace(
            self.fx.inputs,
            retained_artifacts=self.fx.inputs.retained_artifacts[:-1],
        )
        with self.assertRaisesRegex(SchemaValidationError, "missing=.*builder-result-summary"):
            self.fx.build(missing)

        extra = replace(
            self.fx.inputs,
            retained_artifacts=(
                *self.fx.inputs.retained_artifacts,
                RetainedArtifactInput("builder-unused", b"unused exact bytes\n"),
            ),
        )
        with self.assertRaisesRegex(SchemaValidationError, "extra=.*builder-unused"):
            self.fx.build(extra)

    def test_builder_rejects_terminal_output_byte_mismatch(self) -> None:
        retained = list(self.fx.inputs.retained_artifacts)
        index = next(
            index
            for index, item in enumerate(retained)
            if item.artifact_id == self.fx.output_ref.artifact_id
        )
        retained[index] = RetainedArtifactInput(
            artifact_id=self.fx.output_ref.artifact_id,
            raw_bytes=b"forged output bytes\n",
            media_type=self.fx.output_ref.media_type,
        )
        with self.assertRaisesRegex(SchemaValidationError, "does not match its bound reference"):
            self.fx.build(
                replace(self.fx.inputs, retained_artifacts=tuple(retained))
            )

    def test_builder_requires_exact_preregistered_result_coverage(self) -> None:
        missing_metric = replace(self.fx.inputs, metrics=())
        with self.assertRaisesRegex(SchemaValidationError, "missing=.*primary-ba"):
            self.fx.build(missing_metric)

    def test_builder_rejects_reused_artifact_across_packet_roles(self) -> None:
        reused = replace(
            self.fx.inputs,
            uncertainty_artifact_id=self.fx.inputs.result_summary_artifact_id,
        )
        with self.assertRaisesRegex(SchemaValidationError, "duplicate identifiers"):
            self.fx.build(reused)

        protocol_collision = replace(
            self.fx.inputs,
            execution_manifest_id=self.fx.authorization.authorization_id,
        )
        with self.assertRaisesRegex(
            SchemaValidationError,
            "protocol artifact identifiers.*duplicate",
        ):
            self.fx.build(protocol_collision)

    def test_typed_inputs_reject_mutable_or_coerced_values(self) -> None:
        with self.assertRaisesRegex(SchemaValidationError, "exact tuple"):
            replace(
                self.fx.inputs,
                controls=list(self.fx.inputs.controls),  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(SchemaValidationError, "exact bytes"):
            RetainedArtifactInput(
                artifact_id="mutable-bytes",
                raw_bytes=bytearray(b"mutable"),  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(SchemaValidationError, "exact integer"):
            SplitResultInput(
                split_id="coerced-split",
                groups="40",  # type: ignore[arg-type]
                enrolled_rows=164,
                analyzed_rows=160,
                missing_rows=2,
                excluded_rows=2,
                evidence_artifact_id="coerced-split-evidence",
            )


if __name__ == "__main__":
    unittest.main()
