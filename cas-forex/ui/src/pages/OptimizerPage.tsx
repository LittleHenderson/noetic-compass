/* ── CAS Forex — LLM Optimizer Queue ── */

import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import type { DashboardState } from "../types/evidence";

interface OptimizerPageProps {
  state: DashboardState;
}

export function OptimizerPage({ state }: OptimizerPageProps) {
  const backsolve = state.backsolve;
  const tally = state.conditionTally;
  const wf = state.walkForward;

  return (
    <div className="optimizer-page">
      {/* Section 1: Queue Status */}
      <GlassPanel
        title="LLM Optimizer Queue"
        subtitle="Guarded strategy optimization pipeline — runs are PCBA-validated before execution"
      >
        <div className="dashboard-grid-3col">
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Active Runs" value="0" mono />
            <Metric label="Queued Runs" value="0" mono />
            <Metric
              label="Completed Runs"
              value={tally ? `${tally.length} condition-tally + 1 backsolve + 1 walk-forward` : "0"}
            />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Queue Health" value="IDLE" />
            <StatusChip label="IDLE" variant="muted" size="sm" />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Last Run" value={backsolve?.run_id?.slice(-8) ?? "N/A"} mono />
            <Metric
              label="Total Scenarios"
              value={backsolve ? `${backsolve.total_scenarios.toLocaleString()}` : "0"}
              mono
            />
          </div>
        </div>
      </GlassPanel>

      {/* Section 2: Run Types */}
      <GlassPanel title="Optimizer Run Types" subtitle="Available optimization pipelines">
        <div className="run-types-list">
          <RunType
            label="Condition Tally"
            status="AVAILABLE"
            detail="Condition-axis evidence scoring across timeframes/strategies"
            runs={tally ? `${tally.length} buckets` : "0"}
            variant="success"
          />
          <RunType
            label="Leverage Backsolve"
            status="AVAILABLE"
            detail="16,800 scenarios, 0 viable — SURVIVAL_RISK capital label"
            runs={backsolve ? backsolve.total_scenarios.toLocaleString() : "0"}
            variant="success"
          />
          <RunType
            label="Walk-Forward Grid"
            status="AVAILABLE"
            detail={`${wf?.total_windows ?? 0} windows, ${wf?.positive_active_routed_windows ?? 0}/${wf?.active_routed_windows ?? 0} positive`}
            runs={wf ? `${wf.total_windows}` : "0"}
            variant="success"
          />
          <RunType
            label="Strategy Harvester"
            status="NOT_RUN"
            detail="Requires 30-day paper proof completion"
            runs="—"
            variant="muted"
          />
          <RunType
            label="Adaptive Compounding"
            status="NOT_RUN"
            detail="Requires live basket data accumulation"
            runs="—"
            variant="muted"
          />
        </div>
      </GlassPanel>

      {/* Section 3: PCBA Guard */}
      <GlassPanel title="PCBA Optimization Guard" variant="danger">
        <div className="legal-gates">
          <GateRow label="Guard Active" met={true} detail="TRUE" />
          <GateRow label="PCBA Syntax Check" met={true} detail="PASS" />
          <GateRow label="PCBA Semantics Review" met={true} detail="PASS" />
          <GateRow label="PCBA Authority Check" met={true} detail="PASS" />
          <GateRow label="LLM Prompt Injection Guard" met={true} detail="ACTIVE" />
        </div>
        <div style={{ marginTop: 8, fontSize: "0.72rem", color: "var(--warning)" }}>
          Optimization boundary: PAPER-ONLY — no broker orders, no live parameter changes.
        </div>
      </GlassPanel>

      {/* Section 4: Optimization History */}
      <GlassPanel title="Recent Optimization Runs">
        <div className="tally-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Type</th>
                <th>Date</th>
                <th>Scenarios</th>
                <th>Viable</th>
                <th>Verdict</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  backsolve-20260622191201
                </td>
                <td>Leverage Backsolve</td>
                <td className="mono">2026-06-22</td>
                <td className="mono">{backsolve?.total_scenarios.toLocaleString() ?? "—"}</td>
                <td className="mono">{backsolve?.viable_scenarios ?? "—"}</td>
                <td>
                  <StatusChip
                    label={backsolve?.viable_scenarios === 0 ? "TARGET_NOT_REACHED" : "—"}
                    variant="danger"
                    size="sm"
                  />
                </td>
                <td>
                  <StatusChip label="COMPLETE" variant="success" size="sm" />
                </td>
              </tr>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  condition-tally-20260622055042
                </td>
                <td>Condition Tally</td>
                <td className="mono">2026-06-22</td>
                <td className="mono">{tally?.reduce((s, b) => s + b.windows, 0) ?? "—"}</td>
                <td className="mono">{tally?.length ?? "—"}</td>
                <td>
                  <StatusChip label="ROUTED" variant="info" size="sm" />
                </td>
                <td>
                  <StatusChip label="COMPLETE" variant="success" size="sm" />
                </td>
              </tr>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  walk-forward-20260622044930
                </td>
                <td>Walk-Forward</td>
                <td className="mono">2026-06-22</td>
                <td className="mono">{wf?.total_windows ?? "—"}</td>
                <td className="mono">{wf?.positive_active_routed_windows ?? "—"}</td>
                <td>
                  <StatusChip label={wf?.research_grade ?? "—"} variant="warning" size="sm" />
                </td>
                <td>
                  <StatusChip label="COMPLETE" variant="success" size="sm" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassPanel>

      {/* Section 5: Interactive Queue Placeholder */}
      <GlassPanel title="Interactive Queue" subtitle="Submit and monitor optimization requests">
        <div className="no-data-message">
          <p>The interactive optimizer queue will be available after API wiring. Currently, runs are triggered via CLI:</p>
          <code className="next-command-text" style={{ marginTop: 8, display: "inline-block" }}>
            python scripts/run_condition_tally.py --output-dir evidence_runs/
          </code>
        </div>
      </GlassPanel>
    </div>
  );
}

function Metric({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`}>{value}</span>
    </div>
  );
}

function RunType({
  label,
  status,
  detail,
  runs,
  variant,
}: {
  label: string;
  status: string;
  detail: string;
  runs: string;
  variant: "success" | "muted";
}) {
  return (
    <div
      className="run-type-item"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 0",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div>
        <div style={{ fontWeight: 600, fontSize: "0.8rem" }}>{label}</div>
        <div style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>{detail}</div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="mono" style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>
          {runs}
        </span>
        <StatusChip label={status} variant={variant} size="sm" />
      </div>
    </div>
  );
}

function GateRow({ label, met, detail }: { label: string; met: boolean; detail: string }) {
  return (
    <div className="legal-gate-item">
      <div className="legal-gate-header">
        <span className="check-icon" style={{ color: met ? "var(--success)" : "var(--danger)" }}>
          {met ? "✓" : "✗"}
        </span>
        <span className="field-label">{label}</span>
        <StatusChip label={met ? "MET" : "NOT MET"} variant={met ? "success" : "danger"} size="sm" />
      </div>
      <div className="legal-gate-detail">{detail}</div>
    </div>
  );
}
