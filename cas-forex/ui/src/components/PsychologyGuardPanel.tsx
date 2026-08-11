import { useEffect, useState } from "react";
import {
  fetchAiControlAuthority,
  fetchRiskControl,
  type AiControlAuthorityState,
  type RiskControlState,
} from "../data/api";
import { GlassPanel } from "./GlassPanel";

interface PsychologyGuardPanelProps {
  title?: string;
  subtitle?: string;
  refreshIntervalMs?: number;
}

export function PsychologyGuardPanel({
  title = "Psychology Guard",
  subtitle = "Anti-impulse friction on AI dial widening and owner risk-cap loosening",
  refreshIntervalMs = 30_000,
}: PsychologyGuardPanelProps) {
  const [riskControl, setRiskControl] = useState<RiskControlState | null>(null);
  const [aiAuthority, setAiAuthority] = useState<AiControlAuthorityState | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPsychologyGuard() {
      const [riskNext, aiNext] = await Promise.all([
        fetchRiskControl(),
        fetchAiControlAuthority(),
      ]);
      if (cancelled) return;
      if (riskNext) setRiskControl(riskNext);
      if (aiNext) setAiAuthority(aiNext);
    }

    void loadPsychologyGuard();
    const intervalId = window.setInterval(() => void loadPsychologyGuard(), refreshIntervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [refreshIntervalMs]);

  const aiAntiImpulse = aiAuthority?.control_surface?.anti_impulse;
  const riskAntiImpulse = riskControl?.anti_impulse_status;
  const riskCooldown = riskAntiImpulse?.cooldown;
  const riskPersistence = riskControl?.override_persistence;
  const psychologyGuardWarning = Boolean(
    aiAntiImpulse?.cooldown_active
    || aiAntiImpulse?.warning_active
    || riskCooldown?.active
    || riskAntiImpulse?.would_block_new_loosening,
  );

  if (!aiAntiImpulse && !riskAntiImpulse) {
    return (
      <GlassPanel title={title} subtitle={subtitle}>
        <div className="control-field-desc">Psychology guard is syncing.</div>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel title={title} subtitle={subtitle} variant={psychologyGuardWarning ? "warning" : "default"}>
      <div className="dashboard-grid-3col">
        <GuardField
          label="AI Dial Cooldown"
          value={formatCooldownStatus(aiAntiImpulse?.cooldown_active, aiAntiImpulse?.cooldown_remaining_seconds)}
          mono
          danger={Boolean(aiAntiImpulse?.cooldown_active)}
          description={aiAntiImpulse?.cooldown_detail ?? "Repeated AI dial widening is rate-limited; tightening stays available."}
        />
        <GuardField
          label="AI Widenings 24h"
          value={`${aiAntiImpulse?.recent_loosen_count ?? 0} / ${aiAntiImpulse?.loosen_warning_limit ?? 6}`}
          mono
          danger={Boolean(aiAntiImpulse?.warning_active)}
          description={aiAntiImpulse?.policy ?? "Recent dial widenings are counted so FOMO-style drift stays visible."}
        />
        <GuardField
          label="Risk-Cap Cooldown"
          value={formatCooldownStatus(riskCooldown?.active, riskCooldown?.remaining_seconds)}
          mono
          danger={Boolean(riskCooldown?.active)}
          description={riskCooldown?.detail ?? "Another real-money risk-cap loosening can be cooled down while tightening remains available."}
        />
        <GuardField
          label="Typed Confirm"
          value={statusRequired(riskAntiImpulse?.typed_confirmation_required_on_loosen)}
          mono
          danger={Boolean(riskAntiImpulse?.typed_confirmation_required_on_loosen)}
          description="Required before a real-money risk-cap loosening is applied."
        />
        <GuardField
          label="Anti-Impulse Journal"
          value={statusRequired(riskAntiImpulse?.journal_required_on_loosen || aiAntiImpulse?.journal_prompt_required_on_loosen)}
          mono
          danger={Boolean(riskAntiImpulse?.journal_required_on_loosen || aiAntiImpulse?.journal_prompt_required_on_loosen)}
          description={
            aiAntiImpulse?.journal_prompt
            || riskAntiImpulse?.journal_prompt
            || "Loosening requires a written reason so revenge/FOMO changes are auditable."
          }
        />
        <GuardField
          label="Real-Money Controls"
          value={riskAntiImpulse?.real_money_controls_armed ? "ARMED" : "PAPER / DEMO"}
          mono
          danger={Boolean(riskAntiImpulse?.real_money_controls_armed)}
          description="When armed, wider risk changes pick up typed confirmation and cooldown checks."
        />
        <GuardField
          label="Owner Cap Persistence"
          value={formatPersistenceStatus(riskPersistence?.status, riskPersistence?.explicit_override_count)}
          mono
          danger={riskPersistence?.status === "PERSISTENCE_LOAD_ERROR"}
          description={
            riskPersistence?.load_error
            || riskPersistence?.claim_boundary
            || "Explicit owner caps survive API restarts; absent keys remain under Operator-dial precedence."
          }
        />
      </div>

      {(riskAntiImpulse?.would_block_new_loosening || aiAntiImpulse?.warning_active) && (
        <div className="control-field-desc" style={{ marginTop: 10, color: "var(--warning)" }}>
          {riskAntiImpulse?.would_block_new_loosening
            ? "Another risk-cap loosening would be blocked right now until the cooldown clears."
            : "Recent AI dial widenings are stacking up; review before widening again."}
        </div>
      )}

      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {riskAntiImpulse?.claim_boundary
          || "Psychology guard is observational. It reports anti-impulse friction around dial and risk-cap loosening; it does not place orders, authorize live trading, or move money."}
      </div>
    </GlassPanel>
  );
}

function formatCooldownStatus(active?: boolean, seconds?: number): string {
  if (!active) return "CLEAR";
  const minutes = Math.max(1, Math.ceil((seconds ?? 0) / 60));
  return `${minutes}m ACTIVE`;
}

function statusRequired(enabled?: boolean): string {
  return enabled ? "REQUIRED" : "OFF";
}

function formatPersistenceStatus(status?: string, count?: number): string {
  if (status === "PERSISTED_OWNER_OVERRIDES_ACTIVE") return `${count ?? 0} PERSISTED`;
  if (status === "PERSISTENCE_LOAD_ERROR") return "LOAD ERROR";
  if (status === "PERSISTENCE_DISABLED") return "DISABLED";
  return "OPERATOR DIALS";
}

function GuardField({
  label,
  value,
  mono,
  danger,
  description,
}: {
  label: string;
  value: string;
  mono?: boolean;
  danger?: boolean;
  description?: string;
}) {
  return (
    <div className="control-field">
      <div className="control-field-header">
        <span className="field-label">{label}</span>
        <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--warning)" : undefined, fontWeight: 600 }}>
          {value}
        </span>
      </div>
      {description && <div className="control-field-desc">{description}</div>}
    </div>
  );
}
