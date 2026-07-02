import { useEffect, useMemo, useState } from "react";
import {
  acceptCompoundAddOrderDryRunReview,
  dispatchCompoundAddDispatchHandoff,
  fetchCompoundAddDispatchHandoffStatus,
  fetchCompoundAddOrderDryRunLatest,
  fetchCompoundAddOrderDryRunReview,
  resetCompoundAddOrderDryRunReview,
} from "../data/api";
import type {
  CompoundAddDispatchHandoffStatus,
  CompoundAddOrderDryRunLatest,
  CompoundAddOrderDryRunReport,
  CompoundAddOrderDryRunReview,
  DashboardState,
} from "../types/evidence";
import { StatusChip } from "./StatusChip";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface CompoundAddReviewPanelProps {
  state: Pick<DashboardState, "compoundAddOrderDryRun" | "compoundAddOrderDryRunReview" | "compoundAddDispatchHandoff">;
  autoHydrateDelayMs?: number;
}

type NormalizedCheck = {
  id: string;
  status: string;
  detail: string;
  passed: boolean;
};

export function CompoundAddReviewPanel({ state, autoHydrateDelayMs = 15_000 }: CompoundAddReviewPanelProps) {
  const [latest, setLatest] = useState<CompoundAddOrderDryRunLatest | null>(state.compoundAddOrderDryRun ?? null);
  const [review, setReview] = useState<CompoundAddOrderDryRunReview | null>(state.compoundAddOrderDryRunReview ?? null);
  const [handoff, setHandoff] = useState<CompoundAddDispatchHandoffStatus | null>(state.compoundAddDispatchHandoff ?? null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [ownerConfirmAccept, setOwnerConfirmAccept] = useState(false);
  const [ownerConfirmDispatch, setOwnerConfirmDispatch] = useState(false);
  const [ownerConfirmLiveDispatch, setOwnerConfirmLiveDispatch] = useState(false);
  const [notes, setNotes] = useState("Owner reviewed current compound-add evidence.");

  useEffect(() => {
    if (state.compoundAddOrderDryRun) setLatest(state.compoundAddOrderDryRun);
  }, [state.compoundAddOrderDryRun]);

  useEffect(() => {
    if (state.compoundAddOrderDryRunReview) setReview(state.compoundAddOrderDryRunReview);
  }, [state.compoundAddOrderDryRunReview]);

  useEffect(() => {
    if (state.compoundAddDispatchHandoff) setHandoff(state.compoundAddDispatchHandoff);
  }, [state.compoundAddDispatchHandoff]);

  useEffect(() => {
    let cancelled = false;
    let interval: number | undefined;
    let firstLoad: number | undefined;

    async function load() {
      const [nextLatest, nextReview, nextHandoff] = await Promise.all([
        fetchCompoundAddOrderDryRunLatest(),
        fetchCompoundAddOrderDryRunReview(),
        fetchCompoundAddDispatchHandoffStatus(),
      ]);
      if (cancelled) return;
      if (nextLatest) setLatest(nextLatest);
      if (nextReview) setReview(nextReview);
      if (nextHandoff) setHandoff(nextHandoff);
    }

    firstLoad = window.setTimeout(() => {
      void load();
      interval = window.setInterval(load, 30_000);
    }, autoHydrateDelayMs);
    return () => {
      cancelled = true;
      if (firstLoad !== undefined) window.clearTimeout(firstLoad);
      if (interval !== undefined) window.clearInterval(interval);
    };
  }, [autoHydrateDelayMs]);

  const report = compoundAddReportFromLatest(latest);
  const status = report?.status ?? latest?.status ?? "NO_COMPOUND_ADD_DRY_RUN_AUDIT_YET";
  const clearForDispatch = Boolean(review?.compound_add_dry_run_review_clear_for_dispatch);
  const readyForAccept = Boolean(review?.evidence_ready_for_owner_accept);
  const missing = review?.missing_requirements ?? [];
  const blockers = report?.blocking_reasons ?? [];
  const orderRequest = report?.order_request ?? report?.proposed_intent ?? {};
  const summary = review?.latest_compound_add_summary ?? {};
  const checks = useMemo(() => normalizeChecks(review, report), [review, report]);
  const handoffPreview = handoff?.handoff_status ?? handoff;
  const handoffReady = Boolean(handoffPreview?.would_call_dispatch_if_owner_attempted);
  const handoffStatus = handoff?.status ?? handoffPreview?.status ?? "NO_HANDOFF_STATUS";
  const handoffBridgeTouched = Boolean(handoff?.broker_touched || handoff?.dispatched_to_bridge);
  const missingRequirements = missing.length ? missing.join(", ") : "COMPOUND_ADD_EVIDENCE_NOT_READY";
  const acceptBlocker = !ownerConfirmAccept
    ? "OWNER_ACCEPT_CONFIRM_REQUIRED"
    : !readyForAccept
      ? review?.next_action ?? missingRequirements
      : "";
  const dispatchBlocker = !ownerConfirmDispatch
    ? "OWNER_DISPATCH_CONFIRM_REQUIRED"
    : !handoffReady
      ? handoff?.next_action ?? handoffPreview?.next_action ?? handoff?.reason ?? handoffPreview?.reason ?? "COMPOUND_ADD_HANDOFF_NOT_READY"
      : "";

  const orderId = firstString(report?.order_id, latest?.latest_audit?.order_id, summary["order_id"]);
  const decisionRef = firstString(report?.decision_ref, latest?.latest_audit?.decision_ref, summary["decision_ref"]);
  const symbol = firstString(orderRequest["symbol"], summary["symbol"]);
  const side = firstString(orderRequest["direction"], orderRequest["side"], summary["direction"], summary["side"]);
  const parentRef = firstString(
    report?.parent_position_reference,
    report?.compound_context?.["parent_position_reference"],
    summary["parent_position_reference"],
    summary["parent_ticket"],
    summary["parent_order_id"],
  );
  const last = report?.generated_at ?? latest?.latest_audit?.timestamp ?? review?.generated_at;
  const fingerprint = review?.current_fingerprint ?? review?.accepted_fingerprint ?? null;

  async function handleRefresh() {
    if (busy) return;
    setBusy(true);
    try {
      const [nextLatest, nextReview, nextHandoff] = await Promise.all([
        fetchCompoundAddOrderDryRunLatest(),
        fetchCompoundAddOrderDryRunReview(),
        fetchCompoundAddDispatchHandoffStatus(),
      ]);
      if (nextLatest) setLatest(nextLatest);
      if (nextReview) setReview(nextReview);
      if (nextHandoff) setHandoff(nextHandoff);
      setMessage(nextHandoff?.status ?? nextReview?.review_status ?? nextLatest?.status ?? "COMPOUND_ADD_REFRESHED");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "COMPOUND_ADD_REFRESH_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function handleAccept() {
    if (busy) return;
    if (acceptBlocker) {
      setMessage(acceptBlocker);
      return;
    }
    setBusy(true);
    try {
      const nextReview = await acceptCompoundAddOrderDryRunReview(notes, true);
      setReview(nextReview);
      const nextHandoff = await fetchCompoundAddDispatchHandoffStatus();
      if (nextHandoff) setHandoff(nextHandoff);
      setOwnerConfirmAccept(false);
      setOwnerConfirmDispatch(false);
      setOwnerConfirmLiveDispatch(false);
      setMessage(nextReview.review_status);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "COMPOUND_ADD_ACCEPT_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    if (busy) return;
    setBusy(true);
    try {
      const nextReview = await resetCompoundAddOrderDryRunReview("OWNER_RESET");
      setReview(nextReview);
      const nextHandoff = await fetchCompoundAddDispatchHandoffStatus();
      if (nextHandoff) setHandoff(nextHandoff);
      setOwnerConfirmAccept(false);
      setOwnerConfirmDispatch(false);
      setOwnerConfirmLiveDispatch(false);
      setMessage(nextReview.review_status);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "COMPOUND_ADD_RESET_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function handleDispatch() {
    if (busy) return;
    if (dispatchBlocker) {
      setMessage(dispatchBlocker);
      return;
    }
    setBusy(true);
    try {
      const nextHandoff = await dispatchCompoundAddDispatchHandoff(
        notes,
        ownerConfirmDispatch,
        ownerConfirmLiveDispatch,
      );
      setHandoff(nextHandoff);
      setOwnerConfirmDispatch(false);
      setOwnerConfirmLiveDispatch(false);
      setMessage(nextHandoff.status);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "COMPOUND_ADD_HANDOFF_DISPATCH_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="broker-truth-monitor-strip">
      <div className="broker-truth-monitor-header">
        <div className="auto-halt-title">
          <StatusChip label="COMPOUND ADD" variant="paper" size="sm" />
          <StatusChip label={shortStatus(status)} variant={dryRunVariant(status)} size="sm" />
          <StatusChip
            label={latest?.broker_touched || report?.broker_touched ? "BROKER TOUCHED" : "BROKER NOT TOUCHED"}
            variant={latest?.broker_touched || report?.broker_touched ? "danger" : "success"}
            size="sm"
          />
          <StatusChip
            label={clearForDispatch ? "OWNER ACCEPT CURRENT" : review?.owner_review_status ?? "OWNER REVIEW OPEN"}
            variant={clearForDispatch ? "success" : readyForAccept ? "warning" : "danger"}
            size="sm"
          />
          <StatusChip
            label={handoffReady ? "HANDOFF READY" : "HANDOFF BLOCKED"}
            variant={handoffReady ? "info" : "muted"}
            size="sm"
          />
          {(missing.length > 0 || blockers.length > 0) && (
            <StatusChip label={`${missing.length + blockers.length} BLOCKERS`} variant="danger" size="sm" />
          )}
        </div>
        <div className="broker-truth-monitor-actions">
          <button className="sweep-action-button" type="button" onClick={handleRefresh} disabled={busy}>
            Refresh
          </button>
          <button className="sweep-action-button" type="button" onClick={handleRefresh} disabled={busy}>
            Check Handoff
          </button>
          <button className="sweep-action-button danger" type="button" onClick={handleReset} disabled={busy}>
            Reset
          </button>
        </div>
      </div>

      <div className="broker-truth-monitor-meta">
        <span className="mono">order {orderId ?? "NONE"}</span>
        <span className="mono">parent {parentRef ?? "NA"}</span>
        <span className="mono">side {side ?? "NA"}</span>
        <span className="mono">symbol {symbol ?? "NA"}</span>
        <span className="mono">decision {decisionRef ?? "NA"}</span>
        <span className="mono">last {last ? formatShortTime(last) : "NONE"}</span>
        <span>{message ?? review?.next_action ?? report?.next_action ?? latest?.detail ?? "No compound-add dry-run audit has reported yet."}</span>
      </div>

      <div className="auto-halt-clear-row">
        <StatusChip
          label={readyForAccept ? "EVIDENCE READY" : `${missing.length} REVIEW BLOCKERS`}
          variant={readyForAccept ? "info" : "danger"}
          size="sm"
        />
        <input
          className="auto-halt-reason-input"
          type="text"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          aria-label="Compound add dry-run review notes"
        />
        <label className="sweep-confirm-check">
          <input
            type="checkbox"
            checked={ownerConfirmAccept}
            onChange={(event) => setOwnerConfirmAccept(event.target.checked)}
          />
          <span>Owner ACCEPT</span>
        </label>
        <button
          className="sweep-action-button"
          type="button"
          onClick={handleAccept}
          disabled={busy}
          title={acceptBlocker || undefined}
        >
          Accept Add
        </button>
      </div>

      <div className="auto-halt-clear-row">
        <StatusChip
          label={handoffReady ? "HANDOFF READY" : "HANDOFF BLOCKED"}
          variant={handoffReady ? "info" : "danger"}
          size="sm"
        />
        <label className="sweep-confirm-check">
          <input
            type="checkbox"
            checked={ownerConfirmDispatch}
            onChange={(event) => setOwnerConfirmDispatch(event.target.checked)}
          />
          <span>Owner dispatch</span>
        </label>
        <label className="sweep-confirm-check">
          <input
            type="checkbox"
            checked={ownerConfirmLiveDispatch}
            onChange={(event) => setOwnerConfirmLiveDispatch(event.target.checked)}
          />
          <span>Live confirm</span>
        </label>
        <button
          className="sweep-action-button"
          type="button"
          onClick={handleDispatch}
          disabled={busy}
          title={dispatchBlocker || undefined}
        >
          Dispatch Handoff
        </button>
      </div>

      {(missing.length > 0 || blockers.length > 0 || fingerprint) && (
        <div className="broker-truth-monitor-meta">
          {fingerprint && <span className="mono">fingerprint {shortFingerprint(fingerprint)}</span>}
          {missing.length > 0 && <span className="mono">missing {missing.join(", ")}</span>}
          {blockers.length > 0 && <span className="mono">blocked {blockers.join(", ")}</span>}
        </div>
      )}

      <div className="broker-truth-monitor-meta">
        <StatusChip label={shortHandoffStatus(handoffStatus)} variant={handoffReady ? "info" : "warning"} size="sm" />
        <StatusChip
          label={handoffBridgeTouched ? "HANDOFF BRIDGE TOUCHED" : "HANDOFF NO BRIDGE"}
          variant={handoffBridgeTouched ? "danger" : "success"}
          size="sm"
        />
        <span className="mono">handoff order {handoff?.order_id ?? handoffPreview?.order_id ?? orderId ?? "NONE"}</span>
        <span className="mono">handoff decision {handoff?.decision_ref ?? handoffPreview?.decision_ref ?? decisionRef ?? "NA"}</span>
        <span>{handoff?.next_action ?? handoffPreview?.next_action ?? "Dispatch handoff status has not reported yet."}</span>
      </div>

      {checks.length > 0 && (
        <div className="auto-halt-check-grid">
          {checks.slice(0, 8).map((check) => (
            <div className={`auto-halt-check ${check.passed ? "ok" : "tripped"}`} key={check.id}>
              <div className="auto-halt-check-title">
                <span>{formatCheckId(check.id)}</span>
                <StatusChip label={check.status} variant={check.passed ? "success" : "danger"} size="sm" />
              </div>
              <div className="auto-halt-check-detail">{check.detail}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function compoundAddReportFromLatest(
  latest: CompoundAddOrderDryRunLatest | null | undefined,
): CompoundAddOrderDryRunReport | null {
  const payload = latest?.latest_audit?.payload;
  if (!payload || typeof payload !== "object") return null;
  const candidate = payload as Partial<CompoundAddOrderDryRunReport>;
  if (candidate.report_kind !== "cas_forex_compound_add_order_dry_run") return null;
  if (typeof candidate.status !== "string") return null;
  return candidate as CompoundAddOrderDryRunReport;
}

function normalizeChecks(
  review: CompoundAddOrderDryRunReview | null,
  report: CompoundAddOrderDryRunReport | null,
): NormalizedCheck[] {
  if (review?.checks?.length) {
    return review.checks.map((check) => ({
      id: check.check_id,
      status: check.status,
      detail: check.detail,
      passed: isPassingStatus(check.status),
    }));
  }
  return (report?.checks ?? []).map((check) => ({
    id: check.check_id,
    status: check.status,
    detail: check.detail,
    passed: Boolean(check.passed) || isPassingStatus(check.status),
  }));
}

function isPassingStatus(status: string): boolean {
  const normalized = status.toUpperCase();
  return normalized === "PASS" || normalized === "OK" || normalized === "READY";
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value;
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
  }
  return null;
}

function shortStatus(status: string): string {
  return status
    .replace(/^DRY_RUN_/, "")
    .replace(/^NO_COMPOUND_ADD_DRY_RUN_/, "NO ADD ")
    .replace(/_/g, " ");
}

function shortHandoffStatus(status: string): string {
  return status
    .replace(/^COMPOUND_ADD_HANDOFF_/, "")
    .replace(/^BLOCKED_COMPOUND_ADD_/, "BLOCKED ")
    .replace(/_/g, " ");
}

function dryRunVariant(status: string): ChipVariant {
  if (status === "DRY_RUN_PASS") return "success";
  if (status === "DRY_RUN_BLOCKED") return "danger";
  if (status === "NO_COMPOUND_ADD_DRY_RUN_AUDIT_YET") return "warning";
  return "muted";
}

function formatShortTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortFingerprint(value: string): string {
  if (value.length <= 16) return value;
  return `${value.slice(0, 8)}...${value.slice(-8)}`;
}

function formatCheckId(value: string): string {
  return value.replace(/_/g, " ");
}
