/* ── CAS Forex — PCBA/CJT Diagnostics ── */
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { PCBA_COCKPIT_FIXTURE } from "../data/fixtures";
import type { DashboardState, ReadinessCheck } from "../types/evidence";

interface PcbaPageProps {
  state: DashboardState;
}

export function PcbaPage({ state }: PcbaPageProps) {
  const pcba = state.pcba ?? PCBA_COCKPIT_FIXTURE;

  const pcbaChecks = pcba.pcba_readiness.checks;
  const cjtChecks = pcba.cjt_readiness.checks;
  const ccbChecks = pcba.ccb_readiness.board_checks;
  const sourceLabel = pcba.source === "live_api" ? "LIVE API" : "FIXTURE FALLBACK";

  return (
    <div className="pcba-page">
      <GlassPanel title="PCBA Active Cockpit" subtitle="Live diagnostic payload from CAS API">
        <div className="dashboard-grid-3col">
          <div className="metric-stack">
            <Metric label="Panels" value={pcba.panels_active ? "ACTIVE" : "INACTIVE"} />
            <Metric label="Source" value={sourceLabel} mono />
          </div>
          <div className="metric-stack">
            <Metric label="PCBA Checks" value={`${pcba.summary.pcba_ready_checks}/${pcba.summary.pcba_total_checks}`} mono />
            <Metric label="CJT Checks" value={`${pcba.summary.cjt_ready_checks}/${pcba.summary.cjt_total_checks}`} mono />
          </div>
          <div className="metric-stack">
            <Metric label="CCB Designs" value={pcba.summary.ccb_designs_well_formed ? "CRC PASS" : "CHECK FAIL"} danger={!pcba.summary.ccb_designs_well_formed} />
            <Metric label="Boundary Honest" value={pcba.summary.current_boundary_honest ? "YES" : "NO"} danger={!pcba.summary.current_boundary_honest} />
          </div>
        </div>
        <div className="optimizer-detail" style={{ marginTop: 10 }}>{pcba.claim_boundary}</div>
      </GlassPanel>

      <GlassPanel title="PCBA Reference Boards" subtitle={`${pcba.reference_boards.length} live board diagnostics`}>
        <div className="pcba-boards-grid">
          {pcba.reference_boards.map((board) => (
            <div key={board.board_id} className="pcba-board-card">
              <div className="pcba-board-header">
                <code className="pcba-board-id">{board.board_id}</code>
                <StatusChip label={board.claim_ceiling} variant={chipVariant(board.claim_ceiling)} size="sm" />
              </div>
              <div className="pcba-board-name">{titleize(board.board_kind)}</div>
              <div className="pcba-board-purpose">{board.purpose}</div>
              <div className="pcba-board-components">
                {board.component_kinds.map((component) => <span key={component} className="pcba-component-chip">{component.toUpperCase()}</span>)}
              </div>
              <div className="pcba-claim-note">Unlock live: {board.can_unlock_live_trading ? "YES" : "NO"} · Broker ACCEPT: {board.can_create_broker_accept ? "YES" : "NO"}</div>
            </div>
          ))}
        </div>
      </GlassPanel>

      <GlassPanel title="PCBA Production Readiness" subtitle={pcba.pcba_readiness.summary} variant="warning">
        <ReadinessList checks={pcbaChecks} />
      </GlassPanel>

      <GlassPanel title="CJT Production Readiness" subtitle={pcba.cjt_readiness.summary} variant="warning">
        <ReadinessList checks={cjtChecks} />
      </GlassPanel>

      <GlassPanel title="CCB Readiness" subtitle={pcba.ccb_readiness.summary}>
        <div className="cjt-features">
          {ccbChecks.map((check) => (
            <div key={check.board_kind} className="cjt-feature-row">
              <div className="cjt-feature-header">
                <code className="cjt-feature-name">{titleize(check.board_kind ?? "unknown_board")}</code>
                <StatusChip label={check.status} variant={chipVariant(check.status)} size="sm" />
                <span className="cjt-checks mono">{evidenceLabel(check)}</span>
              </div>
              <div className="cjt-feature-detail">{check.rationale ?? "CCB diagnostic readiness."}</div>
              <Progress check={check} />
            </div>
          ))}
          <div className="cjt-feature-row">
            <div className="cjt-feature-header">
              <code className="cjt-feature-name">CjtPredictionHead</code>
              <StatusChip label={pcba.ccb_readiness.prediction_head.status} variant={chipVariant(pcba.ccb_readiness.prediction_head.status)} size="sm" />
              <span className="cjt-checks mono">{pcba.ccb_readiness.prediction_head.present_evidence.length}/{pcba.ccb_readiness.prediction_head.required_evidence.length} checks</span>
            </div>
            <div className="cjt-feature-detail">{pcba.ccb_readiness.prediction_head.rationale}</div>
            <div className="cjt-progress-track"><div className="cjt-progress-fill" style={{ width: `${percent(pcba.ccb_readiness.prediction_head.present_evidence.length, pcba.ccb_readiness.prediction_head.required_evidence.length)}%` }} /></div>
          </div>
        </div>
      </GlassPanel>

      <GlassPanel title="LLM Optimizer Guard" subtitle={`${pcba.optimizer_guard.guard} — active under CAS/PCBA`}>
        <div className="dashboard-grid-3col">
          <div className="metric-stack"><Metric label="Guard" value={pcba.optimizer_guard.active ? "ACTIVE" : "INACTIVE"} /><Metric label="Boundary" value="ENFORCED" /></div>
          <div className="metric-stack"><Metric label="Research Queue" value={`${pcba.optimizer_guard.proposal_counts.research_queue}`} mono /><Metric label="Flagged" value={`${pcba.optimizer_guard.proposal_counts.flagged}`} mono /><Metric label="Rejected" value={`${pcba.optimizer_guard.proposal_counts.rejected}`} mono /></div>
          <div className="metric-stack"><Metric label="Can Create Broker ACCEPT" value={pcba.optimizer_guard.can_create_broker_accept ? "YES" : "NO"} danger={pcba.optimizer_guard.can_create_broker_accept} /><Metric label="Can Unlock Live" value={pcba.optimizer_guard.can_unlock_live_trading ? "YES" : "NO"} danger={pcba.optimizer_guard.can_unlock_live_trading} /></div>
        </div>
        <div className="optimizer-detail">{pcba.optimizer_guard.claim_boundary}</div>
      </GlassPanel>

      <GlassPanel title="PCBA Component Catalog" subtitle={`${pcba.component_catalog.length} live cognitive circuit components`}>
        <div className="component-catalog-grid">
          {pcba.component_catalog.map((component) => (
            <div key={component.kind} className="component-catalog-item">
              <code className="component-name">{component.kind.toUpperCase()}</code>
              <span className="component-role">{component.role}</span>
            </div>
          ))}
        </div>
      </GlassPanel>

      <GlassPanel title="Production Gates" variant="danger">
        <div className="gate-grid">
          {pcbaChecks.concat(cjtChecks).map((check, idx) => (
            <div key={`${check.feature}-${check.status}-${idx}`} className="gate-item">
              <div className="gate-item-header"><span className="gate-item-label">{titleize(check.feature ?? "unknown_feature")}</span><StatusChip label={check.status} variant={chipVariant(check.status)} size="sm" /></div>
              <div className="gate-item-detail">{check.rationale ?? "Diagnostic only — no live authority"}</div>
            </div>
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}

function ReadinessList({ checks }: { checks: ReadinessCheck[] }) {
  return (
    <div className="cjt-features">
      {checks.map((check) => (
        <div key={check.feature} className="cjt-feature-row">
          <div className="cjt-feature-header">
            <code className="cjt-feature-name">{titleize(check.feature ?? "unknown_feature")}</code>
            <StatusChip label={check.status} variant={chipVariant(check.status)} size="sm" />
            <span className="cjt-checks mono">{evidenceLabel(check)}</span>
          </div>
          <div className="cjt-feature-detail">{check.rationale ?? "Readiness evidence is live from API."}</div>
          <Progress check={check} />
          {check.missing_evidence.length > 0 && <div className="pcba-claim-note">Missing: {check.missing_evidence.slice(0, 4).join(", ")}{check.missing_evidence.length > 4 ? ` +${check.missing_evidence.length - 4} more` : ""}</div>}
        </div>
      ))}
    </div>
  );
}

function Progress({ check }: { check: ReadinessCheck }) {
  return <div className="cjt-progress-track"><div className="cjt-progress-fill" style={{ width: `${percent(check.present_evidence.length, check.required_evidence.length)}%` }} /></div>;
}

function Metric({ label, value, mono, danger }: { label: string; value: string; mono?: boolean; danger?: boolean }) {
  return <div className="dashboard-metric"><span className="field-label">{label}</span><span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : undefined }}>{value}</span></div>;
}

function evidenceLabel(check: ReadinessCheck): string {
  return `${check.present_evidence.length}/${check.required_evidence.length} checks`;
}

function percent(present: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((present / total) * 100);
}

function titleize(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function chipVariant(status: string): "success" | "warning" | "danger" | "info" | "muted" | "paper" {
  const normalized = status.toUpperCase();
  if (normalized.includes("LICENSED") && !normalized.includes("NOT")) return "success";
  if (normalized.includes("OPEN") || normalized.includes("ACTIVE")) return "info";
  if (normalized.includes("PASS") || normalized.includes("READY")) return "success";
  if (normalized.includes("FLAG") || normalized.includes("WARN")) return "warning";
  if (normalized.includes("NOT") || normalized.includes("LOCK") || normalized.includes("FALSE")) return "danger";
  return "muted";
}
