import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import MethodKnobsPanel from './MethodKnobsPanel';
import type { KnobValue, ResolvedKnobs } from './MethodKnobsPanel';
import type { TestingMethod } from '../../lib/testingMethods';
import { buildLiveSessionRequest } from '../../lib/liveMethodControls';

const enumMethod: TestingMethod = {
  id: 'm_enum',
  name: 'Enum Method',
  description: 'desc enum',
  reveals: 'rev enum',
  stageAnchor: 'Stage 26 (probe)',
  knobs: [
    {
      id: 'axis',
      label: 'Axis',
      type: 'enum',
      default: 'Drive',
      options: ['Noetic', 'Domain', 'Drive', 'Register'] as const,
    },
  ],
  outputShape: 'out enum',
  costEstimateGpuMinutes: 5,
  prerequisites: ['pre1'],
  validatedArchs: ['Pythia-160M'],
  orderIndex: 1,
};

const numberMethod: TestingMethod = {
  id: 'm_num',
  name: 'Number Method',
  description: 'desc num',
  reveals: 'rev num',
  stageAnchor: 'Stage 27O/P',
  knobs: [
    {
      id: 'gain',
      label: 'Gain',
      type: 'number',
      default: 1.0,
    },
  ],
  outputShape: 'out num',
  costEstimateGpuMinutes: 10,
  prerequisites: [],
  validatedArchs: [],
  orderIndex: 2,
};

const boolMethod: TestingMethod = {
  id: 'm_bool',
  name: 'Bool Method',
  description: 'desc bool',
  reveals: 'rev bool',
  stageAnchor: 'Evidence',
  knobs: [
    {
      id: 'include_detail',
      label: 'Include detail',
      type: 'boolean',
      default: true,
    },
  ],
  outputShape: 'out bool',
  costEstimateGpuMinutes: 0,
  prerequisites: ['any'],
  validatedArchs: [],
  orderIndex: 3,
};

const multiMethod: TestingMethod = {
  id: 'm_multi',
  name: 'Multi Method',
  description: 'desc multi',
  reveals: 'rev multi',
  stageAnchor: 'Stage 27F',
  knobs: [
    {
      id: 'axes',
      label: 'Axes',
      type: 'multiselect',
      default: ['N'],
      options: ['N', 'W', 'F'] as const,
    },
  ],
  outputShape: 'out multi',
  costEstimateGpuMinutes: 3,
  prerequisites: [],
  validatedArchs: [],
  orderIndex: 4,
};

const allMethods: TestingMethod[] = [enumMethod, numberMethod, boolMethod, multiMethod];

function renderPanel(overrides?: {
  enabled?: Set<string>;
  values?: Record<string, Record<string, KnobValue>>;
  onToggle?: (id: string, enabled: boolean) => void;
  onKnob?: (id: string, knob: string, v: KnobValue) => void;
  methods?: TestingMethod[];
  resolvedKnobs?: ResolvedKnobs | null;
  showKnobDiagnostic?: boolean;
}) {
  const onToggle = overrides?.onToggle ?? vi.fn();
  const onKnob = overrides?.onKnob ?? vi.fn();
  render(
    <MethodKnobsPanel
      methods={overrides?.methods ?? allMethods}
      enabledMethodIds={
        overrides?.enabled ?? new Set(allMethods.map((m) => m.id))
      }
      knobValues={overrides?.values ?? {}}
      onToggleMethod={onToggle}
      onKnobChange={onKnob}
      resolvedKnobs={overrides?.resolvedKnobs}
      showKnobDiagnostic={overrides?.showKnobDiagnostic}
    />,
  );
  return { onToggle, onKnob };
}

describe('MethodKnobsPanel', () => {
  it('renders one card per method', () => {
    renderPanel();
    expect(screen.getByTestId('method-card-m_enum')).toBeInTheDocument();
    expect(screen.getByTestId('method-card-m_num')).toBeInTheDocument();
    expect(screen.getByTestId('method-card-m_bool')).toBeInTheDocument();
    expect(screen.getByTestId('method-card-m_multi')).toBeInTheDocument();
  });

  it('renders cards ordered by orderIndex', () => {
    const shuffled = [boolMethod, enumMethod, multiMethod, numberMethod];
    renderPanel({ methods: shuffled });
    const cards = screen.getAllByRole('group');
    const ids = cards
      .map((c) => c.getAttribute('data-testid'))
      .filter((t): t is string => !!t && t.startsWith('method-card-'));
    expect(ids).toEqual([
      'method-card-m_enum',
      'method-card-m_num',
      'method-card-m_bool',
      'method-card-m_multi',
    ]);
  });

  it('shows "Free" cost badge when costEstimateGpuMinutes is 0', () => {
    renderPanel();
    expect(screen.getByTestId('method-cost-m_bool')).toHaveTextContent('Free');
    expect(screen.getByTestId('method-cost-m_enum')).toHaveTextContent(
      '5 GPU-min',
    );
  });

  it('toggle fires onToggleMethod with correct id and new state', () => {
    const onToggle = vi.fn();
    renderPanel({
      enabled: new Set(['m_enum', 'm_num', 'm_bool', 'm_multi']),
      onToggle,
    });
    fireEvent.click(screen.getByTestId('method-toggle-m_enum'));
    expect(onToggle).toHaveBeenCalledWith('m_enum', false);
  });

  it('toggle on a disabled method re-enables it', () => {
    const onToggle = vi.fn();
    renderPanel({
      enabled: new Set(['m_num', 'm_bool', 'm_multi']),
      onToggle,
    });
    fireEvent.click(screen.getByTestId('method-toggle-m_enum'));
    expect(onToggle).toHaveBeenCalledWith('m_enum', true);
  });

  it('enum select change triggers onKnobChange with new string value', () => {
    const onKnob = vi.fn();
    renderPanel({ onKnob });
    const select = screen.getByTestId('knob-m_enum-axis') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: 'Noetic' } });
    expect(onKnob).toHaveBeenCalledWith('m_enum', 'axis', 'Noetic');
  });

  it('number input change triggers onKnobChange with parsed number', () => {
    const onKnob = vi.fn();
    renderPanel({ onKnob });
    const input = screen.getByTestId('knob-m_num-gain') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '2.5' } });
    expect(onKnob).toHaveBeenCalledWith('m_num', 'gain', 2.5);
  });

  it('boolean checkbox triggers onKnobChange with boolean', () => {
    const onKnob = vi.fn();
    renderPanel({
      values: { m_bool: { include_detail: true } },
      onKnob,
    });
    const cb = screen.getByTestId(
      'knob-m_bool-include_detail',
    ) as HTMLInputElement;
    expect(cb.checked).toBe(true);
    fireEvent.click(cb);
    expect(onKnob).toHaveBeenCalledWith('m_bool', 'include_detail', false);
  });

  it('multiselect adds an option when checked', () => {
    const onKnob = vi.fn();
    renderPanel({
      values: { m_multi: { axes: ['N'] } },
      onKnob,
    });
    fireEvent.click(screen.getByTestId('knob-m_multi-axes-W'));
    expect(onKnob).toHaveBeenCalledWith('m_multi', 'axes', ['N', 'W']);
  });

  it('multiselect removes an option when unchecked', () => {
    const onKnob = vi.fn();
    renderPanel({
      values: { m_multi: { axes: ['N', 'W'] } },
      onKnob,
    });
    fireEvent.click(screen.getByTestId('knob-m_multi-axes-N'));
    expect(onKnob).toHaveBeenCalledWith('m_multi', 'axes', ['W']);
  });

  it('disabled method renders with disabled visual state (status badge + disabled controls)', () => {
    renderPanel({ enabled: new Set(['m_num', 'm_bool', 'm_multi']) });
    expect(screen.getByTestId('method-status-m_enum')).toHaveTextContent(
      'off',
    );
    const select = screen.getByTestId('knob-m_enum-axis') as HTMLSelectElement;
    expect(select.disabled).toBe(true);
  });

  it('enabled method shows "sent live" status badge', () => {
    renderPanel();
    expect(screen.getByTestId('method-status-m_enum')).toHaveTextContent(
      'sent live',
    );
  });

  it('collapse chevron hides body knobs section', () => {
    renderPanel();
    expect(screen.getByTestId('method-knobs-m_enum')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('method-expand-m_enum'));
    expect(screen.queryByTestId('method-knobs-m_enum')).toBeNull();
  });

  it('card uses aria-labelledby pointing at the method name element', () => {
    renderPanel();
    const card = screen.getByTestId('method-card-m_enum');
    const labelId = card.getAttribute('aria-labelledby');
    expect(labelId).toBe('method-m_enum-name');
    expect(document.getElementById(labelId!)).toHaveTextContent('Enum Method');
  });

  describe('Knob diagnostic disclosure', () => {
    it('is hidden by default (production builds get no diagnostic)', () => {
      renderPanel({ showKnobDiagnostic: false });
      expect(
        screen.queryByTestId('knob-diagnostic-panel'),
      ).not.toBeInTheDocument();
    });

    it('renders when the feature flag is set', () => {
      renderPanel({ showKnobDiagnostic: true });
      expect(
        screen.getByTestId('knob-diagnostic-panel'),
      ).toBeInTheDocument();
    });

    it('shows "awaiting worker echo" placeholder before any resolution lands', () => {
      renderPanel({ showKnobDiagnostic: true });
      fireEvent.click(screen.getByTestId('knob-diagnostic-toggle'));
      expect(
        screen.getByTestId('knob-diagnostic-empty'),
      ).toBeInTheDocument();
    });

    it('paints ✓ when sent matches resolved (loose number-string equality)', () => {
      renderPanel({
        showKnobDiagnostic: true,
        values: { m_enum: { axis: 'Drive' }, m_num: { gain: 1.5 } },
        resolvedKnobs: {
          m_enum: { axis: 'Drive' },
          m_num: { gain: 1.5 },
        },
      });
      fireEvent.click(screen.getByTestId('knob-diagnostic-toggle'));
      expect(
        screen.getByTestId('knob-diagnostic-m_enum-axis'),
      ).toHaveAttribute('data-knob-match', 'true');
      expect(
        screen.getByTestId('knob-diagnostic-m_num-gain'),
      ).toHaveAttribute('data-knob-match', 'true');
    });

    it('paints ✗ when sent differs from resolved', () => {
      renderPanel({
        showKnobDiagnostic: true,
        values: { m_num: { gain: 2.5 } },
        resolvedKnobs: { m_num: { gain: 1.0 } },
      });
      fireEvent.click(screen.getByTestId('knob-diagnostic-toggle'));
      expect(
        screen.getByTestId('knob-diagnostic-m_num-gain'),
      ).toHaveAttribute('data-knob-match', 'false');
    });

    it('tolerates resolved-only entries (worker diagnostic bits like cover_available)', () => {
      renderPanel({
        showKnobDiagnostic: true,
        values: {},
        resolvedKnobs: {
          m_num: { gain: 1.0, cover_available: false },
        },
      });
      fireEvent.click(screen.getByTestId('knob-diagnostic-toggle'));
      const coverRow = screen.getByTestId(
        'knob-diagnostic-m_num-cover_available',
      );
      // Resolved-only row carries no Sent value -> match = na.
      expect(coverRow).toHaveAttribute('data-knob-match', 'na');
    });
  });

  describe('Outgoing method_config payload', () => {
    // The diagnostic is window dressing without the round-trip. These
    // tests pin the build-step that produces the request body the
    // worker actually receives, so a refactor that drops a knob from
    // the payload trips here.
    it('serialises sent knob values into method_config.knobs', () => {
      const req = buildLiveSessionRequest({
        enabledMethodIds: ['foundation_probe', 'rpm_gate_check'],
        knobValues: {
          foundation_probe: { top_k: 4, layer_range: ['0', '1', '2', '3'] },
          rpm_gate_check: { strictness_threshold: 0.9 },
        },
        verificationMode: 'BALANCED',
        showBlindspots: true,
        showActiveTrace: true,
      });
      expect(req.method_config?.enabled_methods).toEqual([
        'foundation_probe',
        'rpm_gate_check',
      ]);
      expect(req.method_config?.knobs).toEqual({
        foundation_probe: { top_k: 4, layer_range: ['0', '1', '2', '3'] },
        rpm_gate_check: { strictness_threshold: 0.9 },
      });
    });

    it('different top_k values yield different request payloads', () => {
      const low = buildLiveSessionRequest({
        enabledMethodIds: ['foundation_probe'],
        knobValues: { foundation_probe: { top_k: 4 } },
        verificationMode: 'BALANCED',
        showBlindspots: true,
        showActiveTrace: true,
      });
      const high = buildLiveSessionRequest({
        enabledMethodIds: ['foundation_probe'],
        knobValues: { foundation_probe: { top_k: 8 } },
        verificationMode: 'BALANCED',
        showBlindspots: true,
        showActiveTrace: true,
      });
      expect(low.method_config?.knobs).not.toEqual(high.method_config?.knobs);
    });
  });
});
