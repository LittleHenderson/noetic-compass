/// <reference lib="webworker" />

const CACHE_NAME = 'noetic-compass-v2';
const STATIC_CACHE = 'noetic-static-v2';

const STATIC_EXTENSIONS = ['.js', '.css', '.woff', '.woff2', '.ttf', '.svg', '.png', '.jpg', '.ico'];

const OFFLINE_URL = '/offline.html';

// Install: precache the offline fallback
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll([
        OFFLINE_URL,
        '/icon-192.svg',
        '/icon-512.svg',
        '/favicon.svg',
        '/manifest.json',
      ])
    )
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== STATIC_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch: strategy depends on request type
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests — let the browser handle them directly
  if (request.method !== 'GET') return;

  // Cross-origin requests (API calls to Railway, etc.) — pass through untouched.
  // The service worker should NOT intercept or cache these. Let the browser
  // handle them natively so errors propagate correctly.
  if (url.origin !== self.location.origin) return;

  // Same-origin API calls: network-first with no cache fallback
  if (url.pathname.startsWith('/api')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets: cache-first
  if (STATIC_EXTENSIONS.some((ext) => url.pathname.endsWith(ext))) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Navigation requests: network-first, offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Everything else: network-first
  event.respondWith(networkFirst(request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('', { status: 503, statusText: 'Offline' });
  }
}

async function networkFirst(request) {
  try {
    return await fetch(request);
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Re-throw so the real network error surfaces to the caller
    throw err;
  }
}
