import { useCallback, useEffect, useMemo, useRef, useSyncExternalStore } from 'react';
import {
  ReplayController,
  type ReplaySpeed,
  type ReplayState,
  type ReplayTrace,
} from '../lib/replayController';

export interface UseReplayControllerResult {
  state: ReplayState;
  controller: ReplayController;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  seek: (index: number) => void;
  setSpeed: (s: ReplaySpeed) => void;
  step: (delta: number) => void;
}

export function useReplayController(
  trace: ReplayTrace,
  opts?: { initialSpeed?: ReplaySpeed },
): UseReplayControllerResult {
  const initialSpeed = opts?.initialSpeed;
  const controller = useMemo(
    () => new ReplayController(trace, initialSpeed !== undefined ? { initialSpeed } : undefined),
    [trace, initialSpeed],
  );

  const controllerRef = useRef(controller);
  controllerRef.current = controller;

  useEffect(() => {
    return () => {
      controller.destroy();
    };
  }, [controller]);

  const subscribe = useCallback(
    (listener: () => void) => controller.subscribe(listener),
    [controller],
  );
  const getSnapshot = useCallback(() => controller.getState(), [controller]);

  const state = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const play = useCallback(() => controllerRef.current.play(), []);
  const pause = useCallback(() => controllerRef.current.pause(), []);
  const toggle = useCallback(() => controllerRef.current.toggle(), []);
  const seek = useCallback((index: number) => controllerRef.current.seek(index), []);
  const setSpeed = useCallback(
    (s: ReplaySpeed) => controllerRef.current.setSpeed(s),
    [],
  );
  const step = useCallback((delta: number) => controllerRef.current.step(delta), []);

  return { state, controller, play, pause, toggle, seek, setSpeed, step };
}
