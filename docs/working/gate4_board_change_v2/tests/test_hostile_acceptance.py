import copy

import pytest

from core import (
    AttemptLedger,
    ContractError,
    ExperimentState,
    FROZEN_PLAN_NAME,
    PHASE_MOCK_GENERATION_COMPLETE,
    canonical_json_bytes,
    record_authorized_attempt,
    seal_corpus,
    sha256_file,
    sha256_bytes,
    validate_prompt_plan,
    validate_provider_evidence,
)
from helpers import (
    attempt,
    frozen_state,
    ManualClock,
    make_artifacts,
    make_authorization,
    make_label_contract,
    make_plan,
    make_protocol_fixture,
    provider_evidence,
)


def one_generation_attempt(tmp_path):
    _, validation, _, protocol_sha, _, state, _ = frozen_state(tmp_path)
    refs = make_artifacts(state.run_dir / "artifacts")
    row = attempt(
        operation_id="generation/BCV2-N-000/turn-00",
        plan_sha=validation["plan_sha256"], protocol_sha=protocol_sha,
        evidence=provider_evidence(refs),
    )
    return validation, protocol_sha, state, AttemptLedger.for_run(state), refs, row


def test_public_append_is_permanently_audit_only_and_cannot_spend_budget(tmp_path):
    _, _, state, ledger, _, row = one_generation_attempt(tmp_path)
    imported = ledger.append(row)
    assert imported["classification"] == "AUDIT_ONLY_UNTRUSTED_NEVER_ACCEPTABLE"
    assert ledger.audit_records()[0]["source_payload_sha256"]
    assert not ledger.path.exists()
    assert ledger.accepted_operations() == {}

    admitted = record_authorized_attempt(state, ledger, row)
    assert admitted["admission"]["status"] == "MOCK_ONLY_NEVER_PRODUCTION"
    assert len(ledger.verify_for_state(state)) == 1


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("run_id", "other-run", "run_id"),
        ("protocol_lock_sha256", "a" * 64, "protocol lock"),
        ("prompt_plan_sha256", "b" * 64, "prompt plan"),
    ],
)
def test_wrong_run_protocol_or_plan_never_enters_production_ledger(
    tmp_path, field, value, message
):
    _, _, state, ledger, _, row = one_generation_attempt(tmp_path)
    row[field] = value
    with pytest.raises(ContractError, match=message):
        record_authorized_attempt(state, ledger, row)
    assert not ledger.path.exists()


def test_accepted_length_error_or_unverifiable_raw_answer_is_rejected(tmp_path):
    _, _, state, ledger, _, row = one_generation_attempt(tmp_path)
    row["provider_evidence"]["finish_reason"] = {"status": "present", "value": "length"}
    with pytest.raises(ContractError, match="finish_reason=stop"):
        record_authorized_attempt(state, ledger, row)

    _, _, state2, ledger2, _, row2 = one_generation_attempt(tmp_path / "hash")
    row2["provider_evidence"]["response_extraction"]["extracted_text_sha256"] = "c" * 64
    with pytest.raises(ContractError, match="does not match raw response"):
        record_authorized_attempt(state2, ledger2, row2)

    _, _, state3, ledger3, _, row3 = one_generation_attempt(tmp_path / "pointer")
    response_ref = row3["provider_evidence"]["response_artifact"]
    response_path = state3.run_dir / "artifacts" / response_ref["relative_path"]
    response_path.write_bytes(canonical_json_bytes({"model": "mock-model", "not_answer": "mocked"}))
    response_ref["sha256"] = sha256_file(response_path)
    response_ref["bytes"] = response_path.stat().st_size
    row3["provider_evidence"]["transport_receipt"]["response_body_sha256"] = response_ref[
        "sha256"
    ]
    with pytest.raises(ContractError, match="pointer key is absent"):
        record_authorized_attempt(state3, ledger3, row3)


def test_frozen_plan_cannot_be_replaced_after_protocol_freeze(tmp_path):
    _, _, state, ledger, _, row = one_generation_attempt(tmp_path)
    frozen_path = state.run_dir / FROZEN_PLAN_NAME
    changed = copy.deepcopy(__import__("json").loads(frozen_path.read_text(encoding="utf-8")))
    changed["conversations"][0]["seed_prompt"] += " mutated"
    frozen_path.write_bytes(canonical_json_bytes(changed))
    with pytest.raises(ContractError, match="PROTOCOL_FROZEN artifact mismatch"):
        record_authorized_attempt(state, ledger, row)


def test_freeze_recomputes_protocol_validation_and_rejects_caller_assertions(tmp_path):
    plan = make_plan()
    validation = validate_prompt_plan(plan)
    source_root, lock, _ = make_protocol_fixture(tmp_path, plan)
    lock["claim_bearing_files"] = []
    protocol_sha = sha256_bytes(canonical_json_bytes(lock))
    state = ExperimentState(tmp_path / "run-forged-freeze")
    state.initialize(
        run_id="forged-freeze", protocol_lock_sha256=protocol_sha,
        prompt_plan_sha256=validation["plan_sha256"],
    )
    with pytest.raises(ContractError, match="claim_bearing_files must be a non-empty array"):
        state.freeze_protocol(prompt_plan=plan, protocol_lock=lock, source_root=source_root)


def test_authority_and_caller_injected_clock_or_verifier_are_impossible(tmp_path):
    _, validation, _, protocol_sha, authorization, state, _ = frozen_state(
        tmp_path, start_generation=False
    )
    with pytest.raises(ContractError, match="cannot authorize FULL"):
        state.authorize_full(authorization)

    backdated = make_authorization(
        validation["plan_sha256"], protocol_sha,
        authorized_at="2026-08-20T07:00:00Z", expires_at="2026-08-20T08:30:00Z",
    )
    with pytest.raises(TypeError):
        state.authorize_full(backdated, authority_verifier=lambda *_: {"verified": True})
    with pytest.raises(TypeError):
        ExperimentState(tmp_path / "fake-clock", clock=ManualClock())


def test_foreign_ledger_path_cannot_be_used_for_production_acceptance(tmp_path):
    _, _, state, _, _, row = one_generation_attempt(tmp_path)
    foreign = AttemptLedger(tmp_path / "foreign.jsonl", state.run_dir / "artifacts")
    with pytest.raises(ContractError, match="fixed run ledger"):
        record_authorized_attempt(state, foreign, row)


def test_label_raw_json_requires_exact_alias_ids_and_allowlisted_labels(tmp_path):
    answer = '[{"id":1001,"label":"CHANGE"},{"id":1002,"label":"SAME"}]'
    alias_map = [
        {"alias_id": 1001, "item_id": "pair-a"},
        {"alias_id": 1002, "item_id": "pair-b"},
    ]
    contract = make_label_contract(alias_map, answer)
    refs = make_artifacts(tmp_path / "artifacts", answer=answer, stem="labels-good")
    evidence = provider_evidence(refs, answer=answer, operation_kind="label")
    assert validate_provider_evidence(
        evidence, artifact_root=tmp_path / "artifacts", accepted=True,
        operation_kind="label", label_contract=contract, task="change",
    )["parsed_answer"]

    fabricated = '[{"id":1001,"label":"CHANGE"},{"id":9999,"label":"SAME"}]'
    bad_refs = make_artifacts(tmp_path / "artifacts", answer=fabricated, stem="labels-bad")
    bad_evidence = provider_evidence(
        bad_refs, answer=fabricated, operation_kind="label"
    )
    with pytest.raises(ContractError, match="fabricated, duplicate, or missing"):
        validate_provider_evidence(
            bad_evidence, artifact_root=tmp_path / "artifacts", accepted=True,
            operation_kind="label", label_contract=contract, task="change",
        )


def test_direct_internal_transition_cannot_skip_evidence_phases(tmp_path):
    _, _, _, _, _, state, _ = frozen_state(tmp_path)
    with pytest.raises(ContractError, match="direct state transitions are forbidden"):
        state._transition(PHASE_MOCK_GENERATION_COMPLETE, "MOCK_GENERATION_COMPLETED", {})


def test_bogus_request_wrong_origin_and_secret_header_are_rejected(tmp_path):
    _, _, state, ledger, refs, row = one_generation_attempt(tmp_path / "request")
    request_ref = row["provider_evidence"]["request_artifact"]
    request_path = state.run_dir / "artifacts" / request_ref["relative_path"]
    request_path.write_bytes(canonical_json_bytes({"messages": ["mocked"]}))
    request_ref["sha256"] = sha256_file(request_path)
    request_ref["bytes"] = request_path.stat().st_size
    row["provider_evidence"]["transport_receipt"]["request_body_sha256"] = request_ref["sha256"]
    with pytest.raises(ContractError, match="raw generation request does not equal"):
        record_authorized_attempt(state, ledger, row)

    _, _, state2, ledger2, _, row2 = one_generation_attempt(tmp_path / "origin")
    row2["provider_evidence"]["endpoint_origin"] = "https://unrelated.example"
    with pytest.raises(ContractError, match="exact allowlisted provider origin"):
        record_authorized_attempt(state2, ledger2, row2)

    _, _, state3, ledger3, _, row3 = one_generation_attempt(tmp_path / "secret")
    header_ref = row3["provider_evidence"]["response_headers_artifact"]
    header_path = state3.run_dir / "artifacts" / header_ref["relative_path"]
    header_path.write_bytes(canonical_json_bytes({"Authorization": "Bearer top-secret-value"}))
    header_ref["sha256"] = sha256_file(header_path)
    header_ref["bytes"] = header_path.stat().st_size
    row3["provider_evidence"]["transport_receipt"]["response_headers_sha256"] = header_ref["sha256"]
    with pytest.raises(ContractError, match="secret-bearing"):
        record_authorized_attempt(state3, ledger3, row3)
