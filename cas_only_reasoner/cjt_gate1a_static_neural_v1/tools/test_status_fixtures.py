"""test_status_fixtures.py -- self-test of the committed status authority (v3).

Two duties (owner audit 2026-08-31 section 4):
1. BRANCH PROOFS -- every decision branch fires on constructed evidence, and the
   owner's exact counterexample (S0=S1=S2=1.00, S3=0.80, S6=S7=0.70) -- which the
   v2 program wrongly LICENSED -- is a PERMANENT must-not-license fixture.
2. ADVERSARIAL REJECTION PROOFS -- malformed or contradictory evidence raises
   STATUS_INPUT_INVALID instead of producing a status: wrong id count/order,
   missing/extra arms, wrong seed sets, non-binary entries (including booleans
   and floats), wrong vector lengths, unbound passage order, extra fields,
   non-finite claim-A values, missing surface baselines.

Non-neural; permitted in Gate 1A. boot_n=500 here is the documented TEST-ONLY
override (branch logic is boot_n-independent); the CLI always runs the frozen
default 10000.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from emit_gate1_status import LICENSED, StatusInputInvalid, emit  # noqa: E402
from exec.prng import HashPRNG  # noqa: E402

N = 1000
BOOT_N_TEST = 500
IDS = [f"p{i:06d}" for i in range(N)]
ORDER_DIGEST = hashlib.sha256(
    json.dumps(IDS, separators=(",", ":")).encode("utf-8")).hexdigest()


def make_arm(domain, acc):
    rng = HashPRNG(domain)
    return {"per_seed_correct":
            {s: [1 if rng.random() < acc else 0 for _ in range(N)]
             for s in ("11", "23", "47")},
            "passage_order_digest": ORDER_DIGEST}


def make_baseline(overall):
    ok = round(overall * N)
    return {"overall": ok / N, "correct": ok, "total": N,
            "per_question_type": {
                "Q_ATTRACT": {"accuracy": overall, "correct": ok // 3, "total": N // 3},
                "Q_PART": {"accuracy": 0.99, "correct": 165, "total": 166}}}


def fixture(a0=0.60, a1=0.60, a2=0.60, a3=0.85, a4=0.50, a5=0.50,
            a6=0.60, a7=0.60):
    accs = {"S0": a0, "S1": a1, "S2": a2, "S3": a3,
            "S4": a4, "S5": a5, "S6": a6, "S7": a7}
    return {"schema": "RAW_GATE1_RESULTS_v1",
            "protected_passage_ids": list(IDS),
            "arms": {k: make_arm(f"FIX|{k}|{v}", v) for k, v in accs.items()},
            "claim_a": {"probe_protected_accuracy": 0.9,
                        "shuffled_control_accuracy": 0.3},
            "surface_baselines": {
                "train": {"B0": make_baseline(0.62), "B1": make_baseline(1.0)},
                "val": {"B0": make_baseline(0.61), "B1": make_baseline(1.0)},
                "protected": {"B0": make_baseline(0.60), "B1": make_baseline(1.0)}}}


def expect(name, results, want):
    got = emit(results, boot_n=BOOT_N_TEST)["claim_b_status"]
    assert got == want, f"{name}: got {got}, want {want}"
    print(f"PASS {name}: {got}")


def expect_rejected(name, results):
    try:
        emit(results, boot_n=BOOT_N_TEST)
    except StatusInputInvalid as exc:
        assert str(exc).startswith("STATUS_INPUT_INVALID"), str(exc)
        print(f"PASS reject {name}")
        return
    raise AssertionError(f"{name}: malformed evidence was ACCEPTED")


def main():
    # ---- branch proofs -------------------------------------------------------
    expect("licensed_all_seven_controls_beaten", fixture(), LICENSED)
    # THE OWNER'S COUNTEREXAMPLE (audit section 3): v2 licensed this. v3 must not.
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
    # claim A both directions + surface-baseline consumption + determinism
    r = fixture()
    out = emit(r, boot_n=BOOT_N_TEST)
    assert out["claim_a_status"] == "CLAIM_A_LICENSED"
    assert out["task_ceiling_B1_protected"] == 1.0
    assert out["b0_near_ceiling_question_types"] == ["Q_PART"]
    assert "PROHIBITED_ON_THIS_DATASET" in out["cas_specific_language"]
    bad_a = fixture()
    bad_a["claim_a"] = {"probe_protected_accuracy": 0.7,
                        "shuffled_control_accuracy": 0.3}
    assert emit(bad_a, boot_n=BOOT_N_TEST)["claim_a_status"] == "CLAIM_A_NOT_LICENSED"
    assert emit(r, boot_n=BOOT_N_TEST) == emit(r, boot_n=BOOT_N_TEST), \
        "emitter is not deterministic"
    print("PASS claim_a both directions + baselines consumed + deterministic")

    # ---- adversarial rejection proofs ---------------------------------------
    base = fixture()
    m = copy.deepcopy(base); m["protected_passage_ids"] = IDS[:-1]
    expect_rejected("999_ids", m)
    m = copy.deepcopy(base)
    m["protected_passage_ids"][0], m["protected_passage_ids"][1] = \
        m["protected_passage_ids"][1], m["protected_passage_ids"][0]
    expect_rejected("ids_out_of_frozen_order", m)
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

    print("ALL STATUS FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
