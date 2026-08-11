/* CAS Forex - Tracker Page */

import { useEffect, useMemo, useState } from "react";
import { AccountHealthPanel } from "../components/AccountHealthPanel";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import {
  detailEvidenceForLiveReadinessCheck,
  describeMovementPositionFeed,
  isStaticMovementPosition,
  summarizeMovementSource,
} from "../util/movementSource";
import {
  fetchAccountLedger,
  fetchAccountHealth,
  fetchLiveReadiness,
  fetchMobileProofSessionLatest,
  fetchMovementStream,
  type MobileProofGate,
  type MobileProofSession,
} from "../data/api";
import type {
  AccountHealthReport,
  AccountLedgerState,
  DashboardState,
  LiveReadinessCheck,
  LiveReadinessReport,
  MovementStreamState,
} from "../types/evidence";
import "../components/RoutePrimitives.css";
import "./TrackerPage.css";

interface TrackerPageProps {
  state: DashboardState;
}

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

export function TrackerPage({ state }: TrackerPageProps) {
  const [ledger, setLedger] = useState<AccountLedgerState | null>(state.accountLedger ?? null);
  const [accountHealth, setAccountHealth] = useState<AccountHealthReport | null>(state.accountHealth ?? null);
  const [movement, setMovement] = useState<MovementStreamState | null>(state.movementStream ?? null);
  const [liveReadiness, setLiveReadiness] = useState<LiveReadinessReport | null>(state.liveReadiness ?? null);
  const [mobileProof, setMobileProof] = useState<MobileProofSession | null>(null);

  useEffect(() => {
    if (state.accountLedger) setLedger(state.accountLedger);
  }, [state.accountLedger]);

  useEffect(() => {
    if (state.accountHealth) setAccountHealth(state.accountHealth);
  }, [state.accountHealth]);

  useEffect(() => {
    if (state.movementStream) setMovement(state.movementStream);
  }, [state.movementStream]);

  useEffect(() => {
    if (state.liveReadiness) setLiveReadiness(state.liveReadiness);
  }, [state.liveReadiness]);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      const [nextLedger, nextAccountHealth, nextMovement, nextReadiness, nextMobileProof] = await Promise.all([
        fetchAccountLedger(),
        fetchAccountHealth(),
        fetchMovementStream(true),
        fetchLiveReadiness(),
        fetchMobileProofSessionLatest(),
      ]);
      if (cancelled) return;
      if (nextLedger) setLedger(nextLedger);
      if (nextAccountHealth) setAccountHealth(nextAccountHealth);
      if (nextMovement) setMovement(nextMovement);
      if (nextReadiness) setLiveReadiness(nextReadiness);
      if (nextMobileProof) setMobileProof(nextMobileProof);
    }
    void refresh();
    const interval = window.setInterval(() => void refresh(), 15_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const { uiReadiness, dailySchedule, dailyBundle } = state;
  const account = ledger?.summary;
  const moveAccount = movement?.account;
  const paperDays = uiReadiness.completed_trading_days ?? dailySchedule.completed_trading_days ?? 0;
  const completeBundles = uiReadiness.complete_bundle_days ?? dailySchedule.complete_bundle_days ?? 0;
  const minBundles = uiReadiness.min_daily_bundles_for_ui ?? dailySchedule.ui_min_daily_bundles ?? 0;
  const missingTracks = dailySchedule.missing_tracks_for_next_due ?? [];
  const liveChecks = liveReadiness?.checks ?? [];
  const blockingLiveChecks = liveChecks.filter((check) => check.blocks_live && check.status !== "PASSED");
  const mobileGates = mobileProof?.gates ?? [];
  const pendingMobileGates = mobileGates.filter((gate) => !gate.satisfied);
  const quotes = movement?.quotes ?? [];
  const positions = movement?.positions ?? [];
  const movementTruth = movement?.movement_source_truth ?? movement ?? null;
  const staleQuoteCount = movementTruth?.static_quote_count ?? movement?.static_quote_count ?? quotes.filter((quote) => quote.stale).length;
  const staticPositionCount =
    movementTruth?.static_position_count
    ?? movement?.static_position_count
    ?? positions.filter((position) => isStaticMovementPosition(position)).length;
  const brokerTicketCount =
    movementTruth?.broker_ticket_position_count
    ?? movement?.broker_ticket_position_count
    ?? positions.filter((position) => Boolean(position.broker_ticket)).length;
  const movementSource = summarizeMovementSource(movementTruth);
  const positionFeed = describeMovementPositionFeed(movementTruth, moveAccount?.source);
  const bundleSteps = dailyBundle.steps ?? [];
  const completedBundleSteps = bundleSteps.filter((step) => step.status === "complete" || step.status === "passed").length;

  const trackerStatus = useMemo(() => {
    if (paperDays >= 30 && blockingLiveChecks.length === 0 && pendingMobileGates.length === 0) {
      return { label: "TRACKED", variant: "success" as ChipVariant };
    }
    if (paperDays > 0 || completeBundles > 0 || quotes.length > 0 || positions.length > 0) {
      return { label: "ACTIVE", variant: "info" as ChipVariant };
    }
    return { label: "WAITING", variant: "warning" as ChipVariant };
  }, [blockingLiveChecks.length, completeBundles, paperDays, pendingMobileGates.length, positions.length, quotes.length]);

  return (
    <div className="tracker-page">
      <GlassPanel title="Tracker" subtitle="Live evidence tracks across proof, money, markets, phone, and gates">
        <div className="tracker-hero-grid">
          <TrackerMetric label="Overall" value={trackerStatus.label} tone={trackerStatus.variant} />
          <TrackerMetric label="Paper days" value={`${paperDays} / 30`} tone={paperDays >= 30 ? "success" : "warning"} />
          <TrackerMetric label="Bundles" value={`${completeBundles} / ${minBundles || 0}`} tone={completeBundles >= minBundles && minBundles > 0 ? "success" : "warning"} />
          <TrackerMetric label="Open positions" value={`${account?.open_position_count ?? moveAccount?.open_position_count ?? positions.length}`} tone="info" />
        </div>
      </GlassPanel>

      <div className="tracker-grid">
        <GlassPanel title="Proof Track" subtitle={dailySchedule.next_due_status || "Daily evidence schedule"}>
          <div className="tracker-metric-grid">
            <TrackerMetric label="Next due" value={dailySchedule.next_due_date || "unknown"} />
            <TrackerMetric label="UI bundles left" value={`${dailySchedule.ui_bundles_remaining ?? 0}`} tone={dailySchedule.ui_bundles_remaining ? "warning" : "success"} />
            <TrackerMetric label="Paper days left" value={`${dailySchedule.paper_days_remaining ?? Math.max(0, 30 - paperDays)}`} tone={dailySchedule.paper_days_remaining ? "warning" : "success"} />
            <TrackerMetric label="Chain state" value={dailyBundle.latest_proof?.passed ? "PASSED" : "OPEN"} tone={dailyBundle.latest_proof?.passed ? "success" : "warning"} />
          </div>
          <TrackList
            title="Missing tracks"
            empty="No missing tracks reported for the next due date."
            items={missingTracks.map((track) => ({ id: track, label: track, detail: "required for the next complete bundle", variant: "warning" }))}
          />
        </GlassPanel>

        <GlassPanel title="Money Track" subtitle={ledger?.mode || movement?.mode || "paper/demo"}>
          <div className="tracker-metric-grid">
            <TrackerMetric label="Balance" value={money(account?.balance_usd ?? moveAccount?.balance_usd)} />
            <TrackerMetric label="Equity" value={money(account?.equity_usd ?? moveAccount?.equity_usd)} />
            <TrackerMetric label="Floating P/L" value={money(account?.floating_pnl_usd ?? moveAccount?.floating_pnl_usd)} tone={(account?.floating_pnl_usd ?? moveAccount?.floating_pnl_usd ?? 0) >= 0 ? "success" : "danger"} />
            <TrackerMetric label="Drawdown" value={`${((account?.drawdown_pct ?? moveAccount?.drawdown_pct ?? 0)).toFixed(2)}%`} tone={(account?.drawdown_pct ?? moveAccount?.drawdown_pct ?? 0) > 0 ? "warning" : "success"} />
          </div>
          <div className="tracker-boundary">{ledger?.claim_boundary || movement?.claim_boundary || "Tracking evidence is loading."}</div>
        </GlassPanel>

        <AccountHealthPanel
          report={accountHealth}
          title="Health Track"
          subtitle="Decision-grade blockers, protection coverage, and static/stale pricing evidence"
        />

        <GlassPanel title="Market Movement Track" subtitle={movement?.timestamp || "Waiting for movement snapshot"}>
          <div className="tracker-metric-grid">
            <TrackerMetric label="Symbols" value={`${movement?.symbols?.length ?? 0}`} />
            <TrackerMetric label="Quotes" value={`${quotes.length}`} tone={quotes.length ? "success" : "warning"} />
            <TrackerMetric label="Stale quotes" value={`${staleQuoteCount}`} tone={staleQuoteCount ? "warning" : "success"} />
            <TrackerMetric label="Positions" value={`${positions.length}`} tone={positions.length ? "info" : "muted"} />
            <TrackerMetric
              label="Position feed"
              value={positionFeed.isLiveBroker ? "LIVE MT5" : "SIM PROOF"}
              tone={positionFeed.isLiveBroker ? "success" : "warning"}
            />
            <TrackerMetric
              label="Broker-ticket rows"
              value={`${brokerTicketCount}`}
              tone={brokerTicketCount ? "success" : "muted"}
            />
            <TrackerMetric
              label="Static positions"
              value={`${staticPositionCount}`}
              tone={staticPositionCount ? "warning" : "success"}
            />
            <TrackerMetric
              label="Price source"
              value={movementSource.statusLabel}
              tone={movementSource.statusTone}
            />
            <TrackerMetric
              label="Provider-backed"
              value={`${movementSource.providerBackedCount}`}
              tone={movementSource.providerBackedCount ? "success" : "muted"}
            />
            <TrackerMetric
              label="MT5 fallback"
              value={`${movementSource.mt5FallbackCount}`}
              tone={movementSource.mt5FallbackCount ? "info" : "muted"}
            />
            <TrackerMetric
              label="Static fallback"
              value={`${movementSource.staticFallbackCount}`}
              tone={movementSource.staticFallbackCount ? "warning" : "success"}
            />
          </div>
          {movementSource.warningText || staleQuoteCount > 0 ? (
            <div className="tracker-boundary" style={{ color: "var(--warning)" }}>
              {movementSource.warningText
                ?? "Static simulator rows are not being moved by usable provider/MT5 quotes right now; prices and floating P/L can remain unchanged at entry."}
            </div>
          ) : null}
          {positions.length > 0 ? (
            <div className="tracker-boundary">
              {positionFeed.detail}
            </div>
          ) : null}
          <div className="tracker-symbol-strip">
            {(movement?.symbols ?? []).slice(0, 16).map((symbol) => (
              <span key={symbol} className="tracker-symbol">{symbol}</span>
            ))}
          </div>
        </GlassPanel>

        <GlassPanel title="Live Gate Track" subtitle={liveReadiness?.overall_status || "Live readiness loading"}>
          <div className="tracker-metric-grid">
            <TrackerMetric label="Passed" value={`${liveReadiness?.checks_passed ?? 0}`} tone="success" />
            <TrackerMetric label="Open" value={`${liveReadiness?.checks_open ?? 0}`} tone={liveReadiness?.checks_open ? "warning" : "success"} />
            <TrackerMetric label="Live money" value={liveReadiness?.live_money_authorized ? "AUTHORIZED" : "NOT LICENSED"} tone={liveReadiness?.live_money_authorized ? "success" : "warning"} />
            <TrackerMetric label="Payments" value={liveReadiness?.payment_movement_authorized ? "AUTHORIZED" : "NOT LICENSED"} tone={liveReadiness?.payment_movement_authorized ? "success" : "warning"} />
          </div>
          <CheckRows checks={blockingLiveChecks.slice(0, 6)} />
        </GlassPanel>

        <GlassPanel title="Phone Delivery Track" subtitle={mobileProof?.status || "Proof session loading"}>
          <div className="tracker-metric-grid">
            <TrackerMetric label="Package" value={mobileProof?.package_ready_for_phone_install ? "READY" : "PENDING"} tone={mobileProof?.package_ready_for_phone_install ? "success" : "warning"} />
            <TrackerMetric label="Phone proof" value={mobileProof?.phone_browser_verified ? "VERIFIED" : mobileProof?.phone_browser_observed ? "OBSERVED" : "MISSING"} tone={mobileProof?.phone_browser_verified ? "success" : "warning"} />
            <TrackerMetric label="APK pairing" value={mobileProof?.apk_install_pairing_verified ? "VERIFIED" : mobileProof?.apk_install_pairing_attempt_status || "PENDING"} tone={mobileProof?.apk_install_pairing_verified ? "success" : "warning"} />
            <TrackerMetric label="Docker" value={mobileProof?.docker_engine_status || "unknown"} tone={mobileProof?.docker_available ? "success" : "warning"} />
          </div>
          <TrackList
            title="Pending gates"
            empty="No pending phone/APK/Docker gates."
            items={pendingMobileGates.map((gate) => gateToTrackItem(gate))}
          />
        </GlassPanel>

        <GlassPanel title="Today Bundle Track" subtitle={`${completedBundleSteps} / ${bundleSteps.length} steps complete`}>
          <div className="tracker-table-wrap">
            <table className="data-table tracker-table">
              <thead>
                <tr>
                  <th>Step</th>
                  <th>Status</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {bundleSteps.length ? bundleSteps.map((step) => (
                  <tr key={step.name}>
                    <td>{step.name}</td>
                    <td><StatusChip label={step.status || "unknown"} variant={statusVariant(step.status)} size="sm" /></td>
                    <td>{step.detail || step.reasons?.join("; ") || "No detail reported."}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={3}>No daily bundle steps are loaded yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassPanel>
      </div>
    </div>
  );
}

function TrackerMetric({
  label,
  value,
  tone = "muted",
}: {
  label: string;
  value: string;
  tone?: ChipVariant;
}) {
  return (
    <div className={`tracker-metric tracker-metric-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TrackList({
  title,
  empty,
  items,
}: {
  title: string;
  empty: string;
  items: Array<{ id: string; label: string; detail: string; variant: ChipVariant }>;
}) {
  return (
    <div className="tracker-list">
      <div className="tracker-list-title">{title}</div>
      {items.length ? items.map((item) => (
        <div className="tracker-list-row" key={item.id}>
          <StatusChip label={item.label} variant={item.variant} size="sm" />
          <span>{item.detail}</span>
        </div>
      )) : (
        <div className="tracker-empty">{empty}</div>
      )}
    </div>
  );
}

function CheckRows({ checks }: { checks: LiveReadinessCheck[] }) {
  if (!checks.length) {
    return <div className="tracker-empty">No blocking live-readiness checks are currently reported.</div>;
  }
  return (
    <div className="tracker-list">
      <div className="tracker-list-title">Blocking checks</div>
      {checks.map((check) => {
        const followup = detailEvidenceForLiveReadinessCheck(check);
        return (
          <div className="tracker-check-row" key={check.gate_id}>
            <div>
              <strong>{check.label}</strong>
              <span>{check.plain_english}</span>
              {followup && followup !== check.plain_english && <span>{followup}</span>}
            </div>
            <StatusChip label={check.status} variant={statusVariant(check.status)} size="sm" />
          </div>
        );
      })}
    </div>
  );
}

function gateToTrackItem(gate: MobileProofGate) {
  return {
    id: gate.gate_id,
    label: gate.title,
    detail: gate.detail || gate.command || "Pending external proof.",
    variant: "warning" as ChipVariant,
  };
}

function statusVariant(status: string | undefined): ChipVariant {
  const upper = (status || "").toUpperCase();
  if (upper.includes("PASS") || upper.includes("COMPLETE") || upper.includes("VERIFIED") || upper.includes("AUTHORIZED")) return "success";
  if (upper.includes("FAIL") || upper.includes("ERROR") || upper.includes("MISMATCH")) return "danger";
  if (upper.includes("OPEN") || upper.includes("PENDING") || upper.includes("WAIT") || upper.includes("NOT")) return "warning";
  return "muted";
}

function money(value: number | null | undefined): string {
  if (!Number.isFinite(value ?? NaN)) return "$0.00";
  return `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
