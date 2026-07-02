/* ── AI Activity Indicator ──
   A live visual heartbeat: a distinct animated figure for every stage of the
   AI/agent loop, from watching the market to executing a trade. Drive it with a
   real `stage` once the W→A→S→T→E loop is wired; until then it self-cycles so
   every figure is visible. */

import { useEffect, useMemo, useState } from "react";
import { fetchDispatchLoopStatus, fetchWasteLoopStage, fetchWasteLoopStatus } from "../data/loopStatusApi";
import { coerceAiStage, type LoopHeartbeat, useLoopHeartbeat } from "./useAiStage";
import "./AiActivityIndicator.css";

export type AiStage =
  | "idle"
  | "watch"
  | "analyze"
  | "strategize"
  | "test"
  | "execute"
  | "compound"
  | "locked"
  | "no_trade"
  | "blocked";

const STAGE_META: Record<AiStage, { label: string; sub: string }> = {
  idle: { label: "Idle", sub: "standing by" },
  watch: { label: "Watching", sub: "scanning the market" },
  analyze: { label: "Analyzing", sub: "lacunarity · cascade · CJT" },
  strategize: { label: "Strategizing", sub: "forming a setup" },
  test: { label: "Testing", sub: "vs the null gate" },
  execute: { label: "Executing", sub: "placing the order" },
  compound: { label: "Compounding", sub: "stacking a winner" },
  locked: { label: "Principal Locked", sub: "stop at breakeven" },
  no_trade: { label: "No Trade", sub: "no edge — capital safe" },
  blocked: { label: "Blocked", sub: "gate rejected" },
};

const TRACE_LABEL: Record<AiStage, string> = {
  idle: "Idle",
  watch: "Watch",
  analyze: "Analyze",
  strategize: "Strategize",
  test: "Test",
  execute: "Execute",
  compound: "Compound",
  locked: "Lock",
  no_trade: "No Trade",
  blocked: "Blocked",
};

// Demo order walks the whole loop so every figure shows.
const DEMO_ORDER: AiStage[] = [
  "watch", "analyze", "strategize", "test", "execute",
  "compound", "locked", "no_trade", "blocked", "idle",
];

function Figure({ stage }: { stage: AiStage }) {
  switch (stage) {
    case "watch":
      return (
        <span className="aifig aifig-watch">
          <span className="aifig-ring" />
          <span className="aifig-sweep" />
          <span className="aifig-core" />
        </span>
      );
    case "analyze":
      return (
        <span className="aifig aifig-analyze">
          <span className="aifig-orbit"><i /><i /><i /></span>
          <span className="aifig-core" />
        </span>
      );
    case "strategize":
      return <span className="aifig aifig-think"><i /><i /><i /></span>;
    case "test":
      return <span className="aifig aifig-test"><span className="aifig-coin" /></span>;
    case "execute":
      return (
        <span className="aifig aifig-exec">
          <span className="aifig-burst" />
          <span className="aifig-burst d2" />
          <span className="aifig-core" />
        </span>
      );
    case "compound":
      return <span className="aifig aifig-compound"><i /><i /><i /><i /></span>;
    case "locked":
      return <span className="aifig aifig-locked"><span className="aifig-shield" /></span>;
    case "no_trade":
      return <span className="aifig aifig-notrade"><span className="aifig-dash" /></span>;
    case "blocked":
      return <span className="aifig aifig-blocked"><span className="aifig-x" /></span>;
    default:
      return <span className="aifig aifig-idle"><span className="aifig-core" /></span>;
  }
}

interface Props {
  /** Force a stage (controlled). Omit to read the real loop heartbeat. */
  stage?: AiStage;
  /** Opt-in self-cycle showcase (off by default — the real indicator is NOT a demo). */
  demo?: boolean;
  /** Demo cycle interval (ms). */
  intervalMs?: number;
  /** First-paint WASTE status from /dashboard/fast. The heartbeat route still takes over after poll. */
  wasteLoop?: Record<string, unknown> | null;
}

export function AiActivityIndicator({ stage, demo = false, intervalMs = 2200, wasteLoop }: Props) {
  // DEFAULT: read the actual WASTE-loop stage from the backend. It shows OFFLINE/idle
  // until the loop is running, then pulses with what the AI is really doing — no faking.
  const heartbeatSource = useMemo(() => fetchLoopHeartbeatPayload, []);
  const initialHeartbeat = useMemo(() => heartbeatFromWasteLoop(wasteLoop), [wasteLoop]);
  const hb = useLoopHeartbeat(heartbeatSource, 2000, initialHeartbeat);

  const [demoStage, setDemoStage] = useState<AiStage>("watch");
  useEffect(() => {
    if (!demo) return;
    let i = 0;
    const id = setInterval(() => {
      i = (i + 1) % DEMO_ORDER.length;
      setDemoStage(DEMO_ORDER[i]);
    }, intervalMs);
    return () => clearInterval(id);
  }, [demo, intervalMs]);

  const controlled = stage !== undefined;
  const active: AiStage = controlled ? stage : demo ? demoStage : (hb.stage as AiStage);
  const conn: "live" | "demo" | "offline" | "syncing" =
    controlled ? "live" : demo ? "demo" : hb.live === null ? "syncing" : hb.live ? "live" : "offline";
  const meta = STAGE_META[active];
  const trace = controlled || demo ? [] : compactTrace(hb.trace, active);
  const traceLabels = wasteTraceLabels(trace, active);
  const traceText = traceLabels.length > 1 ? traceLabels.join(" > ") : "";
  const traceTitle = wasteTraceTitle(trace, active, traceText);
  const connLabel = conn === "live" ? "LIVE" : conn === "demo" ? "DEMO" : conn === "syncing" ? "SYNC" : "OFFLINE";
  const connTitle =
    conn === "live" ? "Loop connected — live stage" :
    conn === "demo" ? "Demo preview — not connected to the loop" :
    "Loop not running — engine offline";

  const displayConnTitle = conn === "syncing" ? "Checking loop heartbeat" : connTitle;

  return (
    <div
      className={`ai-activity ai-stage-${active} ai-conn-${conn}`}
      title={`AI: ${meta.label} — ${meta.sub} (${connLabel})`}
      aria-live="polite"
      aria-label={`AI ${meta.label}: ${meta.sub}. ${displayConnTitle}`}
    >
        <Figure stage={active} />
      <div className="ai-activity-text">
        <span className="ai-activity-label">{meta.label}</span>
        <span className="ai-activity-sub">{meta.sub}</span>
        {traceText && <span className="ai-activity-trace" title={traceTitle}>{traceText}</span>}
      </div>
      <span className={`ai-conn-badge ai-conn-badge-${conn}`} title={displayConnTitle}>
        <span className="ai-conn-dot" />
        {connLabel}
      </span>
    </div>
  );
}

async function fetchLoopHeartbeatPayload(): Promise<unknown> {
  const wasteStage = await fetchWasteLoopStage();
  if (wasteStage?.running) return wasteStage;

  const wasteStatus = await fetchWasteLoopStatus();
  if (wasteStatus?.running) {
    return {
      ...wasteStatus,
      running: true,
      stage: wasteStatus.current_stage ?? wasteStatus.stage ?? "watch",
    };
  }

  const dispatch = await fetchDispatchLoopStatus();
  if (dispatch?.running) {
    return {
      ...dispatch,
      running: true,
      stage: "watch",
    };
  }

  return wasteStage ?? dispatch;
}

function heartbeatFromWasteLoop(wasteLoop?: Record<string, unknown> | null): LoopHeartbeat | null {
  if (!wasteLoop) return null;
  const running = Boolean(wasteLoop.running);
  const stage =
    coerceAiStage(wasteLoop.current_stage)
    ?? coerceAiStage(wasteLoop.stage)
    ?? coerceAiStage(latestStageFromDurableCycle(asRecord(wasteLoop.durable_cycle)))
    ?? "idle";
  return {
    stage: running ? stage : "idle",
    live: running,
    trace: running ? traceFromWasteLoop(wasteLoop) : [],
  };
}

function latestStageFromDurableCycle(cycle: Record<string, unknown>): string | null {
  const trace = cycle.stage_trace;
  if (!Array.isArray(trace)) return null;
  for (let index = trace.length - 1; index >= 0; index -= 1) {
    const value = trace[index];
    if (typeof value === "string") return value;
  }
  return null;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

function compactTrace(trace: AiStage[] | undefined, active: AiStage): AiStage[] {
  const out: AiStage[] = [];
  for (const stage of trace ?? []) {
    if (stage === "idle") continue;
    if (out[out.length - 1] === stage) continue;
    out.push(stage);
  }
  if (active !== "idle" && out[out.length - 1] !== active) out.push(active);
  return out.slice(-6);
}

function wasteTraceLabels(trace: AiStage[], active: AiStage): string[] {
  if (active !== "no_trade" || trace.length === 0) {
    return trace.map((item) => TRACE_LABEL[item]);
  }

  const withoutTerminal = trace[trace.length - 1] === active ? trace.slice(0, -1) : trace;
  const labels = withoutTerminal.map((item) => TRACE_LABEL[item]);
  if (!withoutTerminal.includes("test")) labels.push(TRACE_LABEL.test);
  if (!withoutTerminal.includes("execute")) labels.push(TRACE_LABEL.execute);
  labels.push(TRACE_LABEL.no_trade);
  return labels;
}

function wasteTraceTitle(trace: AiStage[], active: AiStage, traceText: string): string {
  if (!traceText) return "";
  const terminal = active === "no_trade" || active === "blocked";
  if (!terminal) return traceText;
  if (!trace.includes("test")) {
    return `${traceText}. Test and Execute are armed; this cycle ended before a candidate reached the edge gate.`;
  }
  if (!trace.includes("execute")) {
    return `${traceText}. Execute is armed; this cycle did not receive a fresh PASS token.`;
  }
  return traceText;
}

function traceFromWasteLoop(wasteLoop: Record<string, unknown>): AiStage[] {
  const durableCycle = asRecord(wasteLoop.durable_cycle);
  const rawTrace = Array.isArray(wasteLoop.stage_trace)
    ? wasteLoop.stage_trace
    : Array.isArray(durableCycle.stage_trace)
      ? durableCycle.stage_trace
      : [];
  const trace: AiStage[] = [];
  for (const item of rawTrace) {
    const stage = coerceAiStage(item);
    if (!stage || stage === "idle") continue;
    if (trace[trace.length - 1] === stage) continue;
    trace.push(stage);
  }
  return trace.slice(-8);
}
