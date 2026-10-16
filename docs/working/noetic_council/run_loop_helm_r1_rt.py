"""Run ONE turn of THE Noetic Council loop on the R1-RT target and print its work order.

Usage:
    C:\\Python314\\python.exe -B run_loop_helm_r1_rt.py

R1-RT is "the same brain hosted inside HELM's own runtime". Same council, same engine, same
loop; a third task. This target is measured now, before any code, so that the prerequisite
state is on the record rather than in a design document's optimism.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from council_loop import (  # noqa: E402
    ELEMENTS, SEATS, next_iteration_number, prior_blockers_from_journal, run_iteration,
    write_iteration,
)
import target_helm_r1_rt as target  # noqa: E402

RULE = "=" * 78


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t = target.task()

    print(RULE)
    print("STEP 1  TARGET OUTCOME")
    print(RULE)
    print("  %s" % t["target_statement"])
    print()
    print("  The council is ten seats, and it is the same ten every turn:")
    for s in SEATS:
        print("    seat %2d  %-4s %-12s %s" % (s["seat"], s["noetic"], s["name"],
                                               s["operation"].split(".")[0]))
    print()
    print("  The 40 Elements available for deeper resolution: %d "
          "(10 Noetics x 4 Worlds, generated and assert-checked)" % len(ELEMENTS))
    print()

    n = next_iteration_number()
    prior = prior_blockers_from_journal()
    order, diagnosis = run_iteration(t, n, prior)
    path = write_iteration(order, diagnosis, None)

    print(RULE)
    print("STEP 2  RPM DIAGNOSIS   (iteration %d)" % n)
    print(RULE)
    print("  blocker        : %s" % order.blocker)
    print("  condition      : %s" % order.condition)
    print("  what it is     : %s" % order.condition_statement)
    print("  blocked stage  : %s  (%s)" % (order.stage, order.stage_meaning))
    print("  evidence there : %s" % order.evidence_at_stage)
    print("  recursion depth: %d" % order.depth)
    print("  note           : %s" % order.note)
    if order.frontier:
        print("  WHERE THE FAILURE PHYSICALLY IS (leaves of the diagnosis tree):")
        for f in order.frontier:
            print("    %-26s stage %-2s  %-14s  %s" % (
                f["condition"], f["stage"], f["blocker"], f["statement"]))
    print()
    print("  every condition and its live reading:")
    for c in target.conditions_for():
        r = c.established
        print("    %-26s %-5s %s" % (c.id, str(r.ok), r.detail[:88].replace("\n", " ")))
    print()

    if order.blocker == "SATISFIED":
        print(RULE)
        print("THE TARGET IS SATISFIED. The loop stops.")
        print(RULE)
        print("  iteration record: %s" % path)
        return 0

    print(RULE)
    print("STEP 3  TKS NOETIC COUNCIL   (the seats the canon activates for stage %s)"
          % order.stage)
    print(RULE)
    for s in order.seats:
        print("  seat %d  %s %s" % (s["seat"], s["noetic"], s["name"]))
        print("      canonical definition: %s" % s["definition"])
        print("      that seat's operation: %s" % s["operation"])
        if s.get("anti_drift"):
            print("      ANTI-DRIFT (load-bearing): %s" % s["anti_drift"])
        print()

    if order.frontier_seats:
        print(RULE)
        print("STEP 3b  SEATS FOR THE STAGE THAT PHYSICALLY FAILED")
        print(RULE)
        for g in order.frontier_seats:
            print("    stage %-2s (%s) -> %s" % (g["stage"], g["stage_meaning"],
                                                 ", ".join(g["noetics"])))
        print()

    print(RULE)
    print("STEP 4  CONDITIONAL ELEMENT ANALYSIS")
    print(RULE)
    print("  why: %s" % order.elements_reason)
    if order.elements:
        print("  activated Elements (%d):" % len(order.elements))
        for e in order.elements:
            print("    %-6s  %-12s x %-12s  %s" % (
                e["element"], e["noetic_name"], e["register"], e["register_definition"]))
    else:
        print("  no Elements activated this turn.")
    print()

    print(RULE)
    print("STEP 5  NEXT: resolve and verify, then RPM reevaluates")
    print(RULE)
    print("  iteration record: %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
