import { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import { PrerenderedClaimSurface } from './components/shared/PrerenderedClaimSurface';
import type { ClaimSurfaceKind } from './lib/claimSurfaceContract';

export function InteractiveApplication() {
  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
}

export function PrerenderHydrationMarker({
  surfaceKind,
  onHydrated,
}: {
  surfaceKind: ClaimSurfaceKind;
  onHydrated: () => void;
}) {
  useEffect(() => {
    onHydrated();
  }, [onHydrated]);

  return <PrerenderedClaimSurface surfaceKind={surfaceKind} />;
}
