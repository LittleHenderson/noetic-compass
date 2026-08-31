"""test_status_fixtures.py -- synthetic-fixture self-test of the committed status
program (non-neural; permitted in Gate 1A). Proves every branch of the decision tree
fires on constructed raw results and that the emitter is deterministic."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emit_gate1_status import emit  # noqa: E402

N = 400   # fixture passage count (smaller than 1000 for speed; law is size-agnostic)


def make_arm(rng, acc):
    return {"per_seed_correct": {s: [1 if rng.random() < acc else 0 for _ in range(N)]
                                 for s in ("11", "23", "47")}}


def fixture(a3, a6, a7, a4=0.50, a5=0.50, base=0.50):
    rng = random.Random(7)
    arms = {k: make_arm(rng, base) for k in ("S0", "S1", "S2")}
    arms["S3"] = make_arm(rng, a3)
    arms["S4"] = make_arm(rng, a4)
    arms["S5"] = make_arm(rng, a5)
    arms["S6"] = make_arm(rng, a6)
    arms["S7"] = make_arm(rng, a7)
    return {"protected_passage_ids": [f"p{i}" for i in range(N)], "arms": arms,
            "claim_a": {"probe_protected_accuracy": 0.9,
                        "shuffled_control_accuracy": 0.3}}


def expect(name, results, want):
    got = emit(results)["claim_b_status"]
    assert got == want, f"{name}: got {got}, want {want}"
    print(f"PASS {name}: {got}")


def main():
    expect("licensed", fixture(a3=0.85, a6=0.60, a7=0.60), "CLAIM_B_LICENSED")
    expect("generic_semantic", fixture(a3=0.85, a6=0.60, a7=0.85),
           "GENERIC_SEMANTIC_STRUCTURE_DETECTED")
    expect("capacity", fixture(a3=0.85, a6=0.85, a7=0.60), "CAPACITY_EFFECT_DETECTED")
    expect("side_channel", fixture(a3=0.85, a6=0.85, a7=0.85, a4=0.60),
           "SIDE_CHANNEL_ONLY")
    expect("not_supported", fixture(a3=0.60, a6=0.60, a7=0.60, a4=0.60, a5=0.60),
           "STATIC_CAS_COUPLING_NOT_SUPPORTED")
    r = fixture(a3=0.85, a6=0.60, a7=0.60)
    assert emit(r) == emit(r), "emitter is not deterministic"
    a = emit(fixture(a3=0.85, a6=0.60, a7=0.60))
    assert a["claim_a_status"] == "CLAIM_A_LICENSED"
    bad = fixture(a3=0.85, a6=0.60, a7=0.60)
    bad["claim_a"] = {"probe_protected_accuracy": 0.7, "shuffled_control_accuracy": 0.3}
    assert emit(bad)["claim_a_status"] == "CLAIM_A_NOT_LICENSED"
    print("PASS claim_a licensing both directions")
    print("ALL STATUS FIXTURES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
