import { useEffect, useState } from 'react';
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

  const startLive = async (): Promise<void> => {
    if (liveStatus === 'connecting' || liveStatus === 'streaming') return;
    const storedCode = window.localStorage.getItem('atlas_live_invite_code') ?? '';
    const inviteCode = window.prompt('Enter Atlas LIVE invite code', storedCode);
    if (!inviteCode) return;
    window.localStorage.setItem('atlas_live_invite_code', inviteCode);

    setRuntimeMode('live');
    setLiveStatus('connecting');
    setLiveError(null);
    setLiveTrace(emptyLiveTrace());

    try {
      const session = await createLiveSession(
        {
          prompt: 'I noticed a warm coffee cup beside an open book under a sunny window.',
          max_new_tokens: 24,
          temperature: 0,
          seed: 42,
          probes: ['active_trace', 'blindspots_f1', 'mode7_attribution', 'confidence_margin'],
        },
        inviteCode,
      );

      const source = new EventSource(session.stream_url);
      let acceptedRealManifest = false;

      const applyEvent = (event: LiveTraceEvent): void => {
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
        source.close();
        setLiveStatus('error');
        setLiveError(
          acceptedRealManifest
            ? 'LIVE stream disconnected.'
            : 'LIVE stream failed before proving actual weights.',
        );
      };
    } catch (err) {
      setRuntimeMode('replay');
      setLiveStatus('error');
      setLiveError(err instanceof Error ? err.message : String(err));
    }
  };

  const useReplay = (): void => {
    setRuntimeMode('replay');
    setLiveStatus('idle');
    setLiveError(null);
  };

  const displayedTrace = runtimeMode === 'live' && liveTrace ? liveTrace : bundle.trace;

  return (
    <main style={viewportStyle} data-testid="cockpit-page">
      <AtlasViewerShell
        trace={displayedTrace}
        spatialEvidence={bundle.spatial}
        architecture={PYTHIA_160M_PRESET}
        runtimeMode={runtimeMode}
        liveStatus={liveStatus}
        liveError={liveError}
        onStartLive={startLive}
        onUseReplay={useReplay}
      />
    </main>
  );
}
