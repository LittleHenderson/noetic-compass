/* ── AI Activity Indicator ──
   A live visual heartbeat: a distinct animated figure for every stage of the
   AI/agent loop, from watching the market to executing a trade. Drive it with a
   real `stage` once the W→A→S→T→E loop is wired; until then it self-cycles so
   every figure is visible. */

import { useEffect, useMemo, useState } from "react";
import { getApiBase } from "../data/api";
import { useLoopHeartbeat } from "./useAiStage";
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
}

export function AiActivityIndicator({ stage, demo = false, intervalMs = 2200 }: Props) {
  // DEFAULT: read the actual WASTE-loop stage from the backend. It shows OFFLINE/idle
  // until the loop is running, then pulses with what the AI is really doing — no faking.
  const heartbeatUrl = useMemo(() => `${getApiBase()}/waste-loop/stage`, []);
  const hb = useLoopHeartbeat(heartbeatUrl, 2000);

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
  const conn: "live" | "demo" | "offline" =
    controlled ? "live" : demo ? "demo" : hb.live ? "live" : "offline";
  const meta = STAGE_META[active];
  const connLabel = conn === "live" ? "LIVE" : conn === "demo" ? "DEMO" : "OFFLINE";
  const connTitle =
    conn === "live" ? "Loop connected — live stage" :
    conn === "demo" ? "Demo preview — not connected to the loop" :
    "Loop not running — engine offline";

  return (
    <div
      className={`ai-activity ai-stage-${active} ai-conn-${conn}`}
      title={`AI: ${meta.label} — ${meta.sub} (${connLabel})`}
      aria-live="polite"
      aria-label={`AI ${meta.label}: ${meta.sub}. ${connTitle}`}
    >
      <Figure stage={active} />
      <div className="ai-activity-text">
        <span className="ai-activity-label">{meta.label}</span>
        <span className="ai-activity-sub">{meta.sub}</span>
      </div>
      <span className={`ai-conn-badge ai-conn-badge-${conn}`} title={connTitle}>
        <span className="ai-conn-dot" />
        {connLabel}
      </span>
    </div>
  );
}
