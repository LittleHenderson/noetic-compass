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


def explain_latest_agent_decision(
    *,
    agent_cycle_report: Optional[Mapping[str, Any]] = None,
    agent_memory_report: Optional[Mapping[str, Any]] = None,
    daily_learning_rollup: Optional[Mapping[str, Any]] = None,
    strategy_dev_queue_report: Optional[Mapping[str, Any]] = None,
    strategy_leads: Optional[Mapping[str, Any]] = None,
    walk_forward_report: Optional[Mapping[str, Any]] = None,
    pcba_report: Optional[Mapping[str, Any]] = None,
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

    return AgentDecisionExplanation(
        cycle_id=cycle_id,
        overall_status=overall_status,
        plain_english_summary=summary,
        chain=chain,
        next_action_hint=next_hint,
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
        evidence.append(f"confidence={confidence}")
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
