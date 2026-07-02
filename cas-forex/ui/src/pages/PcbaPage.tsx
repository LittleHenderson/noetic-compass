/* ── CAS Forex — PCBA/CJT Diagnostics ── */
import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { fetchPcbaCockpit } from "../data/api";
import type { DashboardState, PcbaCockpitPayload, ReadinessCheck } from "../types/evidence";
import "./PcbaPage.css";

interface PcbaPageProps {
  state: DashboardState;
}

const PCBA_RETRY_DELAYS_MS = [750, 1_500, 3_000, 5_000, 8_000] as const;

export function PcbaPage({ state }: PcbaPageProps) {
  const initialPcba = state.pcba?.report_kind === "cas_forex_pcba_cockpit" ? state.pcba : null;
  const [livePcba, setLivePcba] = useState<PcbaCockpitPayload | null>(initialPcba);
  const [loading, setLoading] = useState(!initialPcba);
  const pcba = livePcba ?? pcbaStatusPayload(loading ? "loading" : "unavailable");

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;
    let attempt = 0;
    setLoading(true);

    async function refreshPcbaCockpit() {
      const payload = await fetchPcbaCockpit();
      if (cancelled) return;
      if (payload) setLivePcba(payload);

      if (payload && !pcbaPayloadNeedsRetry(payload)) {
        setLoading(false);
        return;
      }

      if (attempt < PCBA_RETRY_DELAYS_MS.length) {
        const delay = PCBA_RETRY_DELAYS_MS[attempt];
        attempt += 1;
        retryTimer = window.setTimeout(() => {
          void refreshPcbaCockpit();
        }, delay);
        return;
      }

      setLoading(false);
    }

    void refreshPcbaCockpit();
    return () => {
      cancelled = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
    };
  }, []);

  const pcbaChecks = pcba.pcba_readiness.checks;
  const cjtChecks = pcba.cjt_readiness.checks;
  const ccbChecks = pcba.ccb_readiness.board_checks;
  const pcbaWarming = pcbaPayloadNeedsRetry(livePcba);
  const sourceLabel = !livePcba ? (loading ? "CONNECTING" : "API UNAVAILABLE") : pcbaWarming ? "API WARMING" : "LIVE API";
  const subtitle = livePcba && !pcbaWarming
    ? "Live diagnostic payload from CAS API"
    : loading
      ? "Connecting to live PCBA/CJT diagnostics..."
      : pcbaWarming
        ? "Live PCBA/CJT diagnostics are warming..."
        : "Live PCBA/CJT diagnostics are unavailable.";

  return (
    <div className="pcba-page">
      <GlassPanel
        title="PCBA Active Cockpit"
        subtitle={subtitle}
      >
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
        <div className="optimizer-detail" style={{ marginTop: 10 }}>{ownerFacingBoundary(pcba.claim_boundary)}</div>
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

      <GlassPanel title="PCBA Production Readiness" subtitle={ownerFacingBoundary(pcba.pcba_readiness.summary)} variant="warning">
        <ReadinessList checks={pcbaChecks} />
      </GlassPanel>

      <GlassPanel title="CJT Production Readiness" subtitle={ownerFacingBoundary(pcba.cjt_readiness.summary)} variant="warning">
        <ReadinessList checks={cjtChecks} />
      </GlassPanel>

      <GlassPanel title="CCB Readiness" subtitle={ownerFacingBoundary(pcba.ccb_readiness.summary)}>
        <div className="cjt-features">
          {ccbChecks.map((check) => (
            <div key={check.board_kind} className="cjt-feature-row">
              <div className="cjt-feature-header">
                <code className="cjt-feature-name">{titleize(check.board_kind ?? "unknown_board")}</code>
                <StatusChip label={chipLabel(check.status)} variant={chipVariant(check.status)} size="sm" />
                <span className="cjt-checks mono">{evidenceLabel(check)}</span>
              </div>
              <div className="cjt-feature-detail">{ownerFacingBoundary(check.rationale ?? "CCB diagnostic readiness.")}</div>
              <Progress check={check} />
            </div>
          ))}
          <div className="cjt-feature-row">
            <div className="cjt-feature-header">
              <code className="cjt-feature-name">CjtPredictionHead</code>
              <StatusChip label={chipLabel(pcba.ccb_readiness.prediction_head.status)} variant={chipVariant(pcba.ccb_readiness.prediction_head.status)} size="sm" />
              <span className="cjt-checks mono">{pcba.ccb_readiness.prediction_head.present_evidence.length}/{pcba.ccb_readiness.prediction_head.required_evidence.length} checks</span>
            </div>
            <div className="cjt-feature-detail">{ownerFacingBoundary(pcba.ccb_readiness.prediction_head.rationale)}</div>
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
        <div className="optimizer-detail">{ownerFacingBoundary(pcba.optimizer_guard.claim_boundary)}</div>
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

      <GlassPanel title="Production Gates" variant="warning">
        <div className="gate-grid">
          {pcbaChecks.concat(cjtChecks).map((check, idx) => (
            <div key={`${check.feature}-${check.status}-${idx}`} className="gate-item">
              <div className="gate-item-header"><span className="gate-item-label">{titleize(check.feature ?? "unknown_feature")}</span><StatusChip label={chipLabel(check.status)} variant={chipVariant(check.status)} size="sm" /></div>
              <div className="gate-item-detail">{ownerFacingBoundary(check.rationale ?? "Diagnostic only - no live authority")}</div>
            </div>
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}

function pcbaStatusPayload(source: "loading" | "unavailable"): PcbaCockpitPayload {
  const label = source === "loading" ? "PCBA/CJT diagnostics are connecting." : "PCBA/CJT API is unavailable.";
  const readiness = {
    report_id: `pcba-cockpit-${source}`,
    generated_at: "",
    summary: label,
    all_ready: false,
    any_live_authority: false,
    any_broker_accept_authority: false,
    checks: [] as ReadinessCheck[],
  };
  return {
    report_kind: "cas_forex_pcba_cockpit",
    panels_active: false,
    source,
    claim_boundary: `${label} This status packet is empty and fail-closed; it does not use local placeholder evidence, create broker ACCEPT, unlock live trading, move money, or mark anything LICENSED.`,
    summary: {
      pcba_ready_checks: 0,
      pcba_total_checks: 0,
      cjt_ready_checks: 0,
      cjt_total_checks: 0,
      ccb_designs_well_formed: false,
      ccb_claims_licensed: false,
      goal_complete: false,
      current_boundary_honest: true,
    },
    local_evidence: {
      pcba: {},
      cjt: {},
      pcba_present_count: 0,
      pcba_total_count: 0,
      cjt_present_count: 0,
      cjt_total_count: 0,
    },
    reference_boards: [],
    component_catalog: [],
    pcba_readiness: readiness,
    cjt_readiness: { ...readiness, report_id: `cjt-cockpit-${source}` },
    ccb_readiness: {
      report_id: `ccb-cockpit-${source}`,
      summary: label,
      all_designs_well_formed: false,
      any_claim_licensed: false,
      board_checks: [],
      prediction_head: {
        status: "OPEN",
        ready: false,
        required_evidence: [],
        present_evidence: [],
        missing_evidence: [],
        rationale: label,
      },
    },
    optimizer_guard: {
      guard: "CASPCBAOptimizerGuard",
      active: false,
      proposal_counts: { research_queue: 0, flagged: 0, rejected: 0 },
      claim_boundary: "Optimizer guard status is unavailable until the live API responds.",
      can_create_broker_accept: false,
      can_unlock_live_trading: false,
    },
    goal_status: {
      goal_complete: false,
      current_boundary_honest: true,
      status: "OPEN",
    },
  };
}

function pcbaPayloadNeedsRetry(payload: PcbaCockpitPayload | null | undefined): boolean {
  if (!payload) return false;
  const packet = payload as PcbaCockpitPayload & {
    cache_status?: string;
    source?: string;
  };
  const cacheStatus = String(packet.cache_status ?? "").toLowerCase();
  return packet.source === "warming" || cacheStatus === "warming";
}

function ReadinessList({ checks }: { checks: ReadinessCheck[] }) {
  return (
    <div className="cjt-features">
      {checks.map((check) => (
        <div key={check.feature} className="cjt-feature-row">
          <div className="cjt-feature-header">
            <code className="cjt-feature-name">{titleize(check.feature ?? "unknown_feature")}</code>
            <StatusChip label={chipLabel(check.status)} variant={chipVariant(check.status)} size="sm" />
            <span className="cjt-checks mono">{evidenceLabel(check)}</span>
          </div>
          <div className="cjt-feature-detail">{ownerFacingBoundary(check.rationale ?? "Readiness evidence is live from API.")}</div>
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

function chipLabel(status: string): string {
  return status.toUpperCase().includes("NOT LICENSED") ? "CLAIM PENDING" : status;
}

function chipVariant(status: string): "success" | "warning" | "danger" | "info" | "muted" | "paper" {
  const normalized = status.toUpperCase();
  if (normalized.includes("NOT LICENSED")) return "warning";
  if (normalized.includes("LICENSED") && !normalized.includes("NOT")) return "success";
  if (normalized.includes("OPEN") || normalized.includes("ACTIVE")) return "info";
  if (normalized.includes("PASS") || normalized.includes("READY")) return "success";
  if (normalized.includes("FLAG") || normalized.includes("WARN")) return "warning";
  if (normalized.includes("NOT") || normalized.includes("LOCK") || normalized.includes("FALSE")) return "danger";
  return "muted";
}

function ownerFacingBoundary(text: string): string {
  return text
    .replace(/CURRENTLY NOT LICENSED/g, "OWNER PENDING")
    .replace(/OPEN \/ NOT LICENSED/g, "OPEN / CLAIM PENDING")
    .replace(/NOT LICENSED/g, "CLAIM PENDING");
}
