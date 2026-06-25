"""CAS Forex Bot — structured conversational agent for CAS Forex operations.

Design principles:
- System-knowledgeable: loads all relevant docs into context
- Menu-driven: limited options at each level to prevent decision paralysis
- Action-capable: dispatches to scripts/functions for all CAS Forex operations
- Learnable: shows underlying commands so the user learns the system

Architecture:
    Level 0: Status summary + 4-6 top-level action groups
    Level 1: Context-specific options within a group
    Dispatch: Maps user intent → script/function execution
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Knowledge Base — auto-discovered from the codebase and docs
# ---------------------------------------------------------------------------


@dataclass
class BotCapability:
    """A single thing the bot can do."""
    key: str                    # Quick-access key (e.g., "1", "cy", "st")
    label: str                  # Short label for display
    description: str            # What it does
    group: str                  # Top-level group
    commands: List[str] = field(default_factory=list)  # Underlying commands
    script: Optional[str] = None  # Script path relative to REPO_ROOT
    api_endpoint: Optional[str] = None  # API endpoint
    danger_level: str = "safe"  # safe | caution | dangerous
    requires_confirm: bool = False


# Auto-discovered capabilities from the codebase
CAPABILITIES: List[BotCapability] = [
    # ---- STATUS & OBSERVABILITY ----
    BotCapability(
        key="1", group="status", label="System Health Check",
        description="Check API health, MT5 terminal connection, operability status",
        api_endpoint="/api/forex/health",
        commands=["curl http://127.0.0.1:8765/api/forex/health"],
    ),
    BotCapability(
        key="2", group="status", label="Dashboard Overview",
        description="Full dashboard: paper proof, operability, adaptive state, PCBA",
        api_endpoint="/api/forex/dashboard",
        commands=["curl http://127.0.0.1:8765/api/forex/dashboard"],
    ),
    BotCapability(
        key="3", group="status", label="Live Readiness Checklist",
        description="What gates are open/blocked for live trading",
        api_endpoint="/api/forex/readiness/live",
        commands=["curl http://127.0.0.1:8765/api/forex/readiness/live"],
    ),
    BotCapability(
        key="4", group="status", label="Terminal Operability",
        description="MT5 terminal connection, account, positions, trade permission",
        script="scripts/run_terminal_operability_verifier.py",
        commands=["py -3.12 scripts/run_terminal_operability_verifier.py --summary-only"],
    ),
    BotCapability(
        key="5", group="status", label="Agent Memory",
        description="Current agent learning memory: trades, P/L, receipts",
        api_endpoint="/api/forex/strategy/agent-memory/latest",
    ),
    BotCapability(
        key="6", group="status", label="Event Journal",
        description="Last agent cycle events, receipts, pending items",
        api_endpoint="/api/forex/strategy/agent-events/latest",
    ),
    BotCapability(
        key="ax", group="status", label="Explain Latest Agent Decision",
        description="Walk the agent's reasoning chain for the most recent cycle: strategy lead, walk-forward, PCBA gate, cycle intent, execution outcome",
        api_endpoint="/api/forex/agent-decision/latest",
    ),
    BotCapability(
        key="ah", group="status", label="Autonomous Loop Health",
        description="Is the autonomous loop alive? Last cycle time, cycles today, decisions/executions/blocked counts, diagnostic hints",
        api_endpoint="/api/forex/autonomous-loop/health",
    ),

    # ---- AGENT WORKFLOW ----
    BotCapability(
        key="cy", group="workflow", label="Run Agent Cycle (dry run)",
        description="Run one agent workflow cycle without sending orders — see what decisions WOULD be made",
        script="scripts/run_agent_workflow_queue.py",
        commands=["py -3.12 scripts/run_agent_workflow_queue.py --terminal-lane PAPER_MT5_DEMO --no-terminal-commands --summary-only"],
        danger_level="safe",
    ),
    BotCapability(
        key="cm", group="workflow", label="Run Agent Cycle (MT5 demo)",
        description="Run full agent cycle with MT5 demo execution + deal history",
        script="scripts/run_agent_workflow_queue.py",
        commands=["py -3.12 scripts/run_agent_workflow_queue.py --terminal-lane PAPER_MT5_DEMO --mt5-path \"C:\\Program Files\\Hugosway\\Hugosway PRO5 Terminal\\terminal64.exe\" --execute-mt5-demo-order --confirm-mt5-demo-order --mt5-use-process-guard --summary-only"],
        danger_level="caution",
        requires_confirm=True,
    ),
    BotCapability(
        key="aw", group="workflow", label="Run Session Autowake",
        description="Check if a trading session should wake and decide on cycle cadence",
        script="scripts/run_session_autowake_runner.py",
        commands=["py -3.12 scripts/run_session_autowake_runner.py --summary-only"],
        danger_level="safe",
    ),
    BotCapability(
        key="ml", group="workflow", label="Daily Learning Rollup",
        description="End-of-day learning summary: P/L, strategies, memory",
        api_endpoint="/api/forex/strategy/daily-learning-rollup/latest",
    ),
    BotCapability(
        key="dp", group="workflow", label="Run MT4 Mailbox Cycle",
        description="Run an agent cycle using MT4 mailbox commands instead of MT5",
        script="scripts/run_agent_workflow_queue.py",
        commands=["py -3.12 scripts/run_agent_workflow_queue.py --terminal-lane PAPER_MT4_MAILBOX --summary-only"],
        danger_level="safe",
    ),

    # ---- MT5 TERMINAL ----
    BotCapability(
        key="mt", group="mt5", label="MT5 Terminal Probe",
        description="Check MT5 terminal connection, account, server, positions",
        script="scripts/run_mt5_terminal_api_verifier.py",
        commands=["py -3.12 scripts/run_mt5_terminal_api_verifier.py --summary-only"],
    ),
    BotCapability(
        key="me", group="mt5", label="MT5 Paper Execution (dry run)",
        description="Build and check an MT5 order WITHOUT sending it",
        script="scripts/run_mt5_paper_execution_verifier.py",
        commands=["py -3.12 scripts/run_mt5_paper_execution_verifier.py --summary-only"],
    ),
    BotCapability(
        key="mo", group="mt5", label="MT5 Demo Order (send + close)",
        description="Send one demo order to MT5 and close it immediately (TESTS the path)",
        script="scripts/run_mt5_paper_execution_verifier.py",
        commands=["py -3.12 scripts/run_mt5_paper_execution_verifier.py --mt5-path \"C:\\Program Files\\Hugosway\\Hugosway PRO5 Terminal\\terminal64.exe\" --execute-demo-order --confirm-demo-order --summary-only"],
        danger_level="caution",
        requires_confirm=True,
    ),
    BotCapability(
        key="dh", group="mt5", label="MT5 Deal History Ingest",
        description="Pull closed deal history from MT5 for a specific ticket",
        script="scripts/run_mt5_deal_history_ingest.py",
        commands=["py -3.12 scripts/run_mt5_deal_history_ingest.py --summary-only"],
    ),

    # ---- PAPER PROOF ----
    BotCapability(
        key="pb", group="proof", label="Paper Daily Bundle",
        description="Generate today's paper proof bundle (entries, exits, evidence)",
        script="scripts/run_paper_daily_bundle.py",
        commands=["py -3.12 scripts/run_paper_daily_bundle.py"],
    ),
    BotCapability(
        key="pp", group="proof", label="Paper Proof Status",
        description="Check paper proof maturity: days, bundles, UI readiness",
        api_endpoint="/api/forex/strategy/paper-proof/latest",
    ),
    BotCapability(
        key="pr", group="proof", label="Paper Risk Review",
        description="Latest paper risk assessment: drawdown, margin, exposure",
        api_endpoint="/api/forex/strategy/paper-risk/latest",
    ),
    BotCapability(
        key="bs", group="proof", label="Backsolve (income target)",
        description="Run leveraged income backsolve — can this edge hit the target?",
        script="scripts/run_leverage_backsolve.py",
        commands=["py -3.12 scripts/run_leverage_backsolve.py --summary-only"],
    ),

    # ---- STRATEGY & PCBA ----
    BotCapability(
        key="sp", group="strategy", label="Strategy Dev Queue",
        description="Strategy development queue: promotions, demotions, review",
        api_endpoint="/api/forex/strategy/strategy-dev-queue/latest",
    ),
    BotCapability(
        key="sl", group="strategy", label="Strategy Leads",
        description="Current strategy leads from Forex Fury replay",
        api_endpoint="/api/forex/strategy/forex-fury-replay-candidates/latest",
    ),
    BotCapability(
        key="pc", group="strategy", label="PCBA Guard Status",
        description="PCBA optimizer guard: verdicts, safety checks, prompt injection scan",
        api_endpoint="/api/forex/strategy/pcba-goal-status/latest",
    ),
    BotCapability(
        key="wf", group="strategy", label="Walk-Forward Analysis",
        description="Latest walk-forward test results for active strategies",
        api_endpoint="/api/forex/strategy/walk-forward/latest",
    ),

    # ---- OWNER & SETTINGS ----
    BotCapability(
        key="oc", group="owner", label="Owner Control Settings",
        description="View current owner control flags (live trading, broker ACCEPT, etc.)",
        api_endpoint="/api/forex/settings/owner-control",
    ),
    BotCapability(
        key="rg", group="owner", label="Runtime Gates",
        description="View runtime gate status (all gates, blocking reasons)",
        api_endpoint="/api/forex/settings/runtime-gates",
    ),
    BotCapability(
        key="bp", group="owner", label="Broker Sync Risk Preview",
        description="Preview what a broker sync would look like before committing",
        api_endpoint="/api/forex/account/broker-sync-risk-preview",
    ),

    # ---- SYSTEM ----
    BotCapability(
        key="rt", group="system", label="Run Tests",
        description="Run the full CAS Forex test suite",
        commands=["py -3.12 -m pytest tests -q"],
    ),
    BotCapability(
        key="rb", group="system", label="Rebuild UI",
        description="Rebuild the React dashboard",
        commands=["cd ui && npm run build"],
    ),
    BotCapability(
        key="ev", group="system", label="View Evidence",
        description="List recent evidence runs",
        commands=["dir evidence_runs /O-D /B"],
    ),
    BotCapability(
        key="ui", group="system", label="Open Dashboard",
        description="Open the CAS Forex dashboard in browser",
        commands=["start http://127.0.0.1:5174"],
    ),
    BotCapability(
        key="api", group="system", label="Open API Docs",
        description="Open the FastAPI docs",
        commands=["start http://127.0.0.1:8765/docs"],
    ),
]


# ---------------------------------------------------------------------------
# Group definitions for the menu system
# ---------------------------------------------------------------------------

GROUPS: Dict[str, Dict[str, str]] = {
    "status": {
        "name": "Status & Observability",
        "emoji": "📊",
        "description": "Check system health, dashboard, operability, memory",
    },
    "workflow": {
        "name": "Agent Workflow",
        "emoji": "🤖",
        "description": "Run agent cycles, autowake, daily rollup",
    },
    "mt5": {
        "name": "MT5 Terminal",
        "emoji": "💹",
        "description": "MT5 connection, order execution, deal history",
    },
    "proof": {
        "name": "Paper Proof",
        "emoji": "📋",
        "description": "Paper bundles, risk, backsolve, evidence",
    },
    "strategy": {
        "name": "Strategy & PCBA",
        "emoji": "🧠",
        "description": "Strategy dev, walk-forward, PCBA guard",
    },
    "owner": {
        "name": "Owner & Settings",
        "emoji": "🔐",
        "description": "Owner controls, runtime gates, broker sync",
    },
    "system": {
        "name": "System",
        "emoji": "⚙️",
        "description": "Tests, UI build, evidence, dashboard",
    },
}

# Group display order
GROUP_ORDER = ["status", "workflow", "mt5", "proof", "strategy", "owner", "system"]


# ---------------------------------------------------------------------------
# Bot state
# ---------------------------------------------------------------------------


@dataclass
class BotState:
    """Mutable bot session state."""
    current_group: Optional[str] = None
    last_capability: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    confirm_pending: Optional[str] = None  # capability key awaiting confirmation
    mt5_path: str = r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe"
    api_base: str = "http://127.0.0.1:8765"


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _header(text: str, emoji: str = "") -> str:
    bar = "=" * 60
    prefix = f"{emoji} " if emoji else ""
    return f"\n{bar}\n  {prefix}{text}\n{bar}\n"


def _option(key: str, label: str, desc: str, danger: str = "") -> str:
    d = f"  ⚠ {danger}" if danger else ""
    return f"  [{key}] {label}\n       {desc}{d}"


def _danger_label(level: str) -> str:
    if level == "dangerous":
        return "LIVE/REAL-MONEY — confirm required"
    if level == "caution":
        return "MT5 demo order — confirm required"
    return ""


# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------


def _status_line(label: str, value: str, ok: bool = True) -> str:
    icon = "✓" if ok else "✗"
    return f"  {icon} {label}: {value}"


def build_status_summary(state: BotState) -> str:
    """Build a concise status summary for the greeting screen."""
    lines: List[str] = []
    try:
        import urllib.request
        health_url = f"{state.api_base}/api/forex/health"
        req = urllib.request.Request(health_url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode())
            lines.append(_status_line("API", health.get("status", "unknown"), health.get("status") == "healthy"))
    except Exception:
        lines.append(_status_line("API", "unreachable", False))

    try:
        readiness_url = f"{state.api_base}/api/forex/readiness/live"
        req = urllib.request.Request(readiness_url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            readiness = json.loads(resp.read().decode())
            overall = str(readiness.get("overall_status") or "unknown")
            passed = readiness.get("checks_passed")
            total = readiness.get("checks_total")
            checks_label = (
                f"{passed}/{total} gates open"
                if passed is not None and total is not None
                else overall
            )
            # Greeting reports gate count only. The operator owns the gates and
            # flips them when they're ready; the bot does not volunteer their
            # licensure status unsolicited.
            lines.append(_status_line("Readiness gates", checks_label, overall == "READY_FOR_LIVE_EXECUTION"))
    except Exception:
        lines.append(_status_line("Readiness gates", "unavailable", False))

    try:
        op_url = f"{state.api_base}/api/forex/dashboard"
        req = urllib.request.Request(op_url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            dashboard = json.loads(resp.read().decode())
            operability = (
                dashboard.get("terminalOperabilityVerifier")
                or dashboard.get("terminal_operability")
                or {}
            )
            op_status = str(operability.get("operability_status") or "unknown")
            lines.append(_status_line("MT5 operability", op_status, "VERIFIED" in op_status))
    except Exception:
        pass

    try:
        loop_url = f"{state.api_base}/api/forex/autonomous-loop/health"
        req = urllib.request.Request(loop_url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            loop = json.loads(resp.read().decode())
            loop_status = str(loop.get("overall_status") or "unknown")
            cycles = loop.get("cycles_today")
            label = f"{loop_status}"
            if cycles is not None:
                label = f"{loop_status} ({cycles} cycles today)"
            lines.append(_status_line("Autonomous loop", label, loop_status == "running"))
    except Exception:
        pass

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------


def execute_capability(cap: BotCapability, state: BotState) -> Tuple[bool, str]:
    """Execute a capability and return (success, output)."""
    output_lines: List[str] = []

    if cap.commands:
        for cmd in cap.commands:
            # Substitute mt5 path if present
            cmd_resolved = cmd.replace(
                r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
                state.mt5_path,
            )
            output_lines.append(f"\n$ {cmd_resolved}")
            try:
                result = subprocess.run(
                    cmd_resolved,
                    shell=True,
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                output = (result.stdout + result.stderr).strip()
                if output:
                    output_lines.append(output[:3000])
                if result.returncode != 0:
                    output_lines.append(f"(exit code: {result.returncode})")
            except subprocess.TimeoutExpired:
                output_lines.append("⚠ Command timed out after 120s")
            except Exception as exc:
                output_lines.append(f"⚠ Error: {exc}")

    elif cap.api_endpoint:
        url = f"{state.api_base}{cap.api_endpoint}"
        output_lines.append(f"\n> GET {url}")
        try:
            import urllib.request
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                output_lines.append(json.dumps(data, indent=2, default=str)[:4000])
        except Exception as exc:
            output_lines.append(f"⚠ API error: {exc}")

    elif cap.script:
        script_path = REPO_ROOT / cap.script
        cmd = f"py -3.12 {cap.script} --summary-only"
        output_lines.append(f"\n$ {cmd}")
        try:
            result = subprocess.run(
                f"py -3.12 {script_path} --summary-only",
                shell=True,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = (result.stdout + result.stderr).strip()
            if output:
                output_lines.append(output[:3000])
        except Exception as exc:
            output_lines.append(f"⚠ Error: {exc}")

    else:
        output_lines.append("⚠ No execution path defined for this capability.")

    return True, "\n".join(output_lines)


# ---------------------------------------------------------------------------
# Bot main loop helpers
# ---------------------------------------------------------------------------


def render_greeting(state: BotState) -> str:
    """Render the greeting / top-level menu."""
    lines = [
        _header("CAS FOREX BOT — What do you want to do?", "🤖"),
        "Current Status:",
        build_status_summary(state),
        "",
        "Choose a group or type a command key:",
        "",
    ]
    for group_key in GROUP_ORDER:
        group = GROUPS[group_key]
        caps = [c for c in CAPABILITIES if c.group == group_key]
        lines.append(_option(group_key, f"{group['emoji']} {group['name']}", group['description']))
    lines.extend([
        "",
        "  [h]   Help — show all commands",
        "  [q]   Quit",
        "",
        "Type a group key (e.g., 'status') or 'h' for all commands:",
    ])
    return "\n".join(lines)


def render_group(group_key: str) -> str:
    """Render a specific capability group."""
    group = GROUPS.get(group_key)
    if not group:
        return f"Unknown group: {group_key}"

    caps = [c for c in CAPABILITIES if c.group == group_key]
    lines = [
        _header(f"{group['name']} — {group['description']}", group['emoji']),
        "",
    ]
    for cap in caps:
        lines.append(_option(cap.key, cap.label, cap.description, _danger_label(cap.danger_level)))
    lines.extend([
        "",
        "  [b]   Back to main menu",
        "  [q]   Quit",
        "",
        "Type a command key to execute, or 'b' to go back:",
    ])
    return "\n".join(lines)


def render_all_commands() -> str:
    """Render flat list of all commands."""
    lines = [
        _header("All Commands", "📋"),
        "",
    ]
    for group_key in GROUP_ORDER:
        group = GROUPS[group_key]
        caps = [c for c in CAPABILITIES if c.group == group_key]
        lines.append(f"  {group['emoji']} {group['name']}:")
        for cap in caps:
            danger = f" [{cap.danger_level.upper()}]" if cap.danger_level != "safe" else ""
            lines.append(f"    [{cap.key}] {cap.label}{danger}")
        lines.append("")
    lines.extend([
        "  [b]   Back to main menu",
        "  [q]   Quit",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def find_capability(key: str) -> Optional[BotCapability]:
    """Find a capability by its key."""
    key_lower = key.lower().strip()
    for cap in CAPABILITIES:
        if cap.key.lower() == key_lower:
            return cap
    return None


def find_group(key: str) -> Optional[str]:
    """Find a group key by partial match."""
    key_lower = key.lower().strip()
    for gk in GROUP_ORDER:
        if gk.startswith(key_lower):
            return gk
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _ensure_utf8_console() -> None:
    """Reconfigure stdout/stderr to UTF-8 so emoji rendering does not crash
    Windows cp1252 consoles. ``errors='replace'`` keeps legacy terminals usable."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None) if stream is not None else None
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def run_bot_cli() -> None:
    """Run the CAS Forex Bot in interactive CLI mode."""
    _ensure_utf8_console()
    state = BotState()

    print(render_greeting(state))

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 CAS Forex Bot signing off.")
            break

        if not raw:
            continue

        cmd = raw.lower()

        # Global commands
        if cmd in ("q", "quit", "exit"):
            print("👋 CAS Forex Bot signing off.")
            break
        if cmd in ("b", "back"):
            state.current_group = None
            state.confirm_pending = None
            print(render_greeting(state))
            continue
        if cmd in ("h", "help"):
            print(render_all_commands())
            continue

        # Confirmation flow
        if state.confirm_pending:
            if cmd in ("y", "yes"):
                cap = find_capability(state.confirm_pending)
                if cap:
                    print(f"\n⚡ Executing: {cap.label}...")
                    success, output = execute_capability(cap, state)
                    print(output)
                    state.last_result = {"success": success, "output": output}
                state.confirm_pending = None
                print(render_greeting(state) if not state.current_group else render_group(state.current_group))
                continue
            elif cmd in ("n", "no"):
                print("Cancelled.")
                state.confirm_pending = None
                print(render_greeting(state) if not state.current_group else render_group(state.current_group))
                continue

        # Group navigation
        group = find_group(cmd)
        if group:
            state.current_group = group
            print(render_group(group))
            continue

        # Capability execution
        cap = find_capability(cmd)
        if cap:
            if cap.requires_confirm:
                state.confirm_pending = cap.key
                print(f"\n⚠ {cap.label} requires confirmation.")
                print(f"   {cap.description}")
                print(f"   Danger level: {cap.danger_level}")
                print(f"\n   Confirm? [y] Yes  [n] No")
                continue

            print(f"\n⚡ Executing: {cap.label}...")
            success, output = execute_capability(cap, state)
            print(output)
            state.last_result = {"success": success, "output": output}
            state.last_capability = cap.key
            print(render_greeting(state) if not state.current_group else render_group(state.current_group))
            continue

        print(f"Unknown command: '{raw}'. Type 'h' for help or 'b' to go back.")


if __name__ == "__main__":
    run_bot_cli()
