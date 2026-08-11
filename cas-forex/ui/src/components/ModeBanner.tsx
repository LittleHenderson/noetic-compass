/* ── CAS Forex — Mode Banner (Always-Visible) ── */

import { useEffect, useState } from "react";
import type {
  UIReadinessReport,
  AuthorityBoundaryState,
} from "../types/evidence";
import { apiGet } from "../data/apiCore";
import { StatusChip } from "./StatusChip";

interface ModeBannerProps {
  readiness: UIReadinessReport;
  authority?: AuthorityBoundaryState;
}

interface DispatchLaneState {
  running?: boolean;
  execution_lane?: string;
  paper_learning_active?: boolean;
  paper_fallback_active?: boolean;
  live_execution_active?: boolean;
}

export function ModeBanner({ readiness, authority }: ModeBannerProps) {
  const [currentAuthority, setCurrentAuthority] = useState<AuthorityBoundaryState | undefined>(authority);
  const [dispatchLane, setDispatchLane] = useState<DispatchLaneState | null>(null);

  useEffect(() => {
    setCurrentAuthority(authority);
  }, [authority]);

  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      void apiGet<AuthorityBoundaryState>("/settings/authority-boundary", 10_000)
        .then((next) => { if (!cancelled) setCurrentAuthority(next); })
        .catch(() => undefined);
    };
    refresh();
    const poll = window.setInterval(refresh, 10_000);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      void apiGet<DispatchLaneState>("/dispatch-loop/status", 10_000)
        .then((next) => { if (!cancelled) setDispatchLane(next); })
        .catch(() => undefined);
    };
    refresh();
    const poll = window.setInterval(refresh, 10_000);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
    };
  }, []);

  const isReady =
    readiness.readiness_status === "READY_FOR_PROOF_COCKPIT_UI_UX";

  // Live status comes from the owner-flag-driven authority gate (NOT the flaky
  // MT5 connection). In non-live mode, show the active paper/demo lane instead
  // of presenting paper-safe operation as a red live-license failure.
  const liveAuthorized = currentAuthority?.live_trading_status === "AUTHORIZED";
  const liveRequested = Boolean(currentAuthority?.live_mode_requested) || currentAuthority?.requested_mode === "LIVE";
  const paperActive = Boolean(dispatchLane?.running && dispatchLane?.execution_lane === "PAPER" && dispatchLane?.paper_learning_active);
  const liveActive = Boolean(dispatchLane?.running && dispatchLane?.live_execution_active);
  const edge = currentAuthority?.trading_edge_status ?? "OPEN";
  const modeChipLabel = liveActive
    ? "LIVE ACTIVE"
    : liveAuthorized
      ? "LIVE AUTHORIZED / LOOP OFF"
    : liveRequested && paperActive
      ? "PAPER ACTIVE / LIVE PENDING"
    : liveRequested
      ? "LIVE REQUESTED / BLOCKED"
      : "PAPER / DEMO ACTIVE";
  const modeChipVariant = liveAuthorized ? "success" : liveRequested ? "warning" : "paper";

  return (
    <div className="mode-banner">
      <div className="mode-banner-left">
        <StatusChip
          label={modeChipLabel}
          variant={modeChipVariant}
          size="sm"
        />
        <span className="mode-banner-label">{liveActive ? "LIVE" : liveAuthorized ? "LIVE READY" : paperActive ? "PAPER" : liveRequested ? "LIVE PENDING" : "PAPER"}</span>
        <span className="mode-banner-sep">|</span>
        <span className="mode-banner-label">edge: {edge}</span>
        <span className="mode-banner-sep">|</span>
        <span className="mode-banner-label">
          {readiness.completed_trading_days} / 30 days
        </span>
      </div>
      <div className="mode-banner-right">
        <StatusChip
          label={isReady ? "COCKPIT READY" : "PROOF PENDING"}
          variant={isReady ? "success" : "warning"}
          size="sm"
        />
        <span className="mode-banner-label mono">
          chains:{" "}
          {readiness.chains_verified.paper_proof &&
          readiness.chains_verified.paper_decision &&
          readiness.chains_verified.paper_risk
            ? "3/3 ✓"
            : "INCOMPLETE"}
        </span>
      </div>
    </div>
  );
}
