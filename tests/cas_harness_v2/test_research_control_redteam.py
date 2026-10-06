from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2 import (  # noqa: E402
    AmbiguousV1UpgradeError,
    AmendmentArtifact,
    ArtifactRef,
    PreregistrationChain,
    SchemaValidationError,
    load_amendment,
    load_evidence_packet,
    load_preregistration,
    reject_automatic_v1_upgrade,
    sha256_bytes,
    verify_evidence_packet,
)
from cas_harness_v2._strict_json import freeze_json  # noqa: E402


_FIXTURE_PATH = Path(__file__).with_name("test_research_control_kernel.py")
_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "_cas_harness_v2_kernel_fixture", _FIXTURE_PATH
)
if _FIXTURE_SPEC is None or _FIXTURE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("could not load the isolated Harness v2 test fixture")
_FIXTURE_MODULE = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURE_MODULE)
Fixture = _FIXTURE_MODULE.Fixture
artifact_ref = _FIXTURE_MODULE.artifact_ref
encode = _FIXTURE_MODULE.encode


def administrative_amendment(base_sha256: str) -> dict:
    return {
        "schema_version": "cas_harness_v2.preregistration_amendment.v1",
        "amendment_id": "AMD-REDTEAM-INJECTED",
        "created_at": "2026-08-05T08:15:00Z",
        "base_preregistration_sha256": base_sha256,
        "previous_amendment_sha256": None,
        "reason": "Adversarial post-seal injection reproducer.",
        "change_class": "ADMINISTRATIVE_CLARIFICATION",
        "changes": {"nonoperative_note": "This carrier was inserted outside the chain API."},
        "outcome_access": {"accessed": False, "evidence_ref": None},
    }


def exact_amendment_carrier(
    *, base_sha256: str, sequence: int, predecessor: AmendmentArtifact | None
) -> AmendmentArtifact:
    created = datetime(2026, 8, 5, 8, 0, 1, tzinfo=timezone.utc) + timedelta(
        seconds=sequence
    )
    value = {
        "schema_version": "cas_harness_v2.preregistration_amendment.v1",
        "amendment_id": f"AMD-DEEP-{sequence:06d}",
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_preregistration_sha256": base_sha256,
        "previous_amendment_sha256": (
            None if predecessor is None else predecessor.sha256
        ),
        "reason": "Construct a bounded-replay adversarial carrier chain.",
        "change_class": "ADMINISTRATIVE_CLARIFICATION",
        "changes": {"nonoperative_note": f"Bounded replay carrier {sequence}."},
        "outcome_access": {"accessed": False, "evidence_ref": None},
    }
    raw = encode(value)
    return AmendmentArtifact(
        raw_bytes=raw,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        amendment_id=value["amendment_id"],
        created_at=value["created_at"],
        base_preregistration_sha256=base_sha256,
        previous_amendment_sha256=value["previous_amendment_sha256"],
        change_class=value["change_class"],
        payload=freeze_json(value),
        artifact_refs=(),
        predecessor=predecessor,
    )


class CarrierAndChronologyRedTeamTests(unittest.TestCase):
    def test_public_chain_getters_replay_integrity_before_returning_state(self) -> None:
        for getter_name in ("base", "amendments", "outcome_access"):
            with self.subTest(getter=getter_name):
                fx = Fixture()
                forged_base = replace(fx.chain.base, claim_id="CLM-FORGED")
                object.__setattr__(
                    fx.chain, "_PreregistrationChain__base", forged_base
                )
                with self.assertRaises(SchemaValidationError):
                    getattr(fx.chain, getter_name)

    def test_amendment_predecessor_self_cycle_fails_with_schema_error(self) -> None:
        fx = Fixture()
        previous = exact_amendment_carrier(
            base_sha256=fx.loaded.sha256, sequence=0, predecessor=None
        )
        object.__setattr__(previous, "predecessor", previous)
        next_value = administrative_amendment(fx.loaded.sha256)
        next_value.update(
            {
                "amendment_id": "AMD-NEXT-AFTER-CYCLE",
                "created_at": "2026-08-05T08:20:00Z",
                "previous_amendment_sha256": previous.sha256,
            }
        )

        with self.assertRaises(SchemaValidationError):
            load_amendment(encode(next_value), base=fx.loaded, previous=previous)

    def test_amendment_chain_total_length_boundary_is_exact(self) -> None:
        fx = Fixture()
        previous = None
        for sequence in range(127):
            previous = exact_amendment_carrier(
                base_sha256=fx.loaded.sha256,
                sequence=sequence,
                predecessor=previous,
            )
        self.assertIsNotNone(previous)
        link_128 = exact_amendment_carrier(
            base_sha256=fx.loaded.sha256,
            sequence=127,
            predecessor=previous,
        )
        accepted = load_amendment(
            link_128.raw_bytes, base=fx.loaded, previous=previous
        )
        self.assertEqual(accepted.sha256, link_128.sha256)

        link_129 = exact_amendment_carrier(
            base_sha256=fx.loaded.sha256,
            sequence=128,
            predecessor=accepted,
        )
        with self.assertRaisesRegex(SchemaValidationError, "exceeds 128"):
            load_amendment(
                link_129.raw_bytes, base=fx.loaded, previous=accepted
            )

    def test_amendment_predecessor_pointer_cannot_skip_a_link(self) -> None:
        fx = Fixture()
        first = exact_amendment_carrier(
            base_sha256=fx.loaded.sha256, sequence=1, predecessor=None
        )
        second = exact_amendment_carrier(
            base_sha256=fx.loaded.sha256, sequence=2, predecessor=first
        )
        object.__setattr__(second, "predecessor", None)
        next_value = administrative_amendment(fx.loaded.sha256)
        next_value.update(
            {
                "amendment_id": "AMD-NEXT-AFTER-SKIP",
                "created_at": "2026-08-05T08:20:00Z",
                "previous_amendment_sha256": second.sha256,
            }
        )

        with self.assertRaises(SchemaValidationError):
            load_amendment(encode(next_value), base=fx.loaded, previous=second)

    def test_amendment_loader_rejects_forged_base_carrier(self) -> None:
        fx = Fixture()
        forged_base = replace(fx.loaded, sha256="A" * 64)
        amendment = administrative_amendment(forged_base.sha256)

        with self.assertRaises(SchemaValidationError):
            load_amendment(encode(amendment), base=forged_base, previous=None)

    def test_amendment_loader_rejects_forged_previous_carrier(self) -> None:
        fx = Fixture()
        first = load_amendment(
            encode(administrative_amendment(fx.loaded.sha256)),
            base=fx.loaded,
            previous=None,
        )
        forged_previous = replace(first, sha256="B" * 64)
        second = administrative_amendment(fx.loaded.sha256)
        second.update(
            {
                "amendment_id": "AMD-REDTEAM-SECOND",
                "created_at": "2026-08-05T08:20:00Z",
                "previous_amendment_sha256": forged_previous.sha256,
            }
        )

        with self.assertRaises(SchemaValidationError):
            load_amendment(
                encode(second), base=fx.loaded, previous=forged_previous
            )

    def test_amendment_identifiers_advance_monotonically_as_specified(self) -> None:
        fx = Fixture()
        chain = PreregistrationChain(fx.loaded)
        first_value = administrative_amendment(fx.loaded.sha256)
        first_value["amendment_id"] = "AMD-Z"
        first = chain.append_amendment(encode(first_value))
        second_value = administrative_amendment(fx.loaded.sha256)
        second_value.update(
            {
                "amendment_id": "AMD-A",
                "created_at": "2026-08-05T08:20:00Z",
                "previous_amendment_sha256": first.sha256,
            }
        )

        with self.assertRaises(SchemaValidationError):
            chain.append_amendment(encode(second_value))

    def test_mutated_chain_base_cannot_rebind_packet_to_nonledger_claim(self) -> None:
        fx = Fixture()
        object.__setattr__(
            fx.chain,
            "_PreregistrationChain__base",
            replace(fx.chain.base, claim_id="CLM-FORGED"),
        )
        packet = copy.deepcopy(fx.packet)
        packet["claim_binding"]["claim_id"] = "CLM-FORGED"

        with self.assertRaises(SchemaValidationError):
            packet["claim_binding"][
                "preregistration_chain_sha256"
            ] = fx.chain.chain_sha256
            load_evidence_packet(encode(packet), chain=fx.chain)

    def test_sealed_chain_rejects_direct_post_seal_amendment_injection(self) -> None:
        fx = Fixture()
        amendment = load_amendment(
            encode(administrative_amendment(fx.loaded.sha256)),
            base=fx.loaded,
            previous=None,
        )
        object.__setattr__(
            fx.chain,
            "_PreregistrationChain__amendments",
            (*fx.chain.amendments, amendment),
        )
        packet = copy.deepcopy(fx.packet)

        with self.assertRaises(SchemaValidationError):
            packet["claim_binding"][
                "preregistration_chain_sha256"
            ] = fx.chain.chain_sha256
            load_evidence_packet(encode(packet), chain=fx.chain)

    def test_execution_must_fall_inside_preregistered_execution_window(self) -> None:
        fx = Fixture()
        chain = PreregistrationChain(fx.loaded)
        amendment = {
            "schema_version": "cas_harness_v2.preregistration_amendment.v1",
            "amendment_id": "AMD-REDTEAM-WINDOW",
            "created_at": "2026-08-05T08:15:00Z",
            "base_preregistration_sha256": fx.loaded.sha256,
            "previous_amendment_sha256": None,
            "reason": "Freeze the only permitted execution window.",
            "change_class": "EXECUTION_WINDOW",
            "changes": {
                "window_start": "2026-08-05T12:00:00Z",
                "window_end": "2026-08-05T13:00:00Z",
            },
            "outcome_access": {"accessed": False, "evidence_ref": None},
        }
        chain.append_amendment(encode(amendment))
        fx.blobs["redteam-window-receipt"] = b"red-team window receipt\n"
        chain.record_outcome_access(
            accessed_at="2026-08-05T09:30:00Z",
            execution_completed_at="2026-08-05T09:20:00Z",
            receipt=ArtifactRef(
                **artifact_ref(
                    "redteam-window-receipt", fx.blobs["redteam-window-receipt"]
                )
            ),
        )
        packet = copy.deepcopy(fx.packet)
        packet["claim_binding"]["preregistration_chain_sha256"] = chain.chain_sha256
        self.assertEqual(packet["execution"]["started_at"], "2026-08-05T09:01:00Z")

        with self.assertRaises(SchemaValidationError):
            load_evidence_packet(encode(packet), chain=chain)


class EvidenceSemanticsRedTeamTests(unittest.TestCase):
    def test_registry_recomputes_identity_from_retained_raw_bytes(self) -> None:
        fx = Fixture()
        packet = fx.load_packet()
        registry = fx.registry()
        retained = registry._entries["raw-outcomes"]  # noqa: SLF001
        object.__setattr__(retained, "raw_bytes", b"tampered after registry snapshot\n")

        assessment = verify_evidence_packet(
            packet, chain=fx.chain, artifact_registry=registry
        )
        self.assertEqual(assessment.structural_completeness, "INCOMPLETE")

    def test_audit_match_cannot_coexist_with_reported_discrepancies(self) -> None:
        fx = Fixture()
        packet = copy.deepcopy(fx.packet)
        packet["independent_numerical_audit"] = {
            "availability": "PRESENT",
            "auditor_id": "auditor-redteam-02",
            "independence_basis": "Declared independent for this structural test.",
            "input_manifest": fx._put("redteam-audit-input"),  # noqa: SLF001
            "code_identity": fx._put("redteam-audit-code"),  # noqa: SLF001
            "result_manifest": fx._put("redteam-audit-result"),  # noqa: SLF001
            "agreement": {
                "reported_metrics_match": True,
                "discrepancies": ["Every recomputed metric differs from the packet."],
            },
        }

        with self.assertRaises(SchemaValidationError):
            load_evidence_packet(encode(packet), chain=fx.chain)

    def test_case_only_aliases_cannot_satisfy_cross_role_independence(self) -> None:
        fx = Fixture()
        packet = copy.deepcopy(fx.packet)
        packet["execution"]["executor_identity"] = "Researcher-A"
        packet["independent_numerical_audit"] = {
            "availability": "PRESENT",
            "auditor_id": "researcher-a",
            "independence_basis": "Case-only alias adversarial reproducer.",
            "input_manifest": fx._put("redteam-alias-input"),  # noqa: SLF001
            "code_identity": fx._put("redteam-alias-code"),  # noqa: SLF001
            "result_manifest": fx._put("redteam-alias-result"),  # noqa: SLF001
            "agreement": {"reported_metrics_match": True, "discrepancies": []},
        }

        with self.assertRaises(SchemaValidationError):
            load_evidence_packet(encode(packet), chain=fx.chain)

    def test_every_repository_known_v1_packet_label_is_explicitly_ambiguous(self) -> None:
        legacy_labels = (
            "evidence_packet.v1",
            "cas_harness_evidence_packet_v1",
            "cas_harness_evidence_packet.v1",
            "cas_harness_stage9_40e_evidence_packet.v1",
        )
        for schema_version in legacy_labels:
            with self.subTest(schema_version=schema_version):
                with self.assertRaises(AmbiguousV1UpgradeError):
                    reject_automatic_v1_upgrade(
                        encode({"schema_version": schema_version})
                    )


class FixedSamplePlanRedTeamTests(unittest.TestCase):
    def test_fixed_sample_and_split_target_fields_are_required(self) -> None:
        fx = Fixture()
        cases = [
            ("top.fixed_sample_plan", None),
            *(
                (f"split.{field}", field)
                for field in (
                    "target_groups",
                    "target_enrolled_rows",
                    "target_analyzed_rows",
                    "maximum_missing_rows",
                    "maximum_excluded_rows",
                )
            ),
            *(
                (f"fixed.{field}", field)
                for field in (
                    "stopping_rule",
                    "interim_outcome_access",
                    "row_accounting",
                    "exclusion_rule",
                    "missing_data_rule",
                    "deviation_effect",
                    "power_analysis",
                )
            ),
        ]
        for label, field in cases:
            with self.subTest(field=label):
                value = copy.deepcopy(fx.prereg)
                if label == "top.fixed_sample_plan":
                    del value["fixed_sample_plan"]
                elif label.startswith("split."):
                    del value["splits"][0][field]
                else:
                    del value["fixed_sample_plan"][field]
                with self.assertRaises(SchemaValidationError):
                    load_preregistration(
                        encode(value), claim_ledger_bytes=fx.claim_ledger_bytes
                    )

    def test_fixed_sample_rules_and_deviation_effect_fail_closed(self) -> None:
        fx = Fixture()
        mutations = {
            "stopping_rule": "OPTIONAL_STOPPING",
            "interim_outcome_access": "ALLOWED",
            "row_accounting": "OVERLAPPING_ATTRITION_BUCKETS",
            "exclusion_rule": "   ",
            "missing_data_rule": "",
            "deviation_effect": "REPORT_ONLY",
        }
        for field, forged in mutations.items():
            with self.subTest(field=field):
                value = copy.deepcopy(fx.prereg)
                value["fixed_sample_plan"][field] = forged
                with self.assertRaises(SchemaValidationError):
                    load_preregistration(
                        encode(value), claim_ledger_bytes=fx.claim_ledger_bytes
                    )

    def test_split_target_and_attrition_constraints_fail_closed(self) -> None:
        fx = Fixture()
        mutations = (
            ("target_groups", 39),
            ("target_analyzed_rows", 39),
            ("target_enrolled_rows", 159),
            ("maximum_missing_rows", -1),
            ("maximum_excluded_rows", -1),
        )
        for field, forged in mutations:
            with self.subTest(field=field):
                value = copy.deepcopy(fx.prereg)
                value["splits"][0][field] = forged
                with self.assertRaises(SchemaValidationError):
                    load_preregistration(
                        encode(value), claim_ledger_bytes=fx.claim_ledger_bytes
                    )

        value = copy.deepcopy(fx.prereg)
        value["splits"][0]["target_enrolled_rows"] = 170
        with self.assertRaisesRegex(SchemaValidationError, "attrition"):
            load_preregistration(
                encode(value), claim_ledger_bytes=fx.claim_ledger_bytes
            )

    def test_power_analysis_is_exact_unique_and_protected(self) -> None:
        fx = Fixture()
        power_refs = [
            reference
            for reference in fx.loaded.artifact_refs
            if reference.artifact_id == "power-analysis"
        ]
        self.assertEqual(len(power_refs), 1)
        self.assertTrue(power_refs[0].verify_bytes(fx.blobs["power-analysis"]))

        changed = copy.deepcopy(fx.prereg)
        changed["fixed_sample_plan"]["exclusion_rule"] += " No discretionary exclusions."
        changed_loaded = load_preregistration(
            encode(changed), claim_ledger_bytes=fx.claim_ledger_bytes
        )
        self.assertNotEqual(
            changed_loaded.protected_design_sha256,
            fx.loaded.protected_design_sha256,
        )

        duplicate = copy.deepcopy(fx.prereg)
        duplicate["fixed_sample_plan"]["power_analysis"] = copy.deepcopy(
            duplicate["identities"]["model"]["weights"]
        )
        with self.assertRaisesRegex(SchemaValidationError, "duplicate"):
            load_preregistration(
                encode(duplicate), claim_ledger_bytes=fx.claim_ledger_bytes
            )

    def test_packet_split_row_accounting_is_closed_and_exact(self) -> None:
        fx = Fixture()
        mutations = (
            {"enrolled_rows": 165},
            {"analyzed_rows": 159},
            {"missing_rows": -1, "analyzed_rows": 163},
            {"excluded_rows": -1, "analyzed_rows": 163},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                packet = copy.deepcopy(fx.packet)
                packet["scientific_evidence"]["split_results"][0].update(mutation)
                with self.assertRaises(SchemaValidationError):
                    load_evidence_packet(encode(packet), chain=fx.chain)

        packet = copy.deepcopy(fx.packet)
        packet["scientific_evidence"]["split_results"][0]["rows"] = 160
        with self.assertRaises(SchemaValidationError):
            load_evidence_packet(encode(packet), chain=fx.chain)

    def test_underpower_and_attrition_deviations_remain_negative_evidence(self) -> None:
        fx = Fixture()
        deviations = (
            {
                "groups": 39,
                "enrolled_rows": 163,
                "analyzed_rows": 159,
                "missing_rows": 2,
                "excluded_rows": 2,
            },
            {
                "groups": 40,
                "enrolled_rows": 164,
                "analyzed_rows": 159,
                "missing_rows": 3,
                "excluded_rows": 2,
            },
        )
        for deviation in deviations:
            with self.subTest(deviation=deviation):
                packet = copy.deepcopy(fx.packet)
                packet["scientific_evidence"]["split_results"][0].update(deviation)
                loaded = load_evidence_packet(encode(packet), chain=fx.chain)
                assessment = verify_evidence_packet(
                    loaded, chain=fx.chain, artifact_registry=fx.registry()
                )
                self.assertEqual(
                    dict(loaded.payload["scientific_evidence"]["split_results"][0]),
                    packet["scientific_evidence"]["split_results"][0],
                )
                self.assertEqual(
                    assessment.preregistered_criteria,
                    "REPORTED_CRITERIA_NOT_MET",
                )
                self.assertEqual(assessment.scientific_eligibility, "INELIGIBLE")
                self.assertEqual(assessment.structural_completeness, "COMPLETE")

    def test_outcome_access_is_post_execution_and_exactly_bound_to_packet(self) -> None:
        fx = Fixture()
        receipt_raw = b"fixed-sample outcome receipt\n"
        receipt = ArtifactRef(**artifact_ref("fixed-sample-receipt", receipt_raw))
        interim_chain = PreregistrationChain(fx.loaded)
        with self.assertRaises(SchemaValidationError):
            interim_chain.record_outcome_access(
                accessed_at="2026-08-05T09:19:59Z",
                execution_completed_at="2026-08-05T09:20:00Z",
                receipt=receipt,
            )

        chain = PreregistrationChain(fx.loaded)
        chain.record_outcome_access(
            accessed_at="2026-08-05T09:20:00Z",
            execution_completed_at="2026-08-05T09:20:00Z",
            receipt=receipt,
        )
        packet = copy.deepcopy(fx.packet)
        packet["claim_binding"]["preregistration_chain_sha256"] = chain.chain_sha256
        load_evidence_packet(encode(packet), chain=chain)

        packet["execution"]["completed_at"] = "2026-08-05T09:19:59Z"
        with self.assertRaises(SchemaValidationError):
            load_evidence_packet(encode(packet), chain=chain)

    def test_bypass_mutated_outcome_access_cannot_be_rehashed_into_packet(self) -> None:
        fx = Fixture()
        outcome_access = fx.chain.outcome_access
        self.assertIsNotNone(outcome_access)
        object.__setattr__(
            outcome_access,
            "execution_completed_at",
            "2026-08-05T09:10:00Z",
        )
        packet = copy.deepcopy(fx.packet)
        packet["execution"]["completed_at"] = "2026-08-05T09:10:00Z"

        with self.assertRaises(SchemaValidationError):
            packet["claim_binding"]["preregistration_chain_sha256"] = fx.chain.chain_sha256
            load_evidence_packet(encode(packet), chain=fx.chain)


if __name__ == "__main__":
    unittest.main()
