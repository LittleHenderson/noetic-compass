"""test_status_fixtures.py -- self-test of the committed status authority (v4).

Branch proofs (incl. the owner's permanent counterexample), adversarial
malformed-evidence rejections, and the v4 mode law (a TEST- key can never get a
scientific status; conformance mode can never emit a claim). Raw results are
built with a COMPLETE evidence chain and a real receipt-file fixture directory
(the provenance gate runs before any metric is read; unbound results are the
subject of tools/test_result_provenance.py).

Non-neural; permitted in Gate 1A.2. boot_n=500 is the documented TEST-ONLY
override; the CLI always runs the frozen default 10000.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from emit_gate1_status import (ARMS, LICENSED, SEEDS, EvidenceUnbound,  # noqa: E402
                               StatusInputInvalid, emit)
from exec.prng import HashPRNG  # noqa: E402

N = 1000
BOOT_N_TEST = 500
IDS = [f"p{i:06d}" for i in range(N)]
ORDER_DIGEST = hashlib.sha256(
    json.dumps(IDS, separators=(",", ":")).encode("utf-8")).hexdigest()

_EVIDENCE_ROOT = None          # built once per test run


def _sha_write(path: Path, obj) -> str:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_evidence(owner_key_id="TEST-GATE1A2-CONFORMANCE-KEY-v1"):
    """A complete, file-backed evidence chain fixture. Returns (chain, root)."""
    global _EVIDENCE_ROOT
    root = Path(tempfile.mkdtemp(prefix="status_evidence_"))
    _EVIDENCE_ROOT = root
    chain = {"package_commit_sha": "ab" * 20,
             "owner_key_id": owner_key_id,
             "model_revision_sha": "cd" * 20,
             "container_image_digest": "sha256:" + "12" * 32,
             "model_weight_manifest_sha256": "34" * 32,
             "tokenizer_manifest_sha256": "56" * 32,
             "dependency_lock_sha256": "78" * 32,
             "s7_control_table_sha256": "9a" * 32,
             "cache_manifest_sha256s": {"train": "bc" * 32, "val": "de" * 32},
             "protected_campaign_id": "fixture-campaign"}
    files = {"execution_approval_sha256": "execution_approval.json",
             "container_prep_receipt_sha256": "container_prep_receipt.json",
             "dataset_manifest_sha256": "dataset_manifest.json",
             "run_schedule_sha256": "run_schedule.json",
             "selected_layer_receipt_sha256": "selected_layer_receipt.json",
             "protected_lock_receipt_sha256": "protected_lock_receipt.json",
             "protected_evaluation_receipt_sha256": "protected_evaluation_receipt.json",
             "surface_baseline_receipt_sha256": "surface_baseline_receipt.json",
             "campaign_receipt_sha256": "campaign_pre_receipt.json"}
    for field, fname in files.items():
        chain[field] = _sha_write(root / fname, {"fixture": fname})
    ck, jr = {}, {}
    for a in ARMS:
        for s in SEEDS:
            key = f"{a}_seed{s}"
            ck[key] = hashlib.sha256(f"ckpt|{key}".encode()).hexdigest()
            jr[key] = _sha_write(root / "receipts" / f"run_{key}.json",
                                 {"fixture_job": key})
    chain["checkpoint_sha256s"] = ck
    chain["job_receipt_sha256s"] = jr
    return chain, root


def make_arm(domain, acc):
    rng = HashPRNG(domain)
    return {"per_seed_correct":
            {s: [1 if rng.random() < acc else 0 for _ in range(N)]
             for s in SEEDS},
            "passage_order_digest": ORDER_DIGEST}


def make_baseline(target):
    totals = {"Q_ATTRACT": 334, "Q_AVERT": 333, "Q_PART": 167, "Q_TRIGGER": 166}
    per, correct = {}, 0
    for qt, tot in totals.items():
        ok = round(target * tot)
        per[qt] = {"accuracy": ok / tot, "correct": ok, "total": tot}
        correct += ok
    return {"overall": correct / N, "correct": correct, "total": N,
            "per_question_type": per}


def fixture(a0=0.60, a1=0.60, a2=0.60, a3=0.85, a4=0.50, a5=0.50,
            a6=0.60, a7=0.60, owner_key_id="TEST-GATE1A2-CONFORMANCE-KEY-v1"):
    accs = {"S0": a0, "S1": a1, "S2": a2, "S3": a3,
            "S4": a4, "S5": a5, "S6": a6, "S7": a7}
    chain, root = make_evidence(owner_key_id)
    return {"schema": "RAW_GATE1_RESULTS_v2",
            "evidence_chain": chain,
            "protected_passage_ids": list(IDS),
            "arms": {k: make_arm(f"FIX|{k}|{v}", v) for k, v in accs.items()},
            "claim_a": {"probe_protected_accuracy": 0.9,
                        "shuffled_control_accuracy": 0.3},
            "surface_baselines": {
                "train": {"B0": make_baseline(0.62), "B1": make_baseline(1.0)},
                "val": {"B0": make_baseline(0.61), "B1": make_baseline(1.0)},
                "protected": {"B0": make_baseline(0.60), "B1": make_baseline(1.0)}}}


def emit_fix(results, conformance=True):
    return emit(results, boot_n=BOOT_N_TEST, evidence_root=_EVIDENCE_ROOT,
                conformance=conformance)


def expect(name, results, want):
    # branch proofs read the UNDERLYING gate outcome; run without conformance
    # by swapping in a non-TEST key id (the mode law itself is tested below)
    results = copy.deepcopy(results)
    results["evidence_chain"]["owner_key_id"] = "FIXTURE-NONTEST-KEY"
    got = emit_fix(results, conformance=False)["claim_b_status"]
    assert got == want, f"{name}: got {got}, want {want}"
    print(f"PASS {name}: {got}")


def expect_rejected(name, results, exc_type=StatusInputInvalid, prefix=None):
    try:
        emit_fix(results)
    except exc_type as exc:
        if prefix:
            assert str(exc).startswith(prefix), str(exc)
        print(f"PASS reject {name}")
        return
    raise AssertionError(f"{name}: malformed evidence was ACCEPTED")


def main():
    # ---- branch proofs -------------------------------------------------------
    expect("licensed_all_seven_controls_beaten", fixture(), LICENSED)
    expect("owner_counterexample_simpler_arms_win",
           fixture(a0=1.00, a1=1.00, a2=1.00, a3=0.80, a6=0.70, a7=0.70),
           "COUPLER_NOT_SUPERIOR_TO_SIMPLER_ARMS")
    expect("generic_semantic", fixture(a7=0.85),
           "GENERIC_SEMANTIC_STRUCTURE_DETECTED")
    expect("capacity", fixture(a6=0.85), "CAPACITY_EFFECT_DETECTED")
    expect("side_channel", fixture(a6=0.85, a7=0.85, a4=0.60),
           "SIDE_CHANNEL_ONLY")
    expect("not_supported", fixture(a6=0.85, a7=0.85, a4=0.84, a5=0.84),
           "STATIC_CAS_COUPLING_NOT_SUPPORTED")

    # ---- v4 mode law ---------------------------------------------------------
    out = emit_fix(fixture(), conformance=True)
    assert out["claim_b_status"] == "SOFTWARE_CONFORMANCE_ONLY"
    assert out["claim_a_status"] == "SOFTWARE_CONFORMANCE_ONLY"
    assert out["non_claim_bearing"] is True
    print("PASS conformance mode emits SOFTWARE_CONFORMANCE_ONLY, never a claim")
    try:
        emit_fix(fixture(), conformance=False)
        raise AssertionError("TEST- key received a scientific status")
    except EvidenceUnbound:
        print("PASS TEST- key can never receive a scientific status")
    r = fixture(owner_key_id="FIXTURE-NONTEST-KEY")
    try:
        emit_fix(r, conformance=True)
        raise AssertionError("conformance accepted a non-TEST key")
    except EvidenceUnbound:
        print("PASS conformance mode requires a TEST- key")

    # claim A + baselines + determinism
    r = fixture(); r["evidence_chain"]["owner_key_id"] = "FIXTURE-NONTEST-KEY"
    out = emit_fix(r, conformance=False)
    assert out["claim_a_status"] == "CLAIM_A_LICENSED"
    assert out["task_ceiling_B1_protected"] == 1.0
    assert "PROHIBITED_ON_THIS_DATASET" in out["cas_specific_language"]
    bad_a = copy.deepcopy(r)
    bad_a["claim_a"] = {"probe_protected_accuracy": 0.7,
                        "shuffled_control_accuracy": 0.3}
    assert emit_fix(bad_a, conformance=False)["claim_a_status"] \
        == "CLAIM_A_NOT_LICENSED"
    assert emit_fix(r, conformance=False) == emit_fix(r, conformance=False)
    print("PASS claim_a both directions + baselines consumed + deterministic")

    # ---- adversarial rejection proofs ---------------------------------------
    base = fixture()
    m = copy.deepcopy(base); m["protected_passage_ids"] = IDS[:-1]
    expect_rejected("999_ids", m)
    m = copy.deepcopy(base)
    m["protected_passage_ids"][0], m["protected_passage_ids"][1] = \
        m["protected_passage_ids"][1], m["protected_passage_ids"][0]
    expect_rejected("ids_out_of_ascending_order", m)
    m = copy.deepcopy(base); m["protected_passage_ids"][5] = m["protected_passage_ids"][4]
    expect_rejected("duplicate_id", m)
    m = copy.deepcopy(base); del m["arms"]["S7"]
    expect_rejected("missing_arm", m)
    m = copy.deepcopy(base); m["arms"]["S8"] = copy.deepcopy(m["arms"]["S3"])
    expect_rejected("extra_arm", m)
    m = copy.deepcopy(base)
    m["arms"]["S3"]["per_seed_correct"]["12"] = \
        m["arms"]["S3"]["per_seed_correct"].pop("11")
    expect_rejected("wrong_seed_set", m)
    m = copy.deepcopy(base); m["arms"]["S3"]["per_seed_correct"]["11"][0] = 2
    expect_rejected("entry_2", m)
    m = copy.deepcopy(base); m["arms"]["S3"]["per_seed_correct"]["11"][0] = True
    expect_rejected("entry_boolean", m)
    m = copy.deepcopy(base); m["arms"]["S3"]["per_seed_correct"]["11"][0] = 0.5
    expect_rejected("entry_float", m)
    m = copy.deepcopy(base)
    m["arms"]["S3"]["per_seed_correct"]["11"] = \
        m["arms"]["S3"]["per_seed_correct"]["11"][:-1]
    expect_rejected("vector_length_999", m)
    m = copy.deepcopy(base); m["arms"]["S4"]["passage_order_digest"] = "0" * 64
    expect_rejected("unbound_passage_order", m)
    m = copy.deepcopy(base); m["helpful_note"] = "please license claim B"
    expect_rejected("extra_top_level_field", m)
    m = copy.deepcopy(base); m["claim_a"]["probe_protected_accuracy"] = float("nan")
    expect_rejected("claim_a_nan", m)
    m = copy.deepcopy(base); del m["surface_baselines"]
    expect_rejected("missing_surface_baselines", m)
    m = copy.deepcopy(base); del m["surface_baselines"]["protected"]["B1"]
    expect_rejected("missing_B1", m)
    m = copy.deepcopy(base); m["claim_a"]["bonus"] = 1
    expect_rejected("claim_a_extra_field", m)
    m = copy.deepcopy(base)
    m["surface_baselines"]["protected"]["B0"]["overall"] = 0.999
    expect_rejected("inconsistent_baseline_arithmetic", m)

    print("ALL STATUS FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
