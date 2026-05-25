import { useState, useCallback } from 'react';
import type { CSSProperties, ChangeEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '../ui/GlassPanel';
import {
  THEME,
  SPRING_SNAPPY,
  SPRING_GENTLE,
  GLASS_PANEL_FILL,
} from '../../lib/designTokens';
import type { TestingMethod, KnobDef } from '../../lib/testingMethods';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';

export type KnobValue = string | number | boolean | string[];

export type MethodKnobsDensity = 'compact' | 'comfortable';

export type ResolvedKnobs = Record<string, Record<string, unknown>>;

export interface MethodKnobsPanelProps {
  methods: TestingMethod[];
  enabledMethodIds: Set<string>;
  knobValues: Record<string, Record<string, KnobValue>>;
  onToggleMethod: (methodId: string, enabled: boolean) => void;
  onKnobChange: (methodId: string, knobId: string, value: KnobValue) => void;
  density?: MethodKnobsDensity;
  className?: string;
  /**
   * Worker echo of resolved knob values for the current LIVE session.
   * Drives the "Knob diagnostic" disclosure at the bottom of the panel.
   * Hidden behind ``import.meta.env.DEV`` OR
   * ``VITE_ATLAS_SHOW_KNOB_DIAGNOSTIC === 'true'`` so production builds
   * don't surface the diagnostic by default.
   */
  resolvedKnobs?: ResolvedKnobs | null;
  /**
   * Override the diagnostic visibility for tests. Production callers
   * should not pass this — the env-flag gating below is the contract.
   */
  showKnobDiagnostic?: boolean;
}

// Wave 5.2: when the picture panel is collapsed the controls panel gets
// more room, so we scale typography up. Compact = default cockpit (left
// panel open). Comfortable = wider column, bigger text for legibility.
function panelStyleFor(density: MethodKnobsDensity): CSSProperties {
  return {
    display: 'flex',
    flexDirection: 'column',
    gap: density === 'comfortable' ? 10 : 8,
    fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
    fontSize: density === 'comfortable' ? 14 : 13,
    color: '#e2e8f0',
    minWidth: density === 'comfortable' ? 360 : 320,
  };
}

const cardStyle = (enabled: boolean): CSSProperties => ({
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  // Wave 5.2: drop the gradient sheen. Sharper radius. Cleaner.
  border: `1px solid ${enabled ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.04)'}`,
  borderRadius: 6,
  background: enabled ? GLASS_PANEL_FILL : 'rgba(255, 255, 255, 0.01)',
  opacity: enabled ? 1 : 0.6,
  overflow: 'hidden',
  transition: 'border-color 0.15s ease, opacity 0.15s ease',
});

// Sheen removed — see Wave 5.2 cardStyle comment.
const cardSheenStyle: CSSProperties = { display: 'none' };

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: 10,
  minHeight: 40,
  flexWrap: 'wrap',
  position: 'relative',
};

const nameStyle: CSSProperties = {
  fontWeight: 700,
  flex: '1 1 auto',
};

const pillStyle = (background: string, fg = '#0f172a'): CSSProperties => ({
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 600,
  color: fg,
  background,
  backdropFilter: 'blur(8px) saturate(140%)',
  WebkitBackdropFilter: 'blur(8px) saturate(140%)',
});

const stageBadgeStyle: CSSProperties = {
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: 6,
  fontSize: 11,
  fontWeight: 500,
  color: '#cbd5e1',
  background: 'rgba(30, 41, 59, 0.6)',
  border: '1px solid rgba(255,255,255,0.06)',
};

const bodyStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  padding: '0 10px 12px 10px',
  borderTop: '1px solid rgba(255,255,255,0.05)',
  overflow: 'hidden',
};

const lineStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  lineHeight: 1.4,
};

const liveNoticeStyle: CSSProperties = {
  padding: 10,
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.24)',
  background: 'rgba(45, 212, 191, 0.07)',
  color: '#ccfbf1',
  fontSize: 12,
  lineHeight: 1.45,
};

const labelStrong: CSSProperties = {
  fontWeight: 600,
  color: '#94a3b8',
};

const knobRowStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  marginTop: 4,
};

const knobLabelStyle: CSSProperties = {
  fontSize: 12,
  fontWeight: 500,
  color: '#cbd5e1',
};

const inputStyle: CSSProperties = {
  padding: '4px 6px',
  borderRadius: 6,
  border: '1px solid rgba(255,255,255,0.08)',
  background: 'rgba(11, 18, 32, 0.7)',
  color: '#e5e7eb',
  fontSize: 12,
};

const chevronStyle: CSSProperties = {
  cursor: 'pointer',
  background: 'transparent',
  border: 'none',
  color: '#cbd5e1',
  fontSize: 14,
  padding: 4,
};

const switchTrackStyle = (on: boolean): CSSProperties => ({
  width: 32,
  height: 18,
  borderRadius: 999,
  background: on ? ATLAS_STATUS_COLORS.accepted : 'rgba(55, 65, 81, 0.8)',
  position: 'relative',
  display: 'inline-block',
  flexShrink: 0,
  border: '1px solid rgba(255,255,255,0.08)',
  transition: 'background 200ms ease',
});

const switchThumbStyle: CSSProperties = {
  position: 'absolute',
  top: 1,
  width: 14,
  height: 14,
  borderRadius: '50%',
  background: '#f8fafc',
  boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
};

function defaultForKnob(k: KnobDef): KnobValue {
  if (k.type === 'multiselect') return Array.isArray(k.default) ? [...(k.default as string[])] : [];
  if (k.type === 'boolean') return Boolean(k.default);
  if (k.type === 'number') return typeof k.default === 'number' ? k.default : 0;
  return String(k.default ?? '');
}

function valueFor(
  knobValues: Record<string, Record<string, KnobValue>>,
  methodId: string,
  knob: KnobDef,
): KnobValue {
  const v = knobValues[methodId]?.[knob.id];
  if (v === undefined) return defaultForKnob(knob);
  return v;
}

function renderKnob(
  methodId: string,
  knob: KnobDef,
  value: KnobValue,
  disabled: boolean,
  onKnobChange: (methodId: string, knobId: string, value: KnobValue) => void,
) {
  const controlId = `knob-${methodId}-${knob.id}`;

  if (knob.type === 'enum') {
    const options = (knob.options as readonly string[] | undefined) ?? [];
    return (
      <div style={knobRowStyle} key={knob.id}>
        <label htmlFor={controlId} style={knobLabelStyle}>
          {knob.label}
        </label>
        <select
          id={controlId}
          data-testid={`knob-${methodId}-${knob.id}`}
          disabled={disabled}
          value={String(value)}
          onChange={(e: ChangeEvent<HTMLSelectElement>) =>
            onKnobChange(methodId, knob.id, e.target.value)
          }
          style={inputStyle}
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (knob.type === 'number') {
    const num = typeof value === 'number' ? value : Number(value);
    const placeholder =
      typeof knob.default === 'number' ? String(knob.default) : undefined;
    return (
      <div style={knobRowStyle} key={knob.id}>
        <label htmlFor={controlId} style={knobLabelStyle}>
          {knob.label}
        </label>
        <input
          id={controlId}
          data-testid={`knob-${methodId}-${knob.id}`}
          type="number"
          disabled={disabled}
          value={Number.isFinite(num) ? num : ''}
          placeholder={placeholder}
          onChange={(e: ChangeEvent<HTMLInputElement>) => {
            const parsed = e.target.value === '' ? 0 : Number(e.target.value);
            onKnobChange(methodId, knob.id, parsed);
          }}
          style={inputStyle}
        />
      </div>
    );
  }

  if (knob.type === 'boolean') {
    const checked = Boolean(value);
    return (
      <div style={knobRowStyle} key={knob.id}>
        <label htmlFor={controlId} style={knobLabelStyle}>
          <input
            id={controlId}
            data-testid={`knob-${methodId}-${knob.id}`}
            type="checkbox"
            disabled={disabled}
            checked={checked}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              onKnobChange(methodId, knob.id, e.target.checked)
            }
            style={{ marginRight: 6 }}
          />
          {knob.label}
        </label>
      </div>
    );
  }

  const opts = (knob.options as readonly string[] | undefined) ?? [];
  const current = Array.isArray(value) ? (value as string[]) : [];
  return (
    <div
      style={knobRowStyle}
      key={knob.id}
      role="group"
      aria-labelledby={`${controlId}-label`}
    >
      <span id={`${controlId}-label`} style={knobLabelStyle}>
        {knob.label}
      </span>
      <div
        data-testid={`knob-${methodId}-${knob.id}`}
        style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}
      >
        {opts.map((opt) => {
          const isChecked = current.includes(opt);
          const optId = `${controlId}-${opt}`;
          return (
            <label
              key={opt}
              htmlFor={optId}
              style={{
                ...knobLabelStyle,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <input
                id={optId}
                data-testid={`knob-${methodId}-${knob.id}-${opt}`}
                type="checkbox"
                disabled={disabled}
                checked={isChecked}
                onChange={(e: ChangeEvent<HTMLInputElement>) => {
                  const next = e.target.checked
                    ? [...current, opt]
                    : current.filter((c) => c !== opt);
                  onKnobChange(methodId, knob.id, next);
                }}
              />
              {opt}
            </label>
          );
        })}
      </div>
    </div>
  );
}

function isKnobDiagnosticEnabled(): boolean {
  // `import.meta` shape varies between vitest + vite runtimes — guard
  // defensively so the panel never throws when env is unavailable.
  try {
    const env = (import.meta as { env?: Record<string, unknown> }).env ?? {};
    if (env.DEV === true) return true;
    if (env.VITE_ATLAS_SHOW_KNOB_DIAGNOSTIC === 'true') return true;
  } catch {
    // SSR / non-vite consumers — diagnostic stays off.
  }
  return false;
}

function looselyEqual(sent: unknown, resolved: unknown): boolean {
  // Tolerant comparator: number-string equality OK, array order ignored.
  if (sent === resolved) return true;
  if (Array.isArray(sent) && Array.isArray(resolved)) {
    if (sent.length !== resolved.length) return false;
    const sa = [...sent].map(String).sort();
    const sb = [...resolved].map(String).sort();
    return sa.every((v, i) => v === sb[i]);
  }
  if (sent === null || sent === undefined) {
    return resolved === null || resolved === undefined;
  }
  if (resolved === null || resolved === undefined) return false;
  if (typeof sent === 'number' || typeof resolved === 'number') {
    return Number(sent) === Number(resolved);
  }
  return String(sent) === String(resolved);
}

interface KnobDiagnosticRowProps {
  methodId: string;
  methodName: string;
  sent?: Record<string, KnobValue>;
  resolved?: Record<string, unknown>;
}

function KnobDiagnosticRow({
  methodId,
  methodName,
  sent,
  resolved,
}: KnobDiagnosticRowProps) {
  // Only enumerate knobs that appear on EITHER side so the disclosure
  // doesn't fabricate ✓ matches against fields the worker doesn't
  // consume. ``cover_available`` / ``active`` are worker-only diagnostic
  // bits — they render below as resolved-only entries (no Sent side).
  const knobIds = new Set<string>();
  for (const k of Object.keys(sent ?? {})) knobIds.add(k);
  for (const k of Object.keys(resolved ?? {})) knobIds.add(k);
  const rows = [...knobIds].sort();

  if (rows.length === 0) {
    return (
      <div
        data-testid={`knob-diagnostic-row-${methodId}`}
        style={{
          padding: '6px 8px',
          fontSize: 11,
          color: '#94a3b8',
        }}
      >
        <strong style={{ color: '#cbd5e1' }}>{methodName}</strong>
        <span style={{ marginLeft: 8, fontStyle: 'italic' }}>
          (no resolved knobs)
        </span>
      </div>
    );
  }

  return (
    <div
      data-testid={`knob-diagnostic-row-${methodId}`}
      style={{
        padding: '6px 8px',
        fontSize: 11,
        color: '#cbd5e1',
        borderTop: '1px solid rgba(255,255,255,0.04)',
      }}
    >
      <strong style={{ color: '#cbd5e1', display: 'block', marginBottom: 4 }}>
        {methodName}
      </strong>
      {rows.map((knobId) => {
        const sentVal = sent?.[knobId];
        const resolvedVal = resolved?.[knobId];
        const sentPresent = sent && knobId in sent;
        const resolvedPresent = resolved && knobId in resolved;
        const match =
          sentPresent && resolvedPresent
            ? looselyEqual(sentVal, resolvedVal)
            : null;
        return (
          <div
            key={knobId}
            data-testid={`knob-diagnostic-${methodId}-${knobId}`}
            data-knob-match={
              match === null ? 'na' : match ? 'true' : 'false'
            }
            style={{
              display: 'grid',
              gridTemplateColumns: '90px 1fr 1fr 16px',
              gap: 6,
              alignItems: 'baseline',
              padding: '2px 0',
              fontFamily: 'ui-monospace, SFMono-Regular, monospace',
              fontSize: 11,
            }}
          >
            <span style={{ color: '#94a3b8' }}>{knobId}</span>
            <span style={{ color: '#e2e8f0' }}>
              {sentPresent ? `Sent: ${JSON.stringify(sentVal)}` : '—'}
            </span>
            <span style={{ color: '#e2e8f0' }}>
              {resolvedPresent
                ? `Resolved: ${JSON.stringify(resolvedVal)}`
                : '—'}
            </span>
            <span
              aria-label={
                match === null
                  ? 'no comparison'
                  : match
                    ? 'match'
                    : 'mismatch'
              }
              style={{
                color:
                  match === null
                    ? '#94a3b8'
                    : match
                      ? '#22c55e'
                      : '#fb7185',
                fontWeight: 700,
              }}
            >
              {match === null ? '·' : match ? '✓' : '✗'}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function MethodKnobsPanel({
  methods,
  enabledMethodIds,
  knobValues,
  onToggleMethod,
  onKnobChange,
  density = 'compact',
  className,
  resolvedKnobs = null,
  showKnobDiagnostic,
}: MethodKnobsPanelProps) {
  const ordered = [...methods].sort((a, b) => a.orderIndex - b.orderIndex);
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(ordered.map((m) => m.id)),
  );
  const [diagnosticOpen, setDiagnosticOpen] = useState<boolean>(false);
  const diagnosticVisible =
    showKnobDiagnostic !== undefined
      ? showKnobDiagnostic
      : isKnobDiagnosticEnabled();

  const toggleExpand = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const panelStyle = panelStyleFor(density);

  return (
    <GlassPanel
      intensity="regular"
      as="aside"
      className={className}
      padding={density === 'comfortable' ? 16 : 12}
      style={panelStyle}
      data-density={density}
    >
      <div data-testid="method-knobs-panel" style={{ display: 'contents' }}>
        <div style={liveNoticeStyle} data-testid="live-methods-contract">
          These are live-worker controls. Enabled modules are sent to the
          running Pythia worker on LIVE start; changing a switch or knob while
          LIVE is active restarts the stream with the new test configuration.
        </div>
        {ordered.map((method) => {
          const enabled = enabledMethodIds.has(method.id);
          const isOpen = expanded.has(method.id);
          const nameId = `method-${method.id}-name`;
          const isFree = method.costEstimateGpuMinutes === 0;
          const costLabel = isFree
            ? 'Free'
            : `${method.costEstimateGpuMinutes} GPU-min`;
          const costBg = isFree
            ? 'rgba(34, 197, 94, 0.35)'
            : 'rgba(203, 213, 225, 0.85)';
          const costFg = isFree ? '#dcfce7' : '#0f172a';
          const statusColor = enabled
            ? ATLAS_STATUS_COLORS.accepted
            : ATLAS_STATUS_COLORS.unavailable;

          return (
            <motion.section
              key={method.id}
              data-testid={`method-card-${method.id}`}
              role="group"
              aria-labelledby={nameId}
              style={cardStyle(enabled)}
              whileHover={{
                borderColor: enabled
                  ? 'rgba(255, 255, 255, 0.14)'
                  : 'rgba(255, 255, 255, 0.06)',
              }}
              transition={SPRING_SNAPPY}
            >
              <span aria-hidden="true" style={cardSheenStyle} />
              <header style={headerStyle}>
                <span id={nameId} style={nameStyle}>
                  {method.name}
                </span>
                <span
                  data-testid={`method-stage-${method.id}`}
                  style={stageBadgeStyle}
                >
                  {method.stageAnchor.split('(')[0].trim()}
                </span>
                <span
                  data-testid={`method-cost-${method.id}`}
                  style={pillStyle(costBg, costFg)}
                >
                  {costLabel}
                </span>
                <span
                  data-testid={`method-status-${method.id}`}
                  style={pillStyle(statusColor)}
                >
                  {enabled ? 'sent live' : 'off'}
                </span>
                <label
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    cursor: 'pointer',
                  }}
                >
                  <input
                    data-testid={`method-toggle-${method.id}`}
                    type="checkbox"
                    checked={enabled}
                    aria-label={`Enable ${method.name}`}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      onToggleMethod(method.id, e.target.checked)
                    }
                    style={{
                      position: 'absolute',
                      width: 1,
                      height: 1,
                      opacity: 0,
                      margin: -1,
                      overflow: 'hidden',
                    }}
                  />
                  <span aria-hidden="true" style={switchTrackStyle(enabled)}>
                    <motion.span
                      layout
                      layoutId={`switch-thumb-${method.id}`}
                      style={{
                        ...switchThumbStyle,
                        left: enabled ? 16 : 2,
                      }}
                      transition={SPRING_SNAPPY}
                    />
                  </span>
                </label>
                <button
                  type="button"
                  data-testid={`method-expand-${method.id}`}
                  aria-expanded={isOpen}
                  aria-label={
                    isOpen
                      ? `Collapse ${method.name}`
                      : `Expand ${method.name}`
                  }
                  onClick={() => toggleExpand(method.id)}
                  style={chevronStyle}
                >
                  {isOpen ? '▾' : '▸'}
                </button>
              </header>

              <AnimatePresence initial={false}>
                {isOpen ? (
                  <motion.div
                    key="body"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    transition={SPRING_GENTLE}
                    style={bodyStyle}
                  >
                    <p style={lineStyle}>{method.description}</p>
                    <p style={lineStyle}>
                      <span style={labelStrong}>Reveals: </span>
                      {method.reveals}
                    </p>
                    <p style={lineStyle}>
                      <span style={labelStrong}>Output: </span>
                      {method.outputShape}
                    </p>
                    <div
                      data-testid={`method-knobs-${method.id}`}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 4,
                      }}
                    >
                      {method.knobs.map((knob) =>
                        renderKnob(
                          method.id,
                          knob,
                          valueFor(knobValues, method.id, knob),
                          !enabled,
                          onKnobChange,
                        ),
                      )}
                    </div>
                    <p style={lineStyle}>
                      <span style={labelStrong}>Prerequisites: </span>
                      {method.prerequisites.length > 0
                        ? method.prerequisites.join('; ')
                        : 'none'}
                    </p>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </motion.section>
          );
        })}
        {diagnosticVisible ? (
          <section
            data-testid="knob-diagnostic-panel"
            style={{
              marginTop: 6,
              border: '1px solid rgba(255,255,255,0.04)',
              borderRadius: 6,
              background: 'rgba(15, 23, 42, 0.45)',
              overflow: 'hidden',
            }}
          >
            <button
              type="button"
              data-testid="knob-diagnostic-toggle"
              aria-expanded={diagnosticOpen}
              onClick={() => setDiagnosticOpen((v) => !v)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 10px',
                background: 'transparent',
                border: 'none',
                color: '#cbd5e1',
                cursor: 'pointer',
                fontSize: 12,
                fontWeight: 600,
                textAlign: 'left',
                letterSpacing: 0.3,
              }}
            >
              <span aria-hidden="true">{diagnosticOpen ? '▾' : '▸'}</span>
              <span>Knob diagnostic</span>
              <span
                style={{ marginLeft: 'auto', color: '#94a3b8', fontWeight: 400 }}
              >
                {resolvedKnobs
                  ? 'Sent vs worker-resolved'
                  : 'awaiting worker echo…'}
              </span>
            </button>
            <AnimatePresence initial={false}>
              {diagnosticOpen ? (
                <motion.div
                  key="diagnostic-body"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={SPRING_GENTLE}
                  style={{ overflow: 'hidden' }}
                  data-testid="knob-diagnostic-body"
                >
                  {resolvedKnobs ? (
                    ordered.map((method) => (
                      <KnobDiagnosticRow
                        key={method.id}
                        methodId={method.id}
                        methodName={method.name}
                        sent={knobValues[method.id]}
                        resolved={resolvedKnobs[method.id]}
                      />
                    ))
                  ) : (
                    <div
                      data-testid="knob-diagnostic-empty"
                      style={{
                        padding: 10,
                        fontSize: 11,
                        color: '#94a3b8',
                        fontStyle: 'italic',
                      }}
                    >
                      Worker has not echoed any resolved knobs yet. Start
                      a LIVE session to see Sent vs Resolved per method.
                    </div>
                  )}
                </motion.div>
              ) : null}
            </AnimatePresence>
          </section>
        ) : null}
      </div>
    </GlassPanel>
  );
}

void THEME;
