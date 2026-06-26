"""Production runner: real agent signals -> overseer -> gated dispatch -> report.

This is the non-demo entry point for the gated agent-dispatch path. It pulls the
agent cycle's REAL route intents from the latest replay evidence
(``collect_route_intents``), runs them through the overseer, and dispatches the
approved ones through the live-trading + risk gate into the configured broker
bridge (the paper broker until live trading is owner-authorized), then writes a
JSON evidence artifact.

    python scripts/run_agent_dispatch_cycle.py

It changes no real-money posture: with default config the broker is the paper
simulator and every money gate is NOT LICENSED.
"""

from __future__ import annotations

from cas_forex.agent_dispatch import (
    run_agent_dispatch_cycle,
    write_agent_dispatch_cycle_report,
)


def main() -> None:
    cycle = run_agent_dispatch_cycle(enforce_receipt_gates=True)
    report = cycle.dispatch_report
    print("=== AGENT DISPATCH CYCLE (real signals -> overseer -> gated dispatch) ===")
    print(
        f"route_intents={len(cycle.route_intents)} approved={cycle.approved_count} "
        f"mode={report.mode} executed={report.executed_count} blocked={report.blocked_count} "
        f"rejected={report.rejected_count} pending={report.pending_count} "
        f"live_locked={report.live_execution_runtime_locked}"
    )
    for r in report.results:
        print(f"  - {r.order_id:24s} {r.status:18s} :: {r.reason}")
    if not cycle.route_intents:
        print(
            "  (no route intents — load Forex Fury replay evidence under "
            "evidence_runs/ to produce live agent signals)"
        )

    paths = write_agent_dispatch_cycle_report(cycle)
    print(f"\nReport written: {paths['json']}")


if __name__ == "__main__":
    main()
