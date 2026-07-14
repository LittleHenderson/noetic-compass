import { StrictMode } from 'react';
import { createRoot, hydrateRoot, type Root } from 'react-dom/client';
import {
  InteractiveApplication,
  PrerenderHydrationMarker,
} from './ApplicationRoot';
import {
  CLAIM_SURFACE_SCHEMA_VERSION,
  claimSurfaceRoute,
  isClaimSurfaceKind,
} from './lib/claimSurfaceContract';
import './index.css';

const rootElement = document.getElementById('root');
if (rootElement === null) {
  throw new Error('Dashboard application mount #root is missing.');
}

const prerenderKind = rootElement.dataset.casPrerenderKind ?? '';
const prerenderRoute = rootElement.dataset.casPrerenderedRoute ?? '';
const prerenderSchema = rootElement.dataset.casPrerenderSchema ?? '';
const canHydratePrerender =
  isClaimSurfaceKind(prerenderKind)
  && prerenderSchema === CLAIM_SURFACE_SCHEMA_VERSION
  && prerenderRoute === claimSurfaceRoute(prerenderKind)
  && window.location.pathname === prerenderRoute;

if (canHydratePrerender) {
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
  // A generic SPA fallback or wrong-route file must never be treated as the
  // route-specific prerender contract. Clear any stale bytes before mounting.
  rootElement.replaceChildren();
  createRoot(rootElement).render(
    <StrictMode>
      <InteractiveApplication />
    </StrictMode>,
  );
}

// Reliability takes priority over offline caching for stakeholder demos.
// Unregister any prior service workers so stale bundles do not survive redeploys.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .getRegistrations()
      .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
      .catch(() => {
        // Ignore cleanup failures.
      });
  });
}
