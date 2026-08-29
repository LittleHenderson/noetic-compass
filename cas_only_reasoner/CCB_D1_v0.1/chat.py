"""TALK TO THE MACHINE - the CONV v0.1 terminal.

    python chat.py            one session; ctrl+c or 'quit' to leave
    python chat.py --trace    also print route/status/source per turn

Every reply comes from the native runtime (no model anywhere at
runtime). What you assert is remembered WITH its source and answered
back only as "based on what you told me"; verified facts say so;
unknowns are honest; conflicts are surfaced, never resolved silently.
The session ends when you leave - session assertions are
session-scoped by design.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
for path in (HERE, os.path.join(LANE, "CAS_CORTEX_v0.1"),
             os.path.join(LANE, "CCB_L1_v0.1")):
    if path not in sys.path:
        sys.path.insert(0, path)

from cortex.router import HybridRouter  # noqa: E402


def main() -> None:
    show_trace = "--trace" in sys.argv
    router = HybridRouter(mode="NATIVE_ONLY")
    print("CONV v0.1 - the CNCM dialogue terminal. lowercase "
          "sentences ending in . or ? ('quit' to leave)")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("quit", "exit"):
            break
        trace = router.turn(line)
        answer = trace["answer"]
        reply = (answer.get("text") or answer.get("acknowledgment")
                 or answer.get("detail") or answer.get("status"))
        print(f"machine> {reply}")
        if show_trace:
            print(f"    [route={trace.get('route')} "
                  f"status={answer.get('status')} "
                  f"source={answer.get('source_class')}]")
    active = router.dialogue.store.active()
    if active:
        print("\nsession assertions on the record at exit "
              "(session-scoped, not persisted):")
        for record in router.dialogue.store.records:
            print(f"  {record['assertion_id']} "
                  f"{record['lifecycle_status']:10} "
                  f"{record['clause']}")


if __name__ == "__main__":
    main()
