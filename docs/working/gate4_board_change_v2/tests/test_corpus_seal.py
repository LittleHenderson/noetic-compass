import pytest

from core import (
    AttemptLedger,
    ContractError,
    complete_generation_if_ready,
    generation_operation_id,
    label_operation_id,
    record_authorized_attempt,
    seal_corpus,
    start_labeling,
    verify_corpus_seal,
)
from helpers import (
    attempt,
    frozen_state,
    make_artifacts,
    make_corpus,
    make_generation_request,
    make_label_contract,
    provider_evidence,
)


def complete_mock_generation(tmp_path):
    plan, validation, _, protocol_sha, _, state, _ = frozen_state(tmp_path)
    ledger = AttemptLedger.for_run(state)
    for ordinal, planned in enumerate(plan["conversations"]):
        prior_answers = []
        for turn_index in range(10):
            operation_id = generation_operation_id(planned["conversation_id"], turn_index)
            answer = f"Mock provider output for {planned['conversation_id']} turn {turn_index}."
            refs = make_artifacts(
                state.run_dir / "artifacts", answer=answer,
                stem=f"generation-{ordinal:03d}-{turn_index:02d}",
                request_payload=make_generation_request(
                    planned, turn_index, prior_answers
                ),
            )
            record_authorized_attempt(
                state, ledger,
                attempt(
                    operation_id=operation_id,
                    plan_sha=validation["plan_sha256"], protocol_sha=protocol_sha,
                    evidence=provider_evidence(
                        refs, answer=answer, provider=planned["generator"]["provider"]
                    ),
                ),
            )
            prior_answers.append(answer)
    complete_generation_if_ready(state, ledger)
    return plan, validation, protocol_sha, state, ledger


def test_complete_generation_seal_then_label_order_is_enforced(tmp_path):
    plan, validation, protocol_sha, state, ledger = complete_mock_generation(tmp_path)
    corpus = make_corpus(plan, ledger.accepted_operations_for_state(state))
    bad_corpus = make_corpus(plan, ledger.accepted_operations_for_state(state))
    bad_corpus[0]["turns"][0]["assistant_text"] = "fabricated text not in raw response"
    from core import sha256_text
    bad_corpus[0]["turns"][0]["assistant_text_sha256"] = sha256_text(
        bad_corpus[0]["turns"][0]["assistant_text"]
    )
    with pytest.raises(ContractError, match="does not equal raw provider response"):
        seal_corpus(state=state, ledger=ledger, corpus_rows=bad_corpus)

    seal = seal_corpus(state=state, ledger=ledger, corpus_rows=corpus)
    assert seal["conversation_count"] == 92
    assert seal["assistant_turn_count"] == 920
    assert seal["labels_present_before_seal"] is False
    assert verify_corpus_seal(state.run_dir)["valid"] is True
    start_labeling(state)

    answer = '[{"id":1001,"label":"CHANGE"}]'
    alias_map = [{"alias_id": 1001, "item_id": "pair-a"}]
    label_contract = make_label_contract(alias_map, answer)
    refs = make_artifacts(
        state.run_dir / "artifacts", answer=answer, stem="predating-label"
    )
    operation_id = label_operation_id(
        task="change", reader="gemini", repair_round=0, batch_ordinal=0,
        item_ids=["pair-a"], corpus_sha256=seal["corpus_sha256"],
    )
    predating = attempt(
        operation_id=operation_id,
        plan_sha=validation["plan_sha256"], protocol_sha=protocol_sha,
        evidence=provider_evidence(
            refs, answer=answer, operation_kind="label",
            started=seal["sealed_at_utc"], finished=seal["sealed_at_utc"],
        ),
        operation_kind="label", task="change", corpus_sha=seal["corpus_sha256"],
        label_contract=label_contract,
    )
    with pytest.raises(ContractError, match="predates the corpus seal"):
        record_authorized_attempt(state, ledger, predating)

    sealed_path = state.run_dir / "corpus.sealed.jsonl"
    sealed_path.write_bytes(sealed_path.read_bytes() + b" ")
    with pytest.raises(ContractError, match="corpus seal artifacts disagree"):
        verify_corpus_seal(state.run_dir)
