import { useCallback, useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import AtlasViewerShell from '../components/cockpit/AtlasViewerShell';
import {
  loadPythiaTrace,
  loadSpatialEvidenceDemos,
} from '../lib/loadFixtures';
import { PYTHIA_160M_PRESET } from '../lib/modelArchitecture';
import type { ReplayTrace } from '../lib/replayController';
import type { SpatialEvidenceArtifact } from '../lib/visualPrimitives';
import {
  AtlasLiveError,
  appendLiveEvent,
  createLiveSession,
  emptyLiveTrace,
  errorFromLiveProof,
  fetchLiveRealModeProof,
  isLiveRealModeProofVerified,
  liveFailureMessage,
  liveProofFailureMessage,
  openLiveEventStream,
  type LiveTraceEvent,
  type LiveEventStreamHandle,
  type LiveRealModeProof,
  type ResolvedKnobs,
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
  spatialOptions: SpatialEvidenceArtifact[];
}

export default function CockpitPage(): JSX.Element {
  const [bundle, setBundle] = useState<FixtureBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>('replay');
  const [liveStatus, setLiveStatus] = useState<LiveStatus>('idle');
  const [liveVerified, setLiveVerified] = useState<boolean | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [liveTrace, setLiveTrace] = useState<ReplayTrace | null>(null);
  const [liveProof, setLiveProof] = useState<LiveRealModeProof | null>(null);
  const [liveProofChecking, setLiveProofChecking] = useState<boolean>(false);
  const [resolvedKnobs, setResolvedKnobs] = useState<ResolvedKnobs | null>(null);
  const sourceRef = useRef<LiveEventStreamHandle | null>(null);
  const runIdRef = useRef(0);
  const restartTimerRef = useRef<number | null>(null);
  const latestControlsRef = useRef<LiveMethodControls | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [trace, spatial] = await Promise.all([
          loadPythiaTrace(),
          loadSpatialEvidenceDemos(),
        ]);
        if (cancelled) return;
        setBundle({ trace, spatial: spatial[0], spatialOptions: spatial });
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

  const refreshLiveProof = useCallback(async (): Promise<LiveRealModeProof> => {
    setLiveProofChecking(true);
    let proof: LiveRealModeProof;
    try {
      proof = await fetchLiveRealModeProof();
    } catch (err) {
      proof = {
        verdict: 'PROOF_CHECK_FAILED',
        is_real_model: false,
        model_loaded: false,
        load_error: err instanceof Error ? err.message : String(err),
        http_status: 0,
        checked_at: new Date().toISOString(),
      };
    } finally {
      setLiveProofChecking(false);
    }
    setLiveProof(proof);
    return proof;
  }, []);

  useEffect(() => {
    void refreshLiveProof();
  }, [refreshLiveProof]);

  const beginLive = useCallback(
    async (controls: LiveMethodControls, reason: 'manual' | 'controls'): Promise<void> => {
      const storedCode = window.localStorage.getItem('atlas_live_invite_code') ?? '';
      const inviteCode =
        reason === 'manual'
          ? window.prompt('Enter Atlas LIVE invite code', storedCode)
          : storedCode;
      if (!inviteCode?.trim()) {
        setRuntimeMode('replay');
        setLiveStatus('error');
        setLiveVerified(false);
        setLiveError(liveFailureMessage('missing_invite'));
        return;
      }
      const trimmedInviteCode = inviteCode.trim();
      window.localStorage.setItem('atlas_live_invite_code', trimmedInviteCode);

      sourceRef.current?.close();
      const runId = runIdRef.current + 1;
      runIdRef.current = runId;

      setRuntimeMode('live');
      setLiveStatus('connecting');
      setLiveVerified(null);
      setLiveError(reason === 'controls' ? 'Live controls changed; restarting worker stream.' : null);
      setLiveTrace(emptyLiveTrace());
      // Reset on each session so the diagnostic disclosure can show
      // "awaiting worker echo" until the new session emits its
      // KnobResolutionEvent.
      setResolvedKnobs(null);

      try {
        const session = await createLiveSession(
          buildLiveSessionRequest(controls),
          trimmedInviteCode,
        );
        const proof = await refreshLiveProof();

        if (runIdRef.current !== runId) return;
        if (!isLiveRealModeProofVerified(proof)) {
          throw errorFromLiveProof(proof);
        }

        const failLive = (err: AtlasLiveError): void => {
          if (runIdRef.current !== runId) return;
          setRuntimeMode('replay');
          setLiveStatus('error');
          setLiveVerified(false);
          setLiveError(err.message);
          setLiveTrace(null);
        };

        const applyEvent = (event: LiveTraceEvent): void => {
          if (runIdRef.current !== runId) return;
          if (event.type === 'manifest') {
            if (!event.manifest.is_real_model || !isLiveRealModeProofVerified(proof)) {
              sourceRef.current?.close();
              failLive(
                new AtlasLiveError(
                  'unverified_model',
                  event.manifest.is_real_model
                    ? liveProofFailureMessage(proof)
                    : 'LIVE worker manifest is fake or unverified, so LIVE was stopped before any actual-weights claim.',
                ),
              );
              return;
            }
            setLiveVerified(true);
            setLiveStatus('streaming');
            setLiveError(null);
          }
          if (event.type === 'knob_resolution') {
            setResolvedKnobs(event.resolved_knobs);
            return;
          }
          if (event.type === 'error') {
            sourceRef.current?.close();
            failLive(new AtlasLiveError('stream_disconnected', event.message));
            return;
          }
          if (event.type === 'complete') {
            setLiveStatus('complete');
            sourceRef.current?.close();
            return;
          }
          setLiveTrace((prev) => appendLiveEvent(prev ?? emptyLiveTrace(session.model_id), event));
        };

        sourceRef.current = openLiveEventStream(session.stream_url, {
          maxTransportErrors: 1,
          onEvent: applyEvent,
          onFailure: failLive,
          onTransportError: (attempt, maxAttempts) => {
            if (runIdRef.current !== runId) return;
            setLiveStatus('connecting');
            setLiveError(
              `LIVE stream disconnected; retrying ${attempt}/${maxAttempts}.`,
            );
          },
        });
      } catch (err) {
        if (runIdRef.current !== runId) return;
        setRuntimeMode('replay');
        setLiveStatus('error');
        setLiveVerified(false);
        setLiveTrace(null);
        setLiveError(
          err instanceof Error
            ? err.message
            : liveFailureMessage('bad_response'),
        );
      }
    },
    [refreshLiveProof],
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
    setLiveVerified(null);
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
        spatialEvidenceOptions={bundle.spatialOptions}
        architecture={PYTHIA_160M_PRESET}
        methods={LIVE_WORKER_METHODS}
        runtimeMode={runtimeMode}
        liveStatus={liveStatus}
        liveVerified={liveVerified}
        liveProof={liveProof}
        liveProofChecking={liveProofChecking}
        liveError={liveError}
        onStartLive={startLive}
        onRefreshLiveProof={refreshLiveProof}
        onLiveControlsChange={handleLiveControlsChange}
        onUseReplay={useReplay}
        resolvedKnobs={resolvedKnobs}
      />
    </main>
  );
}
