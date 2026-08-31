"""rc01_replay_entry.py -- fresh-process replay entry point (RC-0.1 requirement 7).

Usage:  python rc01_replay_entry.py <scenario_id> [--mutate]

Runs ONE registered scenario in THIS process and prints its trace digest. Two separate
OS processes running the same scenario must print the same digest; --mutate changes
exactly one input field (the first cause's payload) and must change the digest — this
kills any constant or insensitive digest function.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rc01_scenarios as SC  # noqa: E402
from rc01_types import Cause  # noqa: E402


def main():
    scenario_id = sys.argv[1]
    mutate = "--mutate" in sys.argv
    sc = next(s for s in SC.SCENARIOS() if s["id"] == scenario_id)
    eng = sc["build"]()
    if mutate:
        # causes is an OWNED immutable tuple (RC-0.4D schema); the sensitivity probe
        # rebuilds it with one mutated input field
        c0 = eng.causes[0]
        eng.causes = (Cause(cause_id=c0.cause_id, evidence=c0.evidence,
                            payload=c0.payload + " MUTATED"),) + tuple(eng.causes[1:])
    res = eng.run()
    print(res["trace_digest"])


if __name__ == "__main__":
    main()
