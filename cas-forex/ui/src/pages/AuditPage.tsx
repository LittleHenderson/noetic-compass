/* ── CAS Forex — Audit Console Page ── */

import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import type { DashboardState } from "../types/evidence";
import "./AuditPage.css";

interface AuditPageProps {
  state: DashboardState;
}

const PIPELINE_STAGES = [
  { id: "forecast", label: "Forecast Harness", desc: "Signal generation from strategy models" },
  { id: "gate0", label: "Gate 0: CAS Compiler", desc: "Expression validation, admissibility" },
  { id: "gate1", label: "Gate 1: Risk", desc: "Position sizing, drawdown, exposure" },
  { id: "gate2", label: "Gate 2: Macro", desc: "News blackout, economic calendar" },
  { id: "gate3", label: "Gate 3: Market", desc: "Spread, liquidity, session hours" },
  { id: "gate4", label: "Gate 4: Execution", desc: "Broker fill, slippage, reject" },
  { id: "broker", label: "Broker Outcome", desc: "Order accept/reject/suppress" },
  { id: "posttrade", label: "Post-Trade", desc: "Reconciliation, P&L, close" },
  { id: "evidence", label: "Evidence Store", desc: "Hash-chain write, packet seal" },
  { id: "lock", label: "Live Lock Controller", desc: "LIVE_LOCKED boundary enforcement" },
] as const;

export function AuditPage({ state }: AuditPageProps) {
  const { dailyBundle: b } = state;
  const decision = b.latest_decision.latest_decision;

  return (
    <div className="audit-page">
      <GlassPanel title="Pipeline Trace" subtitle={`${decision.date} — ${decision.route_action}`}>
        <div className="pipeline">
          {PIPELINE_STAGES.map((stage, idx) => {
            const isPaperLoop =
              stage.id === "forecast" ||
              stage.id === "gate1" ||
              stage.id === "gate2";

            const isNotRun =
              stage.id === "gate0" ||
              stage.id === "gate3";

            const status = isPaperLoop
              ? "PAPER"
              : isNotRun
                ? "NOT_RUN"
                : "SUPPRESSED";

            return (
              <div key={stage.id} className="pipeline-stage">
                <div className="pipeline-connector">
                  {idx > 0 && <div className="pipeline-line" />}
                  <div
                    className={`pipeline-dot ${
                      status === "PAPER"
                        ? "paper"
                        : status === "NOT_RUN"
                          ? "not-run"
                          : "suppressed"
                    }`}
                  />
                </div>
                <div className="pipeline-card">
                  <div className="pipeline-card-header">
                    <span className="pipeline-stage-num">
                      {idx + 1}
                    </span>
                    <span className="pipeline-stage-label">
                      {stage.label}
                    </span>
                    <StatusChip
                      label={status}
                      variant={
                        status === "PAPER"
                          ? "paper"
                          : status === "NOT_RUN"
                            ? "muted"
                            : "warning"
                      }
                      size="sm"
                    />
                  </div>
                  <div className="pipeline-stage-desc">
                    {stage.desc}
                  </div>
                  {isNotRun && (
                    <div
                      className="pipeline-not-run-reason"
                      style={{
                        color: "var(--text-muted)",
                        fontSize: "0.75rem",
                        fontStyle: "italic",
                        marginTop: 4,
                      }}
                    >
                      Not exercised in paper loop — {stage.id === "gate0"
                        ? "no CAS expression compiled (paper route uses strategy signal directly)"
                        : "no live market gate applied (paper route uses historical close)"}
                    </div>
                  )}
                  {stage.id === "lock" && (
                    <div style={{ marginTop: 4 }}>
                      <StatusChip
                        label="LIVE_LOCKED"
                        variant="danger"
                        size="sm"
                      />
                      <span
                        style={{
                          color: "var(--text-muted)",
                          fontSize: "0.75rem",
                          marginLeft: 8,
                        }}
                      >
                        All live execution suppressed
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </GlassPanel>

      {/* Evidence Packet Summary */}
      <GlassPanel title="Evidence Packet" subtitle="Paper day-1 trace">
        <div className="evidence-summary">
          <div className="evidence-row">
            <span className="field-label">Date</span>
            <span className="field-value">{b.date}</span>
          </div>
          <div className="evidence-row">
            <span className="field-label">Route Action</span>
            <StatusChip label={decision.route_action} variant="paper" size="sm" />
          </div>
          <div className="evidence-row">
            <span className="field-label">Macro Gate</span>
            <StatusChip
              label={decision.macro_status}
              variant={decision.macro_status === "PASS" ? "success" : "warning"}
              size="sm"
            />
          </div>
          <div className="evidence-row">
            <span className="field-label">Event Context</span>
            <span className="field-value">{decision.event_context}</span>
          </div>
          <div className="evidence-row">
            <span className="field-label">Symbols Routed</span>
            <span className="field-value mono">
              {decision.symbol_decisions.map((d) => d.symbol).join(", ")}
            </span>
          </div>
          <div className="evidence-row">
            <span className="field-label">Proof Chain</span>
            <StatusChip
              label={b.latest_proof.chain_verified ? "VERIFIED" : "FAILED"}
              variant={b.latest_proof.chain_verified ? "success" : "danger"}
              size="sm"
            />
          </div>
          <div className="evidence-row">
            <span className="field-label">WORM</span>
            <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
              UNAVAILABLE — local hash chain only
            </span>
          </div>
          <div className="evidence-notes">
            {decision.notes.map((note, i) => (
              <div key={i} className="evidence-note">
                {note}
              </div>
            ))}
          </div>
        </div>
      </GlassPanel>

      {/* Symbol-Level Traces */}
      {decision.symbol_decisions.map((d) => (
        <GlassPanel
          key={d.proposal.proposal_id}
          title={`Trace: ${d.symbol}`}
          subtitle={d.proposal.proposal_id}
          variant="info"
        >
          <div className="trace-detail">
            <div className="trace-grid">
              <div className="trace-field">
                <span className="field-label">Direction</span>
                <StatusChip label={d.direction} variant="info" size="sm" />
              </div>
              <div className="trace-field">
                <span className="field-label">Confidence</span>
                <span className="field-value mono">
                  {(d.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div className="trace-field">
                <span className="field-label">Entry</span>
                <span className="field-value mono">
                  {d.proposal.entry_price.toFixed(2)}
                </span>
              </div>
              <div className="trace-field">
                <span className="field-label">SL</span>
                <span className="field-value mono" style={{ color: "var(--danger)" }}>
                  {d.proposal.stop_loss.toFixed(2)}
                </span>
              </div>
              <div className="trace-field">
                <span className="field-label">TP</span>
                <span className="field-value mono" style={{ color: "var(--success)" }}>
                  {d.proposal.take_profit.toFixed(2)}
                </span>
              </div>
              <div className="trace-field">
                <span className="field-label">Model</span>
                <span className="field-value mono">{d.proposal.model_version}</span>
              </div>
            </div>
            <div className="trace-rationale">{d.proposal.rationale}</div>
          </div>
        </GlassPanel>
      ))}
    </div>
  );
}
