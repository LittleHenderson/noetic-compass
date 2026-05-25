from __future__ import annotations

from api.services.cas_harness_verdict_runner import run_evidence_gated_verdict


def _chip(chip_id: str, status: str) -> dict[str, str]:
    return {
        "id": chip_id,
        "name": chip_id,
        "status": status,
        "detail": f"{chip_id} is {status}",
    }


def _complete_chips(status: str = "present") -> list[dict[str, str]]:
    return [
        _chip("model_proof", status),
        _chip("cas_readout", status),
        _chip("causal_proof", status),
        _chip("control_proof", status),
        _chip("output_proof", status),
        _chip("packet_proof", status),
    ]


def test_no_evidence_packet_means_runner_does_not_compute_verdict():
    result = run_evidence_gated_verdict(
        evidence_packet_trace_id=None,
        proof_chips=_complete_chips(),
    )

    assert result.status == "SCAFFOLD_PENDING_RUNNER"
    assert result.verdict is None
    assert result.confidence is None
    assert "no Evidence Packet" in result.message


def test_missing_required_chip_flags_for_human_review_not_accept():
    chips = _complete_chips()
    chips[3] = _chip("control_proof", "missing")

    result = run_evidence_gated_verdict(
        evidence_packet_trace_id="trace-123",
        proof_chips=chips,
    )

    assert result.status == "COMPLETE"
    assert result.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert result.confidence is None
    assert result.missing_or_unavailable == ("control_proof",)
    assert "missing required proof" in result.message


def test_failed_required_chip_flags_for_human_review():
    chips = _complete_chips()
    chips[2] = _chip("causal_proof", "failed")

    result = run_evidence_gated_verdict(
        evidence_packet_trace_id="trace-123",
        proof_chips=chips,
    )

    assert result.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert result.confidence is None
    assert result.failed == ("causal_proof",)
    assert "required proof chips failed" in result.message


def test_complete_proof_chips_still_do_not_create_accept_without_verifier_decision():
    result = run_evidence_gated_verdict(
        evidence_packet_trace_id="trace-123",
        proof_chips=_complete_chips("verified"),
    )

    assert result.status == "COMPLETE"
    assert result.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert result.confidence is None
    assert "no explicit Stage 19/20/21 verifier decision" in result.message


def test_explicit_verifier_decision_can_accept_when_required_proof_is_complete():
    result = run_evidence_gated_verdict(
        evidence_packet_trace_id="trace-123",
        proof_chips=_complete_chips("verified"),
        explicit_verifier_decision={"verdict": "ACCEPT", "confidence": 0.91},
    )

    assert result.status == "COMPLETE"
    assert result.verdict == "ACCEPT"
    assert result.confidence == 0.91


def test_explicit_accept_is_blocked_when_required_proof_is_missing():
    chips = _complete_chips("verified")
    chips[4] = _chip("output_proof", "unavailable")

    result = run_evidence_gated_verdict(
        evidence_packet_trace_id="trace-123",
        proof_chips=chips,
        explicit_verifier_decision={"verdict": "ACCEPT", "confidence": 0.91},
    )

    assert result.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert result.confidence is None
    assert result.missing_or_unavailable == ("output_proof",)


def test_invalid_explicit_decision_does_not_create_fake_accept():
    result = run_evidence_gated_verdict(
        evidence_packet_trace_id="trace-123",
        proof_chips=_complete_chips("verified"),
        explicit_verifier_decision={"verdict": "ACCEPT", "confidence": "0.91"},
    )

    assert result.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert result.confidence is None
