from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import (  # noqa: E402
    StrictJSONError,
    canonical_sha256,
    freeze_json,
    sha256_bytes,
)
from cas_harness_v2._validation import (  # noqa: E402
    ArtifactRef,
    SchemaValidationError,
)
from cas_harness_v2.diagnostic_preregistration import (  # noqa: E402
    DIAGNOSTIC_AMENDMENT_SCHEMA,
    DIAGNOSTIC_CALIBRATION,
    DIAGNOSTIC_ONLY,
    DIAGNOSTIC_OUTCOME_ACCESS_SCHEMA,
    DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE,
    DIAGNOSTIC_PREREGISTRATION_SCHEMA,
    DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA,
    DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE,
    MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH,
    DiagnosticAmendmentArtifact,
    DiagnosticPreregistrationChain,
    DiagnosticStudyOutcomeIndexArtifact,
    load_diagnostic_amendment,
    load_diagnostic_outcome_access,
    load_diagnostic_preregistration,
    load_diagnostic_study_outcome_index,
)


def encode(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def artifact_ref(
    artifact_id: str,
    raw: bytes,
    media_type: str = "application/octet-stream",
) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "sha256": sha256_bytes(raw),
        "byte_length": len(raw),
        "media_type": media_type,
    }


DIAGNOSTIC_OUTCOME_BOUNDARY = {
    "scope": "STRUCTURE_ONLY",
    "execution_authorization": "OPEN_NOT_PROVIDED",
    "terminal_row_coordinator": "OPEN_NOT_PROVIDED",
    "failed_row_semantics": "OPEN_NOT_PROVIDED",
    "diagnostic_nonreporting_disposition": "OPEN_NOT_PROVIDED",
    "retry_evidence": "NOT_ATTESTED",
    "trusted_time": "NOT_PROVIDED",
    "durable_one_use": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "evidence_packet_v2": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
}


class Fixture:
    def __init__(self) -> None:
        self.blobs = {
            "calibration-split": b"frozen calibration split\n",
            "corpus": b"frozen diagnostic corpus\n",
            "surface-bundle": b"frozen surface bundle\n",
            "analysis-plan": b"frozen calibration analysis\n",
            "runtime": b"prospective runtime identity\n",
            "outcome-index": b"aggregate study outcome index\n",
        }
        self.value = {
            "schema_version": DIAGNOSTIC_PREREGISTRATION_SCHEMA,
            "preregistration_id": "DPR-STAGEC-CAL-001",
            "created_at": "2026-08-08T08:00:00Z",
            "study_phase": DIAGNOSTIC_CALIBRATION,
            "claim_ceiling": DIAGNOSTIC_ONLY,
            "reporting_policy": {
                "evidence_packet_v2": "FORBIDDEN",
                "terminal_disposition": "DIAGNOSTIC_NONREPORTING_REQUIRED",
                "downstream_use": "FREEZE_OR_REJECT_CALIBRATION_ARTIFACT_ONLY",
                "evaluation_promotion": "FORBIDDEN",
                "claim_promotion": "FORBIDDEN",
            },
            "splits": [
                {
                    "split_id": "stagec-calibration",
                    "role": DIAGNOSTIC_CALIBRATION,
                    "source_artifact": artifact_ref(
                        "stagec-calibration-split", self.blobs["calibration-split"]
                    ),
                    "allocation_rule": "Freeze disjoint whole intent groups before execution.",
                    "grouping_key": "base_intent_group_id",
                    "minimum_groups": 160,
                    "target_groups": 160,
                    "target_enrolled_rows": 480,
                    "target_analyzed_rows": 480,
                    "maximum_missing_rows": 0,
                    "maximum_excluded_rows": 0,
                }
            ],
            "design": {
                "design_id": "stagec-qwen-calibration-v1",
                "objective": "Fit and either freeze or reject two diagnostic detectors.",
                "fixed_sample_plan": {
                    "stopping_rule": "FIXED_SAMPLE",
                    "interim_outcome_access": "FORBIDDEN",
                    "outcome_access_scope": "AGGREGATE_STUDY_ONLY_AFTER_COMPLETION",
                    "row_accounting": (
                        "DISJOINT_ENROLLED_EQUALS_ANALYZED_PLUS_MISSING_PLUS_EXCLUDED"
                    ),
                    "retry_rule": "ZERO_RETRY_NO_REPLACEMENT",
                    "exclusion_rule": "Use only the frozen parser-validity rule.",
                    "missing_data_rule": "A terminal row with no outcome is missing.",
                },
                "calibration_rule": "Fit independently on the complete C-Cal groups.",
                "freeze_or_reject_rule": "Freeze one exact bundle or reject calibration.",
                "input_artifacts": [
                    artifact_ref("stagec-corpus", self.blobs["corpus"]),
                    artifact_ref("stagec-surface-bundle", self.blobs["surface-bundle"]),
                ],
                "analysis_plan": artifact_ref(
                    "stagec-analysis-plan", self.blobs["analysis-plan"]
                ),
            },
            "governance": {
                "admission_ring": 4,
                "product_claim_status": "NOT LICENSED",
                "disclosure_status": "HELD",
                "public_release": False,
                "product_route": False,
                "license_decision": "NONE",
            },
        }
        self.raw = encode(self.value)
        self.base = load_diagnostic_preregistration(self.raw)

    def amendment(
        self,
        *,
        amendment_id: str = "AMD-DIAG-001",
        created_at: str = "2026-08-08T08:10:00Z",
        previous: DiagnosticAmendmentArtifact | None = None,
        change_class: str = "ADMINISTRATIVE_CLARIFICATION",
    ) -> dict[str, object]:
        if change_class == "ADMINISTRATIVE_CLARIFICATION":
            changes: dict[str, object] = {
                "nonoperative_note": "Clarifies spelling without changing the protected design."
            }
        elif change_class == "EXECUTION_IDENTITY_ADDITION":
            changes = {
                "additional_artifacts": [
                    artifact_ref("stagec-runtime", self.blobs["runtime"])
                ]
            }
        else:
            changes = {
                "window_start": "2026-08-08T09:00:00Z",
                "window_end": "2026-08-08T11:00:00Z",
            }
        return {
            "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
            "amendment_id": amendment_id,
            "created_at": created_at,
            "base_preregistration_sha256": self.base.sha256,
            "previous_amendment_sha256": (
                None if previous is None else previous.sha256
            ),
            "timing": "PROSPECTIVE_PRE_OUTCOME",
            "reason": "Prospective diagnostic-chain update.",
            "change_class": change_class,
            "changes": changes,
        }

    def outcome_bytes(
        self,
        chain: DiagnosticPreregistrationChain,
        *,
        artifact_id: str = "stagec-study-outcome-index-001",
        execution_started_at: str = "2026-08-08T09:00:00Z",
        execution_completed_at: str = "2026-08-08T10:00:00Z",
        accessed_at: str = "2026-08-08T10:01:00Z",
        pre_outcome_chain_sha256: str | None = None,
    ) -> bytes:
        return encode(
            {
                "schema_version": DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA,
                "outcome_index_id": artifact_id,
                "diagnostic_preregistration": {
                    "artifact_id": chain.base.preregistration_id,
                    "sha256": chain.base.sha256,
                    "byte_length": chain.base.byte_length,
                    "media_type": DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE,
                },
                "pre_outcome_chain_sha256": (
                    chain.pre_outcome_chain_sha256
                    if pre_outcome_chain_sha256 is None
                    else pre_outcome_chain_sha256
                ),
                "timing": {
                    "execution_started_at": execution_started_at,
                    "execution_completed_at": execution_completed_at,
                    "accessed_at": accessed_at,
                },
                "boundary": DIAGNOSTIC_OUTCOME_BOUNDARY,
            }
        )

    def outcome_ref(
        self,
        chain: DiagnosticPreregistrationChain,
        artifact_id: str = "stagec-study-outcome-index-001",
    ) -> ArtifactRef:
        raw = self.outcome_bytes(chain, artifact_id=artifact_id)
        return ArtifactRef(
            **artifact_ref(
                artifact_id,
                raw,
                DIAGNOSTIC_STUDY_OUTCOME_INDEX_MEDIA_TYPE,
            )
        )


class DiagnosticArtifactTests(unittest.TestCase):
    def test_exact_artifact_freezes_diagnostic_only_nonreporting_policy(self) -> None:
        fx = Fixture()
        loaded = fx.base

        self.assertEqual(loaded.raw_bytes, fx.raw)
        self.assertEqual(loaded.sha256, sha256_bytes(fx.raw))
        self.assertEqual(loaded.byte_length, len(fx.raw))
        self.assertEqual(loaded.study_phase, DIAGNOSTIC_CALIBRATION)
        self.assertEqual(loaded.claim_ceiling, DIAGNOSTIC_ONLY)
        self.assertEqual(
            loaded.artifact_ref.media_type, DIAGNOSTIC_PREREGISTRATION_MEDIA_TYPE
        )
        self.assertEqual(len(loaded.payload["splits"]), 1)
        self.assertEqual(
            loaded.payload["reporting_policy"]["terminal_disposition"],
            "DIAGNOSTIC_NONREPORTING_REQUIRED",
        )
        self.assertEqual(len(loaded.artifact_refs), 4)
        with self.assertRaises(TypeError):
            loaded.payload["study_phase"] = "CONFIRMATORY_EVALUATION"
        with self.assertRaises(FrozenInstanceError):
            loaded.claim_ceiling = "PRIVATE_RESEARCH_RESULT"

    def test_protected_hash_covers_phase_claim_reporting_split_design_and_governance(self) -> None:
        fx = Fixture()
        protected = {
            key: fx.value[key]
            for key in (
                "study_phase",
                "claim_ceiling",
                "reporting_policy",
                "splits",
                "design",
                "governance",
            )
        }
        self.assertEqual(fx.base.protected_design_sha256, canonical_sha256(protected))

        for path, replacement in (
            (("study_phase",), "CONFIRMATORY_EVALUATION"),
            (("claim_ceiling",), "PRIVATE_RESEARCH_RESULT"),
            (("reporting_policy", "claim_promotion"), "ALLOWED"),
            (("splits", 0, "allocation_rule"), "Changed allocation."),
            (("design", "objective"), "Changed objective."),
            (("governance", "product_route"), True),
        ):
            with self.subTest(path=path):
                changed = copy.deepcopy(protected)
                cursor = changed
                for key in path[:-1]:
                    cursor = cursor[key]
                cursor[path[-1]] = replacement
                self.assertNotEqual(
                    fx.base.protected_design_sha256, canonical_sha256(changed)
                )

    def test_bytes_like_input_is_snapshotted(self) -> None:
        fx = Fixture()
        mutable = bytearray(fx.raw)
        loaded = load_diagnostic_preregistration(mutable)
        mutable[0] = ord("[")
        self.assertEqual(loaded.raw_bytes, fx.raw)
        self.assertIs(type(loaded.raw_bytes), bytes)

    def test_no_automatic_v1_conversion_or_packet_surface_exists(self) -> None:
        fx = Fixture()
        v1 = copy.deepcopy(fx.value)
        v1["schema_version"] = "cas_harness_v2.preregistration.v1"
        with self.assertRaisesRegex(SchemaValidationError, "automatic v1 conversion"):
            load_diagnostic_preregistration(encode(v1))

        import cas_harness_v2.diagnostic_preregistration as diagnostic

        self.assertFalse(hasattr(diagnostic, "load_preregistration"))
        self.assertFalse(hasattr(diagnostic, "load_evidence_packet"))
        self.assertFalse(hasattr(diagnostic, "build_evidence_packet"))

    def test_root_and_nested_schemas_are_closed(self) -> None:
        fx = Fixture()
        mutations = []
        extra_root = copy.deepcopy(fx.value)
        extra_root["packet"] = "CREATE"
        mutations.append(extra_root)
        extra_reporting = copy.deepcopy(fx.value)
        extra_reporting["reporting_policy"]["escape_hatch"] = True
        mutations.append(extra_reporting)
        extra_split = copy.deepcopy(fx.value)
        extra_split["splits"][0]["confirmatory"] = True
        mutations.append(extra_split)
        extra_design = copy.deepcopy(fx.value)
        extra_design["design"]["claim"] = "promoted"
        mutations.append(extra_design)
        extra_fixed = copy.deepcopy(fx.value)
        extra_fixed["design"]["fixed_sample_plan"]["optional_stopping"] = True
        mutations.append(extra_fixed)
        extra_governance = copy.deepcopy(fx.value)
        extra_governance["governance"]["public_override"] = True
        mutations.append(extra_governance)

        for value in mutations:
            with self.subTest(extra=set(value) - set(fx.value)):
                with self.assertRaises(SchemaValidationError):
                    load_diagnostic_preregistration(encode(value))

    def test_strict_json_rejects_duplicate_float_bom_nonobject_and_invalid_utf8(self) -> None:
        fx = Fixture()
        duplicate = fx.raw[:-1] + b',"study_phase":"DIAGNOSTIC_CALIBRATION"}'
        bad_inputs = (
            duplicate,
            fx.raw.replace(b'"target_groups":160', b'"target_groups":160.0'),
            b"\xef\xbb\xbf" + fx.raw,
            b"[]",
            b'{"schema_version":"\xff"}',
        )
        for raw in bad_inputs:
            with self.subTest(raw=raw[:32]):
                with self.assertRaises(StrictJSONError):
                    load_diagnostic_preregistration(raw)

    def test_split_is_exactly_one_diagnostic_calibration_role(self) -> None:
        fx = Fixture()
        confirmatory = copy.deepcopy(fx.value)
        confirmatory["splits"][0]["role"] = "CONFIRMATORY"
        extra = copy.deepcopy(fx.value)
        extra["splits"].append(copy.deepcopy(extra["splits"][0]))
        absent = copy.deepcopy(fx.value)
        absent["splits"] = []
        for value in (confirmatory, extra, absent):
            with self.subTest(splits=value["splits"]):
                with self.assertRaises(SchemaValidationError):
                    load_diagnostic_preregistration(encode(value))

    def test_claim_reporting_and_governance_promotion_fail_closed(self) -> None:
        fx = Fixture()
        cases = (
            ("study_phase", None, "CONFIRMATORY_EVALUATION"),
            ("claim_ceiling", None, "PRIVATE_RESEARCH_RESULT"),
            ("reporting_policy", "evidence_packet_v2", "ALLOWED"),
            ("reporting_policy", "terminal_disposition", "EVIDENCE_PACKET_REQUIRED"),
            ("reporting_policy", "downstream_use", "EVALUATION_RESULT"),
            ("reporting_policy", "evaluation_promotion", "ALLOWED"),
            ("reporting_policy", "claim_promotion", "ALLOWED"),
            ("governance", "admission_ring", 3),
            ("governance", "product_claim_status", "LICENSED"),
            ("governance", "disclosure_status", "PUBLIC"),
            ("governance", "public_release", True),
            ("governance", "product_route", True),
            ("governance", "license_decision", "GRANTED"),
        )
        for outer, inner, replacement in cases:
            with self.subTest(field=(outer, inner)):
                value = copy.deepcopy(fx.value)
                if inner is None:
                    value[outer] = replacement
                else:
                    value[outer][inner] = replacement
                with self.assertRaises(SchemaValidationError):
                    load_diagnostic_preregistration(encode(value))

    def test_design_and_artifact_collisions_fail_closed(self) -> None:
        fx = Fixture()
        bad_count = copy.deepcopy(fx.value)
        bad_count["splits"][0]["target_analyzed_rows"] = 481
        duplicate_id = copy.deepcopy(fx.value)
        duplicate_id["design"]["input_artifacts"][0]["artifact_id"] = (
            "stagec-calibration-split"
        )
        cloned_content = copy.deepcopy(fx.value)
        cloned_content["design"]["input_artifacts"][0].update(
            {
                "sha256": cloned_content["splits"][0]["source_artifact"]["sha256"],
                "byte_length": cloned_content["splits"][0]["source_artifact"]["byte_length"],
            }
        )
        for value in (bad_count, duplicate_id, cloned_content):
            with self.assertRaises(SchemaValidationError):
                load_diagnostic_preregistration(encode(value))


class DiagnosticAmendmentTests(unittest.TestCase):
    def test_three_prospective_classes_append_with_exact_links(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        first = chain.append_amendment(encode(fx.amendment()))
        second_value = fx.amendment(
            amendment_id="AMD-DIAG-002",
            created_at="2026-08-08T08:20:00Z",
            previous=first,
            change_class="EXECUTION_IDENTITY_ADDITION",
        )
        second = chain.append_amendment(encode(second_value))
        third_value = fx.amendment(
            amendment_id="AMD-DIAG-003",
            created_at="2026-08-08T08:30:00Z",
            previous=second,
            change_class="EXECUTION_WINDOW",
        )
        third = chain.append_amendment(encode(third_value))

        self.assertEqual(
            tuple(item.change_class for item in chain.amendments),
            (
                "ADMINISTRATIVE_CLARIFICATION",
                "EXECUTION_IDENTITY_ADDITION",
                "EXECUTION_WINDOW",
            ),
        )
        self.assertIs(second.predecessor, first)
        self.assertIs(third.predecessor, second)
        self.assertEqual(third.previous_amendment_sha256, second.sha256)
        self.assertEqual(len(chain.artifact_refs), len(fx.base.artifact_refs) + 1)

    def test_amendment_schema_is_closed_and_cannot_modify_protected_fields(self) -> None:
        fx = Fixture()
        base = fx.amendment()
        cases = []
        extra = copy.deepcopy(base)
        extra["study_phase"] = "CONFIRMATORY_EVALUATION"
        cases.append(extra)
        wrong_timing = copy.deepcopy(base)
        wrong_timing["timing"] = "RETROSPECTIVE"
        cases.append(wrong_timing)
        wrong_class = copy.deepcopy(base)
        wrong_class["change_class"] = "CLAIM_PROMOTION"
        cases.append(wrong_class)
        wrong_changes = copy.deepcopy(base)
        wrong_changes["changes"]["operative_change"] = True
        cases.append(wrong_changes)
        for value in cases:
            with self.assertRaises(SchemaValidationError):
                load_diagnostic_amendment(
                    encode(value), base=fx.base, previous=None
                )

    def test_links_identifiers_times_windows_and_artifacts_are_append_only(self) -> None:
        fx = Fixture()
        first = load_diagnostic_amendment(
            encode(fx.amendment()), base=fx.base, previous=None
        )
        cases = []
        wrong_base = fx.amendment(
            amendment_id="AMD-DIAG-002",
            created_at="2026-08-08T08:20:00Z",
            previous=first,
        )
        wrong_base["base_preregistration_sha256"] = "A" * 64
        cases.append(wrong_base)
        wrong_link = fx.amendment(
            amendment_id="AMD-DIAG-002",
            created_at="2026-08-08T08:20:00Z",
            previous=first,
        )
        wrong_link["previous_amendment_sha256"] = "B" * 64
        cases.append(wrong_link)
        duplicate_id = fx.amendment(
            amendment_id=first.amendment_id,
            created_at="2026-08-08T08:20:00Z",
            previous=first,
        )
        cases.append(duplicate_id)
        lexical_regression = fx.amendment(
            amendment_id="AMD-DIAG-000",
            created_at="2026-08-08T08:20:00Z",
            previous=first,
        )
        cases.append(lexical_regression)
        time_regression = fx.amendment(
            amendment_id="AMD-DIAG-002",
            created_at=first.created_at,
            previous=first,
        )
        cases.append(time_regression)
        for value in cases:
            with self.subTest(amendment=value):
                with self.assertRaises(SchemaValidationError):
                    load_diagnostic_amendment(
                        encode(value), base=fx.base, previous=first
                    )

        chain = DiagnosticPreregistrationChain(fx.base)
        window_value = fx.amendment(change_class="EXECUTION_WINDOW")
        window_value["changes"]["window_start"] = window_value["created_at"]
        with self.assertRaises(SchemaValidationError):
            chain.append_amendment(encode(window_value))

        first_window = chain.append_amendment(
            encode(fx.amendment(change_class="EXECUTION_WINDOW"))
        )
        second_window = fx.amendment(
            amendment_id="AMD-DIAG-002",
            created_at="2026-08-08T08:20:00Z",
            previous=first_window,
            change_class="EXECUTION_WINDOW",
        )
        with self.assertRaises(SchemaValidationError):
            chain.append_amendment(encode(second_window))

    def test_amendment_reference_identifier_and_content_collisions_fail(self) -> None:
        fx = Fixture()
        duplicate_id = fx.amendment(change_class="EXECUTION_IDENTITY_ADDITION")
        duplicate_id["changes"]["additional_artifacts"][0]["artifact_id"] = (
            "stagec-corpus"
        )
        cloned_content = fx.amendment(change_class="EXECUTION_IDENTITY_ADDITION")
        cloned_content["changes"]["additional_artifacts"][0].update(
            {
                "sha256": fx.base.artifact_refs[0].sha256,
                "byte_length": fx.base.artifact_refs[0].byte_length,
            }
        )
        carrier_collision = fx.amendment()
        carrier_collision["amendment_id"] = fx.base.preregistration_id
        for value in (duplicate_id, cloned_content, carrier_collision):
            with self.assertRaises(SchemaValidationError):
                load_diagnostic_amendment(
                    encode(value), base=fx.base, previous=None
                )

    def test_post_access_amendment_is_forbidden(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        chain.record_outcome_access(fx.outcome_bytes(chain))
        with self.assertRaisesRegex(SchemaValidationError, "sealed after outcome access"):
            chain.append_amendment(encode(fx.amendment()))

    def test_cycle_skipped_link_and_direct_carrier_forgery_fail(self) -> None:
        fx = Fixture()
        first = load_diagnostic_amendment(
            encode(fx.amendment()), base=fx.base, previous=None
        )
        object.__setattr__(first, "predecessor", first)
        next_value = fx.amendment(
            amendment_id="AMD-DIAG-002",
            created_at="2026-08-08T08:20:00Z",
            previous=first,
        )
        with self.assertRaisesRegex(SchemaValidationError, "cycle"):
            load_diagnostic_amendment(
                encode(next_value), base=fx.base, previous=first
            )

        first = load_diagnostic_amendment(
            encode(fx.amendment()), base=fx.base, previous=None
        )
        second_value = fx.amendment(
            amendment_id="AMD-DIAG-002",
            created_at="2026-08-08T08:20:00Z",
            previous=first,
        )
        second = load_diagnostic_amendment(
            encode(second_value), base=fx.base, previous=first
        )
        object.__setattr__(second, "predecessor", None)
        third = fx.amendment(
            amendment_id="AMD-DIAG-003",
            created_at="2026-08-08T08:30:00Z",
            previous=second,
        )
        with self.assertRaises(SchemaValidationError):
            load_diagnostic_amendment(
                encode(third), base=fx.base, previous=second
            )

        forged_base = replace(fx.base, sha256="C" * 64)
        with self.assertRaises(SchemaValidationError):
            load_diagnostic_amendment(
                encode(fx.amendment()), base=forged_base, previous=None
            )

    def test_bounded_replay_accepts_128_and_rejects_129(self) -> None:
        fx = Fixture()
        previous = None
        for sequence in range(1, MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH):
            previous = exact_carrier(fx, sequence=sequence, predecessor=previous)
        accepted_value = amendment_for_sequence(
            fx,
            sequence=MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH,
            predecessor=previous,
        )
        accepted = load_diagnostic_amendment(
            encode(accepted_value), base=fx.base, previous=previous
        )
        self.assertEqual(
            accepted.amendment_id,
            f"AMD-BOUND-{MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH:06d}",
        )
        rejected_value = amendment_for_sequence(
            fx,
            sequence=MAX_DIAGNOSTIC_AMENDMENT_CHAIN_LENGTH + 1,
            predecessor=accepted,
        )
        with self.assertRaisesRegex(SchemaValidationError, "exceeds 128"):
            load_diagnostic_amendment(
                encode(rejected_value), base=fx.base, previous=accepted
            )


def amendment_for_sequence(
    fx: Fixture,
    *,
    sequence: int,
    predecessor: DiagnosticAmendmentArtifact | None,
) -> dict[str, object]:
    created = datetime(2026, 8, 8, 8, 0, tzinfo=timezone.utc) + timedelta(
        seconds=sequence
    )
    return {
        "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
        "amendment_id": f"AMD-BOUND-{sequence:06d}",
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_preregistration_sha256": fx.base.sha256,
        "previous_amendment_sha256": (
            None if predecessor is None else predecessor.sha256
        ),
        "timing": "PROSPECTIVE_PRE_OUTCOME",
        "reason": "Bounded replay fixture.",
        "change_class": "ADMINISTRATIVE_CLARIFICATION",
        "changes": {"nonoperative_note": f"Bounded link {sequence}."},
    }


def exact_carrier(
    fx: Fixture,
    *,
    sequence: int,
    predecessor: DiagnosticAmendmentArtifact | None,
) -> DiagnosticAmendmentArtifact:
    value = amendment_for_sequence(fx, sequence=sequence, predecessor=predecessor)
    raw = encode(value)
    return DiagnosticAmendmentArtifact(
        raw_bytes=raw,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        amendment_id=value["amendment_id"],
        created_at=value["created_at"],
        base_preregistration_sha256=fx.base.sha256,
        previous_amendment_sha256=value["previous_amendment_sha256"],
        change_class=value["change_class"],
        payload=freeze_json(value),
        artifact_refs=(),
        predecessor=predecessor,
    )


class DiagnosticOutcomeAccessTests(unittest.TestCase):
    def test_exactly_one_aggregate_access_is_sealed_after_completion(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        amendment = chain.append_amendment(encode(fx.amendment()))
        pre_outcome_sha = chain.pre_outcome_chain_sha256
        raw_index = fx.outcome_bytes(chain)
        event = chain.record_outcome_access(raw_index)

        self.assertEqual(event.sealed_pre_outcome_chain_sha256, pre_outcome_sha)
        self.assertEqual(event.study_outcome_index, chain.outcome_index.artifact_ref)
        self.assertEqual(event.execution_started_at, "2026-08-08T09:00:00Z")
        self.assertEqual(event.study_completed_at, "2026-08-08T10:00:00Z")
        self.assertEqual(event.accessed_at, "2026-08-08T10:01:00Z")
        self.assertEqual(chain.outcome_index.raw_bytes, raw_index)
        self.assertEqual(
            chain.outcome_index.payload["boundary"]["terminal_row_coordinator"],
            "OPEN_NOT_PROVIDED",
        )
        self.assertEqual(
            chain.outcome_index.payload["boundary"][
                "diagnostic_nonreporting_disposition"
            ],
            "OPEN_NOT_PROVIDED",
        )
        self.assertEqual(chain.outcome_access, event)
        self.assertIn(event.study_outcome_index, chain.artifact_refs)
        self.assertNotEqual(chain.chain_sha256, pre_outcome_sha)
        self.assertEqual(chain.amendments, (amendment,))
        with self.assertRaisesRegex(SchemaValidationError, "already recorded"):
            chain.record_outcome_access(raw_index)

    def test_outcome_times_must_follow_chain_and_completion(self) -> None:
        fx = Fixture()
        cases = (
            ("2026-08-08T07:59:00Z", "2026-08-08T10:00:00Z", "2026-08-08T10:01:00Z"),
            ("2026-08-08T10:01:00Z", "2026-08-08T10:00:00Z", "2026-08-08T10:02:00Z"),
            ("2026-08-08T09:00:00Z", "2026-08-08T10:00:00Z", "2026-08-08T10:00:00Z"),
        )
        for started_at, completed_at, accessed_at in cases:
            chain = DiagnosticPreregistrationChain(fx.base)
            raw = fx.outcome_bytes(
                chain,
                execution_started_at=started_at,
                execution_completed_at=completed_at,
                accessed_at=accessed_at,
            )
            with self.subTest(started_at=started_at, accessed_at=accessed_at):
                with self.assertRaises(SchemaValidationError):
                    chain.record_outcome_access(raw)

    def test_loose_ref_and_caller_invented_time_api_is_removed(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        with self.assertRaises(TypeError):
            chain.record_outcome_access(  # type: ignore[call-arg]
                study_completed_at="2026-08-08T10:00:00Z",
                accessed_at="2026-08-08T10:01:00Z",
                study_outcome_index=fx.outcome_ref(chain),
            )
        with self.assertRaises(ValueError):
            chain.record_outcome_access(b"one child receipt\n")

    def test_outcome_index_identifier_collision_fails(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        raw = fx.outcome_bytes(
            chain,
            artifact_id=fx.base.artifact_refs[0].artifact_id,
        )
        with self.assertRaisesRegex(SchemaValidationError, "collides"):
            chain.record_outcome_access(raw)

    def test_outcome_loader_is_strict_and_seal_bound(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        seal = chain.pre_outcome_chain_sha256
        raw_index = fx.outcome_bytes(chain)
        index = load_diagnostic_study_outcome_index(
            raw_index,
            base=chain.base,
            amendments=chain.amendments,
            expected_pre_outcome_chain_sha256=seal,
        )
        self.assertIsInstance(index, DiagnosticStudyOutcomeIndexArtifact)
        value = {
            "schema_version": DIAGNOSTIC_OUTCOME_ACCESS_SCHEMA,
            "accessed_at": "2026-08-08T10:01:00Z",
            "execution_started_at": "2026-08-08T09:00:00Z",
            "study_completed_at": "2026-08-08T10:00:00Z",
            "study_outcome_index": {
                "artifact_id": index.artifact_ref.artifact_id,
                "sha256": index.artifact_ref.sha256,
                "byte_length": index.artifact_ref.byte_length,
                "media_type": index.artifact_ref.media_type,
            },
            "sealed_pre_outcome_chain_sha256": seal,
        }
        loaded = load_diagnostic_outcome_access(
            encode(value),
            expected_pre_outcome_chain_sha256=seal,
            outcome_index=index,
        )
        self.assertEqual(loaded.study_outcome_index.artifact_id, "stagec-study-outcome-index-001")

        extra = copy.deepcopy(value)
        extra["child_receipts"] = []
        with self.assertRaises(SchemaValidationError):
            load_diagnostic_outcome_access(
                encode(extra),
                expected_pre_outcome_chain_sha256=seal,
                outcome_index=index,
            )
        with self.assertRaises(SchemaValidationError):
            load_diagnostic_outcome_access(
                encode(value),
                expected_pre_outcome_chain_sha256="E" * 64,
                outcome_index=index,
            )

        pretty = json.dumps(value, indent=2).encode("utf-8")
        with self.assertRaisesRegex(SchemaValidationError, "canonical JSON"):
            load_diagnostic_outcome_access(
                pretty,
                expected_pre_outcome_chain_sha256=seal,
                outcome_index=index,
            )

    def test_outcome_loader_replays_amendments_and_derives_expected_chain_seal(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        amendment = chain.append_amendment(encode(fx.amendment()))
        raw = fx.outcome_bytes(chain)
        forged = replace(amendment, change_class="EXECUTION_WINDOW")
        with self.assertRaisesRegex(SchemaValidationError, "exact-byte replay"):
            load_diagnostic_study_outcome_index(
                raw,
                base=chain.base,
                amendments=(forged,),
                expected_pre_outcome_chain_sha256=chain.pre_outcome_chain_sha256,
            )

        invented_seal = "E" * 64
        invented_raw = fx.outcome_bytes(
            chain,
            pre_outcome_chain_sha256=invented_seal,
        )
        with self.assertRaisesRegex(SchemaValidationError, "exact diagnostic chain"):
            load_diagnostic_study_outcome_index(
                invented_raw,
                base=chain.base,
                amendments=chain.amendments,
                expected_pre_outcome_chain_sha256=invented_seal,
            )

    def test_cross_chain_outcome_index_swap_fails(self) -> None:
        fx = Fixture()
        first = DiagnosticPreregistrationChain(fx.base)
        raw = fx.outcome_bytes(first)
        second = DiagnosticPreregistrationChain(fx.base)
        second.append_amendment(encode(fx.amendment()))
        with self.assertRaisesRegex(SchemaValidationError, "different pre-outcome chain"):
            second.record_outcome_access(raw)

    def test_execution_window_is_enforced_by_raw_index_replay(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        chain.append_amendment(encode(fx.amendment(change_class="EXECUTION_WINDOW")))
        late = fx.outcome_bytes(
            chain,
            execution_started_at="2026-08-08T09:00:00Z",
            execution_completed_at="2026-08-08T12:00:00Z",
            accessed_at="2026-08-08T12:01:00Z",
        )
        with self.assertRaisesRegex(SchemaValidationError, "after the prospective"):
            chain.record_outcome_access(late)
        valid = fx.outcome_bytes(
            chain,
            execution_started_at="2026-08-08T09:00:00Z",
            execution_completed_at="2026-08-08T10:00:00Z",
            accessed_at="2026-08-08T11:01:00Z",
        )
        event = chain.record_outcome_access(valid)
        self.assertEqual(event.study_completed_at, "2026-08-08T10:00:00Z")

    def test_direct_base_amendment_and_outcome_mutation_are_detected(self) -> None:
        fx = Fixture()
        chain = DiagnosticPreregistrationChain(fx.base)
        object.__setattr__(
            chain,
            "_DiagnosticPreregistrationChain__base",
            replace(fx.base, protected_design_sha256="F" * 64),
        )
        with self.assertRaises(SchemaValidationError):
            _ = chain.base

        chain = DiagnosticPreregistrationChain(fx.base)
        amendment = chain.append_amendment(encode(fx.amendment()))
        forged_amendment = replace(amendment, change_class="CLAIM_PROMOTION")
        object.__setattr__(
            chain,
            "_DiagnosticPreregistrationChain__amendments",
            (forged_amendment,),
        )
        with self.assertRaises(SchemaValidationError):
            _ = chain.amendments

        chain = DiagnosticPreregistrationChain(fx.base)
        event = chain.record_outcome_access(fx.outcome_bytes(chain))
        forged_event = replace(event, accessed_at="2026-08-08T09:00:00Z")
        object.__setattr__(
            chain,
            "_DiagnosticPreregistrationChain__outcome_access",
            forged_event,
        )
        with self.assertRaises(SchemaValidationError):
            _ = chain.outcome_access


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
