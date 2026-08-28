"""CCB-T1 demonstration: the tool cycle and the G7 fault suite."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from toolboard.faults import (branch_case, budget_case, hostile_result_case,
                              injected_failure_case, permission_case)
from toolboard.intent import execute, validate
from toolboard.toolboard import CCB_T1
from toolboard.tools import default_registry

ROOT = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(ROOT, "fixtures", name), "r",
              encoding="utf-8") as fh:
        return json.load(fh)


def main():
    print("CCB-T1 v0.1 - the Tool Use Board (the strict G7 gate)")
    print("=" * 64)

    board = CCB_T1(load("tool_need_problem.json"),
                   registry=default_registry())
    result = board.run()
    print("The tool cycle:")
    print(f"  kernel round 1: {result['packets'][0]['terminal_status']}")
    print(f"  tool: {board.tool_records[0]['tool']} - "
          f"{board.tool_records[0]['result']['note']}")
    print(f"  kernel round 2: {result['terminal_status']} "
          f"-> {result['conclusion']}")
    print(f"  provenance: committed={board.tool_records[0]['provenance']['committed_outcome']}, "
          f"sealed={board.tool_records[0]['provenance']['sealed_trace']}, "
          f"branch={board.tool_records[0]['provenance']['branch_id']}")

    print()
    print("The fault and adversarial suite:")
    cases = [
        ("branch tries to call a tool", branch_case(), "validate"),
        ("permission denied", permission_case(), "execute"),
        ("budget exhausted", budget_case(), "execute"),
        ("injected tool failure", injected_failure_case(), "execute"),
        ("hostile contradictory result", hostile_result_case(), "execute"),
    ]
    for name, case, mode in cases:
        try:
            if mode == "validate":
                reasons = validate(case["intent"], case["registry"], 0,
                                   5.0, case.get("facts", []))
                outcome = "REJECTED: " + "; ".join(reasons)
            else:
                execute(case["intent"], case["registry"], 0,
                        case.get("budget", 5.0), case.get("facts", []))
                outcome = "UNEXPECTED SUCCESS"
        except Exception as exc:
            outcome = f"{type(exc).__name__}"
        print(f"  {name:<34} -> {outcome}")


if __name__ == "__main__":
    main()
