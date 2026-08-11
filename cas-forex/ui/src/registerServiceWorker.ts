export function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  if (import.meta.env.DEV) return;

  const staleBundleRecoveryKey = 'cas_forex_stale_bundle_recovered_at';
  const runtimeCachePrefixes = [
    'cas-forex-assets-',
    'cas-forex-code-',
    'workbox-precache',
    'precache-',
  ];

  const clearRuntimeCaches = async () => {
    if (!('caches' in window)) return;
    try {
      const names = await window.caches.keys();
      await Promise.all(
        names
          .filter((name) => runtimeCachePrefixes.some((prefix) => name.startsWith(prefix)))
          .map((name) => window.caches.delete(name)),
      );
    } catch {
      // Cache cleanup is best-effort; controllerchange reload still advances the app.
    }
  };

  const isStaleBundleError = (value: unknown): boolean => {
    const message = value instanceof Error
      ? value.message
      : String((value as { message?: unknown } | null)?.message ?? value ?? '');
    return /failed to fetch dynamically imported module|error loading dynamically imported module|importing a module script failed|chunkloaderror|load failed for module/i.test(message);
  };

  const recoverFromStaleBundle = async () => {
    const now = Date.now();
    const recent = Number(window.sessionStorage.getItem(staleBundleRecoveryKey) || 0);
    if (Number.isFinite(recent) && now - recent < 30_000) return;
    window.sessionStorage.setItem(staleBundleRecoveryKey, String(now));

    try {
      await clearRuntimeCaches();
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map((registration) => registration.unregister()));
    } catch {
      // Reload anyway; the network-first worker path may recover on the next boot.
    } finally {
      window.location.reload();
    }
  };

  window.addEventListener('vite:preloadError', (event) => {
    event.preventDefault();
    void recoverFromStaleBundle();
  });

  window.addEventListener('unhandledrejection', (event) => {
    if (!isStaleBundleError(event.reason)) return;
    event.preventDefault();
    void recoverFromStaleBundle();
  });

  let refreshing = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (refreshing) return;
    refreshing = true;
    void clearRuntimeCaches().finally(() => window.location.reload());
  });

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        const requestUpdate = () => {
          void registration.update();
        };

        requestUpdate();
        if (registration.waiting) {
          registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        }
        registration.addEventListener('updatefound', () => {
          const worker = registration.installing;
          if (!worker) return;
          worker.addEventListener('statechange', () => {
            if (worker.state === 'installed' && navigator.serviceWorker.controller) {
              void clearRuntimeCaches().finally(() => {
                worker.postMessage({ type: 'SKIP_WAITING' });
              });
            }
          });
        });
        window.setInterval(requestUpdate, 60_000);
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'visible') requestUpdate();
        });
      })
      .catch((err) => console.warn('CAS Forex service worker registration failed', err));
  });
}
