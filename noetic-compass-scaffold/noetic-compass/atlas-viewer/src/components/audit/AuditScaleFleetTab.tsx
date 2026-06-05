import type { CSSProperties } from 'react';
import EnterpriseScalePlanCard from './EnterpriseScalePlanCard';
import DistributedAuditRunPanel from './DistributedAuditRunPanel';
import FleetExecutorPanel from './FleetExecutorPanel';
import { COLORS, FONT_FAMILY, THEME } from '../../lib/designTokens';
import type {
  CasHarnessDistributedAudit,
  CasHarnessFleetRun,
  CasHarnessFleetVerifierDecision,
} from '../../lib/casHarnessAuditApi';
import type {
  EnterpriseScalePlan,
  EnterpriseScalePlanSize,
} from '../../lib/enterpriseScalePlan';

export interface AuditScaleFleetTabProps {
  // --- Enterprise scale plan ---
  enterprisePlan: EnterpriseScalePlan;
  enterprisePlanSize: EnterpriseScalePlanSize;
  isEnterprisePlanLoading: boolean;
  enterprisePlanError: string | null;
  onSelectSize: (size: EnterpriseScalePlanSize) => void;

  // --- Distributed audit run ---
  distributedAudit: CasHarnessDistributedAudit | null;
  isDistributedAuditLoading: boolean;
  distributedAuditError: string | null;
  onCreateDistributedRun: () => void;
  onDispatchDistributedRun: () => void;
  onMergeDistributedRun: () => void;

  // --- Fleet executor status (display) ---
  fleetRegisteredWorkers: number;
  fleetLeasedJobs: number;
  fleetStaleWorkers: number;
  fleetCompletedFragments: number;
  fleetTotalJobs: number;
  fleetMergedPacketStatus: 'not_created' | 'partial' | 'ready';
  fleetVerifierGateStatus: import('./FleetExecutorPanel').FleetVerifierGateStatus;
  fleetReadiness: import('./FleetExecutorPanel').FleetReadinessSummary | null;

  // --- Fleet executor controls ---
  fleetAuthToken: string;
  onFleetAuthTokenChange: (value: string) => void;
  isFleetExecutorLoading: boolean;
  fleetExecutorError: string | null;
  fleetRun: CasHarnessFleetRun | null;
  fleetVerifierDecision: CasHarnessFleetVerifierDecision | null;
  canPrepareFleet: boolean;
  canRegisterFleetWorker: boolean;
  canLeaseFleetJob: boolean;
  canSubmitFleetReceipt: boolean;
  canMergeFleet: boolean;
  canRunFleetVerifier: boolean;
  onPrepareFleet: () => void;
  onRegisterFleetWorker: () => void;
  onLeaseFleetJob: () => void;
  onSubmitFleetReceipt: () => void;
  onMergeFleet: () => void;
  onRunFleetVerifier: () => void;

  className?: string;
}

const tabStyle: CSSProperties = {
  display: 'grid',
  gap: 16,
  fontFamily: FONT_FAMILY,
};

const introStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12.5,
  lineHeight: 1.5,
};

const fleetControlPanelStyle: CSSProperties = {
  display: 'grid',
  gap: 12,
  padding: 16,
  borderRadius: 8,
  border: '1px solid rgba(45, 212, 191, 0.22)',
  background: 'rgba(2, 6, 23, 0.40)',
};

const fleetControlHeaderStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
};

const fleetControlTitleStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 17,
  fontWeight: 900,
};

const fleetButtonRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
};

const fleetAuthInputStyle: CSSProperties = {
  width: 'min(100%, 360px)',
  minHeight: 38,
  padding: '8px 10px',
  borderRadius: 6,
  border: '1px solid rgba(148, 163, 184, 0.26)',
  background: 'rgba(2, 6, 23, 0.48)',
  color: COLORS.textPrimary,
  fontFamily: THEME.fontMono,
  fontSize: 12,
  outline: 'none',
};

const fleetNoticeStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

const labelStyle: CSSProperties = {
  display: 'block',
  marginBottom: 4,
  fontSize: 12,
  fontWeight: 800,
  letterSpacing: 0.4,
  fontFamily: THEME.fontMono,
  color: COLORS.textPrimary,
};

const actionButtonStyle = (enabled: boolean): CSSProperties => ({
  minHeight: 42,
  padding: '9px 15px',
  borderRadius: 6,
  border: enabled
    ? '1px solid rgba(45, 212, 191, 0.56)'
    : '1px solid rgba(148, 163, 184, 0.24)',
  background: enabled ? 'rgba(45, 212, 191, 0.16)' : 'rgba(148, 163, 184, 0.06)',
  color: enabled ? '#ccfbf1' : COLORS.textMuted,
  cursor: enabled ? 'pointer' : 'not-allowed',
  fontFamily: 'inherit',
  fontSize: 13,
  fontWeight: 900,
  letterSpacing: 0.4,
  textTransform: 'uppercase',
});

/**
 * Off-screen home for the enterprise / distributed / fleet machinery, reached
 * via the "Scale & fleet (advanced)" disclosure in the center. Relocates the
 * EnterpriseScalePlanCard + DistributedAuditRunPanel + FleetExecutorPanel + the
 * inline fleet-button row out of the default audit view so the first screen is
 * just compose -> run -> verdict.
 *
 * All API contracts are unchanged: the distributed/fleet merge path still routes
 * through the same handlers, and the fleet verifier decision is rendered exactly
 * as before (always FLAG_FOR_HUMAN_REVIEW server-side; this UI only displays it).
 */
export function AuditScaleFleetTab({
  enterprisePlan,
  enterprisePlanSize,
  isEnterprisePlanLoading,
  enterprisePlanError,
  onSelectSize,
  distributedAudit,
  isDistributedAuditLoading,
  distributedAuditError,
  onCreateDistributedRun,
  onDispatchDistributedRun,
  onMergeDistributedRun,
  fleetRegisteredWorkers,
  fleetLeasedJobs,
  fleetStaleWorkers,
  fleetCompletedFragments,
  fleetTotalJobs,
  fleetMergedPacketStatus,
  fleetVerifierGateStatus,
  fleetReadiness,
  fleetAuthToken,
  onFleetAuthTokenChange,
  isFleetExecutorLoading,
  fleetExecutorError,
  fleetRun,
  fleetVerifierDecision,
  canPrepareFleet,
  canRegisterFleetWorker,
  canLeaseFleetJob,
  canSubmitFleetReceipt,
  canMergeFleet,
  canRunFleetVerifier,
  onPrepareFleet,
  onRegisterFleetWorker,
  onLeaseFleetJob,
  onSubmitFleetReceipt,
  onMergeFleet,
  onRunFleetVerifier,
  className,
}: AuditScaleFleetTabProps): JSX.Element {
  return (
    <div style={tabStyle} className={className} aria-label="Scale and fleet (advanced)">
      <p style={introStyle}>
        Advanced scale-out: plan capacity for large open-weight models, create a
        distributed audit run, and exercise the real fleet API path. These tools
        never produce a verdict; the distributed/fleet merge stays a human-review
        decision.
      </p>

      <EnterpriseScalePlanCard
        plan={enterprisePlan}
        selectedSize={enterprisePlanSize}
        isLoading={isEnterprisePlanLoading}
        error={enterprisePlanError}
        onSelectSize={onSelectSize}
      />

      <DistributedAuditRunPanel
        audit={distributedAudit}
        isLoading={isDistributedAuditLoading}
        error={distributedAuditError}
        onCreateRun={onCreateDistributedRun}
        onDispatchRun={onDispatchDistributedRun}
        onMergeRun={onMergeDistributedRun}
      />

      <FleetExecutorPanel
        registeredWorkers={fleetRegisteredWorkers}
        leasedJobs={fleetLeasedJobs}
        staleWorkers={fleetStaleWorkers}
        completedFragments={fleetCompletedFragments}
        totalJobs={fleetTotalJobs}
        mergedPacketStatus={fleetMergedPacketStatus}
        verifierGateStatus={fleetVerifierGateStatus}
        readiness={fleetReadiness}
      />

      <section style={fleetControlPanelStyle} aria-label="Fleet executor controls">
        <div style={fleetControlHeaderStyle}>
          <div>
            <h2 style={fleetControlTitleStyle}>Fleet executor controls</h2>
            <p style={fleetNoticeStyle}>
              These controls exercise the real fleet API path. Fleet merge stays
              blocked until a leased job returns an Evidence Packet fragment.
            </p>
            <label htmlFor="fleet-auth-token" style={labelStyle}>
              Protected API token
            </label>
            <input
              id="fleet-auth-token"
              type="password"
              autoComplete="off"
              spellCheck={false}
              value={fleetAuthToken}
              onChange={(event) => onFleetAuthTokenChange(event.target.value)}
              placeholder="Optional bearer token"
              style={fleetAuthInputStyle}
            />
          </div>
          <div style={fleetButtonRowStyle}>
            <button
              type="button"
              style={actionButtonStyle(canPrepareFleet)}
              disabled={!canPrepareFleet}
              onClick={onPrepareFleet}
            >
              Prepare fleet
            </button>
            <button
              type="button"
              style={actionButtonStyle(canRegisterFleetWorker)}
              disabled={!canRegisterFleetWorker}
              onClick={onRegisterFleetWorker}
            >
              Register demo worker
            </button>
            <button
              type="button"
              style={actionButtonStyle(canLeaseFleetJob)}
              disabled={!canLeaseFleetJob}
              onClick={onLeaseFleetJob}
            >
              Lease one job
            </button>
            <button
              type="button"
              style={actionButtonStyle(canSubmitFleetReceipt)}
              disabled={!canSubmitFleetReceipt}
              onClick={onSubmitFleetReceipt}
            >
              Submit one receipt
            </button>
            <button
              type="button"
              style={actionButtonStyle(canMergeFleet)}
              disabled={!canMergeFleet}
              onClick={onMergeFleet}
            >
              Merge fleet
            </button>
            <button
              type="button"
              style={actionButtonStyle(canRunFleetVerifier)}
              disabled={!canRunFleetVerifier}
              onClick={onRunFleetVerifier}
            >
              Run fleet verifier
            </button>
          </div>
        </div>
        {isFleetExecutorLoading ? (
          <p role="status" style={fleetNoticeStyle}>
            Fleet executor request in flight...
          </p>
        ) : null}
        {fleetExecutorError ? (
          <p role="status" style={{ ...fleetNoticeStyle, color: '#fecaca' }}>
            {fleetExecutorError}
          </p>
        ) : null}
        {fleetRun?.merged_packet_trace_id ? (
          <p role="status" style={fleetNoticeStyle}>
            Merged Evidence Packet: {fleetRun.merged_packet_trace_id}
          </p>
        ) : null}
        {fleetVerifierDecision ? (
          <div
            data-testid="fleet-verifier-decision"
            style={{
              display: 'grid',
              gap: 8,
              padding: 12,
              borderRadius: 8,
              border: '1px solid rgba(45, 212, 191, 0.28)',
              background: 'rgba(15, 23, 42, 0.54)',
            }}
          >
            <p style={{ ...fleetNoticeStyle, color: COLORS.textPrimary, fontWeight: 800 }}>
              Fleet verifier decision:{' '}
              {fleetVerifierDecision.verdict.replace(/_/g, ' ')}
            </p>
            <p style={fleetNoticeStyle}>
              Confidence:{' '}
              {fleetVerifierDecision.confidence === null
                ? 'not available'
                : `${Math.round(fleetVerifierDecision.confidence * 100)}%`}
              {' '}· Proof chips: {fleetVerifierDecision.proof_chip_gate}
            </p>
            <p style={fleetNoticeStyle}>{fleetVerifierDecision.reason}</p>
            {fleetVerifierDecision.blockers.length > 0 ? (
              <p style={fleetNoticeStyle}>
                Blocker: {fleetVerifierDecision.blockers.join(' ')}
              </p>
            ) : null}
          </div>
        ) : null}
        {fleetRun ? (
          <p style={fleetNoticeStyle}>
            Fleet merge reason: {fleetRun.merge_reason}
          </p>
        ) : null}
      </section>
    </div>
  );
}

export default AuditScaleFleetTab;
