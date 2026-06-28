/* ── CAS Forex — Mode Banner (Always-Visible) ── */

import type {
  UIReadinessReport,
  AuthorityBoundaryState,
} from "../types/evidence";
import { StatusChip } from "./StatusChip";

interface ModeBannerProps {
  readiness: UIReadinessReport;
  authority?: AuthorityBoundaryState;
}

export function ModeBanner({ readiness, authority }: ModeBannerProps) {
  const isReady =
    readiness.readiness_status === "READY_FOR_PROOF_COCKPIT_UI_UX";

  // Live status comes from the owner-flag-driven authority gate (NOT the flaky
  // MT5 connection), so a connected DEMO account never reads as licensed.
  const liveAuthorized = authority?.live_trading_status === "AUTHORIZED";
  const edge = authority?.trading_edge_status ?? "OPEN";

  return (
    <div className="mode-banner">
      <div className="mode-banner-left">
        <StatusChip
          label={liveAuthorized ? "LIVE AUTHORIZED" : "NOT LICENSED"}
          variant={liveAuthorized ? "success" : "danger"}
          size="sm"
        />
        <span className="mode-banner-label">{liveAuthorized ? "LIVE" : "PAPER"}</span>
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
