import { useEffect, useState, type CSSProperties } from 'react';
import { TreeOfLifeMark } from '../brand/TreeOfLifeMark';
import { LicenseChip } from '../audit/LicenseChip';
import {
  listCasHarnessAuditSessions,
  type CasHarnessAuditSession,
} from '../../lib/casHarnessAuditApi';
import {
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
} from '../../lib/designTokens';
import type { LicenseState as LicenseStateValue } from '../../lib/casHarnessAudit';

export interface AuditRailScopeChip {
  label: string;
  /** True for a validation/scoped run (amber); false for a calm teal scope. */
  validation?: boolean;
}

export interface AuditRailProps {
  /** License chip state (persistent). */
  licenseState?: LicenseStateValue;
  /** Always-visible scope chip; omitted until a scope is known. */
  scopeChip?: AuditRailScopeChip | null;
  /** Currently-open session id, to highlight in Recent Runs. */
  activeSessionId?: string | null;
  /** Reset the workspace to a fresh audit (also fired by clicking the mark). */
  onNewAudit?: () => void;
  /** Select a prior run from the Recent Runs list. */
  onSelectSession?: (session: CasHarnessAuditSession) => void;
  /** Open help / methodology. */
  onHelp?: () => void;
  /** Open settings. */
  onSettings?: () => void;
  /** Refetch token — bump to reload Recent Runs after a run completes. */
  reloadKey?: number;
  authToken?: string | null;
  accountLabel?: string | null;
  onLogout?: () => void;
}

const railStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
  height: '100%',
  minHeight: 0,
  padding: 16,
  fontFamily: FONT_FAMILY,
};

const brandRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  padding: 0,
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  textAlign: 'left',
  color: 'inherit',
};

const wordmarkStyle: CSSProperties = {
  display: 'grid',
  gap: 1,
};

const wordmarkTitleStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 900,
  letterSpacing: 1.4,
  color: COLORS.textPrimary,
};

const wordmarkSubStyle: CSSProperties = {
  fontSize: 9.5,
  fontWeight: 600,
  letterSpacing: 1.2,
  textTransform: 'uppercase',
  color: COLORS.textMuted,
};

const newAuditButtonStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 6,
  minHeight: 38,
  padding: '8px 12px',
  borderRadius: 8,
  border: `1px solid ${TONE_TINT.teal.border}`,
  background: TONE_TINT.teal.fill,
  color: TONE_TINT.teal.text,
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 13,
  fontWeight: 800,
  letterSpacing: 0.3,
};

const sectionLabelStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 10.5,
  fontWeight: 800,
  letterSpacing: 0.8,
  textTransform: 'uppercase',
};

const recentListStyle: CSSProperties = {
  display: 'grid',
  gap: 4,
  margin: 0,
  padding: 0,
  listStyle: 'none',
  overflowY: 'auto',
  minHeight: 0,
  flex: 1,
};

const recentItemStyle = (active: boolean): CSSProperties => ({
  display: 'grid',
  gap: 2,
  width: '100%',
  padding: '7px 9px',
  borderRadius: 6,
  border: `1px solid ${active ? TONE_TINT.teal.borderSoft : 'transparent'}`,
  background: active ? TONE_TINT.teal.fillSoft : 'transparent',
  color: COLORS.textPrimary,
  cursor: 'pointer',
  textAlign: 'left',
  fontFamily: 'inherit',
});

const recentIdStyle: CSSProperties = {
  fontFamily: FONT_MONO,
  fontSize: 11.5,
  fontWeight: 700,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const recentMetaStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontSize: 10.5,
};

const mutedNoteStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textMuted,
  fontSize: 11.5,
  lineHeight: 1.45,
};

const footerStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
  marginTop: 'auto',
  paddingTop: 12,
  borderTop: `1px solid ${COLORS.borderSubtle}`,
};

const scopeChipStyle = (validation: boolean): CSSProperties => {
  const tone = validation ? TONE_TINT.amber : TONE_TINT.teal;
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 7,
    minHeight: 26,
    padding: '4px 9px',
    borderRadius: 6,
    border: `1px solid ${validation ? tone.border : tone.borderSoft}`,
    background: tone.fillSoft,
    color: tone.text,
    fontSize: 11,
    fontWeight: 700,
    lineHeight: 1.3,
  };
};

const helpRowStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
};

const accountLabelStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textMuted,
  fontFamily: FONT_MONO,
  fontSize: 10.5,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const helpButtonStyle: CSSProperties = {
  flex: 1,
  minHeight: 32,
  padding: '6px 8px',
  borderRadius: 6,
  border: `1px solid ${COLORS.borderSubtle}`,
  background: 'rgba(255, 255, 255, 0.03)',
  color: COLORS.textSecondary,
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 12,
  fontWeight: 700,
};

function recentVerdictWord(session: CasHarnessAuditSession): string {
  if (session.verdict) return session.verdict.replace(/_/g, ' ');
  return session.status.replace(/_/g, ' ').toLowerCase();
}

/**
 * Left rail — the persistent CAS Harness identity and navigation column.
 * Carries the breathing 10-dot mark + wordmark (click = New Audit), the
 * +New Audit button, Recent Runs (real `/sessions`), and the persistent scope
 * + license chips. Recent Runs fetches fail-soft: a worker outage leaves a calm
 * muted note rather than an error.
 */
export function AuditRail({
  licenseState,
  scopeChip = null,
  activeSessionId = null,
  onNewAudit,
  onSelectSession,
  onHelp,
  onSettings,
  reloadKey = 0,
  authToken = null,
  accountLabel = null,
  onLogout,
}: AuditRailProps): JSX.Element {
  const [recent, setRecent] = useState<CasHarnessAuditSession[] | null>(null);
  const [recentFailed, setRecentFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setRecentFailed(false);
    listCasHarnessAuditSessions({ signal: controller.signal, authToken })
      .then((list) => {
        if (active) setRecent(list.sessions);
      })
      .catch(() => {
        // Fail soft — show a calm note, never an error banner in the rail.
        if (active) setRecentFailed(true);
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [authToken, reloadKey]);

  return (
    <nav style={railStyle} aria-label="CAS Harness navigation">
      <button
        type="button"
        style={brandRowStyle}
        onClick={onNewAudit}
        aria-label="CAS Harness — start a new audit"
      >
        <TreeOfLifeMark size={32} animated title="CAS Harness" />
        <span style={wordmarkStyle}>
          <span style={wordmarkTitleStyle}>CAS HARNESS</span>
          <span style={wordmarkSubStyle}>Audit Bench</span>
        </span>
      </button>

      <button type="button" style={newAuditButtonStyle} onClick={onNewAudit}>
        + New Audit
      </button>

      <div style={{ display: 'grid', gap: 8, minHeight: 0, flex: 1 }}>
        <p style={sectionLabelStyle}>Recent runs</p>
        {recent && recent.length > 0 ? (
          <ul style={recentListStyle} aria-label="Recent audit runs">
            {recent.map((session) => {
              const isActive = session.audit_id === activeSessionId;
              return (
                <li key={session.audit_id}>
                  <button
                    type="button"
                    style={recentItemStyle(isActive)}
                    aria-current={isActive ? 'true' : undefined}
                    onClick={() => onSelectSession?.(session)}
                  >
                    <span style={recentIdStyle}>{session.audit_id}</span>
                    <span style={recentMetaStyle}>
                      {session.model_id ?? 'unknown model'} · {recentVerdictWord(session)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : recentFailed ? (
          <p style={mutedNoteStyle}>
            Recent runs are unavailable right now. The audit history will appear
            here once the backend is reachable.
          </p>
        ) : recent ? (
          <p style={mutedNoteStyle}>
            No audit runs yet. Start one and it will appear here.
          </p>
        ) : (
          <p style={mutedNoteStyle}>Loading recent runs…</p>
        )}
      </div>

      <div style={footerStyle}>
        {scopeChip ? (
          <span
            role="note"
            aria-label={`Scope: ${scopeChip.label}`}
            style={scopeChipStyle(Boolean(scopeChip.validation))}
          >
            {scopeChip.label}
          </span>
        ) : null}
        <LicenseChip state={licenseState} />
        {accountLabel ? <p style={accountLabelStyle}>{accountLabel}</p> : null}
        <div style={helpRowStyle}>
          <button type="button" style={helpButtonStyle} onClick={onHelp}>
            ? Help
          </button>
          <button type="button" style={helpButtonStyle} onClick={onSettings}>
            ⚙ Settings
          </button>
        </div>
        {onLogout ? (
          <button type="button" style={helpButtonStyle} onClick={onLogout}>
            Sign out
          </button>
        ) : null}
      </div>
    </nav>
  );
}

export default AuditRail;
