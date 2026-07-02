import type { DashboardState } from "../types/evidence";

interface DashboardInstantShellProps {
  state: DashboardState;
}

export function DashboardInstantShell({ state }: DashboardInstantShellProps) {
  const account = state.accountLedger?.summary;
  const risk = state.dailyBundle.latest_risk.latest_review;
  const riskBudget = state.riskBudget;
  const proofProgress = state.proofProgress;
  const accountEquity = riskBudget?.account_equity ?? risk.account_equity;
  const wasteLoop = state.wasteLoop as Record<string, unknown> | null | undefined;
  const wasteRunning = Boolean(wasteLoop?.running);
  const wasteStage = stageLabel(
    stringValue(wasteLoop?.current_stage)
      || stringValue(wasteLoop?.stage)
      || state.dailyBundle.latest_decision.latest_decision.route_action,
  );
  const plannedRiskTotal = riskBudget?.planned_risk_total_usd ?? risk.planned_risk_total_usd ?? risk.sizing.reduce(
    (sum, row) => sum + row.planned_risk_usd,
    0,
  );
  const completedTradingDays = proofProgress?.completed_trading_days ?? state.uiReadiness.completed_trading_days;
  const paperProofChainVerified = proofProgress?.paper_proof_chain_verified ?? state.uiReadiness.chains_verified.paper_proof;

  return (
    <div className="glass-panel" aria-live="polite">
      <div className="glass-panel-header">
        <div className="glass-panel-title">Dashboard</div>
        <div className="glass-panel-sub">
          {wasteRunning ? `WASTE LOOP LIVE: ${wasteStage}` : "WASTE LOOP SYNCING"}
        </div>
      </div>
      <div className="glass-panel-body">
        <div className="dashboard-grid-3col">
          <div className="metric-stack">
            <Metric label="Stage" value={wasteStage} mono />
            <Metric label="Loop" value={wasteRunning ? "LIVE" : "SYNC"} warning={!wasteRunning} />
            <Metric label="Reason" value={stringValue(wasteLoop?.last_reason) || "Reading live heartbeat"} />
          </div>
          <div className="metric-stack">
            <Metric label="Proof" value={`${completedTradingDays} / 30 days`} mono />
            <Metric label="Chain" value={paperProofChainVerified ? "PRESENT" : "WARMING"} warning={!paperProofChainVerified} />
            <Metric label="Account" value={`$${(account?.balance_usd ?? account?.deposit_usd ?? accountEquity).toLocaleString()}`} mono />
          </div>
          <div className="metric-stack">
            <Metric label="Equity" value={`$${(account?.equity_usd ?? accountEquity).toFixed(2)}`} mono />
            <Metric label="Risk Budget" value={`$${plannedRiskTotal.toFixed(2)}`} mono />
            <Metric label="Free Margin" value={`$${(account?.free_margin_usd ?? accountEquity).toFixed(2)}`} mono />
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  mono,
  warning,
}: {
  label: string;
  value: string;
  mono?: boolean;
  warning?: boolean;
}) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: warning ? "var(--warning)" : undefined }}>
        {value}
      </span>
    </div>
  );
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function stageLabel(value: string): string {
  const normalized = value.toLowerCase();
  if (normalized === "no_trade" || normalized === "no-trade" || normalized === "no trade") return "NO TRADE";
  if (!normalized || normalized === "loading" || normalized === "idle") return "CONNECTING";
  return normalized.replace(/_/g, " ").toUpperCase();
}
