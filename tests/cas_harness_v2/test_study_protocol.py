from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
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
    build_worker_authorization,
    build_worker_terminal_receipt,
    canonical_sha256,
    sha256_bytes,
)
from cas_harness_v2.preregistration import (  # noqa: E402
    PreregistrationChain,
    load_preregistration,
)
from cas_harness_v2.study_protocol import (  # noqa: E402
    CONFIRMATORY_EVALUATION,
    DIAGNOSTIC_CALIBRATION,
    FixedSampleStudy,
    ModelForwardPhaseCount,
    STUDY_CASE_PACKAGE_MEDIA_TYPE,
    STUDY_CASE_PACKAGE_SCHEMA,
    STUDY_OUTCOME_ACCESS_SCHEMA,
    STUDY_PLAN_MEDIA_TYPE,
    STUDY_VARIANT_ROLES,
    StudyCounters,
    StudyOutcomeAccessEvent,
    StudyPlanArtifact,
    load_study_plan,
)
from test_research_control_kernel import Fixture, artifact_ref, encode  # noqa: E402


COUNTER_SEMANTICS = {
    "study_cases": "FIXED_CASE_INVENTORY_CARDINALITY",
    "external_joined_requests": "EXTERNAL_JOINED_REQUESTS_ONLY",
    "generations": "GENERATION_CALLS_ONLY",
    "model_forwards_by_phase": "MODEL_FORWARDS_EXCLUDING_STARTUP_CANARIES",
    "startup_canaries": "STARTUP_INTERNAL_CANARIES_ONLY",
}

AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "authentication": "NOT_PROVIDED",
    "durable_one_use": "PROCESS_LOCAL_ONLY",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "packet": "NOT_CREATED",
    "scientific_decision": "NOT_MADE",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "claim_promotion": "FORBIDDEN",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}


def ref_value(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def case_counts_value(*, startup_canaries: int) -> dict[str, object]:
    return {
        "study_cases": 1,
        "external_joined_requests": 1,
        "generations": 1,
        "model_forwards_by_phase": [
            {"phase_id": "prompt-observation", "count": 1},
            {"phase_id": "generation-forward", "count": 1},
        ],
        "startup_canaries": startup_canaries,
    }


def package_bytes(
    *,
    study_id: str,
    study_phase: str,
    split_id: str,
    role: str,
    cases: list[dict],
) -> bytes:
    return encode(
        {
            "schema_version": STUDY_CASE_PACKAGE_SCHEMA,
            "study_id": study_id,
            "study_phase": study_phase,
            "split_id": split_id,
            "role": role,
            "ordered_cases": [
                deepcopy(case) for case in cases if case["split_id"] == split_id
            ],
        }
    )


class StudyProtocolFixture:
    def __init__(self) -> None:
        research = Fixture()
        self.study_id = "stagec-study-001"
        self.request_bytes = tuple(
            f"exact request bytes for stagec-case-{index + 1:03d}\n".encode("ascii")
            for index in range(6)
        )
        self.requests = tuple(
            ArtifactRef(
                **artifact_ref(
                    f"stagec-request-{index + 1:03d}",
                    raw,
                    "application/vnd.cas-harness.study-request+json",
                )
            )
            for index, raw in enumerate(self.request_bytes)
        )
        self.case_inventory = [
            {
                "case_id": f"stagec-case-{index + 1:03d}",
                "group_id": (
                    "matched-group-001" if index < 3 else "matched-group-002"
                ),
                "split_id": "confirmatory" if index < 3 else "replication",
                "variant_role": STUDY_VARIANT_ROLES[index % 3],
                "request": ref_value(self.requests[index]),
                "expected_counts": case_counts_value(
                    startup_canaries=1 if index == 0 else 0
                ),
            }
            for index in range(6)
        ]
        confirmatory_package_bytes = package_bytes(
            study_id=self.study_id,
            study_phase=CONFIRMATORY_EVALUATION,
            split_id="confirmatory",
            role="CONFIRMATORY",
            cases=self.case_inventory,
        )
        replication_package_bytes = package_bytes(
            study_id=self.study_id,
            study_phase=CONFIRMATORY_EVALUATION,
            split_id="replication",
            role="HELD_OUT_REPLICATION",
            cases=self.case_inventory,
        )
        preregistration = deepcopy(research.prereg)
        for split in preregistration["splits"]:
            split["minimum_groups"] = 1
            split["target_groups"] = 1
            split["target_enrolled_rows"] = 3
            split["target_analyzed_rows"] = 3
            split["maximum_missing_rows"] = 0
            split["maximum_excluded_rows"] = 0
            if split["role"] == "CONFIRMATORY":
                split["source_artifact"] = artifact_ref(
                    "split-confirmatory",
                    confirmatory_package_bytes,
                    STUDY_CASE_PACKAGE_MEDIA_TYPE,
                )
            elif split["role"] == "HELD_OUT_REPLICATION":
                split["source_artifact"] = artifact_ref(
                    "split-replication",
                    replication_package_bytes,
                    STUDY_CASE_PACKAGE_MEDIA_TYPE,
                )
        self.base = load_preregistration(
            encode(preregistration),
            claim_ledger_bytes=research.claim_ledger_bytes,
        )
        self.chain = PreregistrationChain(self.base)
        self.base_json = json.loads(self.base.raw_bytes)
        refs = {item.artifact_id: item for item in self.chain.artifact_refs}
        self.split_packages = (
            refs["split-confirmatory"],
            refs["split-replication"],
        )
        self.plan = {
            "schema_version": "cas_harness_v2.study_plan.v1",
            "study_id": self.study_id,
            "created_at": "2026-08-05T08:10:00Z",
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
            "study_phase": CONFIRMATORY_EVALUATION,
            "split_packages": [
                {
                    "split_id": "confirmatory",
                    "role": "CONFIRMATORY",
                    "package": ref_value(self.split_packages[0]),
                },
                {
                    "split_id": "replication",
                    "role": "HELD_OUT_REPLICATION",
                    "package": ref_value(self.split_packages[1]),
                },
            ],
            "case_inventory": deepcopy(self.case_inventory),
            "expected_counts": {
                "study_cases": 6,
                "external_joined_requests": 6,
                "generations": 6,
                "model_forwards_by_phase": [
                    {"phase_id": "prompt-observation", "count": 6},
                    {"phase_id": "generation-forward", "count": 6},
                ],
                "startup_canaries": 1,
            },
            "counter_semantics": deepcopy(COUNTER_SEMANTICS),
            "authority": deepcopy(AUTHORITY),
            "governance": deepcopy(self.base_json["governance"]),
        }
        self.plan_raw = encode(self.plan)
        self.loaded_plan = load_study_plan(self.plan_raw, chain=self.chain)

    def diagnostic_plan(self) -> dict:
        value = deepcopy(self.plan)
        value["study_phase"] = DIAGNOSTIC_CALIBRATION
        value["split_packages"] = [
            {
                "split_id": "diagnostic-calibration",
                "role": DIAGNOSTIC_CALIBRATION,
                "package": {},
            }
        ]
        value["case_inventory"] = []
        for group_index in range(160):
            for variant_index in range(3):
                request = (
                    f"diagnostic request {group_index + 1:03d} "
                    f"variant {variant_index + 1}\n"
                ).encode("ascii")
                value["case_inventory"].append(
                    {
                        "case_id": (
                            f"cal-case-{group_index + 1:03d}-v{variant_index + 1}"
                        ),
                        "group_id": f"cal-group-{group_index + 1:03d}",
                        "split_id": "diagnostic-calibration",
                        "variant_role": STUDY_VARIANT_ROLES[variant_index],
                        "request": artifact_ref(
                            (
                                f"cal-request-{group_index + 1:03d}-"
                                f"v{variant_index + 1}"
                            ),
                            request,
                            "application/vnd.cas-harness.study-request+json",
                        ),
                        "expected_counts": case_counts_value(
                            startup_canaries=(
                                1 if group_index == 0 and variant_index == 0 else 0
                            )
                        ),
                    }
                )
        calibration_package_bytes = package_bytes(
            study_id=self.study_id,
            study_phase=DIAGNOSTIC_CALIBRATION,
            split_id="diagnostic-calibration",
            role=DIAGNOSTIC_CALIBRATION,
            cases=value["case_inventory"],
        )
        value["split_packages"][0]["package"] = artifact_ref(
            "stagec-calibration-package",
            calibration_package_bytes,
            STUDY_CASE_PACKAGE_MEDIA_TYPE,
        )
        value["expected_counts"] = {
            "study_cases": 480,
            "external_joined_requests": 480,
            "generations": 480,
            "model_forwards_by_phase": [
                {"phase_id": "prompt-observation", "count": 480},
                {"phase_id": "generation-forward", "count": 480},
            ],
            "startup_canaries": 1,
        }
        return value

    def plan_from(self, value: dict | None = None) -> StudyPlanArtifact:
        return load_study_plan(
            encode(self.plan if value is None else value),
            chain=self.chain,
        )

    def child_counts(
        self,
        index: int,
        *,
        generations: int = 1,
        prompt_forwards: int = 1,
        generation_forwards: int = 1,
        startup_canaries: int | None = None,
    ) -> StudyCounters:
        return StudyCounters(
            study_cases=1,
            external_joined_requests=1,
            generations=generations,
            model_forwards_by_phase=(
                ModelForwardPhaseCount("prompt-observation", prompt_forwards),
                ModelForwardPhaseCount("generation-forward", generation_forwards),
            ),
            startup_canaries=(1 if index == 0 else 0)
            if startup_canaries is None
            else startup_canaries,
        )

    def child(
        self,
        index: int,
        *,
        audit_id: str | None = None,
        authorization_id: str | None = None,
        receipt_id: str | None = None,
        terminal_status: str = "COMPLETED",
        nonce_byte: int | None = None,
        terminal_at: str | None = None,
        shard_id: str | None = None,
        fleet_id: str | None = None,
    ):
        case = self.loaded_plan.cases[index]
        identities = self.base_json["identities"]
        execution_mapping = {
            "fleet_id": (
                (
                    "study-counts-"
                    + canonical_sha256(case.expected_counts.as_value())
                )
                if fleet_id is None
                else fleet_id
            ),
            "job_id": case.case_id,
            "audit_id": (
                f"study-plan-{self.loaded_plan.sha256}"
                if audit_id is None
                else audit_id
            ),
            "assigned_worker_id": "worker-stagec-01",
            "layer_start": 7,
            "layer_end": 8,
            "shard_id": (
                f"study-request-{case.request.sha256}"
                if shard_id is None
                else shard_id
            ),
            "assigned_methods": ["prompt-observation-v1"],
            "expected_outputs": ["raw-outcomes"],
            "lease_model": {
                "model_id": identities["model"]["model_id"],
                "model_revision": identities["model"]["revision"],
                "model_artifact_manifest_path": "C:\\research\\model-manifest.json",
                "model_artifact_manifest_sha256": "d" * 64,
                "execution_mode": "external_probe_command",
            },
        }
        authorization = build_worker_authorization(
            chain=self.chain,
            authorization_id=(
                f"study-auth-{index + 1:03d}"
                if authorization_id is None
                else authorization_id
            ),
            issued_at=(
                "2026-08-05T08:20:00Z"
                if index == 0
                else "2026-08-05T08:31:00Z"
            ),
            expires_at="2026-08-05T09:30:00Z",
            execution_mapping=execution_mapping,
            run_nonce=bytes([index + 1 if nonce_byte is None else nonce_byte]) * 32,
        )
        output = f"exact output for {case.case_id}\n".encode("ascii")
        if terminal_status == "COMPLETED":
            produced_outputs = [
                {
                    "output_name": "raw-outcomes",
                    "artifact": artifact_ref(
                        f"study-output-{index + 1:03d}",
                        output,
                        "application/jsonl",
                    ),
                }
            ]
            missing_outputs: list[str] = []
            error = None
        else:
            produced_outputs = []
            missing_outputs = ["raw-outcomes"]
            error = {
                "code": "EXECUTION_FAILED",
                "category": "EXECUTION_FAILED",
                "message": "synthetic failure",
                "retryable": False,
            }
        receipt = build_worker_terminal_receipt(
            chain=self.chain,
            authorization=authorization,
            receipt_id=(
                f"study-receipt-{index + 1:03d}"
                if receipt_id is None
                else receipt_id
            ),
            worker_started_at=(
                "2026-08-05T08:21:00Z"
                if index == 0
                else "2026-08-05T08:32:00Z"
            ),
            terminal_at=(
                terminal_at
                if terminal_at is not None
                else (
                    "2026-08-05T08:30:00Z"
                    if index == 0
                    else "2026-08-05T08:40:00Z"
                )
            ),
            terminal_status=terminal_status,
            produced_outputs=produced_outputs,
            missing_outputs=missing_outputs,
            error=error,
        )
        return authorization, receipt

    def register(self, state: FixedSampleStudy, index: int, **counter_overrides: int):
        authorization, receipt = self.child(index)
        state.register_child(
            case_id=self.loaded_plan.cases[index].case_id,
            request=self.requests[index],
            request_bytes=self.request_bytes[index],
            authorization=authorization,
            receipt=receipt,
            counters=self.child_counts(index, **counter_overrides),
        )
        return authorization, receipt


class StudyPlanLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = StudyProtocolFixture()

    def test_exact_plan_loads_with_only_refs_and_fixed_boundaries(self) -> None:
        loaded = self.fx.loaded_plan
        self.assertEqual(loaded.raw_bytes, self.fx.plan_raw)
        self.assertEqual(loaded.sha256, sha256_bytes(self.fx.plan_raw))
        self.assertEqual(loaded.byte_length, len(self.fx.plan_raw))
        self.assertEqual(loaded.artifact_ref.media_type, STUDY_PLAN_MEDIA_TYPE)
        self.assertEqual(
            [item.case_id for item in loaded.cases],
            [f"stagec-case-{index + 1:03d}" for index in range(6)],
        )
        self.assertEqual(loaded.expected_counts.study_cases, 6)
        self.assertEqual(loaded.study_phase, CONFIRMATORY_EVALUATION)
        self.assertEqual(
            tuple(item.role for item in loaded.split_packages),
            ("CONFIRMATORY", "HELD_OUT_REPLICATION"),
        )
        self.assertEqual(loaded.payload["authority"]["scope"], "STRUCTURE_ONLY")
        self.assertEqual(loaded.payload["authority"]["packet"], "NOT_CREATED")
        self.assertEqual(
            loaded.payload["authority"]["scientific_decision"], "NOT_MADE"
        )
        self.assertEqual(loaded.payload["governance"]["admission_ring"], 4)
        self.assertEqual(
            loaded.payload["governance"]["product_claim_status"], "NOT LICENSED"
        )
        self.assertEqual(loaded.payload["governance"]["disclosure_status"], "HELD")
        self.assertNotIn(b'"prompt":', self.fx.plan_raw.lower())
        self.assertNotIn(b'"output":', self.fx.plan_raw.lower())

    def test_strict_loader_rejects_duplicate_keys_and_prompt_or_output_fields(self) -> None:
        duplicate = self.fx.plan_raw.replace(
            b'"study_id":',
            b'"study_id":"forged-study","study_id":',
            1,
        )
        with self.assertRaises(StrictJSONError):
            load_study_plan(duplicate, chain=self.fx.chain)
        for forbidden in ("prompt", "output"):
            value = deepcopy(self.fx.plan)
            value[forbidden] = "forbidden bytes"
            with self.assertRaisesRegex(SchemaValidationError, "forbidden extra"):
                self.fx.plan_from(value)

    def test_duplicate_cases_or_request_refs_and_count_drift_are_rejected(self) -> None:
        duplicate_case = deepcopy(self.fx.plan)
        duplicate_case["case_inventory"][1]["case_id"] = duplicate_case[
            "case_inventory"
        ][0]["case_id"]
        duplicate_request = deepcopy(self.fx.plan)
        duplicate_request["case_inventory"][1]["request"] = deepcopy(
            duplicate_request["case_inventory"][0]["request"]
        )
        wrong_count = deepcopy(self.fx.plan)
        wrong_count["expected_counts"]["study_cases"] = 3
        for value in (duplicate_case, duplicate_request, wrong_count):
            with self.assertRaises(SchemaValidationError):
                self.fx.plan_from(value)

    def test_counter_semantics_and_phase_names_cannot_conflate_ledgers(self) -> None:
        conflated_semantics = deepcopy(self.fx.plan)
        conflated_semantics["counter_semantics"]["startup_canaries"] = (
            "MODEL_FORWARDS_EXCLUDING_STARTUP_CANARIES"
        )
        conflated_phase = deepcopy(self.fx.plan)
        conflated_phase["expected_counts"]["model_forwards_by_phase"][0][
            "phase_id"
        ] = "startup_canaries"
        for value in (conflated_semantics, conflated_phase):
            with self.assertRaises(SchemaValidationError):
                self.fx.plan_from(value)

    def test_negative_counts_wrong_media_and_package_inventory_drift_are_rejected(self) -> None:
        negative_global = deepcopy(self.fx.plan)
        negative_global["expected_counts"]["generations"] = -1
        negative_case = deepcopy(self.fx.plan)
        negative_case["case_inventory"][0]["expected_counts"][
            "startup_canaries"
        ] = -1
        wrong_request_media = deepcopy(self.fx.plan)
        wrong_request_media["case_inventory"][0]["request"]["media_type"] = (
            "application/jsonl"
        )
        wrong_package_media = deepcopy(self.fx.plan)
        wrong_package_media["split_packages"][0]["package"]["media_type"] = (
            "application/jsonl"
        )
        package_inventory_drift = deepcopy(self.fx.plan)
        package_inventory_drift["case_inventory"][0]["request"]["sha256"] = "C" * 64
        for value in (
            negative_global,
            negative_case,
            wrong_request_media,
            wrong_package_media,
            package_inventory_drift,
        ):
            with self.assertRaises(SchemaValidationError):
                self.fx.plan_from(value)
        with self.assertRaises(SchemaValidationError):
            StudyCounters(
                study_cases=1,
                external_joined_requests=1,
                generations=-1,
                model_forwards_by_phase=(
                    ModelForwardPhaseCount("prompt-observation", 1),
                ),
                startup_canaries=0,
            )

    def test_cross_chain_and_promoted_boundaries_fail_closed(self) -> None:
        wrong_chain = deepcopy(self.fx.plan)
        wrong_chain["preregistration_binding"]["pre_outcome_chain_sha256"] = "A" * 64
        promoted = deepcopy(self.fx.plan)
        promoted["governance"]["product_claim_status"] = "LICENSED"
        packet_promoted = deepcopy(self.fx.plan)
        packet_promoted["authority"]["packet"] = "CREATED"
        for value in (wrong_chain, promoted, packet_promoted):
            with self.assertRaises(SchemaValidationError):
                self.fx.plan_from(value)

    def test_diagnostic_calibration_is_one_exact_160_group_non_claim_package(self) -> None:
        loaded = self.fx.plan_from(self.fx.diagnostic_plan())
        self.assertEqual(loaded.study_phase, DIAGNOSTIC_CALIBRATION)
        self.assertEqual(len(loaded.split_packages), 1)
        self.assertEqual(loaded.split_packages[0].role, DIAGNOSTIC_CALIBRATION)
        self.assertEqual(
            {case.split_id for case in loaded.cases},
            {"diagnostic-calibration"},
        )
        self.assertEqual(len(loaded.cases), 480)
        self.assertEqual(len({case.group_id for case in loaded.cases}), 160)
        self.assertEqual(loaded.payload["authority"]["claim_promotion"], "FORBIDDEN")

    def test_diagnostic_phase_rejects_role_impersonation_and_wrong_group_count(self) -> None:
        confirmatory_role = self.fx.diagnostic_plan()
        confirmatory_role["split_packages"][0]["role"] = "CONFIRMATORY"
        impersonated_split = self.fx.diagnostic_plan()
        impersonated_split["split_packages"][0]["split_id"] = "confirmatory"
        for case in impersonated_split["case_inventory"]:
            case["split_id"] = "confirmatory"
        wrong_groups = self.fx.diagnostic_plan()
        del wrong_groups["case_inventory"][-3:]
        wrong_variant_count = self.fx.diagnostic_plan()
        del wrong_variant_count["case_inventory"][-1]
        wrong_variant_role = self.fx.diagnostic_plan()
        wrong_variant_role["case_inventory"][-1]["variant_role"] = "CLEAN_ABSENT"
        for value, message in (
            (confirmatory_role, "exactly one diagnostic package"),
            (impersonated_split, "must not impersonate"),
            (wrong_groups, "exactly 160 distinct"),
            (wrong_variant_count, "exactly one adversarial"),
            (wrong_variant_role, "exactly one adversarial"),
        ):
            with self.assertRaisesRegex(SchemaValidationError, message):
                self.fx.plan_from(value)

    def test_evaluation_phase_requires_both_exact_preregistered_disjoint_packages(self) -> None:
        missing_replication = deepcopy(self.fx.plan)
        missing_replication["split_packages"] = missing_replication["split_packages"][:1]
        missing_replication["case_inventory"] = missing_replication["case_inventory"][:1]
        diagnostic_role = deepcopy(self.fx.plan)
        diagnostic_role["split_packages"][0]["role"] = DIAGNOSTIC_CALIBRATION
        tampered_package = deepcopy(self.fx.plan)
        tampered_package["split_packages"][0]["package"]["sha256"] = "B" * 64
        overlapping_groups = deepcopy(self.fx.plan)
        overlapping_groups["case_inventory"][0]["group_id"] = "matched-group-002"
        overlapping_groups["case_inventory"][3]["group_id"] = "matched-group-001"
        for value, message in (
            (missing_replication, "requires ordered"),
            (diagnostic_role, "requires ordered"),
            (tampered_package, "requires exactly one matching"),
            (overlapping_groups, "must be disjoint"),
        ):
            with self.assertRaisesRegex(SchemaValidationError, message):
                self.fx.plan_from(value)

    def test_loader_snapshots_bytearray_and_state_rejects_mutated_plan_carrier(self) -> None:
        mutable = bytearray(self.fx.plan_raw)
        loaded = load_study_plan(mutable, chain=self.fx.chain)
        mutable[0] = ord("[")
        self.assertEqual(loaded.raw_bytes, self.fx.plan_raw)
        forged = replace(loaded, raw_bytes=loaded.raw_bytes + b" ")
        with self.assertRaisesRegex(SchemaValidationError, "exact-byte loader replay"):
            FixedSampleStudy(forged, chain=self.fx.chain)

    def test_loader_rejects_chain_with_existing_outcome_access(self) -> None:
        research = Fixture()
        with self.assertRaisesRegex(SchemaValidationError, "pre-outcome"):
            load_study_plan(self.fx.plan_raw, chain=research.chain)

    def test_amended_chain_hash_and_added_artifact_ref_are_retained(self) -> None:
        additional_raw = b"prospective execution identity bytes\n"
        amendment = {
            "schema_version": "cas_harness_v2.preregistration_amendment.v1",
            "amendment_id": "AMD-STAGEC-001",
            "created_at": "2026-08-05T08:05:00Z",
            "base_preregistration_sha256": self.fx.base.sha256,
            "previous_amendment_sha256": None,
            "reason": "Bind one additional prospective execution identity.",
            "change_class": "EXECUTION_IDENTITY_ADDITION",
            "changes": {
                "additional_artifacts": [
                    artifact_ref("stagec-added-identity", additional_raw)
                ]
            },
            "outcome_access": {"accessed": False, "evidence_ref": None},
        }
        self.fx.chain.append_amendment(encode(amendment))
        value = deepcopy(self.fx.plan)
        value["preregistration_binding"]["pre_outcome_chain_sha256"] = (
            self.fx.chain.chain_sha256
        )
        loaded = self.fx.plan_from(value)
        retained = {item.artifact_id: item for item in loaded.artifact_refs}
        self.assertIn("stagec-added-identity", retained)
        self.assertTrue(retained["stagec-added-identity"].verify_bytes(additional_raw))


class FixedSampleStudyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = StudyProtocolFixture()
        self.state = FixedSampleStudy(self.fx.loaded_plan, chain=self.fx.chain)

    def test_exact_happy_path_keeps_every_counter_separate_and_accesses_once(self) -> None:
        children = [self.fx.register(self.state, index) for index in range(6)]
        self.assertEqual(
            self.state.registered_case_ids,
            tuple(f"stagec-case-{index + 1:03d}" for index in range(6)),
        )
        self.assertEqual(self.state.remaining_case_ids, ())
        self.assertEqual(self.state.status, "ALL_CASES_TERMINAL_COUNTS_MATCH")
        counts = self.state.counters
        self.assertEqual(counts.study_cases, 6)
        self.assertEqual(counts.external_joined_requests, 6)
        self.assertEqual(counts.generations, 6)
        self.assertEqual(
            tuple((item.phase_id, item.count) for item in counts.model_forwards_by_phase),
            (("prompt-observation", 6), ("generation-forward", 6)),
        )
        self.assertEqual(counts.startup_canaries, 1)

        event = self.state.record_outcome_access(
            accessed_at="2026-08-05T08:50:00Z"
        )
        self.assertIsInstance(event, StudyOutcomeAccessEvent)
        self.assertEqual(event.counters, counts)
        self.assertEqual(
            event.ordered_terminal_receipts,
            tuple(item[1].artifact_ref for item in children),
        )
        self.assertEqual(
            json.loads(event.raw_bytes)["schema_version"],
            STUDY_OUTCOME_ACCESS_SCHEMA,
        )
        self.assertEqual(self.state.status, "STUDY_WIDE_OUTCOME_ACCESSED")
        self.assertIsNone(self.fx.chain.outcome_access)
        with self.assertRaisesRegex(SchemaValidationError, "already recorded"):
            self.state.record_outcome_access(accessed_at="2026-08-05T08:51:00Z")
        with self.assertRaises(SchemaValidationError):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=children[0][0],
                receipt=children[0][1],
                counters=self.fx.child_counts(0),
            )

    def test_reordered_unknown_missing_and_replacement_are_rejected(self) -> None:
        authorization, receipt = self.fx.child(1)
        with self.assertRaisesRegex(SchemaValidationError, "fixed case-inventory order"):
            self.state.register_child(
                case_id="stagec-case-002",
                request=self.fx.requests[1],
                request_bytes=self.fx.request_bytes[1],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(1),
            )
        with self.assertRaisesRegex(SchemaValidationError, "unknown"):
            self.state.register_child(
                case_id="unknown-case",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(0),
            )
        first = self.fx.register(self.state, 0)
        with self.assertRaisesRegex(SchemaValidationError, "every fixed case terminal"):
            self.state.record_outcome_access(accessed_at="2026-08-05T08:50:00Z")
        with self.assertRaisesRegex(SchemaValidationError, "replacement forbidden"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=first[0],
                receipt=first[1],
                counters=self.fx.child_counts(0),
            )

    def test_cross_study_and_tampered_request_are_rejected(self) -> None:
        authorization, receipt = self.fx.child(0, audit_id="different-study")
        with self.assertRaisesRegex(SchemaValidationError, "exact parent study-plan"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(0),
            )

    def test_receipt_binds_exact_plan_request_and_per_case_counter_digests(self) -> None:
        exact_authorization, exact_receipt = self.fx.child(0)
        with self.assertRaisesRegex(SchemaValidationError, "request bytes"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=b"different request bytes\n",
                authorization=exact_authorization,
                receipt=exact_receipt,
                counters=self.fx.child_counts(0),
            )
        wrong_request_binding = self.fx.child(0, shard_id="study-request-" + "A" * 64)
        with self.assertRaisesRegex(SchemaValidationError, "request digest"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=wrong_request_binding[0],
                receipt=wrong_request_binding[1],
                counters=self.fx.child_counts(0),
            )
        wrong_count_binding = self.fx.child(0, fleet_id="study-counts-" + "B" * 64)
        with self.assertRaisesRegex(SchemaValidationError, "counter contract"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=wrong_count_binding[0],
                receipt=wrong_count_binding[1],
                counters=self.fx.child_counts(0),
            )
        changed_plan = deepcopy(self.fx.plan)
        changed_plan["created_at"] = "2026-08-05T08:11:00Z"
        changed_plan_artifact = self.fx.plan_from(changed_plan)
        changed_plan_state = FixedSampleStudy(
            changed_plan_artifact,
            chain=self.fx.chain,
        )
        original_authorization, original_receipt = self.fx.child(0)
        with self.assertRaisesRegex(SchemaValidationError, "parent study-plan bytes"):
            changed_plan_state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=original_authorization,
                receipt=original_receipt,
                counters=self.fx.child_counts(0),
            )
        authorization, receipt = self.fx.child(0)
        wrong_request = replace(self.fx.requests[0], sha256="A" * 64)
        with self.assertRaisesRegex(SchemaValidationError, "predeclared request"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=wrong_request,
                request_bytes=self.fx.request_bytes[0],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(0),
            )

    def test_tampered_and_replayed_receipts_fail_exact_replay(self) -> None:
        authorization, receipt = self.fx.child(0)
        forged = replace(receipt, receipt_id="forged-receipt")
        with self.assertRaisesRegex(SchemaValidationError, "exact-byte loader replay"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=authorization,
                receipt=forged,
                counters=self.fx.child_counts(0),
            )
        self.fx.register(self.state, 0)
        with self.assertRaises(SchemaValidationError):
            self.state.register_child(
                case_id="stagec-case-002",
                request=self.fx.requests[1],
                request_bytes=self.fx.request_bytes[1],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(1),
            )

    def test_mutated_authorization_projection_is_rejected(self) -> None:
        authorization, receipt = self.fx.child(0)
        forged = replace(authorization, authorization_id="forged-authorization")
        with self.assertRaisesRegex(SchemaValidationError, "carrier.*exact-byte"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=forged,
                receipt=receipt,
                counters=self.fx.child_counts(0),
            )

    def test_run_authorization_and_receipt_identities_are_independently_unique(self) -> None:
        first_authorization, first_receipt = self.fx.register(self.state, 0)
        repeated_authorization_id = self.fx.child(
            1,
            authorization_id=first_authorization.authorization_id,
        )
        with self.assertRaisesRegex(SchemaValidationError, "authorization identity"):
            self.state.register_child(
                case_id="stagec-case-002",
                request=self.fx.requests[1],
                request_bytes=self.fx.request_bytes[1],
                authorization=repeated_authorization_id[0],
                receipt=repeated_authorization_id[1],
                counters=self.fx.child_counts(1),
            )
        repeated_receipt_id = self.fx.child(
            1,
            receipt_id=first_receipt.receipt_id,
        )
        with self.assertRaisesRegex(SchemaValidationError, "terminal receipt identity"):
            self.state.register_child(
                case_id="stagec-case-002",
                request=self.fx.requests[1],
                request_bytes=self.fx.request_bytes[1],
                authorization=repeated_receipt_id[0],
                receipt=repeated_receipt_id[1],
                counters=self.fx.child_counts(1),
            )
        repeated_nonce = self.fx.child(1, nonce_byte=1)
        with self.assertRaisesRegex(SchemaValidationError, "run nonce identity"):
            self.state.register_child(
                case_id="stagec-case-002",
                request=self.fx.requests[1],
                request_bytes=self.fx.request_bytes[1],
                authorization=repeated_nonce[0],
                receipt=repeated_nonce[1],
                counters=self.fx.child_counts(1),
            )

    def test_failed_receipt_is_not_a_terminal_case_for_study_v1(self) -> None:
        authorization, receipt = self.fx.child(0, terminal_status="FAILED")
        with self.assertRaisesRegex(SchemaValidationError, "irreversibly stops"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(0, generations=0),
            )
        self.assertEqual(self.state.status, "FAILED_TERMINAL_NO_RETRY")
        successful_authorization, successful_receipt = self.fx.child(0)
        with self.assertRaisesRegex(SchemaValidationError, "retry.*forbidden"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=successful_authorization,
                receipt=successful_receipt,
                counters=self.fx.child_counts(0),
            )
        with self.assertRaisesRegex(SchemaValidationError, "prevents.*outcome access"):
            self.state.record_outcome_access(accessed_at="2026-08-05T08:50:00Z")

    def test_ambiguous_send_is_terminal_and_cannot_be_retried(self) -> None:
        self.state.record_ambiguous_send(
            case_id="stagec-case-001",
            request=self.fx.requests[0],
            request_bytes=self.fx.request_bytes[0],
        )
        self.assertEqual(self.state.status, "AMBIGUOUS_SEND_TERMINAL_NO_RETRY")
        authorization, receipt = self.fx.child(0)
        with self.assertRaisesRegex(SchemaValidationError, "retry.*forbidden"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(0),
            )
        with self.assertRaisesRegex(SchemaValidationError, "prevents.*outcome access"):
            self.state.record_outcome_access(accessed_at="2026-08-05T08:50:00Z")

    def test_per_case_and_aggregate_count_drift_fail_closed(self) -> None:
        authorization, receipt = self.fx.child(0)
        with self.assertRaisesRegex(SchemaValidationError, "per-case contract"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(0, generations=3),
            )
        with self.assertRaisesRegex(SchemaValidationError, "per-case contract"):
            self.state.register_child(
                case_id="stagec-case-001",
                request=self.fx.requests[0],
                request_bytes=self.fx.request_bytes[0],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(
                    0,
                    generations=0,
                    prompt_forwards=0,
                    generation_forwards=0,
                ),
            )
        aggregate_drift = deepcopy(self.fx.plan)
        aggregate_drift["expected_counts"]["generations"] = 7
        with self.assertRaisesRegex(SchemaValidationError, "exact sum"):
            self.fx.plan_from(aggregate_drift)

    def test_premature_timestamp_and_mutated_source_carrier_do_not_change_snapshot(self) -> None:
        children = [self.fx.register(self.state, index) for index in range(6)]
        with self.assertRaisesRegex(SchemaValidationError, "strictly after"):
            self.state.record_outcome_access(accessed_at="2026-08-05T08:39:59Z")
        object.__setattr__(children[-1][1], "sha256", "A" * 64)
        self.assertEqual(self.state.counters, self.fx.loaded_plan.expected_counts)

    def test_fractional_timestamps_select_the_actual_latest_terminal(self) -> None:
        children = []
        for index in range(6):
            terminal_at = (
                "2026-08-05T08:40:00.1Z"
                if index == 1
                else "2026-08-05T08:40:00Z"
            )
            authorization, receipt = self.fx.child(index, terminal_at=terminal_at)
            self.state.register_child(
                case_id=self.fx.loaded_plan.cases[index].case_id,
                request=self.fx.requests[index],
                request_bytes=self.fx.request_bytes[index],
                authorization=authorization,
                receipt=receipt,
                counters=self.fx.child_counts(index),
            )
            children.append((authorization, receipt))
        with self.assertRaisesRegex(SchemaValidationError, "strictly after"):
            self.state.record_outcome_access(
                accessed_at="2026-08-05T08:40:00.05Z"
            )
        event = self.state.record_outcome_access(
            accessed_at="2026-08-05T08:40:00.2Z"
        )
        self.assertEqual(event.execution_completed_at, "2026-08-05T08:40:00.1Z")


if __name__ == "__main__":
    unittest.main()
