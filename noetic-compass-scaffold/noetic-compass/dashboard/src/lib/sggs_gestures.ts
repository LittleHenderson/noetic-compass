/**
 * sggs_gestures.ts — pure-function gesture detector for SGGS Phase 1.
 *
 * Takes raw MediaPipe-style 21-point hand keypoint arrays and emits typed
 * gesture events. No webcam, no DOM, no MediaPipe — that wiring lives in
 * `sggs_hands.ts` and `HandsPanel.tsx`. This file is testable as a pure
 * function on synthetic keypoint sequences.
 *
 * Three gestures per the SGGS spec (docs/working/sggs_v2_v3_product_feature_backlog_2026_05_06.md
 * line 196):
 *   - fist (rotation): 4 of 5 fingertips curled toward the palm.
 *   - pinch (drag/select): thumb-tip ↔ index-tip distance below threshold.
 *   - two_hand_pinch_spread (zoom): both hands pinching; emit zoomDelta as
 *     the per-frame change in distance between the two pinch points.
 *
 * MediaPipe hand keypoint indices used here (same scheme used by `@mediapipe/hands`):
 *   0  WRIST
 *   1  THUMB_CMC      2 THUMB_MCP    3 THUMB_IP    4 THUMB_TIP
 *   5  INDEX_MCP      6 INDEX_PIP    7 INDEX_DIP   8 INDEX_TIP
 *   9  MIDDLE_MCP    10 MIDDLE_PIP  11 MIDDLE_DIP 12 MIDDLE_TIP
 *   13 RING_MCP      14 RING_PIP    15 RING_DIP   16 RING_TIP
 *   17 PINKY_MCP     18 PINKY_PIP   19 PINKY_DIP  20 PINKY_TIP
 *
 * Coordinates are normalized (0..1) in screen space, with y growing
 * downward. Fingers curled means tip-y > knuckle-y (tip below the
 * knuckle on screen when hand is palm-toward-camera with fingers up).
 */

// ── Public types ───────────────────────────────────────────────────────────

export type GestureKind =
  | 'idle'
  | 'fist'
  | 'pinch'
  | 'two_hand_pinch_spread';

export interface GestureState {
  kind: GestureKind;
  /**
   * Gesture-specific payload:
   *   - pinch: { x, y } normalized pinch position (avg of thumb+index tips).
   *   - fist:  { rotation } — radians of palm rotation since the fist began.
   *   - two_hand_pinch_spread: { zoomDelta } — per-frame change in two-pinch
   *     distance. Positive = hands spreading (zoom in). Negative = hands
   *     converging (zoom out).
   */
  value?: {
    x?: number;
    y?: number;
    rotation?: number;
    zoomDelta?: number;
  };
  /**
   * Internal carry-over data: not part of the public API; used by the
   * detector to track gesture continuity across frames (e.g. fist
   * rotation origin, prior two-hand pinch distance). Consumers should
   * pass back the full previous GestureState rather than reconstructing it.
   */
  _internal?: {
    fistOriginAngle?: number;
    twoHandPrevDist?: number;
  };
}

export interface HandPoint {
  x: number;
  y: number;
  z?: number;
}

export type HandKeypoints = HandPoint[]; // expected length: 21

// ── Tunable thresholds ─────────────────────────────────────────────────────
//
// All thresholds are normalized — MediaPipe Hands emits keypoints in [0, 1]
// screen coords, so a `palm width` of ~0.10-0.20 is typical at arm's length.
// Picked to balance false-positives (jittery detection) against false-
// negatives (gestures that need to be exaggerated). Tested on synthetic
// keypoints in sggs_gestures.test.ts; field-tune on real webcam later.

const PINCH_DISTANCE_THRESHOLD = 0.06; // fraction of frame; ~6% of screen width
const FINGER_CURL_TOLERANCE = 0.0; // tip-y must exceed knuckle-y by at least this
const FIST_REQUIRED_CURLED_FINGERS = 4; // index/middle/ring/pinky — thumb optional

// ── Keypoint index constants ───────────────────────────────────────────────

const WRIST = 0;
const THUMB_TIP = 4;
const INDEX_MCP = 5;
const INDEX_TIP = 8;
const MIDDLE_MCP = 9;
const MIDDLE_TIP = 12;
const RING_MCP = 13;
const RING_TIP = 16;
const PINKY_MCP = 17;
const PINKY_TIP = 20;

// ── Helpers ────────────────────────────────────────────────────────────────

function dist2D(a: HandPoint, b: HandPoint): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Approximate palm "size" as the distance from wrist to middle-finger MCP.
 * Used to normalize the pinch threshold against perceived hand size.
 */
function palmSize(hand: HandKeypoints): number {
  if (hand.length <= MIDDLE_MCP) return 0.1;
  return dist2D(hand[WRIST], hand[MIDDLE_MCP]);
}

/**
 * A finger is "curled" when its tip is on the palm side of its knuckle.
 * For a palm-facing-camera, fingers-up hand: curled => tip.y > mcp.y
 * (tip below knuckle on screen). We use the y-axis check because it
 * generalizes regardless of hand orientation we worry about in v0 (the
 * gesture vocab is small and the user is intentionally signaling).
 */
function isFingerCurled(tip: HandPoint, mcp: HandPoint): boolean {
  return tip.y > mcp.y + FINGER_CURL_TOLERANCE;
}

function isFist(hand: HandKeypoints): boolean {
  if (hand.length < 21) return false;
  let curled = 0;
  if (isFingerCurled(hand[INDEX_TIP], hand[INDEX_MCP])) curled += 1;
  if (isFingerCurled(hand[MIDDLE_TIP], hand[MIDDLE_MCP])) curled += 1;
  if (isFingerCurled(hand[RING_TIP], hand[RING_MCP])) curled += 1;
  if (isFingerCurled(hand[PINKY_TIP], hand[PINKY_MCP])) curled += 1;
  return curled >= FIST_REQUIRED_CURLED_FINGERS;
}

function isPinch(hand: HandKeypoints): boolean {
  if (hand.length < 21) return false;
  const p = palmSize(hand);
  if (p <= 0) return false;
  const d = dist2D(hand[THUMB_TIP], hand[INDEX_TIP]);
  // normalize: pinch when the thumb-index gap is small relative to palm.
  // Also gate against the absolute screen-space threshold so tiny hands
  // far from the camera don't trip false pinches.
  return d / p < 0.35 && d < PINCH_DISTANCE_THRESHOLD * 4;
}

/**
 * Pinch position = midpoint between thumb-tip and index-tip.
 */
function pinchPoint(hand: HandKeypoints): { x: number; y: number } {
  return {
    x: (hand[THUMB_TIP].x + hand[INDEX_TIP].x) / 2,
    y: (hand[THUMB_TIP].y + hand[INDEX_TIP].y) / 2,
  };
}

/**
 * Palm orientation angle, used to track fist rotation. Measured from
 * the wrist toward the middle-finger MCP. Returns radians in (-π, π].
 */
function palmAngle(hand: HandKeypoints): number {
  const w = hand[WRIST];
  const m = hand[MIDDLE_MCP];
  return Math.atan2(m.y - w.y, m.x - w.x);
}

/**
 * Smallest signed angular difference (a - b), wrapped to (-π, π].
 * Avoids the 2π jump when rotating across the ±π seam.
 */
function angleDelta(a: number, b: number): number {
  let d = a - b;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d <= -Math.PI) d += 2 * Math.PI;
  return d;
}

// ── Public detector ────────────────────────────────────────────────────────

/**
 * detectGesture — turn 0-2 hand keypoint arrays into a typed GestureState.
 *
 * Behavior:
 *   - 0 hands → 'idle'.
 *   - 2 hands, both pinching → 'two_hand_pinch_spread' with zoomDelta =
 *     (current two-pinch distance) − (previous two-pinch distance).
 *   - 1 hand, pinching → 'pinch' with the pinch position.
 *   - 1 hand, fist → 'fist' with rotation delta vs the angle captured when
 *     the fist first started.
 *   - Otherwise → 'idle'.
 *
 * `prev` is the previous frame's GestureState; carries the fist origin
 * angle and the previous two-hand pinch distance forward.
 */
export function detectGesture(
  hands: HandKeypoints[],
  prev: GestureState,
): GestureState {
  // No hands: reset to idle but preserve nothing carry-over.
  if (!hands || hands.length === 0) {
    return { kind: 'idle' };
  }

  // Two-hand zoom takes precedence when both hands are pinching.
  if (hands.length >= 2 && isPinch(hands[0]) && isPinch(hands[1])) {
    const p0 = pinchPoint(hands[0]);
    const p1 = pinchPoint(hands[1]);
    const currentDist = dist2D(p0, p1);
    const prevDist = prev?._internal?.twoHandPrevDist;
    const zoomDelta = prevDist !== undefined ? currentDist - prevDist : 0;
    return {
      kind: 'two_hand_pinch_spread',
      value: { zoomDelta },
      _internal: { twoHandPrevDist: currentDist },
    };
  }

  const hand = hands[0];

  // Single-hand pinch. Pinch takes precedence over fist because the
  // pinch check requires extended thumb+index — a fist would already
  // have failed pinch via the absolute distance gate.
  if (isPinch(hand)) {
    const pt = pinchPoint(hand);
    return {
      kind: 'pinch',
      value: { x: pt.x, y: pt.y },
    };
  }

  // Single-hand fist. If we were already in a fist, keep the original
  // origin angle and emit rotation delta against it. If not, capture a
  // fresh origin and emit rotation=0 for this first frame.
  if (isFist(hand)) {
    const currentAngle = palmAngle(hand);
    const origin =
      prev?.kind === 'fist' && prev._internal?.fistOriginAngle !== undefined
        ? prev._internal.fistOriginAngle
        : currentAngle;
    const rotation = angleDelta(currentAngle, origin);
    return {
      kind: 'fist',
      value: { rotation },
      _internal: { fistOriginAngle: origin },
    };
  }

  return { kind: 'idle' };
}

// ── Test-only exports ──────────────────────────────────────────────────────
//
// Re-exported helpers so the unit tests can build well-formed synthetic
// hands without duplicating constants. Not part of the public surface;
// runtime cost is zero, but downstream callers should depend only on
// `detectGesture` and the public types above.

export const _internal_for_tests = {
  PINCH_DISTANCE_THRESHOLD,
  FIST_REQUIRED_CURLED_FINGERS,
  WRIST,
  THUMB_TIP,
  INDEX_MCP,
  INDEX_TIP,
  MIDDLE_MCP,
  MIDDLE_TIP,
  RING_MCP,
  RING_TIP,
  PINKY_MCP,
  PINKY_TIP,
  palmAngle,
  isFist,
  isPinch,
  pinchPoint,
};
