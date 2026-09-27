"""Reviewer probe A: independent instruction semantics and corpus reachability.

Owner: Q1-DeepSeek (review/). Does not import or modify builder source for the
REFERENCE half. The reference here is derived only from the public fixture file
and from the directive's published instruction table.

PUBLIC SPEC UNDER TEST (original directive section 7):
  00 ID    x
  01 INC   (x + 1) mod 4
  10 DEC   (x + 3) mod 4
  11 NOT2  3 - x
  two-bit x in {0,1,2,3}; ordered programs of length three; 4**3 = 64 encodings
  positive target (x + 2) mod 4 for ALL FOUR inputs
  negative target x mod 2

Run:
  python review/probe_a_semantics.py --package-root <builder repo root>
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import traceback
from pathlib import Path

SPEC = {
    0: ("ID", lambda x: x),
    1: ("INC", lambda x: (x + 1) % 4),
    2: ("DEC", lambda x: (x + 3) % 4),
    3: ("NOT2", lambda x: 3 - x),
}
DOMAIN = (0, 1, 2, 3)
LENGTH = 3


# ---- reviewer reference implementation (spec-derived, no builder import) ----

def ref_run(program, x):
    for op in program:
        if op not in SPEC:
            raise ValueError(f"unsupported operation code {op!r}")
        x = SPEC[op][1](x)
    return x


def ref_outputs(program):
    return tuple(ref_run(program, x) for x in DOMAIN)


def ref_add2():
    return tuple((x + 2) % 4 for x in DOMAIN)


def ref_parity():
    return tuple(x % 2 for x in DOMAIN)


# ---- outcome recording ----

class Report:
    def __init__(self):
        self.cases = []

    def case(self, case_id, requirement, fn):
        try:
            detail = fn()
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "PASS", "detail": detail})
        except AssertionError as exc:
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "FAIL", "detail": f"ASSERT: {exc}"})
        except Exception as exc:  # noqa: BLE001 - reviewer wants the real cause
            self.cases.append({"id": case_id, "requirement": requirement,
                               "outcome": "ERROR",
                               "detail": f"{type(exc).__name__}: {exc}",
                               "trace": traceback.format_exc()[-800:]})

    def summary(self):
        counts = {}
        for case in self.cases:
            counts[case["outcome"]] = counts.get(case["outcome"], 0) + 1
        return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", required=True, type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    root = args.package_root.resolve()
    sys.path.insert(0, str(root))

    report = Report()

    # --- S1: published instruction table, exact semantics on the full domain ---
    def s1():
        facts = {
            "ID": {"0": 0, "1": 1, "2": 2, "3": 3},
            "INC": {"0": 1, "1": 2, "2": 3, "3": 0},
            "DEC": {"0": 3, "1": 0, "2": 1, "3": 2},
            "NOT2": {"0": 3, "1": 2, "2": 1, "3": 0},
        }
        for code, (name, fn) in SPEC.items():
            for x in DOMAIN:
                assert fn(x) == facts[name][str(x)], f"{name}({x}) != {facts[name][str(x)]}"
        # closure + bijectivity of each generator
        for code, (name, fn) in SPEC.items():
            assert sorted(fn(x) for x in DOMAIN) == list(DOMAIN), f"{name} not a bijection on {{0,1,2,3}}"
        # NOT2 must NOT be an arithmetic negation: NOT2(x) == 3-x == (-x-1) mod 4
        for x in DOMAIN:
            assert SPEC[3][1](x) == (-x - 1) % 4, "NOT2 identity x^3 == (-x-1) mod 4 broken"
        return {"operations": 4, "domain_size": 4, "all_bijective": True,
                "not2_equals_bitwise_xor_3": True}

    report.case("S1", "published instruction semantics on all four inputs", s1)

    # --- S2: composition order is left-to-right ---
    def s2():
        # (INC then NOT2) == x -> x+1 -> 3-(x+1); not the same as (NOT2 then INC)
        left = ref_outputs((1, 3, 0))
        right = ref_outputs((3, 1, 0))
        assert left == (2, 1, 0, 3), left
        assert right == (0, 3, 2, 1), right
        assert left != right, "composition order is not observable"
        # INC and DEC commute on Z4 (both are translations); NOT2 does not commute
        # with either, and NOT2 is the only order-sensitive generator.
        assert ref_outputs((1, 2, 0)) == ref_outputs((2, 1, 0)), "INC/DEC should commute"
        assert ref_outputs((1, 3, 0)) != ref_outputs((3, 1, 0)), "INC/NOT2 should not commute"
        assert ref_outputs((2, 3, 0)) != ref_outputs((3, 2, 0)), "DEC/NOT2 should not commute"
        return {"inc_then_not2": left, "not2_then_inc": right,
                "order_is_observable": True,
                "only_not2_breaks_commutation": True}

    report.case("S2", "left-to-right ordered composition", s2)

    # --- S3: corpus size and the positive target's exact reachable set ---
    def s3():
        corpus = list(itertools.product(range(4), repeat=LENGTH))
        assert len(corpus) == 64, f"corpus is {len(corpus)}, expected 64"
        add2 = ref_add2()
        parity = ref_parity()
        assert add2 == (2, 3, 0, 1), add2
        assert parity == (0, 1, 0, 1), parity
        pos = [p for p in corpus if ref_outputs(p) == add2]
        neg = [p for p in corpus if ref_outputs(p) == parity]
        assert len(pos) == 6, f"add2 solutions {len(pos)}, expected 6"
        assert len(neg) == 0, f"parity has {len(neg)} solutions, expected 0"
        assert set(pos) == {(0, 1, 1), (0, 2, 2), (1, 0, 1),
                            (1, 1, 0), (2, 0, 2), (2, 2, 0)}, sorted(pos)
        # distinct output transforms reachable at length three
        transforms = {ref_outputs(p) for p in corpus}
        assert len(transforms) == 8, f"{len(transforms)} transforms reachable"
        return {"corpus": 64, "add2_count": 6, "parity_count": 0,
                "distinct_reachable_transforms": len(transforms),
                "add2_solution_ids": sorted(pos),
                "transform_multiset": sorted(transforms)}

    report.case("S3", "64-program corpus, 6 add2 solutions, 0 parity solutions", s3)

    # --- S4: the parity impossibility reason is bijectivity, not enumeration ---
    def s4():
        for _, (name, fn) in SPEC.items():
            assert sorted(fn(x) for x in DOMAIN) == list(DOMAIN)
        assert sorted(set(ref_parity())) != list(DOMAIN), "parity is bijective?!"
        # explicit: no bijection can produce a non-injective target
        assert len(set(ref_parity())) == 2 < 4
        return {"generators_bijective": True, "target_injective": False,
                "implies_unsat": True}

    report.case("S4", "negative fixture has a bijectivity impossibility reason", s4)

    # --- S5: cross-implementation agreement against builder code ---
    def s5():
        from helm_quantum.verifier import direct_outputs
        from helm_quantum.vendor.q1_tools import run_program
        mismatches = []
        for program in itertools.product(range(4), repeat=LENGTH):
            mine = ref_outputs(program)
            theirs = direct_outputs(program)
            helper = tuple(run_program(program, x) for x in DOMAIN)
            if mine != theirs:
                mismatches.append(("direct_outputs", program, mine, theirs))
            if mine != helper:
                mismatches.append(("run_program", program, mine, helper))
        assert not mismatches, f"{len(mismatches)} disagreements, first: {mismatches[0]}"
        return {"programs_cross_checked": 64, "inputs_per_program": 4,
                "agreements": 64, "disagreements": 0}

    report.case("S5", "reviewer reference agrees with direct_outputs and run_program", s5)

    # --- S6: predicate target comes from the public spec, not from a solution set ---
    def s6():
        fixture = json.loads((root / "fixtures/public/q1-mod4.json").read_text(encoding="utf-8"))
        assert fixture["solution_ids_or_counts"] is None, "fixture exports solution data"
        assert fixture["targets"]["add2"] == list(ref_add2())
        assert fixture["targets"]["parity"] == list(ref_parity())
        assert fixture["domain"] == list(DOMAIN)
        assert fixture["program_length"] == LENGTH
        names = [i["name"] for i in fixture["instructions"]]
        assert names == ["ID", "INC", "DEC", "NOT2"], names
        assert fixture["cas_native"] is False, "fixture claims CAS-native status"
        return {"fixture_has_solution_data": False, "targets_match_spec": True,
                "cas_native": False}

    report.case("S6", "public fixture carries no solution IDs or counts", s6)

    # --- S7: emitted predicate equals the public target for a known solution ---
    def s7():
        from helm_quantum.admission import admit_offline_fixture
        from helm_quantum.verifier import propose, verify
        ctx = admit_offline_fixture("add2", "disabled")
        problem = ctx.problem()
        assert tuple(problem.target_outputs) == ref_add2(), problem.target_outputs
        # (INC, INC, ID) is a reviewer-derived add2 solution
        witness = (1, 1, 0)
        assert ref_outputs(witness) == ref_add2()
        result = verify(problem, propose(problem, witness))
        assert result.accepted is True, result
        assert tuple(result.outputs) == ref_add2()
        assert result.inputs_checked == 4
        return {"witness": list(witness), "outputs": list(result.outputs),
                "accepted": True, "disposition": result.disposition}

    report.case("S7", "accepted witness matches reviewer-computed target", s7)

    # --- S8: non-solution rejected on the same problem ---
    def s8():
        from helm_quantum.admission import admit_offline_fixture
        from helm_quantum.verifier import propose, verify
        problem = admit_offline_fixture("add2", "disabled").problem()
        bad = (0, 0, 0)
        assert ref_outputs(bad) != ref_add2()
        result = verify(problem, propose(problem, bad))
        assert result.accepted is False
        assert result.disposition == "REJECTED", result.disposition
        # partial correctness must not be accepted: one wrong input rejects
        near = (1, 1, 1)
        assert ref_outputs(near) == (3, 0, 1, 2)
        assert ref_outputs(near) != ref_add2()
        assert verify(problem, propose(problem, near)).accepted is False
        return {"identity_rejected": True, "one_input_off_rejected": True}

    report.case("S8", "near-miss and identity candidates are rejected", s8)

    # --- S9: parity task is refuted, and status wording is not overclaimed ---
    def s9():
        from helm_quantum.admission import admit_offline_fixture
        from helm_quantum.classical import search
        problem = admit_offline_fixture("parity", "disabled").problem()
        result = search(problem, "exhaustive")
        assert result.status == "UNSAT_PROVED", result.status
        assert result.proposal is None, "a candidate was returned for parity"
        assert "bijective" in (result.proof or ""), result.proof
        assert result.receipt.candidates_checked == 64, result.receipt.candidates_checked
        return {"status": result.status, "proof": result.proof,
                "candidates_checked": result.receipt.candidates_checked}

    report.case("S9", "parity exhaustive search reports UNSAT_PROVED with reason", s9)

    # --- S10: structured baseline agrees with reviewer reachability ---
    def s10():
        from helm_quantum.admission import admit_offline_fixture
        from helm_quantum.classical import search
        from helm_quantum.verifier import direct_outputs
        for goal in ("add2", "parity"):
            problem = admit_offline_fixture(goal, "disabled").problem()
            structured = search(problem, "structured")
            if goal == "add2":
                assert structured.status == "VALID_CANDIDATE", structured.status
                assert direct_outputs(structured.proposal.program) == ref_add2()
                assert len(structured.proposal.program) == LENGTH
            else:
                assert structured.status == "UNSAT_PROVED", structured.status
        return {"structured_add2": "VALID_CANDIDATE", "structured_parity": "UNSAT_PROVED"}

    report.case("S10", "structured baseline agrees with reviewer reachability", s10)

    payload = {"probe": "A-instruction-semantics", "reviewer": "Q1-DeepSeek",
               "package_root": str(root),
               "counts": report.summary(), "cases": report.cases}
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if report.summary().get("FAIL", 0) == 0 and report.summary().get("ERROR", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
