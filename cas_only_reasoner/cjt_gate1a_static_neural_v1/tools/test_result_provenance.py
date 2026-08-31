"""test_result_provenance.py -- the section-10 raw-result provenance attacks.

No well-shaped but unbound result file may receive a scientific status; the
status program validates the evidence chain BEFORE reading any metric.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from emit_gate1_status import EvidenceUnbound, StatusInputInvalid, emit  # noqa: E402
import test_status_fixtures as fx  # noqa: E402


def emit_fix(results):
    return emit(results, boot_n=fx.BOOT_N_TEST, evidence_root=fx._EVIDENCE_ROOT,
                conformance=True)


def expect_unbound(name, results, evidence_root="KEEP"):
    root = fx._EVIDENCE_ROOT if evidence_root == "KEEP" else evidence_root
    try:
        emit(results, boot_n=fx.BOOT_N_TEST, evidence_root=root,
             conformance=True)
    except EvidenceUnbound:
        print(f"PASS {name}")
        return
    raise AssertionError(f"{name}: unbound result received a status")


def main():
    base = fx.fixture()                                   # builds evidence dir

    m = copy.deepcopy(base); del m["evidence_chain"]
    expect_unbound("test_unbound_raw_result_refused(no chain)", m)
    expect_unbound("test_unbound_raw_result_refused(no evidence root)",
                   copy.deepcopy(base), evidence_root=None)

    m = copy.deepcopy(base)
    m["evidence_chain"]["campaign_receipt_sha256"] = "0" * 64
    expect_unbound("test_wrong_campaign_receipt_refused", m)

    m = copy.deepcopy(base)
    m["evidence_chain"]["job_receipt_sha256s"]["S3_seed11"] = "0" * 64
    expect_unbound("wrong_job_receipt_digest_refused", m)
    m = copy.deepcopy(base)
    del m["evidence_chain"]["checkpoint_sha256s"]["S3_seed11"]
    expect_unbound("test_missing_checkpoint_provenance_refused", m)

    m = copy.deepcopy(base)
    m["evidence_chain"]["model_revision_sha"] = "TO_BE_RESOLVED"
    expect_unbound("placeholder_identity_refused", m)

    # fabricated correctness vectors: perfect scores with a broken chain must
    # die on the CHAIN, and with a healthy chain non-binary values die on shape
    m = copy.deepcopy(base)
    for a in m["arms"].values():
        for s in a["per_seed_correct"]:
            a["per_seed_correct"][s] = [1] * fx.N
    m["evidence_chain"]["protected_lock_receipt_sha256"] = "0" * 64
    expect_unbound("test_fabricated_correctness_vectors_refused(chain first)", m)

    m = copy.deepcopy(base)
    m["surface_baselines"]["val"]["B0"]["correct"] = 999   # breaks arithmetic
    try:
        emit_fix(m)
        raise AssertionError("inconsistent arithmetic accepted")
    except StatusInputInvalid:
        print("PASS test_inconsistent_baseline_arithmetic_refused")

    m = copy.deepcopy(base)
    m["protected_passage_ids"] = list(reversed(m["protected_passage_ids"]))
    try:
        emit_fix(m)
        raise AssertionError("wrong passage order accepted")
    except StatusInputInvalid:
        print("PASS test_wrong_passage_order_refused")

    # provenance-before-metrics: BOTH defects present -> the refusal must be
    # the EVIDENCE one, proving no metric was read first
    m = copy.deepcopy(base)
    m["arms"]["S3"]["per_seed_correct"]["11"][0] = 7       # invalid metric
    m["evidence_chain"]["execution_approval_sha256"] = "0" * 64  # unbound
    try:
        emit_fix(m)
        raise AssertionError("emitted despite double defect")
    except EvidenceUnbound:
        print("PASS test_status_program_never_reads_metrics_before_provenance_passes")
    except StatusInputInvalid:
        raise AssertionError("metrics were read before provenance")

    print("ALL RESULT-PROVENANCE ATTACKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
