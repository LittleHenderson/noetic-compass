"""Focused tests for the isolated verified language apprenticeship lab."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json

import pytest

import cncm.language_apprenticeship as language


def _new_lab() -> language.LanguageApprenticeship:
    return language.LanguageApprenticeship(language._demo_morphology())


def _assert_no_float(value: object) -> None:
    assert not isinstance(value, float)
    if isinstance(value, dict):
        for key, child in value.items():
            _assert_no_float(key)
            _assert_no_float(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            _assert_no_float(child)


def test_typed_packets_are_immutable_strict_and_canonical() -> None:
    construction = language._active_construction()
    packet = language._lesson_for(construction)

    with pytest.raises(FrozenInstanceError):
        packet.teacher_confidence_basis_points = 10_000  # type: ignore[misc]

    assert packet.packet_content_id == language._lesson_for(construction).packet_content_id
    assert len(packet.packet_digest) == 64
    assert construction.construction_content_id.startswith("construction-")

    with pytest.raises(language.PacketValidationError, match="immutable tuple"):
        language.GrammarConstruction(
            construction_key="bad-list-pattern",
            revision=1,
            surface_pattern=list(construction.surface_pattern),  # type: ignore[arg-type]
            semantic_transformation=construction.semantic_transformation,
            claimed_scope="must fail before compilation",
        )

    with pytest.raises(language.PacketValidationError, match="basis_points"):
        replace(packet, teacher_confidence_basis_points=9_900.0)  # type: ignore[arg-type]


def test_compiler_rejects_unbounded_or_incoherent_patterns_without_eval() -> None:
    active = language._active_construction()
    bad_passive = language.GrammarConstruction(
        construction_key="bad-passive",
        revision=1,
        surface_pattern=(
            language.PatternAtom.noun_phrase("patient"),
            language.PatternAtom.literal("was"),
            language.PatternAtom.verb("predicate", language.VerbForm.PARTICIPLE),
            language.PatternAtom.noun_phrase("agent"),
        ),
        semantic_transformation=language.SemanticTransformation(
            predicate_slot="predicate",
            roles=(
                language.RoleBindingSpec("agent", "agent"),
                language.RoleBindingSpec("patient", "patient"),
            ),
            tense=language.Tense.PAST,
            polarity=language.Polarity.POSITIVE,
            voice=language.Voice.PASSIVE,
        ),
        claimed_scope="invalid because the by literal is absent",
    )
    compiler = language.BoundedPatternCompiler(language._demo_morphology())

    with pytest.raises(language.PatternCompilationError, match="'by'"):
        compiler.compile(bad_passive)

    with pytest.raises(language.PatternCompilationError, match="bounded token language"):
        compiler.parse((active,), "The cat chased the dog; __import__('os').system('x')")


def test_teacher_proposal_and_provisional_rule_do_not_mutate_active_grammar() -> None:
    lab = _new_lab()
    packet = language._lesson_for(language._active_construction())
    active_digest_before = lab.active_grammar_digest

    candidate = lab.submit_teacher_lesson(packet)

    assert candidate.status is language.CandidateStatus.LANG_PROPOSED
    assert lab.store.active_versions() == ()
    assert lab.active_grammar_digest == active_digest_before
    assert lab.parse("The cat chased the dog.").status is language.ParseStatus.UNKNOWN_CONSTRUCTION

    qualification = lab.qualify(
        candidate.candidate_id,
        language._suite_for(
            packet.construction,
            language.SuitePurpose.QUALIFICATION,
        ),
    )
    provisional = lab.promote_provisionally(candidate.candidate_id, qualification.receipt_id)

    assert qualification.passed is True
    assert provisional.status is language.VersionStatus.LANG_PROVISIONAL
    assert lab.store.active_versions() == ()
    assert lab.parse("The cat chased the dog.").status is language.ParseStatus.UNKNOWN_CONSTRUCTION
    assert (
        lab.parse("The cat chased the dog.", include_provisional=True).status
        is language.ParseStatus.PARSED
    )


def test_locally_issued_receipts_gate_provisional_and_durable_promotion() -> None:
    source_lab = _new_lab()
    target_lab = _new_lab()
    packet = language._lesson_for(language._active_construction())
    source_candidate = source_lab.submit_teacher_lesson(packet)
    target_candidate = target_lab.submit_teacher_lesson(packet)
    receipt = source_lab.qualify(
        source_candidate.candidate_id,
        language._suite_for(packet.construction, language.SuitePurpose.QUALIFICATION),
    )

    with pytest.raises(language.PromotionError, match="not issued by this laboratory"):
        target_lab.promote_provisionally(target_candidate.candidate_id, receipt.receipt_id)

    local_receipt = target_lab.qualify(
        target_candidate.candidate_id,
        language._suite_for(packet.construction, language.SuitePurpose.QUALIFICATION),
    )
    provisional = target_lab.promote_provisionally(
        target_candidate.candidate_id,
        local_receipt.receipt_id,
    )

    with pytest.raises(language.PromotionError, match="not issued by this laboratory"):
        target_lab.promote_durably(
            target_candidate.candidate_id,
            local_receipt.receipt_id,
            "retention-receipt-not-local",
        )

    retention = target_lab.evaluate_delayed_retention(
        target_candidate.candidate_id,
        local_receipt.receipt_id,
        language._suite_for(
            packet.construction,
            language.SuitePurpose.DELAYED_RETENTION,
        ),
    )
    durable = target_lab.promote_durably(
        target_candidate.candidate_id,
        local_receipt.receipt_id,
        retention.receipt_id,
    )

    assert provisional.version_id == durable.version_id
    assert durable.status is language.VersionStatus.LANG_ACTIVE
    assert target_lab.store.candidate(target_candidate.candidate_id).status is (
        language.CandidateStatus.LANG_DURABLE
    )


def test_qualification_receipt_has_complete_ordered_independent_ladder() -> None:
    lab = _new_lab()
    construction = language._active_construction()
    candidate = lab.submit_teacher_lesson(language._lesson_for(construction))
    suite = language._suite_for(construction, language.SuitePurpose.QUALIFICATION)

    receipt = lab.qualify(candidate.candidate_id, suite)

    assert receipt.passed is True
    assert receipt.examiner.channel is language.EvidenceChannel.PROTECTED_FIXTURE
    assert receipt.examiner.identity_id != candidate.packet.teacher.identity_id
    assert receipt.suite_digest == suite.suite_digest
    assert tuple(gate.gate for gate in receipt.gates) == language._QUALIFICATION_GATES
    assert all(gate.passed for gate in receipt.gates)
    assert len(receipt.receipt_digest) == 64


def test_teacher_cannot_be_relabelled_as_its_own_examiner() -> None:
    lab = _new_lab()
    construction = language._active_construction()
    packet = language._lesson_for(construction)
    candidate = lab.submit_teacher_lesson(packet)
    protected = language._suite_for(construction, language.SuitePurpose.QUALIFICATION)
    teacher_examiner = language.ExaminerIdentity(
        packet.teacher.model,
        packet.teacher.revision,
        language.EvidenceChannel.PROTECTED_FIXTURE,
    )

    with pytest.raises(language.QualificationError, match="teacher may not examine"):
        lab.qualify(candidate.candidate_id, replace(protected, examiner=teacher_examiner))


def test_failed_delayed_retention_quarantines_without_activation() -> None:
    lab = _new_lab()
    construction = language._active_construction()
    candidate = lab.submit_teacher_lesson(language._lesson_for(construction))
    qualification = lab.qualify(
        candidate.candidate_id,
        language._suite_for(construction, language.SuitePurpose.QUALIFICATION),
    )
    provisional = lab.promote_provisionally(candidate.candidate_id, qualification.receipt_id)
    valid_retention = language._suite_for(
        construction,
        language.SuitePurpose.DELAYED_RETENTION,
    )
    wrong_expected = language.SemanticFrame.event(
        "open",
        agent="door",
        patient="alice",
    )
    failed_retention = replace(
        valid_retention,
        held_out_examples=(
            language.SemanticExample(
                "retention-active-deliberate-failure",
                "Alice opened the door.",
                wrong_expected,
            ),
        ),
    )

    receipt = lab.evaluate_delayed_retention(
        candidate.candidate_id,
        qualification.receipt_id,
        failed_retention,
    )

    assert receipt.passed is False
    assert lab.store.version(provisional.version_id).status is (
        language.VersionStatus.LANG_QUARANTINED
    )
    assert lab.store.candidate(candidate.candidate_id).status is (
        language.CandidateStatus.LANG_QUARANTINED
    )
    assert lab.store.active_versions() == ()


def test_active_and_passive_preserve_meaning_but_role_reversal_does_not() -> None:
    lab = _new_lab()
    language._teach_durably(lab, language._active_construction())
    language._teach_durably(lab, language._passive_construction())

    active = lab.parse("The cat chased the dog.")
    passive = lab.parse("The dog was chased by the cat.")
    reversed_roles = lab.parse("The dog chased the cat.")

    assert active.status is passive.status is language.ParseStatus.PARSED
    assert active.semantics == passive.semantics
    assert active.semantics != reversed_roles.semantics
    assert active.frames[0].voice is language.Voice.ACTIVE
    assert passive.frames[0].voice is language.Voice.PASSIVE


def test_negation_preserves_predicate_and_roles_but_changes_polarity() -> None:
    lab = _new_lab()
    language._teach_durably(lab, language._active_construction())
    language._teach_durably(lab, language._negative_construction())

    positive = lab.parse("Maria kicked the ball.")
    negative = lab.parse("Maria did not kick the ball.")

    assert positive.status is negative.status is language.ParseStatus.PARSED
    assert positive.semantics is not None and negative.semantics is not None
    assert positive.semantics.predicate == negative.semantics.predicate == "kick"
    assert positive.semantics.roles == negative.semantics.roles
    assert positive.semantics.polarity is language.Polarity.POSITIVE
    assert negative.semantics.polarity is language.Polarity.NEGATIVE
    assert positive.semantics != negative.semantics


def test_version_supersession_and_rollback_restore_the_parent() -> None:
    lab = _new_lab()
    _, _, _, first = language._teach_durably(lab, language._active_construction(1))
    second_construction = language._active_construction(2)
    second_candidate = lab.submit_teacher_lesson(language._lesson_for(second_construction))
    second_qualification = lab.qualify(
        second_candidate.candidate_id,
        language._suite_for(second_construction, language.SuitePurpose.QUALIFICATION),
    )
    lab.promote_provisionally(second_candidate.candidate_id, second_qualification.receipt_id)
    second_retention = lab.evaluate_delayed_retention(
        second_candidate.candidate_id,
        second_qualification.receipt_id,
        language._suite_for(
            second_construction,
            language.SuitePurpose.DELAYED_RETENTION,
        ),
    )
    second = lab.promote_durably(
        second_candidate.candidate_id,
        second_qualification.receipt_id,
        second_retention.receipt_id,
        supersedes_version_id=first.version_id,
    )

    assert lab.store.version(first.version_id).status is language.VersionStatus.LANG_SUPERSEDED
    assert lab.store.version(second.version_id).status is language.VersionStatus.LANG_ACTIVE
    assert len(lab.store.active_versions()) == 1

    rolled_back = lab.rollback(second.version_id, "protected post-promotion regression")

    assert rolled_back.status is language.VersionStatus.LANG_ROLLED_BACK
    assert lab.store.version(first.version_id).status is language.VersionStatus.LANG_ACTIVE
    assert lab.store.candidate(first.candidate_id).status is language.CandidateStatus.LANG_DURABLE
    assert len(lab.store.active_versions()) == 1
    assert lab.parse("The cat chased the dog.").status is language.ParseStatus.PARSED


@pytest.mark.parametrize("case_id", language.language_qualification_demo_cases())
def test_browser_demo_is_canonical_primitive_local_and_authority_explicit(
    case_id: str,
) -> None:
    first = language.run_language_qualification_demo(case_id)
    second = language.run_language_qualification_demo(case_id)

    assert first == second
    assert first["state_scope"] == "LOCAL LANGUAGE STORE ONLY"
    assert first["authority_boundary"] == {
        "cas_rrk_promotion_receipt": False,
        "cncm_state_writes": 0,
        "kernel_integrated": False,
    }
    _assert_no_float(first)
    json.dumps(first, sort_keys=True, allow_nan=False)


def test_browser_demo_rejects_unknown_case() -> None:
    with pytest.raises(language.PacketValidationError, match="unknown demo case"):
        language.run_language_qualification_demo("not-a-demo")
