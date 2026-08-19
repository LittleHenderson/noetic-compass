"""
scratch_rpm_compiler_demo.py
============================================================================
Owner's claim under test:
    "RPM's D/W/P stages can each be translated into CAS notation, tested by
     the CAS compiler, and CORRECTED or INVERTED on any of its axes."

This script proves the SYMBOLIC / COMPILER portion of that claim end to end,
using ONLY real repository APIs (no stub of the compiler or the inversion
detector). Every call is annotated with file:symbol.

Pipeline demonstrated for the F5 (Agency) pathway A0 -> D5 -> W5 -> P5:
  (1) EXPRESS  the RPM chain + its D/W/P stages as CAS notation strings
  (2) COMPILE  them via the real compiler and show the structured result
  (3) INJECT   an inversion on a NAMED axis:
                 - axis A (RPM chain / pathway violation)   [numeric]
                 - axis N (Noetic involution imbalance)     [symbolic]
  (4) DETECT   the inversion via the real inversion APIs and print the axis
  (5) CORRECT  it back and show the corrected form now passes; note the
                 recursive-propagation property.

Real modules used (all imported, none stubbed):
  api.notation.compiler          (compile_expression, CompilationArtifact)
  api.notation.inversion         (invert_expression, IMPLEMENTED/DEFERRED axes)
  belief.inversion_gate          (run_inversion_scan, axis_a_check)  [cas-native]
  cas_engine                     (InversionScanner, CognitiveStateVector) [Rust PyO3]
"""

from __future__ import annotations

import json
import os
import sys

# Windows consoles default to cp1252; CAS notation prints Unicode (arrows, etc.).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------
# sys.path wiring — mirror how tests import the package.
# tests/test_notation_compiler.py does `from api.notation.compiler import ...`
# with the repo root (this file's directory) on sys.path. The belief detector
# lives under the sibling `cas-native/` source root, imported as `belief.*`.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_CAS_NATIVE = os.path.join(_REPO_ROOT, "cas-native")
for _p in (_REPO_ROOT, _CAS_NATIVE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --- REAL compiler -----------------------------------------------------------
from api.notation.compiler import compile_expression  # file: api/notation/compiler.py

# --- REAL string-level inversion transform/corrector -------------------------
from api.notation.inversion import (  # file: api/notation/inversion.py
    invert_expression,
    IMPLEMENTED_AXES,
    DEFERRED_AXES,
    AXIS_DESCRIPTIONS,
    DeferredAxisError,
)

# --- REAL pure-Python string/boolean 7-axis detector (cas-native) ------------
from belief.inversion_gate import (  # file: cas-native/belief/inversion_gate.py
    run_inversion_scan,
    axis_a_check,
)

# --- REAL numeric 7-axis detector (Rust PyO3 cas_engine) ---------------------
import cas_engine  # InversionScanner, CognitiveStateVector


SEP = "=" * 76


def _hr(title: str) -> None:
    print("\n" + SEP)
    print(title)
    print(SEP)


def _rj(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


# The 7 numeric inversion axes are indexed N,W,F,E,S,A,P (InversionAxis::index()
# in cas-engine/src/ontology/pathways.rs). Axis A (Pathway/RPM) is index 5.
AXIS_ORDER = ["N", "W", "F", "E", "S", "A", "P"]
AXIS_A_INDEX = AXIS_ORDER.index("A")  # == 5


def step1_express_and_compile():
    _hr("STEP 1+2 — EXPRESS the F5/Agency RPM chain + D/W/P stages, then COMPILE")
    print(
        "Owner claim part 1: 'RPM's D/W/P stages can each be translated into CAS\n"
        "notation and tested by the CAS compiler.'\n"
    )

    # (a) The compiler-native pathway construct. RPM(F5) is the ONLY first-class
    #     pathway token in the grammar; it emits the derived A0->D5->W5->P5 chain.
    #     (api/notation/compiler.py : compile_expression / RpmValue)
    rpm_src = "RPM(F5)"
    art = compile_expression(rpm_src)  # api/notation/compiler.py:compile_expression
    print(f"[compile] {rpm_src!r}")
    print(f"          valid={art.valid}  engine={art.engine}")
    print("          result =", _rj(art.to_dict()["result"]))

    # (b) The individual D / W / P stages of the F5 pathway, each translated into
    #     a *compilable* CAS state literal carrying drive F5, one per Processing
    #     Domain descent tier. These are the "D/W/P stages ... translated into
    #     CAS notation" that the compiler actually type-checks.
    #     NOTE (honest): A0/D5/W5/P5 pathway NODE tokens are NOT lexable inputs
    #     (they error as undefined variables); the stage semantics are therefore
    #     carried by drive-tagged state literals + the RPM(F5) call above.
    stage_exprs = {
        "D5 stage (Desire  / drive F5 in Cognitive domain)": "^2^C_{F5}",
        "W5 stage (Wisdom  / drive F5 in Evaluative domain)": "^6^E_{F5}",
        "P5 stage (Power   / drive F5 in Operational domain)": "^9^O_{F5}",
    }
    print()
    for label, src in stage_exprs.items():
        a = compile_expression(src)
        res = a.to_dict()["result"]
        dom = res.get("dominant_state")
        print(f"[compile] {src:<12} -> valid={a.valid}  dominant_state={dom}  ({label})")

    # (c) The D->W->P descent as compiled binary transitions. NOTE (honest):
    #     the typechecker rejects a chained A->B->C ('ARROW requires state-typed
    #     operands') — arrows are strictly BINARY — so the descent is expressed
    #     as two admissible binary transitions D5->W5 and W5->P5.
    transitions = ["^2^C_{F5} -> ^6^E_{F5}", "^6^E_{F5} -> ^9^O_{F5}"]
    print()
    for t in transitions:
        at = compile_expression(t)
        rt = at.to_dict()["result"]
        print(f"[compile] transition {t!r} -> valid={at.valid} "
              f"kind={rt.get('kind') if rt else None} "
              f"descent_ok={rt.get('domain_descent_ok') if rt else None}")
        assert at.valid, f"transition {t} must compile"
    assert art.valid, "baseline RPM compile must succeed"
    return transitions[0]


def step3_4_axis_A(chain_src: str):
    _hr("STEP 3+4 (axis A) — INJECT an RPM-chain violation and DETECT it")
    print(
        "Axis A = Pathway / RPM-chain violation: a downstream stage is stronger\n"
        "than an UNSATISFIED upstream prerequisite (section-retraction broken).\n"
    )

    scanner = cas_engine.InversionScanner()  # cas_engine (Rust PyO3)
    ops = [0.8] * 10
    drives = [0.8] * 7
    sv = cas_engine.CognitiveStateVector([1.0 / 40] * 40)
    doms = [0.8, 0.8, 0.8, 0.8]
    dds = [[0.8] * 4 for _ in range(7)]

    # Baseline: every pathway chain [A0, D, W, P] well-ordered.
    balanced_paths = [[0.8, 0.8, 0.8, 0.8] for _ in range(7)]
    base = dict(scanner.scan(ops, drives, sv, doms, dds, balanced_paths))
    base_A = base["axis_scores"][AXIS_A_INDEX]  # resistance = 1 - severity
    print(f"[detect A] baseline  axis-A resistance = {base_A:.4f}  (severity {1-base_A:.4f})")

    # Inject: on the F5/Agency chain (drive index 4), A0 & D5 & W5 unsatisfied
    # (<0.5) yet P5 = 0.9 towers over them -> a genuine A-axis pathway inversion.
    bad_paths = [[0.8, 0.8, 0.8, 0.8] for _ in range(7)]
    bad_paths[4] = [0.20, 0.10, 0.10, 0.90]  # [A0, D5, W5, P5] broken
    bad = dict(scanner.scan(ops, drives, sv, doms, dds, bad_paths))
    bad_A = bad["axis_scores"][AXIS_A_INDEX]
    sev = 1 - bad_A
    print(f"[detect A] injected  axis-A resistance = {bad_A:.4f}  (severity {sev:.4f})")
    fired = sev > 1e-9
    print(f"[detect A] >>> AXIS THAT FIRED: {'A (Pathway/RPM chain)' if fired else 'none'}")
    print(f"           severity {sev:.4f} ~= 1/7 (one of seven drive chains violated)")

    # Cross-check with the pure-Python belief gate axis-A detector, which keys
    # off whether the RPM gate cleared. (cas-native/belief/inversion_gate.py)
    scan = run_inversion_scan("^2^C_{F5} -> ^9^O_{F5}", rpm_satisfied=False)
    print(f"[detect A] belief-gate axis_a_check -> clean={scan.axes['A']['clean']} "
          f"reason={scan.axes['A']['reason']!r}")
    assert fired and scan.axes["A"]["clean"] is False
    return scanner, ops, drives, sv, doms, dds, bad_paths


def step5_correct_axis_A(scanner, ops, drives, sv, doms, dds, bad_paths):
    _hr("STEP 5 (axis A) — CORRECT the pathway violation; note recursive propagation")
    print(
        "Axis A has NO string-level corrector (invert_expression('...','A') raises\n"
        "DeferredAxisError). Correction is the RPM engine's recursive-descent solver\n"
        "(cas-engine/src/rpm/recursive.rs::evaluate_recursive): close the blocked\n"
        "upstream node so the prerequisite GATE re-opens for the node above it.\n"
        "Here we realize that correction on the numeric plane and re-scan.\n"
    )
    # Correct the F5 chain: satisfy A0/D5/W5 so the downstream P5 no longer
    # violates an unsatisfied prerequisite. This mirrors "a solve at a lower
    # node re-opens the gate above" (recursive.rs resolved/blocked flag).
    fixed_paths = [row[:] for row in bad_paths]
    fixed_paths[4] = [0.85, 0.80, 0.75, 0.90]  # A0>=D5>=W5 satisfied, order restored
    fixed = dict(scanner.scan(ops, drives, sv, doms, dds, fixed_paths))
    fixed_A = fixed["axis_scores"][AXIS_A_INDEX]
    print(f"[correct A] corrected axis-A resistance = {fixed_A:.4f}  (severity {1-fixed_A:.4f})")
    print(f"[correct A] >>> axis A restored to clean: {abs(fixed_A - 1.0) < 1e-9}")
    print("[correct A] recursive property (cas-engine/src/rpm/recursive.rs): closing\n"
          "            D5/W5 flips their blocked->resolved flag, which re-opens the\n"
          "            prerequisite gate for P5 at the same level -> a fix found by\n"
          "            'going deeper' propagates UP the chain. (Rust-internal; not\n"
          "            re-executed here — exercised by that module's own tests.)")
    assert abs(fixed_A - 1.0) < 1e-9


def step3_4_5_axis_N():
    _hr("STEP 3+4+5 (axis N) — INJECT a Noetic involution imbalance, DETECT, CORRECT")
    print(
        "Axis N = involution imbalance across pairs CO-2<->CO-3, CO-5<->CO-6,\n"
        "CO-8<->CO-9. Unlike axis A, N is a token swap, so it is fully correctable\n"
        "by the real string inverter (an involution: re-applying restores it).\n"
    )

    # Start from a well-formed F5 Desire-stage literal: Positive (CO-2).
    good = "^2^P_{F5}"
    a_good = compile_expression(good)
    print(f"[compile] baseline {good!r} valid={a_good.valid}")

    # INJECT the inversion on axis N with the REAL transform (Positive->Negative).
    inj = invert_expression(good, "N")  # api/notation/inversion.py:invert_expression
    print(f"[inject N] invert_expression({good!r},'N') -> {inj.inverted!r} "
          f"valid={inj.valid}")

    # DETECT: present the state co-present with its shadow, no +/x integrator ->
    # the belief-gate N detector flags the unintegrated involution pair.
    drifted = f"{good} {inj.inverted}"       # "^2^P_{F5} ^3^P_{F5}"
    scan = run_inversion_scan(drifted)       # cas-native/belief/inversion_gate.py
    n_axis = scan.axes["N"]
    print(f"[detect N] run_inversion_scan({drifted!r})")
    print(f"[detect N] scan.clean={scan.clean}  N.clean={n_axis['clean']}  "
          f"flagged_pairs={n_axis.get('flagged_pairs')}")
    print(f"[detect N] >>> AXIS THAT FIRED: "
          f"{'N (Noetic involution)' if not n_axis['clean'] else 'none'}")

    # CORRECT: re-apply the same axis to the inverted token — involution restores
    # the admissible original, re-compiled by the real compiler.
    back = invert_expression(inj.inverted, "N")
    a_back = compile_expression(back.inverted)
    print(f"[correct N] invert_expression({inj.inverted!r},'N') -> {back.inverted!r}")
    print(f"[correct N] restored == original: {back.inverted == good}  "
          f"re-compiles valid={a_back.valid}")
    assert not n_axis["clean"]
    assert back.inverted == good and a_back.valid


def step_axis_catalogue():
    _hr("AXIS CATALOGUE — which axes have a real string corrector vs are deferred")
    print(f"IMPLEMENTED (string corrector exists): {IMPLEMENTED_AXES}")
    print(f"DEFERRED   (no string corrector):      {DEFERRED_AXES}")
    for ax in DEFERRED_AXES:
        try:
            invert_expression("^2^P_{F5}", ax)
            print(f"  axis {ax}: UNEXPECTED — did not raise")
        except DeferredAxisError as e:
            print(f"  axis {ax}: DeferredAxisError (correct-back not available)  "
                  f"-> {AXIS_DESCRIPTIONS.get(ax, '')[:48]}")


def main() -> int:
    _hr("CAS RPM -> COMPILER -> INVERSION (detect) -> CORRECTION — REAL-API DEMO")
    print("Repo root on sys.path:", _REPO_ROOT)
    chain_src = step1_express_and_compile()
    ctx = step3_4_axis_A(chain_src)
    step5_correct_axis_A(*ctx)
    step3_4_5_axis_N()
    step_axis_catalogue()
    _hr("RESULT")
    print("PROVEN (symbolic/compiler plane):")
    print("  * D/W/P stages of the F5 pathway compile as CAS notation (RPM(F5) +")
    print("    drive-tagged state literals + a D->W->P transition chain).")
    print("  * A NAMED-axis inversion is INJECTED and DETECTED by real detectors:")
    print("      - axis A (RPM/pathway) via cas_engine.InversionScanner + belief gate")
    print("      - axis N (involution)  via belief run_inversion_scan")
    print("  * CORRECTION shown for both: axis N by the involutive string inverter;")
    print("    axis A on the numeric plane (recursive-gate story is Rust-internal).")
    print("\nALL COMPILER + INVERSION CALLS HIT REAL MODULES (none stubbed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
