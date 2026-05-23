import { useCallback, useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import AtlasViewerShell from '../components/cockpit/AtlasViewerShell';
import {
  loadPythiaTrace,
  loadSpatialEvidenceDemo,
} from '../lib/loadFixtures';
import { PYTHIA_160M_PRESET } from '../lib/modelArchitecture';
import type { ReplayTrace } from '../lib/replayController';
import type { SpatialEvidenceArtifact } from '../lib/visualPrimitives';
import {
  appendLiveEvent,
  createLiveSession,
  emptyLiveTrace,
  type LiveTraceEvent,
} from '../lib/atlasLiveApi';
import type { LiveStatus, RuntimeMode } from '../components/cockpit/ControlBar';
import {
  buildLiveSessionRequest,
  type LiveMethodControls,
} from '../lib/liveMethodControls';
import { LIVE_WORKER_METHODS } from '../lib/testingMethods';

const viewportStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
  background: '#05070d',
  color: '#e5e7eb',
  fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
};

const messageStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '100%',
  height: '100%',
  fontSize: 14,
};

interface FixtureBundle {
  trace: ReplayTrace;
  spatial: SpatialEvidenceArtifact;
}

export default function CockpitPage(): JSX.Element {
  const [bundle, setBundle] = useState<FixtureBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>('replay');
  const [liveStatus, setLiveStatus] = useState<LiveStatus>('idle');
  const [liveError, setLiveError] = useState<string | null>(null);
  const [liveTrace, setLiveTrace] = useState<ReplayTrace | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const runIdRef = useRef(0);
  const restartTimerRef = useRef<number | null>(null);
  const latestControlsRef = useRef<LiveMethodControls | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [trace, spatial] = await Promise.all([
          loadPythiaTrace(),
          loadSpatialEvidenceDemo(),
        ]);
        if (cancelled) return;
        setBundle({ trace, spatial });
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      sourceRef.current?.close();
      if (restartTimerRef.current !== null) {
        window.clearTimeout(restartTimerRef.current);
      }
    };
  }, []);

  const beginLive = useCallback(
    async (controls: LiveMethodControls, reason: 'manual' | 'controls'): Promise<void> => {
      const storedCode = window.localStorage.getItem('atlas_live_invite_code') ?? '';
      const inviteCode =
        reason === 'manual'
          ? window.prompt('Enter Atlas LIVE invite code', storedCode)
          : storedCode;
      if (!inviteCode) return;
      window.localStorage.setItem('atlas_live_invite_code', inviteCode);

      sourceRef.current?.close();
      const runId = runIdRef.current + 1;
      runIdRef.current = runId;

      setRuntimeMode('live');
      setLiveStatus('connecting');
      setLiveError(reason === 'controls' ? 'Live controls changed; restarting worker stream.' : null);
      setLiveTrace(emptyLiveTrace());

      try {
        const session = await createLiveSession(
          buildLiveSessionRequest(controls),
          inviteCode,
        );

        if (runIdRef.current !== runId) return;
        const source = new EventSource(session.stream_url);
        sourceRef.current = source;
        let acceptedRealManifest = false;

        const applyEvent = (event: LiveTraceEvent): void => {
          if (runIdRef.current !== runId) return;
          if (event.type === 'manifest') {
            if (!event.manifest.is_real_model) {
              source.close();
              setLiveStatus('error');
              setLiveError('LIVE worker is not running actual weights; staying on replay.');
              setRuntimeMode('replay');
              return;
            }
            acceptedRealManifest = true;
            setLiveStatus('streaming');
            setLiveError(null);
          }
          if (event.type === 'error') {
            source.close();
            setLiveStatus('error');
            setLiveError(event.message);
            return;
          }
          if (event.type === 'complete') {
            setLiveStatus('complete');
            source.close();
            return;
          }
          setLiveTrace((prev) => appendLiveEvent(prev ?? emptyLiveTrace(session.model_id), event));
        };

        for (const eventName of ['manifest', 'neuron_covers', 'token', 'error', 'complete']) {
          source.addEventListener(eventName, (evt) => {
            try {
              applyEvent(JSON.parse((evt as MessageEvent).data) as LiveTraceEvent);
            } catch (err) {
              source.close();
              setLiveStatus('error');
              setLiveError(err instanceof Error ? err.message : String(err));
            }
          });
        }

        source.onerror = () => {
          if (runIdRef.current !== runId) return;
          source.close();
          setLiveStatus('error');
          setLiveError(
            acceptedRealManifest
              ? 'LIVE stream disconnected.'
              : 'LIVE stream failed before proving actual weights.',
          );
        };
      } catch (err) {
        if (runIdRef.current !== runId) return;
        setRuntimeMode('replay');
        setLiveStatus('error');
        setLiveError(err instanceof Error ? err.message : String(err));
      }
    },
    [],
  );

  const startLive = useCallback(
    (controls: LiveMethodControls): void => {
      latestControlsRef.current = controls;
      void beginLive(controls, 'manual');
    },
    [beginLive],
  );

  const handleLiveControlsChange = useCallback(
    (controls: LiveMethodControls): void => {
      latestControlsRef.current = controls;
      if (runtimeMode !== 'live') return;
      if (liveStatus === 'connecting') return;
      if (restartTimerRef.current !== null) {
        window.clearTimeout(restartTimerRef.current);
      }
      restartTimerRef.current = window.setTimeout(() => {
        void beginLive(controls, 'controls');
      }, 350);
    },
    [beginLive, liveStatus, runtimeMode],
  );

  const useReplay = useCallback((): void => {
    sourceRef.current?.close();
    runIdRef.current += 1;
    setRuntimeMode('replay');
    setLiveStatus('idle');
    setLiveError(null);
  }, []);

  if (error) {
    return (
      <main style={viewportStyle} data-testid="cockpit-page">
        <div style={messageStyle} role="alert">
          Failed to load Atlas Viewer fixtures: {error}
        </div>
      </main>
    );
  }

  if (!bundle) {
    return (
      <main style={viewportStyle} data-testid="cockpit-page">
        <div style={messageStyle} role="status">
          Loading Atlas Viewer fixtures…
        </div>
      </main>
    );
  }

  const displayedTrace = runtimeMode === 'live' && liveTrace ? liveTrace : bundle.trace;

  return (
    <main style={viewportStyle} data-testid="cockpit-page">
      <AtlasViewerShell
        trace={displayedTrace}
        spatialEvidence={bundle.spatial}
        architecture={PYTHIA_160M_PRESET}
        methods={LIVE_WORKER_METHODS}
        runtimeMode={runtimeMode}
        liveStatus={liveStatus}
        liveError={liveError}
        onStartLive={startLive}
        onLiveControlsChange={handleLiveControlsChange}
        onUseReplay={useReplay}
      />
    </main>
  );
}
