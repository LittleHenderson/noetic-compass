"""PCBA compiler-enforced safety negative-evaluation tests."""

from cas_forex.pcba_safety import run_pcba_negative_safety_eval


def test_pcba_negative_safety_eval_passes_and_anchors_evidence(tmp_path):
    report = run_pcba_negative_safety_eval(tmp_path / "pcba_safety.jsonl")

    assert report.formal_pcba_safety_semantics
    assert report.negative_safety_eval_pass
    assert report.evidence_anchor_pass
    assert report.failure_reasons == []
    assert {case.case_id for case in report.cases} >= {
        "invalid_threshold_rejected",
        "invalid_embedded_cas_rejected",
        "shorthand_not_production",
        "diagnostic_accept_blocked",
        "broker_accept_non_licensable",
    }
