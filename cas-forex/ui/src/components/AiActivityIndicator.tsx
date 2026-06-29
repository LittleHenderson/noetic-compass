/* ── AI Activity Indicator ──
   A live visual heartbeat: a distinct animated figure for every stage of the
   AI/agent loop, from watching the market to executing a trade. Drive it with a
   real `stage` once the W→A→S→T→E loop is wired; until then it self-cycles so
   every figure is visible. */

import { useEffect, useState } from "react";
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
  /** Drive the indicator from real loop state. If omitted, it self-cycles (demo). */
  stage?: AiStage;
  /** Demo cycle interval (ms) when no stage is supplied. */
  intervalMs?: number;
}

export function AiActivityIndicator({ stage, intervalMs = 2200 }: Props) {
  const [demoStage, setDemoStage] = useState<AiStage>("watch");

  useEffect(() => {
    if (stage) return; // real stage supplied — no demo cycle
    let i = 0;
    const id = setInterval(() => {
      i = (i + 1) % DEMO_ORDER.length;
      setDemoStage(DEMO_ORDER[i]);
    }, intervalMs);
    return () => clearInterval(id);
  }, [stage, intervalMs]);

  const active = stage ?? demoStage;
  const meta = STAGE_META[active];

  return (
    <div
      className={`ai-activity ai-stage-${active}`}
      title={`AI: ${meta.label} — ${meta.sub}`}
      aria-live="polite"
      aria-label={`AI ${meta.label}: ${meta.sub}`}
    >
      <Figure stage={active} />
      <div className="ai-activity-text">
        <span className="ai-activity-label">{meta.label}</span>
        <span className="ai-activity-sub">{meta.sub}</span>
      </div>
    </div>
  );
}
