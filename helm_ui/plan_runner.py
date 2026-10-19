"""Run HELM's prerequisite-graph planner on one request and print the result as JSON. Nothing is executed.

Called by helm_ui/server.py in its own process (the planner's helper modules have short names such as `loop` and
`bias` that must not mix with the chat session's modules). Uses docs/working/noetic_council/prereq_planner as-is:
  1. plan_graph.build_plan(text)        -> nodes, edges (each with the sentence that made it), Kahn order, digest,
                                           or a typed refusal (PLAN_CYCLE, PLAN_EMPTY, PLAN_HORIZON, ...)
  2. plan_executor.execute_plan(plan)   -> runner=None: no tool runs; each step only asks the RPM gate and writes
                                           its name into an in-memory Bias. A gate REPAIR here is PLAN_ORDER_VIOLATION.

    python -I helm_ui/plan_runner.py "Write the code for auth.py, verify the tests pass, then commit it to git."
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

PLANNER = Path(__file__).resolve().parent.parent / "docs" / "working" / "noetic_council" / "prereq_planner"


def main() -> int:
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.path.insert(0, str(PLANNER))
    with contextlib.redirect_stdout(io.StringIO()):
        import plan_graph as G
        import plan_executor as X
    out = {"ok": True, "request": text, "claim_ceiling": G.CLAIM_CEILING,
           "source": "docs/working/noetic_council/prereq_planner (plan_graph.build_plan + plan_executor.execute_plan, runner=None)"}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            plan = G.build_plan(text)
        out["plan"] = plan.as_dict()
    except G.PlanRefusal as exc:
        out.update({"refused": True, "stage": "plan", "code": exc.code, "detail": exc.detail})
        print(json.dumps(out))
        return 0
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rec = X.execute_plan(plan)
        out["dry_run"] = rec.as_dict()
        out["refused"] = False
    except G.PlanRefusal as exc:
        out.update({"refused": True, "stage": "gate", "code": exc.code, "detail": exc.detail})
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
