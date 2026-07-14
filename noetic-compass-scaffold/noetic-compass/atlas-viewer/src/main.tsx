import { StrictMode } from 'react';
import { createRoot, hydrateRoot, type Root } from 'react-dom/client';
import {
  InteractiveApplication,
  PrerenderHydrationMarker,
} from './ApplicationRoot';
import { prerenderedClaimSurfaceKind } from './lib/claimSurfaceContract';
import './styles/global.css';

const rootElement = document.getElementById('root');
if (rootElement === null) {
  throw new Error('Atlas Viewer application mount #root is missing.');
}

const prerenderKind = prerenderedClaimSurfaceKind(
  rootElement,
  window.location.pathname,
);

if (prerenderKind !== null) {
  let hydratedRoot: Root | null = null;
  let transitionScheduled = false;
  const transitionToInteractiveApplication = () => {
    if (transitionScheduled) return;
    transitionScheduled = true;
    queueMicrotask(() => {
      rootElement.removeAttribute('data-cas-prerendered-route');
      rootElement.removeAttribute('data-cas-prerender-schema');
      rootElement.removeAttribute('data-cas-prerender-kind');
      hydratedRoot?.render(
        <StrictMode>
          <InteractiveApplication />
        </StrictMode>,
      );
    });
  };
  hydratedRoot = hydrateRoot(
    rootElement,
    <StrictMode>
      <PrerenderHydrationMarker
        surfaceKind={prerenderKind}
        onHydrated={transitionToInteractiveApplication}
      />
    </StrictMode>,
  );
} else {
  // A neutral SPA fallback or wrong-route file must never be treated as the
  // route-specific contract. Clear stale static bytes before mounting.
  rootElement.removeAttribute('data-cas-prerendered-route');
  rootElement.removeAttribute('data-cas-prerender-schema');
  rootElement.removeAttribute('data-cas-prerender-kind');
  rootElement.replaceChildren();
  createRoot(rootElement).render(
    <StrictMode>
      <InteractiveApplication />
    </StrictMode>,
  );
}
