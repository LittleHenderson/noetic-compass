/**
 * Tests for AtlasViewerShell — composes ControlBar, NeuralNetScene,
 * Mode7Timeline, MethodKnobsPanel, SpatialEvidencePanel, VisualPrimitiveCanvas
 * and EvidenceDrawer into the v0.0 cockpit. jsdom has no WebGL, so the real
 * NeuralNetScene is replaced here with a deterministic stub that exposes the
 * same prop contract plus a click hook for evidence-drawer wiring tests.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, act } from '@testing-library/react';
import type { ComponentProps } from 'react';
import type { ReplayTrace } from '../../lib/replayController';
import type { SpatialEvidenceArtifact } from '../../lib/visualPrimitives';
import { PYTHIA_160M_PRESET } from '../../lib/modelArchitecture';

vi.mock('./NeuralNetScene', () => {
  return {
    NeuralNetScene: (props: {
      onNeuronClick?: (c: { layer: number; index: number; label: string }) => void;
      focusedBlindspotCoords?: Array<{ layer: number; index: number; label: string }>;
      focusedBlindspotLabel?: string;
    }) => (
      <div
        data-testid="neuralnet-scene-stub"
        data-focused-cover={props.focusedBlindspotLabel ?? ''}
        data-focused-count={props.focusedBlindspotCoords?.length ?? 0}
      >
        <button
          type="button"
          data-testid="neuralnet-fake-neuron"
          onClick={() =>
            props.onNeuronClick?.({ layer: 3, index: 142, label: 'L3N142' })
          }
        >
          fake neuron
        </button>
      </div>
    ),
  };
});

import AtlasViewerShell from './AtlasViewerShell';

beforeEach(() => {
  if (!('ResizeObserver' in globalThis)) {
    (globalThis as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver =
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      } as unknown as typeof ResizeObserver;
  }
});

const baseTrace: ReplayTrace = {
  tokens: [
    { token_index: 0, token: 'The' },
    { token_index: 1, token: ' patient' },
    { token_index: 2, token: ' nurse' },
    { token_index: 3, token: ' triaged' },
    { token_index: 4, token: ' the' },
    { token_index: 5, token: ' wound' },
    { token_index: 6, token: '.' },
    { token_index: 7, token: ' She' },
    { token_index: 8, token: ' moved' },
    { token_index: 9, token: ' calmly' },
  ],
  per_token_frames: [
    {
      token_index: 0,
      token: 'The',
      top_activated_neurons: [],
      mode7_attribution: [{ from_token_index: null, to_token_index: 0, weight: 1 }],
    },
    {
      token_index: 1,
      token: ' patient',
      top_activated_neurons: [],
      mode7_attribution: [{ from_token_index: 0, to_token_index: 1, weight: 0.7 }],
    },
    { token_index: 2, token: ' nurse', top_activated_neurons: [] },
    { token_index: 3, token: ' triaged', top_activated_neurons: [] },
    { token_index: 4, token: ' the', top_activated_neurons: [] },
    { token_index: 5, token: ' wound', top_activated_neurons: [] },
    { token_index: 6, token: '.', top_activated_neurons: [] },
    { token_index: 7, token: ' She', top_activated_neurons: [] },
    { token_index: 8, token: ' moved', top_activated_neurons: [] },
    { token_index: 9, token: ' calmly', top_activated_neurons: [] },
  ],
};

const baseSpatial: SpatialEvidenceArtifact = {
  schema_version: 'spatial_evidence_v1',
  trace_id: 'test-trace',
  image_id: 'test-image',
  scenario_title: 'Base scene',
  scenario_sentence: 'The patient nurse trace is shown as a visual grounding fixture.',
  image_url: 'about:blank',
  image_width: 200,
  image_height: 100,
  primitives: [
    {
      id: 'p-a',
      kind: 'point',
      image_id: 'test-image',
      label: 'Primitive A',
      coords_norm: [0.25, 0.5],
      source: 'fixture',
      cas_axis: 'Noetic',
      cas_label: '^9^E|E',
      evidence_ref: { packet_id: 'pk-a', row_id: 'row-a' },
    },
    {
      id: 'p-b',
      kind: 'point',
      image_id: 'test-image',
      label: 'Primitive B',
      coords_norm: [0.75, 0.5],
      source: 'fixture',
      cas_axis: 'Drive',
      cas_label: 'F3|E',
      evidence_ref: { packet_id: 'pk-b', row_id: 'row-b' },
    },
  ],
  grounded_steps: [
    {
      trace_id: 'test-trace',
      step_id: 'step-a',
      token_index: 1,
      primitive_ids: ['p-a'],
    },
    {
      trace_id: 'test-trace',
      step_id: 'step-b',
      token_index: 5,
      primitive_ids: ['p-b'],
    },
  ],
};

const altSpatial: SpatialEvidenceArtifact = {
  ...baseSpatial,
  trace_id: 'alt-trace',
  image_id: 'alt-image',
  scenario_title: 'Second scene',
  scenario_sentence: 'A second fixture sentence controls the picture and primitive set.',
  primitives: [
    {
      id: 'p-c',
      kind: 'box',
      image_id: 'alt-image',
      label: 'Primitive C',
      coords_norm: [0.1, 0.1, 0.2, 0.2],
      source: 'fixture',
      cas_axis: 'Drive',
      cas_label: 'F5|E',
      evidence_ref: { packet_id: 'pk-c', row_id: 'row-c' },
    },
  ],
  grounded_steps: [
    {
      trace_id: 'alt-trace',
      step_id: 'step-c',
      token_index: 1,
      primitive_ids: ['p-c'],
    },
  ],
};

function renderShell(props?: Partial<ComponentProps<typeof AtlasViewerShell>>) {
  return render(
    <AtlasViewerShell
      trace={baseTrace}
      spatialEvidence={baseSpatial}
      architecture={PYTHIA_160M_PRESET}
      {...props}
    />,
  );
}

describe('AtlasViewerShell — composition', () => {
  it('renders all five cockpit zones', () => {
    renderShell();
    expect(screen.getByTestId('control-bar')).toBeInTheDocument();
    expect(screen.getByTestId('neuralnet-scene-stub')).toBeInTheDocument();
    expect(screen.getByTestId('mode7-timeline')).toBeInTheDocument();
    expect(screen.getByTestId('method-knobs-panel')).toBeInTheDocument();
    expect(screen.getByTestId('spatial-evidence-panel')).toBeInTheDocument();
  });

  it('shows the Spatial Evidence tab by default', () => {
    renderShell();
    expect(screen.getByTestId('left-tab-spatial')).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(screen.queryByTestId('notation-placeholder')).toBeNull();
  });

  it('switches to the 2D Notation placeholder when its tab is clicked', () => {
    renderShell();
    fireEvent.click(screen.getByTestId('left-tab-notation'));
    expect(screen.getByTestId('notation-placeholder')).toBeInTheDocument();
  });
});

describe('AtlasViewerShell — playback wiring', () => {
  it('toggles playback when the play button is clicked', () => {
    renderShell();
    const play = screen.getByTestId('play-toggle');
    expect(play).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(play);
    expect(play).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(play);
    expect(play).toHaveAttribute('aria-pressed', 'false');
  });

  it('seeks the controller when the token scrubber moves', () => {
    renderShell();
    const scrubber = screen.getByTestId('token-scrubber') as HTMLInputElement;
    fireEvent.change(scrubber, { target: { value: '4' } });
    const label = screen.getByTestId('token-label');
    // Wave 5.2: shortened token label from "token 5 of 10" to "5 / 10"
    // so the control bar fits on a single row in the tighter restyle.
    expect(label.textContent).toContain('5 / 10');
  });
});

describe('AtlasViewerShell — method knobs wiring', () => {
  it('removes a method from the enabled set when toggled off', () => {
    renderShell();
    const toggle = screen.getByTestId(
      'method-toggle-foundation_probe',
    ) as HTMLInputElement;
    expect(toggle.checked).toBe(true);
    fireEvent.click(toggle);
    expect(toggle.checked).toBe(false);
    fireEvent.click(toggle);
    expect(toggle.checked).toBe(true);
  });

  it('passes current side-panel controls when LIVE is clicked', () => {
    const onStartLive = vi.fn();
    renderShell({ onStartLive });
    fireEvent.change(screen.getByTestId('knob-rpm_gate_check-strictness_threshold'), {
      target: { value: '0.4' },
    });
    fireEvent.click(screen.getByTestId('runtime-live'));
    expect(onStartLive).toHaveBeenCalledTimes(1);
    expect(onStartLive.mock.calls[0][0]).toMatchObject({
      enabledMethodIds: expect.arrayContaining(['rpm_gate_check']),
      knobValues: { rpm_gate_check: { strictness_threshold: 0.4 } },
      verificationMode: 'BALANCED',
    });
  });

  it('does not report a live controls change when only the callback prop changes', () => {
    const firstCallback = vi.fn();
    const secondCallback = vi.fn();
    const { rerender } = renderShell({
      runtimeMode: 'live',
      liveStatus: 'connecting',
      onLiveControlsChange: firstCallback,
    });

    expect(firstCallback).toHaveBeenCalledTimes(1);

    rerender(
      <AtlasViewerShell
        trace={baseTrace}
        spatialEvidence={baseSpatial}
        architecture={PYTHIA_160M_PRESET}
        runtimeMode="live"
        liveStatus="streaming"
        onLiveControlsChange={secondCallback}
      />,
    );

    expect(secondCallback).not.toHaveBeenCalled();
  });
});

describe('AtlasViewerShell — LIVE provenance badge', () => {
  it('does not claim actual weights when the LIVE manifest proof is absent', () => {
    renderShell({ runtimeMode: 'live', liveStatus: 'complete' });
    const strip = screen.getByTestId('narration-strip');
    expect(strip.textContent).toContain('Live · complete');
    expect(strip.textContent).toContain('weight proof pending');
    expect(strip.textContent).not.toContain('actual weights verified');
  });

  it('claims actual weights only after an explicit real-model proof', () => {
    renderShell({
      runtimeMode: 'live',
      liveStatus: 'complete',
      liveVerified: true,
    });
    expect(screen.getByTestId('narration-strip').textContent).toContain(
      'actual weights verified',
    );
  });

  it('shows the backend realmode proof as the user-visible connection truth', () => {
    renderShell({
      liveProof: {
        verdict: 'NOT_REAL_PYTHIA_WEIGHTS',
        is_real_model: false,
        model_loaded: false,
        load_error: 'atlas_live_worker_unavailable',
        http_status: 503,
        checked_at: '2026-05-25T06:30:00.000Z',
      },
    });
    expect(screen.getByTestId('live-proof-badge').textContent).toContain(
      'Model connection: not connected',
    );
    expect(screen.getByTestId('live-proof-reason').textContent).toContain(
      'atlas_live_worker_unavailable',
    );
  });

  it('lets the user manually refresh the realmode proof', () => {
    const onRefreshLiveProof = vi.fn();
    renderShell({ onRefreshLiveProof });
    fireEvent.click(screen.getByTestId('live-proof-refresh'));
    expect(onRefreshLiveProof).toHaveBeenCalledTimes(1);
  });
});

describe('AtlasViewerShell — evidence drawer', () => {
  it('opens the evidence drawer when a neuron is clicked', () => {
    renderShell();
    const drawer = screen.getByTestId('evidence-drawer');
    expect(drawer.getAttribute('data-open')).toBe('false');
    fireEvent.click(screen.getByTestId('neuralnet-fake-neuron'));
    expect(screen.getByTestId('evidence-drawer').getAttribute('data-open')).toBe(
      'true',
    );
    expect(screen.getByTestId('evidence-drawer-ref-json').textContent).toContain(
      'L3N142',
    );
  });

  it('closes the drawer when Escape is pressed', () => {
    renderShell();
    fireEvent.click(screen.getByTestId('neuralnet-fake-neuron'));
    expect(screen.getByTestId('evidence-drawer').getAttribute('data-open')).toBe(
      'true',
    );
    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(screen.getByTestId('evidence-drawer').getAttribute('data-open')).toBe(
      'false',
    );
  });

  it('closes the drawer when the backdrop is clicked', () => {
    renderShell();
    fireEvent.click(screen.getByTestId('neuralnet-fake-neuron'));
    const backdrop = screen.getByTestId('evidence-drawer-backdrop');
    fireEvent.click(backdrop);
    expect(screen.getByTestId('evidence-drawer').getAttribute('data-open')).toBe(
      'false',
    );
  });
});

describe('AtlasViewerShell — clickable word spans', () => {
  const wordTrace: ReplayTrace = {
    ...baseTrace,
    word_spans: {
      total_tokens_covered: 10,
      structural_token_indices: [],
      spans: [
        { word: 'The', token_indices: [0], char_start: 0, char_end: 3 },
        { word: 'patient', token_indices: [1], char_start: 4, char_end: 11 },
        { word: 'nurse', token_indices: [2], char_start: 12, char_end: 17 },
        { word: 'triaged', token_indices: [3], char_start: 18, char_end: 25 },
        { word: 'the', token_indices: [4], char_start: 26, char_end: 29 },
        { word: 'wound.', token_indices: [5, 6], char_start: 30, char_end: 36 },
        { word: 'She', token_indices: [7], char_start: 37, char_end: 40 },
        { word: 'moved', token_indices: [8], char_start: 41, char_end: 46 },
        { word: 'calmly', token_indices: [9], char_start: 47, char_end: 53 },
      ],
    },
  };

  it('renders the streamed continuation as clickable word spans', () => {
    renderShell({ trace: wordTrace });
    expect(screen.getByTestId('word-token-stream')).toBeInTheDocument();
    const patient = screen.getByTestId('word-stream-word-4');
    expect(patient).toHaveAttribute('data-word', 'patient');
  });

  it('opens the Evidence Drawer with the word-scoped payload on click', () => {
    renderShell({ trace: wordTrace });
    const drawer = screen.getByTestId('evidence-drawer');
    expect(drawer.getAttribute('data-open')).toBe('false');

    fireEvent.click(screen.getByTestId('word-stream-word-30'));

    expect(screen.getByTestId('evidence-drawer').getAttribute('data-open')).toBe(
      'true',
    );
    // Header carries the word in quotes and the token range.
    expect(screen.getAllByText(/wound\./)[0]).toBeInTheDocument();
    // Multi-token span shows both rows.
    expect(
      screen.getByTestId('evidence-drawer-word-token-row-5'),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('evidence-drawer-word-token-row-6'),
    ).toBeInTheDocument();
  });

  it('seeks playback to the first token in the clicked word', () => {
    renderShell({ trace: wordTrace });
    fireEvent.click(screen.getByTestId('word-stream-word-30'));
    const label = screen.getByTestId('token-label');
    // Span "wound." starts at token 5 → label "6 / 10" (1-indexed display).
    expect(label.textContent).toContain('6 / 10');
  });

  it('shows the placeholder when no word_spans event has arrived yet', () => {
    renderShell();
    expect(screen.getByTestId('word-token-stream-placeholder')).toBeInTheDocument();
  });
});

describe('AtlasViewerShell — grounded step derivation', () => {
  it('shows no active primitives before the first grounded step', () => {
    renderShell();
    expect(screen.getByTestId('spatial-evidence-empty')).toBeInTheDocument();
  });

  it('surfaces step-a primitives once the scrubber reaches token 1', () => {
    renderShell();
    const scrubber = screen.getByTestId('token-scrubber') as HTMLInputElement;
    fireEvent.change(scrubber, { target: { value: '1' } });
    expect(screen.getByTestId('spatial-evidence-card-p-a')).toBeInTheDocument();
    expect(screen.queryByTestId('spatial-evidence-card-p-b')).toBeNull();
  });

  it('switches to step-b primitives once the scrubber reaches token 5', () => {
    renderShell();
    const scrubber = screen.getByTestId('token-scrubber') as HTMLInputElement;
    fireEvent.change(scrubber, { target: { value: '5' } });
    expect(screen.getByTestId('spatial-evidence-card-p-b')).toBeInTheDocument();
    expect(screen.queryByTestId('spatial-evidence-card-p-a')).toBeNull();
  });

  it('switches between multiple picture-and-sentence spatial fixtures', () => {
    renderShell({ spatialEvidenceOptions: [baseSpatial, altSpatial] });
    expect(screen.getByTestId('spatial-scenario-selector')).toBeInTheDocument();
    expect(screen.getByText('Base scene')).toBeInTheDocument();
    expect(screen.getByText('Second scene')).toBeInTheDocument();
    expect(screen.getByTestId('spatial-scenario-active-sentence').textContent).toBe(
      'The patient nurse trace is shown as a visual grounding fixture.',
    );
    expect(screen.getByTestId('word-token-stream-placeholder').textContent).toBe(
      'The patient nurse trace is shown as a visual grounding fixture.',
    );
    expect(screen.getByTestId('mode7-timeline-cell-0').textContent).toContain(
      'The',
    );
    expect(screen.getByTestId('mode7-timeline-cell-1').textContent).toContain(
      'patient',
    );

    fireEvent.click(screen.getByTestId('spatial-scenario-alt-trace'));
    const scrubber = screen.getByTestId('token-scrubber') as HTMLInputElement;
    fireEvent.change(scrubber, { target: { value: '1' } });
    expect(screen.getByTestId('spatial-scenario-active-sentence').textContent).toBe(
      'A second fixture sentence controls the picture and primitive set.',
    );
    expect(screen.getByTestId('word-token-stream-placeholder').textContent).toBe(
      'A second fixture sentence controls the picture and primitive set.',
    );
    expect(screen.getByTestId('mode7-timeline-cell-0').textContent).toContain(
      'A',
    );
    expect(screen.getByTestId('mode7-timeline-cell-1').textContent).toContain(
      'second',
    );
    expect(screen.getByTestId('mode7-timeline-edge-0-1')).toBeInTheDocument();
    expect(screen.getByTestId('spatial-evidence-card-p-c')).toBeInTheDocument();
    expect(screen.queryByTestId('spatial-evidence-card-p-a')).toBeNull();
  });
});

describe('AtlasViewerShell — blindspot cover focusing', () => {
  it('routes a blindspot row click into focused 3D neuron coordinates', () => {
    const traceWithCovers = {
      ...baseTrace,
      neuron_covers: {
        per_class_neuron_covers: {
          F1A: [
            { label: 'L3N142', confidence: 0.84, confidence_band: 'high', evidence_sources: ['probe'] },
            { label: 'L3N518', confidence: 0.82, confidence_band: 'high', evidence_sources: ['probe'] },
          ],
        },
      },
    } as unknown as ReplayTrace;

    renderShell({ trace: traceWithCovers });
    fireEvent.click(screen.getByTestId('blindspot-focus-cover'));
    const scene = screen.getByTestId('neuralnet-scene-stub');
    expect(scene.getAttribute('data-focused-cover')).toBe('F1A');
    expect(scene.getAttribute('data-focused-count')).toBe('2');
  });
});
