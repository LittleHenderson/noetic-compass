import { useMemo, useState, type CSSProperties } from 'react';

import {
  ALPHA_SCENARIOS,
  CAS_DRIVE_VALUES,
  SCENARIO_DIFFICULTIES,
  filterAlphaScenarios,
  type AlphaScenario,
  type CasDrive,
  type ScenarioDifficulty,
} from '../../lib/alphaScenarios';

interface ScenarioPickerProps {
  scenarios?: readonly AlphaScenario[];
  selectedId?: string;
  onSelect?: (scenario: AlphaScenario) => void;
}

const panelStyle = {
  display: 'grid',
  gap: 12,
  color: '#e5eefb',
} satisfies CSSProperties;

const controlsStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
  gap: 8,
} satisfies CSSProperties;

const labelStyle = {
  display: 'grid',
  gap: 4,
  fontSize: 12,
  color: '#9fb0c4',
} satisfies CSSProperties;

const selectStyle = {
  border: '1px solid rgba(148, 163, 184, 0.35)',
  borderRadius: 8,
  background: 'rgba(15, 23, 42, 0.82)',
  color: '#e5eefb',
  padding: '8px 10px',
} satisfies CSSProperties;

const listStyle = {
  display: 'grid',
  gap: 8,
  maxHeight: 360,
  overflowY: 'auto',
} satisfies CSSProperties;

function scenarioCardStyle(selected: boolean): CSSProperties {
  return {
    border: selected
      ? '1px solid rgba(56, 189, 248, 0.9)'
      : '1px solid rgba(148, 163, 184, 0.24)',
    borderRadius: 10,
    background: selected ? 'rgba(14, 116, 144, 0.28)' : 'rgba(15, 23, 42, 0.64)',
    color: '#e5eefb',
    cursor: 'pointer',
    padding: 12,
    textAlign: 'left',
  };
}

export default function ScenarioPicker({
  scenarios = ALPHA_SCENARIOS,
  selectedId,
  onSelect,
}: ScenarioPickerProps) {
  const [drive, setDrive] = useState<CasDrive | 'all'>('all');
  const [difficulty, setDifficulty] = useState<ScenarioDifficulty | 'all'>('all');
  const [demoSafe, setDemoSafe] = useState<'all' | 'safe_only'>('safe_only');

  const filtered = useMemo(
    () =>
      filterAlphaScenarios(scenarios, {
        drive,
        difficulty,
        demoSafe: demoSafe === 'safe_only' ? true : 'all',
      }),
    [demoSafe, difficulty, drive, scenarios],
  );

  return (
    <section aria-label="Atlas alpha scenarios" data-testid="scenario-picker" style={panelStyle}>
      <div style={controlsStyle}>
        <label style={labelStyle}>
          Drive
          <select
            aria-label="Filter scenarios by drive"
            data-testid="scenario-filter-drive"
            onChange={(event) => setDrive(event.target.value as CasDrive | 'all')}
            style={selectStyle}
            value={drive}
          >
            <option value="all">All drives</option>
            {CAS_DRIVE_VALUES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label style={labelStyle}>
          Difficulty
          <select
            aria-label="Filter scenarios by difficulty"
            data-testid="scenario-filter-difficulty"
            onChange={(event) => setDifficulty(event.target.value as ScenarioDifficulty | 'all')}
            style={selectStyle}
            value={difficulty}
          >
            <option value="all">All levels</option>
            {SCENARIO_DIFFICULTIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label style={labelStyle}>
          Safety
          <select
            aria-label="Filter scenarios by demo safety"
            data-testid="scenario-filter-demo-safe"
            onChange={(event) => setDemoSafe(event.target.value as 'all' | 'safe_only')}
            style={selectStyle}
            value={demoSafe}
          >
            <option value="safe_only">Demo-safe only</option>
            <option value="all">All scenarios</option>
          </select>
        </label>
      </div>

      <div aria-live="polite" data-testid="scenario-count">
        {filtered.length} scenarios
      </div>

      <div style={listStyle}>
        {filtered.map((scenario) => (
          <button
            data-testid={`scenario-option-${scenario.id}`}
            key={scenario.id}
            onClick={() => onSelect?.(scenario)}
            style={scenarioCardStyle(scenario.id === selectedId)}
            type="button"
          >
            <strong>
              {scenario.id} · {scenario.expectedCasAxes.drive} · {scenario.difficulty}
            </strong>
            <p>{scenario.prompt}</p>
            <small>{scenario.purpose}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
