import { useState, type CSSProperties } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import {
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  GLASS_PANEL_FILL,
  RADIUS,
} from '../../lib/designTokens';

export type FleetPacketStatus =
  | 'not_created'
  | 'waiting_for_receipts'
  | 'partial'
  | 'complete'
  | 'failed';

export type FleetVerifierGateStatus =
  | 'blocked'
  | 'waiting_for_packet'
  | 'ready'
  | 'running'
  | 'complete';

export interface FleetExecutorPanelProps {
  registered_workers: number;
  leased_jobs: number;
  stale_workers: number;
  completed_fragments: number;
  total_jobs: number;
  merged_packet_status: FleetPacketStatus;
  verifier_gate_status: FleetVerifierGateStatus;
  className?: string;
}

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
  fontFamily: FONT_FAMILY,
  color: COLORS.textPrimary,
  minWidth: 0,
  maxWidth: 820,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: ACCENT_TEAL,
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const titleStyle: CSSProperties = {
  margin: '3px 0 0',
  color: '#f8fafc',
  fontSize: 22,
  lineHeight: 1.15,
  fontWeight: 750,
  letterSpacing: 0,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
  flexWrap: 'wrap',
};

const headerCopyStyle: CSSProperties = {
  minWidth: 0,
};

const bodyTextStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.55,
};

const gateCardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  padding: 12,
  borderRadius: RADIUS.md,
  border: '1px solid rgba(45, 212, 191, 0.24)',
  background:
    'linear-gradient(135deg, rgba(20, 184, 166, 0.13), rgba(15, 23, 42, 0.62))',
};

const gateTitleStyle: CSSProperties = {
  margin: 0,
  color: '#ccfbf1',
  fontSize: 14,
  lineHeight: 1.35,
  fontWeight: 760,
};

const metricGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))',
  gap: 8,
};

const metricStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  minWidth: 0,
  padding: '10px 11px',
  borderRadius: RADIUS.md,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: GLASS_PANEL_FILL,
};

const metricLabelStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontSize: 11,
  fontWeight: 650,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const metricValueStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontSize: 14,
  lineHeight: 1.35,
  fontWeight: 750,
};

const sectionStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
};

const sectionTitleStyle: CSSProperties = {
  margin: 0,
  color: '#f8fafc',
  fontSize: 13,
  fontWeight: 750,
  letterSpacing: 0,
};

const checklistStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))',
  gap: 8,
};

const checkItemStyle: CSSProperties = {
  display: 'flex',
  gap: 9,
  alignItems: 'flex-start',
  padding: 10,
  borderRadius: RADIUS.md,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(15, 23, 42, 0.44)',
};

const checkDotBaseStyle: CSSProperties = {
  flex: '0 0 auto',
  width: 9,
  height: 9,
  marginTop: 5,
  borderRadius: 99,
};

const checkTextStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
  minWidth: 0,
};

const checkLabelStyle: CSSProperties = {
  color: COLORS.textPrimary,
  fontSize: 12,
  lineHeight: 1.35,
  fontWeight: 720,
};

const checkDetailStyle: CSSProperties = {
  color: COLORS.textSecondary,
  fontSize: 12,
  lineHeight: 1.45,
};

const monoStyle: CSSProperties = {
  fontFamily: FONT_MONO,
  fontWeight: 700,
};

const methodFaqWrapStyle: CSSProperties = {
  position: 'relative',
  flex: '0 0 auto',
};

const methodFaqButtonStyle: CSSProperties = {
  width: 28,
  height: 28,
  borderRadius: 999,
  border: '1px solid rgba(45, 212, 191, 0.28)',
  background: 'rgba(15, 23, 42, 0.72)',
  color: '#ccfbf1',
  fontFamily: FONT_MONO,
  fontSize: 14,
  fontWeight: 800,
  lineHeight: 1,
  cursor: 'help',
};

const methodFaqPopoverStyle: CSSProperties = {
  position: 'absolute',
  zIndex: 4,
  top: 34,
  right: 0,
  width: 'min(340px, calc(100vw - 64px))',
  padding: 12,
  borderRadius: RADIUS.md,
  border: '1px solid rgba(45, 212, 191, 0.24)',
  background: 'rgba(2, 6, 23, 0.96)',
  boxShadow: '0 18px 48px rgba(0, 0, 0, 0.42)',
  color: COLORS.textPrimary,
  fontSize: 12,
  lineHeight: 1.45,
};

const methodFaqTitleStyle: CSSProperties = {
  display: 'block',
  marginBottom: 6,
  color: '#ccfbf1',
  fontSize: 12,
  fontWeight: 760,
};

const methodFaqListStyle: CSSProperties = {
  margin: 0,
  paddingLeft: 17,
  color: COLORS.textSecondary,
};

const methodFaqActionStyle: CSSProperties = {
  margin: '7px 0 0',
  color: COLORS.textPrimary,
};

function MethodFaqHint() {
  const [open, setOpen] = useState(false);
  const tooltipId = 'fleet-s7-f28-method-faq';

  return (
    <div
      style={methodFaqWrapStyle}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        aria-label="Explain S7-F28 balanced-logistic Evidence Packet"
        aria-describedby={open ? tooltipId : undefined}
        aria-expanded={open}
        data-testid="fleet-method-faq-trigger"
        title="Audit method FAQ"
        style={methodFaqButtonStyle}
        onClick={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setOpen(false);
          }
        }}
      >
        ?
      </button>

      {open ? (
        <div
          id={tooltipId}
          role="tooltip"
          data-testid="fleet-method-faq"
          style={methodFaqPopoverStyle}
        >
          <strong style={methodFaqTitleStyle}>Audit method discipline</strong>
          <ul style={methodFaqListStyle}>
            <li>
              S7-F28 is the method label for this audit path. Use the same label
              when you check packet rows and verifier logs.
            </li>
            <li>
              Balanced-logistic means several evidence signals are combined into
              one calibrated score, with positive and negative cases balanced
              before the verdict is trusted.
            </li>
            <li>
              The Evidence Packet is the signed receipt: model, prompt set,
              knobs, worker fragments, score, verdict, and integrity hashes.
            </li>
            <li>
              The baseline is the opponent. If a text-only classifier can solve
              the labels from prompt wording alone, the run is blocked before GPU
              capture.
            </li>
            <li>
              Matched-taxonomy control asks whether CAS beats a rival coherent
              labeling, not just shuffled labels or chance.
            </li>
            <li>
              If CAS itself is not recoverable from hidden states, stop there:
              the fixture cannot test CAS specificity yet.
            </li>
          </ul>
          <p style={methodFaqActionStyle}>
            If fragments, hashes, or verifier rows are missing, hold the run
            instead of treating the verdict as final.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function formatStatus(status: string): string {
  return status
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function clampCount(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.floor(value));
}

function Metric({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId?: string;
}) {
  return (
    <div style={metricStyle}>
      <span style={metricLabelStyle}>{label}</span>
      <span data-testid={testId} style={metricValueStyle}>
        {value}
      </span>
    </div>
  );
}

function GateCheck({
  passed,
  label,
  detail,
  testId,
}: {
  passed: boolean;
  label: string;
  detail: string;
  testId: string;
}) {
  const color = passed ? '#2dd4bf' : '#f59e0b';
  return (
    <div data-testid={testId} style={checkItemStyle}>
      <span
        aria-hidden="true"
        style={{
          ...checkDotBaseStyle,
          background: color,
          boxShadow: `0 0 14px ${color}`,
        }}
      />
      <span style={checkTextStyle}>
        <span style={checkLabelStyle}>{label}</span>
        <span style={checkDetailStyle}>{detail}</span>
      </span>
    </div>
  );
}

function buildGateMessage({
  registeredWorkers,
  leasedJobs,
  staleWorkers,
  completedFragments,
  totalJobs,
  mergedPacketStatus,
  verifierGateStatus,
}: {
  registeredWorkers: number;
  leasedJobs: number;
  staleWorkers: number;
  completedFragments: number;
  totalJobs: number;
  mergedPacketStatus: FleetPacketStatus;
  verifierGateStatus: FleetVerifierGateStatus;
}): string {
  if (totalJobs === 0) {
    return 'Blocked: no distributed audit jobs have been created.';
  }
  if (registeredWorkers === 0) {
    return 'Blocked: no Probe Workers are registered for this run.';
  }
  if (leasedJobs < totalJobs) {
    return 'Blocked: not every distributed job has a worker lease.';
  }
  if (staleWorkers > 0) {
    return 'Blocked: stale worker heartbeat detected.';
  }
  if (completedFragments < totalJobs) {
    return 'Blocked: waiting for every worker Evidence Packet fragment.';
  }
  if (mergedPacketStatus !== 'complete') {
    return 'Blocked: merged Evidence Packet is not complete.';
  }
  if (verifierGateStatus !== 'ready' && verifierGateStatus !== 'complete') {
    return 'Blocked: verifier gate has not cleared the merged packet.';
  }
  return 'Ready: registry, leases, receipts, merged packet, and verifier gate are satisfied.';
}

export function FleetExecutorPanel({
  registered_workers,
  leased_jobs,
  stale_workers,
  completed_fragments,
  total_jobs,
  merged_packet_status,
  verifier_gate_status,
  className,
}: FleetExecutorPanelProps) {
  const registeredWorkers = clampCount(registered_workers);
  const leasedJobs = clampCount(leased_jobs);
  const staleWorkers = clampCount(stale_workers);
  const completedFragments = clampCount(completed_fragments);
  const totalJobs = clampCount(total_jobs);
  const hasJobs = totalJobs > 0;
  const leasesComplete = hasJobs && leasedJobs >= totalJobs;
  const receiptsComplete = hasJobs && completedFragments >= totalJobs;
  const noStaleWorkers = staleWorkers === 0;
  const packetComplete = merged_packet_status === 'complete';
  const verifierReady =
    verifier_gate_status === 'ready' || verifier_gate_status === 'complete';

  const gateMessage = buildGateMessage({
    registeredWorkers,
    leasedJobs,
    staleWorkers,
    completedFragments,
    totalJobs,
    mergedPacketStatus: merged_packet_status,
    verifierGateStatus: verifier_gate_status,
  });

  return (
    <GlassPanel
      as="section"
      intensity="regular"
      padding={16}
      className={className}
      ariaLabel="Distributed CAS Harness fleet executor"
      data-testid="fleet-executor-panel"
      style={panelStyle}
    >
      <header style={headerStyle}>
        <div style={headerCopyStyle}>
          <p style={eyebrowStyle}>Distributed fleet executor</p>
          <h2 style={titleStyle}>Worker registry, leases, receipts</h2>
        </div>
        <MethodFaqHint />
      </header>

      <p style={bodyTextStyle}>
        A 100B or 300B CAS Harness run does not move forward from a scale plan.
        It needs registered Probe Workers, leased jobs, fresh heartbeats, and
        returned Evidence Packet fragments before the verifier can judge the
        merged packet.
      </p>

      <section data-testid="fleet-executor-gate" style={gateCardStyle}>
        <h3 style={gateTitleStyle}>{gateMessage}</h3>
        <p style={bodyTextStyle}>
          The planner is only a map. The executor is the proof that workers
          actually touched the assigned model layers or shards and returned
          receipts.
        </p>
      </section>

      <div style={metricGridStyle} aria-label="Fleet executor metrics">
        <Metric
          label="Registered Workers"
          value={`${registeredWorkers}`}
          testId="fleet-registered-workers"
        />
        <Metric
          label="Leased Jobs"
          value={`${leasedJobs} / ${totalJobs}`}
          testId="fleet-leased-jobs"
        />
        <Metric
          label="Stale Workers"
          value={`${staleWorkers}`}
          testId="fleet-stale-workers"
        />
        <Metric
          label="Completed Fragments"
          value={`${completedFragments} / ${totalJobs}`}
          testId="fleet-completed-fragments"
        />
        <Metric
          label="Merged Packet"
          value={formatStatus(merged_packet_status)}
          testId="fleet-merged-packet-status"
        />
        <Metric
          label="Verifier Gate"
          value={formatStatus(verifier_gate_status)}
          testId="fleet-verifier-gate-status"
        />
      </div>

      <section style={sectionStyle} aria-labelledby="fleet-hard-gates">
        <h3 id="fleet-hard-gates" style={sectionTitleStyle}>
          Hard Gates
        </h3>
        <div style={checklistStyle}>
          <GateCheck
            passed={registeredWorkers > 0}
            label="Worker registry"
            detail={`${registeredWorkers} Probe Workers checked in for this audit.`}
            testId="fleet-gate-registry"
          />
          <GateCheck
            passed={leasesComplete}
            label="Job leases"
            detail={`${leasedJobs} of ${totalJobs} jobs leased. Every layer or shard must be claimed.`}
            testId="fleet-gate-leases"
          />
          <GateCheck
            passed={noStaleWorkers}
            label="Fresh heartbeats"
            detail={
              staleWorkers === 0
                ? 'No stale workers reported.'
                : `${staleWorkers} worker heartbeats are stale.`
            }
            testId="fleet-gate-heartbeats"
          />
          <GateCheck
            passed={receiptsComplete}
            label="Evidence receipts"
            detail={`${completedFragments} of ${totalJobs} Evidence Packet fragments returned.`}
            testId="fleet-gate-receipts"
          />
          <GateCheck
            passed={packetComplete}
            label="Merged packet"
            detail={`Merged Evidence Packet status: ${formatStatus(merged_packet_status)}.`}
            testId="fleet-gate-packet"
          />
          <GateCheck
            passed={verifierReady}
            label="Verifier decision gate"
            detail={`Verifier gate status: ${formatStatus(verifier_gate_status)}.`}
            testId="fleet-gate-verifier"
          />
        </div>
      </section>

      <p style={bodyTextStyle}>
        Forward rule:{' '}
        <span style={monoStyle}>
          worker registry + leases + receipts + merged packet + verifier gate
        </span>{' '}
        must all be satisfied before a large open-weight run can advance.
      </p>
    </GlassPanel>
  );
}

export default FleetExecutorPanel;
