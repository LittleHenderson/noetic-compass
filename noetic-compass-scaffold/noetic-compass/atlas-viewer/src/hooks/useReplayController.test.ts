import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { useReplayController, type UseReplayControllerResult } from './useReplayController';
import type { ReplayTrace } from '../lib/replayController';

function makeTrace(n: number): ReplayTrace {
  return {
    tokens: Array.from({ length: n }, (_, i) => ({ token_index: i, token: `t${i}` })),
    per_token_frames: Array.from({ length: n }, () => ({})),
  };
}

interface Harness {
  result: { current: UseReplayControllerResult | null };
  root: Root;
  container: HTMLDivElement;
}

function renderHook(trace: ReplayTrace): Harness {
  const result: { current: UseReplayControllerResult | null } = { current: null };
  function HookHost(): null {
    result.current = useReplayController(trace);
    return null;
  }
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(createElement(HookHost));
  });
  return { result, root, container };
}

function unmount(h: Harness): void {
  act(() => {
    h.root.unmount();
  });
  h.container.remove();
}

describe('useReplayController', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns initial state with paused playback at index 0', () => {
    const h = renderHook(makeTrace(5));
    expect(h.result.current).not.toBeNull();
    const r = h.result.current!;
    expect(r.state).toEqual({
      playbackMode: 'paused',
      speed: 1,
      currentTokenIndex: 0,
      tokenCount: 5,
    });
    unmount(h);
  });

  it('calling play() updates state on re-render', () => {
    const h = renderHook(makeTrace(5));
    act(() => {
      h.result.current!.play();
    });
    expect(h.result.current!.state.playbackMode).toBe('playing');
    expect(h.result.current!.state.currentTokenIndex).toBe(0);
    unmount(h);
  });

  it('seek() updates the state', () => {
    const h = renderHook(makeTrace(8));
    act(() => {
      h.result.current!.seek(4);
    });
    expect(h.result.current!.state.currentTokenIndex).toBe(4);
    unmount(h);
  });

  it('unmount calls controller.destroy', () => {
    const h = renderHook(makeTrace(5));
    const controller = h.result.current!.controller;
    const destroySpy = vi.spyOn(controller, 'destroy');
    unmount(h);
    expect(destroySpy).toHaveBeenCalledTimes(1);
  });
});
