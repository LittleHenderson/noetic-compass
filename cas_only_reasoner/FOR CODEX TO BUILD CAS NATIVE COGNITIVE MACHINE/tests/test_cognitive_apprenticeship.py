"""Focused tests for the isolated domain-neutral CCB-T1 laboratory."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path

import pytest

import cncm.cognitive_apprenticeship as apprenticeship


def _new_board(
    installed: tuple[apprenticeship.InstalledCapability, ...] | None = None,
) -> apprenticeship.CognitiveApprenticeship:
    return apprenticeship.CognitiveApprenticeship(
        apprenticeship._demo_installed_capabilities()
        if installed is None
        else installed
    )


def _qualify_case(
    board: apprenticeship.CognitiveApprenticeship,
    case_id: str,
) -> tuple[
    apprenticeship.LessonProposal,
    apprenticeship.QualificationReceipt,
    apprenticeship.ExaminationSuite,
    apprenticeship.CASOhmObservation,
]:
    proposal, expansion, suite, retention, observation = apprenticeship._demo_material(
        case_id
    )
    board.submit_teacher_proposal(proposal)
    prerequisite = board.check_prerequisites(proposal.proposal_id)
    expansion_id = board.register_cas_sdg_expansion(expansion)
    receipt = board.qualify(
        proposal.proposal_id,
        prerequisite.receipt_id,
        expansion_id,
        suite,
    )
    return proposal, receipt, retention, observation


def _promote_case(
    board: apprenticeship.CognitiveApprenticeship,
    case_id: str,
    *,
    parent_version_id: str | None = None,
) -> tuple[
    apprenticeship.LessonProposal,
    apprenticeship.QualificationReceipt,
    apprenticeship.RetentionReceipt,
    apprenticeship.CapabilityVersion,
]:
    proposal, qualification, retention_suite, _ = _qualify_case(board, case_id)
    board.promote_provisionally(proposal.proposal_id, qualification.receipt_id)
    retention = board.evaluate_delayed_retention(
        proposal.proposal_id,
        qualification.receipt_id,
        retention_suite,
    )
    durable = board.promote_durably(
        proposal.proposal_id,
        qualification.receipt_id,
        retention.receipt_id,
        parent_version_id=parent_version_id,
    )
    return proposal, qualification, retention, durable


def _assert_no_float(value: object) -> None:
    assert not isinstance(value, float)
    if isinstance(value, dict):
        for key, child in value.items():
            _assert_no_float(key)
            _assert_no_float(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_no_float(child)


def test_packets_are_frozen_strict_and_canonical() -> None:
    proposal, expansion, suite, _, observation = apprenticeship._demo_material(
        "exact_reasoning_math"
    )

    with pytest.raises(FrozenInstanceError):
        proposal.teacher_confidence_basis_points = 10_000  # type: ignore[misc]

    with pytest.raises(apprenticeship.ApprenticeshipValidationError, match="basis_points"):
        replace(proposal, teacher_confidence_basis_points=9_800.0)  # type: ignore[arg-type]

    assert proposal.proposal_id == replace(proposal).proposal_id
    assert len(proposal.proposal_digest) == 64
    assert expansion.proposal_id == proposal.proposal_id
    assert len(suite.suite_id_digest) == 64
    assert observation.observational_only is True
    assert observation.promotion_authority is False


def test_procedure_interpreter_has_no_dynamic_code_path() -> None:
    source = Path(apprenticeship.__file__).read_text(encoding="utf-8")

    assert "eval(" not in source
    assert "exec(" not in source
    assert "subprocess" not in source
    assert "importlib" not in source


def test_teacher_submission_is_proposal_only() -> None:
    board = _new_board()
    proposal, _, _, _, _ = apprenticeship._demo_material("exact_reasoning_math")
    before = board.active_local_digest

    episode = board.submit_teacher_proposal(proposal)

    assert episode.status is apprenticeship.EpisodeStatus.PROPOSED
    assert episode.honest_outcome is apprenticeship.HonestOutcome.PROPOSAL_RECORDED_ONLY
    assert board.active_local_digest == before
    assert board.store.active_versions() == ()
    unavailable = board.run_local_capability(
        proposal.artifact.capability_key,
        apprenticeship._named_values(a="2", b="3", c="11"),
    )
    assert unavailable.status is apprenticeship.ExecutionStatus.UNSUPPORTED_ARTIFACT


def test_missing_prerequisite_is_reported_honestly() -> None:
    board = _new_board(())
    proposal, _, _, _, _ = apprenticeship._demo_material("exact_reasoning_math")
    board.submit_teacher_proposal(proposal)

    receipt = board.check_prerequisites(proposal.proposal_id)
    episode = board.store.episode_for_proposal(proposal.proposal_id)

    assert receipt.passed is False
    assert episode.status is apprenticeship.EpisodeStatus.PREREQUISITE_BLOCKED
    assert episode.honest_outcome is apprenticeship.HonestOutcome.MISSING_PREREQUISITE
    assert board.store.active_versions() == ()


def test_teacher_cannot_generate_or_examine_its_own_lesson() -> None:
    board = _new_board()
    proposal, expansion, suite, _, _ = apprenticeship._demo_material(
        "exact_reasoning_math"
    )
    board.submit_teacher_proposal(proposal)
    prerequisite = board.check_prerequisites(proposal.proposal_id)
    teacher = proposal.teachers[0].teacher
    teacher_sdg = replace(
        expansion,
        generator=apprenticeship.CASSDGIdentity(teacher.principal, teacher.revision),
    )

    with pytest.raises(
        apprenticeship.ApprenticeshipQualificationError,
        match="separate from teacher",
    ):
        board.register_cas_sdg_expansion(teacher_sdg)

    expansion_id = board.register_cas_sdg_expansion(expansion)
    teacher_examiner = replace(
        suite,
        examiner=apprenticeship.ExaminerIdentity(
            teacher.principal,
            teacher.revision,
            "protected-fixture-custody",
        ),
    )
    with pytest.raises(
        apprenticeship.ApprenticeshipQualificationError,
        match="teacher cannot hold examiner custody",
    ):
        board.qualify(
            proposal.proposal_id,
            prerequisite.receipt_id,
            expansion_id,
            teacher_examiner,
        )


def test_protected_fixture_ids_must_be_held_out_from_teacher_and_sdg() -> None:
    board = _new_board()
    proposal, expansion, suite, _, _ = apprenticeship._demo_material(
        "exact_reasoning_math"
    )
    board.submit_teacher_proposal(proposal)
    prerequisite = board.check_prerequisites(proposal.proposal_id)
    expansion_id = board.register_cas_sdg_expansion(expansion)
    contaminated = replace(
        suite,
        held_out_cases=(replace(suite.held_out_cases[0], case_id=expansion.transfer_cases[0].case_id),),
    )

    with pytest.raises(
        apprenticeship.ApprenticeshipQualificationError,
        match="held out",
    ):
        board.qualify(
            proposal.proposal_id,
            prerequisite.receipt_id,
            expansion_id,
            contaminated,
        )


def test_exact_reasoning_transfers_and_uses_exact_rationals() -> None:
    board = _new_board()
    proposal, qualification, retention, durable = _promote_case(
        board, "exact_reasoning_math"
    )

    assert qualification.passed is True
    assert retention.passed is True
    assert durable.status is apprenticeship.VersionStatus.ACTIVE_LOCAL
    result = board.run_local_capability(
        proposal.artifact.capability_key,
        apprenticeship._named_values(a="4", b="1", c="3"),
    )
    assert result.status is apprenticeship.ExecutionStatus.SUCCESS
    assert result.outputs == apprenticeship._named_values(x="1/2")
    assert board.store.episode_for_proposal(proposal.proposal_id).honest_outcome is (
        apprenticeship.HonestOutcome.DURABLE_LOCAL_ONLY
    )


def test_tool_use_requires_permission_and_preserves_full_procedure() -> None:
    board = _new_board()
    proposal, _, _, _ = _promote_case(board, "tool_use_procedure")

    denied = board.run_local_capability(
        proposal.artifact.capability_key,
        apprenticeship._named_values(
            permission_granted="false",
            tool_name="database",
        ),
    )
    allowed = board.run_local_capability(
        proposal.artifact.capability_key,
        apprenticeship._named_values(
            permission_granted="true",
            tool_name="database",
        ),
    )

    assert denied.status is apprenticeship.ExecutionStatus.PERMISSION_REQUIRED
    assert allowed.status is apprenticeship.ExecutionStatus.SUCCESS
    assert dict((value.name, value.value) for value in allowed.outputs)["procedure"] == (
        apprenticeship._TOOL_PROCEDURE
    )


def test_changing_fact_is_source_linked_and_expires_honestly() -> None:
    board = _new_board()
    proposal, _, _, _ = _promote_case(board, "source_grounded_changing_fact")

    current = board.run_local_capability(
        proposal.artifact.capability_key,
        apprenticeship._named_values(as_of="2026-09-01"),
    )
    stale = board.run_local_capability(
        proposal.artifact.capability_key,
        apprenticeship._named_values(as_of="2026-10-01"),
    )

    assert proposal.artifact.source_claim is not None
    assert len(proposal.artifact.source_claim.source_digest) == 64
    assert current.status is apprenticeship.ExecutionStatus.SUCCESS
    assert current.outputs == apprenticeship._named_values(release="v3.2.1")
    assert stale.status is apprenticeship.ExecutionStatus.SOURCE_OUTSIDE_VALIDITY_WINDOW
    assert stale.outputs == ()
    assert board.store.episode_for_proposal(proposal.proposal_id).honest_outcome is (
        apprenticeship.HonestOutcome.SOURCE_GROUNDED_LOCAL_ONLY
    )


def test_protected_authority_category_never_promotes() -> None:
    board = _new_board()
    proposal, receipt, _, _ = _qualify_case(
        board, "protected_authority_rejection"
    )
    episode = board.store.episode_for_proposal(proposal.proposal_id)

    assert receipt.passed is False
    assert receipt.gates[-1].gate is apprenticeship.QualificationGate.PROTECTED_CATEGORY_ALLOWED
    assert episode.status is apprenticeship.EpisodeStatus.PROTECTED_REJECTED
    assert episode.honest_outcome is (
        apprenticeship.HonestOutcome.PROTECTED_REQUIRES_SEPARATE_AUTHORITY
    )
    assert board.store.active_versions() == ()
    assert board.store.provisional_versions() == ()
    with pytest.raises(
        apprenticeship.ApprenticeshipPromotionError,
        match="never autonomously promote",
    ):
        board.promote_provisionally(proposal.proposal_id, receipt.receipt_id)


def test_cas_ohm_metrics_are_observational_and_do_not_change_promotion() -> None:
    board = _new_board()
    proposal, qualification, retention, durable = _promote_case(
        board, "exact_reasoning_math"
    )
    active_digest = board.active_local_digest
    before_receipt = qualification.receipt_id
    arbitrary_observation = apprenticeship.CASOhmObservation.create(
        "arbitrary-observation",
        apprenticeship.CapabilityMetrics(
            100,
            900,
            50,
            apprenticeship.EffectStatus.INCORRECT,
        ),
        apprenticeship.CapabilityMetrics(
            90,
            950,
            40,
            apprenticeship.EffectStatus.INCORRECT,
        ),
    )

    episode = board.record_cas_ohm_observation(
        proposal.proposal_id,
        arbitrary_observation,
    )

    assert episode.cas_ohm_observation == arbitrary_observation
    assert board.active_local_digest == active_digest
    assert board.store.version(durable.version_id).status is (
        apprenticeship.VersionStatus.ACTIVE_LOCAL
    )
    assert qualification.receipt_id == before_receipt
    assert retention.passed is True


def test_failed_delayed_retention_rolls_back_provisional_version() -> None:
    board = _new_board()
    proposal, qualification, retention_suite, _ = _qualify_case(
        board, "exact_reasoning_math"
    )
    provisional = board.promote_provisionally(
        proposal.proposal_id,
        qualification.receipt_id,
    )
    bad_case = replace(
        retention_suite.held_out_cases[0],
        expected_outputs=apprenticeship._named_values(x="999"),
    )
    failed_suite = replace(retention_suite, held_out_cases=(bad_case,))

    retention = board.evaluate_delayed_retention(
        proposal.proposal_id,
        qualification.receipt_id,
        failed_suite,
    )

    assert retention.passed is False
    assert board.store.version(provisional.version_id).status is (
        apprenticeship.VersionStatus.ROLLED_BACK
    )
    assert board.store.episode_for_proposal(proposal.proposal_id).honest_outcome is (
        apprenticeship.HonestOutcome.RETENTION_FAILED_ROLLED_BACK
    )
    assert board.store.active_versions() == ()


def test_versioned_episode_supersession_and_rollback_restore_parent() -> None:
    board = _new_board()
    first_proposal, _, _, first = _promote_case(board, "exact_reasoning_math")
    proposal, expansion, suite, retention_suite, _ = apprenticeship._demo_material(
        "exact_reasoning_math"
    )
    proposal = replace(
        proposal,
        lesson_id="ccb-t1-demo-exact-reasoning-math-r2",
        artifact=apprenticeship._math_artifact(2),
    )
    expansion = replace(
        expansion,
        proposal_id=proposal.proposal_id,
        independent_seed="sdg-seed-exact-reasoning-math-r2",
    )
    suite = replace(
        suite,
        suite_id="qualification-exact-reasoning-math-r2",
        custody_seed="protected-qualification-seed-exact-reasoning-math-r2",
    )
    retention_suite = replace(
        retention_suite,
        suite_id="retention-exact-reasoning-math-r2",
        custody_seed="protected-retention-seed-exact-reasoning-math-r2",
    )
    board.submit_teacher_proposal(proposal)
    prerequisite = board.check_prerequisites(proposal.proposal_id)
    expansion_id = board.register_cas_sdg_expansion(expansion)
    qualification = board.qualify(
        proposal.proposal_id,
        prerequisite.receipt_id,
        expansion_id,
        suite,
    )
    board.promote_provisionally(proposal.proposal_id, qualification.receipt_id)
    retention = board.evaluate_delayed_retention(
        proposal.proposal_id,
        qualification.receipt_id,
        retention_suite,
    )
    second = board.promote_durably(
        proposal.proposal_id,
        qualification.receipt_id,
        retention.receipt_id,
        parent_version_id=first.version_id,
    )

    assert board.store.version(first.version_id).status is (
        apprenticeship.VersionStatus.SUPERSEDED
    )
    assert board.store.version(second.version_id).status is (
        apprenticeship.VersionStatus.ACTIVE_LOCAL
    )

    rolled_back = board.rollback(second.version_id, "post-promotion regression")

    assert rolled_back.status is apprenticeship.VersionStatus.ROLLED_BACK
    assert board.store.version(first.version_id).status is (
        apprenticeship.VersionStatus.ACTIVE_LOCAL
    )
    assert board.store.episode_for_proposal(first_proposal.proposal_id).status is (
        apprenticeship.EpisodeStatus.DURABLE_LOCAL
    )
    history = board.store.episode_history(
        board.store.episode_for_proposal(proposal.proposal_id).episode_id
    )
    assert history[-1].rollback_pointer == first.version_id
    assert len(history) >= 5


@pytest.mark.parametrize(
    ("case_id", "expected_outcome"),
    (
        (
            "exact_reasoning_math",
            apprenticeship.HonestOutcome.DURABLE_LOCAL_ONLY.value,
        ),
        (
            "tool_use_procedure",
            apprenticeship.HonestOutcome.DURABLE_LOCAL_ONLY.value,
        ),
        (
            "source_grounded_changing_fact",
            apprenticeship.HonestOutcome.SOURCE_GROUNDED_LOCAL_ONLY.value,
        ),
        (
            "protected_authority_rejection",
            apprenticeship.HonestOutcome.PROTECTED_REQUIRES_SEPARATE_AUTHORITY.value,
        ),
    ),
)
def test_browser_demos_are_deterministic_primitive_and_authority_explicit(
    case_id: str,
    expected_outcome: str,
) -> None:
    first = apprenticeship.run_cognitive_apprenticeship_demo(case_id)
    second = apprenticeship.run_cognitive_apprenticeship_demo(case_id)

    assert first == second
    assert first["honest_outcome"] == expected_outcome
    assert first["state_scope"] == "LOCAL CCB-T1 STORE ONLY"
    assert first["proposal"]["proposal_directly_changed_active_local_store"] is False
    assert first["authority_boundary"] == {
        "cas_ohm_promotion_authority": False,
        "cas_rrk_commits": 0,
        "cas_rrk_promotion_receipt": False,
        "cncm_state_writes": 0,
        "kernel_integrated": False,
    }
    _assert_no_float(first)
    json.dumps(first, sort_keys=True, allow_nan=False)


def test_browser_demo_catalog_and_unknown_case() -> None:
    assert apprenticeship.cognitive_apprenticeship_demo_cases() == (
        "exact_reasoning_math",
        "tool_use_procedure",
        "source_grounded_changing_fact",
        "protected_authority_rejection",
    )
    with pytest.raises(
        apprenticeship.ApprenticeshipValidationError,
        match="unknown demo case",
    ):
        apprenticeship.run_cognitive_apprenticeship_demo("unknown")
