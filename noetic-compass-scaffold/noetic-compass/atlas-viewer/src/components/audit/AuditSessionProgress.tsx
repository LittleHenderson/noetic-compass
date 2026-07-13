import type { CSSProperties } from 'react';
import { GlassPanel } from '../ui/GlassPanel';
import {
  ACCENT_AMBER,
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
} from '../../lib/designTokens';
import { AuditPopover } from './AuditPopover';

export type AuditLifecycleStatus =
  | 'draft'
  | 'validating'
  | 'running'
  | 'runner_pending'
  | 'evidence_pending'
  | 'complete'
  | 'failed';

export interface AuditSessionProgressProps {
  status: AuditLifecycleStatus;
  detail?: string | null;
  errorMessage?: string | null;
  className?: string;
}

interface ProgressStep {
  id: AuditLifecycleStatus;
  label: string;
  description: string;
}

const progressSteps: ProgressStep[] = [
  {
    id: 'draft',
    label: 'Draft',
    description: 'Model, scenario, and audit modules are being prepared.',
  },
  {
    id: 'validating',
    label: 'Validating model',
    description: 'Checking model access, model-license provenance, and runtime proof.',
  },
  {
    id: 'running',
    label: 'Running CAS audit',
    description: 'CAS modules are evaluating the selected model output.',
  },
  {
    id: 'runner_pending',
    label: 'Runner pending',
    description: 'The session exists, but the real audit runner is not connected yet.',
  },
  {
    id: 'evidence_pending',
    label: 'Building evidence packet',
    description: 'The verdict is waiting on the audit trail and packet links.',
  },
  {
    id: 'complete',
    label: 'Complete',
    description: 'Verdict and evidence are ready to review.',
  },
];

const failedStep: ProgressStep = {
  id: 'failed',
  label: 'Failed',
  description: 'The audit stopped before an evidence-gated verdict was produced.',
};

const statusCopy: Record<AuditLifecycleStatus, { headline: string; body: string }> = {
  draft: {
    headline: 'Audit not started',
    body: 'Connect the model and choose the modules before running CAS.',
  },
  validating: {
    headline: 'Validating model connection',
    body: 'CAS is checking whether the model is reachable and allowed to run.',
  },
  running: {
    headline: 'Running CAS audit',
    body: 'The selected CAS modules are evaluating the model output.',
  },
  runner_pending: {
    headline: 'Runner pending',
    body: 'The backend accepted the session, but no final CAS verdict was computed.',
  },
  evidence_pending: {
    headline: 'Evidence packet pending',
    body: 'The run has produced audit data and is assembling the packet.',
  },
  complete: {
    headline: 'Audit complete',
    body: 'The verdict is ready with its supporting evidence.',
  },
  failed: {
    headline: 'Audit failed',
    body: 'Do not use a verdict from this failed run.',
  },
};

const statusOrder: Record<AuditLifecycleStatus, number> = {
  draft: 0,
  validating: 1,
  running: 2,
  runner_pending: 3,
  evidence_pending: 4,
  complete: 5,
  failed: -1,
};

const shellStyle: CSSProperties = {
  display: 'grid',
  gap: 16,
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 12,
  fontWeight: 800,
  letterSpacing: 0,
  textTransform: 'uppercase',
};

const headlineStyle: CSSProperties = {
  margin: '5px 0 0',
  color: COLORS.textPrimary,
  fontSize: 20,
  lineHeight: 1.2,
  fontWeight: 850,
  letterSpacing: 0,
};

const statusPillStyle = (status: AuditLifecycleStatus): CSSProperties => {
  const failed = status === 'failed';
  const complete = status === 'complete';
  const active =
    status === 'running' ||
    status === 'validating' ||
    status === 'runner_pending' ||
    status === 'evidence_pending';
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    minHeight: 30,
    padding: '5px 10px',
    borderRadius: 6,
    border: `1px solid ${
      failed
        ? 'rgba(251, 113, 133, 0.42)'
        : complete
          ? 'rgba(45, 212, 191, 0.42)'
          : active
            ? 'rgba(251, 191, 36, 0.38)'
            : COLORS.borderStrong
    }`,
    background: failed
      ? 'rgba(251, 113, 133, 0.10)'
      : complete
        ? 'rgba(45, 212, 191, 0.11)'
        : active
          ? 'rgba(251, 191, 36, 0.10)'
          : 'rgba(255, 255, 255, 0.04)',
    color: failed ? '#ffe4e6' : complete ? '#ccfbf1' : active ? '#fef3c7' : COLORS.textSecondary,
    fontSize: 12,
    fontWeight: 800,
    whiteSpace: 'nowrap',
  };
};

const infoTipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 22,
  height: 22,
  marginTop: 8,
  borderRadius: 5,
  border: '1px solid rgba(45, 212, 191, 0.24)',
  background: 'rgba(45, 212, 191, 0.07)',
  color: '#ccfbf1',
  cursor: 'help',
  fontSize: 12,
  fontWeight: 900,
};

const stepListStyle: CSSProperties = {
  display: 'grid',
  gap: 9,
  margin: 0,
  padding: 0,
  listStyle: 'none',
};

const stepStyle = (state: 'done' | 'active' | 'pending' | 'failed'): CSSProperties => ({
  display: 'grid',
  gridTemplateColumns: '22px minmax(0, 1fr)',
  gap: 10,
  alignItems: 'flex-start',
  padding: '10px 11px',
  borderRadius: 8,
  border: `1px solid ${
    state === 'failed'
      ? 'rgba(251, 113, 133, 0.40)'
      : state === 'active'
        ? 'rgba(251, 191, 36, 0.38)'
        : state === 'done'
          ? 'rgba(45, 212, 191, 0.30)'
          : COLORS.borderSubtle
  }`,
  background:
    state === 'failed'
      ? 'rgba(251, 113, 133, 0.08)'
      : state === 'active'
        ? 'rgba(251, 191, 36, 0.08)'
        : state === 'done'
          ? 'rgba(45, 212, 191, 0.07)'
          : 'rgba(2, 6, 23, 0.28)',
});

const markerStyle = (state: 'done' | 'active' | 'pending' | 'failed'): CSSProperties => ({
  width: 18,
  height: 18,
  marginTop: 1,
  borderRadius: '50%',
  border: `1px solid ${
    state === 'failed'
      ? '#fb7185'
      : state === 'active'
        ? ACCENT_AMBER
        : state === 'done'
          ? ACCENT_TEAL
          : COLORS.borderStrong
  }`,
  background:
    state === 'failed'
      ? 'rgba(251, 113, 133, 0.22)'
      : state === 'active'
        ? 'rgba(251, 191, 36, 0.22)'
        : state === 'done'
          ? 'rgba(45, 212, 191, 0.20)'
          : 'rgba(255, 255, 255, 0.03)',
});

const stepLabelStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textPrimary,
  fontSize: 13,
  fontWeight: 800,
  lineHeight: 1.25,
};

function stepState(
  step: AuditLifecycleStatus,
  current: AuditLifecycleStatus,
): 'done' | 'active' | 'pending' | 'failed' {
  if (current === 'failed') return step === 'failed' ? 'failed' : 'pending';
  if (step === current) return 'active';
  return statusOrder[step] < statusOrder[current] ? 'done' : 'pending';
}

function visibleSteps(status: AuditLifecycleStatus): ProgressStep[] {
  return status === 'failed' ? [...progressSteps.slice(0, 3), failedStep] : progressSteps;
}

export function AuditSessionProgress({
  status,
  detail,
  errorMessage,
  className,
}: AuditSessionProgressProps): JSX.Element {
  const copy = statusCopy[status];
  const steps = visibleSteps(status);
  const activeDetail = detail ?? copy.body;
  const showSteps = status !== 'draft';

  return (
    <GlassPanel
      as="section"
      intensity="thin"
      padding={18}
      className={className}
      ariaLabel="Audit session progress"
    >
      <div style={shellStyle}>
        <div style={headerStyle}>
          <div>
            <p style={eyebrowStyle}>Audit progress</p>
            <h2 style={headlineStyle}>{copy.headline}</h2>
            <AuditPopover briefing={activeDetail} placement="right">
              <span aria-label={activeDetail} role="note" style={infoTipStyle}>
                ?
              </span>
            </AuditPopover>
          </div>
          <span style={statusPillStyle(status)}>{copy.headline}</span>
        </div>

        {status === 'failed' && errorMessage ? (
          <p
            role="alert"
            style={{
              margin: 0,
              padding: '10px 12px',
              borderRadius: 8,
              border: '1px solid rgba(251, 113, 133, 0.36)',
              background: 'rgba(251, 113, 133, 0.08)',
              color: '#ffe4e6',
              fontSize: 13,
              lineHeight: 1.45,
            }}
          >
            {errorMessage}
          </p>
        ) : null}

        {showSteps ? (
          <ol style={stepListStyle} aria-label="Audit lifecycle steps">
            {steps.map((step) => {
              const state = stepState(step.id, status);
              return (
                <li key={step.id} style={stepStyle(state)} data-state={state}>
                  <span aria-hidden="true" style={markerStyle(state)} />
                  <div>
                    <AuditPopover briefing={step.description} placement="bottom">
                      <p style={stepLabelStyle}>{step.label}</p>
                    </AuditPopover>
                  </div>
                </li>
              );
            })}
          </ol>
        ) : null}
      </div>
    </GlassPanel>
  );
}

export default AuditSessionProgress;
