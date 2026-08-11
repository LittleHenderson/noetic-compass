"""Read-only emergency-control coverage report for CAS Forex.

Emergency Stop already exists, but a professional trading app needs to show the
exact effect of that control. This report separates automation-stop coverage
from broker-exposure management so the owner can see what is covered in-app and
what still requires MT4/MT5 terminal action or a future tested route.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

CLAIM_BOUNDARY = (
    "Emergency controls coverage is a read-only diagnostic. It reports which "
    "automation-stop and broker-exposure controls are wired. It does not start "
    "or stop processes, place orders, close positions, cancel orders, move "
    "money, clear auto-halt, or authorize live trading."
)


def build_emergency_controls_report(root: Path | str | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    controls = [
        _control(
            base,
            key="manual_emergency_stop_latch",
            label="Manual Emergency Stop Latch",
            category="automation_stop",
            route="/api/forex/auto-halt/emergency-stop",
            surface="Dashboard > Verified Profit Sweep > Emergency Stop",
            effect="Latches auto-halt from an owner command so automated live dispatch paths fail closed until cleared.",
            money_impact="No broker order is sent. Existing broker positions remain open.",
            required=[
                _marker("api/routes/auto_halt.py", '@router.post("/emergency-stop")'),
                _marker("cas_forex/auto_halt.py", "manual_emergency_stop"),
                _marker("ui/src/data/api.ts", "triggerAutoHaltEmergencyStop"),
                _marker("ui/src/components/DashboardOperationsWorkbench.tsx", "handleEmergencyStop"),
                _marker("ui/src/components/DashboardSweepOpsPanel.tsx", "Emergency Stop"),
            ],
            missing_detail="Wire the owner emergency-stop route, API client, and visible dashboard button.",
        ),
        _control(
            base,
            key="dispatch_loop_stop",
            label="Dispatch Loop Stop",
            category="automation_stop",
            route="/api/forex/dispatch-loop/stop",
            surface="Dashboard emergency handler",
            effect="Stops the timer-driven dispatch loop that can submit new gated trade attempts.",
            money_impact="No broker order is sent by this stop call. Existing broker positions remain open.",
            required=[
                _marker("api/routes/dispatch_loop.py", '@router.post("/stop")'),
                _marker("cas_forex/dispatch_loop.py", "stop_loop"),
                _marker("ui/src/data/api.ts", "stopDispatchLoop"),
                _marker("ui/src/components/DashboardOperationsWorkbench.tsx", "stopDispatchLoop"),
            ],
            missing_detail="Expose and call the dispatch-loop stop route from the owner emergency handler.",
        ),
        _control(
            base,
            key="waste_runner_stop",
            label="WASTE Runner Stop",
            category="automation_stop",
            route="/api/forex/waste-loop-control/stop",
            surface="Dashboard emergency handler",
            effect="Stops the WASTE runner heartbeat and prevents additional WASTE-driven dispatch handoffs.",
            money_impact="No broker order is sent by this stop call. Existing broker positions remain open.",
            required=[
                _marker("api/routes/waste_loop_control.py", '@router.post("/stop")'),
                _marker("cas_forex/waste_runner.py", "def stop_runner"),
                _marker("ui/src/data/api.ts", "stopWasteLoop"),
                _marker("ui/src/components/DashboardOperationsWorkbench.tsx", "stopWasteLoop"),
            ],
            missing_detail="Expose and call the WASTE-runner stop route from the owner emergency handler.",
        ),
        _control(
            base,
            key="paper_sample_scheduler_stop",
            label="Paper Sample Scheduler Stop",
            category="automation_stop",
            route="/api/forex/waste-loop-control/paper-sample-collector/scheduler/stop",
            surface="Settings and WASTE operations",
            effect="Stops the paper sample collector scheduler used for evidence gathering.",
            money_impact="No broker order is sent. This is evidence collection, not execution.",
            required=[
                _marker("api/routes/waste_loop_control.py", '"/paper-sample-collector/scheduler/stop"'),
                _marker("cas_forex/waste_background_worker.py", "stop_paper_sample_collector_worker"),
                _marker("ui/src/data/api.ts", "stopWastePaperSampleCollectorScheduler"),
            ],
            missing_detail="Expose the paper sample scheduler stop route and API client method.",
        ),
        _control(
            base,
            key="broker_close_all_positions",
            label="Broker Close All Positions",
            category="broker_exposure",
            route="/api/forex/broker-emergency/close-all",
            surface="Broker Emergency API; dashboard/Settings coverage panel",
            effect="Would submit broker close orders for every open position after explicit owner confirmation.",
            money_impact="Money-touching order_send action. This must be idempotent, audited, broker-reconciled, and owner-confirmed.",
            required=[
                _marker("cas_forex/broker/mt5_bridge.py", "def close_position"),
                _any_marker(
                    "api/routes",
                    (
                        "close_all_positions",
                        "close-all-positions",
                        "flatten_all_positions",
                        "broker_flatten",
                    ),
                ),
            ],
            missing_detail="No tested owner route currently closes all broker positions from the app.",
        ),
        _control(
            base,
            key="broker_cancel_pending_orders",
            label="Cancel Pending Broker Orders",
            category="broker_exposure",
            route="/api/forex/broker-emergency/cancel-pending",
            surface="Broker Emergency API; dashboard/Settings coverage panel",
            effect="Would submit broker remove/cancel requests for pending orders after explicit owner confirmation.",
            money_impact="Money-touching broker-state action. This must be idempotent, audited, broker-reconciled, and owner-confirmed.",
            required=[
                _marker("cas_forex/broker/mt5_bridge.py", "def cancel_pending_order"),
                _any_marker(
                    "api/routes",
                    (
                        "cancel_pending_orders",
                        "cancel-pending-orders",
                        "cancel_all_orders",
                        "cancel-all-orders",
                    ),
                ),
            ],
            missing_detail="No tested owner route currently cancels pending broker orders from the app.",
        ),
        _control(
            base,
            key="selective_close_profitable_positions",
            label="Close Profitable Positions",
            category="broker_exposure",
            route="/api/forex/broker-emergency/close-profitable",
            surface="Broker Emergency API; dashboard/Settings coverage panel",
            effect="Would close only currently profitable broker positions after explicit owner confirmation.",
            money_impact="Money-touching broker close action. Requires fresh broker truth and position-level audit.",
            required=[
                _any_marker("api/routes", ("close_profitable_positions", "close-profitable-positions")),
            ],
            missing_detail="No tested owner route currently closes only profitable broker positions from the app.",
        ),
        _control(
            base,
            key="selective_close_losing_positions",
            label="Close Losing Positions",
            category="broker_exposure",
            route="/api/forex/broker-emergency/close-losing",
            surface="Broker Emergency API; dashboard/Settings coverage panel",
            effect="Would close only currently losing broker positions after explicit owner confirmation.",
            money_impact="Money-touching broker close action. Requires fresh broker truth and position-level audit.",
            required=[
                _any_marker("api/routes", ("close_losing_positions", "close-losing-positions")),
            ],
            missing_detail="No tested owner route currently closes only losing broker positions from the app.",
        ),
    ]

    attention = [control for control in controls if control["status"] != "OK"]
    broker_gaps = [control for control in attention if control["category"] == "broker_exposure"]
    automation_stop_controls = [control for control in controls if control["category"] == "automation_stop"]
    automation_stop_ok = all(control["status"] == "OK" for control in automation_stop_controls)

    return {
        "report_kind": "cas_forex_emergency_controls",
        "status": "OK" if not attention else "ATTENTION",
        "ok_count": sum(1 for control in controls if control["status"] == "OK"),
        "attention_count": len(attention),
        "automation_stop_ok": automation_stop_ok,
        "broker_exposure_gap": bool(broker_gaps),
        "controls": controls,
        "attention_items": [control["missing_detail"] for control in attention],
        "automation_stop_scope": (
            "The in-app Emergency Stop path latches auto-halt and stops automation loops. "
            "It is designed to block new automated dispatch, not to change existing broker exposure."
        ),
        "recommended_terminal_actions": [
            "Keep MT4/MT5 visible when automation is running.",
            "For urgent existing-position management, use the broker terminal until a tested app-level flatten/cancel route is added.",
            "After any terminal action, refresh broker truth, account reconciliation, and auto-halt status in CAS Forex.",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _control(
    base: Path,
    *,
    key: str,
    label: str,
    category: str,
    route: str | None,
    surface: str,
    effect: str,
    money_impact: str,
    required: list[dict[str, Any]],
    missing_detail: str,
    ok_when_all_required: bool = True,
) -> dict[str, Any]:
    evidence = [_evaluate_evidence(base, item) for item in required]
    missing = [item for item in evidence if not item["present"]]
    status = "OK" if ok_when_all_required and not missing else "MISSING"
    if not ok_when_all_required and not missing:
        status = "OK"
    return {
        "key": key,
        "label": label,
        "category": category,
        "status": status,
        "route": route,
        "surface": surface,
        "effect": effect,
        "money_impact": money_impact,
        "evidence": evidence,
        "missing_detail": "" if status == "OK" else missing_detail,
        "missing_evidence": [item["description"] for item in missing],
    }


def _marker(path: str, marker: str) -> dict[str, Any]:
    return {"kind": "file_marker", "path": path, "marker": marker}


def _any_marker(path: str, markers: tuple[str, ...]) -> dict[str, Any]:
    return {"kind": "tree_any_marker", "path": path, "markers": markers}


def _evaluate_evidence(base: Path, item: dict[str, Any]) -> dict[str, Any]:
    kind = item.get("kind")
    rel_path = Path(str(item.get("path") or ""))
    full_path = base / rel_path
    if kind == "file_marker":
        marker = str(item.get("marker") or "")
        text = _read_text(full_path)
        present = bool(text and marker in text)
        return {
            "path": rel_path.as_posix(),
            "marker": marker,
            "present": present,
            "description": f"{rel_path.as_posix()} contains {marker!r}",
        }
    if kind == "tree_any_marker":
        markers = tuple(str(marker) for marker in item.get("markers") or ())
        matched = _find_any_marker(full_path, markers)
        return {
            "path": rel_path.as_posix(),
            "markers": list(markers),
            "present": matched is not None,
            "matched_path": matched,
            "description": f"{rel_path.as_posix()} contains one of {', '.join(markers)}",
        }
    return {
        "path": rel_path.as_posix(),
        "present": False,
        "description": f"Unknown evidence kind {kind!r}",
    }


def _find_any_marker(path: Path, markers: tuple[str, ...]) -> str | None:
    if not path.exists():
        return None
    files = [path] if path.is_file() else sorted(path.rglob("*.py"))
    for file_path in files:
        text = _read_text(file_path)
        if not text:
            continue
        if any(marker in text for marker in markers):
            try:
                return file_path.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                return file_path.as_posix()
    return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
