export interface ReplayTrace {
  tokens: { token_index: number; token: string }[];
  per_token_frames: unknown[];
  model_id?: string;
  neuron_covers?: {
    // Each value is now a list of NeuronCoverMember-shaped records OR
    // legacy bare strings (older offline fixtures). The atlas viewer
    // normalises both shapes via atlasLiveApi.normaliseCoverMember.
    per_class_neuron_covers?: Record<string, unknown[]>;
  };
  model_manifest?: unknown;
}

export type ReplaySpeed = 0.25 | 0.5 | 1 | 2 | 4;

export interface ReplayState {
  playbackMode: 'paused' | 'playing';
  speed: ReplaySpeed;
  currentTokenIndex: number;
  tokenCount: number;
}

export type ReplayListener = (state: ReplayState) => void;

const DEFAULT_TICK_INTERVAL_MS = 500;

export class ReplayController {
  private state: ReplayState;
  private listeners: Set<ReplayListener> = new Set();
  private timer: ReturnType<typeof setTimeout> | null = null;
  private readonly baseTickIntervalMs: number;
  private destroyed = false;

  constructor(
    trace: ReplayTrace,
    opts?: { initialSpeed?: ReplaySpeed; tickIntervalMs?: number },
  ) {
    const tokenCount = trace.tokens.length;
    this.baseTickIntervalMs = opts?.tickIntervalMs ?? DEFAULT_TICK_INTERVAL_MS;
    this.state = {
      playbackMode: 'paused',
      speed: opts?.initialSpeed ?? 1,
      currentTokenIndex: 0,
      tokenCount,
    };
  }

  getState(): ReplayState {
    return this.state;
  }

  subscribe(listener: ReplayListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  play(): void {
    if (this.destroyed) return;
    if (this.state.tokenCount === 0) return;
    if (this.state.currentTokenIndex >= this.state.tokenCount - 1) return;
    if (this.state.playbackMode === 'playing') return;
    this.setState({ ...this.state, playbackMode: 'playing' });
    this.scheduleTick();
  }

  pause(): void {
    if (this.state.playbackMode === 'paused') return;
    this.clearTimer();
    this.setState({ ...this.state, playbackMode: 'paused' });
  }

  toggle(): void {
    if (this.state.playbackMode === 'playing') {
      this.pause();
    } else {
      this.play();
    }
  }

  seek(index: number): void {
    const clamped = this.clampIndex(index);
    if (clamped === this.state.currentTokenIndex) return;
    this.setState({ ...this.state, currentTokenIndex: clamped });
  }

  setSpeed(speed: ReplaySpeed): void {
    if (speed === this.state.speed) return;
    const wasPlaying = this.state.playbackMode === 'playing';
    if (wasPlaying) this.clearTimer();
    this.setState({ ...this.state, speed });
    if (wasPlaying) this.scheduleTick();
  }

  step(delta: number): void {
    this.seek(this.state.currentTokenIndex + delta);
  }

  destroy(): void {
    this.destroyed = true;
    this.clearTimer();
    this.listeners.clear();
  }

  private setState(next: ReplayState): void {
    this.state = next;
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }

  private clampIndex(index: number): number {
    if (this.state.tokenCount === 0) return 0;
    if (!Number.isFinite(index)) return this.state.currentTokenIndex;
    const floored = Math.floor(index);
    if (floored < 0) return 0;
    if (floored > this.state.tokenCount - 1) return this.state.tokenCount - 1;
    return floored;
  }

  private currentTickIntervalMs(): number {
    return this.baseTickIntervalMs / this.state.speed;
  }

  private scheduleTick(): void {
    this.clearTimer();
    this.timer = setTimeout(() => {
      this.timer = null;
      this.advance();
    }, this.currentTickIntervalMs());
  }

  private advance(): void {
    if (this.destroyed) return;
    if (this.state.playbackMode !== 'playing') return;
    const nextIndex = this.state.currentTokenIndex + 1;
    if (nextIndex >= this.state.tokenCount - 1) {
      this.setState({
        ...this.state,
        currentTokenIndex: this.state.tokenCount - 1,
        playbackMode: 'paused',
      });
      return;
    }
    this.setState({ ...this.state, currentTokenIndex: nextIndex });
    this.scheduleTick();
  }

  private clearTimer(): void {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}
