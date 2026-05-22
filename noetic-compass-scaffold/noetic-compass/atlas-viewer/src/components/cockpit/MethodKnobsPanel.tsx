import { useState, useCallback } from 'react';
import type { CSSProperties, ChangeEvent } from 'react';
import type { TestingMethod, KnobDef } from '../../lib/testingMethods';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';

export type KnobValue = string | number | boolean | string[];

export interface MethodKnobsPanelProps {
  methods: TestingMethod[];
  enabledMethodIds: Set<string>;
  knobValues: Record<string, Record<string, KnobValue>>;
  onToggleMethod: (methodId: string, enabled: boolean) => void;
  onKnobChange: (methodId: string, knobId: string, value: KnobValue) => void;
  className?: string;
}

const panelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  padding: 12,
  fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  fontSize: 13,
  color: '#e5e7eb',
  background: '#0f172a',
  borderRadius: 6,
  minWidth: 320,
};

const cardStyle = (enabled: boolean): CSSProperties => ({
  display: 'flex',
  flexDirection: 'column',
  border: `1px solid ${enabled ? '#1f2937' : '#374151'}`,
  borderRadius: 6,
  background: enabled ? '#111827' : '#1f2937',
  opacity: enabled ? 1 : 0.6,
});

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: 10,
  minHeight: 40,
  flexWrap: 'wrap',
};

const nameStyle: CSSProperties = {
  fontWeight: 700,
  flex: '1 1 auto',
};

const badgeStyle = (background: string): CSSProperties => ({
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 600,
  color: '#0f172a',
  background,
});

const stageBadgeStyle: CSSProperties = {
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: 4,
  fontSize: 11,
  fontWeight: 500,
  color: '#cbd5e1',
  background: '#1e293b',
  border: '1px solid #334155',
};

const bodyStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  padding: '0 10px 12px 10px',
  borderTop: '1px solid #1e293b',
};

const lineStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  lineHeight: 1.4,
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
  borderRadius: 4,
  border: '1px solid #334155',
  background: '#0b1220',
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

  // multiselect
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

export default function MethodKnobsPanel({
  methods,
  enabledMethodIds,
  knobValues,
  onToggleMethod,
  onKnobChange,
  className,
}: MethodKnobsPanelProps) {
  const ordered = [...methods].sort((a, b) => a.orderIndex - b.orderIndex);
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(ordered.map((m) => m.id)),
  );

  const toggleExpand = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  return (
    <div
      className={className}
      data-testid="method-knobs-panel"
      style={panelStyle}
    >
      {ordered.map((method) => {
        const enabled = enabledMethodIds.has(method.id);
        const isOpen = expanded.has(method.id);
        const nameId = `method-${method.id}-name`;
        const costLabel =
          method.costEstimateGpuMinutes === 0
            ? 'Free'
            : `${method.costEstimateGpuMinutes} GPU-min`;
        const statusColor = enabled
          ? ATLAS_STATUS_COLORS.accepted
          : ATLAS_STATUS_COLORS.unavailable;

        return (
          <section
            key={method.id}
            data-testid={`method-card-${method.id}`}
            role="group"
            aria-labelledby={nameId}
            style={cardStyle(enabled)}
          >
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
                style={badgeStyle('#cbd5e1')}
              >
                {costLabel}
              </span>
              <span
                data-testid={`method-status-${method.id}`}
                style={badgeStyle(statusColor)}
              >
                {enabled ? 'enabled' : 'disabled'}
              </span>
              {/* a11y: toggle exposed as a checkbox so screen readers announce state */}
              <label
                style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
              >
                <input
                  data-testid={`method-toggle-${method.id}`}
                  type="checkbox"
                  checked={enabled}
                  aria-label={`Enable ${method.name}`}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    onToggleMethod(method.id, e.target.checked)
                  }
                />
              </label>
              <button
                type="button"
                data-testid={`method-expand-${method.id}`}
                aria-expanded={isOpen}
                aria-label={
                  isOpen ? `Collapse ${method.name}` : `Expand ${method.name}`
                }
                onClick={() => toggleExpand(method.id)}
                style={chevronStyle}
              >
                {isOpen ? '▾' : '▸'}
              </button>
            </header>

            {isOpen && (
              <div style={bodyStyle}>
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
                  style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
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
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
