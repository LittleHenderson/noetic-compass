import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ReplayController,
  type ReplaySpeed,
  type ReplayState,
  type ReplayTrace,
} from './replayController';

function makeTrace(n: number): ReplayTrace {
  return {
    tokens: Array.from({ length: n }, (_, i) => ({ token_index: i, token: `t${i}` })),
    per_token_frames: Array.from({ length: n }, () => ({})),
  };
}

describe('ReplayController', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('initializes paused at index 0 with speed 1', () => {
    const c = new ReplayController(makeTrace(5));
    expect(c.getState()).toEqual({
      playbackMode: 'paused',
      speed: 1,
      currentTokenIndex: 0,
      tokenCount: 5,
    });
    c.destroy();
  });

  it('respects initialSpeed and tickIntervalMs', () => {
    const c = new ReplayController(makeTrace(3), { initialSpeed: 2, tickIntervalMs: 200 });
    expect(c.getState().speed).toBe(2);
    c.destroy();
  });

  it('play() advances index after tickIntervalMs', () => {
    const c = new ReplayController(makeTrace(5), { tickIntervalMs: 500 });
    c.play();
    expect(c.getState().currentTokenIndex).toBe(0);
    expect(c.getState().playbackMode).toBe('playing');
    vi.advanceTimersByTime(500);
    expect(c.getState().currentTokenIndex).toBe(1);
    vi.advanceTimersByTime(500);
    expect(c.getState().currentTokenIndex).toBe(2);
    c.destroy();
  });

  it('reaches last token, stays there, and transitions to paused', () => {
    const c = new ReplayController(makeTrace(3), { tickIntervalMs: 100 });
    c.play();
    vi.advanceTimersByTime(100);
    expect(c.getState().currentTokenIndex).toBe(1);
    vi.advanceTimersByTime(100);
    expect(c.getState().currentTokenIndex).toBe(2);
    expect(c.getState().playbackMode).toBe('paused');
    vi.advanceTimersByTime(1000);
    expect(c.getState().currentTokenIndex).toBe(2);
    c.destroy();
  });

  it('pause() stops advancement', () => {
    const c = new ReplayController(makeTrace(10), { tickIntervalMs: 100 });
    c.play();
    vi.advanceTimersByTime(100);
    expect(c.getState().currentTokenIndex).toBe(1);
    c.pause();
    expect(c.getState().playbackMode).toBe('paused');
    vi.advanceTimersByTime(1000);
    expect(c.getState().currentTokenIndex).toBe(1);
    c.destroy();
  });

  it('toggle() flips between paused and playing', () => {
    const c = new ReplayController(makeTrace(5), { tickIntervalMs: 100 });
    c.toggle();
    expect(c.getState().playbackMode).toBe('playing');
    c.toggle();
    expect(c.getState().playbackMode).toBe('paused');
    c.destroy();
  });

  it('seek(N) clamps to [0, tokenCount-1]', () => {
    const c = new ReplayController(makeTrace(5));
    c.seek(3);
    expect(c.getState().currentTokenIndex).toBe(3);
    c.seek(-10);
    expect(c.getState().currentTokenIndex).toBe(0);
    c.seek(100);
    expect(c.getState().currentTokenIndex).toBe(4);
    c.destroy();
  });

  it('step(±1) moves by delta, clamped', () => {
    const c = new ReplayController(makeTrace(4));
    c.step(2);
    expect(c.getState().currentTokenIndex).toBe(2);
    c.step(-1);
    expect(c.getState().currentTokenIndex).toBe(1);
    c.step(-100);
    expect(c.getState().currentTokenIndex).toBe(0);
    c.step(100);
    expect(c.getState().currentTokenIndex).toBe(3);
    c.destroy();
  });

  it('setSpeed scales tick interval inverse-proportionally', () => {
    const c = new ReplayController(makeTrace(10), { tickIntervalMs: 500 });
    c.setSpeed(4 as ReplaySpeed);
    c.play();
    vi.advanceTimersByTime(125);
    expect(c.getState().currentTokenIndex).toBe(1);
    vi.advanceTimersByTime(125);
    expect(c.getState().currentTokenIndex).toBe(2);
    c.destroy();
  });

  it('setSpeed while paused does not start playback', () => {
    const c = new ReplayController(makeTrace(5), { tickIntervalMs: 500 });
    c.setSpeed(2 as ReplaySpeed);
    expect(c.getState().playbackMode).toBe('paused');
    vi.advanceTimersByTime(1000);
    expect(c.getState().currentTokenIndex).toBe(0);
    c.destroy();
  });

  it('subscribe receives state updates; unsubscribe stops them', () => {
    const c = new ReplayController(makeTrace(5));
    const received: ReplayState[] = [];
    const unsub = c.subscribe((s) => received.push(s));
    c.seek(2);
    c.seek(3);
    expect(received).toHaveLength(2);
    expect(received[1].currentTokenIndex).toBe(3);
    unsub();
    c.seek(4);
    expect(received).toHaveLength(2);
    c.destroy();
  });

  it('destroy clears pending timer and stops further state changes', () => {
    const c = new ReplayController(makeTrace(10), { tickIntervalMs: 100 });
    c.play();
    c.destroy();
    vi.advanceTimersByTime(10_000);
    expect(c.getState().currentTokenIndex).toBe(0);
  });

  it('play() on the last token restarts from the beginning', () => {
    const c = new ReplayController(makeTrace(3), { tickIntervalMs: 100 });
    c.seek(2);
    c.play();
    expect(c.getState().playbackMode).toBe('playing');
    expect(c.getState().currentTokenIndex).toBe(0);
    vi.advanceTimersByTime(100);
    expect(c.getState().currentTokenIndex).toBe(1);
    c.destroy();
  });
});
