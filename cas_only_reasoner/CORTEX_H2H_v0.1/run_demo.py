"""Run the full head-to-head (Route A native vs Route B cortex) and
seal the results into output/."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from h2h.route_b import RouteB
from h2h.run_h2h import format_report, run


def main():
    print("loading Route B cortex (offline, local cache)...")
    route_b = RouteB()
    print("running the battery on both routes (each item twice)...")
    packet = run(route_b=route_b)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "h2h_results.json"), "w",
              encoding="utf-8") as fh:
        json.dump(packet, fh, indent=1, sort_keys=True)
    report = format_report(packet)
    with open(os.path.join(out, "h2h_report.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(report + "\n")
    print(report)


if __name__ == "__main__":
    main()
