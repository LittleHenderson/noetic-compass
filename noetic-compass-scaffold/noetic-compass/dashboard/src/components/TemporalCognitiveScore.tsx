import { useEffect, useMemo, useRef, useState } from 'react';
import * as Tone from 'tone';
import {
  DOMAIN_NAMES,
  DRIVE_NAMES,
  NOETIC_NAMES,
  REGISTER_NAMES,
} from '../lib/mandala_types';
import type { Domain } from '../lib/mandala_types';
import { DRIVE_TEMPO_MAP } from '../lib/temporal_score/constants';
import { generateTemporalScore } from '../lib/temporal_score/cas_to_audio';
import type {
  PlaybackState,
  TemporalCognitiveScoreProps,
  TemporalScoreEvent,
} from '../lib/temporal_score/types';
import './TemporalCognitiveScore.css';

interface SynthLike {
  triggerAttackRelease: (
    note: string,
    duration: number | string,
    time?: number | string,
    velocity?: number,
  ) => unknown;
  dispose: () => void;
}

type SynthMap = Partial<Record<Domain, SynthLike>>;

function toSynth(value: unknown): SynthLike {
  return value as SynthLike;
}

function createSynths(): Record<Domain, SynthLike> {
  return {
    P: toSynth(new Tone.Synth().toDestination()),
    C: toSynth(new Tone.MonoSynth().toDestination()),
    E: toSynth(new Tone.FMSynth().toDestination()),
    O: toSynth(new Tone.MembraneSynth().toDestination()),
  };
}

function eventAtPosition(events: TemporalScoreEvent[], seconds: number): TemporalScoreEvent | null {
  return events.find((event) => (
    seconds >= event.timeSeconds
    && seconds < event.timeSeconds + Math.max(0.08, event.durationSeconds)
  )) ?? null;
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0:00';
  const whole = Math.floor(seconds);
  const minutes = Math.floor(whole / 60);
  const remainder = `${whole % 60}`.padStart(2, '0');
  return `${minutes}:${remainder}`;
}

export function TemporalCognitiveScore({
  cognitiveState,
  onPlayStateChange,
  onCurrentDomainChange,
}: TemporalCognitiveScoreProps) {
  const [playbackState, setPlaybackState] = useState<PlaybackState>('stopped');
  const [positionSeconds, setPositionSeconds] = useState(0);
  const [volumeDb, setVolumeDb] = useState(-12);
  const [tempoOverrideBpm, setTempoOverrideBpm] = useState(0);
  const [activeDomain, setActiveDomain] = useState<Domain | null>(null);

  const synthsRef = useRef<SynthMap>({});
  const timerRef = useRef<number | null>(null);
  const playedEventIdsRef = useRef<Set<string>>(new Set());
  const startMsRef = useRef(0);
  const basePositionRef = useRef(0);
  const activeDomainRef = useRef<Domain | null>(null);

  const score = useMemo(() => generateTemporalScore(cognitiveState, {
    tempoOverrideBpm,
  }), [cognitiveState, tempoOverrideBpm]);

  const currentEvent = eventAtPosition(score.events, positionSeconds);
  const progressPercent = score.durationSeconds > 0
    ? Math.min(100, (positionSeconds / score.durationSeconds) * 100)
    : 0;
  const dominantDriveTempo = DRIVE_TEMPO_MAP[score.dominantDrive];

  function clearTicker() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  function disposeSynths() {
    Object.values(synthsRef.current).forEach((synth) => synth?.dispose());
    synthsRef.current = {};
  }

  function ensureSynths(): Record<Domain, SynthLike> {
    if (!synthsRef.current.P || !synthsRef.current.C || !synthsRef.current.E || !synthsRef.current.O) {
      synthsRef.current = createSynths();
    }
    return synthsRef.current as Record<Domain, SynthLike>;
  }

  function notifyPlaybackState(nextState: PlaybackState) {
    setPlaybackState(nextState);
    onPlayStateChange?.(nextState);
  }

  function notifyActiveDomain(nextDomain: Domain | null) {
    if (activeDomainRef.current === nextDomain) return;
    activeDomainRef.current = nextDomain;
    setActiveDomain(nextDomain);
    onCurrentDomainChange?.(nextDomain);
  }

  function playDueEvents(seconds: number) {
    const synths = ensureSynths();
    for (const event of score.events) {
      if (event.timeSeconds > seconds || playedEventIdsRef.current.has(event.id)) continue;
      playedEventIdsRef.current.add(event.id);
      if (event.type === 'note' && event.pitch) {
        synths[event.domain].triggerAttackRelease(
          event.pitch,
          Math.max(0.08, event.durationSeconds),
          undefined,
          event.velocity,
        );
      }
    }
  }

  function tick() {
    const elapsed = basePositionRef.current + ((Date.now() - startMsRef.current) / 1000);
    const nextPosition = Math.min(elapsed, score.durationSeconds);
    setPositionSeconds(nextPosition);
    playDueEvents(nextPosition);
    notifyActiveDomain(eventAtPosition(score.events, nextPosition)?.domain ?? null);

    if (score.durationSeconds > 0 && elapsed >= score.durationSeconds) {
      clearTicker();
      Tone.Transport.stop();
      Tone.Transport.cancel();
      disposeSynths();
      notifyActiveDomain(null);
      notifyPlaybackState('stopped');
      basePositionRef.current = 0;
      playedEventIdsRef.current = new Set();
    }
  }

  function startTicker() {
    clearTicker();
    tick();
    timerRef.current = window.setInterval(tick, 80);
  }

  async function handlePlay() {
    if (score.events.length === 0 || playbackState === 'playing') return;
    const resumePosition = positionSeconds >= score.durationSeconds ? 0 : positionSeconds;

    await Tone.start();
    Tone.getDestination().volume.value = volumeDb;
    Tone.Transport.bpm.value = score.bpm;
    Tone.Transport.start();

    basePositionRef.current = resumePosition;
    startMsRef.current = Date.now();
    playedEventIdsRef.current = new Set(
      score.events
        .filter((event) => event.timeSeconds < resumePosition)
        .map((event) => event.id),
    );
    setPositionSeconds(resumePosition);
    notifyPlaybackState('playing');
    startTicker();
  }

  function handlePause() {
    if (playbackState !== 'playing') return;
    clearTicker();
    const pausedAt = Math.min(
      score.durationSeconds,
      basePositionRef.current + ((Date.now() - startMsRef.current) / 1000),
    );
    basePositionRef.current = pausedAt;
    setPositionSeconds(pausedAt);
    Tone.Transport.pause();
    notifyPlaybackState('paused');
  }

  function handleStop() {
    clearTicker();
    Tone.Transport.stop();
    Tone.Transport.cancel();
    disposeSynths();
    playedEventIdsRef.current = new Set();
    basePositionRef.current = 0;
    setPositionSeconds(0);
    notifyActiveDomain(null);
    notifyPlaybackState('stopped');
  }

  function handleScrub(nextPosition: number) {
    const bounded = Math.min(score.durationSeconds, Math.max(0, nextPosition));
    setPositionSeconds(bounded);
    basePositionRef.current = bounded;
    startMsRef.current = Date.now();
    playedEventIdsRef.current = new Set(
      score.events
        .filter((event) => event.timeSeconds < bounded)
        .map((event) => event.id),
    );
    notifyActiveDomain(eventAtPosition(score.events, bounded)?.domain ?? null);
  }

  useEffect(() => {
    Tone.getDestination().volume.value = volumeDb;
  }, [volumeDb]);

  useEffect(() => () => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
    }
    Tone.Transport.stop();
    Tone.Transport.cancel();
    Object.values(synthsRef.current).forEach((synth) => synth?.dispose());
  }, []);

  return (
    <section className="temporal-score" aria-labelledby="temporal-score-title">
      <div className="temporal-score__header">
        <div>
          <p className="temporal-score__eyebrow">Phase B live</p>
          <h3 id="temporal-score-title" className="temporal-score__title">
            Temporal Cognitive Score
          </h3>
          <p className="temporal-score__subtitle">
            Synthesized audio from formal CAS primitives. No samples, no auto-play.
          </p>
        </div>
        <div className="temporal-score__status" data-testid="temporal-score-status">
          {playbackState}
        </div>
      </div>

      <div className="temporal-score__meta-grid">
        <div>
          <span>Dominant drive</span>
          <strong>{score.dominantDrive} {DRIVE_NAMES[score.dominantDrive]}</strong>
        </div>
        <div>
          <span>Tempo source</span>
          <strong>{score.bpm} BPM, {dominantDriveTempo.tempoMarking}</strong>
        </div>
        <div>
          <span>Events</span>
          <strong>{score.events.length} formal events</strong>
        </div>
        <div>
          <span>Current domain</span>
          <strong>{activeDomain ? `${activeDomain} ${DOMAIN_NAMES[activeDomain]}` : 'None'}</strong>
        </div>
      </div>

      <div className="temporal-score__staves" aria-label="Four Domain staves">
        {score.staves.map((stave) => (
          <div
            key={stave.domain}
            className={`temporal-score__stave${activeDomain === stave.domain ? ' temporal-score__stave--active' : ''}`}
            data-testid={`temporal-stave-${stave.domain}`}
            data-domain={stave.domain}
          >
            <div className="temporal-score__stave-label">
              <span>{stave.domain}</span>
              <small>{stave.label}</small>
            </div>
            <div className="temporal-score__stave-line" aria-hidden="true">
              <span style={{ width: `${progressPercent}%` }} />
            </div>
            <div className="temporal-score__instrument">{stave.instrument}</div>
          </div>
        ))}
      </div>

      <div className="temporal-score__controls" aria-label="Temporal Cognitive Score controls">
        <button
          type="button"
          onClick={() => void handlePlay()}
          disabled={score.events.length === 0 || playbackState === 'playing'}
          data-testid="temporal-play"
        >
          Play
        </button>
        <button
          type="button"
          onClick={handlePause}
          disabled={playbackState !== 'playing'}
          data-testid="temporal-pause"
        >
          Pause
        </button>
        <button
          type="button"
          onClick={handleStop}
          disabled={playbackState === 'stopped' && positionSeconds === 0}
          data-testid="temporal-stop"
        >
          Stop
        </button>
      </div>

      <label className="temporal-score__slider">
        <span>Scrub {formatTime(positionSeconds)} / {formatTime(score.durationSeconds)}</span>
        <input
          type="range"
          min="0"
          max={Math.max(0.1, score.durationSeconds)}
          step="0.05"
          value={positionSeconds}
          onChange={(event) => handleScrub(Number(event.currentTarget.value))}
          data-testid="temporal-scrub"
        />
      </label>

      <div className="temporal-score__fine-controls">
        <label>
          <span>Volume</span>
          <input
            type="range"
            min="-48"
            max="0"
            step="1"
            value={volumeDb}
            onChange={(event) => setVolumeDb(Number(event.currentTarget.value))}
            data-testid="temporal-volume"
          />
        </label>
        <label>
          <span>Tempo override</span>
          <input
            type="range"
            min="0"
            max="180"
            step="1"
            value={tempoOverrideBpm}
            onChange={(event) => setTempoOverrideBpm(Number(event.currentTarget.value))}
            aria-description="Set to zero to use the dominant Drive tempo."
            data-testid="temporal-tempo"
          />
          <small>{tempoOverrideBpm === 0 ? 'Drive tempo' : `${tempoOverrideBpm} BPM`}</small>
        </label>
      </div>

      <div className="temporal-score__caption" aria-live="polite" data-testid="temporal-caption">
        {currentEvent
          ? currentEvent.caption
          : score.events.length === 0
            ? 'No active CAS events to sonify.'
            : 'Ready. Press Play to hear the CAS-derived score.'}
      </div>

      <div className="temporal-score__transcript">
        <div className="temporal-score__transcript-head">
          <strong>Visual transcript</strong>
          <span>{score.involutionTensions.length} active involution tensions</span>
        </div>
        <ol data-testid="temporal-transcript">
          {score.transcript.slice(0, 18).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      </div>

      <div className="temporal-score__legend" aria-label="Mapping summary">
        <span>Noetics map to pitch: {NOETIC_NAMES.N0} C4 through {NOETIC_NAMES.N9} C5.</span>
        <span>Registers map to expression: |T fermata, |A staccato, |f legato, |E marcato.</span>
        <span>Lacunarity maps to rests.</span>
        <span>Drives map to tempo: F1 50 BPM through F7 138 BPM.</span>
        <span>Register labels: {REGISTER_NAMES.T}, {REGISTER_NAMES.A}, {REGISTER_NAMES.f}, {REGISTER_NAMES.E}.</span>
      </div>
    </section>
  );
}

export default TemporalCognitiveScore;
