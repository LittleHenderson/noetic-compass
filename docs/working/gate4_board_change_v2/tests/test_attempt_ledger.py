import pytest

from core import (
    AttemptLedger,
    ContractError,
    label_operation_id,
    record_authorized_attempt,
)
from helpers import (
    attempt,
    frozen_state,
    make_artifacts,
    make_generation_request,
    provider_evidence,
)


def test_failed_attempt_is_not_done_and_retry_must_link_exactly(tmp_path):
    _, validation, _, protocol_sha, _, state, _ = frozen_state(tmp_path)
    refs = make_artifacts(state.run_dir / "artifacts")
    ledger = AttemptLedger.for_run(state)
    operation = "generation/BCV2-N-000/turn-00"
    first = attempt(operation_id=operation, plan_sha=validation["plan_sha256"],
                    protocol_sha=protocol_sha,
                    evidence=provider_evidence(refs, accepted=False),
                    disposition="retryable")
    first_row = record_authorized_attempt(state, ledger, first)
    assert operation not in ledger.accepted_operations()
    assert operation in ledger.incomplete_operations()

    bad_retry = attempt(operation_id=operation, plan_sha=validation["plan_sha256"],
                        protocol_sha=protocol_sha,
                        evidence=provider_evidence(refs), attempt_no=2,
                        retry_of="wrong-attempt")
    with pytest.raises(ContractError, match="immediately prior"):
        record_authorized_attempt(state, ledger, bad_retry)

    good_retry = attempt(operation_id=operation, plan_sha=validation["plan_sha256"],
                         protocol_sha=protocol_sha,
                         evidence=provider_evidence(refs), attempt_no=2,
                         retry_of=first_row["attempt_id"])
    record_authorized_attempt(state, ledger, good_retry)
    assert operation in ledger.accepted_operations()
    with pytest.raises(ContractError, match="terminal"):
        record_authorized_attempt(
            state, ledger,
            attempt(operation_id=operation, plan_sha=validation["plan_sha256"],
                    protocol_sha=protocol_sha, evidence=provider_evidence(refs),
                    attempt_no=3, retry_of=good_retry["attempt_id"]),
        )


def test_repair_round_is_part_of_operation_identity():
    corpus_sha = "a" * 64
    main = label_operation_id(task="change", reader="glm", repair_round=0,
                              batch_ordinal=3, item_ids=["x", "y"], corpus_sha256=corpus_sha)
    repair1 = label_operation_id(task="change", reader="glm", repair_round=1,
                                 batch_ordinal=3, item_ids=["x", "y"], corpus_sha256=corpus_sha)
    repair2 = label_operation_id(task="change", reader="glm", repair_round=2,
                                 batch_ordinal=3, item_ids=["x", "y"], corpus_sha256=corpus_sha)
    assert len({main, repair1, repair2}) == 3
    assert "/main/" in main and "/repair-1/" in repair1 and "/repair-2/" in repair2


def test_accepted_attempt_requires_immutable_raw_evidence(tmp_path):
    _, validation, _, protocol_sha, _, state, _ = frozen_state(tmp_path)
    refs = make_artifacts(state.run_dir / "artifacts")
    ledger = AttemptLedger.for_run(state)
    evidence = provider_evidence(refs)
    evidence["response_headers_artifact"] = {"status": "unavailable", "reason": "SDK hid it"}
    row = attempt(operation_id="generation/BCV2-N-000/turn-00",
                  plan_sha=validation["plan_sha256"], protocol_sha=protocol_sha,
                  evidence=evidence)
    with pytest.raises(ContractError, match="response_headers_artifact must be present"):
        record_authorized_attempt(state, ledger, row)


def test_attempt_budget_derived_cost_and_hash_chain_fail_closed(tmp_path):
    plan, validation, _, protocol_sha, _, state, _ = frozen_state(
        tmp_path, max_attempts=1, max_cost="0.00001500"
    )
    refs = make_artifacts(state.run_dir / "artifacts")
    ledger = AttemptLedger.for_run(state)
    record_authorized_attempt(
        state, ledger,
        attempt(operation_id="generation/BCV2-N-000/turn-00",
                plan_sha=validation["plan_sha256"], protocol_sha=protocol_sha,
                evidence=provider_evidence(refs)),
    )
    admitted = ledger.verify()[0]
    assert admitted["cost_evidence"]["derived_cost_usd"] == "0.00001500"
    assert admitted["cost_evidence"]["classification"] == "MOCK_DERIVED_NOT_BILLING_EVIDENCE"
    refs2 = make_artifacts(
        state.run_dir / "artifacts", stem="second-conversation",
        request_payload=make_generation_request(plan["conversations"][4], 0, []),
    )
    with pytest.raises(ContractError, match="ceiling"):
        record_authorized_attempt(
            state, ledger,
            attempt(operation_id="generation/BCV2-N-004/turn-00",
                    plan_sha=validation["plan_sha256"], protocol_sha=protocol_sha,
                    evidence=provider_evidence(refs2)),
        )
    text = ledger.path.read_text(encoding="utf-8").replace("gemini", "tampered", 1)
    ledger.path.write_text(text, encoding="utf-8")
    with pytest.raises(ContractError, match="record hash mismatch"):
        AttemptLedger.for_run(state).records(force_verify=True)


def test_caller_cannot_declare_zero_cost_for_nonzero_usage(tmp_path):
    _, validation, _, protocol_sha, _, state, _ = frozen_state(tmp_path)
    refs = make_artifacts(state.run_dir / "artifacts")
    ledger = AttemptLedger.for_run(state)
    row = attempt(
        operation_id="generation/BCV2-N-000/turn-00",
        plan_sha=validation["plan_sha256"], protocol_sha=protocol_sha,
        evidence=provider_evidence(refs),
    )
    row["charged_cost_usd"] = "0"
    with pytest.raises(ContractError, match="fields must exactly match"):
        record_authorized_attempt(state, ledger, row)
