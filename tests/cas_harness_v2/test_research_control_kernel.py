from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2 import (  # noqa: E402
    AmbiguousV1UpgradeError,
    ArtifactByteRegistry,
    ArtifactRef,
    SchemaValidationError,
    StrictJSONError,
    canonical_json_bytes,
    canonical_sha256,
    load_evidence_packet,
    load_preregistration,
    reject_automatic_v1_upgrade,
    sha256_bytes,
    verify_evidence_packet,
)
from cas_harness_v2.preregistration import PreregistrationChain  # noqa: E402


CLAIM_LEDGER_PATH = ROOT / "docs" / "working" / "project_coherence" / "CLAIM_LEDGER_v0.1.json"


def encode(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def artifact_ref(artifact_id: str, raw: bytes, media_type: str = "application/octet-stream") -> dict:
    return {
        "artifact_id": artifact_id,
        "sha256": sha256_bytes(raw),
        "byte_length": len(raw),
        "media_type": media_type,
    }


def governance() -> dict:
    return {
        "admission_ring": 4,
        "product_claim_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "public_release": False,
        "product_route": False,
        "license_decision": "NONE",
    }


class Fixture:
    def __init__(self) -> None:
        self.claim_ledger_bytes = CLAIM_LEDGER_PATH.read_bytes()
        ledger = json.loads(self.claim_ledger_bytes)
        record = next(row for row in ledger["records"] if row["id"] == "CLM-PROJECTOR-LATENT-CAPACITY")
        self.blobs: dict[str, bytes] = {
            "claim-ledger": self.claim_ledger_bytes,
            "split-confirmatory": b"confirmatory split bytes\n",
            "split-replication": b"replication split bytes\n",
            "model-weights": b"model weights bytes\n",
            "tokenizer": b"tokenizer bytes\n",
            "source-manifest": b"source manifest bytes\n",
            "analysis-manifest": b"analysis manifest bytes\n",
            "dependency-lock": b"dependency lock bytes\n",
            "power-analysis": b"fixed sample power analysis bytes\n",
        }
        self.prereg = {
            "schema_version": "cas_harness_v2.preregistration.v1",
            "preregistration_id": "PREREG-H2-001",
            "created_at": "2026-08-05T08:00:00Z",
            "claim_binding": {
                "claim_ledger": artifact_ref(
                    "claim-ledger", self.blobs["claim-ledger"], "application/json"
                ),
                "claim_id": record["id"],
                "claim_text": record["claim_text"],
                "claim_record_sha256": canonical_sha256(record),
            },
            "hypothesis": {
                "primary": "The registered projector signal exceeds the matched controls.",
                "null": "The registered projector signal does not exceed the matched controls.",
                "estimand": "Held-out group balanced accuracy.",
                "direction": "GREATER",
            },
            "units": [
                {
                    "measure_id": "balanced_accuracy",
                    "unit": "fraction",
                    "operational_definition": "Group-held-out balanced accuracy on the frozen labels.",
                    "measurement_kind": "DERIVED",
                }
            ],
            "splits": [
                {
                    "split_id": "confirmatory",
                    "role": "CONFIRMATORY",
                    "source_artifact": artifact_ref(
                        "split-confirmatory", self.blobs["split-confirmatory"]
                    ),
                    "allocation_rule": "Whole prompt groups assigned before execution.",
                    "grouping_key": "prompt_id",
                    "minimum_groups": 40,
                    "target_groups": 40,
                    "target_enrolled_rows": 164,
                    "target_analyzed_rows": 160,
                    "maximum_missing_rows": 2,
                    "maximum_excluded_rows": 2,
                },
                {
                    "split_id": "replication",
                    "role": "HELD_OUT_REPLICATION",
                    "source_artifact": artifact_ref(
                        "split-replication", self.blobs["split-replication"]
                    ),
                    "allocation_rule": "Disjoint held-out prompt groups.",
                    "grouping_key": "prompt_id",
                    "minimum_groups": 40,
                    "target_groups": 40,
                    "target_enrolled_rows": 164,
                    "target_analyzed_rows": 160,
                    "maximum_missing_rows": 2,
                    "maximum_excluded_rows": 2,
                },
            ],
            "fixed_sample_plan": {
                "stopping_rule": "FIXED_SAMPLE",
                "interim_outcome_access": "FORBIDDEN",
                "row_accounting": (
                    "DISJOINT_ENROLLED_EQUALS_ANALYZED_PLUS_MISSING_PLUS_EXCLUDED"
                ),
                "exclusion_rule": (
                    "Exclude only rows that fail the frozen pre-outcome parser-validity rule."
                ),
                "missing_data_rule": (
                    "Classify a row as missing only when the frozen executor emits no outcome."
                ),
                "deviation_effect": "SCIENTIFICALLY_INELIGIBLE",
                "power_analysis": artifact_ref(
                    "power-analysis", self.blobs["power-analysis"]
                ),
            },
            "thresholds": [
                {
                    "threshold_id": "primary-ba",
                    "measure_id": "balanced_accuracy",
                    "operator": "GE",
                    "value": "0.75",
                    "unit": "fraction",
                    "decision_effect": "REQUIRED_FOR_REPORTED_PASS",
                }
            ],
            "controls": [
                {
                    "control_id": "matched-taxonomy",
                    "kind": "MATCHED_TAXONOMY",
                    "procedure": "Run the identical grouped evaluator on matched non-CAS labels.",
                    "expected_result": "Candidate exceeds control by the preregistered margin.",
                    "failure_effect": "FAIL",
                },
                {
                    "control_id": "wrong-layer",
                    "kind": "WRONG_LAYER",
                    "procedure": "Run the same readout at the frozen wrong layer.",
                    "expected_result": "Wrong-layer result remains below the candidate.",
                    "failure_effect": "INVALID",
                },
                {
                    "control_id": "clean-null",
                    "kind": "CLEAN_NULL",
                    "procedure": "Run the frozen clean-null bank.",
                    "expected_result": "Null remains at chance.",
                    "failure_effect": "INVALID",
                },
            ],
            "falsifiers": [
                {
                    "falsifier_id": "surface-beats-hidden",
                    "condition": "A frozen surface baseline equals or exceeds the hidden readout.",
                    "consequence": "FAIL",
                }
            ],
            "uncertainty": {
                "method": "Grouped permutation plus group bootstrap.",
                "confidence_level": "0.95",
                "multiplicity_correction": "Holm across registered primary contrasts.",
                "permutations": 10000,
                "seeds": [20260805, 20260806],
                "grouping_unit": "prompt_id",
            },
            "identities": {
                "model": {
                    "model_id": "example/research-model",
                    "revision": "0123456789abcdef0123456789abcdef01234567",
                    "weights": artifact_ref("model-weights", self.blobs["model-weights"]),
                    "tokenizer": artifact_ref("tokenizer", self.blobs["tokenizer"]),
                    "license_basis": "Private authorized research only.",
                },
                "code": {
                    "commit_sha": "a" * 40,
                    "dirty_worktree": False,
                    "source_manifest": artifact_ref(
                        "source-manifest", self.blobs["source-manifest"]
                    ),
                    "analysis_manifest": artifact_ref(
                        "analysis-manifest", self.blobs["analysis-manifest"]
                    ),
                },
                "environment": {
                    "environment_id": "env-h2-001",
                    "runtime": "CPython 3.14.0",
                    "dependency_lock": artifact_ref(
                        "dependency-lock", self.blobs["dependency-lock"]
                    ),
                    "container_image_digest": "sha256:" + "b" * 64,
                    "hardware_profile": "Research CPU fixture; no production inference claim.",
                },
            },
            "permitted_wording": {
                "allowed": [
                    "In this preregistered private experiment, the reported values met the frozen criteria."
                ],
                "forbidden": [
                    "CAS Harness is proven safe.",
                    "This result is licensed for customers.",
                ],
                "claim_ceiling": "PRIVATE_RESEARCH_RESULT",
            },
            "governance": governance(),
        }
        self.prereg_bytes = encode(self.prereg)
        self.loaded = load_preregistration(
            self.prereg_bytes, claim_ledger_bytes=self.claim_ledger_bytes
        )
        self.chain = PreregistrationChain(self.loaded)
        self.blobs["outcome-access-receipt"] = b"outcome access receipt bytes\n"
        self.chain.record_outcome_access(
            accessed_at="2026-08-05T09:30:00Z",
            execution_completed_at="2026-08-05T09:20:00Z",
            receipt=ArtifactRef(**artifact_ref("outcome-access-receipt", self.blobs["outcome-access-receipt"])),
        )
        self._build_packet()

    def _put(self, artifact_id: str, content: bytes | None = None) -> dict:
        raw = content if content is not None else f"{artifact_id} bytes\n".encode()
        self.blobs[artifact_id] = raw
        return artifact_ref(artifact_id, raw)

    def _build_packet(self) -> None:
        self.packet = {
            "schema_version": "cas_harness_v2.evidence_packet.v2",
            "packet_id": "PACKET-H2-001",
            "created_at": "2026-08-05T10:00:00Z",
            "claim_binding": {
                "claim_id": self.loaded.claim_id,
                "claim_record_sha256": self.loaded.claim_record_sha256,
                "preregistration_sha256": self.loaded.sha256,
                "protected_design_sha256": self.loaded.protected_design_sha256,
                "preregistration_chain_sha256": self.chain.chain_sha256,
            },
            "outcome_artifacts": [self._put("raw-outcomes")],
            "execution": {
                "run_id": "run-h2-001",
                "started_at": "2026-08-05T09:01:00Z",
                "completed_at": "2026-08-05T09:20:00Z",
                "executor_identity": "executor-research-01",
                "execution_manifest": self._put("execution-manifest"),
                "authentication": {
                    "availability": "UNAVAILABLE",
                    "reason": "No materialized external trust root is wired into this isolated kernel.",
                },
            },
            "scientific_evidence": {
                "metrics": [
                    {
                        "threshold_id": "primary-ba",
                        "measure_id": "balanced_accuracy",
                        "value": "0.80",
                        "unit": "fraction",
                        "evidence_artifact": self._put("metric-primary-ba"),
                    }
                ],
                "controls": [
                    {
                        "control_id": control_id,
                        "outcome": "PASS",
                        "evidence_artifact": self._put(f"control-{control_id}"),
                    }
                    for control_id in ("matched-taxonomy", "wrong-layer", "clean-null")
                ],
                "falsifiers": [
                    {
                        "falsifier_id": "surface-beats-hidden",
                        "triggered": False,
                        "evidence_artifact": self._put("falsifier-surface-beats-hidden"),
                    }
                ],
                "split_results": [
                    {
                        "split_id": split_id,
                        "groups": 40,
                        "enrolled_rows": 164,
                        "analyzed_rows": 160,
                        "missing_rows": 2,
                        "excluded_rows": 2,
                        "evidence_artifact": self._put(f"split-result-{split_id}"),
                    }
                    for split_id in ("confirmatory", "replication")
                ],
                "uncertainty_artifact": self._put("uncertainty-report"),
                "result_summary": self._put("result-summary"),
                "limitations": [
                    "Reported values are not authenticated by this isolated kernel.",
                    "No product, safety, causal, licensing, or disclosure authority is created.",
                ],
            },
            "independent_numerical_audit": {
                "availability": "UNAVAILABLE",
                "reason": "Independent numerical audit has not been attached.",
            },
            "replication": {
                "availability": "UNAVAILABLE",
                "reason": "Held-out independent replication has not been attached.",
            },
            "claim_language_review": {
                "availability": "UNAVAILABLE",
                "reason": "Independent claim-language review has not been attached.",
            },
            "governance": governance(),
        }
        self.packet_bytes = encode(self.packet)

    def load_packet(self, packet: dict | None = None):
        return load_evidence_packet(encode(self.packet if packet is None else packet), chain=self.chain)

    def registry(self) -> ArtifactByteRegistry:
        return ArtifactByteRegistry(self.blobs)


class PreregistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()

    def test_exact_bytes_and_claim_record_are_bound(self) -> None:
        self.assertEqual(self.fx.loaded.raw_bytes, self.fx.prereg_bytes)
        self.assertEqual(self.fx.loaded.sha256, sha256_bytes(self.fx.prereg_bytes))
        self.assertEqual(self.fx.loaded.claim_id, "CLM-PROJECTOR-LATENT-CAPACITY")
        self.assertEqual(self.fx.loaded.payload["governance"]["admission_ring"], 4)

    def test_source_bytearray_is_snapshotted(self) -> None:
        mutable = bytearray(self.fx.prereg_bytes)
        loaded = load_preregistration(mutable, claim_ledger_bytes=self.fx.claim_ledger_bytes)
        original_hash = loaded.sha256
        mutable[0] = ord("[")
        self.assertEqual(loaded.sha256, original_hash)
        self.assertEqual(loaded.raw_bytes, self.fx.prereg_bytes)

    def test_loaded_dataclass_and_payload_are_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.fx.loaded.sha256 = "0" * 64
        with self.assertRaises(TypeError):
            self.fx.loaded.payload["governance"] = {}
        with self.assertRaises(TypeError):
            self.fx.loaded.payload["governance"]["admission_ring"] = 1

    def test_duplicate_json_key_is_rejected(self) -> None:
        raw = self.fx.prereg_bytes.replace(
            b'"preregistration_id":',
            b'"preregistration_id":"forged","preregistration_id":',
            1,
        )
        with self.assertRaises(StrictJSONError):
            load_preregistration(raw, claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_missing_top_level_field_is_rejected(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        del value["thresholds"]
        with self.assertRaisesRegex(SchemaValidationError, "missing required"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_extra_field_and_self_hash_are_rejected(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["self_hash"] = "A" * 64
        with self.assertRaisesRegex(SchemaValidationError, "forbidden extra"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_wrong_claim_ledger_raw_hash_is_rejected(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["claim_binding"]["claim_ledger"]["sha256"] = "A" * 64
        with self.assertRaisesRegex(SchemaValidationError, "exact-byte identity"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_wrong_claim_record_hash_is_rejected(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["claim_binding"]["claim_record_sha256"] = "A" * 64
        with self.assertRaisesRegex(SchemaValidationError, "record canonical hash"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_wrong_claim_text_is_rejected(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["claim_binding"]["claim_text"] = "Rewritten after the fact."
        with self.assertRaisesRegex(SchemaValidationError, "claim text"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_forged_governance_is_rejected(self) -> None:
        for field, forged in (
            ("admission_ring", 3),
            ("product_claim_status", "LICENSED"),
            ("disclosure_status", "PUBLIC"),
            ("public_release", True),
            ("product_route", True),
            ("license_decision", "ACCEPT"),
        ):
            with self.subTest(field=field):
                value = json.loads(self.fx.prereg_bytes)
                value["governance"][field] = forged
                with self.assertRaises(SchemaValidationError):
                    load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_numeric_threshold_instead_of_decimal_string_is_rejected(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["thresholds"][0]["value"] = 0.75
        with self.assertRaises(StrictJSONError):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_bool_cannot_masquerade_as_integer(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["splits"][0]["minimum_groups"] = True
        with self.assertRaisesRegex(SchemaValidationError, "exact integer"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_model_revision_rejects_branch_name_and_short_sha(self) -> None:
        for invalid_revision in ("main", "0123456789abcdef"):
            with self.subTest(revision=invalid_revision):
                value = json.loads(self.fx.prereg_bytes)
                value["identities"]["model"]["revision"] = invalid_revision
                with self.assertRaisesRegex(SchemaValidationError, "40-character Git SHA"):
                    load_preregistration(
                        encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes
                    )

    def test_container_image_requires_exact_lowercase_digest(self) -> None:
        for invalid_digest in (
            "example/image:latest",
            "sha256:" + "A" * 64,
            "sha256:" + "a" * 63,
        ):
            with self.subTest(digest=invalid_digest):
                value = json.loads(self.fx.prereg_bytes)
                value["identities"]["environment"]["container_image_digest"] = invalid_digest
                with self.assertRaisesRegex(SchemaValidationError, "exact lowercase"):
                    load_preregistration(
                        encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes
                    )

    def test_threshold_unit_must_match_registered_measure_unit(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["thresholds"][0]["unit"] = "percent"
        with self.assertRaisesRegex(SchemaValidationError, "registered measure unit"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_allowed_and_forbidden_wording_cannot_overlap_after_normalization(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        allowed = value["permitted_wording"]["allowed"][0]
        value["permitted_wording"]["forbidden"].append(f"  {allowed.upper()}  ")
        with self.assertRaisesRegex(SchemaValidationError, "must not overlap"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_required_control_families_cannot_be_omitted(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["controls"] = value["controls"][:1]
        with self.assertRaisesRegex(SchemaValidationError, "control kinds"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_confirmatory_and_replication_splits_are_required(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["splits"] = value["splits"][:1]
        with self.assertRaisesRegex(SchemaValidationError, "HELD_OUT_REPLICATION"):
            load_preregistration(encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes)

    def test_fixed_sample_plan_and_power_analysis_are_protected(self) -> None:
        self.assertEqual(
            self.fx.loaded.payload["fixed_sample_plan"]["stopping_rule"],
            "FIXED_SAMPLE",
        )
        self.assertIn(
            "power-analysis",
            {reference.artifact_id for reference in self.fx.loaded.artifact_refs},
        )
        changed = json.loads(self.fx.prereg_bytes)
        changed["fixed_sample_plan"]["exclusion_rule"] = "A different prospective rule."
        reloaded = load_preregistration(
            encode(changed), claim_ledger_bytes=self.fx.claim_ledger_bytes
        )
        self.assertNotEqual(
            reloaded.protected_design_sha256,
            self.fx.loaded.protected_design_sha256,
        )

    def test_fixed_sample_target_groups_cannot_be_below_split_floor(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["splits"][0]["target_groups"] = 39
        with self.assertRaisesRegex(SchemaValidationError, "at least minimum_groups"):
            load_preregistration(
                encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes
            )

    def test_fixed_sample_plan_cannot_enable_interim_outcome_access(self) -> None:
        value = json.loads(self.fx.prereg_bytes)
        value["fixed_sample_plan"]["interim_outcome_access"] = "PERMITTED"
        with self.assertRaises(SchemaValidationError):
            load_preregistration(
                encode(value), claim_ledger_bytes=self.fx.claim_ledger_bytes
            )


class AmendmentTests(unittest.TestCase):
    def setUp(self) -> None:
        fx = Fixture()
        self.base = fx.loaded
        self.chain = PreregistrationChain(self.base)
        self.fx = fx

    def amendment(self, *, previous: str | None = None, **overrides) -> dict:
        value = {
            "schema_version": "cas_harness_v2.preregistration_amendment.v1",
            "amendment_id": "AMD-H2-001",
            "created_at": "2026-08-05T08:15:00Z",
            "base_preregistration_sha256": self.base.sha256,
            "previous_amendment_sha256": previous,
            "reason": "Record a non-operative clarification before outcome access.",
            "change_class": "ADMINISTRATIVE_CLARIFICATION",
            "changes": {"nonoperative_note": "This note does not alter the frozen design."},
            "outcome_access": {"accessed": False, "evidence_ref": None},
        }
        value.update(overrides)
        return value

    def test_append_only_hash_chain(self) -> None:
        first = self.chain.append_amendment(encode(self.amendment()))
        second_value = self.amendment(
            previous=first.sha256,
            amendment_id="AMD-H2-002",
            created_at="2026-08-05T08:20:00Z",
        )
        second = self.chain.append_amendment(encode(second_value))
        self.assertEqual(second.previous_amendment_sha256, first.sha256)
        self.assertEqual(self.chain.amendments, (first, second))

    def test_wrong_base_hash_is_rejected(self) -> None:
        value = self.amendment(base_preregistration_sha256="A" * 64)
        with self.assertRaisesRegex(SchemaValidationError, "base preregistration"):
            self.chain.append_amendment(encode(value))

    def test_wrong_previous_hash_is_rejected(self) -> None:
        with self.assertRaisesRegex(SchemaValidationError, "previous-link"):
            self.chain.append_amendment(encode(self.amendment(previous="A" * 64)))

    def test_chain_rejects_directly_forged_preregistration_carrier(self) -> None:
        forged = replace(self.base, claim_id="FORGED-CLAIM")
        with self.assertRaisesRegex(SchemaValidationError, "fresh exact-byte loader replay"):
            PreregistrationChain(forged)

    def test_duplicate_amendment_id_is_rejected(self) -> None:
        first = self.chain.append_amendment(encode(self.amendment()))
        value = self.amendment(previous=first.sha256)
        with self.assertRaisesRegex(SchemaValidationError, "duplicate amendment_id"):
            self.chain.append_amendment(encode(value))

    def test_amendment_timestamp_must_increase(self) -> None:
        value = self.amendment(created_at="2026-08-05T07:59:59Z")
        with self.assertRaisesRegex(SchemaValidationError, "timestamps must increase"):
            self.chain.append_amendment(encode(value))

    def test_amendment_artifact_id_cannot_shadow_frozen_identity(self) -> None:
        value = self.amendment(
            change_class="EXECUTION_IDENTITY_ADDITION",
            changes={
                "additional_artifacts": [
                    artifact_ref("model-weights", self.fx.blobs["model-weights"])
                ]
            },
        )
        with self.assertRaisesRegex(SchemaValidationError, "append-only and unique"):
            self.chain.append_amendment(encode(value))

    def test_retrospective_threshold_patch_has_no_schema_path(self) -> None:
        value = self.amendment(changes={"thresholds": [{"value": "0.50"}]})
        with self.assertRaises(SchemaValidationError):
            self.chain.append_amendment(encode(value))

    def test_amendment_declared_after_outcome_access_is_rejected(self) -> None:
        value = self.amendment(
            outcome_access={
                "accessed": True,
                "evidence_ref": artifact_ref("outcome", b"outcome"),
            }
        )
        with self.assertRaisesRegex(SchemaValidationError, "after outcome access"):
            self.chain.append_amendment(encode(value))

    def test_chain_seals_on_outcome_access(self) -> None:
        receipt_raw = b"seal receipt"
        self.chain.record_outcome_access(
            accessed_at="2026-08-05T08:30:00Z",
            execution_completed_at="2026-08-05T08:29:00Z",
            receipt=ArtifactRef(**artifact_ref("seal-receipt", receipt_raw)),
        )
        with self.assertRaisesRegex(SchemaValidationError, "sealed"):
            self.chain.append_amendment(encode(self.amendment()))

    def test_outcome_access_cannot_be_recorded_twice(self) -> None:
        ref = ArtifactRef(**artifact_ref("seal-receipt", b"seal receipt"))
        self.chain.record_outcome_access(
            accessed_at="2026-08-05T08:30:00Z",
            execution_completed_at="2026-08-05T08:29:00Z",
            receipt=ref,
        )
        with self.assertRaisesRegex(SchemaValidationError, "already recorded"):
            self.chain.record_outcome_access(
                accessed_at="2026-08-05T08:31:00Z",
                execution_completed_at="2026-08-05T08:29:00Z",
                receipt=ref,
            )

    def test_outcome_access_must_follow_frozen_chain(self) -> None:
        ref = ArtifactRef(**artifact_ref("seal-receipt", b"seal receipt"))
        with self.assertRaisesRegex(SchemaValidationError, "must follow"):
            self.chain.record_outcome_access(
                accessed_at="2026-08-05T07:59:59Z",
                execution_completed_at="2026-08-05T07:59:58Z",
                receipt=ref,
            )

    def test_outcome_access_cannot_precede_execution_completion(self) -> None:
        ref = ArtifactRef(**artifact_ref("seal-receipt", b"seal receipt"))
        with self.assertRaisesRegex(SchemaValidationError, "cannot precede"):
            self.chain.record_outcome_access(
                accessed_at="2026-08-05T08:29:00Z",
                execution_completed_at="2026-08-05T08:30:00Z",
                receipt=ref,
            )


class EvidencePacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()

    def test_valid_packet_is_structurally_complete_but_not_scientifically_eligible(self) -> None:
        packet = self.fx.load_packet()
        assessment = verify_evidence_packet(
            packet, chain=self.fx.chain, artifact_registry=self.fx.registry()
        )
        self.assertEqual(assessment.structural_completeness, "COMPLETE")
        self.assertEqual(assessment.authenticated_execution, "UNAVAILABLE")
        self.assertEqual(assessment.preregistered_criteria, "REPORTED_CRITERIA_MET")
        self.assertEqual(assessment.scientific_eligibility, "NOT_ESTABLISHED")
        self.assertEqual(assessment.independent_numerical_audit, "UNAVAILABLE")
        self.assertEqual(assessment.replication, "UNAVAILABLE")
        self.assertEqual(assessment.claim_language_review, "UNAVAILABLE")
        self.assertEqual(assessment.product_claim_status, "NOT LICENSED")
        self.assertEqual(assessment.disclosure_status, "HELD")
        self.assertFalse(assessment.public_release_allowed)
        self.assertFalse(assessment.product_route_allowed)
        self.assertFalse(assessment.self_hash_is_authority)

    def test_packet_source_bytearray_is_snapshotted(self) -> None:
        mutable = bytearray(self.fx.packet_bytes)
        packet = load_evidence_packet(mutable, chain=self.fx.chain)
        original = packet.sha256
        mutable[0] = ord("[")
        self.assertEqual(packet.sha256, original)
        self.assertEqual(packet.raw_bytes, self.fx.packet_bytes)

    def test_packet_payload_is_immutable(self) -> None:
        packet = self.fx.load_packet()
        with self.assertRaises(TypeError):
            packet.payload["governance"]["public_release"] = True

    def test_packet_before_outcome_access_is_rejected(self) -> None:
        chain = PreregistrationChain(self.fx.loaded)
        packet = json.loads(self.fx.packet_bytes)
        packet["claim_binding"]["preregistration_chain_sha256"] = chain.chain_sha256
        with self.assertRaisesRegex(SchemaValidationError, "before outcome access"):
            load_evidence_packet(encode(packet), chain=chain)

    def test_packet_duplicate_key_is_rejected(self) -> None:
        raw = self.fx.packet_bytes.replace(
            b'"packet_id":', b'"packet_id":"forged","packet_id":', 1
        )
        with self.assertRaises(StrictJSONError):
            load_evidence_packet(raw, chain=self.fx.chain)

    def test_packet_missing_section_is_rejected(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        del packet["replication"]
        with self.assertRaisesRegex(SchemaValidationError, "missing required"):
            self.fx.load_packet(packet)

    def test_forged_status_field_is_rejected(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["scientific_eligibility"] = "ELIGIBLE"
        with self.assertRaisesRegex(SchemaValidationError, "forbidden extra"):
            self.fx.load_packet(packet)

    def test_self_hash_field_is_rejected_and_cannot_mint_authority(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["self_hash"] = sha256_bytes(self.fx.packet_bytes)
        with self.assertRaisesRegex(SchemaValidationError, "forbidden extra"):
            self.fx.load_packet(packet)

    def test_wrong_preregistration_hash_is_rejected(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["claim_binding"]["preregistration_sha256"] = "A" * 64
        with self.assertRaisesRegex(SchemaValidationError, "does not match"):
            self.fx.load_packet(packet)

    def test_verifier_rejects_directly_forged_packet_carrier(self) -> None:
        loaded = self.fx.load_packet()
        forged = replace(loaded, sha256="A" * 64)
        with self.assertRaisesRegex(SchemaValidationError, "fresh exact-byte loader replay"):
            verify_evidence_packet(
                forged, chain=self.fx.chain, artifact_registry=self.fx.registry()
            )

    def test_wrong_chain_hash_is_rejected(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["claim_binding"]["preregistration_chain_sha256"] = "B" * 64
        with self.assertRaisesRegex(SchemaValidationError, "sealed chain"):
            self.fx.load_packet(packet)

    def test_packet_creation_must_follow_execution(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["created_at"] = "2026-08-05T09:19:00Z"
        with self.assertRaisesRegex(SchemaValidationError, "creation must follow"):
            self.fx.load_packet(packet)

    def test_packet_execution_completion_must_match_outcome_access_seal(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["execution"]["completed_at"] = "2026-08-05T09:21:00Z"
        with self.assertRaisesRegex(SchemaValidationError, "sealed outcome-access"):
            self.fx.load_packet(packet)

    def test_packet_artifact_id_cannot_shadow_preregistration_artifact(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["outcome_artifacts"][0] = artifact_ref(
            "model-weights", self.fx.blobs["model-weights"]
        )
        with self.assertRaisesRegex(SchemaValidationError, "distinct from preregistration"):
            self.fx.load_packet(packet)

    def test_wrong_evidence_bytes_make_structure_incomplete(self) -> None:
        packet = self.fx.load_packet()
        corrupted = dict(self.fx.blobs)
        corrupted["metric-primary-ba"] = b"wrong metric bytes"
        assessment = verify_evidence_packet(
            packet,
            chain=self.fx.chain,
            artifact_registry=ArtifactByteRegistry(corrupted),
        )
        self.assertEqual(assessment.structural_completeness, "INCOMPLETE")
        self.assertIn("artifact_identity_unverified:metric-primary-ba", assessment.blockers)

    def test_missing_evidence_bytes_make_structure_incomplete(self) -> None:
        packet = self.fx.load_packet()
        incomplete = dict(self.fx.blobs)
        del incomplete["result-summary"]
        assessment = verify_evidence_packet(
            packet,
            chain=self.fx.chain,
            artifact_registry=ArtifactByteRegistry(incomplete),
        )
        self.assertEqual(assessment.structural_completeness, "INCOMPLETE")
        self.assertIn("artifact_identity_unverified:result-summary", assessment.blockers)

    def test_failed_threshold_is_ineligible(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["scientific_evidence"]["metrics"][0]["value"] = "0.70"
        loaded = self.fx.load_packet(packet)
        assessment = verify_evidence_packet(
            loaded, chain=self.fx.chain, artifact_registry=self.fx.registry()
        )
        self.assertEqual(assessment.preregistered_criteria, "REPORTED_CRITERIA_NOT_MET")
        self.assertEqual(assessment.scientific_eligibility, "INELIGIBLE")
        self.assertIn("threshold_not_met:primary-ba", assessment.blockers)
        self.assertIn("authenticated_execution_not_established", assessment.blockers)
        self.assertIn("independent_numerical_audit_not_authenticated", assessment.blockers)
        self.assertIn("replication_not_authenticated", assessment.blockers)
        self.assertIn("claim_language_review_not_authenticated", assessment.blockers)
        self.assertIn("external_scientific_review_not_established", assessment.blockers)

    def test_failed_control_is_ineligible(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["scientific_evidence"]["controls"][0]["outcome"] = "FAIL"
        loaded = self.fx.load_packet(packet)
        assessment = verify_evidence_packet(
            loaded, chain=self.fx.chain, artifact_registry=self.fx.registry()
        )
        self.assertEqual(assessment.scientific_eligibility, "INELIGIBLE")
        self.assertIn("control_fail:matched-taxonomy", assessment.blockers)

    def test_triggered_falsifier_is_ineligible(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["scientific_evidence"]["falsifiers"][0]["triggered"] = True
        loaded = self.fx.load_packet(packet)
        assessment = verify_evidence_packet(
            loaded, chain=self.fx.chain, artifact_registry=self.fx.registry()
        )
        self.assertEqual(assessment.scientific_eligibility, "INELIGIBLE")
        self.assertIn("falsifier_triggered:surface-beats-hidden", assessment.blockers)

    def test_underfilled_split_is_preserved_as_ineligible_negative_evidence(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["scientific_evidence"]["split_results"][0]["groups"] = 39
        loaded = self.fx.load_packet(packet)
        assessment = verify_evidence_packet(
            loaded, chain=self.fx.chain, artifact_registry=self.fx.registry()
        )
        self.assertEqual(assessment.structural_completeness, "COMPLETE")
        self.assertEqual(assessment.scientific_eligibility, "INELIGIBLE")
        self.assertIn("split_group_floor_not_met:confirmatory", assessment.blockers)
        self.assertIn("authenticated_execution_not_established", assessment.blockers)

    def test_fixed_sample_row_deviation_is_preserved_as_ineligible_evidence(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        split = packet["scientific_evidence"]["split_results"][0]
        split["enrolled_rows"] = 163
        split["analyzed_rows"] = 159
        loaded = self.fx.load_packet(packet)
        assessment = verify_evidence_packet(
            loaded, chain=self.fx.chain, artifact_registry=self.fx.registry()
        )
        self.assertEqual(assessment.structural_completeness, "COMPLETE")
        self.assertEqual(assessment.scientific_eligibility, "INELIGIBLE")
        self.assertIn(
            "fixed_sample_enrolled_rows_deviation:confirmatory",
            assessment.blockers,
        )
        self.assertIn(
            "fixed_sample_analyzed_rows_deviation:confirmatory",
            assessment.blockers,
        )

    def test_fixed_sample_attrition_maximum_is_ineligible_not_erased(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        split = packet["scientific_evidence"]["split_results"][0]
        split["missing_rows"] = 3
        split["excluded_rows"] = 1
        loaded = self.fx.load_packet(packet)
        assessment = verify_evidence_packet(
            loaded, chain=self.fx.chain, artifact_registry=self.fx.registry()
        )
        self.assertEqual(assessment.scientific_eligibility, "INELIGIBLE")
        self.assertIn(
            "fixed_sample_missing_rows_exceeded:confirmatory",
            assessment.blockers,
        )

    def test_split_row_accounting_must_be_exact(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["scientific_evidence"]["split_results"][0]["missing_rows"] = 3
        with self.assertRaisesRegex(SchemaValidationError, "must equal"):
            self.fx.load_packet(packet)

    def test_split_analyzed_rows_must_not_be_less_than_groups(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        split = packet["scientific_evidence"]["split_results"][0]
        split["analyzed_rows"] = 39
        split["enrolled_rows"] = 43
        with self.assertRaisesRegex(SchemaValidationError, "at least groups"):
            self.fx.load_packet(packet)

    def test_present_evidence_axes_remain_unauthenticated(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["execution"]["authentication"] = {
            "availability": "PRESENT",
            "authority_id": "declared-authority",
            "receipt": self.fx._put("declared-auth-receipt"),
        }
        packet["independent_numerical_audit"] = {
            "availability": "PRESENT",
            "auditor_id": "auditor-01",
            "independence_basis": "Different implementation and declared reviewer identity.",
            "input_manifest": self.fx._put("audit-input"),
            "code_identity": self.fx._put("audit-code"),
            "result_manifest": self.fx._put("audit-result"),
            "agreement": {"reported_metrics_match": True, "discrepancies": []},
        }
        packet["replication"] = {
            "availability": "PRESENT",
            "replication_id": "replication-001",
            "team_id": "team-002",
            "preregistration_sha256": self.fx.loaded.sha256,
            "model_identity": self.fx._put("replication-model"),
            "environment_identity": self.fx._put("replication-env"),
            "result_manifest": self.fx._put("replication-result"),
            "outcome_relation": "AGREES",
        }
        packet["claim_language_review"] = {
            "availability": "PRESENT",
            "reviewer_id": "reviewer-001",
            "exact_wording": self.fx.prereg["permitted_wording"]["allowed"][0],
            "decision": "APPROVED",
            "review_artifact": self.fx._put("wording-review"),
        }
        loaded = self.fx.load_packet(packet)
        assessment = verify_evidence_packet(
            loaded, chain=self.fx.chain, artifact_registry=self.fx.registry()
        )
        self.assertEqual(assessment.authenticated_execution, "PRESENT_UNAUTHENTICATED")
        self.assertEqual(
            assessment.independent_numerical_audit, "REPORTED_MATCH_UNAUTHENTICATED"
        )
        self.assertEqual(assessment.replication, "REPORTED_AGREES_UNAUTHENTICATED")
        self.assertEqual(
            assessment.claim_language_review, "REPORTED_APPROVED_UNAUTHENTICATED"
        )
        self.assertEqual(assessment.scientific_eligibility, "NOT_ESTABLISHED")

    def test_auditor_cannot_self_collide_with_executor(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["independent_numerical_audit"] = {
            "availability": "PRESENT",
            "auditor_id": packet["execution"]["executor_identity"],
            "independence_basis": "Forged self-audit.",
            "input_manifest": self.fx._put("collision-audit-input"),
            "code_identity": self.fx._put("collision-audit-code"),
            "result_manifest": self.fx._put("collision-audit-result"),
            "agreement": {"reported_metrics_match": True, "discrepancies": []},
        }
        with self.assertRaisesRegex(SchemaValidationError, "pairwise distinct"):
            self.fx.load_packet(packet)

    def test_replication_team_cannot_self_collide_with_executor(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["replication"] = {
            "availability": "PRESENT",
            "replication_id": "replication-collision",
            "team_id": packet["execution"]["executor_identity"],
            "preregistration_sha256": self.fx.loaded.sha256,
            "model_identity": self.fx._put("collision-replication-model"),
            "environment_identity": self.fx._put("collision-replication-env"),
            "result_manifest": self.fx._put("collision-replication-result"),
            "outcome_relation": "AGREES",
        }
        with self.assertRaisesRegex(SchemaValidationError, "pairwise distinct"):
            self.fx.load_packet(packet)

    def test_claim_reviewer_cannot_self_collide_with_executor(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["claim_language_review"] = {
            "availability": "PRESENT",
            "reviewer_id": packet["execution"]["executor_identity"],
            "exact_wording": self.fx.prereg["permitted_wording"]["allowed"][0],
            "decision": "APPROVED",
            "review_artifact": self.fx._put("collision-review"),
        }
        with self.assertRaisesRegex(SchemaValidationError, "pairwise distinct"):
            self.fx.load_packet(packet)

    def test_distinct_artifact_ids_cannot_clone_identical_bytes(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["outcome_artifacts"][0] = artifact_ref(
            "cloned-execution-manifest", self.fx.blobs["execution-manifest"]
        )
        with self.assertRaisesRegex(SchemaValidationError, "may not clone"):
            self.fx.load_packet(packet)

    def test_unregistered_approved_wording_is_rejected(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["claim_language_review"] = {
            "availability": "PRESENT",
            "reviewer_id": "reviewer-001",
            "exact_wording": "CAS Harness is proven safe.",
            "decision": "APPROVED",
            "review_artifact": self.fx._put("bad-wording-review"),
        }
        with self.assertRaisesRegex(SchemaValidationError, "not one of the exact"):
            self.fx.load_packet(packet)

    def test_automatic_v1_upgrade_is_explicitly_rejected(self) -> None:
        for schema in ("evidence_packet.v1", "cas_harness_evidence_packet_v1"):
            raw = encode({"schema_version": schema, "trace_id": "legacy"})
            with self.subTest(schema=schema):
                with self.assertRaises(AmbiguousV1UpgradeError):
                    reject_automatic_v1_upgrade(raw)
                with self.assertRaises(AmbiguousV1UpgradeError):
                    load_evidence_packet(raw, chain=self.fx.chain)

    def test_forged_product_state_is_rejected(self) -> None:
        packet = json.loads(self.fx.packet_bytes)
        packet["governance"]["product_claim_status"] = "LICENSED"
        with self.assertRaisesRegex(SchemaValidationError, "NOT LICENSED"):
            self.fx.load_packet(packet)


class RegistryTests(unittest.TestCase):
    def test_registry_snapshots_mutable_input(self) -> None:
        raw = bytearray(b"stable evidence")
        registry = ArtifactByteRegistry({"evidence": raw})
        reference = ArtifactRef(**artifact_ref("evidence", bytes(raw)))
        raw[:] = b"changed evidence"
        self.assertTrue(registry.verify(reference))

    def test_registry_rejects_wrong_bytes(self) -> None:
        registry = ArtifactByteRegistry({"evidence": b"wrong"})
        reference = ArtifactRef(**artifact_ref("evidence", b"right"))
        self.assertFalse(registry.verify(reference))

    def test_public_artifact_ref_constructor_cannot_forge_invalid_identity(self) -> None:
        with self.assertRaises(SchemaValidationError):
            ArtifactRef(
                artifact_id="invalid artifact id",
                sha256="not-a-sha",
                byte_length=-1,
                media_type="",
            )

    def test_registry_rejects_noncanonical_artifact_id(self) -> None:
        with self.assertRaisesRegex(SchemaValidationError, "machine identifier"):
            ArtifactByteRegistry({"invalid artifact id": b"bytes"})


class CanonicalJSONTests(unittest.TestCase):
    def test_non_string_mapping_key_is_rejected_without_coercion(self) -> None:
        with self.assertRaisesRegex(StrictJSONError, "exact strings"):
            canonical_json_bytes({1: "numeric key"})

    def test_key_coercion_collision_attempt_is_rejected(self) -> None:
        with self.assertRaisesRegex(StrictJSONError, "exact strings"):
            canonical_json_bytes({1: "numeric key", "1": "string key"})


if __name__ == "__main__":
    unittest.main()
