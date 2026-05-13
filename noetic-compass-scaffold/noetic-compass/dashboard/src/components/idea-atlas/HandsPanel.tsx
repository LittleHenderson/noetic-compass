/**
 * HandsPanel — React component that mounts the webcam, runs MediaPipe Hands,
 * and surfaces gesture state via callback props.
 *
 * SGGS spec requirements implemented here:
 *   - Permission flow: user must click "Activate Camera" before the
 *     webcam turns on (spec line 51 privacy property; backlog Phase 1).
 *   - Privacy notice: "Camera stays on this machine. No video is uploaded."
 *   - Status overlay: shows current gesture + zoom level, cribbing the
 *     wording from the reference impl (teleclaudius / Bles Software).
 *   - Three gestures supported via sggs_gestures: fist (rotation),
 *     pinch (drag/select), two_hand_pinch_spread (zoom).
 *
 * Keyboard parity is NOT in scope for this agent — that's the integration
 * step / Agent A's plan. This file is purely the webcam + gesture mount.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useHands } from '../../lib/sggs_hands';
import type { GestureState } from '../../lib/sggs_gestures';

export interface HandsPanelProps {
  onGesture: (state: GestureState) => void;
  className?: string;
}

// ── Display helpers ────────────────────────────────────────────────────────

/**
 * Human-readable gesture label. Mirrors the reference impl's surface
 * wording ("Pinch ready", "Fist rotate", "Zoom"), kept short so the
 * overlay stays scannable.
 */
function gestureLabel(state: GestureState | null): string {
  if (!state) return 'none';
  switch (state.kind) {
    case 'idle':
      return 'idle';
    case 'fist':
      return 'fist rotate';
    case 'pinch':
      return 'pinch ready';
    case 'two_hand_pinch_spread':
      return 'two-hand zoom';
    default:
      return 'unknown';
  }
}

/**
 * Compute the cumulative zoom factor from a sequence of zoomDelta events.
 * Each two_hand_pinch_spread frame contributes its zoomDelta (a normalized
 * 0..1-ish distance change) to a running multiplier. We clamp to a sane
 * range so the displayed value can't run away during noisy detection.
 */
function applyZoomDelta(current: number, delta: number): number {
  // Map normalized distance delta into a multiplicative zoom. The factor
  // 2.5 is empirical — large enough that a clear spread visibly moves
  // the zoom number, small enough that hand jitter stays imperceptible.
  const factor = 1 + delta * 2.5;
  const next = current * factor;
  if (next < 0.2) return 0.2;
  if (next > 5.0) return 5.0;
  return next;
}

// ── Component ──────────────────────────────────────────────────────────────

export function HandsPanel(props: HandsPanelProps) {
  const { onGesture, className } = props;
  const [active, setActive] = useState<boolean>(false);
  const [latestGesture, setLatestGesture] = useState<GestureState | null>(null);
  const [zoom, setZoom] = useState<number>(1.0);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const onGestureRef = useRef(onGesture);
  onGestureRef.current = onGesture;

  const handleGesture = useCallback((state: GestureState) => {
    setLatestGesture(state);
    if (
      state.kind === 'two_hand_pinch_spread' &&
      state.value?.zoomDelta !== undefined
    ) {
      setZoom((prev) => applyZoomDelta(prev, state.value!.zoomDelta!));
    }
    onGestureRef.current(state);
  }, []);

  const { status, error } = useHands({
    videoEl: videoRef.current,
    onGesture: handleGesture,
    enabled: active,
  });

  // Stop the user-facing video stream if the panel unmounts mid-session.
  useEffect(() => {
    return () => {
      const v = videoRef.current;
      const stream = v?.srcObject as MediaStream | null;
      if (stream) {
        for (const track of stream.getTracks()) track.stop();
      }
    };
  }, []);

  // Pretty status string for the overlay.
  let statusLabel: string;
  if (!active) statusLabel = 'Camera off';
  else if (status === 'loading_model') statusLabel = 'Loading model…';
  else if (status === 'ready') statusLabel = 'Camera ready';
  else if (status === 'error') statusLabel = 'Camera error';
  else statusLabel = 'Camera off';

  return (
    <div
      className={
        'sggs-hands-panel relative inline-block rounded-md border border-slate-300 bg-slate-50 p-3 text-sm ' +
        (className ?? '')
      }
      data-testid="sggs-hands-panel"
    >
      <div className="mb-2 font-medium text-slate-800">SGGS — Hands</div>

      {/* Permission gate. Required before any webcam access — explicit
          user opt-in is the privacy contract. */}
      {!active && (
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => setActive(true)}
            className="w-fit rounded bg-slate-800 px-3 py-1.5 text-white hover:bg-slate-700"
            data-testid="sggs-hands-activate"
          >
            Activate Camera
          </button>
          <div className="space-y-1" data-testid="sggs-hands-privacy">
            <p className="text-xs text-slate-700">
              Video stays on this machine. No camera frames are uploaded.
            </p>
            <p className="text-[10px] text-slate-600">
              MediaPipe model files may load from a CDN on first use unless
              self-hosted.
            </p>
          </div>
        </div>
      )}

      {/* Webcam preview + status overlay. */}
      {active && (
        <div className="flex flex-col gap-2">
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="block h-48 w-64 rounded bg-black object-cover"
            data-testid="sggs-hands-video"
          />
          <div
            className="rounded border border-slate-200 bg-white p-2 text-xs text-slate-700"
            data-testid="sggs-hands-overlay"
          >
            <div data-testid="sggs-hands-status">{statusLabel}</div>
            <div data-testid="sggs-hands-gesture">
              Gesture: {gestureLabel(latestGesture)}
            </div>
            <div data-testid="sggs-hands-zoom">
              Zoom: {zoom.toFixed(2)}x
            </div>
            {error && (
              <div
                className="text-red-600"
                data-testid="sggs-hands-error"
              >
                {error}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              setActive(false);
              setLatestGesture(null);
              setZoom(1.0);
            }}
            className="w-fit rounded border border-slate-400 px-2 py-1 text-xs hover:bg-slate-100"
            data-testid="sggs-hands-deactivate"
          >
            Turn off camera
          </button>
        </div>
      )}
    </div>
  );
}

export default HandsPanel;
