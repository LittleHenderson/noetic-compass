"""One-command demonstration: the six fixtures against their goldens."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kernel.fixtures import FIXTURE_NAMES, digest_path, freeze_trace_digests
from kernel.fixtures import load_golden, load_problem
from kernel.kernel import CAS_RRK


def main():
    print("CAS-RRK v0.1 - golden fixture run")
    print("-" * 64)
    packets = {}
    for name in FIXTURE_NAMES:
        golden = load_golden(name)
        packet = CAS_RRK(load_problem(name)).run()
        packets[name] = packet
        status_ok = packet["terminal_status"] == golden["expected_status"]
        concl_ok = (
            (golden["expected_conclusion"] is None
             and packet["conclusion"] is None)
            or (golden["expected_conclusion"] is not None
                and packet["conclusion"] == golden["expected_conclusion"]))
        mark = "PASS" if (status_ok and concl_ok) else "FAIL"
        conclusion = packet["conclusion"] or "-"
        print(f"{mark}  {name:<24} {packet['terminal_status']:<22} {conclusion}")

    if not os.path.exists(digest_path(FIXTURE_NAMES[0])):
        freeze_trace_digests(packets)
        print("")
        print("trace digests frozen into golden/expected_traces/")
    else:
        from kernel.fixtures import load_digest
        for name in FIXTURE_NAMES:
            if packets[name]["trace_digest"] != load_digest(name):
                print(f"TRACE MISMATCH for {name}")


if __name__ == "__main__":
    main()
