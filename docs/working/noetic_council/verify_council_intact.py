"""Is the council mechanism intact? Re-runnable, with no network and no torch.

WHY THIS EXISTS
---------------
The directive's own rule: a claim needs a program reading, and a repaired check needs re-running
against the input that fooled it. This is the council's own smoke test — ten seats from canon, forty
Elements, the engine of record's hash, and the two anti-drift rules proved to fire on drifted prose
AND to stay silent on clean prose.

A rule that never fires is the failure mode this guards against, so every case here is a pair: one
sentence the rule must flag, one it must not.

It also re-runs the exact sentence that fooled the drift rule once: `Therefore we deduce it follows
logically.` The list held `logically follows` but not `follows logically`, so the rule returned two
findings where three were due. That was a real gap in coverage, found by this test, and the sentence
is kept in the list so the repair cannot silently regress.

Usage:
    C:\\Python314\\python.exe -B verify_council_intact.py
"""
from __future__ import annotations

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = r"C:\Users\wakil\Documents\Codex\2026-10-16\rpm_council_work\H_c8\engine.py"
ENGINE_SHA256 = "64c957e948a7754c6c4e8175b07299188a5892e75952b87e36d2d9b0847022ba"

#: (noetic, sentence, how many findings are due, why this case is here)
CASES = [
    ("CO-3", "I can't stomach it; it rubs me the wrong way.", 0,
     "visceral, the canonical register"),
    ("CO-3", "I will audit and scrutinise the critical evaluation.", 3,
     "analytical drift: audit and scrutinise and critical evaluation"),
    ("CO-3", "critique the design and find-flaw in it", 2,
     "analytical drift, the hyphenated and the plain form"),
    ("CO-8", "That reminds me. One thing leads to another.", 0,
     "associative, the canonical register"),
    ("CO-8", "Therefore we deduce it follows logically.", 3,
     "deductive drift, and the sentence that fooled the rule"),
    ("CO-8", "It follows logically from the premise.", 1,
     "the repaired phrasing on its own"),
    ("CO-8", "root-cause analysis of the failure", 1,
     "deductive drift under another name"),
]


def main() -> int:
    sys.path.insert(0, HERE)
    failures = []

    print("=" * 78)
    print("IS THE COUNCIL MECHANISM INTACT?")
    print("=" * 78)

    # 1. The engine of record, by hash.
    if os.path.isfile(ENGINE):
        with open(ENGINE, "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
        engine_ok = got == ENGINE_SHA256
        print("  engine of record  : %s" % ("MATCHES the recorded hash" if engine_ok
                                            else "DIFFERS: %s" % got))
        if not engine_ok:
            failures.append("the engine of record's hash differs from the recorded one")
    else:
        print("  engine of record  : NOT ON DISK at %s" % ENGINE)
        failures.append("the engine of record is not on disk")

    import council_loop as C

    # 2. Ten seats, one per canonical Noetic, and forty Elements.
    canons = sorted({s["noetic"] for s in C.SEATS})
    expected_canons = ["CO-%d" % i for i in range(10)]
    ok_seats = (len(C.SEATS) == 10 and canons == expected_canons)
    ok_elements = len(C.ELEMENTS) == 40
    print("  seats             : %d  %s" % (len(C.SEATS), "one per canonical Noetic" if ok_seats
                                             else "NOT ten canonical Noetics: %s" % canons))
    print("  Elements          : %d  %s" % (len(C.ELEMENTS), "10 Noetics x 4 Registers"
                                             if ok_elements else "NOT 40"))
    if not ok_seats:
        failures.append("the seats are not ten, one per canonical Noetic")
    if not ok_elements:
        failures.append("the Elements are not 40")

    # 3. The four RPM stages each activate the canonical Noetics.
    expected_activation = {"A0": ("CO-1", "CO-4", "CO-7"), "D": ("CO-5", "CO-6"),
                           "W": ("CO-5", "CO-6"), "P": ("CO-8", "CO-9")}
    got_activation = {k.value: tuple(v) for k, v in C.STAGE_ACTIVATION.items()}
    ok_activation = got_activation == expected_activation
    print("  stage activation  : %s" % ("the canonical four" if ok_activation
                                        else "DIFFERS: %s" % got_activation))
    if not ok_activation:
        failures.append("the stage-to-Noetic activation is not the canonical one")

    # 4. The anti-drift rules, each proved to fire AND to stay silent.
    print()
    print("  the anti-drift rules, on sentences that must and must not be flagged:")
    passed = 0
    for noetic, text, due, why in CASES:
        found = C.check_seat_report(noetic, text)
        good = len(found) == due
        passed += good
        print("    %-5s %-44s -> %d %-3s %s" % (noetic, text[:42], len(found),
                                                "OK" if good else "BAD", why))
    print("    %d of %d as expected" % (passed, len(CASES)))
    if passed != len(CASES):
        failures.append("%d of %d anti-drift cases did not behave as expected"
                        % (len(CASES) - passed, len(CASES)))

    print()
    print("=" * 78)
    if failures:
        print("RESULT: THE COUNCIL MECHANISM IS NOT INTACT")
        for f in failures:
            print("  - %s" % f)
    else:
        print("RESULT: THE COUNCIL MECHANISM IS INTACT")
        print("  10 seats from canon, 40 Elements, the engine of record on its recorded hash,")
        print("  the canonical stage activation, and both drift rules firing where they must")
        print("  and silent where they must.")
    print("=" * 78)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
