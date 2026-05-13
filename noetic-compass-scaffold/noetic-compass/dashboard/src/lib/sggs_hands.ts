/**
 * sggs_hands.ts — MediaPipe Hands wrapper hook.
 *
 * Mounts the MediaPipe Hands runtime against a provided <video> element,
 * runs gesture detection on each frame via `sggs_gestures.detectGesture`,
 * and reports gesture state via a callback. The hook is opt-in: it does
 * NOT call getUserMedia or start any inference until `enabled === true`.
 * That gate is owned by `HandsPanel.tsx`, which prompts the user via an
 * "Activate Camera" button.
 *
 * Privacy property (SGGS spec line 51): everything in this file runs
 * locally in the browser. We import MediaPipe Hands via the official npm
 * package; the @mediapipe/hands package loads its WASM model bundle from
 * the same origin (jsdelivr CDN by default — see locateFile override).
 * No video frames leave the browser.
 *
 * MediaPipe is loaded lazily so that:
 *   - Unit tests can mock `useHands` without dragging the runtime into jsdom.
 *   - The 300KB-ish payload only fetches when the user opts in.
 */

import { useEffect, useRef, useState } from 'react';
import {
  detectGesture,
  type GestureState,
  type HandKeypoints,
} from './sggs_gestures';

// ── Minimal MediaPipe Hands typings ────────────────────────────────────────
//
// We deliberately keep this surface narrow rather than depending on
// `@types/mediapipe-hands` (none ships; the package's d.ts is sparse).
// Only the bits we actually call are typed.

interface MpResults {
  multiHandLandmarks?: { x: number; y: number; z: number }[][];
}

interface MpHands {
  setOptions(opts: {
    maxNumHands?: number;
    modelComplexity?: 0 | 1;
    minDetectionConfidence?: number;
    minTrackingConfidence?: number;
  }): void;
  onResults(cb: (results: MpResults) => void): void;
  send(input: { image: HTMLVideoElement }): Promise<void>;
  close?: () => void;
}

interface MpCamera {
  start(): Promise<void>;
  stop(): void;
}

type HandsModule = {
  Hands: new (opts: { locateFile: (file: string) => string }) => MpHands;
};

type CameraModule = {
  Camera: new (
    video: HTMLVideoElement,
    opts: { onFrame: () => Promise<void>; width?: number; height?: number },
  ) => MpCamera;
};

// ── Public API ─────────────────────────────────────────────────────────────

export interface UseHandsOptions {
  videoEl: HTMLVideoElement | null;
  onGesture: (state: GestureState) => void;
  enabled: boolean;
}

export interface UseHandsResult {
  status: 'idle' | 'loading_model' | 'ready' | 'error';
  error: string | null;
}

/**
 * useHands — bind MediaPipe Hands to a video element and surface gesture
 * events. Returns a status + error pair so the panel UI can render
 * appropriate state.
 *
 * Contract:
 *   - Does NOT auto-start when `enabled` is false (camera-off default).
 *   - Calls `onGesture` on every frame that produces a non-error
 *     gesture, including 'idle' frames (so consumers can debounce).
 *   - Cleans up the camera and Hands instance on unmount or when
 *     `enabled` flips back to false.
 */
export function useHands(opts: UseHandsOptions): UseHandsResult {
  const { videoEl, onGesture, enabled } = opts;
  const [status, setStatus] = useState<UseHandsResult['status']>('idle');
  const [error, setError] = useState<string | null>(null);

  // Refs so we can tear down across re-renders without re-creating.
  const handsRef = useRef<MpHands | null>(null);
  const cameraRef = useRef<MpCamera | null>(null);
  const prevGestureRef = useRef<GestureState>({ kind: 'idle' });
  const onGestureRef = useRef(onGesture);
  onGestureRef.current = onGesture;

  useEffect(() => {
    let cancelled = false;
    if (!enabled || !videoEl) {
      setStatus('idle');
      return;
    }

    setStatus('loading_model');
    setError(null);

    (async () => {
      try {
        // Lazy-import so test environments / disabled state don't pull
        // the runtime. Vite must transform these (no @vite-ignore) —
        // otherwise the browser cannot resolve bare package specifiers
        // at runtime (Codex audit 3f495ba blocker 1, 2026-05-13).
        // Tests mock useHands wholesale; this path only runs on opt-in.
        const [handsMod, cameraMod] = await Promise.all([
          import('@mediapipe/hands') as Promise<unknown>,
          import('@mediapipe/camera_utils') as Promise<unknown>,
        ]);
        if (cancelled) return;

        const HandsCtor = (handsMod as HandsModule).Hands;
        const CameraCtor = (cameraMod as CameraModule).Camera;

        const hands = new HandsCtor({
          // MediaPipe Hands requires loading the model WASM + assets at
          // runtime. We point at the jsdelivr CDN matching the installed
          // package version — same scheme the official examples use.
          // No frames are uploaded; this just fetches static assets.
          locateFile: (file) =>
            `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
        });
        hands.setOptions({
          maxNumHands: 2,
          modelComplexity: 1,
          minDetectionConfidence: 0.6,
          minTrackingConfidence: 0.5,
        });
        hands.onResults((results: MpResults) => {
          const landmarks = results.multiHandLandmarks ?? [];
          const hands2d: HandKeypoints[] = landmarks.map((hand) =>
            hand.map((pt) => ({ x: pt.x, y: pt.y, z: pt.z })),
          );
          const next = detectGesture(hands2d, prevGestureRef.current);
          prevGestureRef.current = next;
          onGestureRef.current(next);
        });
        handsRef.current = hands;

        const camera = new CameraCtor(videoEl, {
          onFrame: async () => {
            if (handsRef.current) {
              await handsRef.current.send({ image: videoEl });
            }
          },
          width: 640,
          height: 480,
        });
        cameraRef.current = camera;
        await camera.start();
        if (cancelled) {
          camera.stop();
          return;
        }
        setStatus('ready');
      } catch (e) {
        if (cancelled) return;
        const msg =
          e instanceof Error
            ? e.message
            : typeof e === 'string'
              ? e
              : 'Unknown error initializing MediaPipe Hands';
        setError(msg);
        setStatus('error');
      }
    })();

    return () => {
      cancelled = true;
      try {
        cameraRef.current?.stop();
      } catch {
        // best-effort teardown
      }
      try {
        handsRef.current?.close?.();
      } catch {
        // best-effort teardown
      }
      cameraRef.current = null;
      handsRef.current = null;
      prevGestureRef.current = { kind: 'idle' };
    };
  }, [enabled, videoEl]);

  return { status, error };
}
