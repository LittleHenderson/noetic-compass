/**
 * sggs_gestures.test.ts — pure-function unit tests for the SGGS gesture
 * detector. No webcam, no MediaPipe runtime; everything is synthetic
 * 21-point keypoint arrays.
 *
 * Coverage (matches Agent C brief):
 *   - Detect fist from synthetic curled-finger keypoints.
 *   - Detect pinch from synthetic thumb+index keypoints.
 *   - Detect two_hand_pinch_spread from two synthetic pinching hands moving apart.
 *   - Idle when keypoints are extended-open.
 *   - Rotation delta during fist: synthesize a hand rotating around its
 *     center; verify rotation grows monotonically.
 *   - Zoom delta during two-hand: synthesize hands moving apart; verify
 *     zoomDelta > 0.
 */

import { describe, it, expect } from 'vitest';
import {
  detectGesture,
  type GestureState,
  type HandKeypoints,
  type HandPoint,
} from './sggs_gestures';

// ── Synthetic hand builders ────────────────────────────────────────────────
//
// Each builder returns a fully-populated 21-element HandKeypoints array.
// Coordinates are in normalized [0,1] screen space, with y growing
// downward (MediaPipe convention).

/**
 * Build an extended-open hand centered at (cx, cy). All five fingers
 * are pointing up; no curl. Used as the baseline "idle/open" hand.
 */
function makeOpenHand(cx: number, cy: number): HandKeypoints {
  // Wrist below center, fingers up.
  const wrist: HandPoint = { x: cx, y: cy + 0.10 };
  // Thumb extends sideways.
  const thumbCmc: HandPoint = { x: cx - 0.04, y: cy + 0.06 };
  const thumbMcp: HandPoint = { x: cx - 0.06, y: cy + 0.04 };
  const thumbIp: HandPoint = { x: cx - 0.08, y: cy + 0.02 };
  const thumbTip: HandPoint = { x: cx - 0.10, y: cy };
  // Index, middle, ring, pinky — all extended upward.
  function finger(xOffset: number, mcpY: number): HandPoint[] {
    return [
      { x: cx + xOffset, y: mcpY },
      { x: cx + xOffset, y: mcpY - 0.04 },
      { x: cx + xOffset, y: mcpY - 0.07 },
      { x: cx + xOffset, y: mcpY - 0.10 }, // tip ABOVE mcp ⇒ extended
    ];
  }
  const [iMcp, iPip, iDip, iTip] = finger(-0.02, cy + 0.02);
  const [mMcp, mPip, mDip, mTip] = finger(0.0, cy + 0.02);
  const [rMcp, rPip, rDip, rTip] = finger(0.02, cy + 0.02);
  const [pMcp, pPip, pDip, pTip] = finger(0.04, cy + 0.02);

  return [
    wrist,
    thumbCmc,
    thumbMcp,
    thumbIp,
    thumbTip,
    iMcp,
    iPip,
    iDip,
    iTip,
    mMcp,
    mPip,
    mDip,
    mTip,
    rMcp,
    rPip,
    rDip,
    rTip,
    pMcp,
    pPip,
    pDip,
    pTip,
  ];
}

/**
 * Build a closed-fist hand centered at (cx, cy). Same wrist, but every
 * fingertip is below its knuckle (curled in toward the palm). The thumb
 * sits across the front of the fist near the index knuckle.
 */
function makeFistHand(cx: number, cy: number): HandKeypoints {
  const wrist: HandPoint = { x: cx, y: cy + 0.10 };
  // Thumb folded inward, tip near index MCP.
  const thumbCmc: HandPoint = { x: cx - 0.03, y: cy + 0.06 };
  const thumbMcp: HandPoint = { x: cx - 0.02, y: cy + 0.04 };
  const thumbIp: HandPoint = { x: cx - 0.01, y: cy + 0.03 };
  const thumbTip: HandPoint = { x: cx + 0.0, y: cy + 0.025 };
  function curledFinger(xOffset: number, mcpY: number): HandPoint[] {
    return [
      { x: cx + xOffset, y: mcpY }, // mcp
      { x: cx + xOffset, y: mcpY + 0.01 }, // pip
      { x: cx + xOffset, y: mcpY + 0.02 }, // dip
      { x: cx + xOffset, y: mcpY + 0.03 }, // tip BELOW mcp ⇒ curled
    ];
  }
  const [iMcp, iPip, iDip, iTip] = curledFinger(-0.02, cy + 0.02);
  const [mMcp, mPip, mDip, mTip] = curledFinger(0.0, cy + 0.02);
  const [rMcp, rPip, rDip, rTip] = curledFinger(0.02, cy + 0.02);
  const [pMcp, pPip, pDip, pTip] = curledFinger(0.04, cy + 0.02);
  return [
    wrist,
    thumbCmc,
    thumbMcp,
    thumbIp,
    thumbTip,
    iMcp,
    iPip,
    iDip,
    iTip,
    mMcp,
    mPip,
    mDip,
    mTip,
    rMcp,
    rPip,
    rDip,
    rTip,
    pMcp,
    pPip,
    pDip,
    pTip,
  ];
}

/**
 * Build a pinching hand: thumb-tip and index-tip touching at (cx, cy).
 * Other fingers remain extended so the fist heuristic does not also fire.
 */
function makePinchHand(cx: number, cy: number): HandKeypoints {
  const hand = makeOpenHand(cx, cy);
  // Override thumb tip + index tip to be coincident at (cx, cy).
  hand[4] = { x: cx, y: cy };
  hand[8] = { x: cx + 0.003, y: cy + 0.003 };
  return hand;
}

/**
 * Rotate every point of `hand` by `theta` radians around `(cx, cy)`.
 * Used to verify the fist-rotation tracker.
 */
function rotateHand(
  hand: HandKeypoints,
  theta: number,
  cx: number,
  cy: number,
): HandKeypoints {
  const cos = Math.cos(theta);
  const sin = Math.sin(theta);
  return hand.map((p) => {
    const dx = p.x - cx;
    const dy = p.y - cy;
    return { x: cx + dx * cos - dy * sin, y: cy + dx * sin + dy * cos };
  });
}

const IDLE: GestureState = { kind: 'idle' };

// ── Tests ──────────────────────────────────────────────────────────────────

describe('detectGesture — basic shape detection', () => {
  it('returns idle when no hands are present', () => {
    expect(detectGesture([], IDLE).kind).toBe('idle');
  });

  it('returns idle for an extended-open hand', () => {
    const open = makeOpenHand(0.5, 0.5);
    expect(detectGesture([open], IDLE).kind).toBe('idle');
  });

  it('detects fist from synthetic curled-finger keypoints', () => {
    const fist = makeFistHand(0.5, 0.5);
    const state = detectGesture([fist], IDLE);
    expect(state.kind).toBe('fist');
    expect(state.value?.rotation).toBeDefined();
  });

  it('detects pinch from synthetic thumb+index touching keypoints', () => {
    const pinch = makePinchHand(0.5, 0.5);
    const state = detectGesture([pinch], IDLE);
    expect(state.kind).toBe('pinch');
    expect(state.value?.x).toBeCloseTo(0.5, 2);
    expect(state.value?.y).toBeCloseTo(0.5, 2);
  });

  it('detects two_hand_pinch_spread when both hands are pinching', () => {
    const leftPinch = makePinchHand(0.3, 0.5);
    const rightPinch = makePinchHand(0.7, 0.5);
    const state = detectGesture([leftPinch, rightPinch], IDLE);
    expect(state.kind).toBe('two_hand_pinch_spread');
    expect(state.value?.zoomDelta).toBe(0); // first frame: no prior dist
  });
});

describe('detectGesture — fist rotation tracking', () => {
  it('reports rotation=0 on the first fist frame', () => {
    const fist = makeFistHand(0.5, 0.5);
    const state = detectGesture([fist], IDLE);
    expect(state.kind).toBe('fist');
    expect(state.value?.rotation).toBeCloseTo(0, 6);
  });

  it('grows rotation monotonically as the hand rotates clockwise', () => {
    const base = makeFistHand(0.5, 0.5);
    // Frame 0: capture origin.
    const s0 = detectGesture([base], IDLE);
    expect(s0.kind).toBe('fist');
    // Frame 1: small rotation.
    const r1 = rotateHand(base, 0.2, 0.5, 0.5);
    const s1 = detectGesture([r1], s0);
    expect(s1.kind).toBe('fist');
    expect(s1.value?.rotation).toBeCloseTo(0.2, 3);
    // Frame 2: bigger rotation, same origin carried forward.
    const r2 = rotateHand(base, 0.5, 0.5, 0.5);
    const s2 = detectGesture([r2], s1);
    expect(s2.kind).toBe('fist');
    expect(s2.value?.rotation).toBeCloseTo(0.5, 3);
    // Verify monotonicity vs the previous frame.
    expect((s2.value!.rotation ?? 0) > (s1.value!.rotation ?? 0)).toBe(true);
  });

  it('handles counter-rotation symmetrically (negative rotation)', () => {
    const base = makeFistHand(0.5, 0.5);
    const s0 = detectGesture([base], IDLE);
    const r1 = rotateHand(base, -0.3, 0.5, 0.5);
    const s1 = detectGesture([r1], s0);
    expect(s1.kind).toBe('fist');
    expect(s1.value?.rotation).toBeCloseTo(-0.3, 3);
  });

  it('resets origin angle when fist drops to idle then resumes', () => {
    const base = makeFistHand(0.5, 0.5);
    const s0 = detectGesture([base], IDLE);
    // Lift the fist (idle) — origin should reset.
    const open = makeOpenHand(0.5, 0.5);
    const sIdle = detectGesture([open], s0);
    expect(sIdle.kind).toBe('idle');
    // New fist at an already-rotated pose: rotation should start at 0.
    const rotatedBase = rotateHand(base, 0.4, 0.5, 0.5);
    const s2 = detectGesture([rotatedBase], sIdle);
    expect(s2.kind).toBe('fist');
    expect(s2.value?.rotation).toBeCloseTo(0, 6);
  });
});

describe('detectGesture — two-hand zoom tracking', () => {
  it('emits positive zoomDelta when both pinches move apart', () => {
    // Frame 0: hands at separation 0.4.
    const f0Left = makePinchHand(0.3, 0.5);
    const f0Right = makePinchHand(0.7, 0.5);
    const s0 = detectGesture([f0Left, f0Right], IDLE);
    expect(s0.kind).toBe('two_hand_pinch_spread');
    // Frame 1: hands further apart, separation 0.6.
    const f1Left = makePinchHand(0.2, 0.5);
    const f1Right = makePinchHand(0.8, 0.5);
    const s1 = detectGesture([f1Left, f1Right], s0);
    expect(s1.kind).toBe('two_hand_pinch_spread');
    const zd = s1.value?.zoomDelta ?? 0;
    expect(zd).toBeGreaterThan(0);
    // Should be approximately 0.2 (0.6 − 0.4).
    expect(zd).toBeCloseTo(0.2, 2);
  });

  it('emits negative zoomDelta when pinches converge', () => {
    const f0Left = makePinchHand(0.2, 0.5);
    const f0Right = makePinchHand(0.8, 0.5);
    const s0 = detectGesture([f0Left, f0Right], IDLE);
    const f1Left = makePinchHand(0.4, 0.5);
    const f1Right = makePinchHand(0.6, 0.5);
    const s1 = detectGesture([f1Left, f1Right], s0);
    expect(s1.kind).toBe('two_hand_pinch_spread');
    const zd = s1.value?.zoomDelta ?? 0;
    expect(zd).toBeLessThan(0);
    expect(zd).toBeCloseTo(-0.4, 2);
  });

  it('falls back to single pinch when only one hand is pinching', () => {
    const pinch = makePinchHand(0.4, 0.5);
    const open = makeOpenHand(0.7, 0.5);
    const state = detectGesture([pinch, open], IDLE);
    // Two-hand only fires when BOTH are pinching. With one pinch + one
    // open, the detector inspects hands[0] which is pinching → 'pinch'.
    expect(state.kind).toBe('pinch');
  });
});
