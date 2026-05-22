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

  return (
    <main style={viewportStyle} data-testid="cockpit-page">
      <AtlasViewerShell
        trace={bundle.trace}
        spatialEvidence={bundle.spatial}
        architecture={PYTHIA_160M_PRESET}
      />
    </main>
  );
}
