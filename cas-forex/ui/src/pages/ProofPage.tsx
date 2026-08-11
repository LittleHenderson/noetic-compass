/* ── CAS Forex — Proof Cockpit Page ── */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { LockReasonList } from "../components/LockReasonList";
import { EvidenceHashRow } from "../components/EvidenceHashRow";
import { MoneyMovementSetupStatus } from "../components/MoneyMovementSetupStatus";
import { ProofControlPanel } from "../components/ProofControlPanel";
import { CONVICTION_SCORE_TITLE, formatConvictionScore } from "../util/conviction";
import { brokerPortalInfo } from "../util/brokerPortal";
import { describeReconciliationMovementTruth } from "../util/movementSource";
import {
  fetchBacksolve,
  fetchAuthorization,
  fetchAccountReconciliation,
  fetchMT5ProbeStatus,
  fetchMT5Receipt,
  fetchVerifiedProfitSweepPolicy,
  fetchWalkForward,
  updateAuthorization,
  updateVerifiedProfitSweepPolicy,
  type AuthorizationPatch,
  type AuthorizationState,
  type VerifiedProfitSweepPolicy,
  type VerifiedProfitSweepPolicyUpdate,
} from "../data/api";
import type {
  AccountReconciliationReport,
  BacksolveSummary,
  BrokerRealityReview,
  DashboardState,
  MT5ProbeStatus,
  MT5Receipt,
  WalkForwardSummary,
} from "../types/evidence";
import "../components/RoutePrimitives.css";
import "./ProofPage.css";

interface ProofPageProps {
  state: DashboardState;
}

const REAL_MONEY_ARM_CONFIRM_PHRASE = "ARM REAL MONEY";
const PAYMENT_PROVIDER_LIVE_CONFIRM_PHRASE = "ARM PAYMENT PROVIDER LIVE";

function realMoneyConfirmRequired(payload: { need_confirmation?: string | null }): string {
  return `Type exactly "${payload.need_confirmation ?? REAL_MONEY_ARM_CONFIRM_PHRASE}" to arm live-money authority switches.`;
}

export function ProofPage({ state }: ProofPageProps) {
  const { uiReadiness: r, dailySchedule: s, dailyBundle: b } = state;
  const [backsolveEvidence, setBacksolveEvidence] = useState<BacksolveSummary | null>(state.backsolve ?? null);
  const [walkForwardEvidence, setWalkForwardEvidence] = useState<WalkForwardSummary | null>(state.walkForward ?? null);
  const [mt5ReceiptEvidence, setMt5ReceiptEvidence] = useState<MT5Receipt | null>(state.mt5Receipt ?? null);
  const [mt5ProbeEvidence, setMt5ProbeEvidence] = useState<MT5ProbeStatus | null>(state.mt5ProbeStatus ?? null);

  useEffect(() => { if (state.backsolve) setBacksolveEvidence(state.backsolve); }, [state.backsolve]);
  useEffect(() => { if (state.walkForward) setWalkForwardEvidence(state.walkForward); }, [state.walkForward]);
  useEffect(() => { if (state.mt5Receipt) setMt5ReceiptEvidence(state.mt5Receipt); }, [state.mt5Receipt]);
  useEffect(() => { if (state.mt5ProbeStatus) setMt5ProbeEvidence(state.mt5ProbeStatus); }, [state.mt5ProbeStatus]);

  useEffect(() => {
    let cancelled = false;
    async function refreshProofEvidence() {
      const [nextBacksolve, nextWalkForward, nextMt5Receipt, nextMt5Probe] = await Promise.all([
        fetchBacksolve(),
        fetchWalkForward(),
        fetchMT5Receipt(),
        fetchMT5ProbeStatus(),
      ]);
      if (cancelled) return;
      if (nextBacksolve) setBacksolveEvidence(nextBacksolve);
      if (nextWalkForward) setWalkForwardEvidence(nextWalkForward);
      if (nextMt5Receipt) setMt5ReceiptEvidence(nextMt5Receipt);
      if (nextMt5Probe) setMt5ProbeEvidence(nextMt5Probe);
    }
    void refreshProofEvidence();
    const interval = window.setInterval(() => { void refreshProofEvidence(); }, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const backsolve = backsolveEvidence ?? state.backsolve ?? null;
  const walkForward = walkForwardEvidence ?? state.walkForward ?? null;
  const mt5Receipt = mt5ReceiptEvidence ?? state.mt5Receipt ?? null;
  const mt5ProbeStatus = mt5ProbeEvidence ?? state.mt5ProbeStatus ?? null;

  return (
    <div className="proof-page">
      {/* ── Active Lead ── */}
      <GlassPanel title="Active Lead" subtitle="Paper-proof candidate">
        <div className="lead-grid">
          <div className="lead-field">
            <span className="field-label">Lead ID</span>
            <span className="field-value mono">{r.lead_id}</span>
          </div>
          <div className="lead-field">
            <span className="field-label">Strategy</span>
            <span className="field-value mono">{r.strategy_setting}</span>
          </div>
          <div className="lead-field">
            <span className="field-label">Timeframe</span>
            <span className="field-value">{r.timeframe}</span>
          </div>
          <div className="lead-field">
            <span className="field-label">Status</span>
            <StatusChip
              label="ACTIVE_RESEARCH_LEAD"
              variant="paper"
              size="sm"
            />
          </div>
        </div>
      </GlassPanel>

      {/* ── Proof Control (advance + profit thresholds) ── */}
      <ProofControlPanel />

      {/* ── Paper Proof Progress ── */}
      <div className="proof-grid-2col">
        <GlassPanel title="Paper Proof Progress">
          <div className="progress-stack">
            <div className="progress-row">
              <span className="progress-label">Paper Days</span>
              <div className="progress-bar-track">
                <div
                  className="progress-bar-fill warning"
                  style={{
                    width: `${(r.completed_trading_days / 30) * 100}%`,
                  }}
                />
              </div>
              <span className="progress-value mono">
                {r.completed_trading_days} / 30
              </span>
            </div>
            <div className="progress-row">
              <span className="progress-label">Multi-Day Bundles</span>
              <div className="progress-bar-track">
                <div
                  className="progress-bar-fill warning"
                  style={{
                    width: `${(r.complete_bundle_days / r.min_daily_bundles_for_ui) * 100}%`,
                  }}
                />
              </div>
              <span className="progress-value mono">
                {r.complete_bundle_days} / {r.min_daily_bundles_for_ui}
              </span>
            </div>
            <div className="progress-row">
              <span className="progress-label">Proof Gate</span>
              <StatusChip
                label={b.latest_proof.passed ? "PASSED" : "NOT PASSED"}
                variant={b.latest_proof.passed ? "success" : "warning"}
                size="sm"
              />
              <span className="progress-detail">
                {b.latest_proof.failure_reasons.join("; ")}
              </span>
            </div>
          </div>
        </GlassPanel>

        <GlassPanel title="Evidence Chain">
          <div className="hash-stack">
            <EvidenceHashRow
              label="Paper Proof Chain"
              value={r.chains_verified.paper_proof ? "VERIFIED" : "FAILED"}
              verified={r.chains_verified.paper_proof}
            />
            <EvidenceHashRow
              label="Paper Decision Chain"
              value={r.chains_verified.paper_decision ? "VERIFIED" : "FAILED"}
              verified={r.chains_verified.paper_decision}
            />
            <EvidenceHashRow
              label="Paper Risk Chain"
              value={r.chains_verified.paper_risk ? "VERIFIED" : "FAILED"}
              verified={r.chains_verified.paper_risk}
            />
            <div
              className="hash-row"
              style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 8, marginTop: 4 }}
            >
              <span className="hash-row-label">WORM Anchoring</span>
              <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                UNAVAILABLE — local hash chain only
              </span>
            </div>
          </div>
        </GlassPanel>
      </div>

      {/* ── Live Eligibility Checklist ── */}
      <GlassPanel title="Live Eligibility Checklist" variant="danger">
        <div className="checklist-grid">
          <CheckItem
            label="12-month multi-symbol evidence"
            met={false}
            detail="OPEN — not yet accumulated"
          />
          <CheckItem
            label="30 real trading days paper evidence"
            met={false}
            detail={`${r.completed_trading_days} / 30 days complete`}
          />
          <CheckItem
            label="Broker terminal proof"
            met={false}
            detail="MT5 demo receipt only; no live broker proof"
          />
          <CheckItem
            label="Legal / account acknowledgments"
            met={false}
            detail="Owner acknowledgments pending"
          />
          <CheckItem
            label="No pooled / managed account"
            met={false}
            detail="Account type not verified"
          />
          <CheckItem
            label="No active LIVE_LOCKED"
            met={false}
            detail="LIVE_LOCKED active"
          />
          <CheckItem
            label="WORM evidence anchoring"
            met={false}
            detail="UNAVAILABLE"
          />
        </div>
      </GlassPanel>

      {/* ── Day-1 Route Decisions ── */}
      <GlassPanel title="Latest Paper Route Decisions" subtitle={b.latest_decision.latest_decision.date}>
        <div className="route-list">
          {b.latest_decision.latest_decision.symbol_decisions.map((d) => (
            <div key={d.proposal.proposal_id} className="route-card">
              <div className="route-card-header">
                <span className="route-symbol">{d.symbol}</span>
                <StatusChip label={d.direction} variant="info" size="sm" />
                <StatusChip label={d.action} variant="paper" size="sm" />
                <span
                  className="route-confidence mono"
                  title={CONVICTION_SCORE_TITLE}
                >
                  conviction: {formatConvictionScore(d.confidence)}
                </span>
              </div>
              <div className="route-card-body">
                <div className="route-price-row">
                  <span className="field-label">Entry</span>
                  <span className="field-value mono">
                    {d.proposal.entry_price.toFixed(2)}
                  </span>
                  <span className="field-label">SL</span>
                  <span className="field-value mono" style={{ color: "var(--danger)" }}>
                    {d.proposal.stop_loss.toFixed(2)}
                  </span>
                  <span className="field-label">TP</span>
                  <span className="field-value mono" style={{ color: "var(--success)" }}>
                    {d.proposal.take_profit.toFixed(2)}
                  </span>
                </div>
                <div className="route-rationale">{d.proposal.rationale}</div>
              </div>
            </div>
          ))}
        </div>
      </GlassPanel>

      {/* ── Risk Sizing ── */}
      <GlassPanel title="Paper Risk Sizing" subtitle={`Equity: $${b.latest_risk.latest_review.account_equity.toLocaleString()}`}>
        <div className="sizing-grid">
          {b.latest_risk.latest_review.sizing.map((sz) => (
            <div key={sz.proposal_id} className="sizing-card">
              <div className="sizing-header">
                <span className="route-symbol">{sz.symbol}</span>
                <StatusChip
                  label={sz.attempt_status}
                  variant={sz.attempt_status === "PAPER_ATTEMPT_ALLOWED" ? "info" : "warning"}
                  size="sm"
                />
              </div>
              <div className="sizing-body">
                <div className="sizing-row">
                  <span className="field-label">Lots</span>
                  <span className="field-value mono">{sz.sized_lots}</span>
                </div>
                <div className="sizing-row">
                  <span className="field-label">Risk/Trade</span>
                  <span className="field-value mono">
                    ${sz.planned_risk_usd.toFixed(2)} ({sz.planned_risk_pct.toFixed(2)}%)
                  </span>
                </div>
                <div className="sizing-row">
                  <span className="field-label">Max Risk</span>
                  <span className="field-value mono">${sz.max_risk_usd.toFixed(2)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="risk-summary">
          <span className="field-label">
            Attempts: {b.latest_risk.latest_review.proposed_attempts} proposed /{" "}
            {b.latest_risk.latest_review.max_paper_attempts} max
          </span>
          <span className="field-label" style={{ marginLeft: 16 }}>
            Daily Budget: ${b.latest_risk.latest_review.daily_risk_budget_usd.toFixed(2)} (
            {b.latest_risk.latest_review.daily_risk_budget_pct}%)
          </span>
        </div>
      </GlassPanel>

      {/* ── Next Action ── */}
      <GlassPanel title="Next Action" variant="info">
        <div className="next-action">
          <div className="next-action-meta">
            <span className="field-label">Next Due Date</span>
            <span className="field-value mono">{s.next_due_date}</span>
            <StatusChip
              label={s.next_due_status}
              variant="warning"
              size="sm"
            />
          </div>
          <div className="next-action-command">
            {s.recommended_action || s.recommended_command}
          </div>
          <LockReasonList
            title="Missing Tracks for Next Due Date"
            items={s.missing_tracks_for_next_due}
            variant="warning"
          />
        </div>
      </GlassPanel>

      {/* ── Capital / Backsolve Summary ── */}
      {backsolve && (
        <GlassPanel title="Capital & Backsolve" subtitle={`${backsolve.total_scenarios.toLocaleString()} scenarios — ${backsolve.ai_autonomy_mode}`} variant="warning">
          <div className="backsolve-summary">
            <div className="dashboard-grid-3col">
              <div className="metric-stack">
                <Metric label="Seed Capital" value="$5,000" mono />
                <Metric label="Target Income" value="$5K-$12K/month" />
                <Metric label="Required Return" value={`${backsolve.required_return_math.target_5k_on_5k_pct}%-${backsolve.required_return_math.target_12k_on_5k_pct}%`} mono />
              </div>
              <div className="metric-stack">
                <Metric label="Total Scenarios" value={backsolve.total_scenarios.toLocaleString()} mono />
                <Metric label="Viable" value={`${backsolve.viable_scenarios}`} mono danger={backsolve.viable_scenarios === 0} />
                <Metric label="AI Selection" value={backsolve.ai_selection ?? "NONE"} mono />
              </div>
              <div className="metric-stack">
                <Metric label="Target Not Reached" value={backsolve.verdict_counts.TARGET_NOT_REACHED?.toLocaleString() ?? "—"} mono />
                <Metric label="Drawdown Fail" value={backsolve.verdict_counts.TARGET_REACHED_BUT_DRAWDOWN_FAIL?.toLocaleString() ?? "—"} mono />
                <Metric label="Margin Fail" value={backsolve.verdict_counts.TARGET_REACHED_BUT_MARGIN_FAIL?.toLocaleString() ?? "—"} mono />
              </div>
            </div>
            <div style={{ marginTop: 8, padding: "6px 10px", background: "var(--danger-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--danger)" }}>
              {backsolve.capital_label}: $5K-$12K/month from $5K seed requires 100%-240% monthly return. Current D1 evidence baseline is $32.93/month. Leverage changes margin; it does not create edge.
            </div>
          </div>
        </GlassPanel>
      )}

      {/* ── MT5 Demo Receipt ── */}
      {mt5Receipt && (
        <GlassPanel title="MT5 Demo Receipt" subtitle={`${mt5Receipt.server} — ${mt5Receipt.trading_date}`} variant="info">
          <div className="receipt-detail">
            <div className="receipt-grid">
              <div className="receipt-field">
                <span className="field-label">Status</span>
                <StatusChip label={mt5Receipt.receipt_validation_status} variant="success" size="sm" />
              </div>
              <div className="receipt-field">
                <span className="field-label">Broker API</span>
                <StatusChip label={mt5Receipt.broker_api_authenticated ? "AUTHENTICATED" : "NOT AUTH"} variant={mt5Receipt.broker_api_authenticated ? "success" : "danger"} size="sm" />
              </div>
              <div className="receipt-field">
                <span className="field-label">Chain</span>
                <StatusChip label={mt5Receipt.chain_verified ? "VERIFIED" : "FAILED"} variant={mt5Receipt.chain_verified ? "success" : "danger"} size="sm" />
              </div>
              <div className="receipt-field">
                <span className="field-label">WORM</span>
                <span style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>{mt5Receipt.worm_retained ? "RETAINED" : "UNAVAILABLE"}</span>
              </div>
              <div className="receipt-field">
                <span className="field-label">Live Mode</span>
                <span className="field-value mono" style={{ color: "var(--danger)" }}>{String(mt5Receipt.live_mode)}</span>
              </div>
              <div className="receipt-field">
                <span className="field-label">Positions Reconciled</span>
                <span className="field-value mono">{String(mt5Receipt.open_positions_reconciled)}</span>
              </div>
            </div>
            <div className="receipt-hashes">
              <div className="hash-row"><span className="field-label">Receipt Hash</span><code className="hash-row-value" style={{ fontSize: "0.62rem" }}>{mt5Receipt.receipt_hash_sha256.slice(0, 24)}...</code></div>
              <div className="hash-row"><span className="field-label">Broker Export</span><code className="hash-row-value" style={{ fontSize: "0.62rem" }}>{mt5Receipt.broker_export_sha256.slice(0, 24)}...</code></div>
              <div className="hash-row"><span className="field-label">Packet Hash</span><code className="hash-row-value" style={{ fontSize: "0.62rem" }}>{mt5Receipt.packet_hash.slice(0, 24)}...</code></div>
            </div>
          </div>
        </GlassPanel>
      )}



      {mt5ProbeStatus && (
        <GlassPanel title="Latest MT5 Probe Attempt" subtitle={mt5ProbeStatus.probe_path} variant={mt5ProbeStatus.status === "BROKER_API_VERIFIED" ? "info" : "danger"}>
          <div className="dashboard-grid-3col">
            <div className="metric-stack">
              <Metric label="Probe Status" value={mt5ProbeStatus.status} mono danger={mt5ProbeStatus.status !== "BROKER_API_VERIFIED"} />
              <Metric label="Broker" value={mt5ProbeStatus.broker ?? "—"} mono />
              <Metric label="Trading Date" value={mt5ProbeStatus.trading_date ?? "—"} mono />
            </div>
            <div className="metric-stack">
              <Metric label="Has Receipt" value={String(mt5ProbeStatus.has_receipt)} mono />
              <Metric label="Account Snapshot" value={mt5ProbeStatus.account_snapshot_present ? "PRESENT" : "MISSING"} mono danger={!mt5ProbeStatus.account_snapshot_present} />
              <Metric label="Latest Verified Receipt" value={mt5Receipt?.receipt_validation_status ?? "—"} mono />
            </div>
            <div className="metric-stack">
              <Metric label="Live Trading" value="OWNER PENDING" mono warning />
              <Metric label="Broker ACCEPT" value="OWNER PENDING" mono warning />
              <Metric label="Payment Movement" value="PAYMENT SETUP PENDING" mono warning />
            </div>
          </div>
          {mt5ProbeStatus.reasons.length > 0 && (
            <div style={{ marginTop: 8, color: "var(--warning)", fontSize: "0.72rem" }}>
              Latest probe blocker: {mt5ProbeStatus.reasons.join("; ")}
            </div>
          )}
        </GlassPanel>
      )}

      {/* ── Walk-Forward Summary ── */}
      {walkForward && (
        <GlassPanel title="Walk-Forward Evidence" subtitle={`${walkForward.run_id} — ${walkForward.research_grade}`} variant="info">
          <div className="wf-summary">
            <div className="dashboard-grid-3col">
              <div className="metric-stack">
                <Metric label="Total Windows" value={`${walkForward.total_windows}`} mono />
                <Metric label="Routed" value={`${walkForward.routed_windows}`} mono />
                <Metric label="Active Routed" value={`${walkForward.active_routed_windows}`} mono />
              </div>
              <div className="metric-stack">
                <Metric label="Positive Active" value={`${walkForward.positive_active_routed_windows} / ${walkForward.active_routed_windows}`} mono />
                <Metric label="Mean Return" value={`${walkForward.active_routed_mean_return_pct.toFixed(2)}%`} mono />
                <Metric label="Max DD" value={`${walkForward.routed_max_drawdown_pct.toFixed(2)}%`} mono />
              </div>
              <div className="metric-stack">
                <Metric label="Routed Return" value={`${walkForward.routed_total_return_pct.toFixed(2)}%`} mono />
                <Metric label="Total Trades" value={`${walkForward.total_routed_trades}`} mono />
                <Metric label="Symbols" value={walkForward.symbols.join(", ")} />
              </div>
            </div>
            <div className="wf-grade">
              <StatusChip label={`Grade: ${walkForward.research_grade}`} variant="warning" size="sm" />
              <span className="text-muted-italic" style={{ marginLeft: 8 }}>{walkForward.claim_boundary}</span>
            </div>
          </div>
        </GlassPanel>
      )}

      <ProofLivePaymentControls mt5Receipt={mt5Receipt} brokerReality={state.brokerReality} />
    </div>
  );
}

/* ── Helpers ── */

function ProofLivePaymentControls({
  mt5Receipt,
  brokerReality,
}: {
  mt5Receipt?: MT5Receipt | null;
  brokerReality?: BrokerRealityReview;
}) {
  const [auth, setAuth] = useState<AuthorizationState | null>(null);
  const [policy, setPolicy] = useState<VerifiedProfitSweepPolicy | null>(null);
  const [reconciliation, setReconciliation] = useState<AccountReconciliationReport | null>(null);
  const [busyKey, setBusyKey] = useState("");
  const [status, setStatus] = useState("");
  const [fundingStatus, setFundingStatus] = useState("");
  const [provider, setProvider] = useState("");
  const [providerEnvironment, setProviderEnvironment] = useState("sandbox");
  const [apiKey, setApiKey] = useState("");
  const [providerBaseUrl, setProviderBaseUrl] = useState("");
  const [providerAccountId, setProviderAccountId] = useState("");
  const [destId, setDestId] = useState("");
  const [sweepPct, setSweepPct] = useState("30");
  const [taxReservePct, setTaxReservePct] = useState("20");
  const [minSweepUsd, setMinSweepUsd] = useState("25");

  function loadAuthDraft(nextAuth: AuthorizationState) {
    setProvider(nextAuth.provider.payment_provider ?? "");
    setProviderEnvironment(nextAuth.provider.payment_provider_environment ?? "sandbox");
    setProviderBaseUrl(nextAuth.provider.payment_provider_base_url ?? "");
    setProviderAccountId(nextAuth.provider.payment_provider_account_id ?? "");
    setDestId(nextAuth.provider.payout_destination_id ?? "");
  }

  function loadPolicyDraft(nextPolicy: VerifiedProfitSweepPolicy) {
    setSweepPct(String(nextPolicy.settings.sweep_pct));
    setTaxReservePct(String(nextPolicy.settings.tax_reserve_pct));
    setMinSweepUsd(String(nextPolicy.settings.min_sweep_usd));
  }

  async function refresh() {
    const [nextAuth, nextPolicy, nextReconciliation] = await Promise.all([
      fetchAuthorization(),
      fetchVerifiedProfitSweepPolicy(),
      fetchAccountReconciliation(),
    ]);
    if (nextAuth) {
      setAuth(nextAuth);
      loadAuthDraft(nextAuth);
    }
    if (nextPolicy) {
      setPolicy(nextPolicy);
      loadPolicyDraft(nextPolicy);
    }
    if (nextReconciliation) setReconciliation(nextReconciliation);
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function applyAuth(patch: AuthorizationPatch, key: string, okMessage = "Saved.") {
    setBusyKey(key);
    setStatus("");
    try {
      const nextAuth = await updateAuthorization(patch);
      if (nextAuth.status === "CONFIRM_REQUIRED") {
        setStatus(realMoneyConfirmRequired(nextAuth));
        return;
      }
      setAuth(nextAuth);
      loadAuthDraft(nextAuth);
      setStatus(okMessage);
    } catch {
      setStatus("Could not save owner authorization. Check the API connection.");
    } finally {
      setBusyKey("");
    }
  }

  async function saveProvider() {
    const patch: AuthorizationPatch = {
      payment_provider: provider.trim(),
      payment_provider_environment: providerEnvironment,
      payment_provider_base_url: providerBaseUrl.trim(),
      payment_provider_account_id: providerAccountId.trim(),
      payout_destination_id: destId.trim(),
    };
    if (apiKey.trim()) patch.payment_api_key = apiKey.trim();
    if (providerEnvironment === "live") {
      const confirm = window.prompt(
        `Type exactly "${PAYMENT_PROVIDER_LIVE_CONFIRM_PHRASE}" to mark this middleware as live.`,
        "",
      );
      if (confirm == null) {
        setStatus("Owner confirmation canceled; provider environment was not changed.");
        return;
      }
      patch.confirm = confirm;
    }
    await applyAuth(
      patch,
      "__provider__",
      "Provider configuration saved. Withdrawals and payouts stay scaffolded until the runtime rail, owner gate, allowlist, and receipt evidence are all ready.",
    );
    setApiKey("");
  }

  async function syncBrokerSnapshot() {
    setBusyKey("__broker_snapshot__");
    setFundingStatus("");
    try {
      const report = await fetchAccountReconciliation(true);
      setReconciliation(report);
      setFundingStatus(
        report
          ? "Broker snapshot synced. CAS can compare broker balance/equity against the owner ledger."
          : "Broker snapshot sync returned no report.",
      );
    } catch {
      setFundingStatus("Could not sync broker snapshot. Confirm the API and terminal/broker receipt path are reachable.");
    } finally {
      setBusyKey("");
    }
  }

  async function turnOwnerSwitchesOn() {
    const patch: AuthorizationPatch = {
      personal_account_ack: true,
      no_pooled_capital_ack: true,
      live_mode: true,
      prefer_mt5: true,
      owner_enable_live_trading: true,
      live_trading_licensed: true,
      owner_enable_broker_accept: true,
      owner_enable_auto_deposit: true,
      owner_enable_bank_card_movement: true,
      owner_enable_payout_automation: true,
      payment_provider: provider.trim(),
      payment_provider_environment: providerEnvironment,
      payment_provider_base_url: providerBaseUrl.trim(),
      payment_provider_account_id: providerAccountId.trim(),
      payout_destination_id: destId.trim(),
    };
    if (destId.trim()) patch.payout_destination_allowlisted = true;
    if (apiKey.trim()) patch.payment_api_key = apiKey.trim();
    const confirm = window.prompt(`Type exactly "${REAL_MONEY_ARM_CONFIRM_PHRASE}" to arm these live-money authority switches.`, "");
    if (confirm == null) {
      setStatus("Owner confirmation canceled; no switches changed.");
      return;
    }
    patch.confirm = confirm;
    await applyAuth(
      patch,
      "__all__",
      "Owner authority switches saved. Real money still depends on broker credentials, edge authorization, a supported real provider rail, allowlist, receipts, and action-time risk checks.",
    );
    setApiKey("");
  }

  async function saveSweepPolicy() {
    setBusyKey("__sweep__");
    setStatus("");
    try {
      const patch: VerifiedProfitSweepPolicyUpdate = {
        sweep_pct: cleanNumber(sweepPct, policy?.settings.sweep_pct ?? 30),
        tax_reserve_pct: cleanNumber(taxReservePct, policy?.settings.tax_reserve_pct ?? 20),
        min_sweep_usd: cleanNumber(minSweepUsd, policy?.settings.min_sweep_usd ?? 25),
        destination_id: destId.trim() || null,
      };
      const nextPolicy = await updateVerifiedProfitSweepPolicy(patch);
      setPolicy(nextPolicy);
      loadPolicyDraft(nextPolicy);
      setStatus("Verified-profit sweep policy saved.");
    } catch {
      setStatus("Could not save sweep policy. Check the API connection.");
    } finally {
      setBusyKey("");
    }
  }

  const allAuthorized = Boolean(auth?.all_real_money_authorized && auth?.provider.real_money_provider_ready);
  const snapshot = reconciliation?.broker_snapshot_initial_investment_usd;
  const blockerCount = reconciliation?.blockers?.length ?? 0;
  const syncStatus = reconciliation?.overall_status ?? "READY";
  const statusVariant = syncStatus === "RECONCILIATION_FAILED"
    ? "danger"
    : syncStatus === "RECONCILED_WITH_WARNINGS"
      ? "warning"
      : "info";
  const movementTruth = describeReconciliationMovementTruth(reconciliation);
  const brokerPortal = brokerPortalInfo(
    brokerReality?.broker_id,
    brokerReality?.broker_display_name,
    brokerReality?.broker_website,
  );
  const receiptVerified = Boolean(
    mt5Receipt?.receipt_validation_status === "BROKER_API_VERIFIED" ||
    mt5Receipt?.receipt_validation_status === "VERIFIED",
  );

  return (
    <GlassPanel
      title="Live & Payment Controls"
      subtitle="Owner authorization, broker/payment gates, and verified-profit payout destination"
      variant={allAuthorized ? "default" : "warning"}
    >
      <div style={{ marginBottom: 12, fontSize: "0.78rem", color: "var(--text-secondary)" }}>
        {auth?.summary ?? "Loading owner-controlled capability state..."}
      </div>
      <div className="control-field-desc" style={{ marginBottom: 10 }}>
        Broker funding and payout setup stay observational here until a supported real provider rail is actually ready. Saving a provider label does not make payouts live.
      </div>

      <div className="go-live-group-title">Broker Funding Route</div>
      <div className="dashboard-grid-3col">
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Where to fund</span>
            <StatusChip label="BROKER PORTAL" variant="info" size="sm" />
          </div>
          <div className="control-field-desc">Use the broker client portal for KYC, deposits, withdrawals, and account funding.</div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">CAS custody</span>
            <StatusChip label="NO RAW BANK/CARD STORAGE" variant="success" size="sm" />
          </div>
          <div className="control-field-desc">CAS reads broker/terminal evidence after funding; payment details stay with the broker/provider.</div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Broker snapshot</span>
            <StatusChip label={syncStatus} variant={statusVariant} size="sm" />
          </div>
          <div className="control-field-desc">
            {snapshot != null
              ? `Broker snapshot balance/equity seed: $${snapshot.toFixed(2)}.`
              : `No broker-funded snapshot loaded yet${blockerCount ? `; ${blockerCount} blocker(s) reported.` : "."}`}
          </div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Movement Feed</span>
            <StatusChip label={movementTruth.feedLabel} variant={movementTruth.feedTone} size="sm" />
          </div>
          <div className="control-field-desc">
            {movementTruth.detail
              ? `Price source: ${movementTruth.statusLabel}. ${movementTruth.detail}`
              : "Broker snapshot sync has not reported canonical movement-source truth yet."}
          </div>
        </div>
      </div>
      <div className="mobile-api-row">
        <a className="mobile-api-button" href={brokerPortal.url} target="_blank" rel="noreferrer">
          OPEN BROKER PORTAL
        </a>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busyKey === "__broker_snapshot__"}
          onClick={() => void syncBrokerSnapshot()}
        >
          {busyKey === "__broker_snapshot__" ? "SYNCING..." : "SYNC BROKER SNAPSHOT"}
        </button>
      </div>
      {fundingStatus && (
        <div
          className="control-field-desc"
          style={{ color: fundingStatus.startsWith("Could not") ? "var(--danger)" : "var(--success)" }}
        >
          {fundingStatus}
        </div>
      )}

      <MoneyMovementSetupStatus
        auth={auth}
        receiptVerified={receiptVerified}
        receiptStatusLabel={receiptVerified ? "VERIFIED" : "REQUIRED"}
        receiptDetail={
          receiptVerified
            ? `MT5 receipt evidence status: ${mt5Receipt?.receipt_validation_status ?? "VERIFIED"}.`
            : "Broker receipt and payout evidence are still required before real payouts should be trusted."
        }
      />

      <div className="not-licensed-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
        {(auth?.capabilities ?? []).map((cap) => (
          <div
            key={cap.capability}
            className="disabled-control"
            style={{ borderColor: cap.authorized ? "var(--success)" : "var(--warning-dim)" }}
          >
            <div className="disabled-control-header">
              <span className="disabled-control-label">{cap.title}</span>
              <StatusChip
                label={cap.authorized ? "AUTHORIZED" : cap.status.includes("NOT LICENSED") ? "OWNER PENDING" : cap.status}
                variant={cap.authorized ? "success" : "warning"}
                size="sm"
              />
            </div>
            <div className="disabled-control-reason" style={{ color: cap.authorized ? "var(--success)" : "var(--text-secondary)" }}>
              {cap.authorized ? "Authorized by owner controls." : cap.missing_requirements.join("; ") || "Waiting for owner/provider setup."}
            </div>
            <div style={{ display: "grid", gap: 4, marginTop: 8 }}>
              {cap.toggles.map((toggle) => (
                <div key={toggle.key} className="go-live-row" style={{ borderBottom: "none", padding: "4px 0" }}>
                  <ToggleSwitch
                    on={toggle.enabled}
                    busy={busyKey === toggle.key}
                    label={toggle.label}
                    onClick={() => void applyAuth({ [toggle.key]: !toggle.enabled } as AuthorizationPatch, toggle.key)}
                  />
                  <div className="go-live-row-body">
                    <div className="go-live-row-label">{toggle.label}</div>
                    <div className="go-live-row-consequence">{toggle.consequence}</div>
                  </div>
                </div>
              ))}
            </div>
            {cap.note && <div className="control-field-desc">{cap.note}</div>}
          </div>
        ))}
      </div>

      <div className="go-live-group-title">Bank / Card / Payout Destination</div>
      <div className="dashboard-grid-3col">
        <div className="control-field">
          <span className="field-label">Payment provider</span>
          <input
            className="mobile-api-input"
            value={provider}
            placeholder="broker_webhook or simulated"
            onChange={(event) => { setProvider(event.target.value); setStatus(""); }}
          />
        </div>
        <div className="control-field">
          <span className="field-label">Provider environment</span>
          <select
            className="mobile-api-input"
            value={providerEnvironment}
            onChange={(event) => { setProviderEnvironment(event.target.value); setStatus(""); }}
          >
            <option value="sandbox">Sandbox contract test</option>
            <option value="live">Live broker middleware</option>
          </select>
          <div className="control-field-desc">Sandbox proves the same contract without moving or claiming real money.</div>
        </div>
        <div className="control-field">
          <span className="field-label">Provider API key{auth?.provider.payment_api_key_set ? " - set" : ""}</span>
          <input
            className="mobile-api-input"
            type="password"
            value={apiKey}
            placeholder={auth?.provider.payment_api_key_set ? "leave blank to keep current key" : "provider API key"}
            autoComplete="off"
            onChange={(event) => { setApiKey(event.target.value); setStatus(""); }}
          />
          <div className="control-field-desc">The app stores a provider key/token as a local encrypted runtime envelope, not raw bank or card numbers.</div>
        </div>
        <div className="control-field">
          <span className="field-label">Bank/card destination token</span>
          <input
            className="mobile-api-input"
            value={destId}
            placeholder="allowlisted payout destination id"
            onChange={(event) => { setDestId(event.target.value); setStatus(""); }}
          />
        </div>
      </div>

      <div className="dashboard-grid-3col">
        <div className="control-field">
          <span className="field-label">Broker funding middleware URL</span>
          <input
            className="mobile-api-input"
            value={providerBaseUrl}
            placeholder="https://funding.your-domain.example"
            onChange={(event) => { setProviderBaseUrl(event.target.value); setStatus(""); }}
          />
        </div>
        <div className="control-field">
          <span className="field-label">Bound broker account ID</span>
          <input
            className="mobile-api-input"
            value={providerAccountId}
            placeholder="provider-side broker account id"
            onChange={(event) => { setProviderAccountId(event.target.value); setStatus(""); }}
          />
        </div>
        <div className="control-field">
          <span className="field-label">Custody binding</span>
          <div className="control-field-desc">
            {auth?.provider.broker_account_bound
              ? `Bound: ${auth.provider.custody_scope ?? "configured broker account"}`
              : "Not broker-bound. Stripe alone does not withdraw from MT5/Hugo's Way."}
          </div>
        </div>
      </div>

      <div className="go-live-row" style={{ borderBottom: "none" }}>
        <ToggleSwitch
          on={auth?.provider.payout_destination_allowlisted ?? false}
          busy={busyKey === "payout_destination_allowlisted"}
          label={auth?.provider.allowlist_label ?? "Payout destination allowlisted"}
          onClick={() => void applyAuth(
            { payout_destination_allowlisted: !(auth?.provider.payout_destination_allowlisted ?? false) },
            "payout_destination_allowlisted",
          )}
        />
        <div className="go-live-row-body">
          <div className="go-live-row-label">{auth?.provider.allowlist_label ?? "Payout destination allowlisted"}</div>
          <div className="go-live-row-consequence">Owner confirms the payout destination token is approved for deposits/sweeps.</div>
        </div>
      </div>

      <div className="mobile-api-row">
        <button className="mobile-api-button" type="button" disabled={busyKey === "__provider__"} onClick={() => void saveProvider()}>
          SAVE PROVIDER / DESTINATION
        </button>
        <button className="mobile-api-button" type="button" disabled={busyKey === "__all__"} onClick={() => void turnOwnerSwitchesOn()}>
          TURN OWNER SWITCHES ON
        </button>
      </div>

      <div className="go-live-group-title">Verified-Profit Sweep Policy</div>
      <div className="dashboard-grid-3col">
        <div className="control-field">
          <span className="field-label">Sweep pct</span>
          <input className="mobile-api-input" type="number" min={0} max={100} step="1" value={sweepPct} onChange={(event) => setSweepPct(event.target.value)} />
        </div>
        <div className="control-field">
          <span className="field-label">Tax reserve pct</span>
          <input className="mobile-api-input" type="number" min={0} max={100} step="1" value={taxReservePct} onChange={(event) => setTaxReservePct(event.target.value)} />
        </div>
        <div className="control-field">
          <span className="field-label">Minimum sweep USD</span>
          <input className="mobile-api-input" type="number" min={0} step="1" value={minSweepUsd} onChange={(event) => setMinSweepUsd(event.target.value)} />
        </div>
      </div>
      <div className="mobile-api-row">
        <button className="mobile-api-button ghost" type="button" disabled={busyKey === "__sweep__"} onClick={() => void saveSweepPolicy()}>
          SAVE SWEEP POLICY
        </button>
      </div>

      {status && (
        <div className="control-field-desc" style={{ color: status.startsWith("Could not") ? "var(--danger)" : "var(--success)" }}>
          {status}
        </div>
      )}
    </GlassPanel>
  );
}

function Metric({
  label,
  value,
  mono,
  danger,
  warning,
}: {
  label: string;
  value: string;
  mono?: boolean;
  danger?: boolean;
  warning?: boolean;
}) {
  const color = danger ? "var(--danger)" : warning ? "var(--warning)" : undefined;
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color }}>{value}</span>
    </div>
  );
}

function CheckItem({
  label,
  met,
  detail,
}: {
  label: string;
  met: boolean;
  detail: string;
}) {
  return (
    <div className="check-item">
      <span
        className="check-icon"
        style={{ color: met ? "var(--success)" : "var(--danger)" }}
      >
        {met ? "✓" : "✗"}
      </span>
      <div>
        <div className="check-label">{label}</div>
        <div className="check-detail">{detail}</div>
      </div>
    </div>
  );
}

function ToggleSwitch({
  on,
  busy,
  onClick,
  label,
}: {
  on: boolean;
  busy: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className="go-live-switch"
      data-on={on}
      disabled={busy}
      aria-pressed={on}
      aria-label={`${label} - ${on ? "on" : "off"}`}
      onClick={onClick}
    >
      <span className="knob" />
    </button>
  );
}

function cleanNumber(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}
