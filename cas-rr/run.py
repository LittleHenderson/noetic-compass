"""CLI for the CAS Reasoning Runtime - run, inspect, and extend the machine.

Usage (from the cas-rr directory):

    python run.py list                     list all battery tasks
    python run.py run transitive           run one episode, bench report
    python run.py run recursive_plan --trace
    python run.py run fault --full         full provenance packet as JSON
    python run.py run transitive --json out.json
    python run.py demo                     run the whole battery
    python run.py check                    determinism check on every task
    python run.py repl                     interactive Python session

The runtime itself is importable anywhere: see INTERACTION.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional


def _runtime(task_name):
    from cas_rr.runtime import CASRuntime
    from tasks import battery

    task = battery.BATTERY[task_name]()
    constitution = battery.constitution_for(task_name)
    return CASRuntime(constitution, task)


def cmd_list(args) -> int:
    from tasks import battery

    for name, factory in battery.BATTERY.items():
        task = factory()
        print(f"{name:<24} {task.description}")
    return 0


def cmd_run(args) -> int:
    rt = _runtime(args.task)
    packet = rt.run()

    from cas_rr.report import summarize, trace_compact

    print(summarize(packet))
    if args.trace:
        print("")
        print("--- trace ---")
        print(trace_compact(packet))
    if args.full:
        print("")
        print("--- full packet ---")
        print(json.dumps(packet, indent=2, default=str))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(packet, fh, indent=2, default=str)
        print(f"packet written to {args.json}")
    return 0


def cmd_demo(args) -> int:
    from cas_rr.runtime import CASRuntime
    from cas_rr.report import battery_table
    from tasks import battery

    results = {}
    for name in battery.BATTERY:
        task = battery.BATTERY[name]()
        constitution = battery.constitution_for(name)
        results[name] = CASRuntime(constitution, task).run()
    print(battery_table(results))
    return 0


def cmd_check(args) -> int:
    from cas_rr.report import determinism_check
    from tasks import battery

    failures = 0
    for name in battery.BATTERY:
        constitution = battery.constitution_for(name)
        ok, detail = determinism_check(battery.BATTERY[name], constitution)
        mark = "OK " if ok else "FAIL"
        print(f"{mark} {name:<24} {detail}")
        failures += 0 if ok else 1
    return 1 if failures else 0


def cmd_repl(args) -> int:
    import code

    from cas_rr.report import summarize
    from cas_rr.runtime import CASRuntime, default_constitution
    from tasks import battery

    rt = CASRuntime(default_constitution(), battery.task_transitive())
    packet = rt.run()
    banner = (
        "CAS-RR v0.1 interactive session."
        ""
        "Ready-made: rt (a finished transitive episode), packet (its provenance), "
        "battery (task builders), CASRuntime, default_constitution."
        ""
        "Try: packet['terminal_status'], packet['trace'][-1], "
        "or run a new episode: rt2 = CASRuntime(default_constitution(), "
        "battery.task_fault()); summarize(rt2.run())."
    )
    code.interact(banner=banner, local=dict(
        rt=rt, packet=packet, battery=battery,
        CASRuntime=CASRuntime, default_constitution=default_constitution,
        summarize=summarize,
    ))
    return 0


def cmd_report(args) -> int:
    from cas_rr.benchmark import report_text, run_ladder
    from tasks.levels import LADDER

    print(report_text(run_ladder(LADDER)))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="run.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")

    p_run = sub.add_parser("run")
    p_run.add_argument("task")
    p_run.add_argument("--trace", action="store_true")
    p_run.add_argument("--full", action="store_true")
    p_run.add_argument("--json")

    sub.add_parser("demo")
    sub.add_parser("check")
    sub.add_parser("repl")
    sub.add_parser("report")

    args = parser.parse_args(argv)
    return {
        "list": cmd_list,
        "run": cmd_run,
        "demo": cmd_demo,
        "check": cmd_check,
        "repl": cmd_repl,
        "report": cmd_report,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
