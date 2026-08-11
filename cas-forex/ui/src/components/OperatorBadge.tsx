/* ── CAS Forex — AI Operator badge ──
   Always-visible header indicator for the AI strategy desk: which model is
   driving (Claude vs free local fallback), whether the operator loop is on, the
   token budget, and every model switch. Click to expand controls (start/stop,
   run now, top up Claude tokens) and see recent operator actions. */

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import {
  fetchOperatorState,
  startOperator,
  stopOperator,
  runOperatorNow,
  addOperatorTokens,
  setOperatorKey,
  setDeepSeekKey,
  chatWithOperator,
  fetchGuidance,
  addGuidance,
  removeGuidance,
  type GuidanceNote,
  type OperatorState,
} from "../data/operatorApi";
import { executeCommand, type CommandPreview } from "../data/ownerCommandApi";
import "./OperatorBadge.css";

const POLL_MS = 10_000;
const DEFAULT_INTERVAL_SECONDS = 1800;

type Driver = "claude" | "deepseek" | "gemma" | "local" | "off" | "stalled" | "warming" | "unknown";
type ApiErrorLike = Error & { status?: number; payload?: unknown };

function classifyDriver(state: OperatorState | null): { driver: Driver; label: string; note: string } {
  if (!state) return { driver: "unknown", label: "OPERATOR ?", note: "API unreachable" };
  if (!state.running) return { driver: "off", label: "OPERATOR OFF", note: "strategy desk paused" };

  const modelHealth = String(
    state.model_provider?.provider_reachability || "NOT_PROBED",
  ).toUpperCase();
  const modelError = String(state.model_provider?.provider_last_error || "").trim();
  if (modelHealth === "FAILED") {
    return {
      driver: "stalled",
      label: "MODEL ERROR",
      note: modelError || "the selected model failed its latest real generation request",
    };
  }

  // Prefer the ACTUAL last-tick outcome over "which provider would be tried".
  // A provider name on the last tick means the model DID answer — even if the
  // tick couldn't use that answer (e.g. an over-long reply). That is a model
  // that is UP, not "NO MODEL". Only a tick with NO provider is truly no-model.
  const lastOk = state.last_ok;
  const lastProvider = state.last_provider ?? null;
  const err = state.last_error ?? "";
  const parseHiccup = lastOk === false && !!lastProvider && !/reachable|unavailable|no model|connect|credit|api key/i.test(err);
  if (lastProvider) {
    const isClaude = lastProvider === "claude";
    const isDeepSeek = lastProvider.startsWith("deepseek-");
    const isGemma = lastProvider === "gemma4-backup";
    const note = parseHiccup
      ? "answering, but the last reply was too long to use — recovering next check"
      : isDeepSeek
        ? `${lastProvider === "deepseek-pro" ? "Pro escalation" : "Flash continuous lane"} is answering`
        : isGemma
          ? "Gemma 4 31B cloud backup is answering"
        : isClaude
          ? "paid primary is answering"
          : "free fallback is answering";
    if (isDeepSeek) {
      return {
        driver: "deepseek",
        label: lastProvider === "deepseek-pro" ? "DEEPSEEK PRO" : "DEEPSEEK FLASH",
        note,
      };
    }
    if (isGemma) {
      return {
        driver: "gemma",
        label: "GEMMA 4 BACKUP",
        note,
      };
    }
    return isClaude
      ? { driver: "claude", label: "CLAUDE", note }
      : { driver: "local", label: "LOCAL (free)", note };
  }
  if (lastOk === false) {
    return { driver: "stalled", label: "NO MODEL", note: "no AI model reachable - configure DeepSeek, Claude, or Ollama" };
  }
  // Running but no tick has completed yet.
  return { driver: "warming", label: "OPERATOR ON", note: "starting — first check pending" };
}

function operatorUnavailableMessage(error?: string | null): string {
  const detail = (error || "").trim();
  if (/api key|credit|token|budget/i.test(detail)) {
    return `Operator model unavailable: ${detail}. No command ran and no dials changed.`;
  }
  if (/timeout|timed out/i.test(detail)) {
    return `Operator model timed out. No command ran and no dials changed; local diagnostics may still answer status questions.`;
  }
  return `Operator unavailable: ${detail || "no model reachable"}. No command ran and no dials changed.`;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function readText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function operatorApiFailureDetail(err: unknown): {
  status?: number;
  errorCode?: string | null;
  detail: string;
  moneyImpact?: string | null;
  claimBoundary?: string | null;
} {
  const apiErr = err as ApiErrorLike | null;
  const payload = asRecord(apiErr?.payload);
  const payloadDetail = asRecord(payload?.detail);
  return {
    status: typeof apiErr?.status === "number" ? apiErr.status : undefined,
    errorCode: readText(payloadDetail?.error) ?? readText(payload?.error),
    detail:
      readText(payloadDetail?.detail)
      ?? readText(payloadDetail?.message)
      ?? readText(payloadDetail?.error)
      ?? readText(payload?.message)
      ?? readText(payload?.detail)
      ?? readText(payload?.error)
      ?? (err instanceof Error ? err.message : String(err || "request failed")),
    moneyImpact: readText(payloadDetail?.money_impact) ?? readText(payload?.money_impact),
    claimBoundary: readText(payloadDetail?.claim_boundary) ?? readText(payload?.claim_boundary),
  };
}

function operatorRequestFailureMessage(err: unknown): string {
  const { status, errorCode, detail, moneyImpact } = operatorApiFailureDetail(err);
  const context = `${status ?? ""} ${errorCode ?? ""} ${detail}`.toLowerCase();
  const outcome = moneyImpact || "No command ran and no dials changed.";
  const browserTransportFailure = typeof status !== "number"
    && /failed to fetch|load failed|networkerror|network error|network request failed|fetch failed|refused|econnrefused|err_network/i.test(context);
  if (status === 401 || status === 403 || /owner_auth_required|unauthorized|forbidden|owner|auth|token/i.test(context)) {
    return `Operator API rejected the request as unauthorized. Check owner pairing/token state. ${outcome}`;
  }
  if (/abort|timeout|timed out/i.test(context)) {
    return `Operator request timed out before a reply. ${outcome}`;
  }
  if (browserTransportFailure) {
    return `Operator API is unreachable from this browser. Confirm the local API is running and the phone/laptop API base is correct. ${outcome}`;
  }
  if (status === 500 || status === 502 || status === 503 || /operator_chat_unavailable|internal server error/i.test(context)) {
    return `Operator backend failed before a reply: ${detail}. ${outcome}`;
  }
  return `Operator request failed before a reply: ${detail}. ${outcome}`;
}

function formatMetric(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/a";
  return value.toFixed(digits);
}

function formatUsd(value: number | null | undefined, signed = false): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "unavailable";
  const prefix = value < 0 ? "-" : signed && value > 0 ? "+" : "";
  return `${prefix}$${Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function extractPreviewReason(params: Record<string, unknown> | null | undefined): string {
  const value = params?.journal_reason ?? params?.reason;
  return typeof value === "string" ? value : "";
}

function formatContractValue(value: unknown, valueKind?: string): string {
  if (valueKind === "toggle") return value ? "ON" : "OFF";
  if (Array.isArray(value)) return value.join(", ");
  if (value == null) return "n/a";
  return String(value);
}

function formatOwnerBound(bound: unknown): string {
  if (!bound || typeof bound !== "object" || Array.isArray(bound)) return String(bound ?? "n/a");
  const record = bound as Record<string, unknown>;
  if ("min" in record || "max" in record) {
    return `${String(record.min ?? "n/a")} to ${String(record.max ?? "n/a")}`;
  }
  if (Array.isArray(record.allowed)) {
    return record.allowed.join(", ");
  }
  return JSON.stringify(record);
}

export function OperatorBadge() {
  const [state, setState] = useState<OperatorState | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [topUp, setTopUp] = useState("500000");
  const [keyInput, setKeyInput] = useState("");
  const [keyMsg, setKeyMsg] = useState("");
  const [deepSeekKeyInput, setDeepSeekKeyInput] = useState("");
  const [deepSeekKeyMsg, setDeepSeekKeyMsg] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatReply, setChatReply] = useState("");
  const [chatResponder, setChatResponder] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [guidance, setGuidance] = useState<GuidanceNote[]>([]);
  const [proposed, setProposed] = useState<{ command: string; params: Record<string, unknown> } | null>(null);
  const [preview, setPreview] = useState<CommandPreview | null>(null);
  const [confirmInput, setConfirmInput] = useState("");
  const [journalInput, setJournalInput] = useState("");
  const [receiptMsg, setReceiptMsg] = useState("");
  const [targetInput, setTargetInput] = useState("");
  const [targetMsg, setTargetMsg] = useState("");
  const timer = useRef<number | null>(null);
  const chipRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const panelTitleRef = useRef<HTMLDivElement | null>(null);
  const chatRef = useRef<HTMLDivElement | null>(null);
  const [panelPosition, setPanelPosition] = useState({ top: 72, left: 8 });

  const refresh = useCallback(async () => {
    const next = await fetchOperatorState();
    setState(next);
  }, []);

  useEffect(() => {
    refresh();
    timer.current = window.setInterval(refresh, POLL_MS);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [refresh]);

  useEffect(() => {
    if (open) fetchGuidance().then(setGuidance);
  }, [open]);

  useLayoutEffect(() => {
    if (!open) return;
    const positionPanel = () => {
      const chip = chipRef.current;
      if (!chip) return;
      const rect = chip.getBoundingClientRect();
      const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 360;
      const panelWidth = Math.min(320, Math.max(0, viewportWidth - 16));
      const left = Math.min(
        Math.max(8, rect.right - panelWidth),
        Math.max(8, viewportWidth - panelWidth - 8),
      );
      setPanelPosition({
        top: Math.max(8, rect.bottom + 8),
        left,
      });
    };

    positionPanel();
    window.addEventListener("resize", positionPanel);
    window.addEventListener("scroll", positionPanel, true);
    return () => {
      window.removeEventListener("resize", positionPanel);
      window.removeEventListener("scroll", positionPanel, true);
    };
  }, [open]);

  useLayoutEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    const title = panelTitleRef.current;
    const chat = chatRef.current;
    if (!panel || !chat) return;

    // Chat is the Operator's primary control surface. The panel contains a
    // substantial evidence/status report above it, so open directly at the
    // composer while keeping the sticky identity header visible.
    const titleHeight = title?.getBoundingClientRect().height ?? 0;
    panel.scrollTop = Math.max(0, chat.offsetTop - titleHeight - 12);
  }, [open]);

  const ask = useCallback(async () => {
    const q = chatInput.trim();
    if (!q) return;
    setChatBusy(true);
    setChatReply("…thinking…");
    setChatResponder("");
    setProposed(null);
    setPreview(null);
    setConfirmInput("");
    setJournalInput("");
    setReceiptMsg("");
    try {
      const res = await chatWithOperator(q);
      setChatReply(res.ok ? res.reply || "(no reply)" : operatorUnavailableMessage(res.error));
      if (res.ok && res.model_ok && !res.fallback) {
        setChatResponder(
          `Primary model response · ${res.provider_label || res.provider || "AI model"}`,
        );
      } else if (res.ok && res.fallback) {
        const runtimeTruth =
          res.model_attempted === false &&
          Boolean(res.chat_path_status?.startsWith("LOCAL_"));
        setChatResponder(
          `${runtimeTruth ? "CAS runtime truth" : "Local fallback"} · ${
            res.chat_path_status || "the AI model did not return a usable answer"
          }`,
        );
      } else {
        setChatResponder("Operator response unavailable");
      }
      if (res.ok && res.proposed_command && res.command_preview) {
        setProposed(res.proposed_command);
        setPreview(res.command_preview);
        // Pre-fill the confirm box with the exact phrase so it's one tap to run.
        setConfirmInput(res.command_preview.confirm_phrase || "CONFIRM");
        setJournalInput(extractPreviewReason(res.proposed_command.params));
      }
    } catch (err) {
      setChatReply(operatorRequestFailureMessage(err));
      setChatResponder("Operator request failed");
    } finally {
      setChatBusy(false);
    }
  }, [chatInput]);

  const setDailyTarget = useCallback(async () => {
    const v = Number(targetInput);
    if (!Number.isFinite(v) || v <= 0) { setTargetMsg("Enter a dollar amount."); return; }
    setTargetMsg("Setting…");
    try {
      const res = await executeCommand("set_profit_target", { daily_target: v }, "CONFIRM");
      if (res.ok && res.applied) {
        setTargetMsg(`Daily target set to $${v.toLocaleString()} ✓`);
        setTargetInput("");
        refresh();
      } else {
        setTargetMsg(`Not set: ${res.reason ?? "blocked"}${res.preview?.blockers?.length ? " — " + res.preview.blockers.join("; ") : ""}`);
      }
    } catch {
      setTargetMsg("Could not set the target.");
    }
  }, [targetInput, refresh]);

  const runProposed = useCallback(async () => {
    if (!proposed) return;
    setChatBusy(true);
    setReceiptMsg("");
    try {
      const res = await executeCommand(
        proposed.command,
        {
          ...proposed.params,
          ...(journalInput.trim() ? { journal_reason: journalInput.trim() } : {}),
        },
        confirmInput.trim(),
      );
      if (res.ok && res.applied) {
        const r = (res.result || {}) as Record<string, unknown>;
        setReceiptMsg(`Done ✓ ${JSON.stringify(r)}`);
        setProposed(null);
        setPreview(null);
        setConfirmInput("");
        setJournalInput("");
        refresh();
      } else if (res.need_confirmation) {
        setReceiptMsg(`Type exactly: "${res.need_confirmation}" to run this.`);
      } else {
        setReceiptMsg(`Not applied: ${res.reason ?? "blocked"}${res.preview?.blockers?.length ? " — " + res.preview.blockers.join("; ") : ""}`);
      }
    } catch {
      setReceiptMsg("Command failed to run.");
    } finally {
      setChatBusy(false);
    }
  }, [proposed, confirmInput, journalInput, refresh]);

  const saveGuidance = useCallback(async () => {
    const q = chatInput.trim();
    if (!q) return;
    setChatBusy(true);
    try {
      setGuidance(await addGuidance(q));
      setChatInput("");
      setChatReply("Saved as standing guidance — the operator weighs it on every check from now on.");
      setChatResponder("Standing guidance saved");
    } catch {
      setChatReply("Could not save guidance.");
      setChatResponder("Standing guidance failed");
    } finally {
      setChatBusy(false);
    }
  }, [chatInput]);

  const { driver, label, note } = classifyDriver(state);
  const mp = state?.model_provider;
  const activeObjective = state?.active_account_objective;
  const activeAccount = activeObjective?.current_account;
  const activeGrowth = activeObjective?.growth_measurement;
  const casClosedOutcomes = activeGrowth?.cas_bound_closed_outcomes;
  const dailyObjective = activeObjective?.daily_objective;
  const profit = state?.profit_and_balance;
  const readiness = state?.professional_readiness;
  const contextDelivery = state?.last_context_delivery;
  const running = Boolean(state?.running);
  const execution = state?.execution_runtime;
  const moneyMovement = state?.autonomous_money_movement;
  const executionActive = Boolean(execution?.execution_active);
  const executionBlocked = execution?.status === "LIVE_BLOCKED" || execution?.mode === "LIVE_BLOCKED";
  const paperFallback = Boolean(execution?.paper_fallback_active) || execution?.mode === "PAPER_FALLBACK";
  const paperSimulator = execution?.execution_lane === "PAPER"
    && String(execution?.last_bridge_class ?? "").toUpperCase().includes("SIMULATED");
  const paperMt5 = execution?.execution_lane === "PAPER"
    && String(execution?.last_bridge_class ?? "").toUpperCase().includes("MT5");
  const simulatorHandoffCount = Math.max(
    0,
    Number(execution?.last_management_simulator_handoff_position_count ?? 0) || 0,
  );
  const operatorTradeEdgeStatus = execution?.last_operator_trade_edge_status ?? null;
  const operatorTradeEdge = execution?.last_operator_trade_edge;
  const operatorPositionEdgeStatus = execution?.last_operator_position_edge_status ?? null;
  const operatorPositionEdge = execution?.last_operator_position_edge;
  const scaleInBlockers = execution?.last_scale_in_blockers ?? [];
  const operatorPositionEdgeAwaiting = !operatorPositionEdgeStatus
    || operatorPositionEdgeStatus === "NO_DECISION_YET";
  const operatorDecisionContext = operatorTradeEdge?.decision_context;
  const latestTradeDecision = operatorTradeEdge?.decisions?.[0];
  const latestSizingOptions = latestTradeDecision?.sizing_options_offered ?? [];
  const latestSizingLots = latestSizingOptions
    .map((option) => Number(option.lots))
    .filter((lots) => Number.isFinite(lots) && lots > 0);
  const latestSizingLimiter = latestTradeDecision?.sizing_limiting_source
    ?.replace(/_/g, " ");
  const latestPositionDecision = operatorPositionEdge?.decisions?.find(
    (decision) => decision.decision === "SELECT",
  );
  const latestTradeDecisionEvidence = latestTradeDecision?.intent_id
    ? operatorDecisionContext?.candidate_groups?.[latestTradeDecision.intent_id]
    : undefined;
  const symbolTargeting = execution?.last_symbol_targeting;
  const entryRiskFeasibility = execution?.last_entry_risk_feasibility;
  const latestRiskBlockedCandidate = entryRiskFeasibility?.candidates?.find((candidate) =>
    String(candidate.status ?? "").startsWith("BLOCKED_"),
  );
  const currentBrokerGroupLearningReady = execution?.last_mt5_demo_learning_group_learning_ready;
  const currentBrokerOverallSampleReady = execution?.last_mt5_demo_learning_overall_sample_ready;
  const decisionGroupLearningReady = operatorDecisionContext?.combined_paper_learning?.group_learning_ready
    ?? operatorDecisionContext?.combined_paper_learning?.learning_ready;
  const learningReadinessLabel = currentBrokerGroupLearningReady === true
    ? "broker group learning ready"
    : currentBrokerOverallSampleReady === true
      ? "overall count reached; no broker group ready"
      : currentBrokerGroupLearningReady === false
        ? "broker group samples sparse"
        : decisionGroupLearningReady
          ? "decision snapshot group ready"
          : "decision samples sparse";
  const operatorTradeEdgeAwaiting = !operatorTradeEdgeStatus
    || operatorTradeEdgeStatus === "NO_DECISION_YET";
  const operatorStateLabel = !running
    ? "OFF"
    : executionActive && paperSimulator
      ? "WATCHING + PAPER SIM"
      : executionActive && paperMt5
        ? "WATCHING + MT5 DEMO"
        : executionActive && paperFallback
          ? "WATCHING + PAPER EXECUTING"
          : executionActive
            ? "WATCHING + EXECUTING"
            : executionBlocked
              ? "WATCHING / EXECUTION BLOCKED"
              : "WATCHING / EXECUTION OFF";

  const act = useCallback(
    async (fn: () => Promise<unknown>) => {
      setBusy(true);
      try {
        await fn();
        await refresh();
      } catch {
        /* leave the badge showing last-known state; poll will recover */
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const panelStyle = {
    "--operator-panel-top": `${panelPosition.top}px`,
    "--operator-panel-left": `${panelPosition.left}px`,
  } as CSSProperties;

  return (
    <div className={`operator-badge operator-badge--${driver} ${open ? "operator-badge--open" : ""}`}>
      <button
        ref={chipRef}
        className="operator-badge-chip"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        title="AI operator / model status — click for controls"
      >
        <span className="operator-badge-dot" />
        <span className="operator-badge-label">{label}</span>
        {mp?.budget_capped && driver === "claude" ? (
          <span className="operator-badge-budget">{formatTokens(mp?.budget_remaining ?? 0)} left</span>
        ) : null}
      </button>

      {open && typeof document !== "undefined" ? createPortal((
        <div
          ref={panelRef}
          className="operator-badge-panel"
          style={panelStyle}
          role="region"
          aria-label="AI Operator controls and chat"
        >
          <div ref={panelTitleRef} className="operator-badge-row operator-badge-title">
            <span>AI Operator (trading edge)</span>
            <span className={`operator-badge-state operator-badge-state--${running ? "on" : "off"}`}>
              {operatorStateLabel}
            </span>
          </div>

          <div className="operator-badge-line">
            Driving now: <strong>{label}</strong> <span className="operator-badge-muted">— {note}</span>
          </div>

          <div className="operator-badge-line">
            Execution: <strong>{paperSimulator ? "PAPER SIM / LIVE PENDING" : paperMt5 && simulatorHandoffCount > 0 ? "MT5 DEMO + SIM HANDOFF / LIVE PENDING" : paperMt5 ? "MT5 DEMO / LIVE PENDING" : paperFallback ? "PAPER ACTIVE / LIVE PENDING" : executionBlocked ? "LIVE PENDING" : executionActive ? (execution?.mode ?? "ACTIVE") : "LOOP OFF"}</strong>
            <span className="operator-badge-muted">{` · cycles ${execution?.cycles_run ?? 0}`}</span>
          </div>
          {paperMt5 ? (
            <div className="operator-badge-line operator-badge-muted">
              Execution truth: <strong>PRIMARY MT5 DISPATCH</strong>
              {" · terminal positions and dispatch management are authoritative; SIM PROOF diagnostics are secondary"}
            </div>
          ) : null}
          <div className="operator-badge-line">
            Operator entry edge: <strong>{operatorTradeEdgeAwaiting ? "AWAITING FRESH CANDIDATE" : operatorTradeEdgeStatus}</strong>
            <span className="operator-badge-muted">
              {execution?.operator_trade_edge_prompt_version
                ? ` · engine ${execution.operator_trade_edge_prompt_version}`
                : ""}
              {operatorTradeEdge?.prompt_version
                && operatorTradeEdge.prompt_version !== execution?.operator_trade_edge_prompt_version
                ? ` · last decision ${operatorTradeEdge.prompt_version}`
                : ""}
            </span>
            {!operatorTradeEdgeAwaiting ? (
              <span className="operator-badge-muted">
                {` · ${execution?.last_operator_trade_edge_provider ?? "no provider"}`}
                {` · approved ${execution?.last_operator_trade_edge_approved_count ?? 0}`}
                {` · stood down ${execution?.last_operator_trade_edge_stand_down_count ?? 0}`}
              </span>
            ) : null}
          </div>
          {execution?.last_symbol_targeting_status ? (
            <div className="operator-badge-line">
              Entry scan: <strong>{execution.last_symbol_targeting_status}</strong>
              <span className="operator-badge-muted">
                {` · eligible ${execution.last_eligible_entry_symbols?.length ?? 0}`}
                {` · saturated ${(execution.last_saturated_entry_symbols ?? []).join(", ") || "none"}`}
              </span>
            </div>
          ) : null}
          {execution?.last_entry_timeframe ? (
            <div className="operator-badge-line">
              Timeframe lane: <strong>{execution.last_entry_timeframe}</strong>
              <span className="operator-badge-muted">
                {` · ${execution.last_entry_lane ?? "INTRADAY"}`}
                {` · active ${(execution.active_entry_timeframes ?? []).join(", ") || "none"}`}
              </span>
            </div>
          ) : null}
          {entryRiskFeasibility?.status ? (
            <div className="operator-badge-line">
              Entry risk preflight: <strong>{entryRiskFeasibility.status}</strong>
              <span className="operator-badge-muted">
                {entryRiskFeasibility.max_risk_per_trade_pct != null
                  ? ` · cap ${entryRiskFeasibility.max_risk_per_trade_pct}%`
                  : " · cap unavailable"}
                {` · feasible ${entryRiskFeasibility.feasible_count ?? 0}`}
                {` · blocked ${entryRiskFeasibility.blocked_count ?? 0}`}
                {` · unknown ${entryRiskFeasibility.unknown_count ?? 0}`}
                {` · sent to Operator ${entryRiskFeasibility.operator_candidate_count ?? 0}`}
              </span>
            </div>
          ) : null}
          {latestRiskBlockedCandidate?.reason ? (
            <div className="operator-badge-line operator-badge-muted">
              {latestRiskBlockedCandidate.reason}
            </div>
          ) : null}
          {symbolTargeting?.detail ? (
            <div className="operator-badge-line operator-badge-muted">
              {symbolTargeting.detail}
            </div>
          ) : null}
          {execution?.control_revision ? (
            <div className="operator-badge-line operator-badge-muted">
              {`Target control r${execution.control_revision} · ${execution.control_updated_by ?? "unknown"} · ${execution.control_change_reason ?? "no reason"}`}
            </div>
          ) : null}
          {execution?.last_operator_trade_edge_summary ? (
            <div className="operator-badge-line operator-badge-muted">
              {execution.last_operator_trade_edge_summary}
            </div>
          ) : null}
          {latestTradeDecision?.selected_lots != null ? (
            <div className="operator-badge-line">
              Operator lot choice: <strong>{Number(latestTradeDecision.selected_lots).toFixed(2)} lots</strong>
              <span className="operator-badge-muted">
                {` | ${latestTradeDecision.selected_sizing_label ?? "exact broker-grid size"}`}
                {latestTradeDecision.conviction ? ` | ${latestTradeDecision.conviction} conviction` : ""}
              </span>
            </div>
          ) : null}
          {latestSizingLots.length > 0 ? (
            <div className="operator-badge-line operator-badge-muted">
              Lot envelope: <strong>{latestSizingLots.map((lots) => lots.toFixed(2)).join(" / ")}</strong>
              {latestTradeDecision?.max_executable_lots != null
                ? ` | maximum ${Number(latestTradeDecision.max_executable_lots).toFixed(2)}`
                : ""}
              {latestSizingLimiter ? ` | limited by ${latestSizingLimiter}` : ""}
            </div>
          ) : null}
          {operatorDecisionContext ? (
            <div className="operator-badge-line operator-badge-muted">
              Decision evidence: <strong>{operatorDecisionContext.status ?? operatorTradeEdge?.decision_context_status ?? "UNKNOWN"}</strong>
              {` · combined ${operatorDecisionContext.combined_paper_learning?.bound_trade_count ?? 0}`}
              {` · broker demo ${operatorDecisionContext.broker_verified_mt5_demo?.bound_trade_count ?? 0}`}
              {` · ${learningReadinessLabel}`}
            </div>
          ) : null}
          {(latestTradeDecisionEvidence?.same_symbol_direction?.trades ?? 0) > 0 ? (
            <div className="operator-badge-line operator-badge-muted">
              {`Prior ${latestTradeDecisionEvidence?.symbol ?? latestTradeDecision?.symbol ?? "candidate"} ${latestTradeDecisionEvidence?.direction ?? latestTradeDecision?.direction ?? ""}: `}
              <strong>
                {`${latestTradeDecisionEvidence?.same_symbol_direction?.trades ?? 0} trade${latestTradeDecisionEvidence?.same_symbol_direction?.trades === 1 ? "" : "s"}`}
              </strong>
              {` · ${latestTradeDecisionEvidence?.same_symbol_direction?.wins ?? 0}W/${latestTradeDecisionEvidence?.same_symbol_direction?.losses ?? 0}L`}
              {` · net ${formatSignedUsd(latestTradeDecisionEvidence?.same_symbol_direction?.net_pnl ?? 0)}`}
              {latestTradeDecisionEvidence?.requires_differentiation_after_loss ? " · new evidence required after loss" : ""}
            </div>
          ) : null}
          <div className="operator-badge-line">
            Position management: <strong>{execution?.last_management_status ?? (executionBlocked ? "BLOCKED WITH LIVE" : "NOT RUN")}</strong>
            <span className="operator-badge-muted">
              {` · checks ${execution?.management_cycles_run ?? 0} · terminal effects ${execution?.last_management_terminal_effect_count ?? 0}`}
            </span>
          </div>
          <div className="operator-badge-line">
            Operator position edge: <strong>{operatorPositionEdgeAwaiting ? "AWAITING ACTIONABLE POSITION" : operatorPositionEdgeStatus}</strong>
            <span className="operator-badge-muted">
              {execution?.operator_position_edge_prompt_version
                ? ` · engine ${execution.operator_position_edge_prompt_version}`
                : ""}
              {operatorPositionEdge?.prompt_version
                && operatorPositionEdge.prompt_version !== execution?.operator_position_edge_prompt_version
                ? ` · last decision ${operatorPositionEdge.prompt_version}`
                : ""}
            </span>
            {!operatorPositionEdgeAwaiting ? (
              <span className="operator-badge-muted">
                {` · ${execution?.last_operator_position_edge_provider ?? "policy/no provider"}`}
                {` · selected ${execution?.last_operator_position_edge_selected_count ?? 0}`}
                {` · stood down ${execution?.last_operator_position_edge_stand_down_count ?? 0}`}
                {` · hard policy ${execution?.last_operator_position_edge_hard_policy_count ?? 0}`}
              </span>
            ) : null}
          </div>
          {execution?.last_operator_position_edge_summary ? (
            <div className="operator-badge-line operator-badge-muted">
              {execution.last_operator_position_edge_summary}
            </div>
          ) : null}
          {execution?.last_operator_discretionary_status ? (
            <div className="operator-badge-line">
              Position discretion: <strong>{execution.last_operator_discretionary_status}</strong>
              <span className="operator-badge-muted">
                {` · exact options ${execution.last_operator_discretionary_option_count ?? 0}`}
                {` · positions ${execution.last_operator_discretionary_position_count ?? 0}`}
                {` · blocked ${execution.last_operator_discretionary_blocked_option_count ?? 0}`}
              </span>
            </div>
          ) : null}
          {execution?.last_operator_discretionary_status ? (
            <div className="operator-badge-line operator-badge-muted">
              The Operator may select one exact guarded action or hold. If model review fails, the position is left unchanged.
            </div>
          ) : null}
          {latestPositionDecision?.intent === "scale_in" ? (
            <div className="operator-badge-line">
              Winner compound: <strong>{Number(latestPositionDecision.volume ?? 0).toFixed(2)} lots</strong>
              <span className="operator-badge-muted">
                {` Â· ${latestPositionDecision.symbol ?? "position"}`}
                {` Â· add ${latestPositionDecision.scale_in_unit_index ?? "?"}`}
                {latestPositionDecision.sizing_label ? ` Â· ${latestPositionDecision.sizing_label}` : ""}
              </span>
            </div>
          ) : null}
          {execution?.last_scale_in_status ? (
            <div className="operator-badge-line">
              Compound sizing: <strong>{execution.last_scale_in_status}</strong>
              <span className="operator-badge-muted">
                {` · options ${execution.last_scale_in_action_count ?? 0}`}
                {` · qualified parents ${execution.last_scale_in_parent_candidate_count ?? 0}`}
                {` · blocked ${execution.last_scale_in_blocker_count ?? 0}`}
                {` · unit cap ${execution.last_scale_in_max_compound_units ?? 0}`}
              </span>
            </div>
          ) : null}
          {scaleInBlockers.slice(0, 4).map((blocker, index) => (
            <div
              className="operator-badge-line operator-badge-muted"
              key={`${blocker.role ?? "primary"}:${blocker.parent_broker_ticket ?? index}`}
            >
              Compound blocked: <strong>{blocker.symbol ?? "position"}</strong>
              {` ticket ${blocker.parent_broker_ticket ?? "unknown"} · ${blocker.reason ?? "unspecified blocker"}`}
            </div>
          ))}
          {execution?.last_management_detail ? (
            <div className="operator-badge-line operator-badge-muted">
              {execution.last_management_detail}
            </div>
          ) : null}
          {simulatorHandoffCount > 0 ? (
            <div className="operator-badge-line operator-badge-muted">
              Transition supervision: <strong>{simulatorHandoffCount} simulator position{simulatorHandoffCount === 1 ? "" : "s"}</strong>
              {" remain managed while new entries use MT5 demo."}
            </div>
          ) : null}
          {execution?.last_mt5_demo_learning_sync_status ? (
            <div className="operator-badge-line operator-badge-muted">
              MT5 demo learning: <strong>{execution.last_mt5_demo_learning_sync_status}</strong>
              {` · closed history ${execution.last_mt5_demo_learning_history_count ?? 0}`}
              {` · bound ${execution.last_mt5_demo_learning_bound_trade_count ?? 0}`}
              {execution.last_mt5_demo_learning_group_learning_ready
                ? ` · ${execution.last_mt5_demo_learning_ready_group_count ?? 0} ready group(s)`
                : execution.last_mt5_demo_learning_overall_sample_ready
                  ? ` · overall count only; needs ${execution.last_mt5_demo_learning_min_samples_per_group ?? 0} comparable trades/group`
                  : " · group samples sparse"}
              {execution.last_mt5_demo_learning_sync_error
                ? ` · ${execution.last_mt5_demo_learning_sync_error}`
                : ""}
            </div>
          ) : null}
          {execution?.last_bridge_selection_status ? (
            <div className="operator-badge-line operator-badge-muted">
              Bridge: <strong>{execution.last_bridge_class ?? "unknown"}</strong>
              {` / ${execution.last_bridge_selection_status}`}
            </div>
          ) : null}
          {execution?.last_bridge_selection_detail ? (
            <div className="operator-badge-line operator-badge-muted">
              {execution.last_bridge_selection_detail}
            </div>
          ) : null}
          {executionBlocked && execution?.last_blocking_detail ? (
            <div className="operator-badge-line operator-badge-profit-warning">
              {execution.last_blocking_detail}
            </div>
          ) : null}
          {paperFallback && execution?.live_blocking_detail ? (
            <div className="operator-badge-line operator-badge-profit-warning">
              Live pending only; paper continues: {execution.live_blocking_detail}
            </div>
          ) : null}
          <div className="operator-badge-line">
            AI money movement: <strong>{moneyMovement?.status ?? (moneyMovement?.autonomous_enabled ? "ARMED / IDLE" : "OFF")}</strong>
            <span className="operator-badge-muted">
              {` · provider ${moneyMovement?.provider_touched ? "queried/touched" : "not touched"}`}
            </span>
          </div>
          {(moneyMovement?.detail || moneyMovement?.next_action) ? (
            <div className="operator-badge-line operator-badge-muted">
              {moneyMovement.detail || moneyMovement.next_action}
            </div>
          ) : null}

          {profit ? (
            <div className="operator-badge-profit">
              <div className="operator-badge-profit-goal">#1 goal: grow the balance</div>
              {activeObjective?.objective_account_established && activeAccount ? (
                <>
                  <div className="operator-badge-profit-row">
                    <span>Active execution account</span>
                    <strong>
                      {activeAccount.is_demo ? "MT5 DEMO" : "MT5 LIVE"}
                      {activeAccount.login != null ? ` #${activeAccount.login}` : ""}
                    </strong>
                  </div>
                  <div className="operator-badge-profit-row">
                    <span>Current balance</span>
                    <strong>{formatUsd(activeAccount.balance_usd)}</strong>
                  </div>
                  <div className="operator-badge-profit-row">
                    <span>Current equity</span>
                    <strong>{formatUsd(activeAccount.equity_usd)}</strong>
                  </div>
                  <div className="operator-badge-profit-row">
                    <span>Floating P&amp;L</span>
                    <span className={(activeAccount.floating_pnl_usd ?? 0) >= 0 ? "operator-badge-pos" : "operator-badge-neg"}>
                      {formatUsd(activeAccount.floating_pnl_usd, true)}
                    </span>
                  </div>
                  {activeGrowth?.cashflow_adjusted_realized_growth_usd != null ? (
                    <>
                      <div className="operator-badge-profit-row">
                        <span>Cashflow-adjusted realized growth</span>
                        <span className={activeGrowth.cashflow_adjusted_realized_growth_usd >= 0 ? "operator-badge-pos" : "operator-badge-neg"}>
                          {formatUsd(activeGrowth.cashflow_adjusted_realized_growth_usd, true)}
                        </span>
                      </div>
                      <div className="operator-badge-profit-row operator-badge-muted">
                        <span>Realized today / month</span>
                        <span>{formatUsd(activeGrowth.realized_today_usd, true)} / {formatUsd(activeGrowth.realized_month_usd, true)}</span>
                      </div>
                      <div className="operator-badge-profit-row operator-badge-muted">
                        <span>External capital (not profit)</span>
                        <span>{formatUsd(activeGrowth.net_external_capital_flow_usd)}</span>
                      </div>
                    </>
                  ) : null}
                  <div className="operator-badge-profit-row operator-badge-muted">
                    <span>Open broker positions</span>
                    <span>{activeAccount.open_position_count ?? "unavailable"}</span>
                  </div>
                  {casClosedOutcomes?.trades != null ? (
                    <div className="operator-badge-profit-row operator-badge-muted">
                      <span>CAS-bound closed MT5 P&amp;L ({casClosedOutcomes.trades})</span>
                      <span className={(casClosedOutcomes.net_pnl_usd ?? 0) >= 0 ? "operator-badge-pos" : "operator-badge-neg"}>
                        {formatUsd(casClosedOutcomes.net_pnl_usd, true)}
                      </span>
                    </div>
                  ) : null}
                  {activeGrowth?.account_growth_reconciliation?.reconciled ? (
                    <div className="operator-badge-profit-proof">
                      Realized-growth ledger reconciled to broker balance. Capital flows are excluded from profit.
                    </div>
                  ) : (
                    <div className="operator-badge-profit-warning">
                      Balance growth baseline: {activeGrowth?.balance_baseline_status ?? "UNAVAILABLE"}. Current balance is not labeled profit until deposits, withdrawals, and the baseline reconcile.
                    </div>
                  )}
                  <div className="operator-badge-profit-row operator-badge-muted" style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid #2a2f3a" }}>
                    <span>Secondary simulator evidence</span>
                    <span>not added to MT5</span>
                  </div>
                </>
              ) : (
                <div className="operator-badge-profit-warning">
                  Active execution-account scoreboard is not established; simulator performance remains secondary evidence until account identity is reconciled.
                </div>
              )}
              <div className="operator-badge-profit-row">
                <span>Simulator ledger balance</span>
                <strong>${(profit.honest_paper_balance_usd ?? 0).toLocaleString()}</strong>
              </div>
              <div className="operator-badge-profit-row">
                <span>Balance growth (every lot counts)</span>
                <span className={(profit.balance_growth_net_pnl_usd ?? profit.raw_net_pnl_usd ?? 0) >= 0 ? "operator-badge-pos" : "operator-badge-neg"}>
                  {(profit.balance_growth_net_pnl_usd ?? profit.raw_net_pnl_usd ?? 0) >= 0 ? "+" : ""}
                  ${(profit.balance_growth_net_pnl_usd ?? profit.raw_net_pnl_usd ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="operator-badge-profit-row operator-badge-muted">
                <span>Evidence it repeats (1 vote/signal)</span>
                <span className={(profit.honest_unique_signal_net_pnl_usd ?? 0) >= 0 ? "operator-badge-pos" : "operator-badge-neg"}>
                  {(profit.honest_unique_signal_net_pnl_usd ?? 0) >= 0 ? "+" : ""}
                  ${(profit.honest_unique_signal_net_pnl_usd ?? 0).toLocaleString()}
                </span>
              </div>
              <div className="operator-badge-profit-row operator-badge-muted">
                <span>{profit.unique_signals ?? 0} signals · win {Math.round((profit.unique_win_rate ?? 0) * 100)}%</span>
                <span>PF {profit.unique_profit_factor ?? "—"}</span>
              </div>
              <div className="operator-badge-profit-row operator-badge-muted">
                <span>Cluster inflation (raw/unique)</span>
                <span>{formatMetric(profit.cluster_inflation_x)}x</span>
              </div>
              <div className="operator-badge-profit-row operator-badge-muted">
                <span>Biggest copy stack</span>
                <span>{profit.biggest_cluster_size ?? 0} trades</span>
              </div>
              <div className="operator-badge-profit-row operator-badge-muted">
                <span>Avg win/loss stack</span>
                <span>{formatMetric(profit.avg_winning_stack_depth)} / {formatMetric(profit.avg_losing_stack_depth)}</span>
              </div>
              {profit.stacking_is_blind === true ? (
                <div className="operator-badge-profit-warning">
                  Blind stacking warning: losers are stacking as deep as winners, so concentration looks mechanical rather than selective.
                </div>
              ) : null}
              {(profit.test_artifacts_quarantined ?? 0) > 0 ? (
                <div className="operator-badge-profit-row operator-badge-muted">
                  <span>Test rows quarantined</span>
                  <span>
                    {profit.test_artifacts_quarantined} (${(profit.test_artifacts_net_pnl_usd ?? 0).toLocaleString()} excluded)
                  </span>
                </div>
              ) : null}
              <div
                style={{
                  marginTop: 8,
                  paddingTop: 8,
                  borderTop: "1px solid #2a2f3a",
                }}
              >
                <div className="operator-badge-profit-row">
                  <span>Daily profit objective (not a trade quota)</span>
                  <strong>
                    {(dailyObjective?.target_usd ?? profit.daily_winnings_target_usd) != null
                      ? `$${Number(dailyObjective?.target_usd ?? profit.daily_winnings_target_usd).toLocaleString()}/day`
                      : "not set"}
                    {(dailyObjective?.cap_usd ?? profit.daily_cap_usd) != null
                      ? ` · cap $${Number(dailyObjective?.cap_usd ?? profit.daily_cap_usd).toLocaleString()}`
                      : ""}
                  </strong>
                </div>
                <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                  <input
                    type="number"
                    value={targetInput}
                    onChange={(e) => setTargetInput(e.target.value)}
                    placeholder="new daily objective $"
                    aria-label="New daily profit objective in dollars"
                    style={{
                      flex: 1,
                      minWidth: 0,
                      background: "#0b0d12",
                      border: "1px solid #2a2f3a",
                      borderRadius: 6,
                      padding: "6px 8px",
                      color: "inherit",
                    }}
                  />
                  <button disabled={!targetInput.trim()} onClick={setDailyTarget}>Set</button>
                </div>
                {targetMsg ? <div className="operator-badge-muted" style={{ marginTop: 4, fontSize: 12 }}>{targetMsg}</div> : null}
                <div className="operator-badge-muted" style={{ marginTop: 5, fontSize: 12 }}>
                  Being behind this objective cannot create a setup, lower edge, increase size, loosen risk, or justify chasing losses. The cap may suppress new entries.
                </div>
              </div>

              <div className="operator-badge-profit-caveat">
                Active MT5 account truth and simulator evidence are separate scoreboards. Simulator clusters still count every filled lot for simulated balance movement and one vote per independent signal for repeatability; neither number is added to MT5.
              </div>
            </div>
          ) : null}

          {readiness ? (
            <div className="operator-badge-line operator-badge-readiness">
              <strong>37-item readiness</strong>: {readiness.ok_count ?? 0}/{readiness.item_count ?? 0} OK
              {" · "}partial {readiness.partial_count ?? 0}
              {" · "}gaps {readiness.gap_count ?? 0}
              {readiness.remaining_rows?.length
                ? ` · next ${readiness.remaining_rows
                    .slice(0, 3)
                    .map((row) => `#${row.item_number} ${row.key}`)
                    .join(", ")}`
                : ""}
            </div>
          ) : null}

          {contextDelivery?.status ? (
            <div
              className={`operator-badge-line operator-badge-context ${
                contextDelivery.decision_grade
                  ? "operator-badge-context--ok"
                  : "operator-badge-context--attention"
              }`}
            >
              <strong>Evidence packet</strong>: {contextDelivery.status}
              {` | critical ${contextDelivery.critical_sections_present?.length ?? 0}/${contextDelivery.critical_section_count ?? 0}`}
              {` | ${Number(contextDelivery.packet_json_chars ?? 0).toLocaleString()} chars`}
              {contextDelivery.evidence_fingerprint
                ? ` | ${contextDelivery.evidence_fingerprint.slice(0, 10)}`
                : ""}
              {!contextDelivery.decision_grade && contextDelivery.critical_sections_missing?.length
                ? ` | missing ${contextDelivery.critical_sections_missing.join(", ")}`
                : ""}
            </div>
          ) : null}

          {mp?.deepseek_configured ? (
            <div className="operator-badge-line operator-badge-muted">
              <strong>DeepSeek routing</strong>: Flash continuous
              {mp.role_routes?.fast?.model_ref ? ` (${mp.role_routes.fast.model_ref})` : ""}
              {" | "}Pro escalation
              {mp.role_routes?.pro?.model_ref ? ` (${mp.role_routes.pro.model_ref})` : ""}
              {mp.deepseek_transport ? ` | ${mp.deepseek_transport}` : ""}
            </div>
          ) : (
            <div className="operator-badge-line operator-badge-muted">
              DeepSeek V4 is available but not configured. Add a DeepSeek key or use Ollama Cloud sign-in.
            </div>
          )}

          {mp?.gemma4_backup_configured ? (
            <div className="operator-badge-line operator-badge-muted">
              <strong>Large-model backup</strong>: Gemma 4 31B Cloud
              {mp.role_routes?.backup?.model_ref
                ? ` (${mp.role_routes.backup.model_ref})`
                : ""}
              {mp.role_routes?.backup?.reachability
                ? ` | ${mp.role_routes.backup.reachability}`
                : ""}
            </div>
          ) : (
            <div className="operator-badge-line operator-badge-muted">
              Gemma 4 31B cloud backup is not configured.
            </div>
          )}

          {mp?.primary_configured ? (
            <div className="operator-badge-line operator-badge-muted">
              Claude budget: {formatTokens(mp?.spent_tokens ?? 0)} used
              {mp?.budget_capped ? ` of ${formatTokens(mp?.budget_tokens ?? 0)}` : " (no cap)"}
              {mp?.primary_in_cooldown
                ? ` · primary cooling down ${mp?.primary_cooldown_seconds_left ?? 0}s`
                : ""}
            </div>
          ) : (
            <div className="operator-badge-line operator-badge-muted">
              Claude fallback key is not set.
            </div>
          )}

          <div
            className={`operator-badge-line ${
              mp?.provider_reachability === "FAILED"
                ? "operator-badge-context--attention"
                : "operator-badge-muted"
            }`}
          >
            Model capability: <strong>{mp?.provider_reachability ?? "NOT_PROBED"}</strong>
            {mp?.active_model ? ` | ${mp.active_model}` : ""}
            {typeof mp?.provider_health_age_seconds === "number"
              ? ` | checked ${mp.provider_health_age_seconds}s ago`
              : ""}
            {mp?.provider_last_error ? ` | ${mp.provider_last_error}` : ""}
          </div>

          {mp?.last_switch?.to ? (
            <div className="operator-badge-line operator-badge-switch">
              ↻ switched to <strong>{mp.last_switch.to}</strong>
              {mp.last_switch.reason ? ` — ${mp.last_switch.reason}` : ""}
            </div>
          ) : null}

          {state?.last_summary ? (
            <div className="operator-badge-line operator-badge-summary">“{state.last_summary}”</div>
          ) : null}

          <div className="operator-badge-controls">
            {running ? (
              <button disabled={busy} onClick={() => act(stopOperator)}>
                Pause operator
              </button>
            ) : (
              <button disabled={busy} onClick={() => act(() => startOperator(DEFAULT_INTERVAL_SECONDS))}>
                Start operator
              </button>
            )}
            <button disabled={busy} onClick={() => act(runOperatorNow)}>
              Run once now
            </button>
          </div>

          <div className="operator-badge-keyrow">
            <div className="operator-badge-keylabel">
              DeepSeek API key{" "}
              {mp?.deepseek_key_present ? (
                <span className="operator-badge-keyok">set {mp?.deepseek_key_hint ?? ""}</span>
              ) : (
                <span className="operator-badge-keymissing">not set</span>
              )}
            </div>
            <div className="operator-badge-keyinput">
              <input
                type="password"
                placeholder="paste DeepSeek API key"
                value={deepSeekKeyInput}
                autoComplete="off"
                onChange={(e) => setDeepSeekKeyInput(e.target.value)}
                aria-label="DeepSeek API key"
              />
              <button
                disabled={busy || !deepSeekKeyInput.trim()}
                onClick={() =>
                  act(async () => {
                    await setDeepSeekKey(deepSeekKeyInput.trim());
                    setDeepSeekKeyInput("");
                    setDeepSeekKeyMsg("Key saved locally. Flash is primary; Pro handles escalations.");
                  })
                }
              >
                Save key
              </button>
            </div>
            {deepSeekKeyMsg ? (
              <div className="operator-badge-muted operator-badge-keymsg">{deepSeekKeyMsg}</div>
            ) : null}
          </div>

          <div className="operator-badge-keyrow">
            <div className="operator-badge-keylabel">
              Claude API key{" "}
              {mp?.primary_key_present ? (
                <span className="operator-badge-keyok">set {mp?.primary_key_hint ?? ""} ✓</span>
              ) : (
                <span className="operator-badge-keymissing">not set</span>
              )}
            </div>
            <div className="operator-badge-keyinput">
              <input
                type="password"
                placeholder="paste sk-ant-api03-…"
                value={keyInput}
                autoComplete="off"
                onChange={(e) => setKeyInput(e.target.value)}
                aria-label="Claude API key"
              />
              <button
                disabled={busy || !keyInput.trim()}
                onClick={() =>
                  act(async () => {
                    await setOperatorKey(keyInput.trim());
                    setKeyInput("");
                    setKeyMsg("Key saved locally — Claude will be tried on the next check.");
                  })
                }
              >
                Save key
              </button>
            </div>
            {keyMsg ? <div className="operator-badge-muted operator-badge-keymsg">{keyMsg}</div> : null}
          </div>

          <div className="operator-badge-topup">
            <input
              type="number"
              min={0}
              step={10000}
              value={topUp}
              onChange={(e) => setTopUp(e.target.value)}
              aria-label="Claude tokens to add"
            />
            <button
              disabled={busy}
              onClick={() => act(() => addOperatorTokens(Math.max(0, Number(topUp) || 0)))}
            >
              Add Claude tokens
            </button>
          </div>

          <div ref={chatRef} className="operator-badge-chat">
            <div className="operator-badge-actions-title">Talk to the operator</div>
            <textarea
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask a question, or write a consideration (e.g. bank big winners early, then restart the cycle)…"
              rows={2}
              aria-label="Message to the AI operator"
            />
            <div className="operator-badge-chat-buttons">
              <button disabled={chatBusy || !chatInput.trim()} onClick={ask}>
                Ask
              </button>
              <button disabled={chatBusy || !chatInput.trim()} onClick={saveGuidance}>
                Save as standing guidance
              </button>
            </div>
            {chatResponder ? (
              <div className="operator-badge-chat-responder">Answered by: {chatResponder}</div>
            ) : null}
            {chatReply ? <div className="operator-badge-chat-reply">{chatReply}</div> : null}

            {preview ? (
              <div
                style={{
                  marginTop: 8,
                  border: "1px solid #2a2f3a",
                  borderRadius: 8,
                  padding: 10,
                  background: "#0f1218",
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Proposed: {preview.title}</div>
                <div style={{ fontSize: 12, opacity: 0.85 }}>
                  {String(JSON.stringify(preview.current))} → <strong>{String(JSON.stringify(preview.proposed))}</strong>
                </div>
                {preview.binding?.operational_effect ? (
                  <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>{preview.binding.operational_effect}</div>
                ) : null}
                {(preview.contract_rows || []).map((row, i) => (
                  <div
                    key={`${row.field || "contract"}-${i}`}
                    style={{
                      marginTop: 8,
                      border: "1px solid #252c38",
                      borderRadius: 8,
                      padding: 8,
                      background: "#0b0d12",
                    }}
                  >
                    <div style={{ fontSize: 12, opacity: 0.88 }}>
                      <strong>{row.label || row.field || "Dial"}</strong>: {formatContractValue(row.before, row.value_kind)}
                      {" "}to <strong>{formatContractValue(row.after, row.value_kind)}</strong>
                      {row.units ? ` ${row.units}` : ""}
                    </div>
                    {row.value_kind === "subset" ? (
                      <>
                        {row.added?.length ? <div style={{ fontSize: 12, opacity: 0.76, marginTop: 4 }}>Added: {row.added.join(", ")}</div> : null}
                        {row.removed?.length ? <div style={{ fontSize: 12, opacity: 0.76, marginTop: 4 }}>Removed: {row.removed.join(", ")}</div> : null}
                      </>
                    ) : null}
                    {row.enforced_by ? <div style={{ fontSize: 12, opacity: 0.76, marginTop: 4 }}>Enforced by {row.enforced_by}.</div> : null}
                    {row.owner_bound ? <div style={{ fontSize: 12, opacity: 0.76, marginTop: 4 }}>Owner bound: {formatOwnerBound(row.owner_bound)}</div> : null}
                  </div>
                ))}
                {(preview.effects || []).map((e, i) => (
                  <div key={i} style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>{e}</div>
                ))}
                {preview.blockers && preview.blockers.length > 0 ? (
                  <div style={{ fontSize: 12, color: "#e0574a", marginTop: 6 }}>
                    Can't run yet: {preview.blockers.join("; ")}
                  </div>
                ) : null}
                <div style={{ marginTop: 8 }}>
                  {preview.journal_required ? (
                    <>
                      <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>
                        {preview.journal_prompt || "Record why this widening is not revenge, FOMO, or chasing losses."}
                      </div>
                      <textarea
                        value={journalInput}
                        onChange={(e) => setJournalInput(e.target.value)}
                        rows={3}
                        style={{
                          width: "100%",
                          boxSizing: "border-box",
                          background: "#0b0d12",
                          border: "1px solid #2a2f3a",
                          borderRadius: 6,
                          padding: 8,
                          color: "inherit",
                          marginBottom: 6,
                          resize: "vertical",
                          minHeight: 84,
                        }}
                        aria-label="Anti-impulse journal reason"
                      />
                      <div style={{ fontSize: 12, opacity: 0.76, marginBottom: 4 }}>
                        Minimum {preview.journal_minimum_length ?? 20} characters.
                      </div>
                    </>
                  ) : null}
                  <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 4 }}>
                    To run, this must say exactly: <code>{preview.confirm_phrase}</code>
                  </div>
                  <input
                    value={confirmInput}
                    onChange={(e) => setConfirmInput(e.target.value)}
                    style={{
                      width: "100%",
                      boxSizing: "border-box",
                      background: "#0b0d12",
                      border: "1px solid #2a2f3a",
                      borderRadius: 6,
                      padding: 8,
                      color: "inherit",
                      marginBottom: 6,
                    }}
                    aria-label="Type the confirmation phrase to run the command"
                  />
                  <div style={{ display: "flex", gap: 8 }}>
                    <button disabled={chatBusy} onClick={runProposed}>Confirm &amp; run</button>
                    <button
                      disabled={chatBusy}
                      onClick={() => { setProposed(null); setPreview(null); setConfirmInput(""); setJournalInput(""); }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            ) : null}
            {receiptMsg ? <div className="operator-badge-chat-reply" style={{ marginTop: 6 }}>{receiptMsg}</div> : null}

            {guidance.length > 0 ? (
              <div className="operator-badge-guidance">
                <div className="operator-badge-actions-title">Standing guidance (weighed every check)</div>
                {guidance.slice(0, 6).map((note) => (
                  <div className="operator-badge-guidance-note" key={note.note_id}>
                    <span>{note.text.length > 90 ? note.text.slice(0, 90) + "…" : note.text}</span>
                    <button
                      aria-label="Remove guidance"
                      title="Remove"
                      onClick={() => removeGuidance(note.note_id).then(setGuidance)}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          {state?.recent_actions && state.recent_actions.length > 0 ? (
            <div className="operator-badge-actions">
              <div className="operator-badge-actions-title">Recent operator actions</div>
              {state.recent_actions.slice(0, 5).map((a, i) => (
                <div className="operator-badge-action" key={i}>
                  <span className="operator-badge-muted">{String((a as Record<string, unknown>).provider ?? "")}</span>{" "}
                  {String((a as Record<string, unknown>).summary ?? (a as Record<string, unknown>).error ?? "—")}
                </div>
              ))}
            </div>
          ) : null}

          <div className="operator-badge-boundary">
            The Operator is the trading edge. Inside owner-delegated authority, its entry,
            position-management, take-profit, and configured funds-movement decisions execute
            autonomously through the guarded broker or provider path.
          </div>
        </div>
      ), document.body) : null}
    </div>
  );
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}k`;
  return String(n);
}

function formatSignedUsd(value: number): string {
  const amount = Number(value) || 0;
  const sign = amount > 0 ? "+" : amount < 0 ? "-" : "";
  return `${sign}$${Math.abs(amount).toFixed(2)}`;
}
