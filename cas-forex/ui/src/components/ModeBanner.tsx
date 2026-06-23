/* ── CAS Forex — Mode Banner (Always-Visible) ── */

import type {
  UIReadinessReport,
} from "../types/evidence";
import { StatusChip } from "./StatusChip";

interface ModeBannerProps {
  readiness: UIReadinessReport;
}

export function ModeBanner({ readiness }: ModeBannerProps) {
  const isReady =
    readiness.readiness_status === "READY_FOR_PROOF_COCKPIT_UI_UX";

  return (
    <div className="mode-banner">
      <div className="mode-banner-left">
        <StatusChip
          label="NOT LICENSED"
          variant="danger"
          size="sm"
        />
        <span className="mode-banner-label">PAPER_MT5</span>
        <span className="mode-banner-sep">|</span>
        <span className="mode-banner-label">live_mode=false</span>
        <span className="mode-banner-sep">|</span>
        <span className="mode-banner-label">edge: OPEN</span>
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
