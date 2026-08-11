"""Walk the CAS Forex agent's reasoning chain for the LATEST decision.

The CAS Forex agent cycle trades autonomously on the operator's behalf in order
to REMOVE detrimental trading psychology (anxiety, in-the-moment emotional
decisions) from the operator's loop. The LLM cockpit bot's role is to help the
operator UNDERSTAND what the agent did, never to recommend new trades.

`explain_latest_agent_decision` takes already-parsed evidence dicts (NOT files)
and returns a structured `AgentDecisionExplanation` that walks the agent's
reasoning chain in order:

    1. Strategy lead chosen (from a strategy-dev queue or strategy-leads dict).
    2. Walk-forward evidence (the score/verdict that justified the lead).
    3. PCBA gate verdict (approve or block, with reason).
    4. Cycle decision (symbol, direction, entry/SL/TP, lot, cycle_id).
    5. Execution outcome (broker ticket + close P&L, or blocked reason).
    6. Plain-English summary the bot can surface verbatim.

The function NEVER fabricates: if a chain step's input is absent, the step's
status is "missing" and its detail names the input that would unlock it. The
plain-English summary is explanation-only — it never advises the operator
about a future trade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple


__all__ = [
    "AgentDecisionExplanation",
    "DecisionChainStep",
    "explain_latest_agent_decision",
]


_STEP_STRATEGY = "strategy_lead"
_STEP_WALK_FORWARD = "walk_forward_evidence"
_STEP_PCBA = "pcba_gate_verdict"
_STEP_CYCLE = "cycle_decision"
_STEP_EXECUTION = "execution_outcome"

_STATUS_FOUND = "found"
_STATUS_MISSING = "missing"
_STATUS_BLOCKED = "blocked"

_OVERALL_NO_DECISION = "no_recent_decision"
_OVERALL_EXECUTED = "executed"
_OVERALL_APPROVED_NOT_EXECUTED = "approved_not_executed"
_OVERALL_BLOCKED = "blocked"


@dataclass(frozen=True)
class DecisionChainStep:
    """One link in the agent's reasoning chain for a single decision."""

    name: str
    headline: str
    detail: str
    evidence: Tuple[str, ...] = field(default_factory=tuple)
    status: str = _STATUS_FOUND


@dataclass(frozen=True)
class AgentDecisionExplanation:
    """Structured explanation of the agent's most recent decision."""

    cycle_id: Optional[str]
    overall_status: str
    plain_english_summary: str
    chain: Tuple[DecisionChainStep, ...]
    next_action_hint: Optional[str] = None
    movement_source_truth: Mapping[str, Any] | None = None
    version_trace: Mapping[str, Any] = field(default_factory=dict)


def explain_latest_agent_decision(
    *,
    agent_cycle_report: Optional[Mapping[str, Any]] = None,
    agent_memory_report: Optional[Mapping[str, Any]] = None,
    daily_learning_rollup: Optional[Mapping[str, Any]] = None,
    strategy_dev_queue_report: Optional[Mapping[str, Any]] = None,
    strategy_leads: Optional[Mapping[str, Any]] = None,
    walk_forward_report: Optional[Mapping[str, Any]] = None,
    pcba_report: Optional[Mapping[str, Any]] = None,
    movement_source_truth: Optional[Mapping[str, Any]] = None,
) -> AgentDecisionExplanation:
    """Walk the latest agent decision into an explanation the bot can surface.

    All arguments are already-parsed dicts. The function does not read from
    disk and does not fabricate evidence. Any chain step whose input is
    absent is reported with ``status="missing"`` and a detail that names the
    input that would unlock it.
    """

    # ---- 0. No cycle at all? Bail out early with a clean structured no-op.
    if not agent_cycle_report:
        empty_chain = (
            DecisionChainStep(
                name=_STEP_STRATEGY,
                headline="No strategy lead recorded.",
                detail=(
                    "No agent cycle report was provided, so there is no past "
                    "decision to explain. Run an agent cycle (agent_workflow) "
                    "to produce a cycle report, then re-ask."
                ),
                status=_STATUS_MISSING,
            ),
            DecisionChainStep(
                name=_STEP_WALK_FORWARD,
                headline="No walk-forward evidence available.",
                detail="A walk-forward replay report is required to justify a strategy lead.",
                status=_STATUS_MISSING,
            ),
            DecisionChainStep(
                name=_STEP_PCBA,
                headline="No PCBA gate verdict available.",
                detail="A PCBA review report is required to confirm or block a route intent.",
                status=_STATUS_MISSING,
            ),
            DecisionChainStep(
                name=_STEP_CYCLE,
                headline="No agent cycle decision found.",
                detail="An agent cycle report containing a route intent is required.",
                status=_STATUS_MISSING,
            ),
            DecisionChainStep(
                name=_STEP_EXECUTION,
                headline="No execution outcome available.",
                detail="A broker receipt or blocked-execution reason is required.",
                status=_STATUS_MISSING,
            ),
        )
        return AgentDecisionExplanation(
            cycle_id=None,
            overall_status=_OVERALL_NO_DECISION,
            plain_english_summary=(
                "There is no recent agent decision on record to explain. "
                "Run an agent cycle so the desk has a route intent, overseer "
                "decision, and execution receipt to walk through."
            ),
            chain=empty_chain,
            next_action_hint=(
                "Trigger run_agent_workflow_cycle to produce an "
                "agent-workflow-cycle report, then re-ask."
            ),
            movement_source_truth=_compact_movement_source_truth(movement_source_truth),
            version_trace=_empty_version_trace(
                "NO_AGENT_CYCLE",
                gaps=(
                    "agent_cycle_report_missing",
                    "strategy_ref_not_attached",
                    "model_ref_not_attached",
                    "prompt_version_not_attached",
                    "risk_engine_version_not_attached",
                    "market_data_source_not_attached",
                    "config_hash_not_attached",
                ),
            ),
        )

    cycle_id = _coerce_str(agent_cycle_report.get("cycle_id"))
    intent, decision = _pick_focus_intent(agent_cycle_report)

    # ---- 1. Strategy lead chosen.
    strategy_step = _build_strategy_step(
        intent=intent,
        strategy_dev_queue_report=strategy_dev_queue_report,
        strategy_leads=strategy_leads,
        daily_learning_rollup=daily_learning_rollup,
    )

    # ---- 2. Walk-forward evidence.
    walk_forward_step = _build_walk_forward_step(
        intent=intent,
        walk_forward_report=walk_forward_report,
        daily_learning_rollup=daily_learning_rollup,
    )

    # ---- 3. PCBA gate verdict (PCBA gate also signals overall block).
    pcba_step, pcba_blocked = _build_pcba_step(
        intent=intent,
        decision=decision,
        pcba_report=pcba_report,
    )

    # ---- 4. Cycle decision.
    cycle_step = _build_cycle_step(
        cycle_id=cycle_id,
        intent=intent,
        decision=decision,
    )

    # ---- 5. Execution outcome.
    execution_step, executed = _build_execution_step(
        intent=intent,
        decision=decision,
        agent_cycle_report=agent_cycle_report,
        agent_memory_report=agent_memory_report,
    )

    chain: Tuple[DecisionChainStep, ...] = (
        strategy_step,
        walk_forward_step,
        pcba_step,
        cycle_step,
        execution_step,
    )

    overall_status, next_hint = _resolve_overall_status(
        intent=intent,
        decision=decision,
        pcba_blocked=pcba_blocked,
        executed=executed,
        execution_step=execution_step,
    )

    summary = _build_plain_english_summary(
        cycle_id=cycle_id,
        overall_status=overall_status,
        intent=intent,
        decision=decision,
        strategy_step=strategy_step,
        walk_forward_step=walk_forward_step,
        pcba_step=pcba_step,
        execution_step=execution_step,
    )
    version_trace = _build_agent_version_trace(
        agent_cycle_report=agent_cycle_report,
        intent=intent,
        decision=decision,
    )

    return AgentDecisionExplanation(
        cycle_id=cycle_id,
        overall_status=overall_status,
        plain_english_summary=summary,
        chain=chain,
        next_action_hint=next_hint,
        movement_source_truth=_compact_movement_source_truth(movement_source_truth),
        version_trace=version_trace,
    )


# ---------------------------------------------------------------------------
# Intent / decision picking
# ---------------------------------------------------------------------------


def _pick_focus_intent(
    cycle_report: Mapping[str, Any],
) -> Tuple[Optional[Mapping[str, Any]], Optional[Mapping[str, Any]]]:
    """Pick the most representative intent + decision from a cycle report.

    Preference order:
      1. Approved + executed intent (broker ticket present in terminal commands).
      2. Approved intent (overseer approved=True).
      3. First rejected intent.
      4. First intent in the report regardless of decision.
    """

    intents = [item for item in (cycle_report.get("route_intents") or []) if isinstance(item, Mapping)]
    decisions = [item for item in (cycle_report.get("overseer_decisions") or []) if isinstance(item, Mapping)]
    if not intents:
        return None, None

    decision_by_intent = {
        _coerce_str(d.get("intent_id")): d for d in decisions if _coerce_str(d.get("intent_id"))
    }
    terminal_commands = [
        item for item in (cycle_report.get("terminal_commands") or []) if isinstance(item, Mapping)
    ]
    executed_intent_ids = {
        _coerce_str(cmd.get("intent_id"))
        for cmd in terminal_commands
        if _has_broker_ticket(cmd)
    }

    # 1. approved + executed
    for intent in intents:
        intent_id = _coerce_str(intent.get("intent_id"))
        decision = decision_by_intent.get(intent_id)
        if decision and decision.get("approved") and intent_id in executed_intent_ids:
            return intent, decision

    # 2. approved (any)
    for intent in intents:
        intent_id = _coerce_str(intent.get("intent_id"))
        decision = decision_by_intent.get(intent_id)
        if decision and decision.get("approved"):
            return intent, decision

    # 3. first rejected
    for intent in intents:
        intent_id = _coerce_str(intent.get("intent_id"))
        decision = decision_by_intent.get(intent_id)
        if decision and not decision.get("approved"):
            return intent, decision

    # 4. fallback: first intent
    first = intents[0]
    return first, decision_by_intent.get(_coerce_str(first.get("intent_id")))


# ---------------------------------------------------------------------------
# Step builders
# ---------------------------------------------------------------------------


def _build_strategy_step(
    *,
    intent: Optional[Mapping[str, Any]],
    strategy_dev_queue_report: Optional[Mapping[str, Any]],
    strategy_leads: Optional[Mapping[str, Any]],
    daily_learning_rollup: Optional[Mapping[str, Any]],
) -> DecisionChainStep:
    strategy_setting = _coerce_str(intent.get("strategy_setting")) if intent else ""
    symbol = _coerce_str(intent.get("symbol")) if intent else ""
    timeframe = _coerce_str(intent.get("timeframe")) if intent else ""
    intent_reason = _coerce_str(intent.get("reason")) if intent else ""

    evidence: list[str] = []
    if strategy_setting:
        evidence.append(f"strategy_setting={strategy_setting}")
    if symbol:
        evidence.append(f"symbol={symbol}")
    if timeframe:
        evidence.append(f"timeframe={timeframe}")
    if intent_reason:
        evidence.append(f"intent_reason={intent_reason}")

    matched_item = _find_matching_strategy_item(
        strategy_dev_queue_report=strategy_dev_queue_report,
        strategy_leads=strategy_leads,
        symbol=symbol,
        timeframe=timeframe,
        strategy_setting=strategy_setting,
    )

    if matched_item:
        item_id = _coerce_str(matched_item.get("item_id") or matched_item.get("lead_id") or "")
        hypothesis = _coerce_str(matched_item.get("hypothesis") or matched_item.get("rationale") or "")
        goal = _coerce_str(matched_item.get("plain_english_goal") or matched_item.get("plain_english") or "")
        if item_id:
            evidence.append(f"strategy_lead_id={item_id}")
        if hypothesis:
            evidence.append(f"hypothesis={hypothesis}")
        detail_bits = []
        if goal:
            detail_bits.append(goal)
        if hypothesis and hypothesis not in detail_bits:
            detail_bits.append(f"Hypothesis: {hypothesis}")
        detail = " ".join(detail_bits) or (
            f"Strategy lead {item_id or strategy_setting} was the active candidate when the cycle ran."
        )
        return DecisionChainStep(
            name=_STEP_STRATEGY,
            headline=f"Strategy lead selected: {strategy_setting or item_id or 'unknown'}.",
            detail=detail,
            evidence=tuple(evidence),
            status=_STATUS_FOUND,
        )

    if strategy_setting:
        # Intent recorded a strategy setting but we cannot find a matching lead.
        if daily_learning_rollup is not None:
            return DecisionChainStep(
                name=_STEP_STRATEGY,
                headline=f"Strategy used: {strategy_setting} (no matching lead found).",
                detail=(
                    f"The agent ran strategy `{strategy_setting}` on {symbol or 'unknown symbol'} "
                    f"{timeframe or ''}. Provide the strategy-dev queue report or strategy "
                    f"leads dict to surface the hypothesis behind this lead."
                ),
                evidence=tuple(evidence),
                status=_STATUS_FOUND,
            )
        return DecisionChainStep(
            name=_STEP_STRATEGY,
            headline=f"Strategy used: {strategy_setting} (no matching lead found).",
            detail=(
                "No strategy-dev queue report or strategy-leads dict was provided, so the "
                "underlying hypothesis cannot be quoted. Pass strategy_dev_queue_report or "
                "strategy_leads to unlock the hypothesis."
            ),
            evidence=tuple(evidence),
            status=_STATUS_MISSING,
        )

    return DecisionChainStep(
        name=_STEP_STRATEGY,
        headline="No strategy lead recorded.",
        detail=(
            "The cycle report does not name a strategy_setting on any route intent, "
            "and no strategy-dev queue / leads dict was provided."
        ),
        evidence=tuple(evidence),
        status=_STATUS_MISSING,
    )


def _build_walk_forward_step(
    *,
    intent: Optional[Mapping[str, Any]],
    walk_forward_report: Optional[Mapping[str, Any]],
    daily_learning_rollup: Optional[Mapping[str, Any]],
) -> DecisionChainStep:
    rollup_wf = None
    if daily_learning_rollup is not None:
        rollup_wf = daily_learning_rollup.get("walk_forward") or daily_learning_rollup.get(
            "walk_forward_summary"
        )

    source: Optional[Mapping[str, Any]] = None
    if isinstance(walk_forward_report, Mapping):
        source = walk_forward_report
    elif isinstance(rollup_wf, Mapping):
        source = rollup_wf

    if not source:
        return DecisionChainStep(
            name=_STEP_WALK_FORWARD,
            headline="No walk-forward evidence available.",
            detail=(
                "No walk-forward report was provided and the daily learning rollup did "
                "not carry a walk_forward summary. Pass walk_forward_report or include "
                "`walk_forward` in the daily learning rollup to unlock this step."
            ),
            status=_STATUS_MISSING,
        )

    summary = source.get("summary") if isinstance(source.get("summary"), Mapping) else source
    verdict = _coerce_str(
        summary.get("verdict")
        or summary.get("walk_forward_verdict")
        or source.get("verdict")
        or ""
    )
    score = summary.get("score") or summary.get("walk_forward_score") or source.get("score")
    sharpe = summary.get("sharpe") or source.get("sharpe")
    win_rate = summary.get("win_rate") or source.get("win_rate")
    sample_size = summary.get("sample_size") or summary.get("trade_count") or source.get("trade_count")

    evidence: list[str] = []
    if verdict:
        evidence.append(f"verdict={verdict}")
    if score is not None:
        evidence.append(f"score={score}")
    if sharpe is not None:
        evidence.append(f"sharpe={sharpe}")
    if win_rate is not None:
        evidence.append(f"win_rate={win_rate}")
    if sample_size is not None:
        evidence.append(f"sample_size={sample_size}")

    symbol = _coerce_str(intent.get("symbol")) if intent else ""
    timeframe = _coerce_str(intent.get("timeframe")) if intent else ""

    detail_bits: list[str] = []
    if verdict:
        detail_bits.append(f"Walk-forward verdict: {verdict}.")
    if score is not None:
        detail_bits.append(f"Score: {score}.")
    if sample_size is not None:
        detail_bits.append(f"Sample size: {sample_size}.")
    if symbol or timeframe:
        detail_bits.append(
            f"This walk-forward evidence justified continuing the lead on "
            f"{symbol or 'the symbol'} {timeframe or ''}.".rstrip()
        )
    detail = " ".join(detail_bits) or "Walk-forward evidence was supplied but contained no scoreable fields."

    return DecisionChainStep(
        name=_STEP_WALK_FORWARD,
        headline=(
            f"Walk-forward {verdict}." if verdict else "Walk-forward evidence found (no verdict label)."
        ),
        detail=detail,
        evidence=tuple(evidence),
        status=_STATUS_FOUND,
    )


def _build_pcba_step(
    *,
    intent: Optional[Mapping[str, Any]],
    decision: Optional[Mapping[str, Any]],
    pcba_report: Optional[Mapping[str, Any]],
) -> Tuple[DecisionChainStep, bool]:
    """Return (step, pcba_blocked_flag).

    PCBA can surface from two places: an explicit `pcba_report` dict, or as
    reasons mentioning "pcba" / "license" on the overseer decision. The
    decision's `approved=False` plus a PCBA reason is treated as blocked.
    """

    reasons: list[str] = []
    if decision and isinstance(decision.get("reasons"), Iterable):
        reasons = [_coerce_str(r) for r in decision.get("reasons") or [] if r]

    pcba_reasons = [r for r in reasons if _is_pcba_marker(r)]

    pcba_status: Optional[str] = None
    pcba_detail: Optional[str] = None
    evidence: list[str] = []

    if isinstance(pcba_report, Mapping):
        pcba_status = _coerce_str(
            pcba_report.get("verdict")
            or pcba_report.get("status")
            or pcba_report.get("gate_status")
            or ""
        )
        pcba_detail = _coerce_str(
            pcba_report.get("reason")
            or pcba_report.get("detail")
            or pcba_report.get("plain_english")
            or ""
        )
        if pcba_status:
            evidence.append(f"pcba_status={pcba_status}")
        if pcba_detail:
            evidence.append(f"pcba_reason={pcba_detail}")

    for reason in pcba_reasons:
        evidence.append(f"overseer_reason={reason}")

    approved = bool(decision.get("approved")) if decision else False
    blocked_by_pcba = bool(pcba_reasons) and not approved
    if pcba_status and pcba_status.lower() in {"blocked", "denied", "rejected", "not_licensed"}:
        blocked_by_pcba = True

    if blocked_by_pcba:
        detail = pcba_detail or (
            "PCBA gate blocked the route intent. Reasons: "
            + "; ".join(pcba_reasons or ["(no specific reason recorded)"])
        )
        return (
            DecisionChainStep(
                name=_STEP_PCBA,
                headline="PCBA gate BLOCKED this intent.",
                detail=detail,
                evidence=tuple(evidence),
                status=_STATUS_BLOCKED,
            ),
            True,
        )

    if pcba_status or pcba_detail or pcba_reasons:
        detail = pcba_detail or (
            "PCBA gate approved the route intent. "
            + ("Notes: " + "; ".join(pcba_reasons) if pcba_reasons else "")
        ).strip()
        return (
            DecisionChainStep(
                name=_STEP_PCBA,
                headline=(
                    f"PCBA gate verdict: {pcba_status}." if pcba_status else "PCBA gate approved."
                ),
                detail=detail,
                evidence=tuple(evidence),
                status=_STATUS_FOUND,
            ),
            False,
        )

    if decision is not None:
        # No explicit PCBA evidence, but overseer ran. Report what we know.
        non_pcba_reasons = [r for r in reasons if not _is_pcba_marker(r)]
        if approved:
            detail = (
                "No explicit PCBA report was provided. The overseer decision approved the "
                "intent and did not cite a PCBA gate blocker, so the PCBA gate is treated "
                "as not-blocking for this cycle."
            )
            if non_pcba_reasons:
                detail += " Overseer reasons: " + "; ".join(non_pcba_reasons) + "."
            return (
                DecisionChainStep(
                    name=_STEP_PCBA,
                    headline="PCBA gate: no explicit verdict recorded.",
                    detail=detail,
                    evidence=tuple(evidence),
                    status=_STATUS_FOUND,
                ),
                False,
            )
        # Rejected, not by PCBA — still surface as found-but-non-blocking PCBA.
        detail = (
            "No PCBA report was provided. The overseer rejected the intent for non-PCBA "
            "reasons: " + "; ".join(non_pcba_reasons or reasons or ["(no reasons recorded)"]) + "."
        )
        return (
            DecisionChainStep(
                name=_STEP_PCBA,
                headline="PCBA gate: not the blocker.",
                detail=detail,
                evidence=tuple(evidence),
                status=_STATUS_FOUND,
            ),
            False,
        )

    return (
        DecisionChainStep(
            name=_STEP_PCBA,
            headline="No PCBA gate verdict available.",
            detail=(
                "No PCBA report and no overseer decision were provided. Pass pcba_report "
                "or include an overseer decision in the agent cycle to unlock this step."
            ),
            status=_STATUS_MISSING,
        ),
        False,
    )


def _build_cycle_step(
    *,
    cycle_id: Optional[str],
    intent: Optional[Mapping[str, Any]],
    decision: Optional[Mapping[str, Any]],
) -> DecisionChainStep:
    if not intent:
        return DecisionChainStep(
            name=_STEP_CYCLE,
            headline="No agent cycle decision found.",
            detail=(
                "The cycle report contained no route intents. Run an agent cycle that "
                "produces at least one RouteIntent to unlock this step."
            ),
            status=_STATUS_MISSING,
        )

    symbol = _coerce_str(intent.get("symbol"))
    timeframe = _coerce_str(intent.get("timeframe"))
    direction = _coerce_str(intent.get("direction"))
    action = _coerce_str(intent.get("action"))
    entry = intent.get("entry_price")
    stop_loss = intent.get("stop_loss")
    take_profit = intent.get("take_profit")
    lot_size = intent.get("lot_size")
    confidence = intent.get("confidence")
    intent_id = _coerce_str(intent.get("intent_id"))

    evidence: list[str] = []
    if cycle_id:
        evidence.append(f"cycle_id={cycle_id}")
    if intent_id:
        evidence.append(f"intent_id={intent_id}")
    if symbol:
        evidence.append(f"symbol={symbol}")
    if timeframe:
        evidence.append(f"timeframe={timeframe}")
    if direction:
        evidence.append(f"direction={direction}")
    if action:
        evidence.append(f"action={action}")
    if entry is not None:
        evidence.append(f"entry={entry}")
    if stop_loss is not None:
        evidence.append(f"stop_loss={stop_loss}")
    if take_profit is not None:
        evidence.append(f"take_profit={take_profit}")
    if lot_size is not None:
        evidence.append(f"lot={lot_size}")
    if confidence is not None:
        evidence.append(f"conviction_score={_format_conviction_score(confidence)}")
    if decision:
        evidence.append(f"overseer_decision={_coerce_str(decision.get('decision'))}")
        evidence.append(f"approved={bool(decision.get('approved'))}")

    direction_or_action = direction or action or "trade"
    detail = (
        f"In cycle `{cycle_id or 'unknown'}` the agent formed intent `{intent_id or '?'}` to "
        f"{direction_or_action.lower()} {symbol or '?'} on {timeframe or '?'}"
    )
    if entry is not None:
        detail += f" with entry near {entry}"
    if stop_loss is not None:
        detail += f", stop {stop_loss}"
    if take_profit is not None:
        detail += f", target {take_profit}"
    if lot_size is not None:
        detail += f", size {lot_size}"
    detail += "."

    return DecisionChainStep(
        name=_STEP_CYCLE,
        headline=(
            f"Cycle {cycle_id or 'unknown'}: {direction_or_action} {symbol or '?'} "
            f"{timeframe or ''}".strip()
        ),
        detail=detail,
        evidence=tuple(evidence),
        status=_STATUS_FOUND,
    )


def _build_execution_step(
    *,
    intent: Optional[Mapping[str, Any]],
    decision: Optional[Mapping[str, Any]],
    agent_cycle_report: Mapping[str, Any],
    agent_memory_report: Optional[Mapping[str, Any]],
) -> Tuple[DecisionChainStep, bool]:
    if not intent:
        return (
            DecisionChainStep(
                name=_STEP_EXECUTION,
                headline="No execution outcome available.",
                detail="No route intent was present, so there is no execution outcome to walk.",
                status=_STATUS_MISSING,
            ),
            False,
        )

    intent_id = _coerce_str(intent.get("intent_id"))
    approved = bool(decision.get("approved")) if decision else False
    decision_label = _coerce_str(decision.get("decision")) if decision else ""
    reasons: list[str] = []
    if decision and isinstance(decision.get("reasons"), Iterable):
        reasons = [_coerce_str(r) for r in decision.get("reasons") or [] if r]

    terminal_commands = [
        item
        for item in (agent_cycle_report.get("terminal_commands") or [])
        if isinstance(item, Mapping) and _coerce_str(item.get("intent_id")) == intent_id
    ]
    command = terminal_commands[0] if terminal_commands else None
    receipt = command.get("terminal_receipt") if command and isinstance(command.get("terminal_receipt"), Mapping) else None

    memory_record = _find_memory_record_for_intent(agent_memory_report, intent_id)

    evidence: list[str] = []
    executed = False

    if receipt:
        ticket = receipt.get("broker_ticket")
        lifecycle = _coerce_str(receipt.get("lifecycle_status"))
        status = _coerce_str(receipt.get("status"))
        filled_price = receipt.get("filled_price")
        if ticket:
            evidence.append(f"broker_ticket={ticket}")
        if lifecycle:
            evidence.append(f"lifecycle_status={lifecycle}")
        if status:
            evidence.append(f"receipt_status={status}")
        if filled_price is not None:
            evidence.append(f"filled_price={filled_price}")
        executed = bool(ticket) and status.upper() == "EXECUTED"

    if memory_record:
        pnl = memory_record.get("profit_loss_account")
        outcome_label = _coerce_str(memory_record.get("outcome_label"))
        if pnl is not None:
            evidence.append(f"close_pnl_account={pnl}")
        if outcome_label:
            evidence.append(f"outcome_label={outcome_label}")

    if executed:
        ticket = receipt.get("broker_ticket") if receipt else None
        pnl_text = ""
        if memory_record and memory_record.get("profit_loss_account") is not None:
            pnl_text = f" Close P&L on account: {memory_record.get('profit_loss_account')}."
        return (
            DecisionChainStep(
                name=_STEP_EXECUTION,
                headline=f"Executed: broker ticket {ticket}.",
                detail=(
                    f"The approved intent `{intent_id}` was sent to the paper/demo terminal "
                    f"and a broker receipt was returned (ticket {ticket})." + pnl_text
                ),
                evidence=tuple(evidence),
                status=_STATUS_FOUND,
            ),
            True,
        )

    if approved and not receipt:
        return (
            DecisionChainStep(
                name=_STEP_EXECUTION,
                headline="Approved but no execution receipt.",
                detail=(
                    f"The overseer approved intent `{intent_id}` ({decision_label}) but no "
                    f"terminal receipt is attached. The terminal bridge may have been "
                    f"skipped or the command is still pending."
                ),
                evidence=tuple(evidence),
                status=_STATUS_FOUND,
            ),
            False,
        )

    # Not approved → blocked by overseer / validator / runtime.
    blocker_text = "; ".join(reasons) if reasons else (decision_label or "(no reason recorded)")
    return (
        DecisionChainStep(
            name=_STEP_EXECUTION,
            headline=f"Blocked before execution: {decision_label or 'rejected'}.",
            detail=(
                f"Intent `{intent_id}` was blocked before reaching the broker. Reasons: "
                f"{blocker_text}."
            ),
            evidence=tuple(evidence),
            status=_STATUS_BLOCKED,
        ),
        False,
    )


def _build_agent_version_trace(
    *,
    agent_cycle_report: Mapping[str, Any],
    intent: Optional[Mapping[str, Any]],
    decision: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    cycle_id = _coerce_str(agent_cycle_report.get("cycle_id"))
    command = _find_terminal_command_for_intent(agent_cycle_report, intent)
    provenance = _extract_execution_provenance(command)
    if provenance:
        trace = dict(_mapping(provenance.get("version_trace")))
        if not trace:
            trace = _version_trace_from_execution_provenance(provenance)
        trace.setdefault("trace_source", "dispatch_execution_provenance")
        trace.setdefault("cycle_id", cycle_id or "not_attached")
        trace.setdefault("agent_workflow_version", "agent_workflow_cycle.v1")
        trace.setdefault("dispatch_provenance_hash", _first_nonempty(provenance.get("provenance_hash")) or "not_attached")
        trace.setdefault("gaps", [])
        return trace

    cycle_trace = _mapping(agent_cycle_report.get("version_trace"))
    agent_id = _first_nonempty(
        intent.get("agent_id") if intent else None,
        decision.get("agent_id") if decision else None,
    )
    policy_version = _first_nonempty(
        intent.get("agent_policy_version") if intent else None,
        cycle_trace.get("agent_policy_version"),
        _policy_version_for_agent(agent_id),
    )
    strategy_ref = _first_nonempty(
        intent.get("strategy_setting") if intent else None,
        intent.get("strategy_id") if intent else None,
        cycle_trace.get("strategy_ref"),
    )
    strategy_version = _first_nonempty(
        intent.get("strategy_version") if intent else None,
        cycle_trace.get("strategy_version"),
    )
    model_ref = _first_nonempty(
        intent.get("model_version") if intent else None,
        intent.get("model_ref") if intent else None,
        decision.get("model_version") if decision else None,
        cycle_trace.get("model_ref"),
    )
    prompt_version = _first_nonempty(
        intent.get("prompt_version") if intent else None,
        decision.get("prompt_version") if decision else None,
        cycle_trace.get("prompt_version"),
    )
    risk_engine_version = _first_nonempty(
        decision.get("risk_engine_version") if decision else None,
        cycle_trace.get("risk_engine_version"),
        "agent_overseer.v1" if decision else "",
    )
    market_data_refs = _evidence_refs_for_trace(intent)
    market_data_source = _first_nonempty(
        intent.get("market_data_source") if intent else None,
        cycle_trace.get("market_data_source"),
        _market_data_source_from_refs(market_data_refs),
    )
    execution_router_version = _execution_router_version(command)
    broker_mode = _first_nonempty(command.get("broker_mode") if command else None)
    config_hash = _first_nonempty(
        cycle_trace.get("config_hash"),
        agent_cycle_report.get("config_hash"),
    )

    gaps: list[str] = []
    if not strategy_ref:
        gaps.append("strategy_ref_not_attached")
    if not strategy_version:
        gaps.append("strategy_version_not_attached")
    if not model_ref:
        gaps.append("model_ref_not_attached")
    if not prompt_version:
        gaps.append("prompt_version_not_attached")
    if not risk_engine_version:
        gaps.append("risk_engine_version_not_attached")
    if not market_data_source:
        gaps.append("market_data_source_not_attached")
    if not execution_router_version:
        gaps.append("execution_router_version_not_attached")
    if not config_hash:
        gaps.append("config_hash_not_attached")
    gaps.append("dispatch_execution_provenance_missing")

    return {
        "trace_status": "COMPLETE" if not gaps else "PARTIAL",
        "trace_source": "agent_cycle_report",
        "cycle_id": cycle_id or "not_attached",
        "cycle_schema_version": _coerce_str(agent_cycle_report.get("report_kind")) or "not_attached",
        "agent_workflow_version": "agent_workflow_cycle.v1",
        "agent_ref": agent_id or "not_attached",
        "agent_policy_version": policy_version or "not_attached",
        "strategy_ref": strategy_ref or "not_attached",
        "strategy_version": strategy_version or "not_attached",
        "model_ref": model_ref or "not_attached",
        "prompt_version": prompt_version or "not_attached",
        "risk_engine_version": risk_engine_version or "not_attached",
        "execution_router_version": execution_router_version or "not_attached",
        "broker_mode": broker_mode or "not_attached",
        "market_data_source": market_data_source or "not_attached",
        "market_data_refs": market_data_refs[:5],
        "config_hash": config_hash or "not_attached",
        "gaps": gaps,
    }


def _empty_version_trace(status: str, *, gaps: Sequence[str]) -> dict[str, Any]:
    return {
        "trace_status": status,
        "trace_source": "agent_decision_explainer",
        "cycle_id": "not_attached",
        "agent_workflow_version": "agent_workflow_cycle.v1",
        "strategy_ref": "not_attached",
        "strategy_version": "not_attached",
        "model_ref": "not_attached",
        "prompt_version": "not_attached",
        "risk_engine_version": "not_attached",
        "execution_router_version": "not_attached",
        "market_data_source": "not_attached",
        "config_hash": "not_attached",
        "gaps": list(gaps),
    }


def _find_terminal_command_for_intent(
    agent_cycle_report: Mapping[str, Any],
    intent: Optional[Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    intent_id = _coerce_str(intent.get("intent_id")) if intent else ""
    commands = [
        item
        for item in (agent_cycle_report.get("terminal_commands") or [])
        if isinstance(item, Mapping)
    ]
    if intent_id:
        for command in commands:
            if _coerce_str(command.get("intent_id")) == intent_id:
                return command
    return commands[0] if commands else None


def _extract_execution_provenance(command: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    if not command:
        return {}
    direct = command.get("execution_provenance")
    if isinstance(direct, Mapping):
        return direct
    dispatch_result = command.get("dispatch_result")
    if isinstance(dispatch_result, Mapping):
        direct = dispatch_result.get("execution_provenance")
        if isinstance(direct, Mapping):
            return direct
        card = dispatch_result.get("trade_explanation_card")
        if isinstance(card, Mapping) and isinstance(card.get("execution_provenance"), Mapping):
            return card["execution_provenance"]
    receipt = command.get("terminal_receipt")
    if isinstance(receipt, Mapping) and isinstance(receipt.get("execution_provenance"), Mapping):
        return receipt["execution_provenance"]
    return {}


def _version_trace_from_execution_provenance(provenance: Mapping[str, Any]) -> dict[str, Any]:
    strategy = _mapping(provenance.get("strategy"))
    model = _mapping(provenance.get("model"))
    risk = _mapping(provenance.get("risk_engine"))
    market = _mapping(provenance.get("market_data"))
    return {
        "trace_status": "PARTIAL",
        "trace_source": "execution_provenance",
        "strategy_ref": _first_nonempty(strategy.get("strategy_id")) or "not_attached",
        "strategy_version": _first_nonempty(strategy.get("strategy_version")) or "not_attached",
        "model_ref": _first_nonempty(
            model.get("ai_operator_primary_model"),
            model.get("ai_model_name"),
            model.get("assistant_model"),
        )
        or "not_attached",
        "prompt_version": _first_nonempty(model.get("ai_operator_prompt_version")) or "not_attached",
        "risk_engine_version": _first_nonempty(
            risk.get("risk_control_version"),
            risk.get("pre_execution_risk_gate_version"),
        )
        or "not_attached",
        "dispatch_engine_version": "order_dispatch.v1",
        "market_data_source": _first_nonempty(market.get("market_data_provider")) or "not_attached",
        "config_hash": _first_nonempty(provenance.get("config_hash")) or "not_attached",
        "dispatch_provenance_hash": _first_nonempty(provenance.get("provenance_hash")) or "not_attached",
        "gaps": ["version_trace_summary_missing"],
    }


def _policy_version_for_agent(agent_id: str) -> str:
    token = agent_id.lower()
    if "micro_scalp" in token:
        return "micro_scalp_policy.v1"
    if "hourly" in token or "intraday" in token:
        return "hourly_intraday_policy.v1"
    if "waste" in token:
        return "waste_runner.v1"
    if token:
        return "agent_policy.v1"
    return ""


def _execution_router_version(command: Optional[Mapping[str, Any]]) -> str:
    if not command:
        return ""
    broker_mode = _coerce_str(command.get("broker_mode")).upper()
    command_type = _coerce_str(command.get("command_type"))
    if "PAPER_MT5" in broker_mode or "MT5" in broker_mode:
        return "mt5_demo_agent_loop.v1"
    if "PAPER_MT4" in broker_mode or "MT4" in broker_mode:
        return "mt4_mailbox_bridge.v1"
    return command_type or ""


def _evidence_refs_for_trace(intent: Optional[Mapping[str, Any]]) -> list[str]:
    if not intent:
        return []
    refs = intent.get("evidence_refs") or []
    if isinstance(refs, str):
        return [refs]
    if not isinstance(refs, Iterable):
        return []
    return [_coerce_str(ref) for ref in refs if _coerce_str(ref)]


def _market_data_source_from_refs(refs: Sequence[str]) -> str:
    lowered = " ".join(refs).lower()
    if "forex_fury" in lowered or "forex-fury" in lowered:
        return "forex_fury_replay_artifacts"
    if refs:
        return "evidence_refs"
    return ""


def _compact_movement_source_truth(
    source_truth: Optional[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    if not isinstance(source_truth, Mapping):
        return None
    return {
        "movement_stream_present": bool(source_truth.get("movement_stream_present")),
        "price_source_status": _coerce_str(source_truth.get("price_source_status")) or None,
        "price_source_label": _coerce_str(source_truth.get("price_source_label")) or None,
        "price_source_summary": _coerce_str(source_truth.get("price_source_summary")) or None,
        "price_source_warning": _coerce_str(source_truth.get("price_source_warning")) or None,
        "position_feed_label": _coerce_str(source_truth.get("position_feed_label")) or None,
        "position_feed_detail": _coerce_str(source_truth.get("position_feed_detail")) or None,
        "static_simulation_active": bool(source_truth.get("static_simulation_active")),
        "open_position_count": _coerce_int(source_truth.get("open_position_count")),
        "broker_ticket_position_count": _coerce_int(source_truth.get("broker_ticket_position_count")),
        "simulator_position_count": _coerce_int(source_truth.get("simulator_position_count")),
        "provider_priced_simulator_position_count": _coerce_int(
            source_truth.get("provider_priced_simulator_position_count")
        ),
        "static_simulator_position_count": _coerce_int(source_truth.get("static_simulator_position_count")),
        "stale_price_position_count": _coerce_int(source_truth.get("stale_price_position_count")),
        "source_label_counts": (
            {
                str(key): _coerce_int(value)
                for key, value in dict(source_truth.get("source_label_counts") or {}).items()
            }
            if isinstance(source_truth.get("source_label_counts"), Mapping)
            else {}
        ),
        "configured_market_data_provider": _coerce_str(source_truth.get("configured_market_data_provider")) or None,
        "provider_usable_symbols": _coerce_string_list(source_truth.get("provider_usable_symbols")),
        "static_fallback_symbols": _coerce_string_list(source_truth.get("static_fallback_symbols")),
        "mt5_fallback_symbols": _coerce_string_list(source_truth.get("mt5_fallback_symbols")),
        "provider_stale_symbols": _coerce_string_list(source_truth.get("provider_stale_symbols")),
        "provider_freshness_max_age_seconds": _coerce_int(
            source_truth.get("provider_freshness_max_age_seconds")
        ),
        "provider_error_count": _coerce_int(source_truth.get("provider_error_count")),
        "attention_required": bool(source_truth.get("attention_required")),
        "detail": _coerce_str(source_truth.get("detail")) or None,
        "local_detail": _coerce_str(source_truth.get("local_detail")) or None,
    }


# ---------------------------------------------------------------------------
# Overall status + summary
# ---------------------------------------------------------------------------


def _resolve_overall_status(
    *,
    intent: Optional[Mapping[str, Any]],
    decision: Optional[Mapping[str, Any]],
    pcba_blocked: bool,
    executed: bool,
    execution_step: DecisionChainStep,
) -> Tuple[str, Optional[str]]:
    if executed:
        return _OVERALL_EXECUTED, (
            "Review the broker receipt and the close P&L when the deal history lands."
        )

    if pcba_blocked:
        return _OVERALL_BLOCKED, (
            "Address the PCBA gate reason before this strategy class can run again."
        )

    if execution_step.status == _STATUS_BLOCKED:
        return _OVERALL_BLOCKED, (
            "Review the overseer reasons; this intent was rejected before reaching the broker."
        )

    if decision and decision.get("approved"):
        return _OVERALL_APPROVED_NOT_EXECUTED, (
            "Confirm the terminal bridge dispatched the order; no broker receipt is attached."
        )

    if intent and not decision:
        return _OVERALL_APPROVED_NOT_EXECUTED, (
            "An intent exists but no overseer decision is recorded — re-run the overseer."
        )

    return _OVERALL_NO_DECISION, (
        "No usable intent/decision pair was found in the cycle report."
    )


def _build_plain_english_summary(
    *,
    cycle_id: Optional[str],
    overall_status: str,
    intent: Optional[Mapping[str, Any]],
    decision: Optional[Mapping[str, Any]],
    strategy_step: DecisionChainStep,
    walk_forward_step: DecisionChainStep,
    pcba_step: DecisionChainStep,
    execution_step: DecisionChainStep,
) -> str:
    """Return a 2-3 sentence plain-English summary the LLM bot can surface.

    The summary is explanation-only: it describes the PAST decision the agent
    already made. It never recommends a future trade or asks the operator to
    take a market action.
    """

    symbol = _coerce_str(intent.get("symbol")) if intent else ""
    timeframe = _coerce_str(intent.get("timeframe")) if intent else ""
    direction = _coerce_str(intent.get("direction") or intent.get("action")) if intent else ""
    strategy = _coerce_str(intent.get("strategy_setting")) if intent else ""

    if overall_status == _OVERALL_NO_DECISION:
        return (
            "There is no recent agent decision on record to explain. "
            "Run an agent cycle so the desk produces a route intent, overseer decision, "
            "and execution receipt to walk through."
        )

    head = f"In cycle {cycle_id or 'unknown'}, the agent chose strategy "
    head += f"{strategy or 'unspecified'} and formed an intent to "
    head += f"{direction.lower() or 'trade'} {symbol or 'the instrument'} on {timeframe or 'its timeframe'}."

    middle = _summarize_justification(strategy_step, walk_forward_step, pcba_step)

    if overall_status == _OVERALL_EXECUTED:
        tail = (
            f" The intent was approved and executed on the paper/demo terminal, and the "
            f"outcome can be read in the broker receipt."
        )
    elif overall_status == _OVERALL_APPROVED_NOT_EXECUTED:
        tail = (
            " The intent was approved but no broker receipt is attached, so the terminal "
            "bridge has not yet confirmed dispatch."
        )
    elif overall_status == _OVERALL_BLOCKED:
        tail = f" The intent was blocked before reaching the broker — {execution_step.headline.lower()}"
    else:  # pragma: no cover - defensive
        tail = " The chain status could not be classified."

    return (head + " " + middle + tail).strip()


def _summarize_justification(
    strategy_step: DecisionChainStep,
    walk_forward_step: DecisionChainStep,
    pcba_step: DecisionChainStep,
) -> str:
    bits: list[str] = []
    if strategy_step.status == _STATUS_FOUND:
        bits.append("the strategy lead was on the queue")
    if walk_forward_step.status == _STATUS_FOUND:
        bits.append("walk-forward evidence supported the lead")
    elif walk_forward_step.status == _STATUS_MISSING:
        bits.append("walk-forward evidence was not attached")
    if pcba_step.status == _STATUS_FOUND:
        bits.append("the PCBA gate did not block it")
    elif pcba_step.status == _STATUS_BLOCKED:
        bits.append("the PCBA gate blocked it")

    if not bits:
        return "The justification chain could not be reconstructed from the inputs provided."
    return "Justification: " + "; ".join(bits) + "."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        text = _coerce_str(value).strip()
        return [text] if text else []
    if not isinstance(value, Iterable):
        return []
    out: list[str] = []
    for item in value:
        text = _coerce_str(item).strip()
        if text:
            out.append(text)
    return out


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_nonempty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _format_conviction_score(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "unknown (not_win_probability)"
    bounded = max(0.0, min(1.0, numeric))
    return f"{round(bounded * 100):.0f}% (not_win_probability)"


def _has_broker_ticket(command: Mapping[str, Any]) -> bool:
    receipt = command.get("terminal_receipt")
    if not isinstance(receipt, Mapping):
        return False
    ticket = receipt.get("broker_ticket")
    return ticket is not None and _coerce_str(ticket).strip() != ""


def _is_pcba_marker(text: str) -> bool:
    lowered = text.lower()
    return "pcba" in lowered or "license" in lowered or "not_licensed" in lowered


def _find_memory_record_for_intent(
    memory_report: Optional[Mapping[str, Any]],
    intent_id: str,
) -> Optional[Mapping[str, Any]]:
    if not memory_report or not intent_id:
        return None
    records = memory_report.get("memory_records") or []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        if _coerce_str(record.get("intent_id")) == intent_id:
            return record
        evidence_refs = record.get("evidence_refs") or []
        if isinstance(evidence_refs, Iterable):
            for ref in evidence_refs:
                if intent_id in _coerce_str(ref):
                    return record
    return None


def _find_matching_strategy_item(
    *,
    strategy_dev_queue_report: Optional[Mapping[str, Any]],
    strategy_leads: Optional[Mapping[str, Any]],
    symbol: str,
    timeframe: str,
    strategy_setting: str,
) -> Optional[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    if isinstance(strategy_dev_queue_report, Mapping):
        for item in strategy_dev_queue_report.get("work_items") or []:
            if isinstance(item, Mapping):
                candidates.append(item)
    if isinstance(strategy_leads, Mapping):
        leads = strategy_leads.get("leads") if isinstance(strategy_leads.get("leads"), Sequence) else None
        if leads:
            for lead in leads:
                if isinstance(lead, Mapping):
                    candidates.append(lead)
        else:
            # Flat dict of {strategy_setting: lead_info}
            for key, lead in strategy_leads.items():
                if isinstance(lead, Mapping):
                    merged = dict(lead)
                    merged.setdefault("strategy_setting", key)
                    candidates.append(merged)

    if not candidates:
        return None

    def _match_score(item: Mapping[str, Any]) -> int:
        score = 0
        symbols = [str(s) for s in (item.get("symbols") or []) if s]
        timeframes = [str(t) for t in (item.get("timeframes") or []) if t]
        item_strategy = _coerce_str(
            item.get("strategy_setting") or item.get("family") or ""
        ).lower()
        if strategy_setting and item_strategy and strategy_setting.lower() in item_strategy:
            score += 4
        if strategy_setting and item_strategy and item_strategy in strategy_setting.lower():
            score += 2
        if symbol and symbol in symbols:
            score += 3
        if timeframe and timeframe in timeframes:
            score += 1
        return score

    candidates.sort(key=_match_score, reverse=True)
    best = candidates[0]
    if _match_score(best) > 0:
        return best
    # No match by symbol/timeframe/strategy — fall back to first candidate only
    # if no specifics were provided to match against.
    if not symbol and not timeframe and not strategy_setting:
        return best
    return None
