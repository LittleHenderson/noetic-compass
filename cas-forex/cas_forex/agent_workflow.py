"""Agentic trading-day workflow plan for CAS Forex.

This module does not run the broker or provider bridge itself. It defines the
contract the downstream runtime should execute: when the desk wakes, which
agents exist, what evidence they must read, how often they act, and what they
write back before approved intents continue into guarded autonomous dispatch.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "agent_workflow"
FOREX_FURY_REPLAY_RESULTS_DIR = REPO_ROOT / "evidence_runs" / "forex_fury_replay_results"

CLAIM_BOUNDARY = (
    "Agent workflow plan coordinates CAS Forex autowake, scalp, intraday, "
    "overseer, research, terminal-bridge, and memory agents. It creates "
    "schedules, route intents, research tasks, and evidence requirements; it "
    "does not by itself execute live broker orders, create broker ACCEPT, "
    "deposit, withdraw, move bank/card funds, or automate payouts. Those "
    "side effects occur only when approved intents continue through "
    "order_dispatch.py, execution_guard.py, broker/provider truth, risk, "
    "receipt, and kill-switch gates inside owner-delegated authority."
)


class AgentWorkflowPlanError(ValueError):
    """Raised when an agent workflow plan cannot be loaded or validated."""


def build_agent_workflow_plan(
    *,
    forex_fury_replay_results: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the CAS Forex trading-day agent workflow plan."""

    replay = dict(forex_fury_replay_results or _read_latest_optional(
        FOREX_FURY_REPLAY_RESULTS_DIR,
        "forex-fury-replay-results-*-report.json",
    ))
    replay_highlight = _replay_highlight(replay)

    knowledge_pack = _knowledge_pack(replay)
    agent_roster = _agent_roster(replay_highlight)
    autowake = _autowake_schedule()
    thirty_day_window = _thirty_day_window(replay_highlight)

    payload = {
        "report_kind": "cas_forex_agent_workflow_plan",
        "created_at": datetime.now(UTC).isoformat(),
        "workflow_status": "AGENT_DESK_PLAN_READY",
        "current_execution_mode": "AI_FULL_AUTO_PAPER",
        "target_execution_mode": "OWNER_CONTROLLED_LIVE_MONEY_AGENT_DESK",
        "claim_boundary": CLAIM_BOUNDARY,
        "summary": {
            "agent_count": len(agent_roster),
            "autowake_event_count": len(autowake["events"]),
            "micro_scalp_cadence_minutes": "1-5",
            "hourly_intraday_cadence_minutes": 60,
            "thirty_day_window_days": 30,
            "primary_replay_lead": replay_highlight.get("lead_label"),
            "primary_replay_verdict": replay_highlight.get("replay_verdict"),
            "adaptive_next_step": replay_highlight.get("adaptive_compounding_next_step"),
        },
        "autowake_schedule": autowake,
        "agent_roster": agent_roster,
        "coordination_model": _coordination_model(),
        "knowledge_pack": knowledge_pack,
        "thirty_day_window": thirty_day_window,
        "implementation_queue": _implementation_queue(),
        "source_reports": {
            "forex_fury_replay_results": _source_ref(replay),
        },
        "live_execution_boundary": {
            "live_trading_status": "OWNER_ARMING_REQUIRED",
            "broker_accept_status": "OWNER_ARMING_REQUIRED",
            "auto_deposit_status": "OWNER_AND_PROVIDER_PENDING",
            "debit_card_bank_movement_status": "OWNER_AND_PROVIDER_PENDING",
            "payout_automation_status": "OWNER_AND_PROVIDER_PENDING",
            "owner_runtime_authorization_required": True,
            "autonomous_execution_path": [
                "agent route intents",
                "order_dispatch.py",
                "execution_guard.py",
                "broker or provider bridge",
                "receipt and ledger reconciliation",
            ],
            "plain_english": (
                "This plan tells the agents how to wake up, analyze, propose, "
                "compound, close, research, and record trades. Once the owner "
                "arms live or money authority, approved intents may execute "
                "autonomously through order_dispatch.py, execution_guard.py, "
                "broker truth, risk, provider, receipt, and kill-switch gates."
            ),
        },
    }
    validate_agent_workflow_plan(payload)
    return payload


def write_agent_workflow_plan_report(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Path]:
    """Write JSON and Markdown workflow-plan artifacts."""

    report = build_agent_workflow_plan()
    target_dir = output_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"agent-workflow-plan-{stamp}-report.json"
    md_path = target_dir / f"agent-workflow-plan-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_agent_workflow_plan_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_agent_workflow_plan_report(report_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """Load the newest generated workflow-plan report."""

    payload = _read_latest(report_dir, "agent-workflow-plan-*-report.json")
    validate_agent_workflow_plan(payload)
    return payload


def validate_agent_workflow_plan(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "workflow_status",
        "claim_boundary",
        "summary",
        "autowake_schedule",
        "agent_roster",
        "knowledge_pack",
        "implementation_queue",
    }
    missing = required.difference(payload)
    if missing:
        raise AgentWorkflowPlanError(f"agent workflow plan missing fields: {sorted(missing)}")
    if payload.get("report_kind") != "cas_forex_agent_workflow_plan":
        raise AgentWorkflowPlanError("unexpected agent workflow report_kind")

    agent_ids = {str(agent.get("agent_id")) for agent in payload.get("agent_roster", []) if isinstance(agent, dict)}
    required_agents = {
        "session_autowake_agent",
        "micro_scalp_agent",
        "hourly_intraday_agent",
        "overseer_agent",
        "research_condition_agent",
        "strategy_dev_agent",
        "terminal_bridge_agent",
        "audit_memory_agent",
    }
    missing_agents = required_agents.difference(agent_ids)
    if missing_agents:
        raise AgentWorkflowPlanError(f"agent workflow plan missing agents: {sorted(missing_agents)}")
    if "does not by itself execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise AgentWorkflowPlanError("agent workflow claim boundary must preserve execution boundary")


def render_agent_workflow_plan_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    autowake = report.get("autowake_schedule") or {}
    lines = [
        "# CAS Forex Agentic Trading-Day Workflow Plan",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('workflow_status')}`",
        f"Current mode: `{report.get('current_execution_mode')}`",
        f"Target mode: `{report.get('target_execution_mode')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Agents: `{summary.get('agent_count')}`",
        f"- Autowake events: `{summary.get('autowake_event_count')}`",
        f"- Micro-scalp cadence: `{summary.get('micro_scalp_cadence_minutes')}` minutes",
        f"- Hourly intraday cadence: `{summary.get('hourly_intraday_cadence_minutes')}` minutes",
        f"- Primary replay lead: `{summary.get('primary_replay_lead')}`",
        f"- Replay verdict: `{summary.get('primary_replay_verdict')}`",
        f"- Adaptive next step: `{summary.get('adaptive_next_step')}`",
        "",
        "## Autowake",
        "",
        f"- Market week: `{autowake.get('market_week')}`",
        f"- Timezone policy: {autowake.get('timezone_policy')}",
        "",
    ]
    for event in autowake.get("events") or []:
        lines.append(
            "- "
            f"`{event.get('event_id')}` at `{event.get('trigger')}` -> "
            f"`{event.get('action')}` ({event.get('purpose')})"
        )

    lines.extend(["", "## Agents", ""])
    for agent in report.get("agent_roster") or []:
        lines.extend(
            [
                f"### `{agent.get('agent_id')}`",
                "",
                f"- Role: {agent.get('role')}",
                f"- Cadence: {agent.get('cadence')}",
                f"- Timeframes: `{', '.join(agent.get('timeframes') or [])}`",
                f"- Decisions: `{', '.join(agent.get('decision_outputs') or [])}`",
                f"- Writes: `{', '.join(agent.get('memory_writes') or [])}`",
                "",
            ]
        )

    lines.extend(["## Implementation Queue", ""])
    for item in report.get("implementation_queue") or []:
        lines.append(
            "- "
            f"`{item.get('priority')}` `{item.get('item_id')}`: "
            f"{item.get('plain_english')} -> `{item.get('target_file')}`"
        )
    return "\n".join(lines) + "\n"


def _agent_roster(replay_highlight: Mapping[str, Any]) -> List[Dict[str, Any]]:
    lead_label = str(replay_highlight.get("lead_label") or "no replay lead loaded")
    return [
        {
            "agent_id": "session_autowake_agent",
            "role": "Wake the CAS Forex desk when FX trading is about to begin.",
            "cadence": "FX week open, each major session preopen, and every 60 seconds while market is active.",
            "timeframes": ["tick", "M1", "M5"],
            "primary_inputs": [
                "broker terminal heartbeat",
                "market open/session calendar",
                "spread/slippage snapshot",
                "macro/event context",
                "latest runtime gates",
            ],
            "decision_outputs": [
                "WAKE_TRADING_DESK",
                "STANDBY",
                "PAUSE_FOR_SPREAD",
                "PAUSE_FOR_EVENT",
            ],
            "memory_writes": ["session_state", "autowake_receipt", "spread_snapshot"],
            "plain_english": "This is the alarm clock plus pre-flight check. It wakes the other agents only when the market desk should be alive.",
        },
        {
            "agent_id": "micro_scalp_agent",
            "role": "Scalp small wins that can add up by the end of the trading day.",
            "cadence": "Every 1-5 minutes while an approved session is active.",
            "timeframes": ["M1", "M5"],
            "primary_inputs": [
                lead_label,
                "live or demo quotes",
                "spread/slippage snapshot",
                "open basket state",
                "condition-lab cells",
                "walk-forward summary",
            ],
            "decision_outputs": [
                "OPEN_MICRO_SCALP",
                "ADD_TO_WINNER",
                "TIGHTEN_STOP",
                "CLOSE_FOR_SMALL_PROFIT",
                "NO_TRADE",
            ],
            "memory_writes": ["scalp_route_intent", "winning_condition_snapshot", "basket_outcome"],
            "plain_english": "This is the fast worker: it looks for tiny high-frequency edges, compounds winners when evidence still supports the move, and records what worked.",
        },
        {
            "agent_id": "hourly_intraday_agent",
            "role": "Trade larger intraday moves on hourly rhythm without fighting the scalper.",
            "cadence": "Top of every hour and after each completed H1 candle.",
            "timeframes": ["M15", "H1"],
            "primary_inputs": [
                "condition tally H1 buckets",
                "walk-forward routes",
                "market movement stream",
                "micro-scalp exposure map",
                "macro/event context",
            ],
            "decision_outputs": [
                "OPEN_INTRADAY_ROUTE",
                "HOLD_INTRADAY_ROUTE",
                "SCALE_INTRADAY_WINNER",
                "CLOSE_INTRADAY_ROUTE",
                "NO_TRADE",
            ],
            "memory_writes": ["hourly_route_intent", "intraday_condition_snapshot", "intraday_outcome"],
            "plain_english": "This worker checks the bigger hourly picture so the system is not only hunting pennies while missing cleaner intraday moves.",
        },
        {
            "agent_id": "overseer_agent",
            "role": "Coordinate all trading agents and decide which proposals are allowed to become route intents.",
            "cadence": "Every proposal, every basket change, and every 60 seconds while active.",
            "timeframes": ["tick", "M1", "M5", "M15", "H1", "D1"],
            "primary_inputs": [
                "all agent proposals",
                "runtime gates",
                "account ledger",
                "movement stream",
                "drawdown and margin state",
                "broker terminal heartbeat",
            ],
            "decision_outputs": [
                "APPROVE_ROUTE_INTENT",
                "REJECT_ROUTE_INTENT",
                "SCALE_DOWN_ROUTE_INTENT",
                "HALT_AGENT_DESK",
            ],
            "must_reject_conditions": [
                "proposal conflicts with current exposure",
                "spread/slippage is outside the route evidence range",
                "drawdown or margin limits are exceeded",
                "market/session state is invalid for the strategy",
                "required evidence refs are missing",
            ],
            "memory_writes": ["overseer_decision", "rejection_reason", "approved_route_packet"],
            "plain_english": "This is the desk manager. It can reject and must reject bad proposals, but its normal job is to let good proposals through cleanly.",
        },
        {
            "agent_id": "research_condition_agent",
            "role": "Continuously find conditions and timeframes that produce better profit.",
            "cadence": "Continuous during off-peak cycles; refresh after each trading day.",
            "timeframes": ["M1", "M5", "M15", "H1", "D1"],
            "primary_inputs": [
                "condition lab",
                "walk-forward grid",
                "Forex Fury set/report imports",
                "trade outcome memory",
                "market regime history",
            ],
            "decision_outputs": [
                "QUEUE_CONDITION_REPLAY",
                "PROMOTE_RESEARCH_LEAD",
                "DEMOTE_WEAK_ROUTE",
                "REQUEST_MORE_DATA",
            ],
            "memory_writes": ["condition_tally_update", "walk_forward_update", "research_candidate"],
            "plain_english": "This worker is the lab. It keeps hunting stronger setups, especially on shorter timeframes.",
        },
        {
            "agent_id": "strategy_dev_agent",
            "role": "Turn research findings into testable strategy variants.",
            "cadence": "After new condition-lab or replay results are written.",
            "timeframes": ["M1", "M5", "M15", "H1"],
            "primary_inputs": [
                "research candidates",
                "strategy_leads.json",
                "external benchmarks",
                "Forex Fury replay results",
                "adaptive compounding reviews",
            ],
            "decision_outputs": [
                "PROPOSE_STRATEGY_VARIANT",
                "QUEUE_BACKTEST",
                "QUEUE_WALK_FORWARD",
                "KEEP_ON_WATCHLIST",
            ],
            "memory_writes": ["strategy_variant", "backtest_request", "promotion_note"],
            "plain_english": "This worker converts raw discoveries into strategy jobs the rest of CAS Forex can test.",
        },
        {
            "agent_id": "terminal_bridge_agent",
            "role": "Connect route intents to MT4/MT5 paper/demo receipts and future live bridge commands.",
            "cadence": "Every approved route intent and every terminal heartbeat interval.",
            "timeframes": ["tick", "M1", "M5", "M15", "H1"],
            "primary_inputs": [
                "approved route packets",
                "MT4 mailbox bridge",
                "MT5 receipt/probe status",
                "broker account snapshot",
            ],
            "decision_outputs": [
                "WRITE_PAPER_COMMAND",
                "READ_TERMINAL_RECEIPT",
                "RECONCILE_POSITION",
                "FLAG_BRIDGE_MISMATCH",
            ],
            "memory_writes": ["terminal_command_receipt", "broker_reconciliation_snapshot"],
            "plain_english": "This is the runner between CAS Forex and the trading terminal. It handles receipts so the agents know what actually happened.",
        },
        {
            "agent_id": "audit_memory_agent",
            "role": "Make every decision learnable by saving conditions, outcomes, and hashes.",
            "cadence": "Every route decision, close decision, replay result, and end-of-day rollup.",
            "timeframes": ["all"],
            "primary_inputs": [
                "approved and rejected route packets",
                "closed trade outcomes",
                "daily bundle",
                "hash chain status",
                "thirty-day objective",
            ],
            "decision_outputs": [
                "WRITE_MEMORY_SNAPSHOT",
                "UPDATE_30_DAY_LEDGER",
                "FLAG_EVIDENCE_GAP",
            ],
            "memory_writes": ["winning_condition_snapshot", "losing_condition_snapshot", "daily_agent_desk_rollup"],
            "plain_english": "This worker is the memory. It saves what won, what failed, and what the system should study next.",
        },
    ]


def _autowake_schedule() -> Dict[str, Any]:
    return {
        "market_week": "Sunday 17:00 America/New_York through Friday 17:00 America/New_York",
        "timezone_policy": (
            "Use America/New_York as the human schedule reference, then cross-check broker server time "
            "and market quote freshness before waking agents."
        ),
        "events": [
            {
                "event_id": "FX_WEEK_OPEN_PRECHECK",
                "trigger": "Sunday 16:55 America/New_York",
                "action": "WAKE_TRADING_DESK",
                "purpose": "Start terminal heartbeat, quote freshness checks, spread checks, and evidence loading before weekly open.",
            },
            {
                "event_id": "SYDNEY_TOKYO_SESSION_SCOUT",
                "trigger": "Daily Asian-session preopen window",
                "action": "WAKE_SESSION_SCOUT",
                "purpose": "Find early-session conditions and decide whether micro-scalping should be active.",
            },
            {
                "event_id": "LONDON_PREOPEN_SCOUT",
                "trigger": "Daily London preopen window",
                "action": "WAKE_SESSION_SCOUT",
                "purpose": "Check spread, volatility, and condition buckets before the London liquidity window.",
            },
            {
                "event_id": "NEW_YORK_PREOPEN_SCOUT",
                "trigger": "Daily New York preopen window",
                "action": "WAKE_SESSION_SCOUT",
                "purpose": "Check US-session volatility, news context, and open basket exposure.",
            },
            {
                "event_id": "MICRO_SCALP_LOOP",
                "trigger": "Every 1-5 minutes while a session is approved",
                "action": "RUN_MICRO_SCALP_AGENT",
                "purpose": "Look for small profit captures, add-to-winner opportunities, and quick close conditions.",
            },
            {
                "event_id": "HOURLY_INTRADAY_LOOP",
                "trigger": "Top of every hour after the H1 candle boundary",
                "action": "RUN_HOURLY_INTRADAY_AGENT",
                "purpose": "Evaluate M15/H1 route opportunities and avoid conflict with micro-scalp baskets.",
            },
            {
                "event_id": "END_OF_DAY_MEMORY_ROLLUP",
                "trigger": "End of broker trading day",
                "action": "RUN_AUDIT_MEMORY_AGENT",
                "purpose": "Save winning/losing conditions, update the 30-day window, and queue research jobs.",
            },
        ],
    }


def _coordination_model() -> Dict[str, Any]:
    return {
        "proposal_flow": [
            "session_autowake_agent wakes the desk and marks the session active or standby",
            "micro_scalp_agent and hourly_intraday_agent produce route intents",
            "overseer_agent approves, rejects, scales down, or halts route intents",
            "terminal_bridge_agent converts approved route intents into terminal bridge commands and receipts",
            "audit_memory_agent stores decisions, outcomes, and condition snapshots",
            "research_condition_agent and strategy_dev_agent use that memory to improve the next trading day",
        ],
        "conflict_rules": [
            "micro_scalp_agent cannot add exposure that fights an active hourly route",
            "hourly_intraday_agent must see current micro-scalp basket exposure before opening",
            "overseer_agent is the only agent allowed to approve a route intent",
            "terminal_bridge_agent only acts on overseer-approved route packets",
            "audit_memory_agent records both approvals and rejections for future analysis",
        ],
        "llm_context_bootstrap": [
            "Load the knowledge_pack paths before each agent starts.",
            "Load the latest dashboard API state before every proposal.",
            "Every agent output must name its evidence_refs and the condition snapshot it relied on.",
        ],
    }


def _knowledge_pack(replay: Mapping[str, Any]) -> List[Dict[str, Any]]:
    replay_path = (replay.get("report_path") or "evidence_runs/forex_fury_replay_results/").replace("\\", "/")
    return [
        {
            "path": "strategy_leads.json",
            "purpose": "Current strategy lead ledger and open gates.",
            "required_by": ["overseer_agent", "research_condition_agent", "strategy_dev_agent"],
        },
        {
            "path": replay_path,
            "purpose": "Latest Forex Fury-derived replay result and adaptive compounding queue signal.",
            "required_by": ["micro_scalp_agent", "hourly_intraday_agent", "research_condition_agent"],
        },
        {
            "path": "evidence_runs/forex_fury_replay_candidates/",
            "purpose": "Ranked short-timeframe candidates converted from Forex Fury set/report evidence.",
            "required_by": ["research_condition_agent", "strategy_dev_agent"],
        },
        {
            "path": "evidence_runs/forex_fury_condition_replay/",
            "purpose": "Condition-lab replay cells for M1/M5/M15/H1 route selection.",
            "required_by": ["micro_scalp_agent", "research_condition_agent"],
        },
        {
            "path": "evidence_runs/forex_fury_walk_forward_replay/",
            "purpose": "Walk-forward route durability and drawdown results.",
            "required_by": ["hourly_intraday_agent", "overseer_agent"],
        },
        {
            "path": "evidence_runs/index_tsmom_126_paper_proof/",
            "purpose": "Daily proof bundle, MT5 receipt, route decision, risk review, and schedule chain.",
            "required_by": ["session_autowake_agent", "terminal_bridge_agent", "audit_memory_agent"],
        },
        {
            "path": "docs/working/CAS_FOREX_LLM_HANDOFF_TODO_GOALS_20260623.md",
            "purpose": "Project handoff, feature map, and next implementation goals.",
            "required_by": ["all_agents"],
        },
        {
            "path": "docs/working/cas_harness_production_todo.md",
            "purpose": "Canonical project dashboard and current status.",
            "required_by": ["all_agents"],
        },
    ]


def _thirty_day_window(replay_highlight: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "objective": (
            "Use a 30-day trading window to accumulate small daily profits, test hourly/intraday routes, "
            "save every winning and losing condition, and promote only the routes that hold up under evidence."
        ),
        "primary_short_timeframe_lead": replay_highlight.get("lead_label"),
        "daily_outputs": [
            "autowake receipt",
            "micro-scalp route intents",
            "hourly intraday route intents",
            "overseer approvals and rejections",
            "terminal receipts",
            "winning condition snapshots",
            "losing condition snapshots",
            "end-of-day agent desk rollup",
        ],
        "promotion_criteria": [
            "route shows positive net outcome after spread/slippage and commission",
            "drawdown stays inside owner-selected cap",
            "condition repeats across more than one session or walk-forward window",
            "overseer rejection reasons decrease over time",
            "terminal receipts reconcile with internal ledger",
        ],
    }


def _implementation_queue() -> List[Dict[str, Any]]:
    return [
        {
            "priority": 1,
            "item_id": "agent_state_store",
            "plain_english": "Create the persistent state file/database for agent heartbeats, route intents, approvals, rejections, and memory snapshots.",
            "target_file": "cas_forex/agent_state.py",
        },
        {
            "priority": 2,
            "item_id": "autowake_runner",
            "plain_english": "Build the runner that wakes CAS Forex at market/session open and starts the agent loops.",
            "target_file": "scripts/run_agent_workflow_queue.py",
        },
        {
            "priority": 3,
            "item_id": "micro_scalp_policy",
            "plain_english": "Convert the AUD/CAD M5 replay lead into a micro-scalp policy with add-to-winner and close-for-small-profit rules.",
            "target_file": "cas_forex/micro_scalp_policy.py",
        },
        {
            "priority": 4,
            "item_id": "hourly_intraday_policy",
            "plain_english": "Add H1/M15 route selection that coordinates with active micro-scalp baskets.",
            "target_file": "cas_forex/hourly_intraday_policy.py",
        },
        {
            "priority": 5,
            "item_id": "overseer_router",
            "plain_english": "Make one approval layer that accepts, rejects, scales down, or halts proposals from all trading agents.",
            "target_file": "cas_forex/agent_overseer.py",
        },
        {
            "priority": 6,
            "item_id": "terminal_bridge_receipts",
            "plain_english": "Attach approved route packets to MT4/MT5 paper/demo receipts, then later the live bridge when runtime authorization is configured.",
            "target_file": "cas_forex/broker/mt4_mailbox_bridge.py",
        },
        {
            "priority": 7,
            "item_id": "agent_ui_console",
            "plain_english": "Add a cockpit page/panel for agent health, wake status, current intents, approvals, rejections, and memory rollups.",
            "target_file": "ui/src/pages/OptimizerPage.tsx",
        },
    ]


def _replay_highlight(replay: Mapping[str, Any]) -> Dict[str, Any]:
    condition = replay.get("condition_summary") if isinstance(replay, Mapping) else {}
    if not isinstance(condition, Mapping):
        condition = {}
    top_cells = condition.get("top_condition_cells") or []
    top_cell = next((cell for cell in top_cells if isinstance(cell, Mapping)), {})
    symbol = top_cell.get("symbol") or "AUD/CAD"
    timeframe = top_cell.get("timeframe") or "M5"
    setting = top_cell.get("setting") or "range_scalper_12_80"
    return {
        "lead_label": f"{symbol} {timeframe} {setting}",
        "symbol": symbol,
        "timeframe": timeframe,
        "setting": setting,
        "replay_verdict": replay.get("replay_verdict") or "REPLAY_RESULTS_NOT_LOADED",
        "adaptive_compounding_next_step": replay.get("adaptive_compounding_next_step") or "LOAD_REPLAY_RESULTS",
        "profit_factor": top_cell.get("profit_factor"),
        "mean_return_pct": top_cell.get("mean_return_pct"),
        "win_rate": top_cell.get("win_rate"),
    }


def _read_latest_optional(report_dir: Path, pattern: str) -> Dict[str, Any]:
    try:
        return _read_latest(report_dir, pattern)
    except AgentWorkflowPlanError:
        return {}


def _read_latest(report_dir: Path, pattern: str) -> Dict[str, Any]:
    files = sorted(report_dir.glob(pattern))
    if not files:
        raise AgentWorkflowPlanError(f"No reports found for {pattern} in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1].relative_to(REPO_ROOT))
    return payload


def _source_ref(report: Mapping[str, Any]) -> Dict[str, Any]:
    path = report.get("report_path")
    return {
        "report_kind": report.get("report_kind"),
        "path": path,
        "sha256": _file_sha256(REPO_ROOT / str(path)) if path else None,
        "status": "loaded" if path else "missing",
    }


def _file_sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
