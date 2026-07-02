import "./AiActivityInstantBadge.css";

type AiStage = "idle" | "watch" | "analyze" | "strategize" | "test" | "execute" | "compound" | "locked" | "no_trade" | "blocked";

interface Props {
  wasteLoop?: Record<string, unknown> | null;
}

const VALID_STAGES = new Set<AiStage>(["idle", "watch", "analyze", "strategize", "test", "execute", "compound", "locked", "no_trade", "blocked"]);
const STAGE_LABELS: Record<AiStage, string> = {
  idle: "Idle", watch: "Watching", analyze: "Analyzing", strategize: "Strategizing",
  test: "Testing", execute: "Executing", compound: "Compounding", locked: "Principal Locked",
  no_trade: "No Trade", blocked: "Blocked",
};
const TRACE_LABELS: Record<AiStage, string> = {
  idle: "Idle", watch: "Watch", analyze: "Analyze", strategize: "Strategize",
  test: "Test", execute: "Execute", compound: "Compound", locked: "Lock",
  no_trade: "No Trade", blocked: "Blocked",
};

export function AiActivityInstantBadge({ wasteLoop }: Props) {
  const wasteRecord = asRecord(wasteLoop);
  const running = Boolean(wasteRecord.running);
  const stage = running ? stageFromWasteLoop(wasteRecord) : "idle";
  const conn = running ? "live" : "syncing";
  const label = STAGE_LABELS[stage];
  const sub = stage === "no_trade" ? "no edge - capital safe" : running ? "loop stage active" : "checking heartbeat";
  const connLabel = running ? "LIVE" : "SYNC";
  const connTitle = running ? "Loop connected - live stage" : "Checking loop heartbeat";
  const traceText = running ? traceTextFromWasteLoop(wasteRecord, stage) : "";

  return (
    <div
      className={`ai-activity ai-stage-${stage} ai-conn-${conn}`}
      title={`AI: ${label} - ${sub} (${connLabel})`}
      aria-live="polite"
      aria-label={`AI ${label}: ${sub}. ${connTitle}`}
    >
      <span className="aifig aifig-idle"><span className="aifig-core" /></span>
      <div className="ai-activity-text">
        <span className="ai-activity-label">{label}</span>
        <span className="ai-activity-sub">{sub}</span>
        {traceText && <span className="ai-activity-trace">{traceText}</span>}
      </div>
      <span className={`ai-conn-badge ai-conn-badge-${conn}`} title={connTitle}>
        <span className="ai-conn-dot" />
        {connLabel}
      </span>
    </div>
  );
}

function stageFromWasteLoop(wasteLoop: Record<string, unknown>): AiStage {
  return coerceAiStage(wasteLoop.current_stage)
    ?? coerceAiStage(wasteLoop.stage)
    ?? "idle";
}

function traceTextFromWasteLoop(wasteLoop: Record<string, unknown>, active: AiStage): string {
  const trace = traceFromWasteLoop(wasteLoop, active);
  return trace.length > 1 ? trace.map((stage) => TRACE_LABELS[stage]).join(" > ") : "";
}

function traceFromWasteLoop(wasteLoop: Record<string, unknown>, active: AiStage): AiStage[] {
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
  if (active !== "idle" && trace[trace.length - 1] !== active) trace.push(active);
  return active === "no_trade" ? completeNoTradeTrace(trace) : trace.slice(-8);
}

function completeNoTradeTrace(trace: AiStage[]): AiStage[] {
  const fallback: AiStage[] = ["watch", "analyze", "strategize"];
  const body = (trace.length ? trace : fallback).filter((stage) => stage !== "no_trade");
  if (body.includes("watch") && body.includes("analyze") && body.includes("strategize")) {
    if (!body.includes("test")) body.push("test");
    if (!body.includes("execute")) body.push("execute");
  }
  const completed: AiStage[] = [...body, "no_trade"];
  return completed.slice(-8);
}

function coerceAiStage(value: unknown): AiStage | null {
  if (typeof value === "string") {
    const stage = value as AiStage;
    return VALID_STAGES.has(stage) ? stage : null;
  }
  if (value && typeof value === "object" && "stage" in value) {
    return coerceAiStage((value as { stage: unknown }).stage);
  }
  return null;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}
