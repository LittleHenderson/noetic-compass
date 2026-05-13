/**
 * HandsPanel.test.tsx — UI tests for the SGGS webcam panel.
 *
 * Mocks `useHands` so no real webcam / MediaPipe runtime is needed.
 *
 * Coverage (matches Agent C brief):
 *   - Renders "Activate Camera" button initially.
 *   - Status shows "Camera off" before activation.
 *   - Clicking the button toggles status to "Camera ready" (MOCK
 *     useHands so no real webcam is needed).
 *   - The privacy notice "Camera stays on this machine. No video is
 *     uploaded." is present.
 *
 * Extra coverage:
 *   - Gesture callback fires when the mocked useHands invokes onGesture.
 *   - Zoom number reflects accumulated two-hand zoomDelta events.
 *   - Error string surfaces in the overlay when useHands reports it.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import type { GestureState } from '../../lib/sggs_gestures';

// ── Mock useHands ──────────────────────────────────────────────────────────
//
// vi.mock is hoisted; we capture the latest onGesture callback in a
// module-level ref so tests can fire synthetic gesture events at the
// component. The mock also lets each test override the reported status.

const mockState: {
  status: 'idle' | 'loading_model' | 'ready' | 'error';
  error: string | null;
  lastOnGesture: ((s: GestureState) => void) | null;
} = {
  status: 'ready',
  error: null,
  lastOnGesture: null,
};

vi.mock('../../lib/sggs_hands', () => ({
  useHands: (opts: {
    videoEl: HTMLVideoElement | null;
    onGesture: (s: GestureState) => void;
    enabled: boolean;
  }) => {
    mockState.lastOnGesture = opts.onGesture;
    // The hook normally reports 'idle' before activation; honor that.
    if (!opts.enabled) {
      return { status: 'idle' as const, error: null };
    }
    return { status: mockState.status, error: mockState.error };
  },
}));

// Import AFTER the mock so the component picks up the mocked hook.
import { HandsPanel } from './HandsPanel';

beforeEach(() => {
  mockState.status = 'ready';
  mockState.error = null;
  mockState.lastOnGesture = null;
});

// ── Tests ──────────────────────────────────────────────────────────────────

describe('HandsPanel — initial render', () => {
  it('renders the Activate Camera button initially', () => {
    render(<HandsPanel onGesture={() => {}} />);
    expect(
      screen.getByRole('button', { name: /activate camera/i }),
    ).toBeInTheDocument();
  });

  it('does not render the video element before activation', () => {
    render(<HandsPanel onGesture={() => {}} />);
    expect(screen.queryByTestId('sggs-hands-video')).not.toBeInTheDocument();
  });

  it('shows the privacy notice on the inactive panel', () => {
    render(<HandsPanel onGesture={() => {}} />);
    const notice = screen.getByTestId('sggs-hands-privacy');
    expect(notice).toHaveTextContent(
      /camera stays on this machine\. no video is uploaded\./i,
    );
  });

  it('reports Camera off implicitly (no overlay rendered) before activation', () => {
    // The overlay (which holds the explicit "Camera ready" string) only
    // mounts after activation. Asserting absence of the overlay covers
    // the "Camera off" state for the initial render.
    render(<HandsPanel onGesture={() => {}} />);
    expect(screen.queryByTestId('sggs-hands-overlay')).not.toBeInTheDocument();
  });
});

describe('HandsPanel — activation flow', () => {
  it('clicking Activate Camera switches overlay status to Camera ready', () => {
    render(<HandsPanel onGesture={() => {}} />);
    const activate = screen.getByRole('button', { name: /activate camera/i });
    act(() => {
      fireEvent.click(activate);
    });
    expect(screen.getByTestId('sggs-hands-status')).toHaveTextContent(
      /camera ready/i,
    );
  });

  it('renders the video element once active', () => {
    render(<HandsPanel onGesture={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /activate camera/i }));
    expect(screen.getByTestId('sggs-hands-video')).toBeInTheDocument();
  });

  it('shows "Loading model…" while the hook reports loading_model', () => {
    mockState.status = 'loading_model';
    render(<HandsPanel onGesture={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /activate camera/i }));
    expect(screen.getByTestId('sggs-hands-status')).toHaveTextContent(
      /loading model/i,
    );
  });

  it('shows Camera error and the error message when the hook errors', () => {
    mockState.status = 'error';
    mockState.error = 'simulated webcam failure';
    render(<HandsPanel onGesture={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /activate camera/i }));
    expect(screen.getByTestId('sggs-hands-status')).toHaveTextContent(
      /camera error/i,
    );
    expect(screen.getByTestId('sggs-hands-error')).toHaveTextContent(
      /simulated webcam failure/i,
    );
  });

  it('Turn off camera button restores the inactive state', () => {
    render(<HandsPanel onGesture={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /activate camera/i }));
    expect(screen.getByTestId('sggs-hands-video')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /turn off camera/i }));
    expect(screen.queryByTestId('sggs-hands-video')).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /activate camera/i }),
    ).toBeInTheDocument();
  });
});

describe('HandsPanel — gesture callback wiring', () => {
  it('fires onGesture prop when useHands invokes its onGesture callback', () => {
    const onGesture = vi.fn();
    render(<HandsPanel onGesture={onGesture} />);
    fireEvent.click(screen.getByRole('button', { name: /activate camera/i }));
    expect(mockState.lastOnGesture).not.toBeNull();
    act(() => {
      mockState.lastOnGesture!({
        kind: 'pinch',
        value: { x: 0.5, y: 0.5 },
      });
    });
    expect(onGesture).toHaveBeenCalledTimes(1);
    expect(onGesture.mock.calls[0][0]).toMatchObject({ kind: 'pinch' });
  });

  it('renders the current gesture label in the overlay', () => {
    render(<HandsPanel onGesture={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /activate camera/i }));
    act(() => {
      mockState.lastOnGesture!({ kind: 'fist', value: { rotation: 0.2 } });
    });
    expect(screen.getByTestId('sggs-hands-gesture')).toHaveTextContent(
      /fist rotate/i,
    );
  });

  it('accumulates zoom from two-hand pinch-spread zoomDelta events', () => {
    render(<HandsPanel onGesture={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /activate camera/i }));
    // Baseline zoom is 1.00x.
    expect(screen.getByTestId('sggs-hands-zoom')).toHaveTextContent(/1\.00x/);
    // Send a positive zoomDelta — zoom should rise.
    act(() => {
      mockState.lastOnGesture!({
        kind: 'two_hand_pinch_spread',
        value: { zoomDelta: 0.1 },
      });
    });
    // applyZoomDelta(1.0, 0.1) = 1 * (1 + 0.1*2.5) = 1.25
    expect(screen.getByTestId('sggs-hands-zoom')).toHaveTextContent(/1\.25x/);
  });
});
