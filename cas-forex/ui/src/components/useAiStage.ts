/* ── CAS Forex — useAiStage hook ──
 *
 * Returns the current stage of the AI loop (WATCH → ANALYZE → STRATEGIZE →
 * TEST → EXECUTE → COMPOUND, plus the rest states). The AiActivityIndicator
 * reads this to drive its live heartbeat.
 *
 * Honest by construction: with no poll source it stays 'idle' — it does NOT
 * invent activity. A source can be:
 *   - a function returning a stage (or a promise of one), polled on an interval, or
 *   - a URL string, fetched and read as { stage } | bare-string JSON.
 * Any unrecognized / unreachable value falls back to 'idle' rather than guessing.
 */

import { useEffect, useRef, useState } from "react";

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

const VALID_STAGES: ReadonlySet<string> = new Set<AiStage>([
  "idle",
  "watch",
  "analyze",
  "strategize",
  "test",
  "execute",
  "compound",
  "locked",
  "no_trade",
  "blocked",
]);

/** Narrow an unknown value to an AiStage, or null if it isn't one. */
export function coerceAiStage(value: unknown): AiStage | null {
  if (typeof value === "string" && VALID_STAGES.has(value)) {
    return value as AiStage;
  }
  // Accept { stage: "..." } shaped payloads.
  if (value && typeof value === "object" && "stage" in value) {
    const inner = (value as { stage: unknown }).stage;
    if (typeof inner === "string" && VALID_STAGES.has(inner)) {
      return inner as AiStage;
    }
  }
  return null;
}

/** A poll source: a function yielding a stage, or a URL to fetch one from. */
export type AiStageSource =
  | (() => AiStage | Promise<AiStage | null> | null)
  | string;

export interface UseAiStageOptions {
  /** Where to read the stage from. Omit to stay 'idle'. */
  source?: AiStageSource;
  /** Poll interval in ms. */
  intervalMs?: number;
}

async function readSource(source: AiStageSource): Promise<AiStage | null> {
  if (typeof source === "function") {
    return coerceAiStage(await source());
  }
  try {
    const res = await fetch(source, {
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) return null;
    return coerceAiStage(await res.json());
  } catch {
    return null;
  }
}

/**
 * useAiStage — current AI loop stage from an optional poll source.
 * Defaults to 'idle' and never throws.
 */
export function useAiStage(options: UseAiStageOptions = {}): AiStage {
  const { source, intervalMs = 3000 } = options;
  const [stage, setStage] = useState<AiStage>("idle");
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;

    if (!source) {
      setStage("idle");
      return () => {
        cancelled.current = true;
      };
    }

    const tick = async () => {
      const next = await readSource(source);
      if (cancelled.current) return;
      // Unreachable / unrecognized → fall back to idle rather than guessing.
      setStage(next ?? "idle");
    };

    void tick();
    const handle = window.setInterval(() => void tick(), intervalMs);

    return () => {
      cancelled.current = true;
      window.clearInterval(handle);
    };
  }, [source, intervalMs]);

  return stage;
}

/** The loop heartbeat: the current stage AND whether the loop is actually running.
 * ``live`` is true only when the backend reports a fresh, running loop — so the
 * indicator can honestly show OFFLINE vs LIVE instead of guessing. */
export interface LoopHeartbeat {
  stage: AiStage;
  live: boolean;
}

/** Poll the WASTE-loop stage endpoint ({ stage, running }). Falls back to
 * { idle, live:false } on any error / stale / unreachable — never fakes activity. */
export function useLoopHeartbeat(url: string, intervalMs = 2000): LoopHeartbeat {
  const [hb, setHb] = useState<LoopHeartbeat>({ stage: "idle", live: false });
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;

    const tick = async () => {
      try {
        const res = await fetch(url, {
          headers: { "Content-Type": "application/json" },
          signal: AbortSignal.timeout(6000),
        });
        if (!res.ok) {
          if (!cancelled.current) setHb({ stage: "idle", live: false });
          return;
        }
        const data: unknown = await res.json();
        const running = !!(data && typeof data === "object" && (data as { running?: unknown }).running);
        const stage = coerceAiStage(data) ?? "idle";
        if (!cancelled.current) setHb({ stage: running ? stage : "idle", live: running });
      } catch {
        if (!cancelled.current) setHb({ stage: "idle", live: false });
      }
    };

    void tick();
    const handle = window.setInterval(() => void tick(), intervalMs);
    return () => {
      cancelled.current = true;
      window.clearInterval(handle);
    };
  }, [url, intervalMs]);

  return hb;
}
