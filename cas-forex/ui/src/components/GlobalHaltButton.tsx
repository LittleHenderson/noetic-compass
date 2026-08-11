/* ── CAS Forex — Global Halt ──
 *
 * The only emergency stop used to live inside DashboardOperationsWorkbench:
 * lazy-mounted behind a ~1.6s idle timer, at the bottom of the longest page in
 * the app, reachable from exactly one route. A kill switch you have to scroll
 * to, wait for, and be on the right page for is not a kill switch.
 *
 * This one is mounted eagerly in the shell header on every page. It calls
 * apiCore directly rather than the 5,000-line api.ts barrel so that keeping it
 * in the initial bundle stays cheap.
 *
 * Latching the halt is destructive, so it is two-step: press, then confirm.
 * The confirm state self-cancels after 4s to avoid arming it by accident.
 */

import { useEffect, useRef, useState } from "react";
import { apiPost, apiPostJson } from "../data/apiCore";

type HaltPhase = "idle" | "confirm" | "working" | "done" | "partial";

const CONFIRM_TIMEOUT_MS = 4_000;
const RESULT_TIMEOUT_MS = 6_000;

export function GlobalHaltButton() {
  const [phase, setPhase] = useState<HaltPhase>("idle");
  const [detail, setDetail] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);

  function clearTimer() {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  useEffect(() => clearTimer, []);

  async function runHalt() {
    clearTimer();
    setPhase("working");
    setDetail(null);

    // Fire all three in parallel and report honestly on partial failure — a
    // halt that only half-landed must not read as a clean stop.
    const results = await Promise.allSettled([
      apiPostJson<unknown, { reason: string }>("/auto-halt/emergency-stop", {
        reason: "OWNER_GLOBAL_HALT_HEADER",
      }),
      apiPost<unknown>("/waste-loop-control/stop"),
      apiPost<unknown>("/dispatch-loop/stop"),
    ]);

    const failed = results.filter((r) => r.status === "rejected").length;
    if (failed === 0) {
      setPhase("done");
      setDetail("Halt latched. Loops stopped.");
    } else {
      setPhase("partial");
      setDetail(`${failed} of 3 stop calls failed — verify on Settings.`);
    }
    timerRef.current = window.setTimeout(() => {
      setPhase("idle");
      setDetail(null);
    }, RESULT_TIMEOUT_MS);
  }

  function onClick() {
    if (phase === "working") return;
    if (phase === "confirm") {
      void runHalt();
      return;
    }
    setPhase("confirm");
    clearTimer();
    timerRef.current = window.setTimeout(() => setPhase("idle"), CONFIRM_TIMEOUT_MS);
  }

  const label =
    phase === "confirm" ? "Confirm halt"
    : phase === "working" ? "Halting…"
    : phase === "done" ? "Halted"
    : phase === "partial" ? "Partial halt"
    : "Halt";

  return (
    <button
      type="button"
      className={`global-halt global-halt-${phase}`}
      onClick={onClick}
      disabled={phase === "working"}
      aria-live="polite"
      title={
        detail
        ?? (phase === "confirm"
          ? "Press again to latch the auto-halt and stop the WASTE and dispatch loops."
          : "Emergency stop: latches auto-halt and stops the WASTE and dispatch loops.")
      }
    >
      <span className="global-halt-icon" aria-hidden="true">■</span>
      <span className="global-halt-label">{label}</span>
    </button>
  );
}
