import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import ControlBar from './ControlBar';
import type { ControlBarProps } from './ControlBar';

function makeProps(overrides: Partial<ControlBarProps> = {}): ControlBarProps {
  return {
    playbackMode: 'paused',
    speed: 1,
    zoomLevel: 0,
    currentTokenIndex: 3,
    tokenCount: 10,
    verificationMode: 'BALANCED',
    showBlindspots: false,
    showActiveTrace: false,
    onPlayToggle: vi.fn(),
    onSpeedChange: vi.fn(),
    onZoomLevelChange: vi.fn(),
    onTokenSeek: vi.fn(),
    onVerificationModeChange: vi.fn(),
    onToggleBlindspots: vi.fn(),
    onToggleActiveTrace: vi.fn(),
    ...overrides,
  };
}

describe('ControlBar', () => {
  it('renders toolbar with required ARIA label', () => {
    render(<ControlBar {...makeProps()} />);
    const toolbar = screen.getByRole('toolbar', {
      name: /atlas viewer playback and view controls/i,
    });
    expect(toolbar).toBeTruthy();
  });

  it('fires onPlayToggle when play button is clicked', () => {
    const onPlayToggle = vi.fn();
    render(<ControlBar {...makeProps({ onPlayToggle })} />);
    fireEvent.click(screen.getByTestId('play-toggle'));
    expect(onPlayToggle).toHaveBeenCalledTimes(1);
  });

  it('fires onSpeedChange with the chosen speed', () => {
    const onSpeedChange = vi.fn();
    render(<ControlBar {...makeProps({ onSpeedChange })} />);
    fireEvent.click(screen.getByTestId('speed-2'));
    expect(onSpeedChange).toHaveBeenCalledWith(2);
  });

  it('fires onTokenSeek when scrubber value changes', () => {
    const onTokenSeek = vi.fn();
    render(<ControlBar {...makeProps({ onTokenSeek })} />);
    const scrubber = screen.getByTestId('token-scrubber') as HTMLInputElement;
    fireEvent.change(scrubber, { target: { value: '7' } });
    expect(onTokenSeek).toHaveBeenCalledWith(7);
  });

  it('fires onZoomLevelChange(2) when Z2 is clicked', () => {
    const onZoomLevelChange = vi.fn();
    render(<ControlBar {...makeProps({ onZoomLevelChange })} />);
    fireEvent.click(screen.getByTestId('zoom-2'));
    expect(onZoomLevelChange).toHaveBeenCalledWith(2);
  });

  it('fires onToggleBlindspots when B button is clicked', () => {
    const onToggleBlindspots = vi.fn();
    render(<ControlBar {...makeProps({ onToggleBlindspots })} />);
    fireEvent.click(screen.getByTestId('toggle-blindspots'));
    expect(onToggleBlindspots).toHaveBeenCalledTimes(1);
  });

  it('fires onToggleActiveTrace when T button is clicked', () => {
    const onToggleActiveTrace = vi.fn();
    render(<ControlBar {...makeProps({ onToggleActiveTrace })} />);
    fireEvent.click(screen.getByTestId('toggle-activetrace'));
    expect(onToggleActiveTrace).toHaveBeenCalledTimes(1);
  });

  it('fires onVerificationModeChange when the select changes', () => {
    const onVerificationModeChange = vi.fn();
    render(<ControlBar {...makeProps({ onVerificationModeChange })} />);
    fireEvent.change(screen.getByTestId('verification-mode'), {
      target: { value: 'HIGH_PRECISION' },
    });
    expect(onVerificationModeChange).toHaveBeenCalledWith('HIGH_PRECISION');
  });

  it('Space key triggers onPlayToggle', () => {
    const onPlayToggle = vi.fn();
    render(<ControlBar {...makeProps({ onPlayToggle })} />);
    fireEvent.keyDown(screen.getByTestId('control-bar'), { key: ' ' });
    expect(onPlayToggle).toHaveBeenCalledTimes(1);
  });

  it("',' key decrements token (clamped >= 0)", () => {
    const onTokenSeek = vi.fn();
    render(
      <ControlBar
        {...makeProps({ currentTokenIndex: 4, tokenCount: 10, onTokenSeek })}
      />,
    );
    fireEvent.keyDown(screen.getByTestId('control-bar'), { key: ',' });
    expect(onTokenSeek).toHaveBeenCalledWith(3);

    onTokenSeek.mockClear();
    render(
      <ControlBar
        {...makeProps({ currentTokenIndex: 0, tokenCount: 10, onTokenSeek })}
      />,
    );
    fireEvent.keyDown(screen.getAllByTestId('control-bar')[1], { key: ',' });
    expect(onTokenSeek).toHaveBeenCalledWith(0);
  });

  it("'.' key increments token (clamped <= tokenCount-1)", () => {
    const onTokenSeek = vi.fn();
    render(
      <ControlBar
        {...makeProps({ currentTokenIndex: 4, tokenCount: 10, onTokenSeek })}
      />,
    );
    fireEvent.keyDown(screen.getByTestId('control-bar'), { key: '.' });
    expect(onTokenSeek).toHaveBeenCalledWith(5);

    onTokenSeek.mockClear();
    render(
      <ControlBar
        {...makeProps({ currentTokenIndex: 9, tokenCount: 10, onTokenSeek })}
      />,
    );
    fireEvent.keyDown(screen.getAllByTestId('control-bar')[1], { key: '.' });
    expect(onTokenSeek).toHaveBeenCalledWith(9);
  });

  it('[ and ] keys change zoom level (clamped 0..5)', () => {
    const onZoomLevelChange = vi.fn();
    render(
      <ControlBar
        {...makeProps({ zoomLevel: 3, onZoomLevelChange })}
      />,
    );
    fireEvent.keyDown(screen.getByTestId('control-bar'), { key: '[' });
    expect(onZoomLevelChange).toHaveBeenCalledWith(2);
    fireEvent.keyDown(screen.getByTestId('control-bar'), { key: ']' });
    expect(onZoomLevelChange).toHaveBeenCalledWith(4);
  });

  it('B and T keys fire toggle callbacks', () => {
    const onToggleBlindspots = vi.fn();
    const onToggleActiveTrace = vi.fn();
    render(
      <ControlBar
        {...makeProps({ onToggleBlindspots, onToggleActiveTrace })}
      />,
    );
    fireEvent.keyDown(screen.getByTestId('control-bar'), { key: 'b' });
    expect(onToggleBlindspots).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(screen.getByTestId('control-bar'), { key: 't' });
    expect(onToggleActiveTrace).toHaveBeenCalledTimes(1);
  });

  it('renders Export button only when onExportEvidence is provided', () => {
    const { rerender } = render(<ControlBar {...makeProps()} />);
    expect(screen.queryByTestId('export-evidence')).toBeNull();

    const onExportEvidence = vi.fn();
    rerender(<ControlBar {...makeProps({ onExportEvidence })} />);
    fireEvent.click(screen.getByTestId('export-evidence'));
    expect(onExportEvidence).toHaveBeenCalledTimes(1);
  });

  it('shows token label as 1-indexed of tokenCount', () => {
    render(
      <ControlBar
        {...makeProps({ currentTokenIndex: 4, tokenCount: 10 })}
      />,
    );
    // Wave 5.2: tightened to "5 / 10" so the control bar fits on one row.
    expect(screen.getByTestId('token-label').textContent).toBe(
      '5 / 10',
    );
  });
});
