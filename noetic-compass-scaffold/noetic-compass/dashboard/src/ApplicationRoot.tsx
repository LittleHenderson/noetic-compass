import { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import App from './App.tsx';
import { CinematicIntro } from './components/shared/CinematicIntro';
import { PrerenderedClaimSurface } from './components/shared/PrerenderedClaimSurface';
import type { ClaimSurfaceKind } from './lib/claimSurfaceContract';


const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 60_000,
      gcTime: 5 * 60_000,
    },
  },
});


export function InteractiveApplication() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <CinematicIntro>
          <App />
        </CinematicIntro>
      </BrowserRouter>
    </QueryClientProvider>
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
