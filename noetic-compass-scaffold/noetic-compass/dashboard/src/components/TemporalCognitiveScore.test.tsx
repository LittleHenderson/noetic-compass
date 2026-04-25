import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as Tone from 'tone';
import { TemporalCognitiveScore } from './TemporalCognitiveScore';
import type { CognitiveStateData, Domain, Drive, Noetic, Register } from '../lib/mandala_types';

const toneMocks = vi.hoisted(() => {
  const triggerAttackRelease = vi.fn();
  const dispose = vi.fn();
  const start = vi.fn(() => Promise.resolve());
  const transportStart = vi.fn();
  const transportPause = vi.fn();
  const transportStop = vi.fn();
  const transportCancel = vi.fn();
  const destination = { volume: { value: 0 } };
  const getDestination = vi.fn(() => destination);
  const makeNode = vi.fn(() => ({
    toDestination: vi.fn(() => ({
      triggerAttackRelease,
      dispose,
    })),
  }));
  const Synth = vi.fn(function SynthMock() {
    return makeNode();
  });
  const MonoSynth = vi.fn(function MonoSynthMock() {
    return makeNode();
  });
  const FMSynth = vi.fn(function FMSynthMock() {
    return makeNode();
  });
  const MembraneSynth = vi.fn(function MembraneSynthMock() {
    return makeNode();
  });

  return {
    triggerAttackRelease,
    dispose,
    start,
    transportStart,
    transportPause,
    transportStop,
    transportCancel,
    destination,
    getDestination,
    makeNode,
    Synth,
    MonoSynth,
    FMSynth,
    MembraneSynth,
  };
});

vi.mock('tone', () => ({
  start: toneMocks.start,
  getDestination: toneMocks.getDestination,
  Transport: {
    start: toneMocks.transportStart,
    pause: toneMocks.transportPause,
    stop: toneMocks.transportStop,
    cancel: toneMocks.transportCancel,
    bpm: { value: 0 },
  },
  Synth: toneMocks.Synth,
  MonoSynth: toneMocks.MonoSynth,
  FMSynth: toneMocks.FMSynth,
  MembraneSynth: toneMocks.MembraneSynth,
}));

function emptyState(label = 'test'): CognitiveStateData {
  return {
    label,
    activations: {},
    drives: {},
    lacunarity: {
      register_global_voids: [],
      register_pair_voids: [],
      register_selective_voids: {},
      register_involution_imbalance: [],
    },
  };
}

function stateWithActivation(
  noetic: Noetic = 'N0',
  domain: Domain = 'P',
  register: Register = 'A',
  drive: Drive = 'F2',
): CognitiveStateData {
  return {
    ...emptyState('playable'),
    activations: {
      [noetic]: {
        [domain]: {
          [register]: 0.85,
        },
      },
    },
    drives: {
      [drive]: 0.95,
    },
  };
}

describe('TemporalCognitiveScore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toneMocks.destination.volume.value = 0;
  });

  afterEach(() => {
    vi.useRealTimers();
    cleanup();
  });

  it('renders the public Phase B component name', () => {
    render(<TemporalCognitiveScore cognitiveState={stateWithActivation()} />);
    expect(screen.getByRole('heading', { name: 'Temporal Cognitive Score' })).toBeInTheDocument();
    expect(screen.getByText(/Phase B live/i)).toBeInTheDocument();
  });

  it('does not auto-play on render', () => {
    render(<TemporalCognitiveScore cognitiveState={stateWithActivation()} />);
    expect(Tone.start).not.toHaveBeenCalled();
    expect(toneMocks.transportStart).not.toHaveBeenCalled();
  });

  it('starts Tone only after Play is pressed', async () => {
    const onPlayStateChange = vi.fn();
    render(
      <TemporalCognitiveScore
        cognitiveState={stateWithActivation()}
        onPlayStateChange={onPlayStateChange}
      />,
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId('temporal-play'));
    });

    expect(Tone.start).toHaveBeenCalledTimes(1);
    expect(toneMocks.transportStart).toHaveBeenCalledTimes(1);
    expect(onPlayStateChange).toHaveBeenCalledWith('playing');
    expect(screen.getByTestId('temporal-score-status')).toHaveTextContent('playing');
  });

  it('disables Play when there are no active events', () => {
    render(<TemporalCognitiveScore cognitiveState={emptyState()} />);
    expect(screen.getByTestId('temporal-play')).toBeDisabled();
    expect(screen.getByTestId('temporal-caption')).toHaveTextContent('No active CAS events');
  });

  it('pauses active playback', async () => {
    const onPlayStateChange = vi.fn();
    render(
      <TemporalCognitiveScore
        cognitiveState={stateWithActivation()}
        onPlayStateChange={onPlayStateChange}
      />,
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId('temporal-play'));
    });
    fireEvent.click(screen.getByTestId('temporal-pause'));

    expect(toneMocks.transportPause).toHaveBeenCalledTimes(1);
    expect(onPlayStateChange).toHaveBeenCalledWith('paused');
    expect(screen.getByTestId('temporal-score-status')).toHaveTextContent('paused');
  });

  it('stops playback and resets the scrubber', async () => {
    render(<TemporalCognitiveScore cognitiveState={stateWithActivation()} />);

    await act(async () => {
      fireEvent.click(screen.getByTestId('temporal-play'));
    });
    fireEvent.change(screen.getByTestId('temporal-scrub'), { target: { value: '0.2' } });
    fireEvent.click(screen.getByTestId('temporal-stop'));

    expect(toneMocks.transportStop).toHaveBeenCalled();
    expect(toneMocks.transportCancel).toHaveBeenCalled();
    expect(screen.getByTestId('temporal-score-status')).toHaveTextContent('stopped');
    expect(screen.getByTestId('temporal-scrub')).toHaveValue('0');
  });

  it('updates the global Tone volume from the volume slider', () => {
    render(<TemporalCognitiveScore cognitiveState={stateWithActivation()} />);
    fireEvent.change(screen.getByTestId('temporal-volume'), { target: { value: '-24' } });
    expect(toneMocks.destination.volume.value).toBe(-24);
  });

  it('updates the score tempo through the override control', () => {
    render(<TemporalCognitiveScore cognitiveState={stateWithActivation('N0', 'P', 'A', 'F3')} />);
    expect(screen.getByText(/152 BPM/i)).toBeInTheDocument();
    fireEvent.change(screen.getByTestId('temporal-tempo'), { target: { value: '120' } });
    expect(screen.getAllByText(/120 BPM/i).length).toBeGreaterThan(0);
  });

  it('renders a visual transcript for accessible reading', () => {
    render(<TemporalCognitiveScore cognitiveState={stateWithActivation('N2', 'C', 'f')} />);
    expect(screen.getByTestId('temporal-transcript')).toHaveTextContent('E4');
    expect(screen.getByTestId('temporal-transcript')).toHaveTextContent('|f');
  });

  it('fires the current-domain sync callback during playback', async () => {
    vi.useFakeTimers();
    const onCurrentDomainChange = vi.fn();
    render(
      <TemporalCognitiveScore
        cognitiveState={stateWithActivation('N0', 'P', 'A')}
        onCurrentDomainChange={onCurrentDomainChange}
      />,
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId('temporal-play'));
    });
    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(onCurrentDomainChange).toHaveBeenCalledWith('P');
    expect(toneMocks.triggerAttackRelease).toHaveBeenCalled();
  });

  it('cleans up transport and synths on unmount', async () => {
    const { unmount } = render(<TemporalCognitiveScore cognitiveState={stateWithActivation()} />);

    await act(async () => {
      fireEvent.click(screen.getByTestId('temporal-play'));
    });
    unmount();

    expect(toneMocks.transportStop).toHaveBeenCalled();
    expect(toneMocks.transportCancel).toHaveBeenCalled();
    expect(toneMocks.dispose).toHaveBeenCalled();
  });

  it('uses scrub position to update the caption and active stave', () => {
    const state = stateWithActivation('N8', 'E', 'T');
    render(<TemporalCognitiveScore cognitiveState={state} />);

    fireEvent.change(screen.getByTestId('temporal-scrub'), { target: { value: '0.1' } });

    expect(screen.getByTestId('temporal-caption')).toHaveTextContent('Above/Cause');
    expect(screen.getByTestId('temporal-stave-E')).toHaveClass('temporal-score__stave--active');
  });
});
