import type { CSSProperties } from 'react';
import {
  COLORS,
  FONT_FAMILY,
  FONT_MONO,
  TONE_TINT,
} from '../../lib/designTokens';
import {
  lifecycleToTranscript,
  type TranscriptGlyphState,
  type TranscriptRow,
} from '../../lib/casHarnessAudit';

// Structural session shape — only what the transcript reads. Accepting a
// loose shape keeps this component decoupled from the API session type.
export interface AuditRunTranscriptSession {
  status?: string | null;
  lifecycle?: Array<{
    status?: string | null;
    message?: string | null;
    timestamp?: string | null;
  }> | null;
}

export interface AuditRunTranscriptProps {
  session: AuditRunTranscriptSession | null | undefined;
  /** Optional pre-computed rows (used by tests); defaults to deriving them. */
  rows?: TranscriptRow[];
  className?: string;
}

const GLYPH: Record<TranscriptGlyphState, string> = {
  done: '●',
  active: '◐',
  pending: '○',
  failed: '✕',
};

function glyphColor(state: TranscriptGlyphState): string {
  if (state === 'done') return TONE_TINT.teal.accent;
  if (state === 'active') return TONE_TINT.amber.accent;
  if (state === 'failed') return TONE_TINT.rose.accent;
  return COLORS.textMuted;
}

const shellStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
  fontFamily: FONT_FAMILY,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textSecondary,
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: 0.6,
  textTransform: 'uppercase',
};

const listStyle: CSSProperties = {
  display: 'grid',
  gap: 4,
  margin: 0,
  padding: 0,
  listStyle: 'none',
};

const rowStyle = (active: boolean): CSSProperties => ({
  display: 'grid',
  gridTemplateColumns: '16px 52px minmax(0, 1fr)',
  gap: 9,
  alignItems: 'baseline',
  padding: '6px 8px',
  borderRadius: 6,
  background: active ? TONE_TINT.amber.fillSoft : 'transparent',
  border: active ? `1px solid ${TONE_TINT.amber.borderSoft}` : '1px solid transparent',
});

const timeStyle: CSSProperties = {
  color: COLORS.textMuted,
  fontFamily: FONT_MONO,
  fontSize: 11,
  whiteSpace: 'nowrap',
};

const textStyle = (active: boolean): CSSProperties => ({
  color: active ? COLORS.textPrimary : COLORS.textSecondary,
  fontSize: 13,
  lineHeight: 1.45,
  fontWeight: active ? 600 : 500,
});

const emptyStyle: CSSProperties = {
  margin: 0,
  color: COLORS.textMuted,
  fontSize: 13,
  lineHeight: 1.45,
};

/**
 * Append-only, plain-English run log. Each row is `time · sentence · glyph`,
 * derived from `session.lifecycle[]` via `lifecycleToTranscript`. The active
 * row pulses on the brand heartbeat. This surface NEVER renders raw JSON —
 * every line is a sentence a reviewer can read.
 */
export function AuditRunTranscript({
  session,
  rows,
  className,
}: AuditRunTranscriptProps): JSX.Element {
  const transcript = rows ?? lifecycleToTranscript(session);

  return (
    <section style={shellStyle} className={className} aria-label="Audit run transcript">
      <p style={eyebrowStyle}>Run transcript</p>
      {transcript.length === 0 ? (
        <p style={emptyStyle}>
          No run activity yet. Start an audit and each step will narrate here in
          plain English.
        </p>
      ) : (
        <ol style={listStyle} aria-label="Audit run log">
          {transcript.map((row) => {
            const active = row.state === 'active';
            return (
              <li
                key={row.id}
                className="cas-fade-in"
                style={rowStyle(active)}
                data-state={row.state}
              >
                <span
                  aria-hidden="true"
                  className={active ? 'cas-step-breathe' : undefined}
                  style={{
                    color: glyphColor(row.state),
                    fontSize: 12,
                    animation: active
                      ? 'cas-step-breathe 2.5s ease-in-out infinite alternate'
                      : undefined,
                  }}
                >
                  {GLYPH[row.state]}
                </span>
                <span style={timeStyle}>{row.time}</span>
                <span style={textStyle(active)}>{row.text}</span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

export default AuditRunTranscript;
